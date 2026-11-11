#!/usr/bin/env python3
"""Build an UNSIGNED skin-only APK for an isolated emulator, not for release.

This intentionally has no backup/profile data, no Brazuka integration and no
production version bump. An existing user's saved skin preference is untouched.
"""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import zipfile
from xml.etree import ElementTree as ET

PROJECT = Path(__file__).resolve().parents[2]
SKIN = PROJECT / 'kodi/skin.novatv'
BASE_SHA = '76d70063b3e3783d43bbe757fa8158195a536cdb7ad4707e17a05163db911942'
SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)
SETTINGS = 'assets/system/settings/settings.xml'
MANIFEST = 'assets/system/addon-manifest.xml'


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--skin', type=Path, default=None,
                        help='pasta da skin (padrao kodi/skin.novatv); a do '
                             'repositorio pode ser usada via kodi/skin.estilo.personalizado')
    args = parser.parse_args()
    if args.base.resolve() == args.output.resolve():
        raise SystemExit('Input and output must differ')
    if sha256(args.base) != BASE_SHA:
        raise SystemExit('Unexpected base APK')
    if args.output.exists():
        raise SystemExit('Output already exists')
    skin_dir = args.skin or SKIN
    skin_files = sorted(p for p in skin_dir.rglob('*') if p.is_file())
    skin_root = ET.parse(skin_dir / 'addon.xml').getroot() if (skin_dir / 'addon.xml').is_file() else None
    if not skin_files or skin_root is None or skin_root.get('id') not in ('skin.novatv', 'skin.estilo.personalizado'):
        raise SystemExit('Skin is missing or has the wrong ID')
    skin_version = skin_root.get('version') or '1.0.0'
    for path in skin_files:
        if path.is_symlink():
            raise SystemExit('Symlink in skin is not allowed')
        if path.suffix == '.xml':
            ET.parse(path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(args.base) as src, zipfile.ZipFile(args.output, 'x', allowZip64=True) as dst:
            names = [e.filename for e in src.infolist() if not e.is_dir()]
            if len(names) != len(set(names)) or SETTINGS not in names or MANIFEST not in names:
                raise ValueError('Base APK is incomplete or has duplicate names')
            if any(n.startswith('assets/addons/skin.novatv/') for n in names):
                raise ValueError('Skin already exists in base APK')
            settings = src.read(SETTINGS)
            old = b'<default>skin.estuary</default>'
            if settings.count(old) != 1:
                raise ValueError('Unexpected skin default')
            settings = settings.replace(old, b'<default>skin.novatv</default>')
            ET.fromstring(settings)
            manifest = src.read(MANIFEST)
            if manifest.count(b'</addons>') != 1 or b'>skin.novatv<' in manifest:
                raise ValueError('Unexpected addon manifest')
            manifest = manifest.replace(b'</addons>', b'  <addon optional="true">skin.novatv</addon>\n</addons>')
            ET.fromstring(manifest)
            for entry in src.infolist():
                name = entry.filename
                if entry.is_dir() or SIG.fullmatch(name):
                    continue
                if name.startswith('/') or '..' in name.split('/'):
                    raise ValueError('Unsafe APK path')
                if name in (SETTINGS, MANIFEST):
                    dst.writestr(entry, settings if name == SETTINGS else manifest)
                else:
                    with src.open(entry) as inp, dst.open(entry, 'w') as out:
                        shutil.copyfileobj(inp, out, 1024 * 1024)
            for path in skin_files:
                name = 'assets/addons/skin.novatv/' + path.relative_to(skin_dir).as_posix()
                if name.endswith('/addon.xml') and path.parent == skin_dir:
                    # a skin do repositorio tem id proprio; no APK ela e skin.novatv
                    texto = path.read_text(encoding='utf-8')
                    texto = re.sub(r'(<addon[^>]*?)id="skin\.estilo\.personalizado"', r'\1id="skin.novatv"', texto, count=1)
                    dst.writestr(name, texto)
                    continue
                dst.write(path, name, compress_type=zipfile.ZIP_DEFLATED)
    except BaseException:
        args.output.unlink(missing_ok=True)
        raise
    print('Unsigned emulator-only candidate created; no backup, no integration or runtime validation.')


if __name__ == '__main__':
    main()
