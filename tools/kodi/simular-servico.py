# -*- coding: utf-8 -*-
"""Simula o boot do service.smarted.bootstrap com xbmc/xbmcgui falsos.

Para que serve: o defeito que mais quebrou o app no aparelho foi um modulo do
addon que NAO existia dentro do APK (``FileNotFoundError`` no import, servico
inteiro morto, notificacao de erro no projetor). Testar "o arquivo esta na
lista" ja existe; aqui a prova e mais forte: IMPORTAR o service.py de verdade,
na ordem do Kodi, com todos os modulos vizinhos disponiveis, e ver se ele
carrega sem excecao. E o mesmo caminho do aparelho, sem aparelho.

Uso:  python3 tools/kodi/simular-servico.py
      python3 tools/kodi/simular-servico.py --addon-dir pasta   (simular APK)
"""
from __future__ import print_function

import argparse
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADDON_PADRAO = os.path.join(RAIZ, 'kodi', 'addons',
                            'service.smarted.bootstrap')


def aviso(t):
    print('::notice::' + ' '.join(str(t).split())[:900])


def _stubs(pasta, erros):
    """xbmc/xbmcgui/xbmcvfs mininos, registrando o que o servico chamar."""
    chamadas = []

    xbmc = types.ModuleType('xbmc')
    xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR, xbmc.LOGDEBUG = 1, 3, 4, 0
    xbmc.LOGFATAL = 5
    xbmc.log = lambda msg, nivel=1: chamadas.append(('log', msg))
    xbmc.executebuiltin = lambda *a, **k: chamadas.append(('builtin', a))
    xbmc.getInfoLabel = lambda s: '' 
    xbmc.getCondVisibility = lambda s: False
    xbmc.getLocalizedString = lambda n: ''
    xbmc.getSkinDir = lambda: 'skin.novatv'
    xbmc.translatePath = lambda p: p
    xbmc.executeJSONRPC = lambda *a, **k: '{"result": {"ok": true}}'
    xbmc.sleep = lambda *a, **k: None

    class Player(object):
        def __init__(self, *a, **k):
            pass

        def isPlaying(self):
            return False

        def isPlayingVideo(self):
            return False

        def isPlayingAudio(self):
            return False

        def getPlayingFile(self):
            return ''

        def getTime(self):
            return 0.0

        def getTotalTime(self):
            return 0.0

        def stop(self):
            pass

    xbmc.Player = Player
    xbmc.Monitor = type('Monitor', (object,), {
        'waitForAbort': lambda self, t=None: True,
        'abortRequested': lambda self: True,
    })
    sys.modules['xbmc'] = xbmc

    addon = types.ModuleType('xbmcaddon')
    addon.Addon = lambda *a, **k: types.SimpleNamespace(
        getAddonInfo=lambda c: {'id': 'service.smarted.bootstrap',
                                'path': pasta}.get(c, ''),
        getSetting=lambda _c: '', setSetting=lambda *a: None,
        getLocalizedString=lambda n: '')
    sys.modules['xbmcaddon'] = addon

    vfs = types.ModuleType('xbmcvfs')
    vfs.translatePath = lambda p: p
    vfs.exists = os.path.exists
    vfs.mkdirs = lambda *a, **k: True
    vfs.copy = lambda *a, **k: True
    vfs.delete = lambda *a, **k: True
    vfs.listdir = lambda *a, **k: ([], [])
    vfs.File = lambda *a, **k: types.SimpleNamespace(
        read=lambda *x: '', write=lambda *x: None, close=lambda: None)
    sys.modules['xbmcvfs'] = vfs

    gui = types.ModuleType('xbmcgui')
    gui.NOTIFICATION_INFO = gui.NOTIFICATION_WARNING = gui.NOTIFICATION_ERROR = 0
    gui.Dialog = lambda *a, **k: types.SimpleNamespace(
        ok=lambda *a, **k: None, notification=lambda *a, **k: None,
        yesno=lambda *a, **k: False, select=lambda *a, **k: 0,
        input=lambda *a, **k: '', textviewer=lambda *a, **k: None,
        progress=lambda *a, **k: None)
    gui.ListItem = lambda *a, **k: types.SimpleNamespace(
        setLabel=lambda *a: None, setArt=lambda *a: None,
        setProperty=lambda *a: None)
    gui.Window = lambda *a, **k: types.SimpleNamespace(
        getProperty=lambda _k: '', setProperty=lambda *a: None,
        clearProperty=lambda *a: None, clearProperties=lambda: None)
    sys.modules['xbmcgui'] = gui

    pyxbmct = types.ModuleType('pyxbmct')
    sys.modules.setdefault('pyxbmct', pyxbmct)
    return chamadas


def simular(pasta=ADDON_PADRAO, chamar_wait_for_abort=False):
    """Importa o service.py e devolve (ok, dados). Nao executa o loop do boot."""
    erros = []
    chamadas = _stubs(pasta, erros)
    if pasta not in sys.path:
        sys.path.insert(0, pasta)
    try:
        import importlib
        servico = importlib.import_module('service')
    except Exception as erro:
        import traceback
        return False, {'erro': '%s: %s' % (type(erro).__name__, erro),
                       'traceback': traceback.format_exc()[-1500:],
                       'chamadas': chamadas[-10:]}
    # O service.py importa estes no topo; os demais sao carregados sob demanda
    # (smart_ads -> ads_regra/ads_vast/vip, etc.). Listar o que o boot exige.
    exigidos = ('repair', 'favourites', 'performance', 'menu_smarted',
                'skin_setup', 'smart_ads')
    modulos = sorted(n for n in sys.modules if n in exigidos)
    faltando = [n for n in exigidos if n not in sys.modules]
    return True, {'modulos': modulos, 'faltando': faltando,
                  'chamadas': chamadas[-10:],
                  'tem_main': hasattr(servico, 'main'),
                  'tem_log': hasattr(servico, 'log')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--addon-dir', default=ADDON_PADRAO)
    args = parser.parse_args(argv)
    ok, dados = simular(args.addon_dir)
    if not ok:
        aviso('FALHOU ao importar o servico: %s' % dados['erro'])
        print(dados['traceback'])
        return 1
    if dados['faltando']:
        aviso('FALHOU: modulos exigidos pelo boot nao carregaram: %s'
              % ', '.join(dados['faltando']))
        return 1
    aviso('servico importado: %s modulos do boot carregados (%s)' % (
        len(dados['modulos']), ', '.join(dados['modulos'])))
    aviso('service.py exporta main=%s log=%s' % (dados['tem_main'],
                                                 dados['tem_log']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
