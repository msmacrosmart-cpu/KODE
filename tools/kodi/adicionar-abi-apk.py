#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Acrescenta uma ABI (ex.: armeabi-v7a) a um APK que so tem outra.

As bibliotecas nativas vem de um APK Kodi compilado para a ABI desejada e com
o MESMO APP_PACKAGE do APK de destino (o libkodi.so procura a classe Java pelo
nome do pacote). O script:

  * recusa sobrescrever uma lib que ja exista com conteudo diferente;
  * preserva compressao/ordem de todas as entradas;
  * usa a mesma compressao que a APK de origem da ABI usa para cada .so;
  * nao assina nada (o workflow alinha e assina depois com a mesma chave).

Uso:
    python3 tools/kodi/adicionar-abi-apk.py ENTRADA.apk SAIDA.apk \
        --libs DIR --abi armeabi-v7a [--modelo-apk KODI-ARMV7.apk]
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('entrada', type=Path)
    parser.add_argument('saida', type=Path)
    parser.add_argument('--libs', type=Path, required=True,
                        help='pasta com lib/<abi>/*.so (ex.: .../armeabi-v7a)')
    parser.add_argument('--abi', required=True)
    parser.add_argument('--modelo-apk', type=Path,
                        help='APK Kodi da mesma ABI, para copiar a compressao')
    args = parser.parse_args()
    if args.entrada.resolve() == args.saida.resolve():
        raise SystemExit('Entrada e saida devem ser diferentes')
    if args.saida.exists():
        raise SystemExit('Saida ja existe: %s' % args.saida)
    if not args.libs.is_dir():
        raise SystemExit('Pasta de libs inexistente: %s' % args.libs)

    novas = {}
    for arquivo in sorted(args.libs.rglob('*.so')):
        if not arquivo.is_file():
            continue
        novas['lib/%s/%s' % (args.abi, arquivo.name)] = arquivo.read_bytes()
    if not novas:
        raise SystemExit('nenhuma .so em %s' % args.libs)
    if 'libkodi.so' not in {n.rsplit('/', 1)[-1] for n in novas}:
        raise SystemExit('libkodi.so nao esta na pasta de libs')

    compressao = {}
    if args.modelo_apk and args.modelo_apk.is_file():
        with zipfile.ZipFile(args.modelo_apk) as modelo:
            for info in modelo.infolist():
                compressao[info.filename] = info.compress_type

    with zipfile.ZipFile(args.entrada) as origem:
        nomes = [item.filename for item in origem.infolist() if not item.is_dir()]
        if len(nomes) != len(set(nomes)):
            raise SystemExit('ZIP com entradas duplicadas')
        existentes = {n: origem.read(n) for n in nomes if n.startswith('lib/%s/' % args.abi)}
        for nome, dados in novas.items():
            if nome in existentes and existentes[nome] != dados:
                raise SystemExit('lib ja existe com outro conteudo: %s' % nome)
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(args.saida, 'w', allowZip64=True) as destino:
                for item in origem.infolist():
                    if item.is_dir() or SIG.fullmatch(item.filename):
                        continue
                    if item.filename in novas:
                        continue  # sera escrita abaixo com o conteudo novo
                    with origem.open(item) as fonte, destino.open(item, 'w') as alvo:
                        while True:
                            bloco = fonte.read(1024 * 1024)
                            if not bloco:
                                break
                            alvo.write(bloco)
                for nome, dados in novas.items():
                    tipo = compressao.get(nome, zipfile.ZIP_DEFLATED)
                    info = zipfile.ZipInfo(nome, date_time=(2026, 1, 1, 0, 0, 0))
                    info.compress_type = tipo
                    info.external_attr = 0o644 << 16
                    destino.writestr(info, dados)
        except BaseException:
            args.saida.unlink(missing_ok=True)
            raise

    print('ABI %s: %d libs adicionadas' % (args.abi, len(novas)))
    print('gerado: %s (%d bytes)' % (args.saida, args.saida.stat().st_size))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
