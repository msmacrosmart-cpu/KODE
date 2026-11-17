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

# Caminho da licenca ativada (gravada por validar() quando OK).
HOME = xbmcvfs.translatePath('special://home')
VIP_JSON = os.path.join(HOME, 'userdata', 'vip.json')


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
    """ID 121 - Abre o link de download do APK do Dropbox no navegador externo do Android (sai do app)."""
    url_download = APK + '?dl=1'
    log('abrindo download do APK: %s' % url_download)
    try:
        xbmc.executebuiltin(
            'StartAndroidActivity(android.intent.action.VIEW,%s,,)' % url_download)
        return True
    except Exception as erro:
        log('StartAndroidActivity download falhou: %s' % erro, xbmc.LOGWARNING)
    return False


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


def procurar_atualizacao():
    """Checa se há atualização disponível (abre a release do GitHub no navegador externo)."""
    log('checando atualização')
    return abrir_url(APK_GITHUB, 'atualização')
