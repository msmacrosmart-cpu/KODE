#!/usr/bin/env python3
"""Teste estatico rapido da skin e dos addons (sem emulador, < 30 s).

Faz duas verificacoes que pegam praticamente todo erro que so aparecia no
emulador Android:

1. Todo XML de `kodi/` e `tools/` precisa ser valido (xml.etree.ElementTree).
2. Todo `.py` de `kodi/` e `tools/` precisa compilar (py_compile).

Uso:
    python3 tools/kodi/static-check.py [--quiet] [--root=<pasta>]
"""
import py_compile
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PASTAS = ('kodi', 'tools')
BASE = RAIZ
IGNORAR = ('__pycache__', '.git')


def arquivos(sufixo, raiz=None):
    raiz = raiz or BASE
    for pasta in PASTAS:
        base = raiz / pasta
        if not base.is_dir():
            continue
        for caminho in sorted(base.rglob('*' + sufixo)):
            if any(parte in IGNORAR for parte in caminho.parts):
                continue
            yield caminho


def main(argv):
    global BASE
    quieto = '--quiet' in argv
    for argumento in argv:
        if argumento.startswith('--root='):
            BASE = Path(argumento.split('=', 1)[1]).resolve()
    inicio = time.time()
    xml = list(arquivos('.xml'))
    py = list(arquivos('.py'))
    falhas = []

    for caminho in xml:
        try:
            ET.parse(caminho)
        except (ET.ParseError, OSError) as erro:
            falhas.append('XML %s: %s' % (caminho, erro))

    temporaria = Path(tempfile.mkdtemp(prefix='pycompile-'))
    for indice, caminho in enumerate(py):
        try:
            py_compile.compile(str(caminho), cfile=str(temporaria / ('%d.pyc' % indice)),
                               doraise=True)
        except py_compile.PyCompileError as erro:
            falhas.append('PY %s: %s' % (caminho, erro.msg.strip()))

    duracao = time.time() - inicio
    for falha in falhas:
        print('::error::' + falha.replace('\n', ' ')[:400])
    if not quieto:
        print('Teste estatico: %d XML validos, %d scripts compilados em %.1f s'
              % (len(xml) - sum(1 for f in falhas if f.startswith('XML')),
                 len(py) - sum(1 for f in falhas if f.startswith('PY')), duracao))
    if falhas:
        print('%d falha(s)' % len(falhas))
        return 1
    if duracao > 30:
        print('::warning::teste estatico demorou %.1f s (limite 30 s)' % duracao)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
