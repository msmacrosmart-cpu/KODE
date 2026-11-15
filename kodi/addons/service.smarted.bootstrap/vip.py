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
# Endpoint que recebe {"codigo": "...", "device": "...", "app": "smartedtv"}
# e responde JSON. Confirmar o caminho exato no projeto do site.
VALIDAR = 'https://smartedtv-vip.lovable.app/api/validar'
TIMEOUT = 12

# --- ponte Android (abrir link / compartilhar) ------------------------------
PACOTE = 'smartedtv.full'
CLASSE_ABRIR = 'smartedtv.full.AbrirUrlActivity'
CLASSE_COMPARTILHAR = 'smartedtv.full.CompartilharActivity'
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
    expira = (dados.get('expira') or '').strip()
    if not expira:
        return True
    try:
        limite = time.strptime(expira, '%Y-%m-%d')
    except ValueError:
        return False
    return time.time() <= time.mktime(limite) + 86399


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


def _post(url, corpo):
    """POST JSON → dict. Levanta exceção em erro de rede/HTTP."""
    import urllib.error
    import urllib.request

    dados = json.dumps(corpo).encode('utf-8')
    pedido = urllib.request.Request(url, data=dados, method='POST')
    pedido.add_header('Content-Type', 'application/json; charset=utf-8')
    pedido.add_header('Accept', 'application/json')
    pedido.add_header('User-Agent', 'SMARTEDTV/%s' % xbmcaddon.Addon().getAddonInfo('version'))
    with urllib.request.urlopen(pedido, timeout=TIMEOUT) as resposta:
        texto = resposta.read().decode('utf-8', 'replace')
    try:
        return json.loads(texto)
    except ValueError:
        return {'bruto': texto}


def _ler_resposta(resposta):
    """Aceita as formas comuns de resposta do servidor do site."""
    if not isinstance(resposta, dict):
        return False, '', 'resposta inesperada'
    ok = bool(resposta.get('ativo') or resposta.get('valido')
              or resposta.get('ok') or resposta.get('success'))
    if resposta.get('error') or resposta.get('erro'):
        return False, '', str(resposta.get('error') or resposta.get('erro'))
    expira = resposta.get('expira') or resposta.get('expires') or resposta.get('validade') or ''
    mensagem = resposta.get('mensagem') or resposta.get('message') or ''
    return ok, str(expira), mensagem


def validar(codigo):
    """(ok, mensagem). Valida o código no site e grava a licença se der certo."""
    codigo = (codigo or '').strip().upper()
    if not codigo:
        return False, 'Digite o código.'
    corpo = {'codigo': codigo, 'app': 'smartedtv',
             'device': _aparelho(), 'versao': xbmcaddon.Addon().getAddonInfo('version')}
    try:
        resposta = _post(VALIDAR, corpo)
    except Exception as erro:  # noqa: BLE001 - rede, 404, timeout...
        _log('falha ao validar no site: %s' % erro, xbmc.LOGWARNING)
        return False, 'Sem conexão com o servidor de ativação.'
    ok, expira, mensagem = _ler_resposta(resposta)
    if not ok:
        return False, mensagem or 'Código não reconhecido.'
    if not salvar(codigo, expira, extra={'resposta': resposta}):
        return False, 'Licença validada, mas não consegui gravar no aparelho.'
    return True, mensagem or ('VIP ativo até %s' % expira if expira else 'VIP ativado!')


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
