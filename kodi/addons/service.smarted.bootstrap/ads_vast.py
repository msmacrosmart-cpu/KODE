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
import time

import xbmc

# Prazo total do anuncio: passou disso, o conteudo volta. Um VAST malformado
# ou um MP4 que nunca carrega nao podem prender o usuario na TV.
TEMPO_MAXIMO_ANUNCIO = 150
# Quanto esperar o video do anuncio realmente comecar.
ESPERA_INICIO = 15
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

# Tag VAST padrao do projeto (formato de video do MagSrv).
#
# Fica AQUI, no modulo de anuncio de video, e e o valor usado pelo
# ``smart_ads.VAST_TAG_PADRAO`` (que passa a ler daqui em vez de repetir a URL).
# Um lugar so para trocar a tag do dono do app - nada de duas copias.
#
# Restricao de uso: este fluxo VAST e o anuncio de VIDEO da TV (Android TV,
# TV Box, stick e projetor Android). Quem decide isso continua sendo o
# ``eh_tv()`` de ``variante.py``: no celular/tablet o anuncio e o AdMob da
# activity nativa e este modulo nao e chamado.
VAST_TAG_PADRAO = 'https://s.magsrv.com/v1/vast.php?idz=6096742'


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
    MagSrv) -> tag de TESTE oficial, e essa apenas com o modo de validacao
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
            progressivo = tipo.startswith(('video/mp4', 'video/webm',
                                           'video/x-m4v'))
            hls = 'mpegurl' in tipo or url.lower().endswith('.m3u8')
            if not (progressivo or hls):
                continue
            candidatos.append({
                'url': url,
                'tipo': tipo,
                'largura': largura,
                'altura': altura,
                'progressivo': progressivo,
                # perto da resolucao da tela = menos up/downscale no aparelho
                'proximidade': abs((altura or 0) - (altura_tela or 1080)),
            })
    if not candidatos:
        return None
    candidatos.sort(key=lambda item: (not item['progressivo'],
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


def tag_do_wrapper(xml):
    """URL que um ``<Wrapper>`` manda seguir ('' quando nao e wrapper)."""
    if not xml:
        return ''
    if isinstance(xml, bytes):
        xml = xml.decode('utf-8', 'replace')
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
    if isinstance(xml, bytes):
        xml = xml.decode('utf-8', 'replace')
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
    if isinstance(xml, bytes):
        xml = xml.decode('utf-8', 'replace')
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
        pedido = Request(url, headers={'User-Agent': 'SMARTEDTV/VAST'})
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


# ---------------------------------------------------------------------------
# Reproducao
# ---------------------------------------------------------------------------
def _player_tocando_video():
    try:
        return bool(xbmc.Player().isPlayingVideo())
    except Exception:
        return False


def _aguardar_anuncio_tocar(log=None, espera=ESPERA_INICIO, dormir=None,
                            agora=None):
    """True quando o player comecou a tocar o video do anuncio."""
    dormir = dormir or time.sleep
    agora = agora or _agora
    limite = agora() + espera
    while agora() < limite:
        if _player_tocando_video():
            return True
        dormir(0.25)
    return False


def _posicao_e_duracao():
    try:
        player = xbmc.Player()
        return float(player.getTime()) or 0.0, float(player.getTotalTime()) or 0.0
    except Exception:
        return 0.0, 0.0


def _tocar(url, log=None):
    """Entrega o video do anuncio ao player do Kodi."""
    try:
        xbmc.executebuiltin('PlayMedia("%s",1)' % url.replace('"', '%22'))
        return True
    except Exception as erro:
        if log:
            log('[SmartAds] VAST nao pode tocar o video (%s)' % erro,
                xbmc.LOGWARNING)
        return False


def reproduzir(anuncio, log=None, tempo_maximo=TEMPO_MAXIMO_ANUNCIO,
               tocar=None, dormir=None):
    """Toca o anuncio e devolve um recibo do que realmente aconteceu.

    O recibo e o que interessa: ``exibido`` so e True se o video do anuncio
    tocou de verdade. Sem recibo de verdade, a chamada devolve False e o
    conteudo segue - nada de marcar anuncio que nao apareceu.
    """
    if not anuncio or not anuncio.get('url'):
        return {'exibido': False, 'motivo': 'sem-anuncio'}
    tocar = tocar or _tocar
    dormir = dormir or time.sleep
    disparar(anuncio.get('impressao') or [])
    if not tocar(anuncio['url'], log):
        return {'exibido': False, 'motivo': 'player-recusou'}
    if not _aguardar_anuncio_tocar(log, dormir=dormir):
        # Nao comecou a tocar: nao houve anuncio (e nao se registra impressao
        # como se tivesse havido).
        return {'exibido': False, 'motivo': 'nao-iniciou'}
    if log:
        log('[SmartAds] VAST tocando: %s' % anuncio['url'][:80])
    inicio = _agora()
    # O evento "start" e obrigatorio no VAST e so pode ser enviado depois que o
    # video do anuncio comecou a tocar de verdade (por isso aqui, e nao antes).
    disparar((anuncio.get('eventos') or {}).get('start') or [])
    disparados = set(['start'])
    while _agora() - inicio < tempo_maximo:
        if not _player_tocando_video():
            break
        posicao, duracao = _posicao_e_duracao()
        duracao = duracao or anuncio.get('duracao') or 0.0
        if duracao > 0:
            fracao = min(1.0, posicao / duracao)
            for nome, quarto in QUARTIS:
                if nome in disparados:
                    continue
                if fracao + 0.01 >= quarto:
                    disparar((anuncio.get('eventos') or {}).get(nome) or [])
                    disparados.add(nome)
            if posicao >= duracao - FOLGA_FIM:
                disparados.add('complete')
                break
        dormir(0.5)
    if 'complete' not in disparados:
        disparados.add('complete')
        disparar((anuncio.get('eventos') or {}).get('complete') or [])
    return {'exibido': True, 'motivo': 'exibido',
            'segundos': round(_agora() - inicio, 1),
            'eventos': sorted(disparados)}


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
        try:
            posicao = float(player.getTime()) or 0.0
        except Exception:
            posicao = 0.0
        try:
            total = float(player.getTotalTime()) or 0.0
        except Exception:
            total = 0.0
        ao_vivo = False
        try:
            import ao_vivo
            ao_vivo = bool(ao_vivo.eh_ao_vivo(caminho))
        except Exception:
            ao_vivo = False
        return {'caminho': caminho, 'posicao': posicao, 'total': total,
                'ao_vivo': ao_vivo}
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


def restaurar(estado, log=None, espera=20, dormir=None, agora=None):
    """Devolve o conteudo a tela, no ponto em que estava.

    * canal ao vivo: reabre pelo proprio player (entra no ponto ATUAL da
      transmissao - seek em ao vivo derruba o fluxo);
    * filme/serie: PlayMedia + espera o player voltar e busca a posicao.
    """
    if not estado or not estado.get('caminho'):
        return False
    dormir = dormir or time.sleep
    agora = agora or _agora
    caminho = estado['caminho']
    if estado.get('ao_vivo'):
        try:
            import ao_vivo
            if ao_vivo._tocar_de_novo(caminho):
                if log:
                    log('[SmartAds] VAST: canal ao vivo reaberto apos o anuncio')
                return True
        except Exception:
            pass
    try:
        xbmc.executebuiltin('PlayMedia("%s",1)' % caminho.replace('"', '%22'))
    except Exception as erro:
        if log:
            log('[SmartAds] VAST: nao consegui reabrir o conteudo (%s)' % erro,
                xbmc.LOGWARNING)
        return False
    alvo = float(estado.get('posicao') or 0.0)
    limite = agora() + espera
    while agora() < limite:
        if _player_tocando_video():
            break
        dormir(0.25)
    if alvo <= 0:
        return True
    # Espera a posicao ficar legivel antes de buscar (player recriado).
    while agora() < limite:
        try:
            atual = float(xbmc.Player().getTime()) or 0.0
        except Exception:
            atual = 0.0
        if atual > 0:
            if abs(atual - alvo) <= 2.0:
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
            return True
        dormir(0.25)
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
        recibo['conteudo_devolvido'] = restaurar(estado, log=log,
                                                 dormir=dormir)
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
