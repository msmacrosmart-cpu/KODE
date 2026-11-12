# -*- coding: utf-8 -*-
"""Ponte de favoritos: a Home lê o MESMO favorites.dat do Brazuca Play.

Cobrem o caminho usado pelas três linhas da Home (rota ``favoritos-<categoria>``
do plugin.video.smarted): decodificação do arquivo real do addon, URL nativa de
cada item (tocar canal/filme, abrir pasta de série) e leitura sem escrita.
"""
import base64
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / 'kodi' / 'addons' / 'plugin.video.smarted'


def load(name, filename, modules=None):
    spec = importlib.util.spec_from_file_location(name, BRIDGE / filename)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules or {}):
        spec.loader.exec_module(module)
    return module


favorites = load('favorites', 'favorites.py')
routes = load('routes', 'routes.py')


def encode(value):
    return base64.b16encode(base64.b64encode(value.encode('utf-8'))).decode('ascii')


def fixture(path):
    data = {
        'canais': [['[B][COLOR white]Canal Um[/COLOR][/B]', encode('https://exemplo/um.m3u8'), 11,
                    encode(''), 'https://exemplo/um.png', 'https://exemplo/um-fan.jpg', 'canal']],
        'filmes': [['[B][COLOR white]Filme Um[/COLOR][/B]', encode('https://exemplo/filme'), 16,
                    encode(''), 'https://exemplo/filme.jpg', 'https://exemplo/filme-fan.jpg', 'filme']],
        'series': [['[B][COLOR white]Serie Um[/COLOR][/B]', encode('https://exemplo/serie'), 27,
                    encode(''), 'https://exemplo/serie.jpg', 'https://exemplo/serie-fan.jpg', 'serie']],
    }
    Path(path).write_text(json.dumps(data), encoding='utf-8')


class DecodeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'favorites.dat'
        fixture(self.path)

    def test_le_as_tres_categorias_do_addon(self):
        data = favorites.load(self.path)
        self.assertEqual(sorted(data), ['canais', 'filmes', 'series'])
        entrada = data['canais'][0]
        self.assertEqual(entrada['label'], '[B][COLOR white]Canal Um[/COLOR][/B]')
        self.assertEqual(entrada['url'], 'https://exemplo/um.m3u8')
        self.assertEqual(entrada['mode'], 11)
        self.assertEqual(entrada['thumb'], 'https://exemplo/um.png')
        self.assertEqual(entrada['fanart'], 'https://exemplo/um-fan.jpg')

    def test_arquivo_nunca_e_alterado(self):
        antes = self.path.read_bytes()
        favorites.load(self.path)
        favorites.favorite_items(self.path, 'canais')
        self.assertEqual(self.path.read_bytes(), antes)

    def test_arquivo_ausente_lista_vazio(self):
        self.assertEqual(favorites.load(Path(self.tmp.name) / 'nao-existe.dat'), {})
        self.assertEqual(favorites.favorite_items(Path(self.tmp.name) / 'nao.dat', 'canais'), [])
        self.assertFalse(favorites.has_favorites(Path(self.tmp.name) / 'nao.dat'))

    def test_arquivo_corrompido_lista_vazio(self):
        self.path.write_text('lixo que nao e json')
        self.assertEqual(favorites.load(self.path), {})
        self.assertEqual(favorites.favorite_items(self.path, 'canais'), [])

    def test_lista_legada_vira_unknown(self):
        self.path.write_text(json.dumps([['antigo', encode('https://exemplo/a'), 11, encode(''),
                                         'i.png', 'f.jpg', 'd']]))
        self.assertEqual(list(favorites.load(self.path)), ['unknown'])

    def test_canais_e_filmes_tocam_e_series_abrem_pasta(self):
        itens = favorites.favorite_items(self.path, 'canais')
        self.assertTrue(itens[0]['playable'])
        self.assertFalse(itens[0]['folder'])

        itens = favorites.favorite_items(self.path, 'filmes')
        self.assertTrue(itens[0]['playable'])

        itens = favorites.favorite_items(self.path, 'series')
        self.assertFalse(itens[0]['playable'])
        self.assertTrue(itens[0]['folder'])

    def test_url_reaproveita_a_rota_original_do_addon(self):
        item = favorites.favorite_items(self.path, 'filmes')[0]
        parsed = urlsplit(item['url'])
        self.assertEqual(parsed.scheme, 'plugin')
        self.assertEqual(parsed.netloc, 'plugin.video.BrazucaPlay.Matrix')
        params = parse_qs(parsed.query, keep_blank_values=True)
        self.assertEqual(params['mode'][0], '16')
        self.assertEqual(params['url'][0], 'https://exemplo/filme')
        self.assertIn('iconimage', params)

    def test_pasta_de_serie_leva_fanart_e_icone(self):
        item = favorites.favorite_items(self.path, 'series')[0]
        params = parse_qs(urlsplit(item['url']).query, keep_blank_values=True)
        self.assertEqual(params['mode'][0], '27')
        self.assertEqual(params['iconimage'][0], 'https://exemplo/serie.jpg')
        self.assertEqual(params['fanart'][0], 'https://exemplo/serie-fan.jpg')

    def test_categorias_com_favoritos(self):
        self.assertEqual(favorites.categories(self.path), ['canais', 'filmes', 'series'])


class RouteTest(unittest.TestCase):
    """A rota favoritos-<categoria> devolve itens para o container da Home."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'favorites.dat'
        fixture(self.path)
        self.events = []

    def _modules(self):
        events = self.events

        class Item(object):
            def __init__(self, label=''):
                self.label = label
                self.art = {}
                self.props = {}
                self.info = types.SimpleNamespace(
                    setTitle=lambda *a: None, setPlot=lambda *a: None,
                    setMediaType=lambda *a: None)

            def setArt(self, value):
                self.art = value

            def setProperty(self, key, value):
                self.props[key] = value

            def getVideoInfoTag(self):
                return self.info

        gui = types.SimpleNamespace(ListItem=Item)
        plugin = types.SimpleNamespace(
            setContent=lambda *a: events.append(('content',) + a),
            setProperty=lambda *a: None,
            addSortMethod=lambda *a: None,
            SORT_METHOD_UNSORTED=0,
            addDirectoryItem=lambda handle, url, item, isFolder=False:
                events.append(('item', handle, url, item, isFolder)),
            endOfDirectory=lambda handle, **kw: events.append(('end', handle, kw)))
        xbmc = types.SimpleNamespace(LOGINFO=1, LOGWARNING=2, log=lambda *a: None)
        vfs = types.SimpleNamespace(translatePath=lambda path: str(self.path))
        return {'xbmc': xbmc, 'xbmcvfs': vfs, 'xbmcgui': gui, 'xbmcplugin': plugin,
                'favorites': favorites, 'routes': routes}

    def _main(self):
        with patch.dict(sys.modules, self._modules()):
            return load('bridge_main', 'default.py', self._modules())

    def test_lista_os_favoritos_de_filmes(self):
        main = self._main()
        with patch.dict(sys.modules, self._modules()):
            main.favorites_window(4, 'filmes')
        kinds = [event[0] for event in self.events]
        self.assertEqual(kinds, ['content', 'item', 'end'])
        url, item, is_folder = self.events[1][2], self.events[1][3], self.events[1][4]
        self.assertFalse(is_folder)
        self.assertEqual(item.props.get('IsPlayable'), 'true')
        self.assertIn('plugin.video.BrazucaPlay.Matrix', url)
        self.assertTrue(self.events[2][2].get('succeeded'))

    def test_categoria_sem_favoritos_nao_quebra(self):
        main = self._main()
        with patch.dict(sys.modules, self._modules()):
            main.favorites_window(4, 'doramas')
        self.assertEqual([event[0] for event in self.events], ['end'])
        self.assertTrue(self.events[0][2].get('succeeded'))

    def test_rota_despachada_no_main(self):
        main = self._main()
        argv = ['plugin://plugin.video.smarted/', '4', '?route=favoritos-series']
        with patch.dict(sys.modules, self._modules()), patch.object(sys, 'argv', argv):
            main.main()
        self.assertEqual([event[0] for event in self.events], ['content', 'item', 'end'])
        self.assertTrue(self.events[1][4], 'série é pasta')


if __name__ == '__main__':
    unittest.main()
