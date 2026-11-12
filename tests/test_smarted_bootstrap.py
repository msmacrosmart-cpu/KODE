"""Testes do serviço de boot que garante o Brazuca Play registrado.

Cobrem o caminho que o usuário reportou: perfil semeado sem o addon instalado
(o Kodi mostrava "o addon não pôde ser carregado" e a interface abria vazia).
"""
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'repair.py'
PAYLOAD = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'payload' / 'cloudrequest-py3.zip'
ADDON_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<addon id="{id}" version="1.0.0" name="{id}" provider-name="test">
  <requires>
{requires}
  </requires>
  <extension point="xbmc.python.pluginsource" library="{library}">
    <provides>video</provides>
  </extension>
</addon>
'''

spec = importlib.util.spec_from_file_location('smarted_repair', MODULE_PATH)
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


def make_package(path, addon_id, requires=(), library='default.py'):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = ''.join('    <import addon="%s"/>' % r for r in requires)
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('%s/addon.xml' % addon_id,
                         ADDON_XML.format(id=addon_id, requires=body, library=library))
        archive.writestr('%s/%s' % (addon_id, library), '# plugin\n')


class RepairTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / '.kodi'
        self.addons = self.home / 'addons'
        self.packages = self.addons / 'packages'
        self.packages.mkdir(parents=True)
        (self.home / 'userdata').mkdir()

    def test_restaura_addon_ausente_a_partir_do_pacote(self):
        make_package(self.packages / 'plugin.video.BrazucaPlay.Matrix-2.1.4.zip',
                     repair.BRAZUCA_ID, requires=['script.module.requests'])
        make_package(self.packages / 'script.module.requests-2.31.0.zip',
                     'script.module.requests')
        log = []
        report = repair.repair_profile(str(self.home), str(ROOT / 'nope'), log)
        self.assertTrue(report['ok'], report['log'])
        self.assertIn(repair.BRAZUCA_ID, report['repaired'])
        self.assertTrue((self.addons / repair.BRAZUCA_ID / 'default.py').is_file())
        self.assertTrue((self.home / 'userdata' / 'addon_data' /
                         repair.BRAZUCA_ID).is_dir())

    def test_addon_corrompido_e_reinstalado(self):
        target = self.addons / repair.BRAZUCA_ID
        target.mkdir(parents=True)
        (target / 'addon.xml').write_text('<addon id="outro"/>')
        make_package(self.packages / 'plugin.video.BrazucaPlay.Matrix-2.1.4.zip',
                     repair.BRAZUCA_ID)
        report = repair.repair_profile(str(self.home), str(ROOT / 'nope'))
        self.assertTrue(report['ok'], report['log'])
        self.assertEqual(repair.addon_status(str(self.addons), repair.BRAZUCA_ID)[0], True)

    def test_sem_pacote_reporta_faltando_sem_inventar(self):
        report = repair.repair_profile(str(self.home), str(ROOT / 'nope'))
        self.assertFalse(report['ok'])
        self.assertIn(repair.BRAZUCA_ID, report['missing'])
        self.assertFalse((self.addons / repair.BRAZUCA_ID).exists())

    def test_pacote_com_path_traversal_e_recusado(self):
        package = self.packages / 'plugin.video.BrazucaPlay.Matrix-2.1.4.zip'
        with zipfile.ZipFile(package, 'w') as archive:
            archive.writestr('%s/addon.xml' % repair.BRAZUCA_ID, '<addon id="x"/>')
            archive.writestr('%s/../../evil.py' % repair.BRAZUCA_ID, 'boom')
        report = repair.repair_profile(str(self.home), str(ROOT / 'nope'))
        self.assertFalse(report['ok'])
        self.assertFalse((Path(self.tmp.name) / 'evil.py').exists())

    def test_dependencias_obrigatorias_sao_seguidas(self):
        make_package(self.packages / 'plugin.video.BrazucaPlay.Matrix-2.1.4.zip',
                     repair.BRAZUCA_ID, requires=['script.module.six'])
        make_package(self.packages / 'script.module.six-1.16.0.zip', 'script.module.six')
        report = repair.repair_profile(str(self.home), str(ROOT / 'nope'))
        self.assertIn('script.module.six', report['required'])
        self.assertIn('script.module.six', report['repaired'])

    def test_cloudrequest_embutido_e_descompactado(self):
        make_package(self.packages / 'plugin.video.BrazucaPlay.Matrix-2.1.4.zip',
                     repair.BRAZUCA_ID)
        report = repair.repair_profile(str(self.home), str(PAYLOAD.parent))
        self.assertTrue(report['ok'], report['log'])
        addon_path = self.addons / repair.BRAZUCA_ID
        self.assertTrue(repair.cloudrequest_ready(str(addon_path)))
        self.assertTrue((addon_path / 'cloudrequest' / 'requests_toolbelt' /
                         '__init__.py').is_file())

    def test_perfil_intacto_quando_tudo_esta_instalado(self):
        make_package(self.packages / 'plugin.video.BrazucaPlay.Matrix-2.1.4.zip',
                     repair.BRAZUCA_ID)
        repair.repair_profile(str(self.home), str(PAYLOAD.parent))
        marker = self.addons / repair.BRAZUCA_ID / 'addon.xml'
        before = marker.stat().st_mtime_ns
        report = repair.repair_profile(str(self.home), str(PAYLOAD.parent))
        self.assertTrue(report['ok'])
        self.assertEqual(report['repaired'], [])
        self.assertEqual(marker.stat().st_mtime_ns, before)


class ShippedEnvironmentTest(unittest.TestCase):
    """O addon de bootstrap precisa ir para o APK com o payload junto."""

    def test_addon_declara_servico_de_startup(self):
        xml = (ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'addon.xml').read_text()
        self.assertIn('point="xbmc.service"', xml)
        self.assertIn('start="startup"', xml)
        self.assertIn('library="service.py"', xml)

    def test_payload_cloudrequest_presente_e_valido(self):
        self.assertTrue(PAYLOAD.is_file(), PAYLOAD)
        with zipfile.ZipFile(PAYLOAD) as archive:
            names = archive.namelist()
        self.assertIn('cloudrequest/requests_toolbelt/__init__.py', names)
        self.assertIn('cloudrequest/__init__.py', names)

    def test_build_injeta_o_servico(self):
        build = (ROOT / 'tools' / 'kodi' / 'build-release-apk.py').read_text()
        self.assertIn('service.smarted.bootstrap', build)


if __name__ == '__main__':
    unittest.main()
