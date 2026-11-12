#!/usr/bin/env python3
"""Copia add-ons para os assets de um APK decodificado (apenas emulador).

Motivo: no emulador o Kodi não reconhece add-ons copiados para o perfil por
`adb push` (o CAddonMgr só varre `special://xbmc/addons`, os assets). Este
script coloca o add-on público e suas dependências em `assets/addons` e registra
cada um em `assets/system/addon-manifest.xml`, exatamente como o APK de produção
faz com a skin e a ponte. Nada é publicado: serve só para o teste no emulador.

Uso: python3 tools/android/stage-public-addons.py DECODED ADDONS_DIR
"""
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def addon_id(folder):
    root = ET.parse(folder / 'addon.xml').getroot()
    value = root.get('id')
    if not value:
        raise SystemExit('addon.xml sem id: %s' % folder)
    return value


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    decoded, source = Path(argv[1]), Path(argv[2])
    addons_out = decoded / 'assets' / 'addons'
    manifest = decoded / 'assets' / 'system' / 'addon-manifest.xml'
    if not addons_out.is_dir() or not manifest.is_file():
        raise SystemExit('APK decodificado invalido: %s' % decoded)
    if not source.is_dir():
        raise SystemExit('pasta de addons ausente: %s' % source)

    texto = manifest.read_text(encoding='utf-8')
    ET.fromstring(texto)
    copiados = []
    for folder in sorted(p for p in source.iterdir() if p.is_dir()):
        if not (folder / 'addon.xml').is_file():
            print('ignorado (sem addon.xml): %s' % folder.name)
            continue
        identificador = addon_id(folder)
        destino = addons_out / identificador
        if destino.exists():
            print('ja existe, mantido: %s' % identificador)
            continue
        for arquivo in folder.rglob('*'):
            if arquivo.is_symlink():
                raise SystemExit('symlink proibido: %s' % arquivo)
            if arquivo.is_file():
                alvo = destino / arquivo.relative_to(folder)
                alvo.parent.mkdir(parents=True, exist_ok=True)
                alvo.write_bytes(arquivo.read_bytes())
        if '>%s<' % identificador not in texto:
            texto = texto.replace('</addons>', '  <addon optional="true">%s</addon>\n</addons>' % identificador, 1)
        copiados.append(identificador)

    ET.fromstring(texto)
    manifest.write_text(texto, encoding='utf-8')
    print('addons nos assets: %d -> %s' % (len(copiados), ', '.join(copiados) or 'nenhum'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
