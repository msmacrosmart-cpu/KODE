import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

BRIDGE = Path(__file__).resolve().parents[1] / 'kodi/addons/plugin.video.smarted'

def load(name, filename):
    spec=importlib.util.spec_from_file_location(name, BRIDGE / filename)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

routes=load('routes','routes.py')
with patch.dict(sys.modules, {'routes': routes}): search=load('search','search.py')
with patch.dict(sys.modules, {'search': search}): channels=load('channel_search','channel_search.py')
with patch.dict(sys.modules, {'routes': routes, 'search': search}): catalogue=load('catalogue','catalogue.py')
favorites=load('favorites','favorites.py')

class ChannelFavoritesTest(unittest.TestCase):
    def test_empty_legacy_and_malformed_never_modified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'favorites.dat'
            self.assertFalse(favorites.has_channel_favorites(p))
            for content in ('[]','{}','{"canais": []}','not json'):
                p.write_text(content)
                self.assertFalse(favorites.has_channel_favorites(p))
                self.assertEqual(p.read_text(),content)
            p.write_text('{"canais":[["channel"]]}')
            self.assertTrue(favorites.has_channel_favorites(p))

    def test_widget_only_calls_native_favorites_when_channels_exist(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'favorites.dat'; events=[]
            class Item:
                def __init__(self,label): self.label=label
                def setArt(self,value): pass
                def setProperty(self,key,value): pass
            gui=types.SimpleNamespace(ListItem=Item)
            plugin=types.SimpleNamespace(setContent=lambda *a:None,
                addDirectoryItem=lambda *a,**kw:events.append(('item',a,kw)),
                endOfDirectory=lambda *a,**kw:events.append(('end',a,kw)))
            target=routes.BRAZUCA+'?'+urlencode({'mode':'16','url':'channel'})
            def rpc(request):
                data=json.loads(request)
                self.assertEqual(data['params']['directory'],routes.brazuca(15,'canais'))
                return json.dumps({'result': {'files':[{'label':'TV','file':target,'filetype':'file'}]}})
            xbmc=types.SimpleNamespace(executeJSONRPC=rpc, LOGWARNING=2, log=lambda *a:events.append(('log',a)))
            vfs=types.SimpleNamespace(translatePath=lambda _:str(path))
            modules={'xbmc':xbmc,'xbmcvfs':vfs,'xbmcgui':gui,'xbmcplugin':plugin,'routes':routes,
                     'search':search,'channel_search':channels,'catalogue':catalogue,'favorites':favorites}
            with patch.dict(sys.modules,modules):
                main=load('channel_favorites_main','default.py')
                main.channel_favorites(4)
                self.assertEqual([e[0] for e in events],['end'])
                path.write_text('{"canais":[["channel"]]}')
                before=path.read_bytes(); events.clear()
                main.channel_favorites(4)
                self.assertEqual([e[0] for e in events],['item','end'])
                self.assertEqual(events[0][1][1],target)
                self.assertEqual(path.read_bytes(),before)

if __name__=='__main__': unittest.main()
