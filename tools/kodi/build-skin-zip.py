#!/usr/bin/env python3
"""Build SKIN_KODI_OMEGA21.zip from kodi/skin.novatv (Kodi Omega 21).

Structure required by Kodi: the ZIP must contain a single top-level
folder named after the skin id (skin.novatv) with addon.xml inside it.
Development-only files (README.md, docs/) are excluded from the ZIP.

Usage:
    python3 tools/kodi/build-skin-zip.py [--output PATH] [--check]

Without --check, writes the ZIP and prints size + SHA-256 + file list.
With --check, only validates an existing ZIP (structure + XML parse).
"""
import argparse
import hashlib
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SKIN_DIR = ROOT / "kodi" / "skin.novatv"
DEFAULT_OUTPUT = ROOT / "ENTREGA_FINAL" / "SKIN_KODI_OMEGA21.zip"
SKIN_ID = "skin.novatv"

# Development-only paths inside the skin folder, excluded from the ZIP.
EXCLUDED = {"README.md", "docs"}


def collect_files():
    files = []
    for path in sorted(SKIN_DIR.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(SKIN_DIR)
        if rel.parts[0] in EXCLUDED:
            continue
        if "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        files.append(path)
    return files


def build(output: Path):
    files = collect_files()
    if not files:
        print("ERROR: no skin files found", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            arcname = f"{SKIN_ID}/{path.relative_to(SKIN_DIR).as_posix()}"
            zf.write(path, arcname)
    print(f"Wrote {output} ({len(files)} files, {output.stat().st_size} bytes)")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"SHA-256: {digest}")
    with zipfile.ZipFile(output) as zf:
        for name in zf.namelist():
            print(f"  {name}")
    return 0


def check(zip_path: Path):
    errors = []
    if not zip_path.is_file():
        print(f"ERROR: {zip_path} not found", file=sys.stderr)
        return 1
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if f"{SKIN_ID}/addon.xml" not in names:
            errors.append(f"missing {SKIN_ID}/addon.xml at ZIP root")
        for name in names:
            if not name.startswith(f"{SKIN_ID}/"):
                errors.append(f"unexpected top-level entry: {name}")
            if name.endswith(".xml"):
                try:
                    ET.fromstring(zf.read(name))
                except ET.ParseError as exc:
                    errors.append(f"invalid XML {name}: {exc}")
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print(f"OK: {zip_path} ({len(names)} entries, structure + XML valid)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--check", action="store_true", help="validate existing ZIP only")
    args = parser.parse_args()
    if args.check:
        return check(Path(args.output))
    return build(Path(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
