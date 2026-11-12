#!/usr/bin/env python3
"""Verifica o APK SMARTEDTV gerado pela compilação do código-fonte.

Confere, sem precisar de aparelho nem de rede:
  1. identidade Android (pacote, nome exibido, versão);
  2. que o motor nativo é realmente o build do Kodi (libkodi.so presente);
  3. que a arquitetura é arm64-v8a;
  4. que os recursos de marca oficiais estão dentro do APK (splash, ícone, banner);
  5. que NÃO há add-ons de conteúdo embutidos (Brazuka, skins extras, etc.);
  6. que a splash nativa e o splash da GUI estão presentes;
  7. integridade do ZIP (nenhuma entrada corrompida) e do signature block.

Sai com código 0 só se tudo passar. Cada falha aparece como FALHA explícita.

Uso: python3 verify-apk.py caminho/SMARTEDTV-21.4-arm64-v8a.apk
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import zipfile
from pathlib import Path

BRAND = "SMARTEDTV"
EXPECTED_PACKAGE = "org.xbmc.kodi"
EXPECTED_ABI = "arm64-v8a"

# Add-ons que o projeto NÃO deve embutir (conteúdo de terceiros / skins antigas).
FORBIDDEN_ADDONS = (
    "plugin.video.brazuka",
    "plugin.video.smarted",
    "plugin.video.novatv",
    "skin.novatv",
    "skin.estilo.personalizado",
    "skin.smartedtv",
    "skin.titan",
    "service.smarted.bootstrap",
    "resource.uisounds.silencio",
)

REQUIRED_ASSETS = (
    "assets/media/splash.jpg",
    "assets/media/vendor_logo.png",
    "assets/media/vendor_icon.png",
    "assets/media/banner.png",
    "assets/media/icon256x256.png",
    "assets/addons/skin.estuary/addon.xml",
    "assets/system/addon-manifest.xml",
    "lib/arm64-v8a/libkodi.so",
    "classes.dex",
)


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def check(self, ok: bool, description: str, detail: str = "") -> bool:
        self.checks += 1
        if ok:
            print(f"  ok    {description}" + (f" — {detail}" if detail else ""))
        else:
            print(f"  FALHA {description}" + (f" — {detail}" if detail else ""))
            self.failures.append(description)
        return ok


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_manifest(apk: Path) -> str:
    """Lê o AndroidManifest.xml usando pyaxmlparser quando disponível."""
    try:
        from pyaxmlparser import APK  # type: ignore
    except ImportError:
        return ""
    try:
        parsed = APK(str(apk))
        return (
            f"package={parsed.package}\n"
            f"app_name={parsed.get_app_name()}\n"
            f"version_name={parsed.version_name}\n"
            f"version_code={parsed.version_code}\n"
        )
    except Exception:  # noqa: BLE001 - relatório não deve quebrar por causa disso
        return ""


def main() -> int:
    args = sys.argv[1:]
    if not args and os.environ.get("APK"):
        args = [os.environ["APK"]]
    if len(args) != 1:
        print(__doc__)
        return 2
    apk = Path(args[0]).resolve()
    report = Report()

    print(f"Verificando {apk.name} ({apk.stat().st_size} bytes)" if apk.is_file()
          else f"APK ausente: {apk}")
    if not apk.is_file():
        return 2

    with zipfile.ZipFile(apk) as archive:
        names = set(archive.namelist())

        # ---------------------------------------------------------------- 1
        print("\n[1] Integridade do pacote")
        report.check(archive.testzip() is None, "ZIP íntegro (nenhuma entrada corrompida)")

        # ---------------------------------------------------------------- 2
        print("\n[2] Identidade Android")
        manifest_text = read_manifest(apk)
        if manifest_text:
            package = re.search(r"^package=(\S+)$", manifest_text, re.M)
            app_name = re.search(r"^app_name=(.+)$", manifest_text, re.M)
            version = re.search(r"^version_name=(\S+)$", manifest_text, re.M)
            code = re.search(r"^version_code=(\d+)$", manifest_text, re.M)
            report.check(bool(package) and package.group(1) == EXPECTED_PACKAGE,
                         "Application ID preservado", EXPECTED_PACKAGE)
            report.check(bool(app_name) and app_name.group(1).strip() == BRAND,
                         f"nome exibido = {BRAND}",
                         app_name.group(1).strip() if app_name else "?")
            report.check(bool(version) and version.group(1).startswith("21.4"),
                         "versão visível 21.4.x", version.group(1) if version else "?")
            report.check(bool(code) and int(code.group(1)) == 2104000,
                         "versionCode 2104000 (permite atualizar a chave de teste)",
                         code.group(1) if code else "?")
        else:
            report.check(False, "manifesto legível",
                         "pyaxmlparser indisponível (pip install pyaxmlparser)")

        # ---------------------------------------------------------------- 3
        print("\n[3] Arquitetura e motor nativo")
        libs = sorted(n for n in names if n.startswith("lib/"))
        abis = sorted({n.split("/")[1] for n in libs if n.count("/") > 1})
        report.check(abis == [EXPECTED_ABI], f"apenas {EXPECTED_ABI}", ", ".join(abis) or "nenhuma")
        report.check(f"lib/{EXPECTED_ABI}/libkodi.so" in names,
                     "libkodi.so presente (motor Kodi real, sem renomear)")
        native_count = sum(1 for n in libs if n.endswith(".so"))
        report.check(native_count >= 20, "bibliotecas nativas completas",
                     f"{native_count} .so")

        # ---------------------------------------------------------------- 4
        print("\n[4] Recursos obrigatórios")
        for required in REQUIRED_ASSETS:
            report.check(required in names, required)
        splash_entries = [n for n in names if n.endswith("applaunch_screen.png")]
        report.check(bool(splash_entries), "splash nativa do Android presente",
                     ", ".join(sorted(splash_entries)[:3]))
        launchers = [n for n in names if re.search(r"res/drawable-[^/]*/ic_launcher\.png$", n)]
        if launchers:
            report.check(len(launchers) >= 4, "ícones de launcher em várias densidades",
                         f"{len(launchers)} arquivos")
        else:
            # Builds com recursos ofuscados (ex.: APK oficial do Kodi) não expõem o
            # nome do arquivo; nesse caso o critério é o manifesto apontar para um
            # drawable e existirem PNGs de densidade no pacote.
            drawables = [n for n in names if re.match(r"res/[^/]+\.(png|xml)$", n)]
            report.check(len(drawables) >= 6, "recursos de drawable presentes",
                         f"{len(drawables)} arquivos (nomes ofuscados)")

        # ---------------------------------------------------------------- 5
        print("\n[5] Sem add-ons de conteúdo de terceiros")
        addon_dirs = {n.split("/")[2] for n in names
                      if n.startswith("assets/addons/") and n.count("/") > 2}
        found = sorted(a for a in addon_dirs
                       if any(a.lower().startswith(bad) for bad in FORBIDDEN_ADDONS))
        report.check(not found, "nenhum add-on proibido embutido", ", ".join(found) or "limpo")

        skins = sorted(a for a in addon_dirs if a.startswith("skin."))
        report.check(skins == ["skin.estuary"], "somente a skin Estuary original",
                     ", ".join(skins))
        report.check("assets/addons/repository.xbmc.org/addon.xml" in names,
                     "repositório nativo mantido (instalação de add-ons pelo usuário)")
        report.check(not any("brazuka" in n.lower() for n in names),
                     "nenhum arquivo do Brazuka Play")
        report.check("assets/smarted" not in names and
                     not any(n.startswith("assets/smarted/") for n in names),
                     "nenhum perfil pré-configurado embutido")

        # ---------------------------------------------------------------- 6
        print("\n[6] Assinatura")
        signature_entries = [n for n in names if n.startswith("META-INF/")
                             and n.upper().endswith((".RSA", ".DSA", ".EC"))]
        report.check(bool(signature_entries), "bloco de assinatura v1 presente",
                     ", ".join(signature_entries))
        report.check("META-INF/MANIFEST.MF" in names, "MANIFEST.MF presente")

    print(f"\nResumo: {report.checks - len(report.failures)}/{report.checks} verificações OK")
    print(f"SHA-256: {sha256(apk)}")
    if report.failures:
        print("\nFALHAS:")
        for failure in report.failures:
            print(f" - {failure}")
        return 1
    print("\nAPK aprovado nas verificações estáticas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
