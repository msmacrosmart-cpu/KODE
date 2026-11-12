# -*- coding: utf-8 -*-
"""Troca o menu generico do Kodi pelo menu SMARTEDTV (categorias do Brazuca Play).

A skin padrao (base Bingie) traz um menu superior estatico gerado a partir das
rotas do Brazuca Play. Como o Kodi guarda os includes da skin em cache e o
script.skinshortcuts mantem dados do menu antigo no perfil, no primeiro boot
depois da atualizacao o menu velho continuaria aparecendo. Esta rotina roda uma
vez por versao: limpa os dados antigos e recarrega a skin.
"""
from __future__ import absolute_import, unicode_literals

import os

import xbmc
import xbmcvfs

MARCADOR = 'menu-smarted-v1.done'


def _perfil(*partes):
    return xbmcvfs.translatePath(
        os.path.join('special://profile/addon_data', *partes))


def limpar_menu_antigo():
    """Apaga os dados do skinshortcuts gravados para a skin padrao."""
    pasta = _perfil('script.skinshortcuts')
    if not xbmcvfs.exists(pasta):
        return []
    removidos = []
    try:
        _, arquivos, _ = xbmcvfs.listdir(pasta)
    except Exception:  # noqa: BLE001 - listdir pode falhar em perfis antigos
        return []
    for nome in arquivos:
        if 'novatv' not in nome.lower():
            continue
        caminho = os.path.join(pasta, nome)
        try:
            xbmcvfs.delete(caminho)
            removidos.append(nome)
        except Exception:  # noqa: BLE001
            pass
    return removidos


def garantir_menu(xbmc_module=xbmc, log=None):
    """Executa a troca uma unica vez e devolve o que foi feito."""
    log = log or (lambda *a, **k: None)
    pasta = _perfil('service.smarted.bootstrap')
    marcador = os.path.join(pasta, MARCADOR)
    if xbmcvfs.exists(marcador):
        return {'applied': False, 'removed': []}
    removidos = limpar_menu_antigo()
    if not xbmcvfs.exists(pasta):
        xbmcvfs.mkdirs(pasta)
    try:
        with xbmcvfs.File(marcador, 'w') as arquivo:
            arquivo.write('ok')
    except Exception as erro:  # noqa: BLE001
        log('menu: marcador nao gravado (%s)' % erro)
    xbmc_module.executebuiltin('ReloadSkin()')
    log('menu SMARTEDTV ativado (dados antigos removidos: %s)'
        % (', '.join(removidos) or 'nenhum'))
    return {'applied': True, 'removed': removidos}
