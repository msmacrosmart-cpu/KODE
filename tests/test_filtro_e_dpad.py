# -*- coding: utf-8 -*-
"""Filtro da tela de pastas, ordenacao real e d-pad das telas de pastas/ajustes.

Dois defeitos que o cliente via como "nao da para navegar" e "o filtro nao
funciona", com causa raiz no Kodi 21 (nao no layout):

1. ``Container.SetSortMethod(id)`` -> ``GUI_MSG_CHANGE_SORT_METHOD`` ->
   ``CGUIViewState::SetCurrentSortMethod`` so aplica o metodo se o ``id``
   existir em ``m_sortMethods``. Diretorio de plugin nasce com um unico
   metodo, ``SortByNone`` (``CPluginDirectory::EndOfDirectory``). Logo os
   botoes "Todos/A a Z/..." nao mudavam nada.
2. ``CGUIWindow::OnMove`` ignora um destino igual ao controle atual e, se o
   ``onup``/``ondown`` do container aponta para fora quando o container ainda
   tem itens, o foco nunca percorre a lista. As setas tem de sair do container
   apenas quando nao ha mais item naquela direcao -- e a vista visivel (50/51/
   52) precisa ser considerada, senao o alvo aponta para um controle invisivel.
"""
import pathlib
import sys
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'kodi/addons/plugin.video.smarted'
XML = ROOT / 'kodi/skin.estilo.personalizado/xml'
XML_ESPELHO = ROOT / 'kodi/skin.novatv/xml'

sys.path.insert(0, str(PLUGIN))


def carregar(nome, caminho):
    """Importa um modulo do plugin com nome unico (sem poluir sys.modules)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(nome, str(caminho))
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class OrdenacaoTest(unittest.TestCase):
    def setUp(self):
        self.ordering = carregar('ordering_teste', PLUGIN / 'ordering.py')
        self.itens = [
            {'label': 'Canal B', 'url': 'u-b', 'votes': 10, 'rating': 7.0,
             'dateadded': '2024-01-02', 'premiered': '2024-01-02'},
            {'label': 'Canal A', 'url': 'u-a', 'votes': 900, 'rating': 6.5,
             'dateadded': '2025-03-04', 'premiered': '2025-03-04'},
            {'label': 'Canal C', 'url': 'u-c', 'votes': 5, 'rating': 8.5,
             'dateadded': '2023-12-31', 'premiered': '2023-12-31'},
        ]

    def rotulos(self, ordem):
        return [item['label'] for item in self.ordering.aplicar(self.itens, ordem)]

    def test_todos_preserva_a_ordem_do_addon(self):
        self.assertEqual(self.rotulos('todos'), ['Canal B', 'Canal A', 'Canal C'])

    def test_az_e_za_invertem_de_verdade(self):
        self.assertEqual(self.rotulos('az'), ['Canal A', 'Canal B', 'Canal C'])
        self.assertEqual(self.rotulos('za'), ['Canal C', 'Canal B', 'Canal A'])

    def test_mais_votados_usa_os_votos_reais(self):
        self.assertEqual(self.rotulos('votados'), ['Canal A', 'Canal B', 'Canal C'])

    def test_adicionados_e_recentes_olham_a_data(self):
        self.assertEqual(self.rotulos('adicionados'), ['Canal A', 'Canal B', 'Canal C'])
        self.assertEqual(self.rotulos('recentes'), ['Canal A', 'Canal B', 'Canal C'])

    def test_ordem_desconhecida_nao_quebra(self):
        self.assertEqual(self.rotulos('qualquer-coisa'), self.rotulos('todos'))
        self.assertEqual(self.rotulos(''), self.rotulos('todos'))
        self.assertEqual(self.ordering.aplicar(None, 'az'), [])

    def test_url_da_rota_aceita_pasta_nativa_e_ja_reordenada(self):
        nativa = 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23filmes_menu'
        primeira = self.ordering.url_da_rota(nativa, 'az')
        self.assertIn('route=pasta', primeira)
        self.assertIn('ordem=az', primeira)
        # trocar de ordem nao pode empilhar parametros na propria rota
        segunda = self.ordering.url_da_rota(primeira, 'votados')
        self.assertIn('ordem=votados', segunda)
        self.assertEqual(segunda.count('route=pasta'), 1)
        self.assertNotIn('ordem=az', segunda)

    def test_paginas_do_addon_nao_sao_reordenadas(self):
        # rota propria do app (ex.: filmes, busca) nao e pasta do Brazuca
        self.assertEqual(self.ordering.url_da_rota(
            'plugin://plugin.video.smarted/?route=movies', 'az'), '')


class RotasDoPluginTest(unittest.TestCase):
    """`route=ordenar` e `route=pasta` respondem com itens reais."""

    def setUp(self):
        import types
        self.chamadas = []
        self.fins = []
        self.itens = []
        falso = types.ModuleType('xbmcplugin')
        falso.SORT_METHOD_UNSORTED = -1
        falso.setContent = lambda handle, tipo: None
        falso.addSortMethod = lambda handle, metodo: None
        falso.addDirectoryItem = lambda handle, url, item, isFolder: self.itens.append(
            (item.getLabel() if hasattr(item, 'getLabel') else url, url, isFolder))
        falso.endOfDirectory = lambda handle, succeeded=True, cacheToDisc=False: \
            self.fins.append(succeeded)
        gui = types.ModuleType('xbmcgui')
        gui.ListItem = lambda label='': type('Item', (), {
            'getLabel': lambda s: label,
            'setArt': lambda s, art: None,
            'setProperty': lambda s, k, v: None,
            'getVideoInfoTag': lambda s: type('Info', (), {
                'setTitle': lambda s, v: None, 'setPlot': lambda s, v: None,
                'setYear': lambda s, v: None, 'setGenres': lambda s, v: None,
                'setPremiered': lambda s, v: None, 'setRating': lambda s, v: None,
                'setMediaType': lambda s, v: None})(),
        })()
        self.kodi = types.ModuleType('xbmc')
        self.kodi.LOGWARNING, self.kodi.LOGINFO = 30, 20
        self.kodi.log = lambda *a, **k: None
        self.kodi.getInfoLabel = lambda rotulo: self.pasta
        self.kodi.executebuiltin = self.chamadas.append
        self.kodi.executeJSONRPC = lambda pedido: self._resposta(pedido)
        self.pasta = ''
        self.modules = {'xbmc': self.kodi, 'xbmcgui': gui, 'xbmcplugin': falso}

    def _resposta(self, pedido):
        import json
        return json.dumps({'jsonrpc': '2.0', 'id': 1, 'result': {'files': [
            {'label': 'Canal B', 'file': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=11&url=b',
             'filetype': 'file', 'votes': 10, 'dateadded': '2024-01-01'},
            {'label': 'Canal A', 'file': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=11&url=a',
             'filetype': 'file', 'votes': 99, 'dateadded': '2025-01-01'}]}})

    def _default(self):
        return carregar('bridge_default_teste', PLUGIN / 'default.py')

    def test_ordenar_reabre_a_pasta_com_a_ordem_pedida(self):
        self.pasta = 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23x'
        with patch.dict(sys.modules, self.modules):
            self._default().sort_folder(1, {'ordem': ['az']})
        atualizacoes = [c for c in self.chamadas if c.startswith('Container.Update(')]
        self.assertEqual(len(atualizacoes), 1, self.chamadas)
        self.assertIn('route=pasta', atualizacoes[0])
        self.assertIn('ordem=az', atualizacoes[0])

    def test_ordenar_fora_de_pasta_do_addon_nao_faz_nada(self):
        self.pasta = 'plugin://plugin.video.smarted/?route=movies'
        with patch.dict(sys.modules, self.modules):
            self._default().sort_folder(1, {'ordem': ['az']})
        self.assertEqual([c for c in self.chamadas if c.startswith('Container.Update(')], [])

    def test_ordenar_na_mesma_ordem_nao_recarrega(self):
        self.pasta = ('plugin://plugin.video.smarted/?route=pasta&ordem=az&url='
                      'plugin%3A%2F%2Fplugin.video.BrazucaPlay.Matrix%2F%3Fmode%3D27')
        with patch.dict(sys.modules, self.modules):
            self._default().sort_folder(1, {'ordem': ['az']})
        self.assertEqual([c for c in self.chamadas if c.startswith('Container.Update(')], [])

    def test_pasta_devolve_os_itens_na_ordem_escolhida(self):
        with patch.dict(sys.modules, self.modules):
            self._default().folder_window(1, {
                'url': ['plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23x'],
                'ordem': ['az']})
        rotulos = [item[0] for item in self.itens]
        self.assertEqual(rotulos, ['Canal A', 'Canal B'])
        # a URL nativa do addon continua sendo a do item (nada e inventado)
        self.assertIn('url=a', self.itens[0][1])


class DpadDasTelasTest(unittest.TestCase):
    """Grafo de foco: nenhum beco sem saida e nenhum alvo invisivel."""

    ARQUIVOS = (XML / 'MyVideoNav.xml', XML / 'Settings.xml')

    def setUp(self):
        sys.path.insert(0, str(ROOT / 'tools/kodi'))
        self.auditor = carregar('auditor_foco', ROOT / 'tools/kodi/check-foco-skin.py')

    def test_todas_as_telas_tem_dpad_completo(self):
        for caminho in self.ARQUIVOS:
            padrao, vistos, arestas, alcancados, problemas = self.auditor.audita(str(caminho))
            self.assertIsNotNone(padrao, caminho.name)
            self.assertEqual([p for p in problemas if p[0] == 'SEM SAIDA'], [], caminho.name)
            self.assertEqual([p for p in problemas if p[0] == 'INALCANCAVEL'], [], caminho.name)
            self.assertEqual(set(vistos), alcancados, caminho.name)

    def test_as_duas_skins_continuam_iguais(self):
        for nome in ('MyVideoNav.xml', 'Settings.xml'):
            self.assertEqual((XML / nome).read_text(),
                             (XML_ESPELHO / nome).read_text(),
                             '%s: a skin espelho saiu do lugar' % nome)

    def test_grade_de_ajustes_declara_orientacao(self):
        # sem <orientation> o Kodi assume VERTICAL: um tile por linha e o d-pad
        # parecia travado na primeira fileira
        for caminho in (XML / 'Settings.xml', XML_ESPELHO / 'Settings.xml'):
            raiz = ET.parse(caminho).getroot()
            painel = raiz.find(".//control[@id='9000']")
            self.assertEqual((painel.findtext('orientation') or '').strip(), 'horizontal')

    def test_barra_de_filtros_vale_nas_duas_vistas(self):
        for caminho in (XML / 'MyVideoNav.xml', XML_ESPELHO / 'MyVideoNav.xml'):
            raiz = ET.parse(caminho).getroot()
            barra = raiz.find(".//control[@id='9060']")
            visible = (barra.findtext('visible') or '').strip()
            self.assertNotIn('Control.IsVisible(50)', visible,
                             '%s: a barra sumia na grade' % caminho.name)
            destinos = {(c.text or '').strip() for c in barra.findall('ondown')}
            self.assertIn('50', destinos)
            self.assertIn('52', destinos)

    def test_barra_inferior_e_alcancavel_pela_barra_lateral(self):
        raiz = ET.parse(XML / 'MyVideoNav.xml').getroot()
        lateral = raiz.find(".//control[@id='9000']")
        self.assertIn('9050', {(c.text or '').strip() for c in lateral.findall('ondown')})


if __name__ == '__main__':
    unittest.main()
