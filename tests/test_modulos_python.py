# -*- coding: utf-8 -*-
"""Modulos Python de terceiros empacotados como addons (erros do log do Kodi)."""
import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'tools/kodi/vendor-python-modules.py'
FLUXO = ROOT / '.github/workflows/build-release-apk.yml'


def carregar():
    spec = importlib.util.spec_from_file_location('vendor_modulos', VENDOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ManifestoTest(unittest.TestCase):
    def setUp(self):
        self.modulo = carregar()

    def test_modulos_dos_logs_estao_na_lista(self):
        ids = {addon_id for addon_id, _ in self.modulo.MODULOS}
        for necessario in ('script.module.arrow', 'script.module.unidecode',
                           'script.module.simpleeval', 'script.module.simplejson',
                           'script.module.requests', 'script.module.dateutil'):
            self.assertIn(necessario, ids)

    def test_xbmc_nao_e_empacotado(self):
        ids = {addon_id for addon_id, _ in self.modulo.MODULOS}
        self.assertFalse(any('xbmc' in i for i in ids))

    def test_addon_xml_e_modulo_do_kodi(self):
        xml = self.modulo.ADDON_XML.format(addon_id='script.module.arrow', pacote='arrow', versao='1.3.0')
        self.assertIn('point="xbmc.python.module"', xml)
        self.assertIn('library="lib"', xml)


class VerificacaoTest(unittest.TestCase):
    """O verificador precisa pegar import sem modulo e ignorar try/except."""

    def setUp(self):
        self.modulo = carregar()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _addon(self, nome, codigo, arquivos=()):
        pasta = self.dir / nome
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / 'addon.xml').write_text('<addon id="%s"/>' % nome)
        (pasta / 'run.py').write_text(codigo)
        for rel in arquivos:
            alvo = pasta / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text('')

    def test_import_obrigatorio_sem_modulo_falha(self):
        self._addon('script.teste', 'import arrow\n')
        self.assertEqual(self.modulo.verificar(self.dir), 1)

    def test_import_protegido_por_try_nao_falha(self):
        self._addon('script.teste', 'try:\n    import arrow\nexcept ImportError:\n    arrow = None\n')
        self.assertEqual(self.modulo.verificar(self.dir), 0)

    def test_modulo_empacotado_satisfaz_o_import(self):
        self._addon('script.teste', 'import arrow\n')
        self.dir.joinpath('script.module.arrow', 'lib', 'arrow').mkdir(parents=True)
        self.dir.joinpath('script.module.arrow', 'lib', 'arrow', '__init__.py').write_text('')
        self.assertEqual(self.modulo.verificar(self.dir), 0)


class FluxoTest(unittest.TestCase):
    def test_workflow_empacota_os_modulos_antes_do_build(self):
        fluxo = FLUXO.read_text(encoding='utf-8')
        self.assertIn('vendor-python-modules.py "$RUNNER_TEMP/extra"', fluxo)
        self.assertLess(fluxo.index('vendor-python-modules.py'),
                        fluxo.index('build-release-apk.py --from-version'))
        self.assertIn('--to-version 1.0.52', fluxo)


if __name__ == '__main__':
    unittest.main()
