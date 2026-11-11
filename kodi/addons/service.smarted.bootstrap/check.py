# -*- coding: utf-8 -*-
"""Ponte entre a skin e o bootstrap.

Dois usos:

* ``RunScript(service.smarted.bootstrap,diagnostico)`` — repete o reparo dos
  addons e mostra o relatório (botão "Diagnóstico Brazuca Play" dos Ajustes).
* ``RunScript(service.smarted.bootstrap,secret-*)`` — contadores do unlock
  secreto da skin. ``Skin.SetSetting`` **não** é um builtin do Kodi (o keymapper
  responde "no such action"), então a aritmética é feita aqui e o resultado é
  gravado com o builtin oficial ``Skin.SetString``, que a skin lê de volta com
  ``Skin.String(...)``.
"""
from __future__ import absolute_import, unicode_literals

import sys

import xbmc
import xbmcgui

import service

# valor máximo de cada contador (o unlock usa >= 8 cliques e >= 2 ciclos)
SECRET_LIMITS = {
    'secret_click_count': 8,
    'secret_settings_cycle': 2,
}


def _current(name):
    raw = xbmc.getInfoLabel('Skin.String(%s)' % name) or ''
    try:
        return int(float(raw))
    except ValueError:
        return 0


def _store(name, value):
    xbmc.executebuiltin('Skin.SetString(%s,%d)' % (name, max(0, value)))


def bump_secret(name):
    """Incrementa (com teto) um contador do unlock secreto."""
    limit = SECRET_LIMITS[name]
    value = min(limit, _current(name) + 1)
    _store(name, value)
    return value


def reset_secret(name):
    _store(name, 0)
    return 0


def handle_skin_command(command):
    """Executa um comando vindo da skin. Retorna True se tratou o comando."""
    if command == 'secret-click':
        bump_secret('secret_click_count')
        return True
    if command == 'secret-cycle':
        bump_secret('secret_settings_cycle')
        return True
    if command == 'secret-reset':
        reset_secret('secret_click_count')
        return True
    if command in ('secret-full-reset', 'secret reset all'):
        reset_secret('secret_click_count')
        reset_secret('secret_settings_cycle')
        return True
    return False


def show_report():
    progress = xbmcgui.DialogProgress()
    progress.create('Brazuca Play', 'Verificando addons e dependências...')
    progress.update(30, 'Conferindo addons e dependências...')
    report = service.run_repair(show_dialogs=False)
    progress.update(100, 'Verificação concluída')
    progress.close()
    if report['ok']:
        xbmcgui.Dialog().ok(
            'Brazuca Play',
            'OK: %d addons verificados.\nRestaurados agora: %s' % (
                len(report['required']),
                ', '.join(report['repaired']) or 'nenhum'))
    else:
        xbmcgui.Dialog().ok(
            'Brazuca Play',
            'Pendências: %s\n\nRelatório completo: userdata/smarted-bootstrap.log' % (
                ', '.join(report['missing']) or 'nenhuma'))


if __name__ == '__main__':
    arguments = sys.argv[1:]
    command = arguments[0].strip().lower() if arguments else ''
    if not handle_skin_command(command):
        show_report()
