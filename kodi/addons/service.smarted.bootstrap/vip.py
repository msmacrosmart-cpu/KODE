# -*- coding: utf-8 -*-
"""Modulo de licenca VIP do SMARTED-TV.

Implementa as rotas que a tela de entrada (script.smartedtv.welcome) chama:
abrir checkout, abrir o Dropbox, compartilhar link, baixar APK, checar
atualizacao e validar codigo de ativacao. Tudo reutiliza o que ja existe no app
(xbmc/xbmcgui) e nao inventa endpoint: checkout aponta para o
pay.cakto.com.br do pacote, o Dropbox e o link verdadeiro gravado no QR Code
qr_apk.png do pacote, e a validacao de codigo usa
/api/public/validar-codigo (rota real do site, campo JSON "code").

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
import re
import threading
import time

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

# O arquivo publicado no Dropbox tem NOME FIXO: quem mantem o app troca o
# conteudo por dentro e o link nunca muda. O nome faz parte do contrato.
APK_NOME = 'SMARTEDTV.apk'

# Link da PASTA onde o APK fica publicado. E este link que amarra o download
# ao NOME do arquivo: o app pede <pasta>/SMARTEDTV.apk, entao basta
# trocar o arquivo por dentro (mesmo nome novo conteudo) e nada mais muda.
# Diferente do /scl/fi/, que fica preso ao ID de UM arquivo.
DROPBOX_PASTA = ('https://www.dropbox.com/scl/fo/5w6yfp0tvee0xro2wh0m3/'
                 'AKikmSEMGOvGv1QTiKCV8CU?rlkey=3b8m9dnw571waz7vs83n0vn17')

# Link do Dropbox (com rlkey; sem ele o link /scl/fi/ nao abre).
# dl=0 mostra a pagina do Dropbox; dl=1 baixa o APK direto.
# ATENCAO: o /scl/fi/ resolve pelo ID do arquivo, nao pelo nome. Se o link for
# criado em outro arquivo, ele continua baixando aquele arquivo, mesmo que o
# texto da URL diga APK_NOME. resolver_apk_publicado() confere o tamanho e,
# na duvida, cai para a release do GitHub.
DROPBOX_URL = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
               'SMARTEDTV.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j'
               '&st=p1m6ebvg&dl=0')
APK = DROPBOX_URL.replace('&dl=0', '&dl=1')
APK_GITHUB = ('https://github.com/msmacrosmart-cpu/KODE/releases/latest/'
              'download/SMARTEDTV-universal.apk')

# Um APK do Kodi com as duas ABIs passa de 240 MB. Abaixo disso o arquivo
# baixado e pagina de erro do Dropbox/HTML com extensao .apk, nao o app.
APK_TAMANHO_MINIMO = 200 * 1024 * 1024

# Manifesto de atualizacao remoto (Dropbox). Substituir pelo URL verdadeiro
# do arquivo JSON de atualizacao quando estiver hospedado no Dropbox.
# Estrutura esperada:
#   {
#     "versionName": "1.0.84",
#     "versionCode": 2103070,
#     "apkUrl": "https://www.dropbox.com/scl/fi/.../SMARTEDTV.apk?dl=1",
#     "sha256": "<hash sha-256 do APK>",
#     "releaseNotes": "Novidades desta versao"
#   }
MANIFEST_URL = None  # configurar com o URL do manifesto JSON no Dropbox

from smarted_release import VERSION_NAME as CURRENT_VERSION_NAME, VERSION_CODE as CURRENT_VERSION_CODE

# Caminho da licenca ativada (gravada por validar() quando OK).
# O Java Licenca/SmartAds le exatamente addon_data/service.smarted.bootstrap/
# vip.json; o antigo userdata/vip.json era ignorado pelo app.
HOME = xbmcvfs.translatePath('special://home')
PERFIL = xbmcvfs.translatePath('special://profile')
ADDON_DATA = os.path.join(PERFIL, 'addon_data', ADDON_ID)
VIP_JSON = os.path.join(ADDON_DATA, 'vip.json')
VIP_JSON_ANTIGO = os.path.join(HOME, 'userdata', 'vip.json')

# Pasta de downloads do app (dentro do userdata do Kodi).
DOWNLOADS_DIR = os.path.join(HOME, 'userdata', 'smartedtv-downloads')
APK_DOWNLOAD_PATH = os.path.join(DOWNLOADS_DIR, 'SMARTEDTV.apk')


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


# --- licenca VIP: validacao real do backend --------------------------------
# Rota confirmada em 2026-11-17 contra o site de producao:
#   POST https://smartedtv-vip.lovable.app/api/public/validar-codigo
#   corpo {"code": "<codigo>"}  (o campo e "code", nao "codigo")
#   200 {"status":"success","active":true} + Set-Cookie smartedtv_device=...
#   403 {"status":"error","active":false,"message":"Codigo invalido..."}
# A rota /public/api/cakto NAO valida codigo: com JSON ela responde 406
# ("Only HTML requests are supported here") e com HTML devolve a SPA. Ela fica
# como segunda tentativa apenas quando a primeira falha por rede/servidor; so
# ativa se o JSON disser active=true. Uma recusa definitiva nunca vai para a
# segunda rota (evita dupla ativacao).
VALIDAR_URL = 'https://smartedtv-vip.lovable.app/api/public/validar-codigo'
VALIDAR_FALLBACK = 'https://smartedtv-vip.lovable.app/public/api/cakto'
TIMEOUT = 10
PRAZO_TOTAL = 18

_ROTA_BOA = os.path.join(ADDON_DATA, 'vip-endpoint-ok.txt')
_COOKIE = os.path.join(ADDON_DATA, 'device-cookie.txt')
_EM_ANDAMENTO = [0.0]   # timestamp da validacao em curso (0 = livre)
_COOKIE_RE = re.compile(r'smartedtv_device=([^;,\s]+)')


def _garantir_pasta():
    try:
        if not os.path.isdir(ADDON_DATA):
            os.makedirs(ADDON_DATA)
        return True
    except Exception:
        return False


def _ler_texto(caminho):
    try:
        with open(caminho, 'r', encoding='utf-8') as handle:
            return handle.read()
    except Exception:
        return ''


def _gravar_json(caminho, dados):
    """Grava JSON de forma atomica; nunca guarda o codigo inteiro."""
    try:
        _garantir_pasta()
        temporario = caminho + '.tmp'
        with open(temporario, 'w', encoding='utf-8') as handle:
            json.dump(dados, handle, ensure_ascii=False, indent=2)
        try:
            os.replace(temporario, caminho)
        except AttributeError:                 # Python 2 (nao usado no Kodi 21)
            os.rename(temporario, caminho)
        try:
            os.chmod(caminho, 0o600)
        except Exception:
            pass
        return True
    except Exception as erro:
        log('nao consegui gravar %s: %s' % (os.path.basename(caminho), erro),
            xbmc.LOGWARNING)
        return False


def _ler_json(caminho):
    texto = _ler_texto(caminho)
    if not texto.strip():
        return {}
    try:
        dados = json.loads(texto)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        return {}


def _hash_codigo(codigo):
    return hashlib.sha256(codigo.encode('utf-8')).hexdigest()[:16]


def _mascarar(codigo):
    if not codigo:
        return '(vazio)'
    if len(codigo) <= 6:
        return codigo[:1] + '***'
    return codigo[:4] + '...' + codigo[-2:]


def normalizar_codigo(codigo):
    """Apara espacos externos e usa MAIUSCULAS (como o app/Java fazem).

    Nao remove hifens e nao corta caracteres: o codigo enviado ao servidor e o
    mesmo que o usuario digitou/colou, apenas sem espacos nas pontas e em
    maiusculas. Assim digitar em caixa baixa (teclado do Kodi) nao invalida um
    codigo que o site entrega em caixa alta.
    """
    if codigo is None:
        return ''
    try:
        return codigo.strip().upper()
    except Exception:
        return str(codigo).strip().upper()


def estado():
    """Conteudo do vip.json (dict vazio quando nao existe ou esta ilegivel)."""
    dados = _ler_json(VIP_JSON)
    if dados:
        return dados
    # compatibilidade com a versao antiga, que gravava em userdata/vip.json
    antigo = _ler_json(VIP_JSON_ANTIGO)
    if not antigo:
        return {}
    codigo = normalizar_codigo(antigo.get('codigo') or '')
    migrado = dict(antigo)
    migrado.pop('codigo', None)
    if codigo:
        migrado['codigo_hash'] = _hash_codigo(codigo)
    _gravar_json(VIP_JSON, migrado)
    return migrado


def dentro_do_prazo(expira):
    """Aceita AAAA-MM-DD (fim do dia UTC) e ISO ...T...Z."""
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
    except Exception:
        log('prazo invalido: %r' % expira, xbmc.LOGWARNING)
        return False
    return time.time() <= limite


def ativa():
    """True somente com licenca gravada e ainda dentro do prazo."""
    dados = estado()
    if not dados.get('ativo'):
        return False
    return dentro_do_prazo(dados.get('expira'))


def em_instantes(segundos):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() + segundos))


def _expira_de(resposta, codigo):
    if isinstance(resposta, dict):
        for chave in ('expiresAt', 'expira', 'expires', 'expires_at',
                      'validade', 'data_expiracao', 'expiration'):
            valor = resposta.get(chave)
            if valor:
                texto = str(valor).strip().replace(' ', 'T')
                if len(texto) == 10:
                    return texto + 'T23:59:59Z'
                if not texto.endswith('Z') and '+' not in texto[10:]:
                    texto += 'Z'
                return texto
        for chave, fator in (('dias', 86400), ('durationDays', 86400),
                             ('minutos', 60), ('durationMinutes', 60)):
            try:
                quantidade = float(resposta.get(chave))
            except (TypeError, ValueError):
                continue
            if quantidade > 0:
                return em_instantes(quantidade * fator)
    # O backend nao devolve prazo na ativacao. O plano e mensal (30 dias); o
    # codigo de teste do painel e TESTE-... e vale 10 minutos.
    if codigo.upper().startswith('TESTE-'):
        return em_instantes(10 * 60)
    return em_instantes(30 * 86400)


def _ler_cookie():
    valor = _ler_texto(_COOKIE).strip()
    return valor if re.match(r'^[0-9a-fA-F-]{8,64}$', valor) else ''


def _gravar_cookie(valor):
    if not valor:
        return
    try:
        _garantir_pasta()
        with open(_COOKIE, 'w', encoding='utf-8') as handle:
            handle.write(valor + '\n')
        try:
            os.chmod(_COOKIE, 0o600)
        except Exception:
            pass
    except Exception:
        pass


def _cookie_da_resposta(headers):
    """Guarda o smartedtv_device que o servidor manda (identidade do aparelho)."""
    valores = []
    try:
        if hasattr(headers, 'get_all'):
            valores = headers.get_all('Set-Cookie') or []
    except Exception:
        valores = []
    if not valores:
        try:
            valores = [headers.get('Set-Cookie') or '']
        except Exception:
            valores = []
    for texto in valores:
        achado = _COOKIE_RE.search(texto or '')
        if achado:
            _gravar_cookie(achado.group(1))
            return achado.group(1)
    return ''


def _post_json(url, corpo, timeout, cookie=''):
    """POST JSON. Devolve (status, headers, texto, tipo_de_erro)."""
    Request, urlopen = _urlopen_request()
    pedido = Request(url, data=json.dumps(corpo).encode('utf-8'), method='POST')
    pedido.add_header('Content-Type', 'application/json; charset=utf-8')
    pedido.add_header('Accept', 'application/json')
    try:
        versao = xbmcaddon.Addon().getAddonInfo('version')
    except Exception:
        versao = '1.0'
    pedido.add_header('User-Agent', 'SMARTEDTV/%s' % versao)
    if cookie:
        pedido.add_header('Cookie', 'smartedtv_device=%s' % cookie)
    try:
        with urlopen(pedido, timeout=timeout) as resposta:
            status = getattr(resposta, 'status', 200) or 200
            return status, getattr(resposta, 'headers', {}), \
                resposta.read(200000).decode('utf-8', 'replace'), None
    except Exception as erro:
        status = getattr(erro, 'code', 0) or 0
        if status:
            try:
                texto = erro.read(200000).decode('utf-8', 'replace')
            except Exception:
                texto = ''
            return status, getattr(erro, 'headers', {}), texto, 'http'
        return 0, {}, '', 'conexao'


def _mensagem_recusa(mensagem, status):
    baixo = (mensagem or '').lower()
    if 'já' in baixo and ('utiliz' in baixo or 'usad' in baixo):
        return 'Este código já foi utilizado.'
    if 'expir' in baixo or 'vencid' in baixo:
        return 'Este código expirou. Solicite um novo código.'
    if 'informe' in baixo and 'código' in baixo:
        return 'Digite o código de ativação.'
    if any(palavra in baixo for palavra in
           ('inválid', 'invalid', 'não encontrado', 'nao encontrado', 'inativa')):
        return 'Este código não é válido. Verifique e tente novamente.'
    if mensagem and len(mensagem) <= 160:
        return mensagem
    if status == 409:
        return 'Este código já foi utilizado.'
    return 'Este código não é válido. Verifique e tente novamente.'


def _classificar(status, texto):
    """(categoria, mensagem, json) — sucesso exige active=true de verdade."""
    dados = None
    if texto and texto.lstrip().startswith(('{', '[')):
        try:
            dados = json.loads(texto)
        except Exception:
            dados = None
    if dados is None:
        if status == 0:
            return ('conexao',
                    'Não foi possível conectar ao servidor. Verifique sua internet.',
                    None)
        return ('comunicacao',
                'Servidor de ativação temporariamente indisponível.', None)
    if isinstance(dados, list):
        dados = dados[0] if dados else {}
    if not isinstance(dados, dict):
        return ('comunicacao',
                'Servidor de ativação temporariamente indisponível.', None)
    ativo = dados.get('active')
    ativo_ok = ativo is True or ativo == 1 or str(ativo).lower() == 'true'
    estado_txt = str(dados.get('status') or dados.get('estado') or '').lower()
    mensagem = str(dados.get('message') or dados.get('mensagem')
                   or dados.get('error') or dados.get('erro') or '').strip()
    if ativo_ok and estado_txt in ('success', 'ok', 'ativo', 'active',
                                   'liberado', ''):
        return ('ok', 'VIP ativado com sucesso!', dados)
    if status in (400, 401, 403, 404, 409, 410, 422) \
            or estado_txt in ('error', 'erro', 'invalid', 'invalido',
                              'expired', 'expirado'):
        return ('recusa', _mensagem_recusa(mensagem, status), dados)
    if status in (406, 429) or status >= 500:
        return ('servidor',
                'Servidor de ativação temporariamente indisponível.', dados)
    if status == 200 and ativo is False:
        return ('recusa', _mensagem_recusa(mensagem, status), dados)
    return ('comunicacao',
            'Servidor de ativação temporariamente indisponível.', dados)


def _gravar_licenca(codigo, expira, rota):
    """Grava vip.json no caminho que o Java (Licenca/SmartAds) le.

    Nao guarda o codigo inteiro: apenas o hash e o prazo, suficientes para o
    app saber que a licenca esta ativa e para conferir o mesmo codigo depois.
    """
    # `expira` fica no formato de DATA (AAAA-MM-DD), que e o que o Java
    # Licenca/SmartAds le; `expira_em` guarda o instante exato para o Python.
    dados = {'ativo': True,
             'codigo_hash': _hash_codigo(codigo),
             'expira': (expira or '')[:10],
             'expira_em': expira,
             'origem': 'site',
             'rota': rota,
             'salvo_em': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    salvou = _gravar_json(VIP_JSON, dados)
    if salvou:
        log('licenca VIP salva (codigo %s, expira %s)' % (_mascarar(codigo), expira))
    return salvou


def lembrar_rota(rota):
    if not rota or not rota.startswith('http'):
        return
    try:
        _garantir_pasta()
        with open(_ROTA_BOA, 'w', encoding='utf-8') as handle:
            handle.write(rota + '\n')
    except Exception:
        pass


def validar(codigo):
    """(ok, mensagem). So ativa com confirmacao real do backend.

    Ordem: rota real do site; se e somente se ela falhar por rede/servidor,
    tenta /public/api/cakto (que nao e API de codigo, mas e a segunda rota
    pedida). Uma recusa definitiva (codigo invalido/expirado) NAO consulta a
    segunda rota e nao ativa nada. HTTP 200 sozinho nunca e sucesso.
    """
    codigo = normalizar_codigo(codigo)
    if not codigo:
        return (False, 'Digite o código de ativação.')
    agora = time.time()
    if _EM_ANDAMENTO[0] and agora - _EM_ANDAMENTO[0] < 25:
        return (False, 'Já existe uma validação em andamento. Aguarde.')
    _EM_ANDAMENTO[0] = agora
    try:
        dados = estado()
        if (dados.get('ativo') and dentro_do_prazo(dados.get('expira'))
                and dados.get('codigo_hash') == _hash_codigo(codigo)):
            return (True, 'VIP já está ativo neste aparelho.')

        inicio = time.time()
        cookie = _ler_cookie()
        tipos = []
        for url, rotulo in ((VALIDAR_URL, 'site'),
                            (VALIDAR_FALLBACK, 'cakto')):
            restante = PRAZO_TOTAL - (time.time() - inicio)
            if restante <= 1:
                break
            timeout = max(3, min(TIMEOUT, restante))
            status, headers, texto, _ = _post_json(
                url, {'code': codigo}, timeout, cookie)
            novo_cookie = _cookie_da_resposta(headers)
            if novo_cookie:
                cookie = novo_cookie
            categoria, mensagem, resposta = _classificar(status, texto)
            tipos.append(categoria)
            log('validacao %s: HTTP %s -> %s' % (rotulo, status, categoria))
            if categoria == 'ok':
                expira = _expira_de(resposta, codigo)
                if not _gravar_licenca(codigo, expira, url):
                    return (False, 'VIP confirmado, mas não consegui salvar a '
                                   'licença neste aparelho. Tente novamente.')
                lembrar_rota(url)
                return (True, 'VIP ativado com sucesso!')
            if categoria == 'recusa':
                # definitivo: nao consulta a segunda rota, nao duplica ativacao
                return (False, mensagem)
            # conexao/servidor/comunicacao: tenta a proxima rota
        if tipos and all(tipo == 'conexao' for tipo in tipos):
            return (False, 'Não foi possível conectar ao servidor. '
                           'Verifique sua internet.')
        return (False, 'Servidor de ativação temporariamente indisponível.')
    finally:
        _EM_ANDAMENTO[0] = 0.0


def desativar():
    for caminho in (VIP_JSON, VIP_JSON_ANTIGO):
        try:
            if os.path.exists(caminho):
                os.remove(caminho)
        except Exception:
            pass


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
    """Abre o download direto do APK no navegador externo do Android.

    Prefere o arquivo de nome fixo do Dropbox e cai para a release do GitHub
    quando o link do Dropbox nao entrega o APK completo (link preso a outro
    arquivo). Nunca abre uma pagina de erro como se fosse o app.
    """
    url, motivo = resolver_apk_publicado()
    if not url:
        log('nenhum APK confiavel para baixar (%s)' % motivo,
            xbmc.LOGWARNING)
        return False
    log('baixando o APK de %s (%s)' % (motivo, url))
    return abrir_url(url, 'download do APK')


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


def _deixar_legivel(caminho):
    """Da leitura do APK ao instalador do Android (outro processo/uid).

    O Kodi grava com 0600; o instalador entao nao consegue abrir o arquivo e o
    Android responde "Aplicativo nao instalado" sem mostrar a barra de
    progresso. 0644 deixa o arquivo legivel por quem recebe o file://.
    """
    try:
        os.chmod(caminho, 0o644)
        return True
    except Exception as erro:
        log('nao consegui ajustar a permissao do APK: %s' % erro,
            xbmc.LOGWARNING)
        return False


def download_update(apk_url):
    """Baixa o APK de atualizacao para a pasta de downloads do Kodi.

    Grava em blocos: o APK tem ~250 MB e ler tudo para a memoria trava em TV
    box/stick (era uma origem de arquivo truncado). Confere o tamanho final
    contra o Content-Length; download incompleto e descartado aqui, antes de
    chegar ao instalador do Android. Devolve o caminho local ou None.
    """
    Request, urlopen = _urlopen_request()
    try:
        if not xbmcvfs.exists(DOWNLOADS_DIR):
            xbmcvfs.mkdir(DOWNLOADS_DIR)
        req = Request(apk_url, headers={'User-Agent': 'SMARTEDTV'})
        resposta = urlopen(req, timeout=60)
        esperado = resposta.headers.get('Content-Length')
        esperado = int(esperado) if esperado else None
        total = 0
        with open(APK_DOWNLOAD_PATH, 'wb') as handle:
            while True:
                bloco = resposta.read(1024 * 1024)
                if not bloco:
                    break
                handle.write(bloco)
                total += len(bloco)
        log('APK baixado em %s (%d bytes%s)' % (
            APK_DOWNLOAD_PATH, total,
            ', esperado %d' % esperado if esperado else ''))
        _deixar_legivel(APK_DOWNLOAD_PATH)
        if total < APK_TAMANHO_MINIMO or (esperado and total != esperado):
            log('download incompleto: %d de %s bytes' % (total, esperado),
                xbmc.LOGWARNING)
            try:
                os.remove(APK_DOWNLOAD_PATH)
            except Exception:
                pass
            return None
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


def _cabecalhos_remotos(url):
    """HEAD na URL e devolve (tamanho, nome do arquivo) do servidor."""
    Request, urlopen = _urlopen_request()
    try:
        requisicao = Request(url, headers={'User-Agent': 'SMARTEDTV'},
                             method='HEAD')
        resposta = urlopen(requisicao, timeout=15)
        tamanho = resposta.headers.get('Content-Length')
        nome = None
        disposicao = resposta.headers.get('Content-Disposition') or ''
        achado = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)",
                           disposicao, re.I)
        if achado:
            from urllib.parse import unquote
            nome = unquote(achado.group(1)).strip()
        return (int(tamanho) if tamanho else None, nome)
    except Exception as erro:
        log('HEAD em %s falhou: %s' % (url, erro), xbmc.LOGWARNING)
        return (None, None)


def _pasta_e_token():
    """Separa o link da pasta em (id, token, rlkey) para consultar/baixar."""
    if not DROPBOX_PASTA:
        return (None, None, None)
    base, _, consulta = DROPBOX_PASTA.partition('?')
    partes = [p for p in base.rstrip('/').split('/') if p]
    # .../scl/fo/<id>/<token>
    try:
        indice = partes.index('fo')
        pasta_id, token = partes[indice + 1], partes[indice + 2]
    except (ValueError, IndexError):
        return (None, None, None)
    achado = re.search(r'(?:^|&)rlkey=([^&]+)', consulta)
    return (pasta_id, token, achado.group(1) if achado else None)


def url_do_apk_por_nome(nome=None):
    """URL direta para baixar <pasta>/<nome>, resolvendo o nome na pasta.

    O Dropbox NAO aceita "pasta/nome" no link (testado: cada arquivo tem o
    proprio token). O que da para fazer sem depender de link criado a mao e
    perguntar ao proprio Dropbox, pela pagina publica da pasta, qual e o token
    do arquivo com o nome combinado. Assim: publicou SMARTEDTV.apk na
    pasta -> o app acha e baixa; trocou o conteudo do mesmo nome -> continua
    achando. Devolve None quando nao acha (aí vale o link fixo/reserva).
    """
    nome = nome or APK_NOME
    pasta_id, token, _ = _pasta_e_token()
    if not (pasta_id and token):
        return None
    Request, urlopen = _urlopen_request()
    pagina = 'https://www.dropbox.com/scl/fo/%s/%s?dl=0' % (pasta_id, token)
    try:
        resposta = urlopen(Request(pagina,
                                   headers={'User-Agent': 'Mozilla/5.0'}),
                           timeout=20)
        html = resposta.read().decode('utf-8', 'replace')
    except Exception as erro:
        log('nao consegui listar a pasta do Dropbox: %s' % erro,
            xbmc.LOGWARNING)
        return None
    # A pagina publica traz o token de cada arquivo junto do nome:
    # /scl/fo/<pasta>/<token-do-arquivo>/<nome>
    padrao = r'/scl/fo/%s/([A-Za-z0-9_-]+)/%s' % (
        re.escape(pasta_id), re.escape(nome))
    achado = re.search(padrao, html)
    if not achado:
        return None
    return ('https://www.dropbox.com/scl/fo/%s/%s/%s?rlkey=%s&dl=1'
            % (pasta_id, achado.group(1), nome,
               _pasta_e_token()[2] or ''))


def _tamanho_remoto(url):
    """Content-Length em bytes (int) ou None. Mantido por compatibilidade."""
    return _cabecalhos_remotos(url)[0]


def resolver_apk_publicado():
    """Escolhe de onde baixar o APK e devolve (url, motivo).

    Ordem das tentativas:

    1. pasta publicada + NOME do arquivo (``url_do_apk_por_nome``). E o que
       amarra o download ao contrato "SMARTEDTV.apk": quem publica
       substitui o arquivo na pasta e nada mais precisa mudar;
    2. o link /scl/fi/ gravado em DROPBOX_URL, quando ele entrega o arquivo
       certo (o /scl/fi/ resolve pelo ID do arquivo criado quando o link
       nasceu, foi assim que um link com o nome certo servia a v22 antiga);
    3. a release do GitHub, como reserva.

    Em todos os casos confere TAMANHO (pagina de erro salva como .apk tem
    poucos KB) e, quando o servidor informa, o NOME do arquivo entregue.
    Nunca devolve URL que baixe outra coisa no lugar do app.
    """
    motivos = []
    candidatos = [(url_do_apk_por_nome(), 'dropbox-nome'),
                  (APK, 'dropbox')]
    for url, origem in candidatos:
        if not url:
            continue
        tamanho, nome = _cabecalhos_remotos(url)
        if tamanho is not None and tamanho < APK_TAMANHO_MINIMO:
            motivos.append('%s: %d bytes, nao e o APK' % (origem, tamanho))
            log(motivos[-1], xbmc.LOGWARNING)
            continue
        if nome and nome.lower() != APK_NOME.lower():
            # Servidor preso a OUTRO arquivo: baixaria a versao errada.
            motivos.append('%s entrega %s, nao %s'
                           % (origem, nome, APK_NOME))
            log(motivos[-1], xbmc.LOGWARNING)
            continue
        log('Dropbox (%s): %s (%s)' % (origem, APK_NOME,
                                       tamanho or 'tamanho desconhecido'))
        return (url, origem)
    if APK_GITHUB:
        tamanho, _ = _cabecalhos_remotos(APK_GITHUB)
        if tamanho is None or tamanho >= APK_TAMANHO_MINIMO:
            log('usando o APK da release no GitHub (%s)' % APK_GITHUB)
            return (APK_GITHUB, 'github')
    motivo = '; '.join(motivos) or 'sem link de APK configurado'
    return (None, motivo)


def versao_do_apk(caminho_apk):
    """Le a versao de dentro do APK baixado, sem SDK e sem parsear AXML.

    O APK carrega `assets/addons/service.smarted.bootstrap/smarted_release.py`
    em texto puro, com VERSION_NAME/VERSION_CODE - o mesmo descritor que gera
    o manifesto. Ler dali e mais confiavel do que decodificar o
    AndroidManifest.xml binario e nao depende de ferramenta externa.

    Devolve (codigo, nome) ou (None, None) quando o arquivo nao for o app -
    nunca inventa uma versao.
    """
    if not xbmcvfs.exists(caminho_apk):
        return (None, None)
    try:
        import zipfile
        with zipfile.ZipFile(caminho_apk) as apk:
            nomes = apk.namelist()
            for nome in nomes:
                if not nome.endswith('/service.smarted.bootstrap/'
                                     'smarted_release.py'):
                    continue
                texto = apk.read(nome).decode('utf-8', 'replace')
                achado_nome = re.search(
                    r'^VERSION_NAME\s*=\s*["\']?([^"\'\s]+)', texto, re.M)
                achado_codigo = re.search(
                    r'^VERSION_CODE\s*=\s*["\']?([0-9]+)', texto, re.M)
                if achado_nome and achado_codigo:
                    return (int(achado_codigo.group(1)),
                            achado_nome.group(1))
        log('o APK nao tem o descritor de versao do SMARTEDTV', xbmc.LOGWARNING)
        return (None, None)
    except Exception as erro:
        log('nao consegui ler a versao do APK baixado: %s' % erro,
            xbmc.LOGWARNING)
        return (None, None)


def _apk_mais_novo_que_o_instalado(caminho_apk):
    """True quando o arquivo pode ser instalado por cima sem downgrade.

    Sem versao legivel nao bloqueia (o instalador do Android decide); com
    versao legivel menor/igual avisa e devolve False, evitando o generico
    "Aplicativo nao instalado" que o usuario nao consegue interpretar.
    """
    codigo, nome = versao_do_apk(caminho_apk)
    if codigo is None:
        log('versao do APK baixado desconhecida; deixando o Android decidir')
        return True
    log('APK baixado: %s (codigo %d); instalado: %s (codigo %d)' % (
        nome, codigo, CURRENT_VERSION_NAME, CURRENT_VERSION_CODE))
    if codigo < CURRENT_VERSION_CODE:
        log('APK baixado e MAIS ANTIGO que o instalado; nao vou instalar',
            xbmc.LOGWARNING)
        return False
    return True


def install_update(caminho_apk):
    """Abre o instalador oficial do Android para o APK.

    Usa StartAndroidActivity com ACTION_VIEW e tipo
    application/vnd.android.package-archive. O usuario confirma a instalacao.
    """
    caminho_apk = str(caminho_apk)
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
        # Sem manifesto o caminho e o mesmo do botao 122: arquivo de nome
        # fixo no Dropbox, com a release do GitHub como reserva.
        log('MANIFEST_URL nao configurado; usando o APK publicado')
        return open_apk_download()
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
    return instalar_apk_baixado(caminho)


def instalar_apk_baixado(caminho):
    """Instala o APK baixado so depois de conferir a versao e o tamanho.

    O Android mostra "Aplicativo nao instalado" tanto para arquivo truncado
    quanto para versao mais antiga que a instalada. Aqui a causa e dita ao
    usuario antes de abrir o instalador, em vez de deixar a mensagem generica.
    """
    tamanho = _tamanho_do_arquivo(caminho)
    if not tamanho or tamanho < APK_TAMANHO_MINIMO:
        log('APK baixado incompleto (%s bytes): nao vou instalar' % tamanho,
            xbmc.LOGWARNING)
        xbmcgui.Dialog().notification(
            'SMARTEDTV',
            'O download veio incompleto. Baixe de novo.',
            xbmcgui.NOTIFICATION_ERROR, 6000)
        return False
    if not _apk_mais_novo_que_o_instalado(caminho):
        xbmcgui.Dialog().notification(
            'SMARTEDTV',
            'O arquivo publicado ainda e a versao %s. Instale quando sair '
            'uma atualizacao mais nova.' % CURRENT_VERSION_NAME,
            xbmcgui.NOTIFICATION_INFO, 6000)
        return False
    return install_update(caminho)


def _tamanho_do_arquivo(caminho):
    """Tamanho local em bytes ou None se o arquivo nao existir."""
    try:
        if not xbmcvfs.exists(caminho):
            return None
        return int(os.path.getsize(caminho))
    except Exception as erro:
        log('nao consegui medir %s: %s' % (caminho, erro), xbmc.LOGWARNING)
        return None