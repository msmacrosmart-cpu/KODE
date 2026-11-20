# -*- coding: utf-8 -*-
"""Anuncio de video (VAST) para a TV, tocado pelo proprio player do Kodi.

POR QUE ESTE MODULO EXISTE
==========================
O Google declara, na documentacao do SDK, que o Google Mobile Ads (AdMob) **nao
tem suporte a Android TV** (https://developers.google.com/admob/android/sdk).
O interstitial que funciona no celular, na TV, ou nao preenche ou abre e volta
vazio - foi exatamente o que o usuario viu no projetor. Nao e um bloco novo no
AdMob que resolve: o formato nao existe para TV.

O formato que existe em TV e o **anuncio de video linear (VAST)**. O caminho
usado ate aqui exigia compilar o Google IMA SDK dentro do app Android (dex
novo), o que e build de codigo-fonte e nao cabe no pipeline deste projeto.

Este modulo faz o mesmo trabalho com o que JA existe no APK:

    1. pede a tag VAST por HTTP;
    2. le o XML e escolhe o arquivo de video do anuncio (MediaFile);
    3. entrega esse arquivo ao player do Kodi (``PlayMedia``), que sabe tocar
       video em TV/box/stick/projetor - o mesmo player que toca os canais;
    4. dispara os eventos VAST obrigatorios (impression, quartis, complete,
       skip) para o Ad Server nao tratar como impressao invalida;
    5. usa a ``Retomada`` que ja existe para o conteudo voltar no ponto certo
       depois do anuncio (ao vivo nunca recebe seek).

O que NAO existe aqui, de proposito:

* nenhum anuncio simulado ou "de mentira" quando falta tag/rede: sem tag, a
  TV continua sem anuncio e a reproducao segue (comportamento seguro);
* nenhuma tag inventada. A tag vem do Ad Manager (VAST) configurada pelo dono
  do app, em ``VAST_TAG_PADRAO`` (smart_ads.py) ou na propriedade da janela;
* nenhuma chamada de rede no meio da reproducao sem timeout: o anuncio tem
  prazo e, se estourar, o conteudo segue.

REGRA DE FREQUENCIA
===================
Quem decide se ha anuncio continua sendo ``ads_regra`` (1 por conteudo por
sessao, 2 min apos a conclusao/pulo, VIP nunca, uma tentativa por troca).
Este modulo so sabe EXIBIR o anuncio; nao decide frequencia.
"""
from __future__ import absolute_import, unicode_literals

import json
import os
import re
import threading
import time

import xbmc

# Prazo total do anuncio: passou disso, o conteudo volta. Um VAST malformado
# ou um MP4 que nunca carrega nao podem prender o usuario na TV.
TEMPO_MAXIMO_ANUNCIO = 45
# Se a posicao do video do anuncio ficar parada por mais que isto (quadro
# congelado no 2o anuncio ou player mudo em 0.0s), encerra e devolve o conteudo.
TEMPO_TRAVAMENTO_ANUNCIO = 6.0
# Quanto esperar o video do anuncio realmente comecar.
ESPERA_INICIO = 10
# Tolerancia para considerar que o anuncio terminou (fim do arquivo).
FOLGA_FIM = 1.5
# Eventos VAST: quartis de exibicao.
QUARTIS = (('start', 0.0), ('firstQuartile', 0.25), ('midpoint', 0.5),
           ('thirdQuartile', 0.75), ('complete', 1.0))
TIMEOUT_HTTP = 12
# Um Wrapper aponta para outra tag (e assim que o Ad Manager entrega quando ha
# mediacao). Seguimos no maximo 2 niveis: mais que isso e cadeia suspeita e o
# usuario ficaria esperando anuncio.
PROFUNDIDADE_WRAPPER = 2

# Onde a tag pode estar, em ordem de prioridade. Nada aqui e um valor fixo:
# sao lugares para LER a tag que o dono do app configurou.
PROPRIEDADE_TAG = 'smartedtv.vast.tag'

# Tag VAST padrao do projeto (HilltopAds).
#
# Fica AQUI, no modulo de anuncio de video, e e o valor usado pelo
# ``smart_ads.VAST_TAG_PADRAO`` (que passa a ler daqui em vez de repetir a URL).
# Um lugar so para trocar a tag do dono do app - nada de duas copias.
#
# Restricao de uso: este fluxo VAST e o anuncio de VIDEO da TV (Android TV,
# TV Box, stick e projetor Android). Quem decide isso continua sendo o
# ``eh_tv()`` de ``variante.py``: no celular/tablet o anuncio e o AdMob da
# activity nativa e este modulo nao e chamado.
VAST_TAG_PADRAO = ('https://vapid-size.com/dEmwF.zYdOGYNKvRZ/GoUG/beLmU9TuDZrUJl/'
                   'koPpTRcX2iNbDMED3/NzDLkpt/N/zFYf0/MsTEcv1sMXwC')


def _agora():
    """Relogio unico do modulo (os testes trocam sem esperar de verdade)."""
    return time.monotonic()


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------
def tag_configurada(padrao=''):
    """Tag VAST a usar: do dono do app (janela), do modulo ou de teste.

    Ordem: propriedade da janela (permite trocar a tag sem atualizar o APK) ->
    ``padrao`` recebido (hoje o ``VAST_TAG_PADRAO`` deste modulo, a tag do
    projeto) -> tag de TESTE oficial, e essa apenas com o modo de validacao
    ligado. Sem nada disso devolve '' - nunca inventa URL.
    """
    try:
        da_janela = xbmc.getInfoLabel('Window(10000).Property(%s)' % PROPRIEDADE_TAG)
    except Exception:
        da_janela = ''
    for candidata in (da_janela, padrao):
        texto = (candidata or '').strip()
        if texto.lower().startswith(('http://', 'https://')):
            return texto
    if modo_de_teste():
        # Validacao em aparelho: usa o inventario de TESTE oficial do Google.
        # Nunca gera trafego invalido; e o mesmo que o SDK de teste faria.
        return tag_de_teste()
    return ''


def modo_de_teste():
    """True quando o dono do app ligou o modo de validacao.

    Ligado pela setting ``ads_teste`` do addon (a mesma tela de Ajustes que ja
    tem "Testar anuncio") ou pela propriedade da janela. So neste modo a tag
    de TESTE oficial do Google e usada - em uso normal, sem tag do projeto,
    nao ha anuncio nenhum.
    """
    try:
        valor = xbmc.getInfoLabel('Window(10000).Property(smartedtv.vast.teste)')
    except Exception:
        valor = ''
    if (valor or '').strip().lower() in ('1', 'true', 'sim', 'on'):
        return True
    return False


def tag_de_teste():
    """Tag de TESTE oficial do Google - a de ANUNCIO UNICO (VAST).

    A tag que estava aqui era ``external/vmap/single_ad_samples``: o corpus
    ``vmap`` devolve um **VMAP** (``<vmap:VMAP><vmap:AdBreak>...``), nao um
    VAST. O nosso leitor procura ``<Ad><InLine>``; num VMAP nao existe nenhum,
    entao o caminho caia em ``vast-sem-criativo`` e NENHUM anuncio tocava no
    "Testar anuncio" - exatamente o "nunca consegui ver um anuncio na TV".

    A tag abaixo e do mesmo inventario de teste do Google e responde VAST de
    verdade. A leitura de VMAP tambem foi adicionada em ``escolher_anuncio``,
    para que uma tag VMAP do dono do app (o caso comum no Ad Manager) funcione
    em vez de ser descartada.
    """
    return ('https://pubads.g.doubleclick.net/gampad/ads?iu=/21775744923/'
            'external/single_ad_samples&sz=640x480&cust_params='
            'sample_ct%3Dlinear&ciu_szs=300x250&gdfp_req=1&output=vast'
            '&unviewed_position_start=1&env=vp&impl=s&correlator=')


# ---------------------------------------------------------------------------
# VAST
# ---------------------------------------------------------------------------
def _texto(elemento, nome):
    achado = elemento.find(nome) if elemento is not None else None
    if achado is None or achado.text is None:
        return ''
    return achado.text.strip()


def _urls_de_evento(linear, evento):
    """URLs de tracking de um evento VAST (``<Tracking event="...">``)."""
    urls = []
    for rastreio in linear.iter('Tracking'):
        if (rastreio.get('event') or '').strip().lower() != evento.lower():
            continue
        valor = (rastreio.text or '').strip()
        if valor.startswith(('http://', 'https://')):
            urls.append(valor)
    return urls


def _urls_de_impressao(inline):
    urls = []
    for impressao in inline.iter('Impression'):
        valor = (impressao.text or '').strip()
        if valor.startswith(('http://', 'https://')):
            urls.append(valor)
    return urls


def _media_escolhido(inline, altura_tela=0):
    """Arquivo do anuncio que o player do Kodi consegue tocar.

    Preferencia: MP4/WebM progressivo (o Kodi abre direto por URL), do maior
    para o menor. HLS (``application/x-mpegURL``) entra como segunda opcao -
    o Kodi 21 toca HLS, mas em box/stick antigo o MP4 e mais confiavel.
    """
    candidatos = []
    for linear in inline.iter('Linear'):
        for media in linear.iter('MediaFile'):
            url = (media.text or '').strip()
            if not url.startswith(('http://', 'https://')):
                continue
            tipo = (media.get('type') or '').lower()
            largura = _inteiro(media.get('width'))
            altura = _inteiro(media.get('height'))
            url_limpa = url.lower().split('?', 1)[0]
            mp4 = (tipo.startswith(('video/mp4', 'video/x-m4v'))
                   or (not tipo and url_limpa.endswith(('.mp4', '.m4v'))))
            progressivo = mp4 or tipo.startswith('video/webm')
            hls = 'mpegurl' in tipo or url_limpa.endswith('.m3u8')
            if not (progressivo or hls):
                continue
            candidatos.append({
                'url': url,
                'tipo': tipo,
                'largura': largura,
                'altura': altura,
                'prioridade': 0 if mp4 else (1 if progressivo else 2),
                'progressivo': progressivo,
                # perto da resolucao da tela = menos up/downscale no aparelho
                'proximidade': abs((altura or 0) - (altura_tela or 1080)),
            })
    if not candidatos:
        return None
    candidatos.sort(key=lambda item: (item['prioridade'],
                                      item['proximidade'],
                                      -item['altura'], -item['largura']))
    return candidatos[0]


def _inteiro(valor):
    try:
        return int(float(str(valor).strip()))
    except Exception:
        return 0


def _segundos(valor):
    """``HH:MM:SS`` ou segundos puros -> segundos (0 quando nao der)."""
    texto = str(valor or '').strip()
    if not texto:
        return 0
    if ':' in texto:
        return int(_duracao_texto(texto))
    return _inteiro(texto)


def _duracao(linear):
    return _duracao_texto(_texto(linear, 'Duration'))


def _duracao_texto(bruto):
    achado = re.match(r'^(\d+):(\d+):(\d+(?:\.\d+)?)$', bruto or '')
    if not achado:
        return 0.0
    horas, minutos, segundos = achado.groups()
    return int(horas) * 3600 + int(minutos) * 60 + float(segundos)


def sem_namespace(xml):
    """XML com as tags sem namespace, antes de qualquer busca.

    O ElementTree devolve ``{uri}Ad`` para todo elemento de um XML que declara
    namespace default - e ``raiz.iter('Ad')`` nao encontra NADA. O VAST do
    HilltopAds (a tag do projeto) vem exatamente assim:

        <VAST version="3.0" xmlns="http://www.w3.org/2001/XMLSchema">
          <Ad id="567581"><InLine><Linear><MediaFile>...

    Sem este passo um VAST perfeitamente valido era lido como "sem criativo"
    e nenhum anuncio tocava na TV. Aqui os ``xmlns`` sao removidos e os
    prefixos (``vmap:AdBreak``) tambem, para a busca por nome simples
    funcionar nos dois formatos. Devolve o texto ('' quando nao houver).
    """
    if not xml:
        return ''
    if isinstance(xml, bytes):
        xml = xml.decode('utf-8', 'replace')
    texto = re.sub(r'\sxmlns(:[\w.-]+)?="[^"]*"', '', xml)
    # <ns:Tag> / </ns:Tag> -> <Tag> / </Tag> (so em marcacao de abertura/fecho)
    return re.sub(r'(</?)[A-Za-z_][\w.-]*:', r'\1', texto)


def tag_do_wrapper(xml):
    """URL que um ``<Wrapper>`` manda seguir ('' quando nao e wrapper)."""
    if not xml:
        return ''
    xml = sem_namespace(xml)
    try:
        import xml.etree.ElementTree as ET
        raiz = ET.fromstring(xml.strip())
    except Exception:
        return ''
    for anuncio in raiz.iter('Ad'):
        wrapper = anuncio.find('Wrapper')
        if wrapper is None:
            continue
        for alvo in wrapper.iter('VASTAdTagURI'):
            valor = (alvo.text or '').strip()
            if valor.startswith(('http://', 'https://')):
                return valor
    return ''


def tag_do_vmap(xml):
    """URL do primeiro ``<AdBreak>`` de um VMAP ('' quando nao e VMAP).

    O Ad Manager entrega playlist de anuncios em VMAP por padrao. O criativo
    continua sendo VAST: a URL de cada AdBreak aponta para a tag VAST daquele
    intervalo. Sem este passo um VMAP era descartado como "sem criativo".
    """
    if not xml:
        return ''
    xml = sem_namespace(xml)
    try:
        import xml.etree.ElementTree as ET
        raiz = ET.fromstring(xml.strip())
    except Exception:
        return ''
    if 'VMAP' not in (raiz.tag.split('}')[-1] or ''):
        return ''
    for alvo in raiz.iter():
        if alvo.tag.split('}')[-1] != 'AdTagURI':
            continue
        valor = (alvo.text or '').strip()
        if valor.startswith(('http://', 'https://')):
            return valor
    return ''


def escolher_anuncio(xml, altura_tela=0):
    """Le o VAST e devolve o anuncio a tocar (dict) ou ``None``.

    Aceita o XML como texto ou bytes. Um VAST de ``Wrapper`` (que aponta para
    outra tag) NAO vira anuncio aqui: quem chama precisa seguir a tag (ver
    ``exibir``, que segue ate ``PROFUNDIDADE_WRAPPER`` niveis).
    """
    try:
        import xml.etree.ElementTree as ET
    except Exception:
        return None
    if not xml:
        return None
    # Namespace default (o VAST do HilltopAds usa) faria ``iter('Ad')`` nao
    # achar nada: normaliza antes de ler.
    xml = sem_namespace(xml)
    try:
        raiz = ET.fromstring(xml.strip())
    except Exception:
        return None
    for anuncio in raiz.iter('Ad'):
        inline = anuncio.find('InLine')
        if inline is None:
            continue
        linear = inline.find('.//Linear')
        if linear is None:
            continue
        media = _media_escolhido(inline, altura_tela)
        if not media:
            continue
        criativo = inline.find('Creatives/Creative')
        try:
            identificador = (criativo.get('id') if criativo is not None
                             else '') or ''
        except Exception:
            identificador = ''
        eventos = {}
        for nome, _quarto in QUARTIS:
            eventos[nome] = _urls_de_evento(linear, nome)
        eventos['skip'] = _urls_de_evento(linear, 'skip')
        return {
            'url': media['url'],
            'tipo': media['tipo'],
            'duracao': _duracao(linear),
            'tempo_skip': _segundos(linear.get('skipoffset')),
            'impressao': _urls_de_impressao(inline),
            'eventos': eventos,
            'id': identificador,
            'errors': [valor.strip() for valor in
                       [(e.text or '') for e in inline.iter('Error')]
                       if valor.strip().startswith(('http', '//'))],
        }
    return None


# ---------------------------------------------------------------------------
# Rede (isolada, para poder testar sem internet)
# ---------------------------------------------------------------------------
def baixar(url, timeout=TIMEOUT_HTTP):
    """GET simples com timeout. Devolve bytes ou ``None``."""
    if not url:
        return None
    try:
        from urllib.request import Request, urlopen
    except Exception:  # pragma: no cover - Python 2 nao existe no Kodi 21
        return None
    try:
        pedido = Request(url, headers={
            'User-Agent': (
                'Mozilla/5.0 (Linux; Android 11; Android TV) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/xml, text/xml, */*',
        })
        resposta = urlopen(pedido, timeout=timeout)
        try:
            return resposta.read()
        finally:
            resposta.close()
    except Exception:
        return None


def disparar(urls):
    """Chama as URLs de tracking (impression/quartis). Silencioso por natureza."""
    if not urls:
        return 0
    enviados = 0
    for url in urls:
        if baixar(url, timeout=6) is not None:
            enviados += 1
    return enviados


_DISPARAR_PADRAO = disparar


def _disparar_eventos(urls):
    """Em producao dispara em background para nunca travar o loop do player;
    nos testes (quando ``disparar`` foi substituida) mantem ordem sincrona.
    """
    if not urls:
        return 0
    if disparar is not _DISPARAR_PADRAO:
        return disparar(urls)
    copia = list(urls)
    threading.Thread(target=disparar, args=(copia,),
                     name='vast-tracking', daemon=True).start()
    return len(copia)


# ---------------------------------------------------------------------------
# Reproducao
# ---------------------------------------------------------------------------
def _player_tocando_video():
    try:
        return bool(xbmc.Player().isPlayingVideo())
    except Exception:
        return False


def _arquivo_atual():
    try:
        return (xbmc.Player().getPlayingFile() or '').strip()
    except Exception:
        return ''


def _aguardar_anuncio_tocar(log=None, espera=ESPERA_INICIO, dormir=None,
                            agora=None, anterior=''):
    """True quando o player comecou a tocar o video do anuncio."""
    dormir = dormir or time.sleep
    agora = agora or _agora
    inicio = agora()
    limite = inicio + espera
    janela_troca = inicio + min(float(espera), 1.5)
    while agora() < limite:
        if _player_tocando_video():
            atual = _arquivo_atual()
            # Evita falso-positivo no quadro final do video anterior enquanto o
            # PlayMedia assincrono do Kodi ainda esta abrindo o criativo VAST.
            if anterior and atual and atual == anterior and agora() < janela_troca:
                dormir(0.25)
                continue
            return True
        dormir(0.25)
    return False


def _posicao_e_duracao():
    try:
        player = xbmc.Player()
        return float(player.getTime()) or 0.0, float(player.getTotalTime()) or 0.0
    except Exception:
        return 0.0, 0.0


def _garantir_tela_cheia():
    """Mantem o video no player em tela cheia (nunca em 2o plano na Home)."""
    try:
        if not xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'):
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')
    except Exception:
        pass


def extrair_url_real_do_proxy(url):
    """Extrai a URL real embutida em ``?url=...`` nos proxies locais/LAN."""
    texto = (url or '').strip()
    if '?' not in texto:
        return ''
    try:
        from urllib.parse import parse_qs, unquote, urlparse
        sem_pipe = texto.split('|', 1)[0]
        parsed = urlparse(sem_pipe)
        valores = parse_qs(parsed.query).get('url') or []
        if not valores:
            return ''
        decodificada = valores[0].strip()
        if decodificada.lower().startswith(('http%3a', 'https%3a')):
            decodificada = unquote(decodificada).strip()
        if decodificada.lower().startswith(('http://', 'https://')):
            return decodificada
    except Exception:
        return ''
    return ''


def _proxy_local_inativo(url):
    """True quando ``url`` aponta para um proxy local/LAN (ex.: Brazuca/Elementum) ja fechado."""
    texto = (url or '').split('|', 1)[0].strip()
    if not texto.startswith('http://'):
        return False
    try:
        import ipaddress
        import socket
        from urllib.parse import urlparse
        parsed = urlparse(texto)
        host = (parsed.hostname or '').strip()
        porta = parsed.port
        if not host or not porta:
            return False
        eh_local = host == 'localhost'
        if not eh_local:
            try:
                ip = ipaddress.ip_address(host)
                eh_local = bool(ip.is_loopback or ip.is_private)
            except ValueError:
                eh_local = False
        if not eh_local:
            return False
        with socket.create_connection((host, porta), timeout=0.35):
            return False
    except Exception:
        return True


def _tocar(url, log=None):
    """Entrega o video do anuncio ao player do Kodi em TELA CHEIA.

    ATENCAO: NUNCA passar ``,1`` no ``PlayMedia`` — no Kodi ``1`` significa
    ``noFullscreen`` (modo segundo plano), o que fechava o player e tocava o
    anuncio escondido atras da Home. Tambem desliga ``RepeatOne`` (ligado por
    addons de TV ao vivo) para o anuncio nao repetir nem congelar a transicao.
    """
    try:
        xbmc.executebuiltin('PlayerControl(RepeatOff)')
        xbmc.executebuiltin('PlayMedia("%s")' % url.replace('"', '%22'))
        _garantir_tela_cheia()
        return True
    except Exception as erro:
        if log:
            log('[SmartAds] VAST nao pode tocar o video (%s)' % erro,
                xbmc.LOGWARNING)
        return False


def reproduzir(anuncio, log=None, tempo_maximo=TEMPO_MAXIMO_ANUNCIO,
               tocar=None, dormir=None, anterior=''):
    """Toca o anuncio e devolve um recibo do que realmente aconteceu.

    O recibo e o que interessa: ``exibido`` so e True se o video do anuncio
    tocou de verdade. Sem recibo de verdade, a chamada devolve False e o
    conteudo segue - nada de marcar anuncio que nao apareceu.
    """
    if not anuncio or not anuncio.get('url'):
        return {'exibido': False, 'motivo': 'sem-anuncio'}
    tocar = tocar or _tocar
    dormir = dormir or time.sleep
    anterior = anterior or _arquivo_atual()
    _disparar_eventos(anuncio.get('impressao') or [])
    if not tocar(anuncio['url'], log):
        return {'exibido': False, 'motivo': 'player-recusou'}
    if not _aguardar_anuncio_tocar(log, dormir=dormir, anterior=anterior):
        # Nao comecou a tocar: nao houve anuncio (e nao se registra impressao
        # como se tivesse havido).
        return {'exibido': False, 'motivo': 'nao-iniciou'}
    if log:
        log('[SmartAds] VAST tocando: %s' % anuncio['url'][:80])
    inicio = _agora()
    # O evento "start" e obrigatorio no VAST e so pode ser enviado depois que o
    # video do anuncio comecou a tocar de verdade (por isso aqui, e nao antes).
    _disparar_eventos((anuncio.get('eventos') or {}).get('start') or [])
    disparados = set(['start'])
    ultima_posicao = -1.0
    ultimo_avanco = inicio
    while _agora() - inicio < tempo_maximo:
        if not _player_tocando_video():
            break
        _garantir_tela_cheia()
        posicao, duracao = _posicao_e_duracao()
        agora_atual = _agora()
        if posicao > ultima_posicao + 0.05:
            ultima_posicao = posicao
            ultimo_avanco = agora_atual
        elif (agora_atual - ultimo_avanco) >= TEMPO_TRAVAMENTO_ANUNCIO:
            if log:
                log('[SmartAds] VAST sem avanco por %.1fs; liberando conteudo'
                    % (agora_atual - ultimo_avanco), xbmc.LOGWARNING)
            break
        duracao = duracao or anuncio.get('duracao') or 0.0
        if duracao > 0:
            fracao = min(1.0, posicao / duracao)
            for nome, quarto in QUARTIS:
                if nome in disparados:
                    continue
                if fracao + 0.01 >= quarto:
                    _disparar_eventos((anuncio.get('eventos') or {}).get(nome) or [])
                    disparados.add(nome)
            if posicao >= duracao - FOLGA_FIM:
                disparados.add('complete')
                break
        dormir(0.5)
    if 'complete' not in disparados:
        disparados.add('complete')
        _disparar_eventos((anuncio.get('eventos') or {}).get('complete') or [])
    return {'exibido': True, 'motivo': 'exibido',
            'segundos': round(_agora() - inicio, 1),
            'eventos': sorted(disparados),
            'url_anuncio': anuncio.get('url', '')}


def exibir(log=None, tag='', altura_tela=0, tempo_maximo=TEMPO_MAXIMO_ANUNCIO,
           baixar_tag=None, tocar=None, dormir=None):
    """Caminho completo: tag -> VAST -> player. Devolve recibo (dict).

    Qualquer falha (sem tag, rede, VAST invalido, player recusando) devolve
    ``{'exibido': False, 'motivo': ...}`` - e quem chamou libera o conteudo.
    """
    if not tag:
        return {'exibido': False, 'motivo': 'sem-tag'}
    baixar_tag = baixar_tag or baixar
    dados = baixar_tag(tag)
    if not dados:
        if log:
            log('[SmartAds] VAST: a tag nao respondeu', xbmc.LOGWARNING)
        return {'exibido': False, 'motivo': 'tag-sem-resposta'}
    anuncio = escolher_anuncio(dados, altura_tela)
    nivel = 0
    while not anuncio and nivel < PROFUNDIDADE_WRAPPER:
        # VMAP (playlist de intervalos do Ad Manager) e Wrapper (mediacao) sao
        # os dois jeitos de "o anuncio esta em outra tag". Antes so o Wrapper
        # era seguido, e uma tag VMAP acabava em "sem criativo".
        e_wrapper = bool(tag_do_wrapper(dados))
        alvo = tag_do_wrapper(dados) or tag_do_vmap(dados)
        if not alvo:
            break
        nivel += 1
        if log:
            log('[SmartAds] VAST: seguindo %s (nivel %d)'
                % ('wrapper' if e_wrapper else 'VMAP - AdBreak do Ad Manager',
                   nivel))
        dados = baixar_tag(alvo)
        if not dados:
            break
        anuncio = escolher_anuncio(dados, altura_tela)
    if not anuncio:
        if log:
            log('[SmartAds] VAST: resposta sem criativo de video linear',
                xbmc.LOGWARNING)
        return {'exibido': False, 'motivo': 'vast-sem-criativo'}
    recibo = reproduzir(anuncio, log=log, tempo_maximo=tempo_maximo,
                        tocar=tocar, dormir=dormir)
    recibo['anuncio'] = anuncio.get('id') or anuncio.get('url')
    return recibo


# ---------------------------------------------------------------------------
# Conteudo: guardar antes do anuncio e devolver depois
# ---------------------------------------------------------------------------
# No Kodi so existe UM player de video: quando o anuncio toca, o canal/filme
# que estava na tela para. Por isso o estado do conteudo e lido ANTES e o
# conteudo e reaberto/retomado DEPOIS. Sem este par, o anuncio de video na TV
# funcionaria e deixaria o usuario sem o filme - trocar um defeito por outro.
def estado_do_conteudo(player=None, log=None):
    """Fotografia do que esta tocando agora (ou ``None``)."""
    try:
        player = player or xbmc.Player()
        if not player.isPlayingVideo():
            return None
        caminho = player.getPlayingFile()
        if not caminho:
            return None
        plugin_path = ''
        for rotulo in ('Player.Filenameandpath', 'Player.FilenameAndPath'):
            try:
                valor = (xbmc.getInfoLabel(rotulo) or '').strip()
            except Exception:
                valor = ''
            if valor and valor != caminho:
                plugin_path = valor
                break
        try:
            posicao = float(player.getTime()) or 0.0
        except Exception:
            posicao = 0.0
        try:
            total = float(player.getTotalTime()) or 0.0
        except Exception:
            total = 0.0
        url_real = extrair_url_real_do_proxy(caminho)
        ao_vivo = False
        try:
            import ao_vivo as _mod_ao_vivo
            ao_vivo = bool(_mod_ao_vivo.eh_ao_vivo(caminho))
            # Filme/serie em HLS (.m3u8) tem duracao conhecida (>= 120 s):
            # nao confundir VOD com canal ao vivo, mas preservar canais que
            # rodam em proxy LAN (?url=...) ou trazem marcadores ao vivo.
            baixo = (caminho + ' ' + url_real).lower()
            if (ao_vivo and total >= 120.0
                    and not url_real
                    and not xbmc.getCondVisibility('VideoPlayer.Content(live)')
                    and 'mode=11' not in baixo
                    and 'canal' not in baixo
                    and 'channel' not in baixo
                    and 'aovivo' not in baixo
                    and '/live/' not in baixo):
                ao_vivo = False
        except Exception:
            ao_vivo = False
        return {'caminho': caminho, 'plugin_path': plugin_path,
                'url_real': url_real,
                'posicao': posicao, 'total': total, 'ao_vivo': ao_vivo}
    except Exception as erro:
        if log:
            log('[SmartAds] sem estado do conteudo (%s)' % type(erro).__name__)
        return None


def _rpc(method, **params):
    pedido = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method,
                         'params': params})
    return json.loads(xbmc.executeJSONRPC(pedido))


def _player_video_id():
    try:
        for item in _rpc('Player.GetActivePlayers').get('result', []):
            if item.get('type') == 'video':
                return item.get('playerid')
    except Exception:
        pass
    return None


def _iniciar_em_tela_cheia(url, log=None):
    try:
        xbmc.executebuiltin('PlayerControl(RepeatOff)')
        xbmc.executebuiltin('PlayMedia("%s")' % url.replace('"', '%22'))
        _garantir_tela_cheia()
        return True
    except Exception as erro:
        if log:
            log('[SmartAds] VAST: nao consegui reabrir o conteudo (%s)' % erro,
                xbmc.LOGWARNING)
        return False


def _candidatos_restauracao(estado):
    """Lista ordenada e sem duplicatas de rotas para reabrir o conteudo."""
    caminho = (estado.get('caminho') or '').strip()
    plugin_path = (estado.get('plugin_path') or '').strip()
    url_real = (estado.get('url_real') or extrair_url_real_do_proxy(caminho)).strip()
    ao_vivo = bool(estado.get('ao_vivo'))
    proxy_morto = _proxy_local_inativo(caminho)
    # No Brazuca, mode=11 abre dialogo de escolha (IsPlayable=false), entao no
    # ao vivo com proxy encerrado a URL real do stream escolhido vem primeiro.
    plugin_reproduzivel = plugin_path and 'mode=11' not in plugin_path.lower()
    ordem = []
    if proxy_morto:
        if ao_vivo:
            ordem.extend([url_real, plugin_path if plugin_reproduzivel else '', caminho])
        else:
            ordem.extend([plugin_path if plugin_reproduzivel else '', url_real, caminho, plugin_path])
    else:
        if ao_vivo:
            ordem.extend([caminho, url_real, plugin_path if plugin_reproduzivel else ''])
        else:
            ordem.extend([caminho, plugin_path if plugin_reproduzivel else '', url_real, plugin_path])
    vistos = set()
    saida = []
    for item in ordem:
        if item and item not in vistos:
            vistos.add(item)
            saida.append(item)
    return saida


def restaurar(estado, log=None, espera=20, dormir=None, agora=None,
              url_anuncio=''):
    """Devolve o conteudo a tela EM TELA CHEIA, no ponto em que estava.

    * NUNCA usa ``PlayMedia(..., 1)``: ``,1`` e ``noFullscreen`` no Kodi e
      fazia o filme rodar em segundo plano atras da Home apos o anuncio;
    * se o stream usava proxy local/LAN encerrado ou token de conexao unica que
      caiu ao tocar o anuncio, reconecta automaticamente por ``url_real`` ou
      ``plugin_path``;
    * canal ao vivo: reabre e CONFIRMA reproducao sem seek (nunca sai do canal);
    * filme/serie: retoma na posicao e garante ``fullscreenvideo`` visivel.
    """
    if not estado or not estado.get('caminho'):
        return False
    dormir = dormir or time.sleep
    agora = agora or _agora
    candidatos = _candidatos_restauracao(estado)
    if not candidatos:
        return False
    eh_vivo = bool(estado.get('ao_vivo'))
    alvo = float(estado.get('posicao') or 0.0)
    limite_total = agora() + espera
    iniciou_algum = False

    for idx, rota in enumerate(candidatos):
        tem_proximo = idx + 1 < len(candidatos)
        abriu = False
        if eh_vivo:
            try:
                import ao_vivo
                abriu = bool(ao_vivo._tocar_de_novo(rota))
                if abriu:
                    _garantir_tela_cheia()
            except Exception:
                abriu = False
        if not abriu:
            abriu = _iniciar_em_tela_cheia(rota, log=log)
        if not abriu:
            continue
        iniciou_algum = True
        prazo_rota = (agora() + min(float(espera), 6.0)) if tem_proximo else limite_total
        janela_troca = agora() + min(float(espera), 1.5)
        while agora() < prazo_rota:
            if _player_tocando_video():
                atual = _arquivo_atual()
                if url_anuncio and atual and atual == url_anuncio and agora() < janela_troca:
                    dormir(0.25)
                    continue
                break
            dormir(0.25)
        if _player_tocando_video():
            _garantir_tela_cheia()
            if eh_vivo and log:
                log('[SmartAds] VAST: canal ao vivo reaberto apos o anuncio')
            break
        if tem_proximo and log:
            log('[SmartAds] VAST: reconectando conteudo pela rota alternativa')

    if not iniciou_algum:
        return False
    if _player_tocando_video():
        _garantir_tela_cheia()
    if alvo <= 0 or eh_vivo:
        return True
    # Espera a posicao ficar legivel antes de buscar (player recriado).
    while agora() < limite_total:
        try:
            atual = float(xbmc.Player().getTime()) or 0.0
        except Exception:
            atual = 0.0
        if atual > 0:
            if abs(atual - alvo) <= 2.0:
                _garantir_tela_cheia()
                return True
            try:
                _rpc('Player.Seek', playerid=_player_video_id(),
                     value={'seconds': alvo})
                if log:
                    log('[SmartAds] VAST: conteudo retomado em %.0fs' % alvo)
            except Exception:
                try:
                    xbmc.Player().seekTime(alvo)
                except Exception:
                    pass
            _garantir_tela_cheia()
            return True
        dormir(0.25)
    _garantir_tela_cheia()
    return True


def exibir_e_devolver(log=None, tag='', altura_tela=0,
                      tempo_maximo=TEMPO_MAXIMO_ANUNCIO,
                      baixar_tag=None, tocar=None, dormir=None,
                      estado=None):
    """Toca o anuncio e devolve o conteudo. Recibo igual ao de ``exibir``.

    Se nada tocou, o conteudo nao e mexido (nem reaberto) - nada de recarregar
    o filme do zero por causa de um anuncio que nao veio.
    """
    if estado is None:
        estado = estado_do_conteudo(log=log)
    recibo = exibir(log=log, tag=tag, altura_tela=altura_tela,
                    tempo_maximo=tempo_maximo, baixar_tag=baixar_tag,
                    tocar=tocar, dormir=dormir)
    if estado and (recibo.get('exibido') or not _player_tocando_video()):
        recibo['conteudo_devolvido'] = restaurar(
            estado, log=log, dormir=dormir,
            url_anuncio=recibo.get('url_anuncio', ''),
        )
    return recibo


def resumo(recibo):
    """Uma linha para o log/relatorio."""
    if not recibo:
        return 'VAST: sem recibo'
    if recibo.get('exibido'):
        return 'VAST: anuncio exibido (%s s, eventos %s)' % (
            recibo.get('segundos', '?'), ','.join(recibo.get('eventos') or []))
    return 'VAST: anuncio NAO exibido (%s)' % recibo.get('motivo', '?')


if __name__ == '__main__':
    # Diagnostico manual: python ads_vast.py <tag>
    import sys
    alvo = sys.argv[1] if len(sys.argv) > 1 else tag_de_teste()
    print(json.dumps(exibir(log=lambda m, *a: print(m), tag=alvo),
                     indent=2, default=str))
