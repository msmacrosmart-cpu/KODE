# -*- coding: utf-8 -*-
"""Modulo de licenca VIP do SMARTED-TV.

Implementa as rotas que a tela de entrada (script.smartedtv.welcome) chama:
abrir checkout, compartilhar link, baixar APK, checar atualizacao e validar
codigo de ativacao. Tudo reutiliza o que ja existe no app (xbmc/xbmcgui) e nao
inventa endpoint: checkout aponta para o pay.cakto.com.br do pacote, o APK para
o link do Dropbox/GitHub ja constante no VipFake dos testes, e a validacao de
codigo usa /api/validar e /functions/v1/validar-codigo (rotas reais do projeto).
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


def _abrir_url_externa(url, rotulo='link'):
    """Abre uma URL externa no Kodi (tenta PlayMedia; fallback: notificacao)."""
    try:
        xbmc.executebuiltin('PlayMedia(%s)' % url)
        return True
    except Exception as erro:
        log('nao foi possível abrir %s (%s): %s' % (rotulo, url, erro),
            xbmc.LOGWARNING)
    try:
        xbmcgui.Dialog().notification(
            'SMARTEDTV', rotulo, xbmcgui.NOTIFICATION_INFO, 4000)
    except Exception:
        pass
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
    """Abre o checkout de pagamento (pay.cakto.com.br)."""
    log('abrindo checkout: %s' % CHECKOUT)
    return _abrir_url_externa(CHECKOUT, 'checkout')


def compartilhar(texto=None):
    """Compartilha o link do app (mostra o link para copiar/encaminhar)."""
    msg = texto or ('Baixe o SMARTED-TV: %s' % APK)
    log('compartilhando link do app')
    try:
        xbmcgui.Dialog().ok('Compartilhar', msg, 'Copiar')
    except Exception as erro:
        log('nao foi possível abrir o compartilhamento: %s' % erro,
            xbmc.LOGWARNING)
        return False
    return True


def abrir_url(url, rotulo='link'):
    """Abre uma URL (download do APK, site, etc.)."""
    log('abrindo %s: %s' % (rotulo, url))
    return _abrir_url_externa(url, rotulo)


def procurar_atualizacao():
    """Checa se há atualização disponível (abre a release do GitHub)."""
    log('checando atualização')
    return _abrir_url_externa(APK_GITHUB, 'atualização')
