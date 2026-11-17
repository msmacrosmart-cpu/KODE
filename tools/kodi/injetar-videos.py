#!/usr/bin/env python3
"""
Injeta as modificacoes da tela VIDEOS no APK base do SMARTEDTV.

Copia para dentro do APK:
  - assets/addons/skin.novatv/     (com MyVideos.xml, Home.xml, qrcode.png)
  - assets/addons/plugin.video.smarted/   (default.py com as 6 acoes)
  - assets/addons/service.smarted.bootstrap/ (arquivos do bootstrap)

Atualiza system/addon-manifest.xml para registrar os 3 addons.

Remove assinaturas antigas (META-INF) para reassinatura posterior.

Uso:
    python3 injetar-videos.py --apk base.apk --saida bruto.apk
"""

import argparse
import re
import shutil
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)

INJECT_DIRS = [
    (PROJECT / "kodi" / "skin.novatv", "assets/addons/skin.novatv"),
    (PROJECT / "kodi" / "addons" / "plugin.video.smarted", "assets/addons/plugin.video.smarted"),
    (PROJECT / "kodi" / "addons" / "service.smarted.bootstrap", "assets/addons/service.smarted.bootstrap"),
]

MANIFEST_PATH = "system/addon-manifest.xml"
ADDONS_TO_REGISTER = ["skin.novatv", "plugin.video.smarted", "service.smarted.bootstrap"]


def collect_inject_files():
    entradas = {}
    for src_dir, apk_prefix in INJECT_DIRS:
        if not src_dir.is_dir():
            raise SystemExit(f"Diretorio fonte nao encontrado: {src_dir}")
        for p in sorted(src_dir.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                rel = p.relative_to(src_dir).as_posix()
                entradas[f"{apk_prefix}/{rel}"] = p
    return entradas


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apk", required=True, type=Path, help="APK base")
    ap.add_argument("--saida", required=True, type=Path, help="APK de saida (injetado)")
    args = ap.parse_args()

    if args.apk.resolve() == args.saida.resolve():
        raise SystemExit("Entrada e saida devem ser diferentes.")

    args.saida.parent.mkdir(parents=True, exist_ok=True)

    entradas = collect_inject_files()
    nomes_vistos = set()

    n_skin = sum(1 for k in entradas if k.startswith("assets/addons/skin.novatv/"))
    n_plugin = sum(1 for k in entradas if k.startswith("assets/addons/plugin.video.smarted/"))
    n_bootstrap = sum(1 for k in entradas if k.startswith("assets/addons/service.smarted.bootstrap/"))

    print(f"Arquivos para injetar - skin.novatv: {n_skin}, plugin.video.smarted: {n_plugin}, service.smarted.bootstrap: {n_bootstrap}")

    with zipfile.ZipFile(args.apk) as src, zipfile.ZipFile(args.saida, 'w', allowZip64=True) as dst:
        # Copia todas as entradas do original (exceto META-INF assinaturas)
        for entry in src.infolist():
            name = entry.filename
            if entry.is_dir() or SIG.fullmatch(name):
                continue
            if name.startswith('/') or '..' in name.split('/') or name in nomes_vistos:
                raise ValueError(f'Entrada invalida ou duplicada: {name}')
            nomes_vistos.add(name)
            zi = zipfile.ZipInfo(name, date_time=entry.date_time)
            zi.external_attr = entry.external_attr
            zi.compress_type = entry.compress_type
            with src.open(entry) as source, dst.open(zi, 'w') as target:
                shutil.copyfileobj(source, target, 1024 * 1024)

        # Injeta/sobrescreve com os arquivos do repositorio
        for apk_path, local_path in sorted(entradas.items()):
            if apk_path in nomes_vistos:
                dst.writestr(apk_path, local_path.read_bytes())
                print(f"  sobrescrito: {apk_path}")
            else:
                zi = zipfile.ZipInfo(apk_path, date_time=(2024, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                dst.writestr(zi, local_path.read_bytes())
                nomes_vistos.add(apk_path)
                print(f"  injetado: {apk_path}")

        # Atualiza addon-manifest.xml
        if MANIFEST_PATH in nomes_vistos:
            src.seek(0)
            with src.open(MANIFEST_PATH) as f:
                manifest_text = f.read().decode('utf-8')
            for addon in ADDONS_TO_REGISTER:
                tag = f'  <addon>{addon}</addon>'
                if tag not in manifest_text:
                    anchor = '  <addon>skin.estuary</addon>'
                    if anchor in manifest_text:
                        manifest_text = manifest_text.replace(anchor, anchor + '\n' + tag, 1)
                    else:
                        manifest_text = manifest_text.replace('</addons>', tag + '\n</addons>', 1)
                    print(f"  manifesto: {addon} registrado")
                else:
                    print(f"  -- manifesto: {addon} ja presente")
            dst.writestr(MANIFEST_PATH, manifest_text.encode('utf-8'))
        else:
            print(f"  aviso: {MANIFEST_PATH} nao encontrado no APK base")

    print(f"\nTotal de entradas no APK injetado: {len(nomes_vistos)}")
    print(f"APK injetado gerado: {args.saida}")


if __name__ == '__main__':
    main()
