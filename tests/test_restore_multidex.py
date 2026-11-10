import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('restore_multidex', Path(__file__).resolve().parents[1] / 'tools/kodi/restore-multidex.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def archive(path, entries):
    with zipfile.ZipFile(path, 'w') as z:
        for name, data in entries:
            z.writestr(name, data)


class MultiDexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a, self.b = Path(self.tmp.name) / 'a.apk', Path(self.tmp.name) / 'b.apk'
        archive(self.a, [('classes.dex', b'one'), ('classes2.dex', b'two'), ('classes3.dex', b'three')])

    def test_recovers_missing_file(self):
        archive(self.b, [('classes.dex', b'one'), ('classes2.dex', b'two')])
        mod.restore(self.a, self.b)
        with zipfile.ZipFile(self.b) as z:
            self.assertEqual(z.read('classes3.dex'), b'three')
        mod.restore(self.a, self.b)  # idempotent

    def test_rejects_changed_code(self):
        archive(self.b, [('classes.dex', b'changed')])
        with self.assertRaises(ValueError):
            mod.restore(self.a, self.b)

    def test_rejects_noncontiguous(self):
        archive(self.b, [('classes.dex', b'one'), ('classes3.dex', b'three')])
        with self.assertRaises(ValueError):
            mod.restore(self.a, self.b)

    def test_rejects_extra_dex(self):
        archive(self.b, [('classes.dex', b'one'), ('classes2.dex', b'two'), ('classes3.dex', b'three'), ('classes4.dex', b'four')])
        with self.assertRaises(ValueError):
            mod.restore(self.a, self.b)
