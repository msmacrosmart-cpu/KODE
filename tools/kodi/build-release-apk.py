#!/usr/bin/env python3
"""Build an UNSIGNED release candidate from the published SMARTED-TV APK.

ZIP-level update only (no apktool decode): bumps versionName/versionCode,
refreshes skin.novatv + plugin.video.smarted from this repo, preserves every
other entry (native libs, dex, backup/profile data) byte for byte, and strips
old signatures. Align + sign + verify are separate steps (see workflow).

Usage:
    python3 tools/kodi/build-release-apk.py BASE.apk OUTPUT.apk
"""
import hashlib
import re
import struct
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SKIN = ROOT / "kodi" / "skin.estilo.personalizado"
BRIDGE = ROOT / "kodi" / "addons" / "plugin.video.smarted"
SIG = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\\.(?:SF|RSA|DSA|EC))$", re.I)
MANIFEST = "assets/system/addon-manifest.xml"
SETTINGS = "assets/system/settings/settings.xml"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(source: Path, prefix: str):
    files = sorted(p for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    if not files:
        raise SystemExit(f"No files in {source}")
    for p in files:
        if p.is_symlink():
            raise SystemExit(f"Symlink not allowed: {p}")
        if p.suffix == ".xml":
            ET.parse(p)
    return {prefix + p.relative_to(source).as_posix(): p for p in files}


def main():
    argv = sys.argv[1:]
    from_version = to_version = to_code = None
    while len(argv) >= 2 and argv[0].startswith("--"):
        opt = argv.pop(0)
        if opt == "--from-version":
            from_version = argv.pop(0)
        elif opt == "--to-version":
            to_version = argv.pop(0)
        elif opt == "--to-code":
            to_code = int(argv.pop(0))
        else:
            raise SystemExit(f"Unknown option: {opt}")
    if len(argv) != 2:
        raise SystemExit("Usage: build-release-apk.py [--from-version V] [--to-version V] [--to-code N] BASE.apk OUTPUT.apk")
    base, out = Path(argv[0]), Path(argv[1])
    if base.resolve() == out.resolve():
        raise SystemExit("Input and output must differ")
    if out.exists():
        raise SystemExit("Output already exists")

    # --- Identity check (package + current version) ---
    from pyaxmlparser import APK

    apk = APK(str(base))
    if apk.package != "org.xbmc.kodi":
        raise SystemExit(f"Unexpected package: {apk.package}")
    old_name, old_code = apk.version_name, int(apk.version_code)
    if from_version is not None and old_name != from_version:
        raise SystemExit(f"Unexpected base versionName: {old_name} (expected {from_version})")
    # Determine target version: explicit --to-version/--to-code or auto-bump.
    if to_version is not None:
        new_name = to_version
    elif from_version is not None and old_name == from_version:
        parts = old_name.split(".")
        new_name = ".".join(parts[:-1] + [str(int(parts[-1]) + 1)])
    else:
        raise SystemExit("Provide --to-version (and --to-code) or a matching --from-version")
    new_code = to_code if to_code is not None else old_code + 1
    print(f"Version: {old_name} ({old_code}) -> {new_name} ({new_code})")

    skin_files = collect(SKIN, "assets/addons/skin.estilo.personalizado/")
    bridge_files = collect(BRIDGE, "assets/addons/plugin.video.smarted/")
    if ET.parse(SKIN / "addon.xml").getroot().get("id") != "skin.estilo.personalizado":
        raise SystemExit("Skin ID mismatch")
    if ET.parse(BRIDGE / "addon.xml").getroot().get("id") != "plugin.video.smarted":
        raise SystemExit("Bridge ID mismatch")

    with zipfile.ZipFile(base) as src:
        names = [e.filename for e in src.infolist() if not e.is_dir()]
        if len(names) != len(set(names)):
            raise SystemExit("Duplicate ZIP members in base APK")
        if "AndroidManifest.xml" not in names or MANIFEST not in names:
            raise SystemExit("Base APK missing manifest files")

        manifest_bin = src.read("AndroidManifest.xml")
        old_v, new_v = old_name.encode("utf-16le"), new_name.encode("utf-16le")
        old_c, new_c = struct.pack("<I", old_code), struct.pack("<I", new_code)
        if manifest_bin.count(old_v) != 1 or manifest_bin.count(old_c) != 1:
            raise SystemExit("Manifest version data is not unique")
        manifest_bin = manifest_bin.replace(old_v, new_v).replace(old_c, new_c)

        # Addon manifest: ensure skin + bridge entries exist (no duplicates).
        addon_manifest = src.read(MANIFEST)
        if addon_manifest.count(b"</addons>") != 1:
            raise SystemExit("Unexpected addon manifest")
        for addon_id in ("skin.estilo.personalizado", "plugin.video.smarted"):
            if f">{addon_id}<".encode() not in addon_manifest:
                addon_manifest = addon_manifest.replace(
                    b"</addons>",
                    f'  <addon optional="true">{addon_id}</addon>\n</addons>'.encode(),
                )
        ET.fromstring(addon_manifest)

        replacements = {
            "AndroidManifest.xml": manifest_bin,
            MANIFEST: addon_manifest,
        }
        # Refresh skin + bridge from repo (replace if present, add if missing).
        for arcname, path in {**skin_files, **bridge_files}.items():
            replacements[arcname] = path.read_bytes()

        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(out, "w", allowZip64=True) as dst:
                seen = set()
                for item in src.infolist():
                    if item.is_dir() or SIG.fullmatch(item.filename):
                        continue
                    if item.filename in seen:
                        raise SystemExit("Duplicate ZIP member")
                    seen.add(item.filename)
                    if item.filename in replacements:
                        dst.writestr(item, replacements[item.filename])
                    else:
                        with src.open(item) as inp, dst.open(item, "w") as target:
                            import shutil

                            shutil.copyfileobj(inp, target, 1024 * 1024)
                for arcname, data in replacements.items():
                    if arcname not in seen:
                        dst.writestr(arcname, data, compress_type=zipfile.ZIP_DEFLATED)
        except BaseException:
            out.unlink(missing_ok=True)
            raise

    print(f"Unsigned candidate: {out} ({out.stat().st_size} bytes, SHA-256 {sha256(out)})")
    print("Runtime remains untested. Align + sign + verify are separate steps.")


if __name__ == "__main__":
    main()
