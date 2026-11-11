# -*- coding: utf-8 -*-
"""Carrossel da Home: o resolver desce a árvore do addon até conteúdo real.

Cobrem o caminho usado pelas três linhas da Home (rota ``carrossel&alvo=…`` do
``plugin.video.smarted``): a linha não pode listar pastas de menu ("CATEGORIA:
GÊNEROS", "TODAS SÉRIES") quando existe mídia abaixo; séries param nas capas;
uma raiz indisponível cai para a alternativa; e nada volta vazio sem aviso.
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / 'kodi' / 'addons' / 'plugin.video.smarted'
PLUGIN = 'plugin://plugin.video.BrazucaPlay.Matrix/'


def load(name, filename, modules=None):
    spec = importlib.util.spec_from_file_location(name, BRIDGE / filename)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules or {}):
        spec.loader.exec_module(module)
    return module


routes = load('routes', 'routes.py')
search = load('search', 'search.py', {'routes': routes})
catalogue = load('catalogue', 'catalogue.py', {'routes': routes, 'search': search})


def item(label, mode, path, kind='directory', thumb='', plot=''):
    """Item como o addon devolve: a URL passa pelo mesmo urlencode da ponte."""
    link = routes.brazuca(mode, path)
    return {'label': label, 'file': link, 'filetype': kind,
            'thumbnail': thumb, 'plot': plot, 'year': 0}


class FakeRpc:
    """Responde Files.GetDirectory a partir de um mapa url -> itens."""

    def __init__(self, tree):
        self.tree = tree
        self.calls = []

    def __call__(self, request):
        payload = json.loads(request)
        directory = payload['params']['directory']
        self.calls.append(directory)
        entries = self.tree.get(directory)
        if entries is None:
            return json.dumps({'error': {'code': -1, 'message': 'indisponivel'}})
        return json.dumps({'result': {'files': entries}})


def url(mode, path):
    return routes.brazuca(mode, path)


class WalkTest(unittest.TestCase):
    def test_desce_ate_a_midia_e_ignora_o_menu(self):
        menu = [item('CATEGORIA: GÊNEROS', 27, '#filmes_por_generos_menu'),
                item('CATEGORIA: LANÇAMENTOS', 27, '#lancamentos'),
                item('PESQUISE POR FILMES', 20, '#pesquisar_filmes')]
        filmes = [item('Filme A', 16, 'https://exemplo/a.mp4', 'file', 'a.jpg'),
                  item('Filme B', 16, 'https://exemplo/b.mp4', 'file', 'b.jpg')]
        rpc = FakeRpc({url(27, '#filmes_menu'): menu, url(27, '#lancamentos'): filmes})
        items, found = catalogue.walk(rpc, url(27, '#filmes_menu'), depth=2,
                                      prefer=('lancamento', 'recente'))
        self.assertTrue(found)
        self.assertEqual([entry['label'] for entry in items], ['Filme A', 'Filme B'])
        self.assertTrue(all(not entry['folder'] for entry in items))
        # ramo preferido escolhido e nada alem de duas chamadas
        self.assertIn(url(27, '#lancamentos'), rpc.calls)
        self.assertNotIn(url(27, '#filmes_por_generos_menu'), rpc.calls)

    def test_series_param_nas_capas_e_nao_no_menu(self):
        menu = [item('PESQUISAR SÉRIES', 20, '#pesquisar_series'),
                item('TODAS SÉRIES', 27, '#todas_series')]
        series = [item('Série A', 26, '#serie_a'),
                  item('Série B', 26, '#serie_b')]
        rpc = FakeRpc({url(27, '#series_menu'): menu, url(27, '#todas_series'): series})
        items, found = catalogue.walk(rpc, url(27, '#series_menu'), depth=2,
                                      prefer=('todas', 'series'))
        self.assertFalse(found)  # ainda são pastas (temporadas), mas são as capas
        self.assertEqual([entry['label'] for entry in items], ['Série A', 'Série B'])
        self.assertNotIn('TODAS SÉRIES', [entry['label'] for entry in items])

    def test_raiz_indisponivel_volta_vazio(self):
        rpc = FakeRpc({})
        self.assertEqual(catalogue.walk(rpc, url(21, '#menu_canais')), ([], False))

    def test_nivel_mais_fundo_e_entregue_quando_nao_ha_midia(self):
        menu = [item('Pluto TV', 21, '#pluto_menu')]
        categorias = [item('Filmes', 21, '#plutotv_4'), item('Séries', 21, '#plutotv_12')]
        rpc = FakeRpc({url(21, '#menu_canais'): menu, url(21, '#pluto_menu'): categorias})
        items, found = catalogue.walk(rpc, url(21, '#menu_canais'), depth=2, prefer=('pluto',))
        self.assertFalse(found)
        self.assertEqual([entry['label'] for entry in items], ['Filmes', 'Séries'])


class CarouselTest(unittest.TestCase):
    def test_canais_usa_a_raiz_de_canais_quando_disponivel(self):
        canais = [item('Canal 1', 11, 'https://exemplo/c1.m3u8', 'file', 'c1.png'),
                  item('Canal 2', 11, 'https://exemplo/c2.m3u8', 'file', 'c2.png')]
        rpc = FakeRpc({url(21, '#todoscanais'): canais})
        items, origem, found = catalogue.carousel(rpc, 'canais')
        self.assertTrue(found)
        self.assertEqual(origem, '#todoscanais')
        self.assertEqual(len(items), 2)

    def test_canais_cai_para_o_menu_quando_a_raiz_falha(self):
        menu = [item('PLUTO TV', 21, '#pluto_menu')]
        categorias = [item('Filmes', 21, '#plutotv_4')]
        canais = [item('Canal X', 11, 'https://exemplo/x.m3u8', 'file', 'x.png')]
        rpc = FakeRpc({url(21, '#todoscanais'): None,
                       url(21, '#menu_canais'): menu,
                       url(21, '#pluto_menu'): categorias,
                       url(21, '#plutotv_4'): canais})
        rpc.tree[url(21, '#todoscanais')] = None
        items, origem, found = catalogue.carousel(rpc, 'canais')
        self.assertTrue(found)
        self.assertEqual(origem, '#menu_canais')
        self.assertEqual([entry['label'] for entry in items], ['Canal X'])

    def test_alvo_desconhecido_e_erro_explicito(self):
        with self.assertRaises(ValueError):
            catalogue.carousel(FakeRpc({}), 'inexistente')

    def test_nunca_inventa_item(self):
        items, origem, found = catalogue.carousel(FakeRpc({}), 'filmes')
        self.assertEqual(items, [])
        self.assertFalse(found)
        self.assertEqual(origem, '')


if __name__ == '__main__':
    unittest.main()
