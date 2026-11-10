#!/usr/bin/env python3
"""Stage the SMARTED navigation bridge into an apktool-decoded APK.

Does not bundle Brazuka or profile data, build or sign an APK. Kodi must find
Brazuca and its dependencies in the active profile. Test on a disposable APK.
"""
import argparse
from pathlib import Path
import shutil
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / 'kodi/addons/plugin.video.smarted'
ADDON_ID = 'plugin.video.smarted'


def stage(decoded):
    decoded = Path(decoded)
    manifest = decoded / 'assets/system/addon-manifest.xml'
    addons = decoded / 'assets/addons'
    target = addons / ADDON_ID
    if not addons.is_dir() or not manifest.is_file() or target.exists() or target.is_symlink():
        raise ValueError('Decoded APK missing assets or bridge already exists')
    source_xml = ET.parse(BRIDGE / 'addon.xml').getroot()
    if source_xml.get('id') != ADDON_ID:
        raise ValueError('Unexpected bridge ID')
    paths = sorted(p for p in BRIDGE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    if not paths or any(p.is_symlink() for p in BRIDGE.rglob('*')):
        raise ValueError('Invalid bridge source')
    content = manifest.read_bytes()
    tree = ET.fromstring(content)
    if any((entry.text or '').strip() == ADDON_ID for entry in tree.findall('addon')) or content.count(b'</addons>') != 1:
        raise ValueError('Unexpected addon manifest')
    updated = content.replace(b'</addons>', b'  <addon optional="true">plugin.video.smarted</addon>\n</addons>')
    ET.fromstring(updated)
    try:
        for source in paths:
            dest = target / source.relative_to(BRIDGE)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        manifest.write_bytes(updated)
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        manifest.write_bytes(content)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded', type=Path)
    args = parser.parse_args()
    stage(args.decoded)
    print('SMARTED bridge staged; Brazuca, runtime tests, APK build and signature are separate.')


if __name__ == '__main__':
    main()
