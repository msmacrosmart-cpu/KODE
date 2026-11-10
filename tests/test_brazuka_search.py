import base64
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, unquote_plus, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / 'kodi/addons/plugin.video.smarted'
spec = importlib.util.spec_from_file_location('routes', BRIDGE / 'routes.py')
routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routes)
spec = importlib.util.spec_from_file_location('smarted_search', BRIDGE / 'search.py')
search = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'routes': routes}):
    spec.loader.exec_module(search)


def fixture(title='[B][COLOR white]Coração &amp; Ação[/COLOR][/B]', link='#series_list=resolver1_tvshows=a+b%20c'):
    image = base64.b64encode(b'https://example.test/poster.jpg').decode('ascii')
    return ('<channel><name>' + title + '</name><externallink>' + link + '</externallink>'
            '<thumbnail>' + image + '</thumbnail><fanart>https://example.test/bg.jpg</fanart>'
            '<info>Resumo</info></channel>')


class SearchTests(unittest.TestCase):
    def test_matches_accents_and_keeps_brazuca_route_through_double_decode(self):
        items = search.parse_feed('Séries', fixture(), 'coracao acao')
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item['title'], 'Coração & Ação')
        self.assertEqual(item['thumb'], 'https://example.test/poster.jpg')
        self.assertEqual(urlsplit(item['url']).netloc, 'plugin.video.BrazucaPlay.Matrix')
        params = parse_qs(urlsplit(item['url']).query)
        self.assertEqual(params['mode'], ['6'])
        self.assertEqual(unquote_plus(params['url'][0]), '#series_list=resolver1_tvshows=a+b%20c')
        self.assertEqual(unquote_plus(params['name'][0]), '[B][COLOR white]Coração & Ação[/COLOR][/B]')

    def test_expected_resolvers_and_reject_unknown(self):
        for url, expected_mode, expected_url in [
            ('animes4=abc', 31, 'resolver1_tvshows=abc'),
            ('novelas=abc', 25, 'novelas=abc'),
            ('wvmob=' + base64.b64encode(b'a+b').decode(), 30, 'wvmob=a+b'),
            ('#doramas_list=abc', 6, '#doramas_list=abc'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(search.select_mode(url), (expected_mode, expected_url))
        self.assertEqual(search.parse_feed('Séries', fixture(link='javascript:bad'), 'coracao'), [])
        self.assertEqual(search.parse_feed('Séries', fixture(), '!!!'), [])

    def test_five_sources_and_partial_failures_are_reported(self):
        def loader(url):
            if url == search.SOURCES[1][1]:
                raise OSError('offline')
            if url == search.SOURCES[4][1]:
                return '<html>service unavailable</html>'
            return fixture().encode('utf-8')
        results, failed = search.search('coracao', loader=loader)
        self.assertEqual([r['category'] for r in results], ['Séries', 'Animes', 'Doramas'])
        self.assertEqual(failed, ['Novelas', 'Desenhos'])

    def test_empty_query_never_fetches(self):
        self.assertEqual(search.search('!!!', loader=lambda u: self.fail('network call')), ([], []))

    def test_recent_uses_real_dates_not_feed_order_or_future(self):
        from datetime import date
        def dated(name, when):
            return fixture(title=name).replace('</channel>', '<tmdb_date>' + when + '</tmdb_date></channel>')
        feed = dated('Antiga', '01/01/2022') + dated('Recente', '10/11/2025') + dated('Futura', '01/01/2099') + dated('Inválida', 'xx')
        def loader(url):
            if url == search.SOURCES[1][1]:
                raise OSError('offline')
            return feed
        results, failed = search.recent_series(loader=loader, today=date(2026,11,10))
        self.assertEqual([i['title'] for i in results], ['Recente', 'Antiga'])
        self.assertEqual([i['release_date'] for i in results], ['2025-11-10', '2022-01-01'])
        self.assertEqual(failed, ['Novelas'])
        self.assertEqual(search.parse_recent_feed('Séries', fixture(), today=date(2026,11,10)), [])


    def test_kodi_search_reports_partial_results_and_cancel(self):
        events = []
        query = ['amor']
        class Dialog:
            def input(self, heading): return query[0]
            def notification(self, *args): events.append(('notice', args))
        class Item:
            def __init__(self, label): self.label = label
            def setArt(self, art): self.art = art
            def getVideoInfoTag(self): return self
            def setTitle(self, value): self.title = value
            def setPlot(self, value): self.plot = value
        gui = types.SimpleNamespace(Dialog=Dialog, ListItem=Item, NOTIFICATION_WARNING=1, NOTIFICATION_INFO=2)
        plugin = types.SimpleNamespace(
            setContent=lambda *a: events.append(('content', a)),
            addDirectoryItem=lambda *a, **kw: events.append(('item', a, kw)),
            endOfDirectory=lambda *a, **kw: events.append(('end', a, kw)))
        source = types.SimpleNamespace(SOURCES=search.SOURCES, normalize=search.normalize,
            search=lambda term: ([{'category': 'Séries', 'title': 'Amor', 'thumb': '', 'fanart': '',
                                   'description': '', 'url': 'plugin://real-route'}], ['Novelas']))
        spec = importlib.util.spec_from_file_location('bridge_test_main', BRIDGE / 'default.py')
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'routes': routes, 'search': source, 'xbmcgui': gui, 'xbmcplugin': plugin}):
            spec.loader.exec_module(module)
            module.search_series(12)
            self.assertEqual(len([e for e in events if e[0] == 'item']), 1)
            self.assertTrue(any(e[0] == 'notice' and 'Novelas' in e[1][1] for e in events))
            self.assertTrue(events[-1][2]['succeeded'])
            events.clear()
            query[0] = ''
            module.search_series(12)
            self.assertEqual(len(events), 1)
            self.assertFalse(events[-1][2]['succeeded'])


if __name__ == '__main__':
    unittest.main()
