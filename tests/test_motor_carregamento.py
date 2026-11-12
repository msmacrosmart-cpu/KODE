# -*- coding: utf-8 -*-
"""Motor de carregamento da Home: barra superior e carrosséis voltam a popular.

Simula o Kodi (xbmc/xbmcgui/xbmcplugin) e o addon (JSON-RPC) para garantir, com
1 teste por funcao, que a Home recebe as categorias na barra e os itens dos
carrosséis - o cenario que ficou vazio na captura do usuario.
"""
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
with patch.dict(sys.modules, {'routes': routes}):
    favorites = load('favorites', 'favorites.py')
with patch.dict(sys.modules, {'routes': routes, 'search': search, 'catalogue': catalogue,
                              'favorites': favorites}):
    navigation = load('navigation', 'navigation.py')


def plugin_url(mode, target='', nome=''):
    return routes.BRAZUCA + '?' + urlencode({'url': target, 'mode': mode, 'name': nome})


CATEGORIAS = [('TV ao vivo', 21, '#menu_canais'), ('Filmes', 27, '#filmes_menu'),
              ('Séries', 27, '#series_menu'), ('Novelas', 25, '#novelas_menu'),
              ('Animes', 22, '#animes_menu'), ('Doramas', 31, '#doramas_menu'),
              ('Desenhos', 28, '#desenhos_menu')]


class FakeKodi:
    def __init__(self, arquivos):
        self.arquivos = arquivos       # url -> lista de itens da pasta
        self.builtins = []

    def install(self):
        xbmc = types.ModuleType('xbmc')
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 2, 3
        xbmc.executebuiltin = self.builtins.append
        xbmc.log = lambda *a, **k: None
        xbmc.sleep = lambda *_: None

        def rpc(raw):
            pedido = json.loads(raw)
            url = pedido['params']['directory']
            if url not in self.arquivos:
                return json.dumps({'error': {'code': -32602, 'message': 'not found'}})
            return json.dumps({'result': {'files': self.arquivos[url]}})

        xbmc.executeJSONRPC = rpc
        xbmcgui = types.ModuleType('xbmcgui')
        itens = []

        class Item:
            def __init__(self, label='', **k):
                self.label = label
                self.art = {}
                self.info = {}

            def setArt(self, art):
                self.art = art

            def setInfo(self, kind, info):
                self.info = info

            def setProperty(self, *a, **k):
                return None

            def getVideoInfoTag(self):
                class Tag:
                    def __getattr__(self, nome):
                        return lambda *a, **k: None
                return Tag()

        xbmcgui.ListItem = Item
        xbmcgui.NOTIFICATION_INFO = 'info'
        xbmcgui.NOTIFICATION_WARNING = 'warning'
        xbmcgui.NOTIFICATION_ERROR = 'error'
        xbmcgui.Dialog = lambda: types.SimpleNamespace(notification=lambda *a, **k: None)
        xbmcplugin = types.ModuleType('xbmcplugin')
        xbmcplugin.SORT_METHOD_UNSORTED = 0

        def add(handle, url, item, isFolder=False):
            itens.append((item.label, url, isFolder))

        xbmcplugin.addDirectoryItem = add
        xbmcplugin.endOfDirectory = lambda *a, **k: None
        xbmcplugin.setContent = lambda *a, **k: None
        xbmcplugin.addSortMethod = lambda *a, **k: None
        xbmcplugin.SORT_METHOD_LABEL = 1
        self.itens = itens
        xbmcvfs = types.ModuleType('xbmcvfs')
        xbmcvfs.translatePath = lambda caminho: caminho
        xbmcvfs.exists = lambda *a: False
        xbmcvfs.mkdirs = lambda *a: True
        self.modules = {'xbmcvfs': xbmcvfs, 'xbmc': xbmc, 'xbmcgui': xbmcgui, 'xbmcplugin': xbmcplugin,
                        'routes': routes, 'search': search, 'catalogue': catalogue,
                        'favorites': favorites, 'navigation': navigation}


class MotorTest(unittest.TestCase):
    def test_barra_superior_recebe_as_sete_categorias(self):
        menu = [{'label': nome, 'file': plugin_url(mode, url), 'filetype': 'directory'}
                for nome, mode, url in CATEGORIAS]
        falso = FakeKodi({routes.brazuca(0, ''): menu})
        falso.install()
        with patch.dict(sys.modules, falso.modules):
            entradas, origem = navigation.build('favoritos.dat', falso.modules['xbmc'].executeJSONRPC,
                                                None)
            navigation.apply_skin_strings(entradas, falso.modules['xbmc'].executebuiltin)
        rotulos = [e['label'] for e in entradas]
        self.assertEqual(origem, 'menu')
        self.assertEqual(rotulos[:7], [n for n, _, _ in CATEGORIAS])
        publicados = [c for c in falso.builtins if c.startswith('Skin.SetString(smarted_nav_url_')]
        self.assertEqual(len(publicados), len(entradas))
        self.assertIn('mode=21', publicados[0])
        self.assertIn('mode=27', publicados[1])

    def test_carrossel_da_home_traz_itens_do_addon(self):
        lancamentos = [{'label': '[B]CATEGORIA: LANÇAMENTOS[/B]',
                        'file': plugin_url(27, 'lanc'), 'filetype': 'directory'}]
        filme = plugin_url(16, '#movie=1')
        arquivos = {
            routes.brazuca(27, '#filmes_menu'): lancamentos,
            plugin_url(27, 'lanc'): [
                {'label': '[B]Filme A[/B]', 'file': filme, 'filetype': 'file',
                 'thumbnail': 'capa-a', 'year': 2026, 'plot': 'sinopse', 'rating': 8.1},
                {'label': '[B]Filme B[/B]', 'file': plugin_url(16, '#movie=2'),
                 'filetype': 'file', 'thumbnail': 'capa-b'}],
        }
        falso = FakeKodi(arquivos)
        falso.install()
        with patch.dict(sys.modules, falso.modules):
            default = load('bridge_default_carrossel', 'default.py')
            default.carousel(1, {'alvo': ['filmes']})
        titulos = [rotulo.replace('[B]', '').replace('[/B]', '') for rotulo, _, _ in falso.itens]
        self.assertEqual(titulos, ['Filme A', 'Filme B'])
        self.assertEqual(falso.itens[0][1], filme)          # URL nativa preservada
        self.assertFalse(falso.itens[0][2])

    def test_pasta_do_addon_abre_direto_sem_ponte(self):
        entrada = {'label': 'Filmes', 'url': plugin_url(27, '#filmes_menu'),
                   'playable': False, 'origem': 'menu'}
        comando = navigation.open_command(entrada)
        self.assertTrue(comando.startswith('ActivateWindow(Videos,plugin://plugin.video'))
        self.assertNotIn('route=pasta', comando)
        self.assertNotIn(',return)', comando)
        video = {'label': 'Filme', 'url': plugin_url(16, '#movie=1'), 'playable': True,
                 'origem': 'menu'}
        self.assertTrue(navigation.open_command(video).startswith('PlayMedia('))


if __name__ == '__main__':
    unittest.main()
