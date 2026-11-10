import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
JAVA_SRC = ROOT / 'tools/android/src/org/smartedtv/bootstrap/ProfileSeed.java'
HARNESS_SRC = ROOT / 'tests/java/org/smartedtv/bootstrap/ProfileSeedHarness.java'
JAVA = shutil.which('java') or str(Path.home() / '.cache/kode-build/python/jdk4py/java-runtime/bin/java')
JAVAC = shutil.which('javac')
ECJ = os.environ.get('SMARTED_ECJ_JAR')
OLD = b'<settings><setting id="lookandfeel.skin" default="true">skin.estuary</setting></settings>'


@unittest.skipUnless(Path(JAVA).is_file() and (JAVAC or ECJ), 'Java compiler required for Android seed core tests')
class AndroidProfileSeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classes = tempfile.TemporaryDirectory()
        sources = [str(JAVA_SRC), str(HARNESS_SRC)]
        if JAVAC:
            cmd = [JAVAC, '-source', '8', '-target', '8', '-d', cls.classes.name] + sources
        else:
            cmd = [JAVA, '-cp', ECJ, 'org.eclipse.jdt.internal.compiler.batch.Main', '-1.8', '-d', cls.classes.name] + sources
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.classes.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.private = self.root / 'private'
        self.home.mkdir()
        self.private.mkdir()
        self.backup = self.root / 'backup.zip'

    def make_backup(self, extras=(), settings=OLD):
        with zipfile.ZipFile(self.backup, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('files/.kodi/userdata/guisettings.xml', settings)
            z.writestr('files/.kodi/addons/example/addon.xml', b'original addon data')
            for name, value in extras:
                z.writestr(name, value)
        return hashlib.sha256(self.backup.read_bytes()).hexdigest()

    def seed(self, digest, check=True):
        cmd = [JAVA, '-cp', self.classes.name, 'org.smartedtv.bootstrap.ProfileSeedHarness',
               str(self.backup), str(self.home), str(self.private), digest]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if check and result.returncode:
            self.fail(result.stderr)
        return result

    def test_fresh_install_changes_only_skin_and_existing_profile_is_preserved(self):
        digest = self.make_backup()
        original = self.backup.read_bytes()
        self.assertIn('INSTALLED', self.seed(digest).stdout)
        target = self.home / '.kodi'
        xml = (target / 'userdata/guisettings.xml').read_bytes()
        self.assertIn(b'<setting id="lookandfeel.skin">skin.novatv</setting>', xml)
        self.assertEqual((target / 'addons/example/addon.xml').read_bytes(), b'original addon data')
        self.assertEqual(self.backup.read_bytes(), original)
        sentinel = target / 'userdata/user-existing.txt'
        sentinel.write_text('untouched')
        self.backup.unlink()
        self.assertIn('EXISTING_PROFILE_PRESERVED', self.seed(digest).stdout)
        self.assertEqual(sentinel.read_text(), 'untouched')
        self.assertEqual([p.name for p in self.home.iterdir()], ['.kodi'])

    def test_hash_mismatch_and_zip_slip_leave_no_profile(self):
        digest = self.make_backup([('files/.kodi/../../escape', b'bad')])
        self.assertNotEqual(self.seed('0' * 64, check=False).returncode, 0)
        self.assertFalse((self.home / '.kodi').exists())
        self.assertNotEqual(self.seed(digest, check=False).returncode, 0)
        self.assertFalse((self.home / '.kodi').exists())
        self.assertFalse((self.root / 'escape').exists())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_invalid_skin_and_file_directory_conflict_are_rejected(self):
        digest = self.make_backup(settings=b'<settings/>')
        self.assertNotEqual(self.seed(digest, check=False).returncode, 0)
        self.assertEqual(list(self.home.iterdir()), [])
        digest = self.make_backup([('files/.kodi/addons/example/addon.xml/extra', b'bad')])
        self.assertNotEqual(self.seed(digest, check=False).returncode, 0)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_recover_only_own_empty_reservation(self):
        digest = self.make_backup()
        target = self.home / '.kodi'
        target.mkdir()
        marker = self.private / 'smarted-seed-reserved.flag'
        marker.touch()
        self.assertIn('INSTALLED', self.seed(digest).stdout)
        self.assertFalse(marker.exists())
        sentinel = target / 'keep.txt'
        sentinel.write_text('keep')
        marker.touch()
        self.assertIn('EXISTING_PROFILE_PRESERVED', self.seed(digest).stdout)
        self.assertEqual(sentinel.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
