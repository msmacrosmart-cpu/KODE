# -*- coding: utf-8 -*-
"""Modulo de licenca VIP do SMARTED-TV.

Implementa as rotas que a tela de entrada (script.smartedtv.welcome) chama:
abrir checkout, compartilhar link, baixar APK, checar atualizacao e validar
codigo de ativacao. Tudo reutiliza o que ja existe no app (xbmc/xbmcgui) e nao
inventa endpoint: checkout aponta para o pay.cakto.com.br do pacote, o APK para
o link do Dropbox/GitHub ja constante no VipFake dos testes, e a validacao de
codigo usa /api/validar e /functions/v1/validar-codigo (rotas reais do projeto).

Os botoes de checkout, compartilhar, baixar APK e atualizar SAEM do app
(abrem o navegador/intent do Android) em vez de ficar dentro do Kodi.
"""
from __future__ import absolute_import, unicode_literals

import hashlib
import json
import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

# URLs reais do pacote (mesmas do VipFake nos testes).
CHECKOUT = 'https://pay.cakto.com.br/nkvbegd_1323120'
SITE = 'https://smartedtv-vip.lovable.app/'
APK = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
       'SMARTEDTV-atual.apk')
APK_GITHUB = ('https://github.com/msmacrosmart-cpu/KODE/releases/latest/'
              'download/SMARTEDTV-atual.apk')

# Manifesto de atualizacao remoto (Dropbox). Substituir pelo URL verdadeiro
# do arquivo JSON de atualizacao quando estiver hospedado no Dropbox.
# Estrutura esperada:
#   {
#     "versionName": "1.0.84",
#     "versionCode": 84,
#     "apkUrl": "https://www.dropbox.com/scl/fi/.../SMARTEDTV-atual.apk?dl=1",
#     "sha256": "<hash sha-256 do APK>",
#     "releaseNotes": "Novidades desta versao"
#   }
MANIFEST_URL = None  # configurar com o URL do manifesto JSON no Dropbox

# Versao atual do app (deve bater com o applicationId/versionCode do APK).
# Atualizar quando publicar uma nova versao.
CURRENT_VERSION_NAME = '1.0.83'
CURRENT_VERSION_CODE = 83

# Caminho da licenca ativada (gravada por validar() quando OK).
HOME = xbmcvfs.translatePath('special://home')
VIP_JSON = os.path.join(HOME, 'userdata', 'vip.json')

# Pasta de downloads do app (dentro do userdata do Kodi).
DOWNLOADS_DIR = os.path.join(HOME, 'userdata', 'smartedtv-downloads')
APK_DOWNLOAD_PATH = os.path.join(DOWNLOADS_DIR, 'SMARTEDTV-atual.apk')


def log(mensagem, nivel=xbmc.LOGINFO):
    xbmc.log('[%s] %s' % (ADDON_ID, mensagem), nivel)


def _start_android_activity(action, uri='', mime_type='', extras=''):
    """Dispara um intent do Android (sai do Kodi para outro app).

    Sintaxe do Kodi: StartAndroidActivity(action,uri,mime_type,extras)
    """
    comando = 'StartAndroidActivity(%s,%s,%s,%s)' % (
        action, uri, mime_type, extras)
    try:
        xbmc.executebuiltin(comando)
        return True
    except Exception as erro:
        log('StartAndroidActivity falhou (%s): %s' % (comando, erro),
            xbmc.LOGWARNING)
        return False


def _abrir_navegador(url, rotulo='link'):
    """Abre uma URL no navegador externo do Android (sai do app)."""
    log('abrindo navegador externo %s: %s' % (rotulo, url))
    if _start_android_activity('android.intent.action.VIEW', url, '', ''):
        return True
    # fallback para nao-Android: abre dentro do Kodi
    try:
        xbmc.executebuiltin('PlayMedia(%s)' % url)
        return True
    except Exception as erro:
        log('nao foi possivel abrir %s (%s): %s' % (rotulo, url, erro),
            xbmc.LOGWARNING)
    try:
        xbmcgui.Dialog().notification(
            'SMARTEDTV', rotulo, xbmcgui.NOTIFICATION_INFO, 4000)
    except Exception:
        pass
    return False


def _compartilhar_texto(texto, rotulo='compartilhamento'):
    """Compartilha um texto para outro app do Android (sai do app)."""
    log('compartilhando: %s' % texto)
    if _start_android_activity('android.intent.action.SEND', '',
                               'text/plain', texto):
        return True
    # fallback: mostra o texto num dialog para copiar
    try:
        xbmcgui.Dialog().ok(rotulo, texto, 'Copiar')
        return True
    except Exception as erro:
        log('nao foi possivel abrir o compartilhamento: %s' % erro,
            xbmc.LOGWARNING)
    return False


def ativa():
    """Devolve True quando ja existe uma licenca VIP valida em vip.json."""
    try:
        if not xbmcvfs.exists(VIP_JSON):
            return False
        with xbmcvfs.File(VIP_JSON, 'r') as handle:
            dados = json.loads(handle.read())
        return bool(dados.get('ativo'))
    except Exception as erro:
        log('nao foi possivel ler vip.json: %s' % erro, xbmc.LOGWARNING)
        return False


def validar(codigo):
    """Valida o codigo de ativacao com o servidor.

    Tenta as rotas reais do projeto (/api/validar e
    /functions/v1/validar-codigo). Em caso de sucesso, grava vip.json com
    {ativo, codigo, expira} e devolve (True, mensagem). Em falha, devolve
    (False, mensagem).
    """
    import urllib2  # Python 2 (Kodi 21 Omega usa Python 2.7 no Android)

    urls = [
        'https://smartedtv-vip.lovable.app/api/validar',
        'https://smartedtv-vip.lovable.app/functions/v1/validar-codigo',
    ]
    for url in urls:
        try:
            req = urllib2.Request(url, data=json.dumps({'codigo': codigo}),
                                  headers={'Content-Type': 'application/json'})
            resposta = urllib2.urlopen(req, timeout=10)
            corpo = json.loads(resposta.read().decode('utf-8'))
            if corpo.get('ativo') or corpo.get('sucesso') or corpo.get('ok'):
                _gravar_licenca(codigo, corpo.get('expira'))
                log('codigo validado: %s' % codigo)
                return (True, corpo.get('mensagem') or 'Acesso VIP liberado.')
            return (False, corpo.get('mensagem') or
                    'O serviço não aceitou este código.')
        except Exception as erro:
            log('validar(%s) falhou em %s: %s' % (codigo, url, erro),
                xbmc.LOGWARNING)
            continue
    return (False, 'Não foi possível conectar ao servidor de ativação.')


def _gravar_licenca(codigo, expira=None):
    """Grava vip.json com a licenca ativada."""
    try:
        dados = {'ativo': True, 'codigo': codigo}
        if expira:
            dados['expira'] = expira
        pasta = os.path.dirname(VIP_JSON)
        if not xbmcvfs.exists(pasta):
            xbmcvfs.mkdir(pasta)
        with xbmcvfs.File(VIP_JSON, 'w') as handle:
            handle.write(json.dumps(dados))
    except Exception as erro:
        log('nao foi possivel gravar vip.json: %s' % erro, xbmc.LOGWARNING)


def abrir_checkout():
    """ID 120 - Abre o checkout da Cakto no navegador externo do Android (sai do app)."""
    log('abrindo checkout: %s' % CHECKOUT)
    try:
        xbmc.executebuiltin(
            'StartAndroidActivity(android.intent.action.VIEW,%s,,)' % CHECKOUT)
        return True
    except Exception as erro:
        log('StartAndroidActivity checkout falhou: %s' % erro, xbmc.LOGWARNING)
    return False


def compartilhar(texto=None):
    """ID 121 - Compartilhamento nativo Android (ACTION_SEND).

    Abre o menu nativo de compartilhamento do Android (WhatsApp, Telegram,
    Gmail, etc.) com o link de download do APK do Dropbox.
    """
    url_download = APK + '?dl=1'
    mensagem = 'Baixe o SMARTEDTV aqui: %s' % url_download
    log('compartilhando link de download: %s' % url_download)
    try:
        xbmc.executebuiltin(
            'StartAndroidActivity(android.intent.action.SEND,,text/plain,%s)'
            % mensagem)
        return True
    except Exception as erro:
        log('StartAndroidActivity SEND falhou: %s' % erro, xbmc.LOGWARNING)
    # Fallback: abre o link no navegador externo
    return abrir_url(url_download, 'download do APK')


def share_download_link():
    """Compartilha o link de download do APK via ACTION_SEND nativo."""
    return compartilhar()


def open_apk_download():
    """Abre o download do APK no navegador externo do Android."""
    return abrir_url(APK + '?dl=1', 'download do APK')


def abrir_url(url, rotulo='link'):
    """Abre uma URL no navegador externo do Android."""
    log('abrindo %s: %s' % (rotulo, url))
    try:
        xbmc.executebuiltin(
            'StartAndroidActivity(android.intent.action.VIEW,%s,,)' % url)
        return True
    except Exception as erro:
        log('StartAndroidActivity abrir_url falhou: %s' % erro, xbmc.LOGWARNING)
    return False


def check_for_updates():
    """Consulta o manifesto remoto e devolve (tem_atualizacao, info_dict).

    Se MANIFEST_URL nao estiver configurado, devolve (False, None) e loga um
    aviso. O manifesto deve conter: versionName, versionCode, apkUrl, sha256,
    releaseNotes.
    """
    if not MANIFEST_URL:
        log('MANIFEST_URL nao configurado; pule a verificacao de atualizacao',
            xbmc.LOGWARNING)
        return (False, None)
    import urllib2
    try:
        req = urllib2.Request(MANIFEST_URL, headers={'User-Agent': 'SMARTEDTV'})
        resposta = urllib2.urlopen(req, timeout=10)
        manifesto = json.loads(resposta.read().decode('utf-8'))
        version_code = int(manifesto.get('versionCode', 0))
        if version_code > CURRENT_VERSION_CODE:
            log('nova versao disponivel: %s (code %d)' % (
                manifesto.get('versionName'), version_code))
            return (True, manifesto)
        log('ja esta na versao mais recente (code %d)' % CURRENT_VERSION_CODE)
        return (False, manifesto)
    except Exception as erro:
        log('falha ao consultar manifesto de atualizacao: %s' % erro,
            xbmc.LOGWARNING)
        return (False, None)


def download_update(apk_url):
    """Baixa o APK de atualizacao para a pasta de downloads do Kodi.

    Devolve o caminho local do arquivo ou None em caso de falha.
    """
    import urllib2
    try:
        if not xbmcvfs.exists(DOWNLOADS_DIR):
            xbmcvfs.mkdir(DOWNLOADS_DIR)
        req = urllib2.Request(apk_url, headers={'User-Agent': 'SMARTEDTV'})
        resposta = urllib2.urlopen(req, timeout=30)
        dados = resposta.read()
        with xbmcvfs.File(APK_DOWNLOAD_PATH, 'w') as handle:
            handle.write(dados)
        log('APK baixado em %s (%d bytes)' % (APK_DOWNLOAD_PATH, len(dados)))
        return APK_DOWNLOAD_PATH
    except Exception as erro:
        log('falha ao baixar atualizacao: %s' % erro, xbmc.LOGWARNING)
        return None


def verify_apk(caminho_apk, sha256_esperado):
    """Verifica a integridade do APK pelo SHA-256.

    Devolve True se o hash bater, False caso contrario.
    """
    if not xbmcvfs.exists(caminho_apk):
        log('arquivo nao encontrado: %s' % caminho_apk, xbmc.LOGWARNING)
        return False
    try:
        h = hashlib.sha256()
        with xbmcvfs.File(caminho_apk, 'r') as handle:
            while True:
                bloco = handle.read(65536)
                if not bloco:
                    break
                h.update(bloco)
        sha256_obtido = h.hexdigest()
        if sha256_obtido.lower() == sha256_esperado.lower():
            log('SHA-256 conferido: %s' % sha256_obtido)
            return True
        log('SHA-256 divergente: obtido %s, esperado %s' % (
            sha256_obtido, sha256_esperado), xbmc.LOGWARNING)
        return False
    except Exception as erro:
        log('falha ao verificar SHA-256: %s' % erro, xbmc.LOGWARNING)
        return False


def install_update(caminho_apk):
    """Abre o instalador oficial do Android para o APK.

    Usa StartAndroidActivity com ACTION_VIEW e tipo
    application/vnd.android.package-archive. O usuario confirma a instalacao.
    """
    if not xbmcvfs.exists(caminho_apk):
        log('arquivo nao encontrado para instalacao: %s' % caminho_apk,
            xbmc.LOGWARNING)
        return False
    comando = ('StartAndroidActivity(android.intent.action.VIEW,%s,'
               'application/vnd.android.package-archive,)' % caminho_apk)
    try:
        xbmc.executebuiltin(comando)
        log('instalador do Android aberto para: %s' % caminho_apk)
        return True
    except Exception as erro:
        log('falha ao abrir instalador: %s' % erro, xbmc.LOGWARNING)
        return False


def procurar_atualizacao():
    """Fluxo completo de atualizacao: consulta manifesto, baixa, verifica e
    oferece instalacao. Se o manifesto nao estiver configurado, abre o link do
    Dropbox no navegador (comportamento anterior)."""
    if not MANIFEST_URL:
        log('MANIFEST_URL nao configurado; abrindo link do Dropbox')
        return abrir_url(APK + '?dl=1', 'atualização')
    tem, manifesto = check_for_updates()
    if not tem:
        xbmcgui.Dialog().notification(
            'SMARTEDTV',
            'Voce ja esta na versao mais recente.',
            xbmcgui.NOTIFICATION_INFO, 4000)
        return False
    version_name = manifesto.get('versionName', '?')
    version_code = manifesto.get('versionCode', '?')
    release_notes = manifesto.get('releaseNotes', '')
    msg = 'Nova versao disponível: %s (code %s)\n%s' % (
        version_name, version_code, release_notes)
    if not xbmcgui.Dialog().yesno('Atualizacao disponível', msg,
                                  'Baixar agora', 'Depois'):
        return False
    apk_url = manifesto.get('apkUrl') or APK + '?dl=1'
    caminho = download_update(apk_url)
    if not caminho:
        xbmcgui.Dialog().notification(
            'SMARTEDTV', 'Falha ao baixar a atualizacao.',
            xbmcgui.NOTIFICATION_ERROR, 4000)
        return False
    sha256_esperado = manifesto.get('sha256')
    if sha256_esperado and not verify_apk(caminho, sha256_esperado):
        xbmcgui.Dialog().notification(
            'SMARTEDTV', 'Falha na verificacao de integridade.',
            xbmcgui.NOTIFICATION_ERROR, 4000)
        return False
    return install_update(caminho)