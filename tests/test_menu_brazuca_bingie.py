# -*- coding: utf-8 -*-
"""Menu superior da skin SMARTEDTV (base Bingie) integrado ao Brazuca Play."""
import importlib.util
import os
import pathlib
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERLAY = ROOT / 'kodi/skin.smartedtv.bingie'
MENU = OVERLAY / 'xml/script-skinshortcuts-includes.xml'
HOME = OVERLAY / 'xml/Home.xml'
BUILD = ROOT / 'tools/kodi/build-release-apk.py'
FLUXO = ROOT / '.github/workflows/build-release-apk.yml'

# Home com VOD do Brazuca Play + TV ao vivo na primeira aba
CATEGORIAS = ['TV ao vivo', 'Filmes', 'Séries', 'Novelas', 'Animes', 'Doramas', 'Desenhos']


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def itens_do_menu():
    raiz = ET.parse(MENU).getroot()
    for include in raiz.findall('include'):
        if include.get('name') == 'skinshortcuts-mainmenu':
            return include.findall('item')
    raise AssertionError('include skinshortcuts-mainmenu ausente')


class MenuSuperiorTest(unittest.TestCase):
    def test_overlay_existe_e_e_xml_valido(self):
        self.assertTrue(MENU.is_file() and HOME.is_file())
        ET.parse(MENU)
        ET.parse(HOME)

    def test_sete_categorias_na_barra_superior(self):
        rotulos = [i.findtext('label') for i in itens_do_menu()]
        for categoria in CATEGORIAS:
            self.assertIn(categoria, rotulos)

    def test_cada_categoria_abre_a_rota_do_brazuca(self):
        acoes = {i.findtext('label'): i.findtext('onclick') for i in itens_do_menu()}
        esperado = {'TV ao vivo': 'mode=21', 'Filmes': 'mode=27', 'Séries': 'mode=27',
                    'Novelas': 'mode=25', 'Animes': 'mode=22', 'Doramas': 'mode=31',
                    'Desenhos': 'mode=28'}
        for categoria, modo in esperado.items():
            self.assertIn('plugin.video.BrazucaPlay.Matrix', acoes[categoria], categoria)
            self.assertIn(modo, acoes[categoria], categoria)

    def test_menu_apenas_busca_ajustes_e_sair(self):
        rotulos = [i.findtext('label') for i in itens_do_menu()]
        self.assertEqual(len(rotulos), len(CATEGORIAS) + 3, rotulos)
        self.assertIn('Busca', rotulos)
        self.assertIn('Ajustes', rotulos)
        self.assertIn('Sair', rotulos)
        self.assertNotIn('Add-ons', rotulos)

    def test_sem_botao_de_addons(self):
        self.assertNotIn('ActivateWindow(10040', MENU.read_text(encoding='utf-8'))

    def test_home_nao_regera_o_menu(self):
        self.assertNotIn('type=buildxml', HOME.read_text(encoding='utf-8'))

    def test_tv_ao_vivo_continua_na_home(self):
        texto = MENU.read_text(encoding='utf-8')
        self.assertIn('TV ao vivo', texto)
        self.assertIn('mode=21', texto)
        self.assertIn('menu_canais', texto)
        self.assertIn('route=carrossel&amp;alvo=canais', texto)

    def test_carrosseis_usam_rotas_do_smarted(self):
        texto = MENU.read_text(encoding='utf-8')
        self.assertIn('route=recent-movies', texto)
        for alvo in ('filmes', 'series', 'novelas', 'animes', 'doramas', 'desenhos'):
            self.assertIn('route=carrossel&amp;alvo=' + alvo, texto)

    def test_widgets_legados_nao_sao_chamados(self):
        texto = MENU.read_text(encoding='utf-8')
        self.assertNotIn('plugin://script.skin.helper.widgets/', texto)
        self.assertNotIn('plugin://plugin.video.themoviedb.helper', texto)
        self.assertNotIn('special://skin/playlists/', texto)


class BuildOverlayTest(unittest.TestCase):
    def test_build_aplica_overlay_na_skin_padrao(self):
        script = BUILD.read_text(encoding='utf-8')
        self.assertIn('--skin-overlay', script)
        self.assertIn('Overlay aplicado na skin padrao', script)

    def test_workflow_publica_versao_com_overlay(self):
        fluxo = FLUXO.read_text(encoding='utf-8')
        self.assertIn('--skin-overlay kodi/skin.smartedtv.bingie', fluxo)
        self.assertIn('--to-version 1.0.52', fluxo)
        self.assertIn('v1.0.52-smarted-arm64', fluxo)


class BootstrapMenuTest(unittest.TestCase):
    """O bootstrap limpa o menu antigo e recarrega a skin uma unica vez."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(self.tmp.name)
        perfil = base / 'addon_data'
        (perfil / 'script.skinshortcuts').mkdir(parents=True)
        (perfil / 'script.skinshortcuts' / 'skin.novatv.DATA.xml').write_text('<x/>')
        (perfil / 'script.skinshortcuts' / 'outra.DATA.xml').write_text('<x/>')
        self.perfil = perfil

        xbmcvfs = types.ModuleType('xbmcvfs')
        xbmcvfs.translatePath = lambda p: p.replace('special://profile/', str(base) + '/')
        xbmcvfs.exists = os.path.exists
        xbmcvfs.listdir = lambda p: ([''], sorted(os.listdir(p)) if os.path.isdir(p) else [], [])
        xbmcvfs.delete = os.remove
        xbmcvfs.mkdirs = lambda p: os.makedirs(p, exist_ok=True)

        class Arquivo:
            def __init__(self, caminho, modo):
                self.fh = open(caminho, modo)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                self.fh.close()

            def write(self, dado):
                self.fh.write(dado)

        xbmcvfs.File = Arquivo
        xbmc = types.ModuleType('xbmc')
        self.builtins_chamados = []
        xbmc.executebuiltin = self.builtins_chamados.append
        sys.modules['xbmcvfs'] = xbmcvfs
        sys.modules['xbmc'] = xbmc

        spec = importlib.util.spec_from_file_location(
            'menu_smarted',
            ROOT / 'kodi/addons/service.smarted.bootstrap/menu_smarted.py')
        self.modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.modulo)

    def tearDown(self):
        sys.modules.pop('xbmc', None)
        sys.modules.pop('xbmcvfs', None)
        self.tmp.cleanup()

    def test_primeira_execucao_limpa_menu_e_recarrega(self):
        resultado = self.modulo.garantir_menu(log=lambda *a, **k: None)
        self.assertTrue(resultado['applied'])
        self.assertIn('skin.novatv.DATA.xml', resultado['removed'])
        self.assertTrue((self.perfil / 'script.skinshortcuts' / 'outra.DATA.xml').exists())
        self.assertIn('ReloadSkin()', self.builtins_chamados)

    def test_segunda_execucao_nao_repete(self):
        self.modulo.garantir_menu(log=lambda *a, **k: None)
        self.builtins_chamados.clear()
        resultado = self.modulo.garantir_menu(log=lambda *a, **k: None)
        self.assertFalse(resultado['applied'])
        self.assertEqual(self.builtins_chamados, [])


if __name__ == '__main__':
    unittest.main()
