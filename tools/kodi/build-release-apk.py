#!/usr/bin/env python3
"""Build an UNSIGNED release candidate from the published SMARTED-TV APK.

ZIP-level update only (no apktool decode): bumps versionName/versionCode,
replaces assets/addons/skin.novatv/ wholesale with the SMARTEDTV skin from
this repo (addon.xml rewritten to id=skin.novatv — the id the launcher dex
applies at first boot), refreshes plugin.video.smarted, preserves every other
entry (native libs, dex, profile data) byte for byte, and strips old signatures.

IMPORTANT (boot fix v1.0.25 -> v1.0.26):
  The launcher (org.smartedtv.bootstrap, classes3.dex) integrity-checks the
  seeded profile: it hashes assets/smarted/profile-manifest.txt (expected
  1447de81...) and verifies every file under assets/smarted/profile/ against
  that manifest, then rewrites the exact line
      <setting id="lookandfeel.skin" default="true">skin.estuary</setting>
  in the staged userdata/guisettings.xml to
      <setting id="lookandfeel.skin">skin.novatv</setting>
  before publishing the profile.
  Therefore THIS build NEVER touches anything under assets/smarted/profile/
  (the dex applies the default skin itself). The skin is injected as the
  skin.novatv addon so the first boot activates it without profile failure.

Usage:
    python3 tools/kodi/build-release-apk.py [--from-version V] [--to-version V] [--to-code N] BASE.apk OUTPUT.apk
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
# Addons do repositório injetados como addons de sistema (assets/addons/).
# service.smarted.bootstrap garante o Brazuca Play registrado no primeiro boot.
BRIDGE_ADDONS = [BRIDGE, ROOT / "kodi" / "addons" / "service.smarted.bootstrap"]
SIG = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$", re.I)
MANIFEST = "assets/system/addon-manifest.xml"

# Id that the launcher dex applies as default skin at first boot.
SKIN_ADDON_ID = "skin.novatv"
SKIN_NAME = "SMARTEDTV"
SKIN_VERSION = "1.0.2"
SKIN_PREFIX = "assets/addons/skin.novatv/"


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


def skin_payload():
    """Collect the skin files and rewrite addon.xml to the shipped id."""
    files = collect(SKIN, "assets/addons/skin.novatv/")
    root = ET.parse(SKIN / "addon.xml").getroot()
    if root.get("id") != "skin.estilo.personalizado":
        raise SystemExit(f"Skin source ID mismatch: {root.get('id')} (expected skin.estilo.personalizado)")
    root.set("id", SKIN_ADDON_ID)
    root.set("name", SKIN_NAME)
    root.set("provider-name", SKIN_NAME)
    root.set("version", SKIN_VERSION)
    payload = {arcname: path.read_bytes() for arcname, path in files.items()}
    payload["assets/addons/skin.novatv/addon.xml"] = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
    if ET.parse(SKIN / "addon.xml").getroot().get("id") == SKIN_ADDON_ID:
        raise SystemExit("Refusing to build: source addon.xml already ships as skin.novatv")
    return payload


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
    if to_version is not None:
        new_name = to_version
    elif from_version is not None and old_name == from_version:
        parts = old_name.split(".")
        new_name = ".".join(parts[:-1] + [str(int(parts[-1]) + 1)])
    else:
        raise SystemExit("Provide --to-version (and --to-code) or a matching --from-version")
    new_code = to_code if to_code is not None else old_code + 1
    print(f"Version: {old_name} ({old_code}) -> {new_name} ({new_code})")

    skin_files = skin_payload()
    bridge_files = {}
    bridge_ids = []
    for addon_dir in BRIDGE_ADDONS:
        addon_id = ET.parse(addon_dir / "addon.xml").getroot().get("id")
        if addon_id != addon_dir.name:
            raise SystemExit(f"Addon ID mismatch: {addon_dir.name} declares {addon_id}")
        bridge_ids.append(addon_id)
        bridge_files.update(collect(addon_dir, f"assets/addons/{addon_id}/"))

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

        # Addon manifest: ensure skin.novatv + bridge entries exist (no duplicates).
        addon_manifest = src.read(MANIFEST)
        if addon_manifest.count(b"</addons>") != 1:
            raise SystemExit("Unexpected addon manifest")
        for addon_id in [SKIN_ADDON_ID] + bridge_ids:
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
        for arcname, data in {**skin_files, **bridge_files}.items():
            replacements[arcname] = data if isinstance(data, (bytes, bytearray)) else Path(data).read_bytes()

        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(out, "w", allowZip64=True) as dst:
                seen = set()
                for item in src.infolist():
                    if item.is_dir() or SIG.fullmatch(item.filename):
                        continue
                    if item.filename in seen:
                        raise SystemExit("Duplicate ZIP member")
                    if item.filename.startswith(SKIN_PREFIX):
                        # skin.novatv is replaced wholesale by the repo payload
                        # (the base's skin.novatv entries are dropped).
                        continue
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
    print("Bridge addons: " + ", ".join(bridge_ids))
    print("Profile (assets/smarted/profile/) left untouched — launcher dex applies the default skin at first boot.")
    print("Run tools/kodi/verify-boot-integrity.py on the candidate before signing.")


if __name__ == "__main__":
    main()
