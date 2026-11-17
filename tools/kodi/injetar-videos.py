#!/usr/bin/env python3
"""
Injeta as modificações da tela VÍDEOS no APK base do SMARTEDTV.

Baseado no fluxo de injeção do workflow build-atual-com-tela.yml:
1. Abre o APK base como zip
2. Cria novo zip copiando todas as entradas (menos META-INF)
3. Injeta/atualiza:
   - addon-manifest.xml: registra skin.novatv, plugin.video.smarted, service.smarted.bootstrap
   - assets/addons/skin.novatv/ (todos os arquivos da skin, incluindo MyVideos.xml)
   - assets/addons/plugin.video.smarted/ (default.py com as 5 ações, etc.)
   - assets/addons/service.smarted.bootstrap/ (arquivos do bootstrap)
4. Remove assinaturas antigas (META-INF) para reassinatura posterior

Uso:
    python3 injetar-videos.py --apk base.apk --saida bruto.apk
"""

import argparse
import io
import re
import shutil
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)

# Diretórios a injetar (fonte -> destino dentro do APK)
INJECT_DIRS = [
    (PROJECT / "kodi" / "skin.novatv", "assets/addons/skin.novatv"),
    (PROJECT / "kodi" / "addons" / "plugin.video.smarted", "assets/addons/plugin.video.smarted"),
    (PROJECT / "kodi" / "addons" / "service.smarted.bootstrap", "assets/addons/service.smarted.bootstrap"),
]

# Arquivos específicos a atualizar/addon-manifest
MANIFEST_PATH = "system/addon-manifest.xml"
ADDONS_TO_REGISTER = ["skin.novatv", "plugin.video.smarted", "service.smarted.bootstrap"]


def iter_inject_files(src_dir: Path, apk_prefix: str):
    """Yield (apk_path, local_path) para todos os arquivos de um diretório."""
    for p in sorted(src_dir.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            rel = p.relative_to(src_dir).as_posix()
            yield f"{apk_prefix}/{rel}", p


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apk", required=True, type=Path, help="APK base")
    ap.add_argument("--saida", required=True, type=Path, help="APK de saída (injetado)")
    args = ap.parse_args()

    if args.apk.resolve() == args.saida.resolve():
        raise SystemExit("Entrada e saída devem ser diferentes.")

    args.saida.parent.mkdir(parents=True, exist_ok=True)

    nomes_vistos = set()
    entradas_injetar = {}

    # Coleta todos os arquivos para injetar
    for src_dir, apk_prefix in INJECT_DIRS:
        if not src_dir.is_dir():
            raise SystemExit(f"Diretório fonte não encontrado: {src_dir}")
        for apk_path, local_path in iter_inject_files(src_dir, apk_prefix):
            entradas_injetar[apk_path] = local_path

    with zipfile.ZipFile(args.apk) as src, zipfile.ZipFile(args.saida, 'w', allowZip64=True) as dst:
        # Copia todas as entradas do original (exceto META-INF assinaturas)
        for entry in src.infolist():
            name = entry.filename
            if entry.is_dir() or SIG.fullmatch(name):
                continue
            if name.startswith('/') or '..' in name.split('/') or name in nomes_vistos:
                raise ValueError(f'Entrada inválida ou duplicada: {name}')
            nomes_vistos.add(name)
            zi = zipfile.ZipInfo(name, date_time=entry.date_time)
            zi.external_attr = entry.external_attr
            zi.compress_type = entry.compress_type
            with src.open(entry) as source, dst.open(zi, 'w') as target:
                shutil.copyfileobj(source, target, 1024 * 1024)

        # Injeta/sobrescreve com os arquivos do repositório
        for apk_path, local_path in sorted(entradas_injetar.items()):
            if apk_path in nomes_vistos:
                # Sobrescreve entrada existente
                dst.writestr(apk_path, local_path.read_bytes())
                print(f"  sobrescrito: {apk_path}")
            else:
                zi = zipfile.ZipInfo(apk_path, date_time=(2024, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                dst.writestr(zi, local_path.read_bytes())
                nomes_vistos.add(apk_path)
                print(f"  injetado: {apk_path}")

        # Atualiza addon-manifest.xml para registrar os addons
        if MANIFEST_PATH in nomes_vistos:
            # Lê o manifesto existente e adiciona entradas faltantes
            src.seek(0)
            with src.open(MANIFEST_PATH) as f:
                manifest_text = f.read().decode('utf-8')
            for addon in ADDONS_TO_REGISTER:
                tag = f'  <addon>{addon}</addon>'
                if tag not in manifest_text:
                    # Insere antes de </addons>
                    manifest_text = manifest_text.replace(
                        '</addons>', tag + '\n</addons>', 1
                    )
                    print(f"  manifesto: {addon} registrado")
            dst.writestr(MANIFEST_PATH, manifest_text.encode('utf-8'))
        else:
            print(f"  aviso: {MANIFEST_PATH} não encontrado no APK base")

    total = len(nomes_vistos)
    print(f"\nTotal de entradas no APK injetado: {total}")
    print(f"Arquivos injetados da skin.novatv: {sum(1 for k in entradas_injetar if k.startswith('assets/addons/skin.novatv/'))}")
    print(f"Arquivos injetados de plugin.video.smarted: {sum(1 for k in entradas_injetar if k.startswith('assets/addons/plugin.video.smarted/'))}")
    print(f"Arquivos injetados de service.smarted.bootstrap: {sum(1 for k in entradas_injetar if k.startswith('assets/addons/service.smarted.bootstrap/'))}")
    print(f"\nAPK injetado gerado: {args.saida}")


if __name__ == '__main__':
    main()
