# -*- coding: utf-8 -*-
"""Suite dedicada da v1.0.154: correcao do carregamento infinito na Home.

Reproduz o ambiente Android real em que ``xbmcvfs.translatePath`` devolve um
caminho ABSOLUTO para ``widget-cache`` (onde as versoes 1.0.152 e 1.0.153
lancavam ``ValueError('Invalid widget cache name')`` em ``daily_cache.py`` e
encerravam ``Container(9201)`` e ``Container(9203)`` com ``succeeded=False``).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / 'kodi' / 'addons' / 'plugin.video.smarted'


class _FakeInfoTag:
    def __init__(self):
        self.title = ''
        self.plot = ''
        self.year = 0

    def setTitle(self, v): self.title = v
    def setPlot(self, v): self.plot = v
    def setGenre(self, v): pass
    def setGenres(self, v): pass
    def setYear(self, v): self.year = v
    def __getattr__(self, _name):
        return lambda *a, **k: None


class _FakeListItem:
    def __init__(self, label='', offscreen=False):
        self.label = label
        self.art = {}
        self.props = {}
        self.tag = _FakeInfoTag()

    def setArt(self, art): self.art.update(art)
    def setProperty(self, k, v): self.props[k] = v
    def getVideoInfoTag(self): return self.tag


def _gerar_filmes_jsonrpc(qtd):
    return [
        {
            'label': 'Filme %02d (2026)' % i,
            'title': 'Filme %02d' % i,
            'file': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=12&url=f%d' % i,
            'filetype': 'file',
            'thumbnail': 'https://img.exemplo/f%d.jpg' % i,
            'fanart': 'https://img.exemplo/fan%d.jpg' % i,
            'plot': 'Sinopse completa do filme %d com acentuacao çãõé.' % i,
            'year': 2026,
            'genre': ['Acao'],
            'rating': 7.8,
            'premiered': '2026-10-%02d' % ((i % 28) + 1),
            'duration': 5400,
        }
        for i in range(1, qtd + 1)
    ]


def _gerar_feed_series_xml(qtd):
    blocos = ['<channels>']
    for i in range(1, qtd + 1):
        blocos.append(
            '<channel>'
            '<name>[COLOR yellow]Serie %02d[/COLOR]</name>'
            '<externallink>#series_list=s%d</externallink>'
            '<tmdb_date>%02d/10/2026</tmdb_date>'
            '<thumbnail>https://img.exemplo/s%d.jpg</thumbnail>'
            '<fanart>https://img.exemplo/sf%d.jpg</fanart>'
            '<info>Sinopse da serie %d com acentuacao çãõé.</info>'
            '</channel>' % (i, i, (i % 28) + 1, i, i, i)
        )
    blocos.append('</channels>')
    return ''.join(blocos).encode('utf-8')


class _AmbienteHomeAndroidReal:
    """Simula o Kodi no Android com widget-cache em caminho ABSOLUTO real."""

    def __init__(self, cache_dir: str, qtd_filmes: int = 40, qtd_series: int = 38):
        assert os.path.isabs(cache_dir), 'O teste precisa usar caminho absoluto real!'
        self.cache_dir = cache_dir
        self.qtd_filmes = qtd_filmes
        self.qtd_series = qtd_series
        self.chamadas_rpc = 0
        self.chamadas_http = 0
        self.lock = threading.Lock()
        self.resultados_por_handle = {}
        self.end_por_handle = {}

    def rpc(self, payload_str):
        with self.lock:
            self.chamadas_rpc += 1
        req = json.loads(payload_str)
        directory = req.get('params', {}).get('directory', '')
        if 'filmes_menu' in directory:
            files = [{
                'label': 'Categoria: Lancamentos',
                'file': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=lancamentos',
                'filetype': 'directory',
            }]
        else:
            files = _gerar_filmes_jsonrpc(self.qtd_filmes)
        return json.dumps({'result': {'files': files}})

    def baixar_feed(self, url):
        with self.lock:
            self.chamadas_http += 1
        if 'SERIES' in url.upper():
            return _gerar_feed_series_xml(self.qtd_series)
        return b'<channels><channel><name>Vazio</name><items></items></channel></channels>'

    def instalar_modulos(self):
        xbmc = types.ModuleType('xbmc')
        xbmc.LOGINFO = 1
        xbmc.LOGWARNING = 2
        xbmc.LOGERROR = 3
        xbmc.log = lambda *a, **k: None
        xbmc.executeJSONRPC = self.rpc

        xbmcgui = types.ModuleType('xbmcgui')
        xbmcgui.ListItem = _FakeListItem

        xbmcplugin = types.ModuleType('xbmcplugin')
        xbmcplugin.SORT_METHOD_UNSORTED = 0
        xbmcplugin.setContent = lambda *a, **k: None
        xbmcplugin.addSortMethod = lambda *a, **k: None

        def add_item(handle, url, item, isFolder=False):
            with self.lock:
                self.resultados_por_handle.setdefault(handle, []).append((url, item, isFolder))
            return True

        def end_dir(handle, succeeded=True, updateListing=False, cacheToDisc=True):
            with self.lock:
                self.end_por_handle[handle] = bool(succeeded)

        xbmcplugin.addDirectoryItem = add_item
        xbmcplugin.endOfDirectory = end_dir

        xbmcvfs = types.ModuleType('xbmcvfs')
        xbmcvfs.translatePath = lambda p: self.cache_dir

        xbmcaddon = types.ModuleType('xbmcaddon')
        xbmcaddon.Addon = lambda *a, **k: types.SimpleNamespace(getAddonInfo=lambda *x: '')

        return {
            'xbmc': xbmc,
            'xbmcgui': xbmcgui,
            'xbmcplugin': xbmcplugin,
            'xbmcvfs': xbmcvfs,
            'xbmcaddon': xbmcaddon,
        }


class HomeCarregamentoInfinitoFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = os.path.join(self.tmp.name, 'widget-cache')
        self.assertTrue(os.path.isabs(self.cache_dir))

    def tearDown(self):
        for mod in ('default', 'daily_cache', 'catalogue', 'search', 'routes', 'ordering', 'favorites'):
            sys.modules.pop(mod, None)
        self.tmp.cleanup()

    def _carregar_plugin(self, env: _AmbienteHomeAndroidReal):
        mods = env.instalar_modulos()
        patcher = patch.dict(sys.modules, mods)
        patcher.start()
        self.addCleanup(patcher.stop)
        if str(PLUGIN_DIR) not in sys.path:
            sys.path.insert(0, str(PLUGIN_DIR))
            self.addCleanup(lambda: sys.path.remove(str(PLUGIN_DIR)) if str(PLUGIN_DIR) in sys.path else None)
        for mod in ('default', 'daily_cache', 'catalogue', 'search'):
            sys.modules.pop(mod, None)
        import search
        search.download = env.baixar_feed
        import default as plugin_default
        return plugin_default

    def test_tentativa_1_home_fria_caminho_absoluto_carrega_30_filmes_e_30_series(self):
        """1a tentativa: Home fria no Android real popula 9201 e 9203 com succeeded=True."""
        env = _AmbienteHomeAndroidReal(self.cache_dir, qtd_filmes=42, qtd_series=36)
        plugin = self._carregar_plugin(env)

        plugin.recent_movies(9201)
        plugin.recent_series(9203)

        self.assertIs(env.end_por_handle.get(9201), True)
        self.assertIs(env.end_por_handle.get(9203), True)
        self.assertEqual(len(env.resultados_por_handle.get(9201, [])), 30)
        self.assertEqual(len(env.resultados_por_handle.get(9203, [])), 30)
        self.assertTrue(os.path.isfile(os.path.join(self.cache_dir, 'recent-movies-30.json')))
        self.assertTrue(os.path.isfile(os.path.join(self.cache_dir, 'recent-series-30.json')))

    def test_tentativa_2_reentrada_na_home_usa_daily_cache_sem_rede_e_sem_travar(self):
        """2a tentativa: voltar para a Home no mesmo dia le do disco instantaneamente."""
        env = _AmbienteHomeAndroidReal(self.cache_dir, qtd_filmes=35, qtd_series=32)
        plugin = self._carregar_plugin(env)

        plugin.recent_movies(101)
        plugin.recent_series(102)
        self.assertIs(env.end_por_handle.get(101), True)
        self.assertIs(env.end_por_handle.get(102), True)

        # Desliga completamente RPC e HTTP: a segunda ida para a Home precisa ler 100% do cache!
        def proibido(*_a, **_k):
            raise AssertionError('Nao deveria chamar rede quando o cache diario ja existe!')

        env.xbmc_broken = True
        sys.modules['xbmc'].executeJSONRPC = proibido
        sys.modules['search'].download = proibido

        plugin.recent_movies(201)
        plugin.recent_series(202)
        self.assertIs(env.end_por_handle.get(201), True)
        self.assertIs(env.end_por_handle.get(202), True)
        self.assertEqual(len(env.resultados_por_handle.get(201, [])), 30)
        self.assertEqual(len(env.resultados_por_handle.get(202, [])), 30)

    def test_tentativa_3_upgrade_com_cache_antigo_e_abertura_simultanea_da_home_e_18_itens(self):
        """3a tentativa: cache antigo da 1.0.149 + abertura concorrente de 9201/9203 + pasta <30."""
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(os.path.join(self.cache_dir, 'recent-movies.json'), 'w', encoding='utf-8') as fh:
            json.dump({'version': 1, 'date': '2026-11-18', 'value': [{'antigo': i} for i in range(8)]}, fh)
        with open(os.path.join(self.cache_dir, 'recent-series.json'), 'w', encoding='utf-8') as fh:
            json.dump({'version': 1, 'date': '2026-11-18', 'value': [[{'antigo': i} for i in range(10)], []]}, fh)

        env = _AmbienteHomeAndroidReal(self.cache_dir, qtd_filmes=18, qtd_series=18)
        plugin = self._carregar_plugin(env)

        erros = []

        def rodar(fn, handle):
            try:
                fn(handle)
            except Exception as exc:  # pragma: no cover
                erros.append(exc)

        t1 = threading.Thread(target=rodar, args=(plugin.recent_movies, 9201))
        t2 = threading.Thread(target=rodar, args=(plugin.recent_series, 9203))
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        self.assertEqual(erros, [])
        self.assertIs(env.end_por_handle.get(9201), True)
        self.assertIs(env.end_por_handle.get(9203), True)
        self.assertEqual(len(env.resultados_por_handle.get(9201, [])), 18)
        self.assertEqual(len(env.resultados_por_handle.get(9203, [])), 18)


if __name__ == '__main__':
    unittest.main()
