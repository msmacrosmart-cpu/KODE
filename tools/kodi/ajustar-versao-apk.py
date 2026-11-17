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

Tambem desliga android:debuggable (e testOnly, se existir) no mesmo manifesto.
O APK base do Kodi vem com debuggable=true; o Play Protect costuma tratar
build de desenvolvedor como suspeita e cancelar a instalacao sem explicar
("Aplicativo nao instalado"). O atributo booleano e trocado no lugar, sem
mexer em offsets do AXML.

Uso:
    python3 tools/kodi/ajustar-versao-apk.py ENTRADA.apk SAIDA.apk \
        --de 1.0.83 --para 1.0.84 --de-codigo 2103069 --para-codigo 2103070
    # --manter-debug para nao mexer no debuggable
"""
from __future__ import annotations

import argparse
import re
import struct
import zipfile
from pathlib import Path

SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)
MANIFESTO = 'AndroidManifest.xml'


def _u16(dados: bytes, pos: int) -> int:
    return struct.unpack_from('<H', dados, pos)[0]


def _u32(dados: bytes, pos: int) -> int:
    return struct.unpack_from('<I', dados, pos)[0]


def _strings_do_pool(dados: bytes, inicio: int) -> list:
    if _u16(dados, inicio) != 0x0001:
        raise ValueError('chunk de string pool esperado em %d' % inicio)
    tamanho = _u32(dados, inicio + 4)
    total = _u32(dados, inicio + 8)
    flags = _u32(dados, inicio + 16)
    base_strings = inicio + _u32(dados, inicio + 20)
    if inicio + tamanho > len(dados):
        raise ValueError('string pool passa do arquivo')
    utf8 = bool(flags & 0x100)
    saida = []
    for indice in range(total):
        deslocamento = _u32(dados, inicio + 28 + 4 * indice)
        pos = base_strings + deslocamento
        if utf8:
            comprimento = dados[pos]
            pos += 1
            if comprimento & 0x80:
                comprimento = ((comprimento & 0x7F) << 8) | dados[pos]
                pos += 1
            saida.append(dados[pos:pos + comprimento].decode('utf-8', 'replace'))
        else:
            comprimento = _u16(dados, pos)
            pos += 2
            if comprimento & 0x8000:
                comprimento = ((comprimento & 0x7FFF) << 16) | _u16(dados, pos)
                pos += 2
            saida.append(dados[pos:pos + 2 * comprimento].decode('utf-16-le', 'replace'))
    return saida


def _chunks_axml(dados: bytes):
    if len(dados) < 8 or _u16(dados, 0) != 0x0003:
        raise ValueError('AndroidManifest.xml nao e um AXML valido')
    pos = _u16(dados, 2)
    while pos + 8 <= len(dados):
        tipo = _u16(dados, pos)
        tamanho = _u32(dados, pos + 4)
        if tamanho < 8 or pos + tamanho > len(dados):
            raise ValueError('chunk AXML invalido em %d' % pos)
        yield pos, tipo, _u16(dados, pos + 2), tamanho
        pos += tamanho


def desligar_debug(manifesto: bytes) -> tuple:
    """Troca android:debuggable/testOnly true por false no lugar.

    Devolve (manifesto, lista_de_alteracoes, vistos). Nao mexe em tamanho nem
    em offsets: so no inteiro de valor do atributo (AXML Res_value).
    """
    dados = bytearray(manifesto)
    strings = None
    alterados = []
    vistos = []
    for inicio, tipo, _cabecalho, tamanho in _chunks_axml(dados):
        if tipo == 0x0001 and strings is None:
            strings = _strings_do_pool(dados, inicio)
            continue
        if tipo != 0x0102 or strings is None:  # START_ELEMENT
            continue
        nome_elemento = strings[_u32(dados, inicio + 20)]
        atributo_inicio = _u16(dados, inicio + 24)
        atributo_tamanho = _u16(dados, inicio + 26)
        total = _u16(dados, inicio + 28)
        if atributo_tamanho < 20 or total == 0:
            continue
        base = inicio + 16 + atributo_inicio
        for indice in range(total):
            attr = base + indice * atributo_tamanho
            if attr + 20 > inicio + tamanho:
                raise ValueError('atributo AXML passa do chunk')
            nome = strings[_u32(dados, attr + 4)]
            if nome not in ('debuggable', 'testOnly'):
                continue
            vistos.append((nome_elemento, nome))
            valor = _u32(dados, attr + 16)
            if valor:
                dados[attr + 16:attr + 20] = struct.pack('<I', 0)
                alterados.append((nome_elemento, nome))
    return bytes(dados), alterados, vistos


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
    parser.add_argument('--manter-debug', action='store_true',
                        help='nao desliga android:debuggable/testOnly')
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
        if not args.manter_debug:
            manifesto, alterados, vistos = desligar_debug(manifesto)
            if 'debuggable' not in [nome for _elemento, nome in vistos]:
                raise SystemExit('android:debuggable nao encontrado no manifesto')
            print('debug/testOnly vistos: %s' % (vistos,))
            print('debug/testOnly desligados: %s' % (alterados or 'ja estavam false'))
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
