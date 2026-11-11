# -*- coding: utf-8 -*-
"""Verificação manual do bootstrap (botão "Diagnóstico" da skin).

Executa o mesmo reparo do serviço, mostra o resultado e oferece o relatório.
"""
from __future__ import absolute_import, unicode_literals

import xbmcgui

import service


if __name__ == '__main__':
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
