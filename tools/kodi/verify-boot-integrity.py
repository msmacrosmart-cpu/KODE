#!/usr/bin/env python3
"""Simulate the SMARTED-TV launcher boot flow against a built APK.

The launcher (org.smartedtv.bootstrap, classes3.dex) performs, at first boot:

  1. if <data>/.kodi exists -> profile preserved, return (no seed needed);
  2. otherwise it checks the staged profile:
       - assets/smarted/profile/         must be a directory
       - assets/smarted/profile-manifest.txt must be a file (< 2 MB)
       - sha256(profile-manifest.txt) == 1447de81... (hardcoded in the dex)
       - copyVerified(): every manifest entry (sha256 + size) must match the
         file under assets/smarted/profile/ (any mismatch -> boot failure)
       - setDefaultSkin(staged/userdata/guisettings.xml): the exact line
             <setting id="lookandfeel.skin" default="true">skin.estuary</setting>
         must be present; it is rewritten to
             <setting id="lookandfeel.skin">skin.novatv</setting>
         (absence -> "Unexpected skin setting in profile" -> boot failure)
       - re-hash the manifest (unchanged) -> publish profile -> boot.

This script verifies all of the above statically against an APK, so a build
that would fail on device is caught before signing/release.

Usage:
    python3 tools/kodi/verify-boot-integrity.py BUILT.apk [BASE.apk]
"""
import hashlib
import sys
import zipfile
from pathlib import Path

MANIFEST_PATH = "assets/smarted/profile-manifest.txt"
PROFILE_PREFIX = "assets/smarted/profile/"
OLD_SKIN_LINE = '<setting id="lookandfeel.skin" default="true">skin.estuary</setting>'
NEW_SKIN_LINE = '<setting id="lookandfeel.skin">skin.novatv</setting>'
EXPECTED_MANIFEST_SHA256 = "1447de816a44ecc11c42c2c315cf20e61c9baa037e914a13293711cf152d1ede"
SKIN_ADDON_XML = "assets/addons/skin.novatv/addon.xml"
BUILD_SCRIPT = Path(__file__).resolve().parent / "build-release-apk.py"


def expected_skin_version() -> str:
    """Versao da skin vem do script de build (evita quebrar a cada release)."""
    import re

    try:
        text = BUILD_SCRIPT.read_text(encoding="utf-8")
        match = re.search(r'SKIN_VERSION\s*=\s*"([^"]+)"', text)
        if match:
            return match.group(1)
    except OSError:
        pass
    return "1.0.18"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    if len(sys.argv) not in (2, 3):
        raise SystemExit("Usage: verify-boot-integrity.py BUILT.apk [BASE.apk]")
    built = Path(sys.argv[1])
    base = Path(sys.argv[2]) if len(sys.argv) == 3 else None

    failures = []
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, ok, detail))
        if not ok:
            failures.append(f"{name}: {detail}")

    with zipfile.ZipFile(built) as z:
        names = set(z.namelist())

        # --- 1. profile-manifest.txt present + hash matches the dex constant ---
        if MANIFEST_PATH in names:
            manifest = z.read(MANIFEST_PATH)
            h = sha256_bytes(manifest)
            check(
                "manifest sha256 == dex const",
                h == EXPECTED_MANIFEST_SHA256,
                f"got {h}",
            )
            check("manifest size < 2 MB", len(manifest) < 2 * 1024 * 1024, f"{len(manifest)} bytes")
            lines = manifest.decode("utf-8").splitlines()
            check("manifest has entries", len(lines) > 0, f"{len(lines)} lines")

            # --- 2. every manifest entry matches the file in the APK (copyVerified) ---
            checked = mismatched = missing = 0
            for line in lines:
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) != 3:
                    mismatched += 1
                    continue
                want_sha, want_size, rel = parts[0].strip(), int(parts[1]), parts[2]
                path = PROFILE_PREFIX + rel
                if path not in names:
                    missing += 1
                    continue
                data = z.read(path)
                checked += 1
                if sha256_bytes(data) != want_sha or len(data) != want_size:
                    mismatched += 1
            check("all manifest entries verified", mismatched == 0 and missing == 0,
                  f"{checked} checked, {missing} missing, {mismatched} mismatched")

            # --- 3. guisettings OLD_SKIN line present (setDefaultSkin) ---
            gs_path = PROFILE_PREFIX + "userdata/guisettings.xml"
            if gs_path in names:
                gs = z.read(gs_path).decode("utf-8")
                check("guisettings has OLD_SKIN line", OLD_SKIN_LINE in gs, "line ausente")
            else:
                check("guisettings present", False, gs_path)
        else:
            check("profile-manifest.txt present", False, MANIFEST_PATH)

        # --- 4. skin.novatv is the SMARTEDTV skin (id + addon.xml) ---
        if SKIN_ADDON_XML in names:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(z.read(SKIN_ADDON_XML))
            check("skin.novatv addon id", root.get("id") == "skin.novatv", f"got {root.get('id')}")
            wanted = expected_skin_version()
            check("skin.novatv version", root.get("version") == wanted,
                  f"got {root.get('version')} (esperado {wanted})")
            # the dex rewrites the skin line to skin.novatv — skin must load that id
        else:
            check("skin.novatv addon.xml present", False, SKIN_ADDON_XML)

        # --- 5. profile untouched vs base (no post-build patching) ---
        if base is not None:
            with zipfile.ZipFile(base) as b:
                base_names = set(b.namelist())
                profile_names = {n for n in names if n.startswith(PROFILE_PREFIX) and n in base_names}
                diff = 0
                for n in profile_names:
                    if z.read(n) != b.read(n):
                        diff += 1
                check("profile byte-identical to base", diff == 0, f"{diff} files changed")

    print(f"Verificação de boot: {built} ({built.stat().st_size} bytes)")
    for name, ok, detail in checks:
        mark = "OK  " if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))
    if failures:
        print(f"\nFALHAS ({len(failures)}):")
        for f in failures:
            print("  -", f)
        raise SystemExit(1)
    print("\nTodos os checks passaram: o launcher dex deve preparar o perfil no primeiro boot sem falha.")


if __name__ == "__main__":
    main()
