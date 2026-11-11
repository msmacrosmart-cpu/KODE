"""Contratos da skin para celular/HD: addons, Ajustes e tela cheia.

Três defeitos relatados em 2026-11-11 (log do Kodi + screenshot do aparelho):

1. ``plugin.video.BrazucaPlay.Matrix`` quebrava com
   ``TypeError: quote_from_bytes() expected bytes`` ao abrir Filmes/Séries. A
   causa não é o addon: a skin abria o plugin só com ``mode``/``url``/``name``,
   então ``iconimage``/``fanart`` chegavam ``None`` e o ``addDir`` do plugin
   chamava ``quote_plus(None)``. Toda URL da skin precisa levar os dois.
2. Ajustes tinha ``Skin.SetSetting`` (builtin inexistente no Kodi 21) e uma
   grade de 4 colunas que estourava a borda inferior.
3. A tela não preenchia a largura (faixa vazia à direita): vários controles com
   ``<width>1920</width>`` fixo num canvas que, no aparelho, é a resolução real
   do display (2400x1080).
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest
from urllib.parse import unquote_plus
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SKIN = ROOT / 'kodi/skin.estilo.personalizado'
XML = SKIN / 'xml'
BOOTSTRAP = ROOT / 'kodi/addons/service.smarted.bootstrap'
RUNNER = ROOT / 'tests/kodi_plugin_stubs/run_plugin.py'
PROFILE = os.environ.get('SMARTED_PROFILE', '')

PLUGIN_PREFIX = 'plugin://plugin.video.BrazucaPlay.Matrix/'
FULL_BLEED = re.compile(r'<left>0</left><top>0</top><width>1920</width><height>1080</height>')


def skin_xml_files():
    return sorted(XML.glob('*.xml'))


class PluginCallTest(unittest.TestCase):
    def test_toda_chamada_do_plugin_leva_iconimage_e_fanart(self):
        found = 0
        for path in skin_xml_files():
            text = path.read_text(encoding='utf-8')
            for url in re.findall(re.escape(PLUGIN_PREFIX) + r'\?[^"\'()\s]*', text):
                found += 1
                self.assertIn('iconimage=', url, '%s: %s' % (path.name, url))
                self.assertIn('fanart=', url, '%s: %s' % (path.name, url))
        self.assertGreaterEqual(found, 20, 'esperava as chamadas do plugin na skin')

    def test_plugin_nao_quebra_sem_dados_opcionais(self):
        """Documenta o bug: sem iconimage/fanart o addon estoura TypeError."""
        if not (PROFILE and Path(PROFILE).is_dir()):
            self.skipTest('defina SMARTED_PROFILE com um perfil .kodi semeado')
        result = subprocess.run(
            [sys.executable, str(RUNNER), PROFILE, 'mode=27&url=%23filmes_menu&name=Filmes'],
            capture_output=True, text=True, timeout=600)
        self.assertIn('quote_from_bytes', result.stdout)

    def test_url_da_skin_abre_o_menu_de_filmes(self):
        if not (PROFILE and Path(PROFILE).is_dir()):
            self.skipTest('defina SMARTED_PROFILE com um perfil .kodi semeado')
        home = (XML / 'Home.xml').read_text(encoding='utf-8')
        url = re.search(re.escape(PLUGIN_PREFIX) + r'\?mode=27&amp;url=%23filmes_menu[^"]*', home)
        self.assertIsNotNone(url, 'botão Filmes ausente do Home')
        query = url.group(0).split('?', 1)[1].replace('&amp;', '&')
        self.assertIn('iconimage=', query)
        result = subprocess.run(
            [sys.executable, str(RUNNER), PROFILE, query],
            capture_output=True, text=True, timeout=600)
        self.assertIn('RUN OK', result.stdout, result.stdout[-1500:])
        self.assertIn('PESQUISE POR FILMES', result.stdout)


class SecretUnlockTest(unittest.TestCase):
    def test_sem_builtin_inexistente_na_skin(self):
        for path in skin_xml_files():
            text = re.sub(r'<!--.*?-->', '', path.read_text(encoding='utf-8'), flags=re.S)
            self.assertNotIn('Skin.SetSetting', text, path.name)
            self.assertNotIn('Skin.GetSetting', text, path.name)

    def test_contadores_passam_pelo_addon_ponte(self):
        home = (XML / 'Home.xml').read_text(encoding='utf-8')
        self.assertIn('RunScript(service.smarted.bootstrap,secret-click)', home)
        settings = (XML / 'Settings.xml').read_text(encoding='utf-8')
        self.assertIn('RunScript(service.smarted.bootstrap,secret-cycle)', settings)
        self.assertIn('<onload>RunScript(service.smarted.bootstrap,secret-cycle)</onload>', settings)

    def test_check_py_implementa_os_comandos(self):
        source = (BOOTSTRAP / 'check.py').read_text(encoding='utf-8')
        for command in ('secret-click', 'secret-cycle', 'secret-reset'):
            self.assertIn(command, source)
        self.assertIn('Skin.SetString(', source)


class SettingsScreenTest(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(XML / 'Settings.xml').getroot()

    def test_grade_ancorada_nas_quatro_bordas(self):
        panel = self.root.find(".//control[@id='9000']")
        self.assertIsNotNone(panel)
        self.assertIsNotNone(panel.find('right'), 'painel precisa de <right> para esticar')
        self.assertIsNotNone(panel.find('bottom'), 'painel precisa de <bottom> para não cortar')
        self.assertIsNone(panel.find('height'), 'altura fixa corta a última linha')

    def test_todo_item_tem_icone(self):
        items = self.root.findall(".//control[@id='9000']/content/item")
        self.assertGreaterEqual(len(items), 12)
        for item in items:
            label = item.findtext('label')
            icon = item.findtext('icon')
            self.assertTrue(icon, 'item sem ícone: %s' % label)
            self.assertTrue((SKIN / 'media' / icon).is_file(), icon)

    def test_tiles_cabem_na_tela(self):
        includes = ET.parse(XML / 'Includes.xml').getroot()
        tile = includes.find(".//include[@name='SettingsTile']")
        self.assertIsNotNone(tile, 'include SettingsTile ausente')
        for name in ('itemlayout', 'focusedlayout'):
            layout = tile.find(name)
            self.assertIsNotNone(layout, name)
            self.assertEqual(layout.get('width'), '320')
            self.assertEqual(layout.get('height'), '180')

    def test_cabecalho_nao_sobrepoe(self):
        ids = {c.get('id'): c for c in self.root.iter('control') if c.get('id')}
        voltar = ids['9050']
        self.assertEqual(voltar.findtext('top'), '40')
        self.assertEqual(voltar.findtext('left'), '60')
        titulo = [c for c in self.root.iter('control')
                  if c.get('type') == 'label' and (c.findtext('label') or '') == 'AJUSTES']
        self.assertTrue(titulo)
        self.assertEqual(titulo[0].findtext('left'), '240')


class FullScreenTest(unittest.TestCase):
    def test_resolucao_unica_1080p(self):
        addon = ET.parse(SKIN / 'addon.xml').getroot()
        resolutions = list(addon.iter('res'))
        self.assertEqual(len(resolutions), 1, 'mais de um <res> desalinha o canvas')
        self.assertEqual(resolutions[0].get('width'), '1920')
        self.assertEqual(resolutions[0].get('height'), '1080')
        self.assertEqual(resolutions[0].get('default'), 'true')

    def test_sem_fundo_fixo_de_1920(self):
        for path in skin_xml_files():
            text = path.read_text(encoding='utf-8')
            self.assertIsNone(FULL_BLEED.search(text), path.name)

    def test_fundos_usam_porcentagem(self):
        home = (XML / 'Home.xml').read_text(encoding='utf-8')
        self.assertIn('<width>100%</width><height>100%</height>', home)

    def test_barra_superior_ancorada_a_direita(self):
        root = ET.parse(XML / 'Home.xml').getroot()
        for control_id in ('9121', '9122', '9123'):
            node = root.find(".//control[@id='%s']" % control_id)
            self.assertIsNotNone(node, control_id)
            self.assertIsNotNone(node.find('right'), '%s precisa de <right>' % control_id)

    def test_listas_do_home_esticam_ate_a_borda(self):
        root = ET.parse(XML / 'Home.xml').getroot()
        for control_id in ('9200', '9210', '9220'):
            node = root.find(".//control[@id='%s']" % control_id)
            if node is None:
                continue
            self.assertIsNotNone(node.find('right'), '%s precisa de <right>' % control_id)


if __name__ == '__main__':
    unittest.main()
