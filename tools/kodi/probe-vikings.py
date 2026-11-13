#!/usr/bin/env python3
"""Sonda as URLs candidatas do Vikings Repo e escreve um relatorio em texto.

Serve para descobrir, num ambiente com internet (a CI), qual e o caminho real
do zip do repositorio, o id/versao declarados no addon.xml e se o addon de
video ``plugin.video.BrazucaPlay.Matrix`` existe nesse repositorio.

Uso:
    python3 tools/kodi/probe-vikings.py RELATORIO.txt
"""
from __future__ import annotations

import hashlib
import io
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# Candidatos conhecidos (a ordem importa: o primeiro que responder manda).
RAIZ = 'https://vkodi.net/repo/'
CANDIDATOS = [
    RAIZ + 'repository.vikings.zip',
    RAIZ,
    RAIZ + 'addons.xml',
    RAIZ + 'zips/',
]
ZIPS_PLUGIN = [
    RAIZ + 'zips/plugin.video.BrazucaPlay.Matrix/plugin.video.BrazucaPlay.Matrix-2.1.4.zip',
    RAIZ + 'plugin.video.BrazucaPlay.Matrix/plugin.video.BrazucaPlay.Matrix-2.1.4.zip',
    RAIZ + 'zips/plugin.video.BrazucaPlay.Matrix/plugin.video.BrazucaPlay.Matrix-2.2.0.zip',
]
TIMEOUT = 25
UA = {'User-Agent': 'SMARTEDTV build probe/1.0'}


def obter(url: str, limite: int = 4 * 1024 * 1024) -> tuple[int, bytes, str]:
    pedido = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT) as resposta:
            dados = resposta.read(limite)
            return resposta.status, dados, resposta.geturl()
    except urllib.error.HTTPError as erro:
        return erro.code, b'', url
    except Exception as erro:  # noqa: BLE001 - relatorio, nao excecao
        return 0, str(erro).encode(), url


def descrever_zip(dados: bytes, saida: list[str], rotulo: str) -> None:
    saida.append('-- ' + rotulo)
    if not dados:
        saida.append('   (vazio)')
        return
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as z:
            saida.append('   sha256 %s (%d bytes, %d entradas)'
                         % (hashlib.sha256(dados).hexdigest(), len(dados), len(z.namelist())))
            for nome in z.namelist()[:25]:
                saida.append('     ' + nome)
            for nome in [n for n in z.namelist() if n.endswith('addon.xml')][:3]:
                saida.append('   --- ' + nome)
                texto = z.read(nome).decode('utf-8', 'replace')
                saida.append(texto[:2500])
    except zipfile.BadZipFile:
        saida.append('   nao e um zip: ' + dados[:200].decode('utf-8', 'replace'))


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    destino = Path(sys.argv[1])
    saida: list[str] = ['SONDA VIKINGS REPO']

    for url in CANDIDATOS:
        status, dados, final = obter(url)
        saida.append('=== %s -> http=%s bytes=%d final=%s' % (url, status, len(dados), final))
        if len(dados) and dados[:2] == b'PK':
            descrever_zip(dados, saida, 'zip de ' + url)
        elif dados:
            saida.append(dados[:1200].decode('utf-8', 'replace'))
        if url.endswith('.zip') and status == 200 and dados[:2] == b'PK':
            descrever_zip(dados, saida, 'repositorio')

    for url in ZIPS_PLUGIN:
        status, dados, _ = obter(url)
        saida.append('=== %s -> http=%s bytes=%d' % (url, status, len(dados)))
        if dados[:2] == b'PK':
            descrever_zip(dados, saida, 'plugin ' + url)

    destino.write_text('\n'.join(saida) + '\n', encoding='utf-8')
    print('\n'.join(saida))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
