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


class CatalogueTest(unittest.TestCase):
    def test_recent_movies_follows_native_menu_and_preserves_paths(self):
        launch = url(1, 'source')
        menu = [{'label': '[B]CATEGORIA: [COLOR gold]LANÇAMENTOS[/COLOR][/B]', 'file': launch, 'filetype': 'directory'}]
        movie = url(16, '#movies_list=one|two')
        choices = url(11, 'option-a|option-b')
        files = [{'label': 'Cabeçalho', 'file': url(16, 'here'), 'filetype': 'file'},
                 {'label': '[B]Filme[/B]', 'file': movie, 'filetype': 'file', 'thumbnail': 'poster', 'fanart': 'wide', 'year': 2026},
                 {'label': 'Opções', 'file': choices, 'filetype': 'file'},
                 {'label': 'Outro', 'file': 'https://example.invalid/x', 'filetype': 'file'}]
        requests = []
        def rpc(raw):
            request = json.loads(raw); path = request['params']['directory']; requests.append(path)
            return json.dumps({'result': {'files': menu if len(requests) == 1 else files}})
        found = catalogue.recent_movies(rpc)
        self.assertEqual(requests, [routes.brazuca(27, '#filmes_menu'), launch])
        self.assertEqual([x['url'] for x in found], [movie])
        self.assertEqual([x['playable'] for x in found], [True])
        self.assertEqual(found[0]['title'], 'Filme')
        self.assertEqual(found[0]['fanart'], 'wide')
        self.assertEqual(found[0]['year'], 2026)

    def test_movies_overview_keeps_native_search_and_flattens_genres_and_page(self):
        def entry(label, target, kind='directory'):
            return {'label': label, 'file': target, 'filetype': kind}
        search_url, launches, genres, alphabet, trilogy = [url(27, str(i)) for i in range(5)]
        genre, movie = url(27, 'acao'), url(16, 'movie')
        menu = [entry('[B]PESQUISE POR FILMES[/B]',search_url),
                entry('[B]CATEGORIA: GÊNEROS[/B]',genres),
                entry('[B]CATEGORIA: LANÇAMENTOS[/B]',launches),
                entry('[B]CATEGORIA: ORDEM ALFABÉTICA[/B]',alphabet),
                entry('[B]CATEGORIA: TRILOGIA[/B]',trilogy)]
        values = {routes.brazuca(27, '#filmes_menu'):menu, genres:[entry('Ação',genre)],
                  alphabet:[entry('Um filme',movie,'file')]}
        def rpc(raw):
            req=json.loads(raw)
            return json.dumps({'result': {'files': values[req['params']['directory']]}})
        found, failed = catalogue.movie_overview(rpc)
        self.assertEqual([x['url'] for x in found], [search_url, launches, genre, movie, alphabet, trilogy,
                                                    routes.brazuca(27, '#filmes_menu')])
        self.assertEqual(failed, [])
        values[genres] = []
        found, failed = catalogue.movie_overview(rpc)
        self.assertIn(genres, [x['url'] for x in found])
        self.assertEqual(failed, ['gêneros'])

    def test_empty_source_and_error_are_not_fabricated(self):
        self.assertEqual(catalogue.recent_movies(lambda _: '{"result": {}}'), [])
        with self.assertRaises(ValueError):
            catalogue.recent_movies(lambda _: '{"error": {}}')

    def test_widget_entrypoint_exposes_real_result_and_safe_failure(self):
        events = []
        class Info:
            def setTitle(self, value): self.title = value
            def setPlot(self, value): self.plot = value
            def setYear(self, value): self.year = value
        class Item:
            def __init__(self, label): self.label = label; self.info = Info()
            def setArt(self, value): self.art = value
            def getVideoInfoTag(self): return self.info
            def setProperty(self, key, value): self.prop = (key, value)
        plugin = types.SimpleNamespace(setContent=lambda *a: events.append(('content', a)),
            SORT_METHOD_UNSORTED=0, addSortMethod=lambda *a: None,
            addDirectoryItem=lambda *a, **kw: events.append(('item', a, kw)),
            endOfDirectory=lambda *a, **kw: events.append(('end', a, kw)))
        xbmc = types.SimpleNamespace(executeJSONRPC=lambda _: '{}', LOGWARNING=2,
                                     log=lambda *a: events.append(('log', a)))
        sample = {'label':'Filme','url':url(16,'original'),'title':'Filme', 'folder':False,
                  'playable':True,'thumbnail':'poster','fanart':'wide','plot':'','year':2026}
        source = types.SimpleNamespace(recent_movies=lambda rpc: [sample])
        with patch.dict(sys.modules, {'routes':routes,'xbmcgui':types.SimpleNamespace(ListItem=Item),
                'xbmcplugin':plugin,'xbmc':xbmc,'catalogue':source}):
            main = load('catalogue_main','default.py')
            main.recent_movies(4)
            item = next(e for e in events if e[0] == 'item')
            self.assertEqual(item[1][1], sample['url'])
            self.assertEqual(item[1][2].info.year, 2026)
            self.assertTrue(events[-1][2]['succeeded'])
            events.clear()
            def bad(_): raise RuntimeError('sensitive details not to log')
            source.recent_movies=bad
            main.recent_movies(4)
            self.assertFalse(events[-1][2]['succeeded'])
            self.assertNotIn('sensitive', str(events))

    def test_home_keeps_original_hero_dimensions_and_uses_brazuca(self):
        from xml.etree import ElementTree as ET
        home=ET.parse(BRIDGE.parents[1] / 'skin.novatv/xml/Home.xml').getroot()
        hero=home.find(".//control[@id='9100']")
        self.assertEqual((hero.findtext('width'), hero.findtext('height')), ('1920','780'))
        self.assertEqual(hero.findtext('content'), 'plugin://plugin.video.smarted/?route=recent-movies')
        latest=home.find(".//control[@id='9200']/content")
        self.assertEqual(latest.text, 'plugin://plugin.video.smarted/?route=recent-movies')
        self.assertEqual(latest.get('limit'), '10')
        favourite_channels=home.find(".//control[@id='9230']/content")
        self.assertEqual(favourite_channels.text, 'plugin://plugin.video.smarted/?route=channel-favorites')
        self.assertNotIn('pvr://', favourite_channels.text)

if __name__ == '__main__':
    unittest.main()
