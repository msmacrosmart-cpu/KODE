#!/usr/bin/env python3
"""Reempacota um APK Kodi 21.3 inspecionado sem alterar o código nativo."""
import argparse
import io
import re
import shutil
import struct
import zipfile
from pathlib import Path
from PIL import Image, ImageOps
from pyaxmlparser import APK

PROJECT = Path(__file__).resolve().parents[2]
COLORS = 'assets/addons/skin.estuary/colors/defaults.xml'
SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)
SUPPORTED = {'armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    args = ap.parse_args()
    if args.source.resolve() == args.output.resolve():
        raise SystemExit('Entrada e saída devem ser diferentes.')
    info = APK(str(args.source))
    if info.package != 'org.xbmc.kodi' or info.version_name != '21.3' or str(info.version_code) != '2103000':
        raise SystemExit('APK deve ser Kodi 21.3 oficial: pacote/versão não correspondem.')
    app = info.get_android_manifest_xml().find('application')
    extraction = app.get('{http://schemas.android.com/apk/res/android}extractNativeLibs') if app is not None else None
    if extraction != 'true':
        raise SystemExit('APK deve declarar extractNativeLibs=true; compactar bibliotecas não seria seguro.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.source) as src, zipfile.ZipFile(args.output, 'w', allowZip64=True) as dst:
        names = set()
        for entry in src.infolist():
            name = entry.filename
            if entry.is_dir() or SIG.fullmatch(name):
                continue
            if name.startswith('/') or '..' in name.split('/') or name in names:
                raise ValueError(f'Entrada inválida ou duplicada: {name}')
            names.add(name)
            zi = zipfile.ZipInfo(name, date_time=entry.date_time)
            zi.external_attr = entry.external_attr
            zi.compress_type = zipfile.ZIP_STORED if name == 'resources.arsc' else zipfile.ZIP_DEFLATED
            if name == 'resources.arsc':
                padding = (-(dst.fp.tell() + 30 + len(name.encode('utf-8')) + 4)) % 4
                zi.extra = struct.pack('<HH', 0xD935, padding) + b'\0' * padding
            if name == COLORS:
                dst.writestr(zi, (PROJECT / 'kodi/skin/defaults.xml').read_bytes())
            elif name.startswith('assets/addons/skin.estuary/extras/home-images/') and name.lower().endswith(('.jpg', '.jpeg')):
                with Image.open(io.BytesIO(src.read(entry))) as im:
                    output = io.BytesIO()
                    ImageOps.grayscale(im).convert('RGB').save(output, format='JPEG', quality=95)
                    dst.writestr(zi, output.getvalue())
            else:
                with src.open(entry) as source, dst.open(zi, 'w') as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
        abis = {n.split('/')[1] for n in names if n.startswith('lib/') and len(n.split('/')) > 2}
        required = {'AndroidManifest.xml', 'classes.dex', 'resources.arsc', COLORS}
        if not required <= names or not (abis & SUPPORTED) or any(f'lib/{abi}/libkodi.so' not in names for abi in abis):
            raise ValueError(f'APK incompleto ou ABI não reconhecida: {abis}')
        print('ABI(s): ' + ', '.join(sorted(abis)))
        print(f'Empacotados {len(names)} arquivos: {args.output}')


if __name__ == '__main__':
    main()
