# -*- coding: utf-8 -*-
"""Licença VIP (assistir sem anúncios) — ativação por código do site.

Fluxo:

    site (Lovable)  --pagamento Cakto-->  código  -->  app  -->  vip.json
                                                                   |
                                          SmartAds/Licenca (Java) lê aqui

* O código é validado no servidor do site; o app NUNCA decide sozinho que um
  código é válido.
* O resultado bom vira `vip.json` dentro do próprio perfil do Kodi:
  `<perfil>/.kodi/userdata/addon_data/service.smarted.bootstrap/vip.json`
  com `{"ativo": true, "codigo": "...", "expira": "AAAA-MM-DD"}`.
* O Java (`smartedtv.full.Licenca`) lê esse arquivo antes de cada anúncio:
  com VIP ativo, nenhuma tela de anúncio abre.
* Sem rede, sem servidor ou com código inválido, o app segue com anúncios —
  falha sempre para o lado seguro (nunca "ganha" VIP por engano).

Endereços de produção ficam nas constantes abaixo; o checkout é o mesmo link
usado no site.
"""
from __future__ import absolute_import, unicode_literals

import json
import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

ADDON_ID = 'service.smarted.bootstrap'
ARQUIVO = 'vip.json'

# --- produção ---------------------------------------------------------------
CHECKOUT = 'https://pay.cakto.com.br/nkvbegd_1323120'
SITE = 'https://smartedtv-vip.lovable.app/'
SITE_ATIVAR = 'https://smartedtv-vip.lovable.app/#ativar'
# Rota que recebe {"codigo": "...", "device": "...", "app": "smartedtv"} e
# responde JSON. O site é uma SPA: caminho desconhecido devolve HTML de 404, não
# JSON — por isso testamos as candidatas em ordem e paramos na primeira que
# responder JSON. Um arquivo `vip-endpoint.txt` (pasta do app ou addon_data)
# com uma URL tem prioridade, sem precisar recompilar.
VALIDAR = 'https://smartedtv-vip.lovable.app/api/validar'
VALIDAR_URIS = (
    VALIDAR,
    'https://smartedtv-vip.lovable.app/api/validate',
    'https://smartedtv-vip.lovable.app/api/ativar',
    'https://smartedtv-vip.lovable.app/api/codigos/validar',
    'https://smartedtv-vip.lovable.app/functions/v1/validar-codigo',
)
TIMEOUT = 12
# Rota que já respondeu JSON de verdade. O app (Java) e o add-on gravam o
# mesmo arquivo, então a próxima ativação começa por ela — ativação instantânea
# e sem depender da descoberta do backend.
ROTA_BOA = 'vip-endpoint-ok.txt'

# --- ponte Android (abrir link / compartilhar) ------------------------------
PACOTE = 'smartedtv.full'
CLASSE_ABRIR = 'smartedtv.full.AbrirUrlActivity'
CLASSE_COMPARTILHAR = 'smartedtv.full.CompartilharActivity'
CLASSE_ATUALIZAR = 'smartedtv.full.AtualizaActivity'
ACAO_ATUALIZAR = 'smartedtv.ATUALIZAR'
ACAO_ABRIR = 'smartedtv.ABRIR'
ACAO_COMPARTILHAR = 'smartedtv.COMPARTILHAR'


def _log(mensagem, nivel=None):
    xbmc.log('[smarted-vip] %s' % mensagem, nivel or xbmc.LOGINFO)


def perfil():
    return xbmcvfs.translatePath('special://profile')


def pasta():
    destino = os.path.join(perfil(), 'addon_data', ADDON_ID)
    if not xbmcvfs.exists(destino):
        try:
            xbmcvfs.mkdirs(destino)
        except Exception:  # noqa: BLE001 - perfil somente leitura
            pass
    return destino


def caminho():
    return os.path.join(pasta(), ARQUIVO)


def estado():
    """Conteúdo do vip.json (dict vazio quando não existe ou está ilegível)."""
    arquivo = caminho()
    if not xbmcvfs.exists(arquivo):
        return {}
    try:
        with open(arquivo, 'r', encoding='utf-8') as handle:
            dados = json.load(handle)
        return dados if isinstance(dados, dict) else {}
    except Exception as erro:  # noqa: BLE001
        _log('vip.json ilegivel: %s' % erro, xbmc.LOGWARNING)
        return {}


def ativa():
    dados = estado()
    if not dados.get('ativo'):
        return False
    return dentro_do_prazo(dados.get('expira'))


def dentro_do_prazo(expira):
    """Aceita ``AAAA-MM-DD`` (fim do dia UTC) e ISO ``…T…Z`` (código de teste)."""
    expira = (expira or '').strip()
    if not expira:
        return True
    import calendar
    try:
        if len(expira) == 10:
            limite = calendar.timegm(time.strptime(expira, '%Y-%m-%d')) + 86399
        else:
            texto = expira.replace(' ', 'T').rstrip('Z')
            if '.' in texto:
                texto = texto.split('.', 1)[0]
            limite = calendar.timegm(time.strptime(texto, '%Y-%m-%dT%H:%M:%S'))
    except Exception:  # noqa: BLE001
        _log('prazo invalido: %r' % expira, xbmc.LOGWARNING)
        return False
    return time.time() <= limite


def salvar(codigo, expira='', origem='cakto', extra=None):
    dados = {'ativo': True, 'codigo': codigo, 'expira': expira,
             'origem': origem, 'salvo_em': time.strftime('%Y-%m-%d %H:%M:%S')}
    if extra:
        dados.update(extra)
    try:
        with open(caminho(), 'w', encoding='utf-8') as handle:
            json.dump(dados, handle, ensure_ascii=False, indent=2)
        _log('licenca salva (expira %r)' % expira)
        return True
    except Exception as erro:  # noqa: BLE001
        _log('nao consegui salvar a licenca: %s' % erro, xbmc.LOGERROR)
        return False


def desativar():
    try:
        if xbmcvfs.exists(caminho()):
            xbmcvfs.delete(caminho())
        return True
    except Exception:  # noqa: BLE001
        return False


def _post(url, corpo, chave=''):
    """POST JSON → dict. Levanta exceção em erro de rede/HTTP."""
    import urllib.error
    import urllib.request

    dados = json.dumps(corpo).encode('utf-8')
    pedido = urllib.request.Request(url, data=dados, method='POST')
    pedido.add_header('Content-Type', 'application/json; charset=utf-8')
    pedido.add_header('Accept', 'application/json')
    pedido.add_header('User-Agent', 'SMARTEDTV/%s' % xbmcaddon.Addon().getAddonInfo('version'))
    if chave:
        # Edge Functions e PostgREST do Supabase pedem a chave anon nos dois
        pedido.add_header('apikey', chave)
        pedido.add_header('Authorization', 'Bearer ' + chave)
    with urllib.request.urlopen(pedido, timeout=TIMEOUT) as resposta:
        texto = resposta.read().decode('utf-8', 'replace')
    try:
        return json.loads(texto)
    except ValueError:
        return {'bruto': texto}


def _get(url, chave=''):
    """GET JSON (tabela do Supabase). Devolve dict/lista ou {'bruto': texto}."""
    import urllib.request

    pedido = urllib.request.Request(url, method='GET')
    pedido.add_header('Accept', 'application/json')
    pedido.add_header('User-Agent', 'SMARTEDTV/%s' % xbmcaddon.Addon().getAddonInfo('version'))
    if chave:
        pedido.add_header('apikey', chave)
        pedido.add_header('Authorization', 'Bearer ' + chave)
    with urllib.request.urlopen(pedido, timeout=TIMEOUT) as resposta:
        texto = resposta.read().decode('utf-8', 'replace')
    try:
        return json.loads(texto)
    except ValueError:
        return {'bruto': texto}


SUPABASE_FUNCOES = ('/functions/v1/validar-codigo', '/functions/v1/validar',
                    '/functions/v1/ativar-codigo', '/functions/v1/ativa-codigo')
SITE = SITE if 'SITE' in globals() else 'https://smartedtv-vip.lovable.app/'


def _arquivo_texto(caminho):
    try:
        if not os.path.isfile(caminho):
            return ''
        with open(caminho, 'r', encoding='utf-8') as handle:
            return handle.read()
    except Exception:  # noqa: BLE001
        return ''


def supabase():
    """(url, chave) do projeto Supabase do site — override, cache ou descoberta."""
    for base in (pasta(), perfil()):
        texto = _arquivo_texto(os.path.join(base, 'supabase.txt'))
        par = _par_supabase(texto)
        if par:
            _log('supabase (configuracao): %s' % par[0])
            return par
    url = _arquivo_texto(os.path.join(pasta(), 'supabase-url.txt')).strip()
    if url.startswith('http'):
        chave = _arquivo_texto(os.path.join(pasta(), 'supabase-chave.txt')).strip()
        _log('supabase (manual): %s' % url)
        return (url.rstrip('/'), chave)
    par = _par_supabase(_arquivo_texto(os.path.join(pasta(), 'supabase-cache.txt')))
    if par:
        return par
    par = _descobrir_supabase()
    if par:
        try:
            with open(os.path.join(pasta(), 'supabase-cache.txt'), 'w', encoding='utf-8') as handle:
                handle.write('%s\n%s\n' % par)
        except Exception:  # noqa: BLE001
            pass
    return par


def _par_supabase(texto):
    url, chave = None, ''
    for linha in (texto or '').splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if linha.startswith('http') and 'supabase.co' in linha:
            url = linha.rstrip('/')
        elif linha.startswith('eyJ'):
            chave = linha
    return (url, chave) if url else None


def _descobrir_supabase():
    """Lê o bundle do site e acha ``https://<projeto>.supabase.co`` + chave anon."""
    import re
    import urllib.request

    def baixar(endereco):
        pedido = urllib.request.Request(endereco, method='GET')
        pedido.add_header('User-Agent', 'SMARTEDTV/1.0')
        with urllib.request.urlopen(pedido, timeout=TIMEOUT) as resposta:
            return resposta.read(4 * 1024 * 1024).decode('utf-8', 'replace')

    try:
        html = baixar(SITE)
    except Exception as erro:  # noqa: BLE001
        _log('supabase: site fora do ar (%s)' % erro, xbmc.LOGWARNING)
        return None
    projeto = re.compile(r'(https://[a-z0-9]{6,}\.supabase\.co)')
    chave_re = re.compile(r'(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})')
    projetos = projeto.findall(html)
    chave = (chave_re.findall(html) or [''])[0]
    for src in re.findall(r'src="([^"]+\.js[^"]*)"', html)[:6]:
        if projetos and chave:
            break
        endereco = src if src.startswith('http') else SITE + src.lstrip('/')
        try:
            texto = baixar(endereco)
        except Exception:  # noqa: BLE001
            continue
        projetos += projeto.findall(texto)
        if not chave:
            achadas = chave_re.findall(texto)
            chave = achadas[0] if achadas else ''
    if not projetos:
        _log('supabase: nada encontrado no JavaScript do site', xbmc.LOGWARNING)
        return None
    par = (projetos[0].rstrip('/'), chave)
    _log('supabase (descoberto): %s (chave %s)' % (par[0], 'ok' if chave else 'ausente'))
    return par


def rotas_supabase():
    """Rotas do Supabase (Edge Functions) para o código."""
    par = supabase()
    if not par:
        return [], ''
    base, chave = par
    return [base + funcao for funcao in SUPABASE_FUNCOES], chave


def _ler_resposta(resposta):
    """Aceita as formas comuns de resposta do site, da Edge Function e da tabela."""
    tabela = False
    if isinstance(resposta, list):
        tabela = True
        resposta = resposta[0] if resposta else {}
    if not isinstance(resposta, dict):
        return False, '', 'resposta inesperada'
    ok = bool(resposta.get('ativo') or resposta.get('valido')
              or resposta.get('valid') or resposta.get('ok')
              or resposta.get('success') or resposta.get('liberado'))
    if not ok and str(resposta.get('status') or '').lower() in ('ativo', 'valido', 'liberado', 'ok'):
        ok = True
    if not ok and tabela and resposta:
        # linha do painel: existe o código e ele (ainda) não foi usado
        if resposta.get('usado') in (False, 0, 'false', 'False', None) \
                or resposta.get('ativo') in (True, 'true', 'True'):
            ok = True
    if resposta.get('error') or resposta.get('erro'):
        return False, '', str(resposta.get('error') or resposta.get('erro'))
    mensagem = resposta.get('mensagem') or resposta.get('message') or ''
    if not ok:
        return False, '', mensagem
    return True, expira_de(resposta), mensagem


def expira_de(resposta):
    """Prazo: data/hora explícita, minutos (teste, 10) ou dias (mensal, 30)."""
    for chave in ('expira', 'expira_em', 'expires', 'expires_at', 'validade',
                  'data_expiracao', 'expiration'):
        valor = resposta.get(chave)
        if valor:
            texto = str(valor).strip().replace(' ', 'T')
            if len(texto) == 10:
                return texto + 'T23:59:59Z'
            if not texto.endswith('Z') and '+' not in texto[10:]:
                texto += 'Z'
            return texto
    for chave in ('minutos', 'duracao_minutos', 'validade_minutos', 'duration_minutes'):
        try:
            minutos = int(float(resposta.get(chave)))
        except (TypeError, ValueError):
            continue
        if minutos > 0:
            return em_instantes(minutos * 60)
    for chave in ('dias', 'duracao_dias', 'validade_dias', 'duration_days'):
        try:
            dias = int(float(resposta.get(chave)))
        except (TypeError, ValueError):
            continue
        if dias > 0:
            return em_instantes(dias * 86400)
    tipo = ' '.join(str(resposta.get(c) or '') for c in ('tipo', 'type', 'plano')).lower()
    if any(palavra in tipo for palavra in ('teste', 'trial', 'demo', '10')):
        return em_instantes(600)            # código de teste: 10 minutos
    return em_instantes(30 * 86400)         # código mensal: 30 dias


def em_instantes(segundos):
    """Data/hora UTC no formato do vip.json (…T…Z)."""
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() + segundos))


def _rota_lembrada():
    """Última rota que funcionou (gravada pelo app ou por este add-on)."""
    for candidato in (os.path.join(pasta(), ROTA_BOA),
                      os.path.join(perfil(), ROTA_BOA)):
        try:
            if os.path.isfile(candidato):
                with open(candidato, 'r', encoding='utf-8') as handle:
                    texto = handle.read().strip().splitlines()
                if texto and texto[0].strip().startswith('http'):
                    return texto[0].strip()
        except Exception:  # noqa: BLE001
            continue
    return ''


def lembrar_rota(rota):
    """Grava a rota que deu certo (o app Java lê o mesmo nome de arquivo)."""
    if not rota or not rota.startswith('http'):
        return
    for destino in (os.path.join(pasta(), ROTA_BOA),):
        try:
            with open(destino, 'w', encoding='utf-8') as handle:
                handle.write(rota + '\n')
            _log('rota memorizada: %s' % rota)
        except Exception as erro:  # noqa: BLE001
            _log('nao consegui memorizar a rota: %s' % erro, xbmc.LOGDEBUG)


def rotas():
    """Candidatas de rota: lembrada, override do aparelho e as de produção."""
    lista = []
    lembrada = _rota_lembrada()
    if lembrada:
        lista.append(lembrada)
    for candidato in (os.path.join(pasta(), 'vip-endpoint.txt'),
                      os.path.join(perfil(), 'vip-endpoint.txt')):
        try:
            if os.path.isfile(candidato):
                with open(candidato, 'r', encoding='utf-8') as handle:
                    texto = handle.read().strip()
                if texto.startswith('http'):
                    lista.append(texto)
                    _log('rota de override: %s' % texto)
                    break
        except Exception:  # noqa: BLE001
            continue
    for rota in VALIDAR_URIS:
        if rota not in lista:
            lista.append(rota)
    return lista


def validar(codigo):
    """(ok, mensagem). Valida o código (site ou Supabase) e grava a licença."""
    codigo = (codigo or '').strip().upper()
    if not codigo:
        return False, 'Digite o código.'
    corpo = {'codigo': codigo, 'app': 'smartedtv',
             'device': _aparelho(), 'versao': xbmcaddon.Addon().getAddonInfo('version')}

    def concluir(resposta, origem):
        ok, expira, mensagem = _ler_resposta(resposta)
        if not ok:
            return False, mensagem or 'Código não reconhecido.'
        if not salvar(codigo, expira, origem='app' if 'supabase' in origem else 'site',
                      extra={'resposta': resposta, 'rota': origem}):
            return False, 'Licença validada, mas não consegui gravar no aparelho.'
        lembrar_rota(origem)
        _log('licenca ativa por %s ate %s' % (origem, expira))
        return True, mensagem or ('VIP ativo até %s' % expira if expira else 'VIP ativado!')

    # 1º: rotas do próprio site (mais rápido quando existirem)
    achou = False
    recusa = ''
    for rota in rotas():
        try:
            bruta = _post(rota, corpo)
        except Exception as erro:  # noqa: BLE001 - rede, 404, timeout...
            _log('rota %s falhou: %s' % (rota, erro), xbmc.LOGDEBUG)
            continue
        if isinstance(bruta, dict) and 'bruto' in bruta:
            continue                       # HTML da SPA, não é API
        achou = True
        ok, _, mensagem = _ler_resposta(bruta)
        if ok:
            return concluir(bruta, rota)
        recusa = recusa or mensagem

    # 2º: Supabase do site (Edge Functions, depois a tabela do painel)
    try:
        funcoes, chave = rotas_supabase()
    except Exception as erro:  # noqa: BLE001
        _log('supabase indisponivel: %s' % erro, xbmc.LOGDEBUG)
        funcoes, chave = [], ''
    for rota in funcoes:
        try:
            bruta = _post(rota, corpo, chave)
        except Exception as erro:  # noqa: BLE001
            _log('supabase %s falhou: %s' % (rota, erro), xbmc.LOGDEBUG)
            continue
        if isinstance(bruta, dict) and 'bruto' in bruta:
            continue
        achou = True
        ok, _, mensagem = _ler_resposta(bruta)
        if ok:
            return concluir(bruta, rota)
        recusa = recusa or mensagem
    if funcoes:
        base = funcoes[0].split('/functions/v1/')[0]
        try:
            import urllib.parse
            tabela = '%s/rest/v1/codigos?codigo=eq.%s&select=*' % (
                base, urllib.parse.quote(codigo))
            bruta = _get(tabela, chave)
            if not (isinstance(bruta, dict) and 'bruto' in bruta):
                achou = True
                ok, _, mensagem = _ler_resposta(bruta)
                if ok:
                    return concluir(bruta, tabela)
                recusa = recusa or mensagem
        except Exception as erro:  # noqa: BLE001
            _log('tabela do supabase falhou: %s' % erro, xbmc.LOGDEBUG)

    if not achou:
        return False, 'Não consegui falar com o servidor de ativação. Tente de novo.'
    return False, recusa or 'Código não reconhecido.'


def _aparelho():
    """Identificação estável e sem dado sensível do aparelho."""
    import hashlib

    base = '%s|%s|%s' % (
        xbmc.getInfoLabel('System.FriendlyName') or 'smartedtv',
        xbmc.getInfoLabel('System.BuildVersion') or '',
        xbmc.getInfoLabel('Network.MacAddress') or '',
    )
    return hashlib.sha256(base.encode('utf-8')).hexdigest()[:16]


# --------------------------------------------------------------------- pontes
def _builtin(pacote, acao, classe, url):
    return ('StartAndroidActivity(%s,%s,,%s,,,,,,%s)' % (pacote, acao, url, classe))


def abrir_url(url, rotulo='link'):
    """Abre um link no navegador do aparelho (Android)."""
    if xbmc.getCondVisibility('System.Platform.Android'):
        alvo = url
        xbmc.executebuiltin(_builtin(PACOTE, ACAO_ABRIR, CLASSE_ABRIR, alvo))
        _log('abrindo %s: %s' % (rotulo, url))
        return True
    _log('plataforma sem ponte para abrir %s' % rotulo, xbmc.LOGWARNING)
    return False


def abrir_checkout():
    """Leva o usuário ao checkout da Cakto (versão VIP, R$ 24,90)."""
    return abrir_url(CHECKOUT, 'checkout Cakto')


def abrir_site(pagina=SITE_ATIVAR):
    return abrir_url(pagina, 'site')


def procurar_atualizacao():
    """Abre a checagem de versão do app (OTA) pela ponte dos anúncios."""
    if not xbmc.getCondVisibility('System.Platform.Android'):
        _log('atualizacao: so disponivel no app Android')
        return False
    xbmc.executebuiltin(
        _builtin(PACOTE, ACAO_ATUALIZAR, CLASSE_ATUALIZAR, 'smartedtv://atualizar'))
    _log('checagem de atualizacao aberta')
    return True


def compartilhar(texto=None):
    """Abre a folha de compartilhamento do Android com o convite do app."""
    convite = texto or (
        'Estou usando o SMARTEDTV (TV, filmes e séries) e recomendo: %s' % SITE)
    if xbmc.getCondVisibility('System.Platform.Android'):
        xbmc.executebuiltin(
            _builtin(PACOTE, ACAO_COMPARTILHAR, CLASSE_COMPARTILHAR,
                     'smartedtv://compartilhar'))
        _log('folha de compartilhamento aberta')
        return True
    # fora do Android: copia o texto e avisa
    try:
        xbmc.executebuiltin('Notification(SMARTEDTV, %s, 8000)' % convite)
    except Exception:  # noqa: BLE001
        pass
    return False
