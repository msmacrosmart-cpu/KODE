# -*- coding: utf-8 -*-
"""Modulo de licenca VIP do SMARTED-TV.

Implementa as rotas que a tela de entrada (script.smartedtv.welcome) chama:
abrir checkout, abrir o Dropbox, compartilhar link, baixar APK, checar
atualizacao e validar codigo de ativacao. Tudo reutiliza o que ja existe no app
(xbmc/xbmcgui) e nao inventa endpoint: checkout aponta para o
pay.cakto.com.br do pacote, o Dropbox e o link verdadeiro gravado no QR Code
qr_apk.png do pacote, e a validacao de codigo usa /api/validar e
/functions/v1/validar-codigo (rotas reais do projeto).

Os botoes de checkout, Dropbox, compartilhar, baixar APK e atualizar SAEM do
app (abrem o navegador/intent do Android) em vez de ficar dentro do Kodi.

Assinatura real do builtin no Kodi (confirmada no fonte do Omega,
xbmc/interfaces/builtins/AndroidBuiltins.cpp):

    StartAndroidActivity(package,intent,dataType,dataURI[,flags,extras,...])

O primeiro parametro e o PACOTE Android, nao a action. Package vazio vira
``null`` no intent (jstring NULL em libandroidjni), ou seja, intent implicito:
o Android escolhe o navegador padrao. Era esse o erro que impedia os botoes
120/121 de abrir qualquer coisa.
"""
from __future__ import absolute_import, unicode_literals

import hashlib
import json
import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

try:
    ADDON = xbmcaddon.Addon('service.smarted.bootstrap')
except Exception:
    ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')

# URLs reais do pacote.
CHECKOUT = 'https://pay.cakto.com.br/nkvbegd_1323120'
SITE = 'https://smartedtv-vip.lovable.app/'

# Link verdadeiro do Dropbox: e o mesmo conteudo gravado no QR Code
# qr_apk.png que acompanha a tela (lido do proprio PNG do pacote). Tem o
# rlkey; sem ele o link /scl/fi/ nao abre. dl=0 mostra a pagina do Dropbox
# (com o botao de download); dl=1 baixa o APK direto.
DROPBOX_URL = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
               'SMARTEDTV-atual.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j'
               '&st=p1m6ebvg&dl=0')
APK = DROPBOX_URL.replace('&dl=0', '&dl=1')
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


def _urlopen_request():
    """Request/urlopen do Python da vez (Kodi 21 usa Python 3)."""
    try:
        from urllib.request import Request, urlopen  # Python 3
    except ImportError:                              # pragma: no cover
        from urllib2 import Request, urlopen          # Python 2
    return (Request, urlopen)


def _aspas_builtin(valor):
    """Coloca um parametro entre aspas para o parser de builtins do Kodi.

    O parser (CExecString/SplitParams) separa parametros por virgula e so
    respeita virgula dentro de aspas. Extras de intent sao JSON (tem virgula e
    aspas), entao vao entre aspas com as aspas internas escapadas.
    """
    return '"%s"' % valor.replace('\\', '\\\\').replace('"', '\\"')


def _start_android_activity(intent, data_uri='', data_type='', extras='',
                            package='', flags=''):
    """Dispara um intent do Android (sai do Kodi para outro app).

    Ordem real do Kodi:
    ``StartAndroidActivity(package,intent,dataType,dataURI,flags,extras)``.

    ``package`` fica vazio de proposito: no Android vira ``null`` e o intent
    e implicito (o sistema escolhe o navegador padrao). Passar a action no
    primeiro campo, como fazia a versao anterior, fazia o Kodi procurar um
    pacote chamado ``android.intent.action.VIEW`` e nada abria.
    """
    campos = [package, intent, data_type, data_uri]
    if extras or flags:
        campos.extend([flags, _aspas_builtin(extras) if extras else ''])
    comando = 'StartAndroidActivity(%s)' % ','.join(campos)
    try:
        xbmc.executebuiltin(comando)
        log('intent disparado: %s' % comando)
        return True
    except Exception as erro:
        log('StartAndroidActivity falhou (%s): %s' % (comando, erro),
            xbmc.LOGWARNING)
        return False


def _abrir_navegador(url, rotulo='link'):
    """Abre uma URL no navegador externo do Android (sai do app)."""
    log('abrindo navegador externo %s: %s' % (rotulo, url))
    if _start_android_activity('android.intent.action.VIEW', url):
        return True
    # fallback apenas fora do Android: no Android o PlayMedia abriria o link
    # DENTRO do Kodi, que e justamente o que o usuario nao quer.
    try:
        if not xbmc.getCondVisibility('System.Platform.Android'):
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
    """Compartilha um texto para outro app do Android (ACTION_SEND).

    O tipo do intent so e aplicado pelo Kodi junto com um dataURI, por isso o
    link do APK vai como dado e o texto como EXTRA_TEXT. O menu nativo do
    Android (WhatsApp, Telegram, Gmail) abre por cima do Kodi.
    """
    log('compartilhando: %s' % texto)
    extras = json.dumps([
        {'type': 'string', 'key': 'android.intent.extra.TEXT', 'value': texto},
        {'type': 'string', 'key': 'android.intent.extra.SUBJECT',
         'value': 'SMARTEDTV'},
    ])
    if _start_android_activity('android.intent.action.SEND', APK, 'text/plain',
                               extras):
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
    Request, urlopen = _urlopen_request()

    urls = [
        'https://smartedtv-vip.lovable.app/api/validar',
        'https://smartedtv-vip.lovable.app/functions/v1/validar-codigo',
    ]
    for url in urls:
        try:
            req = Request(url, data=json.dumps({'codigo': codigo}).encode('utf-8'),
                          headers={'Content-Type': 'application/json'})
            resposta = urlopen(req, timeout=10)
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
    """ID 120 - Abre o checkout da Cakto no navegador externo do Android.

    Sai da interface do Kodi: o intent ACTION_VIEW implicito (package vazio)
    entrega a URL ao navegador padrao do aparelho.
    """
    log('abrindo checkout: %s' % CHECKOUT)
    return _start_android_activity('android.intent.action.VIEW', CHECKOUT)


def abrir_dropbox():
    """ID 121 - Abre o link verdadeiro do Dropbox no navegador externo.

    Mostra a pagina do Dropbox (dl=0), de onde o APK pode ser baixado. O
    endereco e o mesmo do QR Code do pacote; nada e inventado aqui.
    """
    log('abrindo Dropbox: %s' % DROPBOX_URL)
    return abrir_url(DROPBOX_URL, 'Dropbox')


def compartilhar(texto=None):
    """Compartilhamento nativo Android (ACTION_SEND).

    Abre o menu nativo de compartilhamento do Android (WhatsApp, Telegram,
    Gmail, etc.) com o link de download do APK do Dropbox. Continua
    disponivel (pressionar e segurar o botao 121 na tela de entrada).
    """
    mensagem = texto or 'Baixe o SMARTEDTV aqui: %s' % APK
    log('compartilhando link de download: %s' % mensagem)
    if _compartilhar_texto(mensagem):
        return True
    # Fallback: abre a pagina do Dropbox no navegador externo
    return abrir_dropbox()


def share_download_link():
    """Compartilha o link de download do APK via ACTION_SEND nativo."""
    return compartilhar()


def open_apk_download():
    """Abre o download direto do APK no navegador externo do Android."""
    return abrir_url(APK, 'download do APK')


def abrir_url(url, rotulo='link'):
    """Abre uma URL no navegador externo do Android."""
    log('abrindo %s: %s' % (rotulo, url))
    return _start_android_activity('android.intent.action.VIEW', url)


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
    Request, urlopen = _urlopen_request()
    try:
        req = Request(MANIFEST_URL, headers={'User-Agent': 'SMARTEDTV'})
        resposta = urlopen(req, timeout=10)
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
    Request, urlopen = _urlopen_request()
    try:
        if not xbmcvfs.exists(DOWNLOADS_DIR):
            xbmcvfs.mkdir(DOWNLOADS_DIR)
        req = Request(apk_url, headers={'User-Agent': 'SMARTEDTV'})
        resposta = urlopen(req, timeout=30)
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
    uri = 'file://' + caminho_apk.replace(' ', '%20')
    if _start_android_activity('android.intent.action.VIEW', uri,
                               'application/vnd.android.package-archive'):
        log('instalador do Android aberto para: %s' % caminho_apk)
        return True
    log('falha ao abrir instalador: %s' % caminho_apk, xbmc.LOGWARNING)
    return False


def procurar_atualizacao():
    """Fluxo completo de atualizacao: consulta manifesto, baixa, verifica e
    oferece instalacao. Se o manifesto nao estiver configurado, abre o link do
    Dropbox no navegador (comportamento anterior)."""
    if not MANIFEST_URL:
        log('MANIFEST_URL nao configurado; abrindo link do Dropbox')
        return abrir_url(DROPBOX_URL, 'atualização')
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
    apk_url = manifesto.get('apkUrl') or APK
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