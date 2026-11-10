import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(Image is None, 'Pillow required for artwork processing')
class ArtworkTest(unittest.TestCase):
    def test_decode_tree_has_android_icons_splash_and_real_progress(self):
        spec = importlib.util.spec_from_file_location('brand_artwork', ROOT / 'tools/kodi/apply-user-brand.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def image(name, size):
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                Image.new('RGB', size, 'black').save(p)
            manifest = root / 'AndroidManifest.xml'
            manifest.write_text('<application android:icon="@drawable/ic_launcher"/>')
            layout = root / 'res/layout/activity_splash.xml'
            layout.parent.mkdir(parents=True)
            layout.write_text('<ProgressBar android:id="@id/progressBar1" android:layout_width="wrap_content" android:layout_height="wrap_content" android:progress="50" android:layout_alignParentBottom="true" android:layout_centerHorizontal="true" style="test"/>')
            progress = root / 'res/drawable/progresscolor.xml'
            progress.parent.mkdir(parents=True)
            progress.write_text('<old/>')
            for density, size in [('ldpi', 36), ('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
                image('res/drawable-%s/ic_launcher.png' % density, (size, size))
            for name, size in [
                ('res/drawable/applaunch_screen.png', (1920, 1080)),
                ('res/drawable-xxxhdpi/applaunch_screen.png', (1920, 1080)),
                ('res/drawable-xhdpi/banner.png', (320, 180)),
                ('assets/media/applaunch_screen.png', (1920, 1080)),
                ('assets/media/banner.png', (320, 180)),
                ('assets/media/vendor_logo.png', (465, 128)),
                ('assets/media/vendor_icon.png', (128, 128)),
                ('assets/media/icon256x256.png', (256, 256)),
                ('assets/media/splash.jpg', (1920, 1080))]:
                image(name, size)
            with patch.object(sys, 'argv', ['brand', str(root)]):
                module.main()
            self.assertIn('android:roundIcon="@drawable/ic_launcher_round"', manifest.read_text())
            self.assertIn('android:progress="0"', layout.read_text())
            self.assertIn('#fff2f2f2', progress.read_text())
            p = root / 'res/drawable-xxxhdpi/ic_launcher_round.png'
            with Image.open(p) as im:
                self.assertEqual(im.size, (192, 192))
                self.assertEqual(im.mode, 'RGBA')
                self.assertEqual(im.getpixel((0, 0))[3], 0)
                self.assertEqual(im.getpixel((96, 96))[3], 255)
            with Image.open(root / 'res/drawable/applaunch_screen.png') as im:
                self.assertEqual(im.size, (1920, 1080))
                self.assertGreater(im.getpixel((960, 540))[0], 180)

    def test_original_uploads_preserved(self):
        expected = {
            'square.jpg': '4484968d482f79c7ebc825f5e2da7f8980777c1f241591a204c654cef3199315',
            'round.jpg': '4484968d482f79c7ebc825f5e2da7f8980777c1f241591a204c654cef3199315',
            'splash.jpg': '8e1d08646eb36de19b3d4be296c7ab5552fd2922433ef5be5afcbe5cb21a05ee',
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / 'assets/brand/source' / name).read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
