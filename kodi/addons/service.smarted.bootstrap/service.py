# -*- coding: utf-8 -*-
"""Serviço de boot do SMARTED-TV.

Roda no início do Kodi e garante que o Brazuca Play esteja instalado,
habilitado e com o bootstrap interno pronto antes de qualquer tela abrir.
"""
from __future__ import absolute_import, unicode_literals

import os
import time

import xbmc
import xbmcaddon
import xbmcvfs

import repair

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PAYLOAD_DIR = os.path.join(ADDON_PATH, 'payload')

# Instalação do perfil semeado pode levar alguns segundos: tentamos por ~90s.
WAIT_SECONDS = 90
POLL_SECONDS = 5


def log(message, level=xbmc.LOGINFO):
    xbmc.log('[%s] %s' % (ADDON_ID, message), level)


def jsonrpc(method, params=None):
    import json
    request = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params is not None:
        request['params'] = params
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except Exception as error:
        log('JSON-RPC %s falhou: %s' % (method, error), xbmc.LOGWARNING)
        return {}


def addon_manager_ready():
    """O Kodi só responde quando terminou de montar o banco de addons."""
    return 'result' in jsonrpc('Addons.GetAddons', {'enabled': True})


def enable_addons(addon_ids):
    """Habilita os addons no Kodi (idempotente) e devolve os que falharam."""
    failed = []
    jsonrpc('Addons.SetAddonEnabled', {'addonid': 'metadata.local', 'enabled': True})
    xbmc.executebuiltin('UpdateLocalAddons()')
    for addon_id in addon_ids:
        response = jsonrpc('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': True})
        if response.get('error'):
            # já habilitado / sem permissão: só registra, não interrompe o boot
            log('não foi possível habilitar %s: %s' % (addon_id, response['error']),
                xbmc.LOGWARNING)
            failed.append(addon_id)
    return failed


def write_report(home, report):
    path = os.path.join(home, 'userdata', 'smarted-bootstrap.log')
    lines = ['smarted bootstrap %s' % time.strftime('%Y-%m-%d %H:%M:%S'),
             'resultado: %s' % ('ok' if report['ok'] else 'incompleto')]
    lines += ['  ' + entry for entry in report['log']]
    try:
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        with open(path, 'a') as handle:
            handle.write('\n'.join(lines) + '\n\n')
    except Exception as error:
        log('não foi possível gravar o relatório: %s' % error, xbmc.LOGWARNING)


def run_repair(show_dialogs=False):
    home = xbmcvfs.translatePath('special://home')
    report = repair.repair_profile(home, PAYLOAD_DIR)
    for entry in report['log']:
        log(entry)
    write_report(home, report)
    if report['repaired']:
        xbmc.executebuiltin('UpdateLocalAddons()')
    failed = enable_addons(report['required'])
    if show_dialogs:
        dialog = xbmcaddon.Addon().getLocalizedString
        import xbmcgui
        if report['ok'] and not failed:
            xbmcgui.Dialog().ok(
                'Brazuca Play',
                'Addons verificados: %d\nTudo pronto para abrir o Brazuca Play.' %
                len(report['required']))
        else:
            problems = report['missing'] + failed
            xbmcgui.Dialog().ok(
                'Brazuca Play',
                'Não foi possível preparar:\n%s\n\nRelatório: userdata/smarted-bootstrap.log' %
                '\n'.join(problems[:8]))
    return report


def main():
    monitor = xbmc.Monitor()
    log('startup: verificando perfil')
    waited = 0
    while waited < WAIT_SECONDS and not monitor.abortRequested():
        if addon_manager_ready():
            break
        if monitor.waitForAbort(POLL_SECONDS):
            return
        waited += POLL_SECONDS
    report = run_repair(show_dialogs=False)
    if not report['ok']:
        log('perfil incompleto: %s' % ', '.join(report['missing']), xbmc.LOGWARNING)
        if not monitor.abortRequested():
            xbmc.executebuiltin(
                'Notification(SMARTED-TV, '
                'Brazuca Play incompleto: veja userdata/smarted-bootstrap.log, 8000)')
    while not monitor.abortRequested():
        if monitor.waitForAbort(3600):
            return


if __name__ == '__main__':
    main()
