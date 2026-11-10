import hashlib
import importlib.util
import io
from pathlib import Path
import stat
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
SKIN = ROOT / 'kodi' / 'skin.novatv'
spec = importlib.util.spec_from_file_location('stage_profile', ROOT / 'tools/kodi/stage-profile.py')
stage_profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_profile)


class SkinContracts(unittest.TestCase):
    def test_xml_parses(self):
        xmls = list(SKIN.rglob('*.xml'))
        self.assertGreaterEqual(len(xmls), 94)
        for path in xmls:
            with self.subTest(path=path.relative_to(SKIN)):
                ET.parse(path)

    def test_settings_controls_match_kodi_21(self):
        types = {'2': 'label', '3': 'grouplist', '5': 'grouplist', '6': 'textbox',
                 '7': 'button', '8': 'radiobutton', '9': 'spincontrolex',
                 '10': 'button', '11': 'image', '12': 'edit', '13': 'sliderex',
                 '14': 'label', '15': 'colorbutton'}
        for name in ('SettingsCategory.xml', 'DialogAddonSettings.xml', 'DialogSettings.xml'):
            with self.subTest(window=name):
                root = ET.parse(SKIN / 'xml' / name).getroot()
                controls = [c for c in root.iter('control') if c.get('id')]
                ids = [c.get('id') for c in controls]
                self.assertEqual(len(ids), len(set(ids)))
                found = {c.get('id'): c for c in controls}
                for ident, expected in types.items():
                    self.assertEqual(found[ident].get('type'), expected, ident)
                for ident in ('3', '5'):
                    self.assertFalse(found[ident].findall('control'), 'Templates must not be in the dynamic list')
                if name == 'SettingsCategory.xml':
                    self.assertEqual(found['20'].findtext('onclick'), 'SettingsLevelChange')
                else:
                    for ident in ('28', '29', '30'):
                        self.assertEqual(found[ident].get('type'), 'button')

    def test_main_settings_navigates_to_kodi_windows(self):
        root = ET.parse(SKIN / 'xml' / 'Settings.xml').getroot()
        menu = root.find(".//control[@id='9000']")
        self.assertEqual(root.findtext('defaultcontrol'), '9000')
        actions = {item.findtext('onclick') for item in menu.findall('./content/item')}
        for window in ('PlayerSettings', 'MediaSettings', 'ServiceSettings', 'InterfaceSettings',
                       'SystemSettings', 'AddonBrowser', 'Profiles'):
            self.assertIn('ActivateWindow(%s)' % window, actions)
        for language in ('resource.language.pt_br', 'resource.language.en_gb'):
            text = (SKIN / 'language' / language / 'strings.po').read_text(encoding='utf-8')
            self.assertIn('msgctxt "#31067"', text)

    def test_skin_palette(self):
        root = ET.parse(SKIN / 'colors/defaults.xml').getroot()
        colors = {c.get('name'): c.text.lower() for c in root.findall('color')}
        self.assertEqual({k: colors[k] for k in ('bg', 'panel', 'panel2', 'white', 'text', 'muted', 'accent')},
                         dict(bg='ff0d0d0d', panel='ff181818', panel2='ff262626', white='fff2f2f2',
                              text='ffd9d9d9', muted='ffa6a6a6', accent='fff2f2f2'))


class BackupStage(unittest.TestCase):
    def make_zip(self, root, entries):
        path = root / 'backup.zip'
        with ZipFile(path, 'w') as z:
            for name, data in entries:
                z.writestr(name, data)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_stages_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backup, sha = self.make_zip(root, [('files/.kodi/userdata/file.xml', b'profile')])
            dest = root / 'private'
            stage_profile.stage(backup, dest, sha)
            self.assertEqual((dest / 'userdata/file.xml').read_bytes(), b'profile')
            self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o700)
            with self.assertRaises(FileExistsError):
                stage_profile.stage(backup, dest, sha)
            self.assertEqual((dest / 'userdata/file.xml').read_bytes(), b'profile')

    def test_unsafe_paths_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('files/.kodi/../evil', '/files/.kodi/evil', 'files/.kodi/..\\evil', 'elsewhere/a'):
                with self.subTest(name=name):
                    backup, sha = self.make_zip(root, [(name, b'bad')])
                    with self.assertRaises(ValueError):
                        stage_profile.stage(backup, root / 'dest', sha)
                    self.assertFalse((root / 'dest').exists())
                    self.assertFalse((root / 'evil').exists())

    def test_wrong_hash_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            link = ZipInfo('files/.kodi/link')
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            backup, sha = self.make_zip(root, [(link, b'target')])
            with self.assertRaises(ValueError):
                stage_profile.stage(backup, root / 'dest', '0' * 64)
            with self.assertRaises(ValueError):
                stage_profile.stage(backup, root / 'dest', sha)
            self.assertFalse((root / 'dest').exists())


if __name__ == '__main__':
    unittest.main()
