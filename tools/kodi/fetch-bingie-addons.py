#!/usr/bin/env python3
"""Baixa a skin Bingie Mod e suas dependencias para injetar no APK (uso no CI).

Nada disso fica versionado no repositorio: o script clona o repositorio oficial
do mod (github.com/AchillesPunks/repository.titan.bingie.mod), extrai os addons
da pasta ``omega`` (Kodi 21) e deixa tudo pronto em ``destino``.

Uso:
    python3 tools/kodi/fetch-bingie-addons.py /tmp/extra
"""
import re
import shutil
import xml.etree.ElementTree as ET
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = 'https://github.com/AchillesPunks/repository.titan.bingie.mod'
SKIN = 'skin.titan.bingie.mod'
# importacoes que NAO existem nesse repositorio e que a skin tolera sem os addons
AUSENTES = ('plugin.video.youtube', 'plugin.program.autocompletion',
            'resource.images.studios.coloured')


def versao(nome):
    return [int(p) if p.isdigit() else 0 for p in re.split(r'[^0-9]+', nome) if p]


def clonar(destino):
    subprocess.run(['git', 'clone', '--depth', '1', '--filter=blob:none', '--no-checkout',
                    REPO, str(destino)], check=True, capture_output=True)
    subprocess.run(['git', 'sparse-checkout', 'init', '--no-cone'], cwd=destino, check=True,
                   capture_output=True)
    subprocess.run(['git', 'sparse-checkout', 'set', 'omega/*/*.zip'], cwd=destino, check=True,
                   capture_output=True)
    subprocess.run(['git', 'checkout'], cwd=destino, check=True, capture_output=True)


def addons(clone):
    """Um zip por addon: sempre a versao mais nova da pasta omega."""
    escolhidos = {}
    for zipado in sorted((clone / 'omega').rglob('*.zip')):
        if zipado.name.endswith('.md5'):
            continue
        atual = escolhidos.get(zipado.parent.name)
        if atual is None or versao(zipado.name) > versao(atual.name):
            escolhidos[zipado.parent.name] = zipado
    return escolhidos


def extrair(zipado, destino):
    with zipfile.ZipFile(zipado) as z:
        raiz = {n.split('/')[0] for n in z.namelist() if n}
        if len(raiz) != 1:
            raise SystemExit('zip com mais de um addon: %s' % zipado.name)
        z.extractall(destino)
    return raiz.pop()


def dependencias(pasta):
    """Imports de um addon (ignora os do proprio Kodi)."""
    try:
        raiz = ET.parse(pasta / 'addon.xml').getroot()
    except (ET.ParseError, OSError):
        return set()
    nomes = set()
    for importado in raiz.iter('import'):
        addon_id = importado.get('addon') or ''
        if addon_id and not addon_id.startswith(('xbmc.', 'kodi.')):
            nomes.add(addon_id)
    return nomes


def fechar_dependencias(staging, raiz_id):
    """So os addons que a skin realmente precisa (ela + dependencias)."""
    precisos, fila = {raiz_id}, [raiz_id]
    while fila:
        atual = fila.pop()
        for dep in dependencias(staging / atual):
            if dep in precisos:
                continue
            if (staging / dep / 'addon.xml').is_file():
                precisos.add(dep)
                fila.append(dep)
            else:
                print('  (sem o addon %s neste repositorio - segue sem ele)' % dep)
    return precisos


def liberar_dependencias_ausentes(pasta_skin):
    """Remove do addon.xml imports que nao podem ser atendidos (a skin funciona sem)."""
    addon_xml = pasta_skin / 'addon.xml'
    texto = addon_xml.read_text(encoding='utf-8')
    removidos = []
    for addon_id in AUSENTES:
        padrao = r'\s*<import[^>]*addon="%s"[^>]*/>' % re.escape(addon_id)
        if re.search(padrao, texto):
            texto = re.sub(padrao, '', texto)
            removidos.append(addon_id)
    addon_xml.write_text(texto, encoding='utf-8')
    return removidos


def main():
    if len(sys.argv) != 2:
        raise SystemExit('uso: fetch-bingie-addons.py <destino>')
    destino = Path(sys.argv[1]).resolve()
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / 'bingie'
        staging = Path(tmp) / 'staging'
        staging.mkdir()
        print('clonando %s ...' % REPO)
        clonar(clone)
        escolhidos = addons(clone)
        for nome, zipado in sorted(escolhidos.items()):
            extrair(zipado, staging)
        necessarios = fechar_dependencias(staging, SKIN)
        for addon_id in sorted(necessarios):
            shutil.copytree(staging / addon_id, destino / addon_id)
            print('  %s' % addon_id)
    skin = destino / SKIN
    if not (skin / 'addon.xml').is_file():
        raise SystemExit('skin %s nao encontrada' % SKIN)
    removidos = liberar_dependencias_ausentes(skin)
    if removidos:
        print('dependencias ausentes liberadas: ' + ', '.join(removidos))
    total = sum(f.stat().st_size for f in destino.rglob('*') if f.is_file())
    print('addons extras prontos: %d addons, %.1f MB em %s'
          % (len([d for d in destino.iterdir() if (d / 'addon.xml').is_file()]),
             total / 1048576, destino))


if __name__ == '__main__':
    main()
