#!/usr/bin/env python3
"""Gera (e confere) o ``atualizacao.json`` do OTA do SMARTEDTV.

O app consulta **sempre** o mesmo endereço:

    https://github.com/<org>/<repo>/releases/latest/download/atualizacao.json
    https://github.com/<org>/<repo>/releases/latest/download/SMARTEDTV-atual.apk

Então o JSON e o APK precisam ter nome fixo em todas as releases — quem cuida
disso é este script, chamado pelo workflow do build (e pelo workflow de
"publicar só o APK"). Formato:

    {"versao": "1.0.75", "codigo": 2103061, "apk": "https://…/SMARTEDTV-atual.apk",
     "json": "https://…/atualizacao.json", "sha256": "…", "notas": "…",
     "obrigatorio": false}

Uso:
    python3 smartedtv/tools/ota_json.py --versao 1.0.75 --codigo 2103061 \\
        --apk out/SMARTEDTV-atual.apk --saida out/atualizacao.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

REPOSITORIO = 'msmacrosmart-cpu/KODE'
NOME_APK = 'SMARTEDTV-atual.apk'
NOME_JSON = 'atualizacao.json'


def sha256_arquivo(caminho, bloco=1024 * 1024):
    """SHA-256 do arquivo, sem carregar 240 MB na memória."""
    digest = hashlib.sha256()
    with open(caminho, 'rb') as handle:
        while True:
            parte = handle.read(bloco)
            if not parte:
                break
            digest.update(parte)
    return digest.hexdigest()


def montar(versao, codigo, repositorio=REPOSITORIO, sha='', notas='', obrigatorio=False):
    """Dicionário do JSON (separado para poder ser testado sem arquivo)."""
    base = 'https://github.com/%s/releases/latest/download' % repositorio.strip('/')
    texto_notas = notas.strip() or ('Atualização do SMARTEDTV %s. Instala por cima:'
                                    ' perfil e licença continuam.' % versao)
    return {
        'versao': str(versao),
        'codigo': int(codigo),
        'apk': '%s/%s' % (base, NOME_APK),
        'json': '%s/%s' % (base, NOME_JSON),
        'sha256': sha,
        'notas': texto_notas,
        'obrigatorio': bool(obrigatorio),
    }


def principal(argv=None):
    parser = argparse.ArgumentParser(description='gera o atualizacao.json do OTA')
    parser.add_argument('--saida', required=True, help='caminho do atualizacao.json')
    parser.add_argument('--versao', required=True)
    parser.add_argument('--codigo', required=True, type=int)
    parser.add_argument('--apk', default='', help='APK com nome fixo (para o sha256)')
    parser.add_argument('--repositorio', default=os.environ.get('GITHUB_REPOSITORY', REPOSITORIO))
    parser.add_argument('--notas', default='')
    parser.add_argument('--obrigatorio', action='store_true')
    args = parser.parse_args(argv)

    sha = ''
    if args.apk:
        if not os.path.isfile(args.apk):
            print('APK nao encontrado: %s' % args.apk, file=sys.stderr)
            return 2
        sha = sha256_arquivo(args.apk)
        print('APK %s (%d bytes) sha256=%s' % (args.apk, os.path.getsize(args.apk), sha))

    dados = montar(args.versao, args.codigo, args.repositorio, sha, args.notas, args.obrigatorio)
    pasta = os.path.dirname(os.path.abspath(args.saida))
    if pasta and not os.path.isdir(pasta):
        os.makedirs(pasta)
    with open(args.saida, 'w', encoding='utf-8') as handle:
        json.dump(dados, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(open(args.saida, encoding='utf-8').read())
    return 0


if __name__ == '__main__':
    sys.exit(principal())
