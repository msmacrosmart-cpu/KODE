# -*- coding: utf-8 -*-
"""Build lateral com a skin Bingie: script de download e injecao dos addons."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


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


class BuildTest(unittest.TestCase):
    def test_build_aceita_addons_extras(self):
        script = (ROOT / 'tools/kodi/build-release-apk.py').read_text(encoding='utf-8')
        self.assertIn('--extra-addons', script)
        self.assertIn('extra_addons', script)
        self.assertIn("f\"assets/addons/{addon_id}/\"", script.replace("'", '"'))

    def test_workflow_baixa_e_injeta(self):
        fluxo = (ROOT / '.github/workflows/build-release-apk.yml').read_text(encoding='utf-8')
        self.assertIn('fetch-bingie-addons.py', fluxo)
        self.assertIn('--extra-addons "$RUNNER_TEMP/extra"', fluxo)


if __name__ == '__main__':
    unittest.main()
