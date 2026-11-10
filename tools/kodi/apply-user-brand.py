#!/usr/bin/env python3
"""Apply supplied SMARTED-TV artwork to an apktool-decoded 1.0.16 tree.

This only edits a decoded build tree; it neither signs nor publishes an APK.
Requires Pillow. Keep the three original images under assets/brand/source.
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'assets/brand/source'


def fit(path, size):
    with Image.open(path) as source:
        return ImageOps.fit(source.convert('RGB'), size, method=Image.Resampling.LANCZOS)


def round_icon(path, size):
    # Remove excess black margin but preserve the central circular design.
    with Image.open(path) as source:
        image = source.convert('RGB')
        w, h = image.size
        side = min(w, h) * 5 // 8
        image = image.crop(((w-side)//2, (h-side)//2, (w+side)//2, (h+side)//2))
        image = ImageOps.fit(image, (size * 4, size * 4), method=Image.Resampling.LANCZOS).convert('RGBA')
    mask = Image.new('L', image.size)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    image.putalpha(mask)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise ValueError('Unexpected decoded resource: ' + label)
    return text.replace(old, new, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded', type=Path)
    args = parser.parse_args()
    root = args.decoded
    if not all((SOURCE / (n + '.jpg')).is_file() for n in ('splash', 'square', 'round')):
        raise SystemExit('Original supplied artwork is missing')
    manifest = root / 'AndroidManifest.xml'
    layout = root / 'res/layout/activity_splash.xml'
    progress = root / 'res/drawable/progresscolor.xml'
    # Check the tree before doing any writes.
    m = manifest.read_text(encoding='utf-8')
    if 'android:roundIcon=' in m:
        raise ValueError('roundIcon already present')
    m = replace_once(m, 'android:icon="@drawable/ic_launcher"',
                     'android:icon="@drawable/ic_launcher" android:roundIcon="@drawable/ic_launcher_round"', 'manifest icon')
    l = layout.read_text(encoding='utf-8')
    l = replace_once(l, 'android:id="@id/progressBar1" android:layout_width="wrap_content" android:layout_height="wrap_content"',
                     'android:id="@id/progressBar1" android:layout_width="280.0dip" android:layout_height="8.0dip"', 'progress dimensions')
    l = replace_once(l, 'android:progress="50"', 'android:progress="0"', 'progress initial value')
    l = replace_once(l, 'android:layout_alignParentBottom="true" android:layout_centerHorizontal="true" style=',
                     'android:layout_alignParentBottom="true" android:layout_centerHorizontal="true" android:layout_marginBottom="32.0dip" style=', 'progress placement')
    if not progress.exists():
        raise ValueError('Progress drawable missing')
    icons = sorted((root / 'res').glob('drawable-*/ic_launcher.png'))
    if len(icons) != 6:
        raise ValueError('Unexpected Android icon variants')
    for path in icons:
        with Image.open(path) as im:
            w, h = im.size
        if w != h:
            raise ValueError('Non-square launcher icon')
        fit(SOURCE / 'square.jpg', (w, h)).save(path)
        round_icon(SOURCE / 'round.jpg', w).save(path.with_name('ic_launcher_round.png'))
    media = root / 'assets/media'
    square_paths = sorted(media.glob('icon*x*.png')) + [media / 'vendor_icon.png']
    for path in square_paths:
        with Image.open(path) as im: size = im.size
        fit(SOURCE / 'square.jpg', size).save(path)
    for path in (root / 'res/drawable/applaunch_screen.png',
                 root / 'res/drawable-xxxhdpi/applaunch_screen.png',
                 root / 'res/drawable-xhdpi/banner.png', media / 'applaunch_screen.png',
                 media / 'banner.png', media / 'vendor_logo.png', media / 'splash.jpg'):
        with Image.open(path) as im: size = im.size
        image = fit(SOURCE / 'splash.jpg', size)
        if path.suffix == '.jpg': image.save(path, quality=95)
        else: image.save(path)
    progress.write_text('''<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
  <item android:id="@android:id/background"><shape><corners android:radius="4dp"/><solid android:color="#4dffffff"/></shape></item>
  <item android:id="@android:id/progress"><clip><shape><corners android:radius="4dp"/><solid android:color="#fff2f2f2"/></shape></clip></item>
</layer-list>
''', encoding='utf-8')
    layout.write_text(l, encoding='utf-8')
    manifest.write_text(m, encoding='utf-8')
    print('Applied supplied artwork and white progress drawable to decoded tree; APK still needs building and testing.')


if __name__ == '__main__':
    main()
