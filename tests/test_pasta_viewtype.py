# -*- coding: utf-8 -*-
"""Tela final x intermediaria: a grade (e os filtros) so entram quando ha video."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

BRIDGE = Path(__file__).resolve().parents[1] / 'kodi/addons/plugin.video.smarted'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BRIDGE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


routes = load('routes', 'routes.py')
with patch.dict(sys.modules, {'routes': routes}):
    search = load('search', 'search.py')
with patch.dict(sys.modules, {'routes': routes, 'search': search}):
    catalogue = load('catalogue', 'catalogue.py')


def url(mode, target):
    return routes.BRAZUCA + '?' + urlencode({'mode': mode, 'url': target})


class FakeDir:
    def __init__(self):
        self.buildins = []
        self.items = []
        self.vista = None

    def install(self):
        xbmc = types.ModuleType('xbmc')
        xbmc.LOGINFO, xbmc.LOGWARNING = 1, 2
        xbmc.executebuiltin = self.buildins.append
        xbmc.sleep = lambda *_: None
        xbmc.executeJSONRPC = self.rpc
        xbmc.log = lambda *a, **k: None
        xbmcgui = types.ModuleType('xbmcgui')
        xbmcgui.ListItem = lambda label='', **k: types.SimpleNamespace(
            label=label, art={}, info={},
            setArt=lambda art: None, setInfo=lambda kind, info: None)
        xbmcgui.NOTIFICATION_ERROR = 'error'
        xbmcgui.Dialog = lambda: types.SimpleNamespace(notification=lambda *a, **k: None)
        xbmcplugin = types.ModuleType('xbmcplugin')
        xbmcplugin.addDirectoryItem = lambda handle, link, item, isFolder=False: self.items.append(
            (item.label, link, isFolder))
        xbmcplugin.endOfDirectory = lambda *a, **k: None
        xbmcplugin.setContent = lambda *a, **k: None
        self.modules = {'xbmc': xbmc, 'xbmcgui': xbmcgui, 'xbmcplugin': xbmcplugin,
                        'routes': routes, 'catalogue': catalogue}

    def rpc(self, raw):
        return json.dumps({'result': {'files': self.files}})

    def vista_escolhida(self):
        for comando in self.buildins:
            if comando.startswith('Container.SetViewMode('):
                return int(comando.split('(')[1].rstrip(')'))
        return None


class PastaViewTypeTest(unittest.TestCase):
    def rodar(self, files, params):
        falso = FakeDir()
        falso.files = files
        falso.install()
        with patch.dict(sys.modules, falso.modules):
            with patch.dict(sys.modules, {'routes': routes}):
                importlib.reload(catalogue) if False else None
                bridge = load('bridge_default_pasta', 'default.py')
                bridge.pasta(1, params)
        return falso

    def test_pasta_intermediaria_fica_na_lista(self):
        pastas = [{'label': '[B]CATEGORIA: LANÇAMENTOS[/B]', 'file': url(27, 'lanc'),
                   'filetype': 'directory'},
                  {'label': '[B]CATEGORIA: GÊNEROS[/B]', 'file': url(27, 'gen'),
                   'filetype': 'directory'}]
        falso = self.rodar(pastas, {'url': [url(27, '#filmes_menu')]})
        self.assertEqual(falso.vista_escolhida(), 50)          # lista vertical
        self.assertTrue(all(link.startswith('plugin://plugin.video.smarted/?route=pasta&url=')
                            for _, link, _ in falso.items))
        self.assertTrue(all(pasta for _, _, pasta in falso.items))

    def test_tela_final_usa_grade_e_respeita_o_filtro(self):
        filmes = [{'label': 'Zulu', 'file': url(16, 'zulu'), 'filetype': 'file',
                   'rating': 7.5, 'votes': '1,200'},
                  {'label': 'Alfa', 'file': url(16, 'alfa'), 'filetype': 'file',
                   'rating': 8.1, 'votes': '9,000'},
                  {'label': 'Beta', 'file': url(16, 'beta'), 'filetype': 'file',
                   'rating': 6.0, 'votes': '10'}]
        falso = self.rodar(filmes, {'url': [url(27, 'lanc')], 'ordem': ['az']})
        self.assertEqual(falso.vista_escolhida(), 52)          # grade de cards
        self.assertEqual([rotulo for rotulo, _, _ in falso.items], ['Alfa', 'Beta', 'Zulu'])
        # video continua com a URL nativa do addon (conteudo e reproducao intactos)
        self.assertEqual(falso.items[0][1], url(16, 'alfa'))
        self.assertFalse(falso.items[0][2])
        # o link da pasta atual vai para a skin (os chips de filtro usam ele)
        self.assertTrue(any(c.startswith('Skin.SetString(smarted_ordem_url,') for c in falso.buildins))

        votados = self.rodar(filmes, {'url': [url(27, 'lanc')], 'ordem': ['votados']})
        self.assertEqual([rotulo for rotulo, _, _ in votados.items], ['Alfa', 'Zulu', 'Beta'])

    def test_tv_ao_vivo_nunca_entra_na_grade(self):
        canais = [{'label': 'CANAL A', 'file': url(21, 'canal-a'), 'filetype': 'file'},
                  {'label': 'CANAL B', 'file': url(21, 'canal-b'), 'filetype': 'file'}]
        falso = self.rodar(canais, {'url': [url(21, '#menu_canais')], 'tv': ['1']})
        self.assertEqual(falso.vista_escolhida(), 50)


if __name__ == '__main__':
    unittest.main()
