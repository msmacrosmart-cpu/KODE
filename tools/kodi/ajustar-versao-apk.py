#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sobe versionName/versionCode do APK sem apktool e sem tocar no resto.

Um versionCode crescente evita downgrade. Edita os atributos AXML tipados,
sem recompilar recursos/Dex ou substituir inteiros globalmente no binario.
Opcionalmente eleva o minSdk; nunca reduz a API exigida pela base nativa.
A saida sem assinatura deve ser alinhada e assinada depois.

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
            # AXML UTF-8: primeiro o comprimento em UTF-16, depois em bytes.
            pos += 2 if dados[pos] & 0x80 else 1
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


ANDROID = 'http://schemas.android.com/apk/res/android'
NO_INDEX = 0xffffffff


def _atributos_android(dados):
    strings = None
    for inicio, tipo, _, tamanho in _chunks_axml(dados):
        if tipo == 0x0001:
            strings = _strings_do_pool(dados, inicio)
        if tipo != 0x0102 or strings is None:  # START_ELEMENT
            continue
        elemento = strings[_u32(dados, inicio + 20)]
        passo = _u16(dados, inicio + 26)
        base = inicio + 16 + _u16(dados, inicio + 24)
        for i in range(_u16(dados, inicio + 28)):
            pos = base + i * passo
            if passo < 20 or pos + 20 > inicio + tamanho:
                raise ValueError('atributo AXML invalido')
            ns = _u32(dados, pos)
            if ns != NO_INDEX and strings[ns] == ANDROID:
                yield elemento, strings[_u32(dados, pos + 4)], pos


def desligar_debug(manifesto: bytes) -> tuple:
    dados = bytearray(manifesto)
    alterados, vistos = [], []
    for elemento, nome, pos in _atributos_android(dados):
        if elemento == 'application' and nome in ('debuggable', 'testOnly'):
            vistos.append((elemento, nome))
            if _u32(dados, pos + 16):
                struct.pack_into('<I', dados, pos + 8, NO_INDEX)
                struct.pack_into('<I', dados, pos + 16, 0)
                alterados.append((elemento, nome))
    return bytes(dados), alterados, vistos


def tornar_features_opcionais(manifesto: bytes) -> tuple:
    """Garante android:required="false" em todas as tags <uses-feature>.

    Algumas TV Boxes (Rockchip/Allwinner/Amlogic AOSP) e sticks nao declaram
    ``android.hardware.screen.landscape`` em /etc/permissions e recusam o APK
    com INSTALL_FAILED_MISSING_FEATURE ("App nao instalado") quando algum
    ``<uses-feature>`` fica com ``required=true`` (ou sem o atributo required).
    """
    dados = bytearray(manifesto)
    strings = None
    res_ids = []
    modelo_req_false = None
    indice_req = None

    for inicio, tipo, _, tamanho in _chunks_axml(dados):
        if tipo == 0x0001:
            strings = _strings_do_pool(dados, inicio)
        elif tipo == 0x0180:
            qtd = (tamanho - 8) // 4
            res_ids = [ _u32(dados, inicio + 8 + 4 * i) for i in range(qtd) ]
        elif tipo == 0x0102 and strings is not None:
            if strings[_u32(dados, inicio + 20)] != 'uses-feature':
                continue
            passo = _u16(dados, inicio + 26)
            base = inicio + 16 + _u16(dados, inicio + 24)
            for i in range(_u16(dados, inicio + 28)):
                pos = base + i * passo
                ns = _u32(dados, pos)
                ind_nome = _u32(dados, pos + 4)
                if ns != NO_INDEX and strings[ns] == ANDROID and strings[ind_nome] == 'required':
                    indice_req = ind_nome
                    bloco = bytearray(dados[pos:pos + 20])
                    struct.pack_into('<I', bloco, 8, NO_INDEX)
                    bloco[15] = 0x12  # TYPE_INT_BOOLEAN
                    struct.pack_into('<I', bloco, 16, 0)
                    modelo_req_false = bytes(bloco)
                    break

    alteradas = []
    # Passo 1: desligar in-place qualquer uses-feature que ja tenha required != 0
    for inicio, tipo, _, tamanho in list(_chunks_axml(dados)):
        if tipo != 0x0102 or strings is None:
            continue
        if strings[_u32(dados, inicio + 20)] != 'uses-feature':
            continue
        passo = _u16(dados, inicio + 26)
        base = inicio + 16 + _u16(dados, inicio + 24)
        qtd_attr = _u16(dados, inicio + 28)
        nome_feat = '?'
        pos_req = None
        for i in range(qtd_attr):
            pos = base + i * passo
            ns = _u32(dados, pos)
            if ns == NO_INDEX or strings[ns] != ANDROID:
                continue
            atrib = strings[_u32(dados, pos + 4)]
            if atrib == 'name' and dados[pos + 15] == 3:
                nome_feat = strings[_u32(dados, pos + 16)]
            elif atrib == 'required':
                pos_req = pos
        if pos_req is not None and _u32(dados, pos_req + 16) != 0:
            struct.pack_into('<I', dados, pos_req + 8, NO_INDEX)
            dados[pos_req + 15] = 0x12
            struct.pack_into('<I', dados, pos_req + 16, 0)
            alteradas.append(nome_feat)

    # Passo 2: inserir required="false" nos uses-feature que omitiam o atributo
    if modelo_req_false is not None and indice_req is not None:
        res_req = res_ids[indice_req] if indice_req < len(res_ids) else 0x0101028e
        while True:
            inseriu = False
            for inicio, tipo, _, tamanho in _chunks_axml(dados):
                if tipo != 0x0102:
                    continue
                if strings[_u32(dados, inicio + 20)] != 'uses-feature':
                    continue
                passo = _u16(dados, inicio + 26)
                if passo != 20:
                    continue
                base = inicio + 16 + _u16(dados, inicio + 24)
                qtd_attr = _u16(dados, inicio + 28)
                nome_feat = '?'
                tem_req = False
                pos_insercao = base + qtd_attr * passo
                for i in range(qtd_attr):
                    pos = base + i * passo
                    ns = _u32(dados, pos)
                    ind_n = _u32(dados, pos + 4)
                    if ns != NO_INDEX and strings[ns] == ANDROID:
                        atrib = strings[ind_n]
                        if atrib == 'name' and dados[pos + 15] == 3:
                            nome_feat = strings[_u32(dados, pos + 16)]
                        elif atrib == 'required':
                            tem_req = True
                    rid = res_ids[ind_n] if ind_n < len(res_ids) else 0xffffffff
                    if rid > res_req and pos < pos_insercao:
                        pos_insercao = pos
                if not tem_req:
                    dados[pos_insercao:pos_insercao] = modelo_req_false
                    struct.pack_into('<H', dados, inicio + 28, qtd_attr + 1)
                    struct.pack_into('<I', dados, inicio + 4, tamanho + 20)
                    struct.pack_into('<I', dados, 4, len(dados))
                    alteradas.append(nome_feat)
                    inseriu = True
                    break
            if not inseriu:
                break

    # Confere integridade estrutural de todos os chunks AXML apos o ajuste
    list(_chunks_axml(dados))
    return bytes(dados), alteradas


def _versao_no_pool(dados, indice, antigo, novo):
    # A base assinada usa um pool sem estilos. Conserva índices (inclusive os
    # do resource map), recalculando offsets para versões como 1.0.100.
    p, _, header, size = next(c for c in _chunks_axml(dados) if c[1] == 1)
    if header != 28 or _u32(dados, p + 12) or _u32(dados, p + 24):
        raise ValueError('pool com estilos nao suportado')
    if _strings_do_pool(dados, p)[indice] != antigo:
        raise ValueError('versionName da base inesperado')
    utf8 = bool(_u32(dados, p + 16) & 0x100)

    def codificar(texto):
        if not texto.isascii() or not 0 < len(texto) < 128:
            raise ValueError('versionName deve ser ASCII curto')
        if utf8:
            return bytes([len(texto)] * 2) + texto.encode() + b'\0'
        return struct.pack('<H', len(texto)) + texto.encode('utf-16-le') + b'\0\0'

    offsets = p + header
    offset = _u32(dados, offsets + indice * 4)
    pos = p + _u32(dados, p + 20) + offset
    antes, depois = codificar(antigo), codificar(novo)
    if dados[pos:pos + len(antes)] != antes:
        raise ValueError('entrada de versionName invalida')
    delta = len(depois) - len(antes)
    for i in range(_u32(dados, p + 8)):
        ptr = offsets + i * 4
        n = _u32(dados, ptr)
        if n > offset:
            struct.pack_into('<I', dados, ptr, n + delta)
    dados[pos:pos + len(antes)] = depois
    end = p + size + delta
    pad = -end % 4
    dados[end:end] = bytes(pad)
    struct.pack_into('<I', dados, p + 4, size + delta + pad)
    struct.pack_into('<I', dados, p + 16, _u32(dados, p + 16) & ~1)  # SORTED_FLAG
    struct.pack_into('<I', dados, 4, len(dados))


def trocar_manifesto(manifesto: bytes, de_nome: str, para_nome: str,
                     de_codigo: int, para_codigo: int, min_sdk=None) -> bytes:
    dados = bytearray(manifesto)
    atributos = list(_atributos_android(dados))

    def atributo(elemento, nome, tipos):
        posicoes = [p for e, n, p in atributos if (e, n) == (elemento, nome)]
        if len(posicoes) != 1 or dados[posicoes[0] + 15] not in tipos:
            raise ValueError('atributo ausente, ambiguo ou tipo inesperado: ' + nome)
        return posicoes[0]

    def inteiro(elemento, nome, novo, esperado=None):
        pos = atributo(elemento, nome, (0x10, 0x11))
        valor = _u32(dados, pos + 16)
        if esperado is not None and valor != esperado or novo < valor:
            raise ValueError('valor de origem inesperado ou downgrade: ' + nome)
        struct.pack_into('<I', dados, pos + 8, NO_INDEX)
        struct.pack_into('<I', dados, pos + 16, novo)

    inteiro('manifest', 'versionCode', para_codigo, de_codigo)
    if min_sdk is not None:
        inteiro('uses-sdk', 'minSdkVersion', min_sdk)
    pos = atributo('manifest', 'versionName', (3,))
    _versao_no_pool(dados, _u32(dados, pos + 16), de_nome, para_nome)
    return bytes(dados)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('entrada', type=Path)
    parser.add_argument('saida', type=Path)
    parser.add_argument('--de', required=True)
    parser.add_argument('--para', required=True)
    parser.add_argument('--de-codigo', type=int, required=True)
    parser.add_argument('--para-codigo', type=int, required=True)
    parser.add_argument('--min-sdk', type=int, help='elevar a API minima')
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
                                     args.de_codigo, args.para_codigo, args.min_sdk)
        if not args.manter_debug:
            manifesto, alterados, vistos = desligar_debug(manifesto)
            if 'debuggable' not in [nome for _elemento, nome in vistos]:
                raise SystemExit('android:debuggable nao encontrado no manifesto')
            print('debug/testOnly vistos: %s' % (vistos,))
            print('debug/testOnly desligados: %s' % (alterados or 'ja estavam false'))
            manifesto, feats_opc = tornar_features_opcionais(manifesto)
            print('uses-feature tornadas opcionais: %s' % (feats_opc or 'ja eram todas false'))
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
