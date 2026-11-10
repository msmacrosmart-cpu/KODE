#!/usr/bin/env python3
"""Reempacota o conteúdo compilado do ZIP Kodi; não compila o código-fonte."""
import argparse
import hashlib
import io
import re
import shutil
import struct
import zipfile
from pathlib import Path
from PIL import Image, ImageOps

ROOT = 'Kodi.for.Android.21.3/'
COLORS = 'assets/addons/skin.estuary/colors/defaults.xml'
EXPECTED = '01eeb9a9b2efc9f0de322fc4a7f128ba1bbe17021596128fa7622b65cfe2fbbc'
SIGNATURE = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.IGNORECASE)
PROJECT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    h = hashlib.sha256()
    with args.source.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): h.update(chunk)
    if h.hexdigest() != EXPECTED:
        raise SystemExit(f'SHA-256 não corresponde ao ZIP inspecionado: {h.hexdigest()}')
    if args.source.resolve() == args.output.resolve():
        raise SystemExit('Entrada e saída devem ser arquivos diferentes.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    names = set()
    with zipfile.ZipFile(args.source) as src, zipfile.ZipFile(args.output, 'w', allowZip64=True) as dst:
        for entry in src.infolist():
            if not entry.filename.startswith(ROOT):
                raise ValueError(f'Entrada fora da raiz esperada: {entry.filename}')
            name = entry.filename[len(ROOT):]
            if not name or entry.is_dir() or SIGNATURE.fullmatch(name): continue
            if name.startswith('/') or '..' in name.split('/') or name in names:
                raise ValueError(f'Entrada inválida ou duplicada: {name}')
            names.add(name)
            zi = zipfile.ZipInfo(name, date_time=entry.date_time)
            zi.compress_type = zipfile.ZIP_STORED if name == 'resources.arsc' else zipfile.ZIP_DEFLATED
            zi.external_attr = entry.external_attr
            # resources.arsc precisa estar sem compressão e alinhado a 4 bytes.
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
    required = {'AndroidManifest.xml', 'classes.dex', 'resources.arsc', COLORS, 'lib/armeabi-v7a/libkodi.so'}
    if not required.issubset(names):
        args.output.unlink(missing_ok=True)
        raise SystemExit('ZIP incompleto: ' + ', '.join(sorted(required - names)))
    print(f'Empacotados {len(names)} arquivos: {args.output}')


if __name__ == '__main__': main()
