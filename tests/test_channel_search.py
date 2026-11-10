import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / 'kodi/addons/plugin.video.smarted'

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, BRIDGE / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

routes = load('routes', 'routes.py')
with patch.dict(sys.modules, {'routes': routes}):
    search = load('search', 'search.py')
with patch.dict(sys.modules, {'search': search}):
    channels = load('channel_search', 'channel_search.py')


def path(mode, url):
    return routes.BRAZUCA + '?' + urlencode({'mode': mode, 'url': url, 'name': 'exemplo'})


class ChannelSearchTest(unittest.TestCase):
    def test_filters_real_directory_entries_and_preserves_modes(self):
        data = [
            {'label': '[B][COLOR white]Ação TV[/COLOR][/B]', 'file': path(16, 'live=original'), 'filetype': 'file', 'thumbnail': 'logo'},
            {'label': '[B]AÇÃO TV (2 OPÇÕES)[/B]', 'file': path(11, 'option-a|option-b'), 'filetype': 'file'},
            {'label': 'Ação Kids', 'file': path(1, 'menu'), 'filetype': 'directory'},
            {'label': 'Ação cabeçalho', 'file': path(16, 'here'), 'filetype': 'file'},
            {'label': 'Ação exterior', 'file': 'https://example.invalid/video', 'filetype': 'file'},
            {'label': 'Notícias', 'file': path(16, 'n'), 'filetype': 'file'},
            {'label': 'Ação inválida', 'file': 'plugin://[broken', 'filetype': 'file'},
        ]
        found = channels.matches(data, 'acao')
        self.assertEqual(len(found), 3)
        self.assertEqual([x['url'] for x in found], [d['file'] for d in data[:3]])
        self.assertEqual([x['playable'] for x in found], [True, False, False])
        self.assertEqual([x['folder'] for x in found], [False, False, True])
        self.assertEqual(found[0]['thumb'], 'logo')
        self.assertEqual(channels.matches(data, '!!!'), [])

    def test_kodi_requests_real_brazuka_directory_and_shows_results(self):
        events = []
        query = ['noticia']
        class Dialog:
            def input(self, heading): return query[0]
            def notification(self, *args): events.append(('notification', args))
        class Item:
            def __init__(self, label): self.label = label
            def setArt(self, value): self.art = value
            def setProperty(self, key, value): self.property = (key, value)
        gui = types.SimpleNamespace(Dialog=Dialog, ListItem=Item, NOTIFICATION_INFO=1, NOTIFICATION_WARNING=2)
        plugin = types.SimpleNamespace(
            setContent=lambda *args: events.append(('content', args)),
            addDirectoryItem=lambda *args, **kw: events.append(('item', args, kw)),
            endOfDirectory=lambda *args, **kw: events.append(('end', args, kw)))
        source = [{'label': 'Notícia TV', 'file': path(16, 'stream'), 'filetype': 'file'}]
        def json_rpc(request):
            request = json.loads(request)
            self.assertEqual(request['method'], 'Files.GetDirectory')
            parsed = parse_qs(urlsplit(request['params']['directory']).query, keep_blank_values=True)
            self.assertEqual(parsed['url'], ['#todoscanais'])
            return json.dumps({'result': {'files': source}})
        xbmc = types.SimpleNamespace(executeJSONRPC=json_rpc)
        with patch.dict(sys.modules, {'routes': routes, 'search': search, 'channel_search': channels,
                                      'xbmcgui': gui, 'xbmcplugin': plugin, 'xbmc': xbmc}):
            main = load('channel_search_main', 'default.py')
            main.search_channels(5)
            item = next(e for e in events if e[0] == 'item')
            self.assertEqual(item[1][1], source[0]['file'])
            self.assertEqual(item[1][2].property, ('IsPlayable', 'true'))
            self.assertTrue(events[-1][2]['succeeded'])
            events.clear(); query[0] = ''
            main.search_channels(5)
            self.assertEqual(len(events), 1)
            self.assertFalse(events[-1][2]['succeeded'])

    def test_kodi_reports_source_failure(self):
        events = []
        gui = types.SimpleNamespace(Dialog=lambda: types.SimpleNamespace(input=lambda _: 'tv',
            notification=lambda *args: events.append(('notification', args))), NOTIFICATION_WARNING=2)
        plugin = types.SimpleNamespace(endOfDirectory=lambda *a, **kw: events.append(('end', a, kw)))
        xbmc = types.SimpleNamespace(executeJSONRPC=lambda _: json.dumps({'error': {'message': 'failed'}}))
        with patch.dict(sys.modules, {'routes': routes, 'search': search, 'channel_search': channels,
                                      'xbmcgui': gui, 'xbmcplugin': plugin, 'xbmc': xbmc}):
            main = load('channel_error_main', 'default.py')
            main.search_channels(5)
            self.assertEqual(events[0][0], 'notification')
            self.assertFalse(events[-1][2]['succeeded'])


if __name__ == '__main__':
    unittest.main()
