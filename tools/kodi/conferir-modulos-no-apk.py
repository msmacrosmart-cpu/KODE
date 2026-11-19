#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confere, DENTRO do APK, se todo modulo do addon foi realmente embalado.

Por que existe: em 19/11 o APK publicado saiu sem
``assets/addons/service.smarted.bootstrap/ads_regra.py``. O arquivo existia no
repositorio, mas nao estava na lista MODULOS do injetor. No aparelho o
``import ads_regra`` do topo do ``smart_ads.py`` estourou e derrubou o
``service.py`` inteiro - o projetor mostrou notificacao de erro Python no boot
e nada do servico rodou. Nada no pipeline olhava para dentro dessa pasta.

A lista vem do proprio injetor (uma fonte so): se um modulo novo entrar em
MODULOS, esta conferencia passa a cobri-lo automaticamente.

Uso: python3 tools/kodi/conferir-modulos-no-apk.py build/.../SMARTEDTV-universal.apk
Sai com 1 e imprime as faltas quando algo nao foi embalado.
"""
import ast
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INJETOR = ROOT / 'tools' / 'kodi' / 'atualizar-apk-v17.py'
PREFIXO = 'assets/addons/service.smarted.bootstrap/'


def modulos_do_injetor(injetor=INJETOR):
    arvore = ast.parse(Path(injetor).read_text(encoding='utf-8'))
    for no in arvore.body:
        if isinstance(no, ast.Assign) and any(
                getattr(alvo, 'id', None) == 'MODULOS' for alvo in no.targets):
            return list(ast.literal_eval(no.value))
    raise SystemExit('MODULOS nao encontrado em %s' % injetor)


def conferir(caminho_apk, modulos=None):
    """Devolve (presentes, faltando) - listas ordenadas de nomes."""
    modulos = modulos or modulos_do_injetor()
    with zipfile.ZipFile(caminho_apk) as apk:
        nomes = set(apk.namelist())
    presentes = [m for m in modulos if PREFIXO + m in nomes]
    faltando = [m for m in modulos if PREFIXO + m not in nomes]
    return presentes, faltando


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    presentes, faltando = conferir(argv[0])
    for nome in presentes:
        print('modulo presente: %s' % nome)
    for nome in faltando:
        print('::error::modulo do addon AUSENTE no APK: %s' % nome)
    print('modulos do addon no APK: %d de %d'
          % (len(presentes), len(presentes) + len(faltando)))
    return 1 if faltando else 0


if __name__ == '__main__':
    sys.exit(main())
