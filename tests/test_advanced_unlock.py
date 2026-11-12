# -*- coding: utf-8 -*-
"""Modo avançado: 5 entradas consecutivas em Ajustes liberam as opções de admin.

Este teste carrega o ``check.py`` real do addon de bootstrap com um ``xbmc``
falso que guarda as skin strings/bools **em disco**, para provar:

* 1 a 4 entradas não liberam nada (o modo básico continua simples);
* a 5ª entrada roda ``Skin.SetBool(secret_unlocked)`` e mostra o aviso discreto;
* a 6ª em diante não conta nem avisa de novo;
* o estado sobrevive a um restart (releitura do arquivo de skin settings);
* o comando antigo de clique na logo foi desativado.
"""
from __future__ import absolute_import, unicode_literals

import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
STUBS = ROOT / 'tests' / 'kodi_plugin_stubs'
CHECK = BOOTSTRAP / 'check.py'


class SkinSettings(object):
    """Reproduz o addon_data/skin.novatv/settings.xml de forma persistente."""

    def __init__(self, path):
        self.path = path
        self.strings = {}
        self.flags = set()
        self.builtins = []
        self.notifications = []
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            self.strings = data.get('strings', {})
            self.flags = set(data.get('flags', []))

    def save(self):
        with open(self.path, 'w', encoding='utf-8') as handle:
            json.dump({'strings': self.strings, 'flags': sorted(self.flags)}, handle)


def make_xbmc(store):
    module = types.ModuleType('xbmc')

    def getInfoLabel(info):
        match = re.match(r'Skin\.String\((.*?)\)$', info or '')
        if match:
            return store.strings.get(match.group(1), '')
        return ''

    def getCondVisibility(condition):
        match = re.match(r'Skin\.HasSetting\((.*?)\)$', condition or '')
        if match:
            return match.group(1) in store.flags
        return False

    def executebuiltin(command, wait=False):
        store.builtins.append(command)
        match = re.match(r'Skin\.SetString\(([^,]+),(-?\d+)\)$', command)
        if match:
            store.strings[match.group(1)] = match.group(2)
            store.save()
            return
        match = re.match(r'Skin\.SetBool\((.*?)\)$', command)
        if match:
            store.flags.add(match.group(1))
            store.save()
            return
        match = re.match(r'Skin\.Reset\((.*?)\)$', command)
        if match:
            store.flags.discard(match.group(1))
            store.strings.pop(match.group(1), None)
            store.save()
            return
        match = re.match(r'Notification\((.*)\)$', command)
        if match:
            store.notifications.append(match.group(1))

    module.getInfoLabel = getInfoLabel
    module.getCondVisibility = getCondVisibility
    module.executebuiltin = executebuiltin
    module.log = lambda *a, **k: None
    module.LOGDEBUG = 0
    module.LOGINFO = 1
    module.LOGWARNING = 2
    module.LOGERROR = 3
    module.LOGFATAL = 4
    module.LOGNONE = 5
    module.sleep = lambda *a, **k: None
    module.translatePath = lambda path: path

    class Monitor(object):
        def abortRequested(self):
            return False

        def waitForAbort(self, timeout=0):
            return True

    module.Monitor = Monitor
    return module


def install_stubs(store):
    """Coloca os fakes em sys.modules antes de carregar o addon."""
    for name, path in (('xbmcvfs', STUBS), ('xbmcaddon', None)):
        if name == 'xbmcvfs' or name not in sys.modules:
            module = types.ModuleType(name)
            module.translatePath = lambda path: path
            module.exists = os.path.exists
            module.listdir = lambda path: ([], []) if os.path.isdir(path) else ([], [])
            module.mkdir = lambda path: os.makedirs(path, exist_ok=True) or True
            module.mkdirs = module.mkdir
            module.remove = lambda path: os.remove(path) or True
            module.writeFile = lambda path, data: None
            module.readFile = lambda path: None
            if name == 'xbmcaddon':
                module.Addon = lambda *a, **k: types.SimpleNamespace(
                    getAddonInfo=lambda key: str(ROOT),
                    getSetting=lambda key: '',
                    setSetting=lambda key, value: None,
                    getLocalizedString=lambda key: '')
            sys.modules[name] = module
    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.Dialog = lambda *a, **k: types.SimpleNamespace(
        notification=lambda *a, **k: None,
        ok=lambda *a, **k: True,
        yesno=lambda *a, **k: False)
    xbmcgui.ListItem = lambda *a, **k: types.SimpleNamespace()
    sys.modules['xbmcgui'] = xbmcgui
    sys.modules['xbmc'] = make_xbmc(store)


def load_check(store):
    install_stubs(store)
    package = 'smarted_bootstrap'
    if package not in sys.modules:
        module = types.ModuleType(package)
        module.__path__ = [str(BOOTSTRAP)]
        sys.modules[package] = module
    for name in list(sys.modules):
        if name in ('service', 'favourites', 'performance', 'repair', 'check'):
            del sys.modules[name]
    sys.path.insert(0, str(BOOTSTRAP))
    try:
        spec = importlib.util.spec_from_file_location('check', str(CHECK))
        module = importlib.util.module_from_spec(spec)
        sys.modules['check'] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(BOOTSTRAP))


class AdvancedUnlockTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = os.path.join(self.tmp.name, 'settings.xml')
        self.store = SkinSettings(self.settings)
        self.check = load_check(self.store)

    def visitas(self, vezes):
        for _ in range(vezes):
            self.assertTrue(self.check.handle_skin_command('secret-cycle'))

    def test_quatro_entradas_nao_liberam_nada(self):
        self.visitas(4)
        self.assertEqual(self.store.strings.get('secret_settings_cycle'), '4')
        self.assertEqual(self.store.flags, set())
        self.assertEqual(self.store.notifications, [])

    def test_quinta_entrada_libera_com_aviso_discreto(self):
        self.visitas(5)
        self.assertIn('secret_unlocked', self.store.flags)
        self.assertIn('Skin.SetBool(secret_unlocked)', self.store.builtins)
        self.assertEqual(len(self.store.notifications), 1)
        self.assertIn('Modo avancado liberado', self.store.notifications[0])
        self.assertEqual(self.store.strings.get('secret_settings_cycle'), '5')

    def test_sexta_entrada_nao_conta_nem_avisa_de_novo(self):
        self.visitas(6)
        self.assertEqual(self.store.strings.get('secret_settings_cycle'), '5')
        self.assertEqual(len(self.store.notifications), 1)

    def test_desbloqueio_sobrevive_ao_restart(self):
        self.visitas(5)
        # "reinicia o app": novo estado lido do mesmo arquivo de skin settings
        novo = SkinSettings(self.settings)
        self.assertIn('secret_unlocked', novo.flags)
        check = load_check(novo)
        for _ in range(3):
            check.handle_skin_command('secret-cycle')
        self.assertIn('secret_unlocked', novo.flags)
        self.assertEqual(novo.notifications, [])
        # continua liberado sem precisar entrar 5x de novo
        self.assertTrue(check.handle_skin_command('secret-cycle'))

    def test_comando_antigo_de_clique_na_logo_desativa_o_unlock(self):
        self.visitas(5)
        self.assertIn('secret_unlocked', self.store.flags)
        self.assertTrue(self.check.handle_skin_command('secret-click'))
        self.assertNotIn('secret_unlocked', self.store.flags)
        self.assertEqual(self.store.strings.get('secret_settings_cycle'), '0')

    def test_comando_desconhecido_nao_quebra(self):
        self.assertFalse(self.check.handle_skin_command('qualquer-coisa'))
        self.assertEqual(self.store.builtins, [])


if __name__ == '__main__':
    unittest.main()
