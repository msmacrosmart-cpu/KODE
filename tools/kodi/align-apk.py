#!/usr/bin/env python3
"""Alinha entradas não comprimidas a 4 bytes antes da assinatura do APK."""
import argparse
import re
import shutil
import struct
import zipfile
from pathlib import Path

SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path); p.add_argument('target',type=Path); args=p.parse_args()
if args.source.resolve()==args.target.resolve(): raise SystemExit('Entrada e saída devem ser diferentes')
with zipfile.ZipFile(args.source) as src,zipfile.ZipFile(args.target,'w',allowZip64=True) as dst:
    names=set()
    for item in src.infolist():
        if item.is_dir() or SIG.fullmatch(item.filename): continue
        name=item.filename
        if name in names or name.startswith('/') or '..' in name.split('/'): raise ValueError(f'Nome inválido: {name}')
        names.add(name)
        if item.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED): raise ValueError(f'Compressão não suportada: {name}')
        out=zipfile.ZipInfo(name,date_time=item.date_time);out.external_attr=item.external_attr
        if name=='resources.arsc':
            # resources.arsc deve estar sem comprimicao para o Android ler corretamente
            out.compress_type=zipfile.ZIP_STORED
            data=src.read(item)
            dst.writestr(out, data)
            if out.compress_type==zipfile.ZIP_STORED:
                padding=(-(dst.fp.tell()+30+len(name.encode('utf-8'))+4))%4
                out.extra=struct.pack('<HH',0xD935,padding)+b'\0'*padding
            continue
        if item.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED): raise ValueError(f'Compressão não suportada: {name}')
        out.compress_type=item.compress_type
        if out.compress_type==zipfile.ZIP_STORED:
            padding=(-(dst.fp.tell()+30+len(name.encode('utf-8'))+4))%4
            out.extra=struct.pack('<HH',0xD935,padding)+b'\0'*padding
        with src.open(item) as source,dst.open(out,'w') as target: shutil.copyfileobj(source,target,1024*1024)
