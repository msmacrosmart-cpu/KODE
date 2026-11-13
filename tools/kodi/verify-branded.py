#!/usr/bin/env python3
"""Verificações estáticas do APK SMARTEDTV contra o APK Kodi de entrada."""
import hashlib
import struct
import sys
import zipfile
from pyaxmlparser import APK

if len(sys.argv)!=3: raise SystemExit('Uso: verify-branded.py ORIGEM RESULTADO')
source,output=sys.argv[1:]
a=APK(output)
if (a.package,a.get_app_name(),a.version_name,str(a.version_code)) != ('org.xbmc.kodi','SMARTEDTV','1.0.15','2103001'):
    raise SystemExit(f'Identidade inesperada: {a.package}, {a.get_app_name()}, {a.version_name}, {a.version_code}')
def digest(z,n):
    h=hashlib.sha256()
    with z.open(n) as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.digest()
with zipfile.ZipFile(source) as before,zipfile.ZipFile(output) as after:
    bad=after.testzip()
    if bad: raise SystemExit(f'CRC inválido: {bad}')
    oldlibs={n for n in before.namelist() if n.startswith('lib/') and n.endswith('.so')}
    newlibs={n for n in after.namelist() if n.startswith('lib/') and n.endswith('.so')}
    if oldlibs!=newlibs or not oldlibs: raise SystemExit('Lista de bibliotecas diferente da original')
    for n in sorted(oldlibs | {'classes.dex'}):
        if digest(before,n)!=digest(after,n): raise SystemExit(f'Código modificado: {n}')
    assets1={n for n in before.namelist() if n.startswith('assets/') and not n.endswith('/')}
    assets2={n for n in after.namelist() if n.startswith('assets/') and not n.endswith('/')}
    if assets1!=assets2: raise SystemExit('Arquivos de assets removidos ou adicionados')
    allowed={'assets/addons/skin.estuary/colors/defaults.xml','assets/addons/skin.estuary/extras/home-images/movie.jpg','assets/addons/skin.estuary/extras/home-images/music.jpg','assets/media/applaunch_screen.png','assets/media/banner.png','assets/media/vendor_icon.png','assets/media/vendor_logo.png','assets/media/splash.jpg'}
    allowed.update(n for n in assets1 if n.startswith('assets/media/icon') and n.endswith('.png'))
    changed={n for n in assets1 if digest(before,n)!=digest(after,n)}
    if changed!=allowed: raise SystemExit(f'Assets alterados inesperadamente: {changed-allowed}; alterações ausentes: {allowed-changed}')
    abis={n.split('/')[1] for n in newlibs}
    for i in after.infolist():
        if i.compress_type==zipfile.ZIP_STORED:
            after.fp.seek(i.header_offset); h=struct.unpack('<IHHHHHIIIHH',after.fp.read(30))
            if (i.header_offset+30+h[-2]+h[-1])%4: raise SystemExit(f'Entrada desalinhada: {i.filename}')
    print(f'Verificado: SMARTEDTV 1.0.15, ABI={sorted(abis)}, {len(oldlibs)} bibliotecas e classes.dex intactos, {len(changed)} assets de marca/tema alterados, ZIP íntegro e alinhado.')
