# -*- coding: utf-8 -*-
"""Barra superior alimentada pelos favoritos reais do Brazuca Play.

Cobre a rota ``sync-nav`` do plugin.video.smarted: leitura do MESMO
``favorites.dat`` do addon, ordem/nomes preservados, destino nativo de cada
opcao (tocar video ou abrir a pasta) e publicacao nos slots da skin.
"""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

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
search = load('search', 'search.py', {'routes': routes})
catalogue = load('catalogue', 'catalogue.py',
                 {'routes': routes, 'search': search})
navigation = load('navigation', 'navigation.py',
                  {'favorites': favorites, 'routes': routes, 'catalogue': catalogue})


def encode(value):
    return base64.b16encode(base64.b64encode(value.encode('utf-8'))).decode('ascii')


def fixture(path):
    """Mesmo formato que o Brazuca 2.1.4 grava (lista de 7 campos)."""
    data = {
        'canais': [
            ['[B][COLOR white]TV ao vivo[/COLOR][/B]', encode('#menu_canais'), 21,
             encode(''), 'DefaultFolder.png', 'DefaultFolder.png', 'Menu'],
            ['[B][COLOR white]Canal Um[/COLOR][/B]', encode('https://exemplo/um.m3u8'), 11,
             encode(''), 'https://exemplo/um.png', 'https://exemplo/um-fan.jpg', 'canal'],
        ],
        'filmes': [
            ['[B][COLOR white]Filmes Lançamentos[/COLOR][/B]', encode('#lancamentos'), 27,
             encode(''), 'DefaultFolder.png', 'DefaultFolder.png', 'Menu'],
            ['[B][COLOR white]Filme Um[/COLOR][/B]', encode('https://exemplo/filme'), 16,
             encode(''), 'https://exemplo/filme.jpg', 'https://exemplo/filme-fan.jpg', 'filme'],
        ],
        'series': [
            ['[B][COLOR white]Série Teste[/COLOR][/B]', encode('#series_list'), 6,
             encode(''), 'DefaultFolder.png', 'DefaultFolder.png', 'Menu'],
        ],
    }
    Path(path).write_text(json.dumps(data), encoding='utf-8')


def query(url):
    return parse_qs(urlsplit(url).query)


class FavoritosNaBarraTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'favorites.dat'
        fixture(self.path)
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_cada_favorito_vira_uma_opcao_na_ordem_do_addon(self):
        entradas = navigation.favorites_entries(self.path)
        self.assertEqual([e['label'] for e in entradas],
                         ['TV ao vivo', 'Canal Um', 'Filmes Lançamentos', 'Filme Um',
                          'Série Teste'])
        # rotulos limpos: nenhuma tag de cor do addon na skin
        for entrada in entradas:
            self.assertNotIn('[', entrada['label'])
            self.assertNotIn('COLOR', entrada['label'])
            self.assertLessEqual(len(entrada['label']), navigation.MAX_LABEL)

    def test_opcao_abre_o_destino_nativo_do_favorito(self):
        entradas = navigation.favorites_entries(self.path)
        pastas = [e for e in entradas if not e['playable']]
        videos = [e for e in entradas if e['playable']]
        self.assertEqual(len(pastas), 3)
        self.assertEqual(len(videos), 2)
        for entrada in pastas:
            self.assertTrue(entrada['url'].startswith('plugin://plugin.video.BrazucaPlay.Matrix/'))
            self.assertTrue(navigation.open_command(entrada).startswith('ActivateWindow(Videos,'))
        for entrada in videos:
            self.assertTrue(navigation.open_command(entrada).startswith('PlayMedia('))

    def test_modo_do_addon_e_preservado_na_url(self):
        entradas = {e['label']: e for e in navigation.favorites_entries(self.path)}
        canal = query(entradas['Canal Um']['url'])
        self.assertEqual(canal['mode'], ['11'])
        self.assertEqual(canal['url'], ['https://exemplo/um.m3u8'])
        filme = query(entradas['Filme Um']['url'])
        self.assertEqual(filme['mode'], ['16'])

    def test_arquivo_de_favoritos_fica_intocado(self):
        navigation.build(self.path)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), self.digest)


class SlotsDaSkinTest(unittest.TestCase):
    def setUp(self):
        self.chamadas = []

    def execute(self, comando):
        self.chamadas.append(comando)

    def test_publica_dez_slots_e_limpa_o_resto(self):
        entradas = [{'label': 'Opcao %d' % i, 'url': 'plugin://x/?i=%d' % i,
                     'playable': False, 'origem': 'favoritos'} for i in range(1, 4)]
        navigation.apply_skin_strings(entradas, self.execute)
        self.assertEqual(len(self.chamadas), navigation.SLOTS)
        self.assertEqual(self.chamadas[0], 'Skin.SetString(smarted_nav_1,Opcao 1)')
        self.assertEqual(self.chamadas[2], 'Skin.SetString(smarted_nav_3,Opcao 3)')
        for comando in self.chamadas[3:]:
            self.assertTrue(comando.startswith('Skin.Reset(smarted_nav_'))
            self.assertNotIn('SetString', comando)

    def test_cache_do_dia_volta_e_o_de_ontem_e_ignorado(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cache = str(Path(tmp.name) / 'navegacao.json')
        entradas = [{'label': 'TV ao vivo', 'url': 'plugin://a/?mode=21', 'playable': False,
                     'origem': 'favoritos'}]
        self.assertTrue(navigation.save_cache(cache, entradas, 'favoritos', today='2026-11-11'))
        self.assertEqual(navigation.load_cache(cache, today='2026-11-11'), entradas)
        self.assertIsNone(navigation.load_cache(cache, today='2026-11-12'))
        # aceitar_antigo serve a rota navegacao (conferencia, sem rede)
        self.assertEqual(navigation.load_cache(cache, today='2026-11-12', aceitar_antigo=True),
                         entradas)

    def test_resolve_respeita_o_indice_do_slot(self):
        entradas = [{'label': 'A', 'url': 'plugin://a', 'playable': False},
                    {'label': 'B', 'url': 'plugin://b', 'playable': False}]
        self.assertEqual(navigation.resolve(entradas, 0)['label'], 'A')
        self.assertEqual(navigation.resolve(entradas, 1)['label'], 'B')
        self.assertIsNone(navigation.resolve(entradas, 2))
        self.assertIsNone(navigation.resolve(entradas, -1))


class SemFavoritosTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'favorites.dat'

    def test_perfil_novo_usa_o_menu_do_addon(self):
        def rpc(_payload):
            return json.dumps({'result': {'files': [
                {'file': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=%23menu_canais',
                 'label': 'TV ao vivo', 'filetype': 'directory', 'fanart': '', 'thumbnail': ''},
                {'file': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23filmes_menu',
                 'label': 'Filmes', 'filetype': 'directory', 'fanart': '', 'thumbnail': ''},
            ]}})

        entradas = navigation.root_entries(rpc)
        self.assertEqual([e['label'] for e in entradas], ['TV ao vivo', 'Filmes'])
        self.assertEqual(query(entradas[1]['url'])['mode'], ['27'])

    def test_sem_rede_cai_nas_pastas_reais_do_addon(self):
        entradas, origem = navigation.build(str(self.path), None)
        self.assertEqual(origem, 'pastas')
        self.assertEqual(len(entradas), len(navigation.PASTAS))
        for entrada in entradas:
            self.assertIn('plugin.video.BrazucaPlay.Matrix', entrada['url'])
            self.assertTrue(navigation.open_command(entrada).startswith('ActivateWindow(Videos,'))

    def test_ordem_das_pastas_do_addon(self):
        modos = [query(e['url'])['mode'][0] for e in navigation.folder_entries()]
        self.assertEqual(modos, ['21', '27', '27', '25', '22', '31', '28'])


if __name__ == '__main__':
    unittest.main()
