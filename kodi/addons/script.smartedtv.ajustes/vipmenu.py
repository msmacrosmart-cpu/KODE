# -*- coding: utf-8 -*-
"""Menu VIP como fonte de plugin: ``plugin://script.smartedtv.ajustes/``.

A barra da Home abre uma URL de plugin (`ActivateWindow(Videos,$INFO[…]`), e o
atalho permanente precisa de um endereço que exista **no APK**. O
`plugin.video.smarted` que vai para o APK é o do APK estável do usuário
(`inject-base-estavel.py` troca essa pasta inteira), então as rotas novas não
chegariam lá; este add-on de ajustes é copiado do repositório e por isso é quem
hospeda o menu.

Rotas:

    plugin://script.smartedtv.ajustes/                 -> menu
    plugin://script.smartedtv.ajustes/?acao=comprar    -> checkout Cakto
    plugin://script.smartedtv.ajustes/?acao=codigo     -> menu de ajustes (código)
    plugin://script.smartedtv.ajustes/?acao=compartilhar
    plugin://script.smartedtv.ajustes/?acao=qrcode     -> QR do site
    plugin://script.smartedtv.ajustes/?acao=continuar  -> retoma o último ponto

Nada aqui depende do plugin de conteúdo: só chama o serviço (vip/retomar) ou um
builtin do Kodi.
"""
from __future__ import absolute_import, unicode_literals

import os
import sys
from urllib.parse import parse_qs

import xbmc
import xbmcgui
import xbmcplugin

BASE = 'plugin://script.smartedtv.ajustes/'
SITE = 'https://smartedtv-vip.lovable.app/'


def _servico():
    """Põe o add-on do serviço no sys.path (vip.py, retomar.py)."""
    try:
        import xbmcvfs
        pasta = os.path.join(xbmcvfs.translatePath('special://home'), 'addons',
                             'service.smarted.bootstrap')
        if pasta not in sys.path:
            sys.path.append(pasta)
    except Exception:  # noqa: BLE001
        pass


def _modulos():
    _servico()
    try:
        import vip
    except Exception:  # noqa: BLE001
        vip = None
    try:
        import retomar
    except Exception:  # noqa: BLE001
        retomar = None
    return vip, retomar


def acoes(vip, retomar):
    lista = [
        ('Assistir sem anúncios (VIP)', 'comprar',
         'Plano de R$ 24,90/mês, pagamento pela Cakto'),
        ('Já tenho um código', 'codigo',
         'Insira o código de ativação e desligue os anúncios'),
        ('Compartilhar aplicativo', 'compartilhar',
         'Envie o convite pelo WhatsApp, Telegram ou e-mail'),
        ('Mostrar QR Code', 'qrcode',
         'Aponte a câmera do celular para baixar o app'),
        ('Procurar atualização', 'atualizar',
         'Verifica se existe uma versão nova do aplicativo'),
    ]
    if retomar is not None:
        ponto = retomar.ultimo()
        if ponto:
            lista.insert(0, ('Continuar assistindo: %s' % ponto['titulo'], 'continuar',
                             'Volta do ponto onde você parou'))
    if vip is not None:
        try:
            if vip.ativa():
                lista[0] = ('VIP ativo — renovar ou ver opções', 'comprar',
                            'Seu plano está ativo: nenhum anúncio')
        except Exception:  # noqa: BLE001
            pass
    return lista


def menu(handle):
    vip, retomar = _modulos()
    xbmcplugin.setContent(handle, 'files')
    for rotulo, acao, descricao in acoes(vip, retomar):
        item = xbmcgui.ListItem(label=rotulo, label2=descricao)
        item.setInfo('video', {'title': rotulo, 'plot': descricao})
        xbmcplugin.addDirectoryItem(handle, BASE + '?acao=' + acao, item, isFolder=False)
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


def mostrar_qr():
    qr = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'qrcode.png')
    if os.path.isfile(qr):
        xbmc.executebuiltin('ShowPicture(%s)' % qr)
        return True
    xbmcgui.Dialog().ok('SMARTEDTV', 'QR Code indisponível neste aparelho.',
                        'Baixe o app em ' + SITE)
    return False


def executar(acao):
    vip, retomar = _modulos()
    if acao == 'comprar':
        if vip is not None:
            vip.abrir_checkout()
        else:
            xbmcgui.Dialog().ok('SMARTEDTV VIP', 'Checkout: pay.cakto.com.br/nkvbegd_1323120')
    elif acao == 'codigo':
        xbmc.executebuiltin('RunAddon(script.smartedtv.ajustes)')
    elif acao == 'compartilhar':
        if vip is not None:
            vip.compartilhar()
    elif acao == 'qrcode':
        mostrar_qr()
    elif acao == 'atualizar':
        if vip is not None:
            vip.procurar_atualizacao()
        else:
            xbmcgui.Dialog().ok('SMARTEDTV', 'Atualização indisponível neste aparelho.')
    elif acao == 'continuar':
        if retomar is None or not retomar.continuar():
            xbmcgui.Dialog().ok('SMARTEDTV', 'Nenhum ponto salvo para retomar.')


def main():
    handle = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else -1
    params = parse_qs(sys.argv[2].lstrip('?'), keep_blank_values=True) if len(sys.argv) > 2 else {}
    acao = params.get('acao', [''])[0]
    if acao:
        executar(acao)
        if handle >= 0:
            xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)
        return
    if handle >= 0:
        menu(handle)


if __name__ == '__main__':
    main()
