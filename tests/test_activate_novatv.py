"""Testes da ativacao da Nova TV no APK e no perfil semeado."""
import importlib.util
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'activate_novatv', ROOT / 'tools/kodi/activate-novatv.py')
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)

SETTINGS = ('<settings version="2">\n'
            '  <setting id="lookandfeel.skin" type="addon">\n'
            '    <default>skin.estuary</default>\n'
            '  </setting>\n'
            '</settings>\n')
SETTINGS_OK = SETTINGS.replace('skin.estuary', 'skin.novatv')
GUI = ('<settings version="2">\n'
       '    <setting id="lookandfeel.skin" default="true">skin.estuary</setting>\n'
       '    <setting id="lookandfeel.font">Default</setting>\n'
       '</settings>\n')


class ActivationTest(unittest.TestCase):
    def test_settings_default_switched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'settings.xml'
            path.write_bytes(SETTINGS.encode())
            MOD.activate_settings(path)
            data = path.read_bytes()
            self.assertEqual(data.count(b'<default>skin.novatv</default>'), 1)
            self.assertNotIn(b'skin.estuary', data)

    def test_settings_already_novatv_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'settings.xml'
            path.write_bytes(SETTINGS_OK.encode())
            self.assertFalse(MOD.activate_settings(path))
            self.assertEqual(path.read_bytes(), SETTINGS_OK.encode())

    def test_settings_missing_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'settings.xml'
            path.write_bytes(b'<settings/>')
            with self.assertRaises(SystemExit):
                MOD.activate_settings(path)

    def test_guisettings_preserves_profile_format(self):
        """O dex exige a linha exata; o restante do arquivo nao pode mudar."""
        updated, changed = MOD.activate_guisettings(GUI.encode())
        self.assertTrue(changed)
        expected = GUI.replace('>skin.estuary<', '>skin.novatv<')
        self.assertEqual(updated.decode(), expected)
        # continua com exatamente uma linha, no formato que o ProfileSeed aceita
        self.assertEqual(updated.count(b'id="lookandfeel.skin"'), 1)

    def test_guisettings_idempotent(self):
        once, _ = MOD.activate_guisettings(GUI.encode())
        twice, changed = MOD.activate_guisettings(once)
        self.assertFalse(changed)
        self.assertEqual(once, twice)

    def test_guisettings_rejects_duplicate(self):
        dup = GUI.replace('</settings>', GUI.splitlines()[1] + '\n</settings>')
        with self.assertRaises(SystemExit):
            MOD.activate_guisettings(dup.encode())

    def test_backup_zip_rewritten_and_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'backup.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('guisettings.xml', GUI)
                z.writestr('profiles.xml', '<profiles/>')

            def transform(name, data):
                if name.endswith('guisettings.xml'):
                    return MOD.activate_guisettings(data)[0]
                return None

            self.assertTrue(MOD.rewrite_zip(path, transform))
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                self.assertIn(b'skin.novatv', z.read('guisettings.xml'))
                self.assertEqual(z.read('profiles.xml'), b'<profiles/>')
            # segunda passada nao altera nada
            self.assertFalse(MOD.rewrite_zip(path, transform))


if __name__ == '__main__':
    unittest.main()
