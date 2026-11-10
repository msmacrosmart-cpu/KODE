#!/usr/bin/env python3
"""Confere o conteúdo do APK comparando-o com o ZIP recebido."""
import hashlib
import re
import struct
import sys
import zipfile
from pathlib import Path

ROOT = 'Kodi.for.Android.21.3/'
SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)
CHANGED = {
    'assets/addons/skin.estuary/colors/defaults.xml',
    'assets/addons/skin.estuary/extras/home-images/movie.jpg',
    'assets/addons/skin.estuary/extras/home-images/music.jpg',
}

def digest(archive, name):
    h = hashlib.sha256()
    with archive.open(name) as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.digest()

from_apk = len(sys.argv) == 4 and sys.argv[1] == '--apk'
if not from_apk and len(sys.argv) != 3:
    raise SystemExit('Uso: verify-content.py [--apk] ENTRADA APK')
source, output = sys.argv[2:4] if from_apk else sys.argv[1:3]
if from_apk:
    ROOT = ''
with zipfile.ZipFile(source) as src, zipfile.ZipFile(output) as apk:
    expected = {i.filename[len(ROOT):] for i in src.infolist()
                if i.filename.startswith(ROOT) and not i.is_dir() and i.filename != ROOT
                and not SIG.fullmatch(i.filename[len(ROOT):])}
    actual = {i.filename for i in apk.infolist() if not i.is_dir() and not SIG.fullmatch(i.filename)}
    if expected != actual:
        raise SystemExit(f'Arquivos faltantes: {expected-actual}; extras: {actual-expected}')
    if not CHANGED <= expected:
        raise SystemExit('Assets esperados não encontrados')
    for name in sorted(expected - CHANGED):
        if digest(src, ROOT + name) != digest(apk, name):
            raise SystemExit(f'Conteúdo inesperadamente alterado: {name}')
    color_file = Path(__file__).resolve().parents[2] / 'kodi/skin/defaults.xml'
    if apk.read('assets/addons/skin.estuary/colors/defaults.xml') != color_file.read_bytes():
        raise SystemExit('Paleta do APK difere da paleta no projeto')
    info = apk.getinfo('resources.arsc')
    apk.fp.seek(info.header_offset)
    header = struct.unpack('<IHHHHHIIIHH', apk.fp.read(30))
    offset = info.header_offset + 30 + header[-2] + header[-1]
    if info.compress_type != zipfile.ZIP_STORED or offset % 4:
        raise SystemExit('resources.arsc não está armazenado e alinhado a 4 bytes')
    print(f'Conteúdo verificado: {len(expected)} arquivos; apenas paleta e dois fundos substituídos.')
