# -*- coding: utf-8 -*-
"""Teste estatico rapido (XML + py_compile) que substitui o emulador no build."""
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/kodi/static-check.py'
FLUXO = ROOT / '.github/workflows/build-release-apk.yml'


def carregar():
    spec = importlib.util.spec_from_file_location('static_check', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RepositorioTest(unittest.TestCase):
    def test_skin_e_scripts_do_repositorio_passam(self):
        resultado = subprocess.run([sys.executable, str(SCRIPT), '--quiet'],
                                   capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_roda_em_menos_de_30_segundos(self):
        inicio = time.time()
        subprocess.run([sys.executable, str(SCRIPT), '--quiet'], capture_output=True)
        self.assertLess(time.time() - inicio, 30)


class DeteccaoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = pathlib.Path(self.tmp.name)
        (self.raiz / 'kodi').mkdir()
        (self.raiz / 'tools').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _rodar(self):
        return subprocess.run([sys.executable, str(SCRIPT), '--quiet',
                               '--root=%s' % self.raiz], capture_output=True, text=True)

    def test_xml_invalido_falha(self):
        (self.raiz / 'kodi' / 'quebrado.xml').write_text('<window><control></window>')
        self.assertEqual(self._rodar().returncode, 1)

    def test_python_invalido_falha(self):
        (self.raiz / 'tools' / 'quebrado.py').write_text('def x(:\n')
        self.assertEqual(self._rodar().returncode, 1)

    def test_arvore_valida_passa(self):
        (self.raiz / 'kodi' / 'ok.xml').write_text('<window><control/></window>')
        (self.raiz / 'tools' / 'ok.py').write_text('VALOR = 1\n')
        self.assertEqual(self._rodar().returncode, 0)


class WorkflowTest(unittest.TestCase):
    def test_fluxo_roda_o_teste_estatico_antes_do_build(self):
        fluxo = FLUXO.read_text(encoding='utf-8')
        self.assertIn('tools/kodi/static-check.py', fluxo)
        self.assertLess(fluxo.index('static-check.py'), fluxo.index('build-release-apk.py --from-version'))

    def test_fluxo_de_release_nao_usa_emulador(self):
        fluxo = FLUXO.read_text(encoding='utf-8').lower()
        for proibido in ('emulator', 'avd', 'kvm', 'x86_64'):
            self.assertNotIn(proibido, fluxo)


if __name__ == '__main__':
    unittest.main()
