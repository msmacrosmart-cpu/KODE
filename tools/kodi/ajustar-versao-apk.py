#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sobe versionName/versionCode do APK sem apktool e sem tocar no resto.

O Android so aceita a atualizacao se o ``versionCode`` for MAIOR que o da
versao instalada. Varias instaladoras (MIUI, Samsung, Android TV, Fire OS)
mostram so "Aplicativo nao instalado" quando o APK tem o MESMO codigo da
versao que ja esta no aparelho. Este passo troca os dois valores no
AndroidManifest.xml binario (string pool + atributo inteiro), no mesmo estilo
de tools/kodi/build-release-apk.py, e reescreve o ZIP preservando todas as
outras entradas.

O APK de saida continua SEM assinatura valida (as assinaturas antigas sao
removidas): o workflow chama align-apk.py e apksigner logo depois.

Uso:
    python3 tools/kodi/ajustar-versao-apk.py ENTRADA.apk SAIDA.apk \
        --de 1.0.83 --para 1.0.84 --de-codigo 2103069 --para-codigo 2103070
"""
from __future__ import annotations

import argparse
import re
import struct
import zipfile
from pathlib import Path

SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)
MANIFESTO = 'AndroidManifest.xml'


def trocar_manifesto(manifesto: bytes, de_nome: str, para_nome: str,
                     de_codigo: int, para_codigo: int) -> bytes:
    if len(para_nome) != len(de_nome):
        raise SystemExit(
            'versionName novo (%s) precisa ter o mesmo tamanho de %s (%d)'
            % (para_nome, de_nome, len(de_nome)))
    if not 0 <= de_codigo <= 0xFFFFFFFF or not 0 <= para_codigo <= 0xFFFFFFFF:
        raise SystemExit('versionCode fora da faixa de 32 bits')
    antigo_nome = de_nome.encode('utf-16-le')
    novo_nome = para_nome.encode('utf-16-le')
    antigo_codigo = struct.pack('<I', de_codigo)
    novo_codigo = struct.pack('<I', para_codigo)
    for rotulo, antigo in (('versionName', antigo_nome),
                           ('versionCode', antigo_codigo)):
        ocorrencias = manifesto.count(antigo)
        if ocorrencias != 1:
            raise SystemExit('%s %r aparece %d vezes no manifesto (esperado 1)'
                             % (rotulo, antigo, ocorrencias))
    manifesto = manifesto.replace(antigo_nome, novo_nome)
    manifesto = manifesto.replace(antigo_codigo, novo_codigo)
    if novo_nome not in manifesto or novo_codigo not in manifesto:
        raise SystemExit('a troca nao entrou no manifesto')
    return manifesto


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('entrada', type=Path)
    parser.add_argument('saida', type=Path)
    parser.add_argument('--de', required=True)
    parser.add_argument('--para', required=True)
    parser.add_argument('--de-codigo', type=int, required=True)
    parser.add_argument('--para-codigo', type=int, required=True)
    args = parser.parse_args()
    if args.entrada.resolve() == args.saida.resolve():
        raise SystemExit('Entrada e saida devem ser diferentes')
    if args.saida.exists():
        raise SystemExit('Saida ja existe: %s' % args.saida)
    if args.para_codigo <= args.de_codigo:
        raise SystemExit('O versionCode novo precisa ser MAIOR (atualizacao)')

    with zipfile.ZipFile(args.entrada) as origem:
        nomes = [item.filename for item in origem.infolist() if not item.is_dir()]
        if len(nomes) != len(set(nomes)):
            raise SystemExit('ZIP com entradas duplicadas')
        if MANIFESTO not in nomes:
            raise SystemExit('APK sem AndroidManifest.xml')
        manifesto = trocar_manifesto(origem.read(MANIFESTO), args.de, args.para,
                                     args.de_codigo, args.para_codigo)
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(args.saida, 'w', allowZip64=True) as destino:
                for item in origem.infolist():
                    if item.is_dir() or SIG.fullmatch(item.filename):
                        continue
                    if item.filename == MANIFESTO:
                        destino.writestr(item, manifesto)
                        continue
                    with origem.open(item) as fonte, destino.open(item, 'w') as alvo:
                        while True:
                            bloco = fonte.read(1024 * 1024)
                            if not bloco:
                                break
                            alvo.write(bloco)
        except BaseException:
            args.saida.unlink(missing_ok=True)
            raise

    print('versao: %s (%d) -> %s (%d)'
          % (args.de, args.de_codigo, args.para, args.para_codigo))
    print('gerado: %s (%d bytes)' % (args.saida, args.saida.stat().st_size))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
