import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('splash', ROOT / 'tools/kodi/hide-splash-text.py')
splash = importlib.util.module_from_spec(spec)
spec.loader.exec_module(splash)


class SplashTest(unittest.TestCase):
    def test_hides_text_but_preserves_control_for_kodi(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'layout.xml'
            path.write_text('<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"><TextView android:id="@id/textView1" android:text=""/><ProgressBar android:id="@id/progressBar1"/></FrameLayout>')
            splash.hide(path)
            splash.hide(path)
            root = ET.parse(path).getroot()
            self.assertEqual(root.find('TextView').get(splash.ANDROID + 'visibility'), 'gone')
            self.assertEqual(root.find('TextView').get(splash.ANDROID + 'id'), '@id/textView1')
            self.assertIsNotNone(root.find('ProgressBar'))

    def test_unexpected_layout_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'layout.xml'
            path.write_text('<FrameLayout/>')
            with self.assertRaises(ValueError): splash.hide(path)
