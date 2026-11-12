# -*- coding: utf-8 -*-
"""Skin Bingie embarcada como skin padrao SMARTEDTV: download, injecao e rename."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

BUILD = ROOT / 'tools/kodi/build-release-apk.py'
FLUXO = ROOT / '.github/workflows/build-release-apk.yml'


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch = carregar('fetch_bingie', ROOT / 'tools/kodi/fetch-bingie-addons.py')


class BingieTest(unittest.TestCase):
    def test_escolhe_a_versao_mais_nova(self):
        nomes = ['skin.titan.bingie.mod-2.2.0.zip', 'skin.titan.bingie.mod-2.2.3.zip',
                 'skin.titan.bingie.mod-2.2.10.zip', 'skin.titan.bingie.mod-2.1.9.zip']
        self.assertEqual(max(nomes, key=fetch.versao), 'skin.titan.bingie.mod-2.2.10.zip')

    def test_dependencias_ausentes_ficam_de_fora(self):
        self.assertIn('plugin.video.youtube', fetch.AUSENTES)
        self.assertEqual(fetch.SKIN, 'skin.titan.bingie.mod')


class SkinPadraoTest(unittest.TestCase):
    """A skin Bingie passa a ser a skin padrao, com nome SMARTEDTV."""

    def test_build_aceita_skin_padrao_externa(self):
        script = BUILD.read_text(encoding='utf-8')
        self.assertIn('--default-skin', script)
        self.assertIn('default_skin', script)
        self.assertIn('skin.titan.bingie.mod', script)

    def test_skin_padrao_se_chama_smartedtv(self):
        script = BUILD.read_text(encoding='utf-8')
        self.assertIn('SKIN_ADDON_ID = "skin.novatv"', script)
        self.assertIn('SKIN_NAME = "SMARTEDTV"', script)
        self.assertIn('SKIN_VERSION = "2.2.3"', script)

    def test_skin_classica_continua_embarcada(self):
        script = BUILD.read_text(encoding='utf-8')
        self.assertIn('SKIN_CLASSIC_ID = "skin.smartedtv.classic"', script)
        self.assertIn('SKIN_CLASSIC_VERSION = "1.0.17"', script)

    def test_versao_do_apk_mantem_tamanho_do_nome(self):
        """versionName vive no string pool binario: precisa do mesmo tamanho."""
        script = BUILD.read_text(encoding='utf-8')
        self.assertIn('len(new_name.encode("utf-16-le")) != len(old_name.encode("utf-16-le"))', script)

    def test_workflow_monta_a_versao_atual_com_a_skin_padrao(self):
        fluxo = FLUXO.read_text(encoding='utf-8')
        self.assertIn('fetch-bingie-addons.py', fluxo)
        self.assertIn('--extra-addons "$RUNNER_TEMP/extra"', fluxo)
        self.assertIn('--default-skin "$RUNNER_TEMP/extra/skin.titan.bingie.mod"', fluxo)
        self.assertIn('--to-version 1.0.50', fluxo)
        self.assertIn('--to-code 2103036', fluxo)
        self.assertIn('v1.0.50-smarted-arm64', fluxo)


if __name__ == '__main__':
    unittest.main()
