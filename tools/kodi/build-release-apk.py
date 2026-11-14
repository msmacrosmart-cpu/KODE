#!/usr/bin/env python3
"""Build an UNSIGNED release candidate from the published SMARTEDTV APK.

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
    python3 tools/kodi/build-release-apk.py [--from-version V] [--to-version V] \
        [--to-code N] [--app-label SMARTEDTV] BASE.apk OUTPUT.apk

``--app-label`` troca o nome exibido do aplicativo no string pool do
``resources.arsc`` (o Android le o rotulo dali, nao do manifesto). A troca e
feita por ``patch-resources-label.py``, que remonta o pool inteiro e falha se o
arquivo nao estiver no formato esperado.
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
BRIDGE_ADDONS = [BRIDGE, ROOT / "kodi" / "addons" / "service.smarted.bootstrap",
                 ROOT / "kodi" / "addons" / "resource.uisounds.silencio"]
SIG = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$", re.I)


def carregar_patcher():
    """Carrega o trocador de texto do resources.arsc (mesma pasta)."""
    import importlib.util

    caminho = Path(__file__).resolve().parent / "patch-resources-label.py"
    if not caminho.is_file():
        raise SystemExit(f"nao encontrei {caminho}")
    spec = importlib.util.spec_from_file_location("patch_resources", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo
MANIFEST = "assets/system/addon-manifest.xml"

# Id that the launcher dex applies as default skin at first boot.
SKIN_ADDON_ID = "skin.novatv"
SKIN_NAME = "SMARTED"
# Versao da skin padrao embarcada. 2.2.3 = skin BINGIE MOD (Kodi 21) renomeada
# para SMARTEDTV e usada como skin padrao do APK.
SKIN_VERSION = "2.2.3"
SKIN_PREFIX = "assets/addons/skin.novatv/"
# Skin classica do repositorio: vai junto como opcao de volta, para nao deixar o
# usuario sem alternativa se a skin nova nao agradar (Ajustes > Aparencia > Skin).
SKIN_CLASSIC_ID = "skin.smartedtv.classic"
SKIN_CLASSIC_NAME = "SMARTED Classica"
SKIN_CLASSIC_VERSION = "1.0.18"
SKIN_CLASSIC_PREFIX = "assets/addons/skin.smartedtv.classic/"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(source: Path, prefix: str, strict: bool = True):
    """Lista os arquivos do addon. ``strict`` valida cada .xml (addons do repo).

    Addons de terceiros (ex.: skins baixadas no CI) podem ter XML fora do padrao
    estrito do ElementTree - o Kodi aceita, entao nao barramos a build por isso.
    """
    files = sorted(p for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    if not files:
        raise SystemExit(f"No files in {source}")
    for p in files:
        if p.is_symlink():
            raise SystemExit(f"Symlink not allowed: {p}")
        if strict and p.suffix == ".xml":
            ET.parse(p)
    return {prefix + p.relative_to(source).as_posix(): p for p in files}


def skin_payload(source: Path = SKIN, addon_id: str = SKIN_ADDON_ID, name: str = SKIN_NAME,
                 version: str = SKIN_VERSION, expected_id: str = "skin.estilo.personalizado",
                 strict: bool = True):
    """Coleta a skin e reescreve addon.xml com o id/nome que o APK usa."""
    prefix = f"assets/addons/{addon_id}/"
    files = collect(source, prefix, strict=strict)
    root = ET.parse(source / "addon.xml").getroot()
    if root.get("id") != expected_id:
        raise SystemExit(f"Skin source ID mismatch: {root.get('id')} (expected {expected_id})")
    root.set("id", addon_id)
    root.set("name", name)
    root.set("provider-name", name)
    root.set("version", version)
    payload = {arcname: path.read_bytes() for arcname, path in files.items()}
    payload[prefix + "addon.xml"] = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
    if expected_id == SKIN_ADDON_ID:
        raise SystemExit("Refusing to build: source addon.xml already ships as skin.novatv")
    return payload

def main():
    argv = sys.argv[1:]
    from_version = to_version = to_code = None
    extra_addons = []
    default_skin = None
    skin_overlay = None
    app_label = None
    skin_version = SKIN_VERSION
    keep_bridge = False
    copia_classica = True
    bridge_escolhidos = None
    while len(argv) >= 2 and argv[0].startswith("--"):
        opt = argv.pop(0)
        if opt == "--from-version":
            from_version = argv.pop(0)
        elif opt == "--to-version":
            to_version = argv.pop(0)
        elif opt == "--to-code":
            to_code = int(argv.pop(0))
        elif opt == "--extra-addons":
            # pasta com addons extras (ex.: skin Bingie baixada no CI) - nao
            # versionada no repositorio, injetada so no APK desta build
            extra_addons.append(Path(argv.pop(0)))
        elif opt == "--skin-overlay":
            # pasta com arquivos que substituem parte da skin padrao (ex.: menu
            # superior do Bingie apontando para as rotas do Brazuca Play)
            skin_overlay = Path(argv.pop(0))
        elif opt == "--app-label":
            # nome exibido no Android (resources.arsc), ex.: SMARTEDTV
            app_label = argv.pop(0)
        elif opt == "--skin-version":
            # versao do addon da skin padrao (serve para o Kodi invalidar a skin
            # compilada em cache quando apenas os XMLs mudam)
            skin_version = argv.pop(0)
        elif opt == "--bridge-addons":
            # lista de addons do repositorio a REEMBARCAR (os demais ficam como
            # estao no APK base). Ex.: --bridge-addedons service.smarted.bootstrap
            bridge_escolhidos = [nome.strip() for nome in argv.pop(0).split(',') if nome.strip()]
        elif opt == "--no-classic-copy":
            # a skin classica ja e a skin padrao: nao embarcar uma segunda copia
            copia_classica = False
        elif opt == "--keep-bridge":
            # mantem os addons do repositorio (ponte + bootstrap) que ja estao no
            # APK base: build que muda so a skin, sem trocar o motor do perfil
            keep_bridge = True
        elif opt == "--default-skin":
            # skin de terceiro (ex.: Bingie) que passa a ser a skin padrao do APK,
            # renomeada para SMARTEDTV
            default_skin = Path(argv.pop(0))
        else:
            raise SystemExit(f"Unknown option: {opt}")
    if len(argv) != 2:
        raise SystemExit("Usage: build-release-apk.py [--from-version V] [--to-version V] [--to-code N] [--extra-addons DIR] [--default-skin DIR] [--skin-overlay DIR] [--app-label NOME] [--skin-version V] [--keep-bridge] [--no-classic-copy] [--bridge-addons ID,ID] BASE.apk OUTPUT.apk")
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
    # O AndroidManifest.xml e binario: o versionName vive no string pool, entao o
    # texto novo precisa ter exatamente o mesmo tamanho do antigo.
    if len(new_name.encode("utf-16-le")) != len(old_name.encode("utf-16-le")):
        raise SystemExit(
            f"versionName novo ({new_name}) precisa ter o mesmo tamanho de {old_name} "
            f"({len(old_name)} caracteres) - senao o manifest binario quebra"
        )
    print(f"Version: {old_name} ({old_code}) -> {new_name} ({new_code})")

    if default_skin is not None:
        if not default_skin.is_dir() or not (default_skin / "addon.xml").is_file():
            raise SystemExit(f"Skin padrao inexistente: {default_skin}")
        skin_files = skin_payload(default_skin, version=skin_version,
                                  expected_id="skin.titan.bingie.mod", strict=False)
        print(f"Skin padrao: {default_skin.name} -> {SKIN_ADDON_ID} ({SKIN_NAME} {skin_version})")
    else:
        skin_files = skin_payload(version=skin_version)
    if skin_overlay is not None:
        if not skin_overlay.is_dir():
            raise SystemExit(f"Overlay de skin inexistente: {skin_overlay}")
        aplicados = []
        for origem in sorted(p for p in skin_overlay.rglob("*") if p.is_file()):
            rel = origem.relative_to(skin_overlay).as_posix()
            if rel == "addon.xml":
                raise SystemExit("O overlay nao pode sobrescrever o addon.xml da skin")
            destino = SKIN_PREFIX + rel
            if destino not in skin_files:
                raise SystemExit(f"Overlay aponta para arquivo inexistente na skin: {rel}")
            skin_files[destino] = origem.read_bytes()
            aplicados.append(rel)
        print("Overlay aplicado na skin padrao: " + ", ".join(aplicados))
    if copia_classica:
        skin_files.update(skin_payload(SKIN, SKIN_CLASSIC_ID, SKIN_CLASSIC_NAME, SKIN_CLASSIC_VERSION))
    bridge_files = {}
    bridge_ids = []
    extras = []
    for pasta in extra_addons:
        if not pasta.is_dir():
            raise SystemExit(f"Pasta de addons extras inexistente: {pasta}")
        for filho in sorted(pasta.iterdir()):
            if (filho / "addon.xml").is_file():
                extras.append(filho)
            elif filho.is_dir():
                for neto in sorted(filho.iterdir()):
                    if (neto / "addon.xml").is_file():
                        extras.append(neto)
    base_addons = [] if keep_bridge else list(BRIDGE_ADDONS)
    if bridge_escolhidos is not None:
        por_id = {pasta.name: pasta for pasta in base_addons}
        desconhecidos = [nome for nome in bridge_escolhidos if nome not in por_id]
        if desconhecidos:
            raise SystemExit("Addons desconhecidos em --bridge-addons: %s" % ", ".join(desconhecidos))
        base_addons = [por_id[nome] for nome in bridge_escolhidos]
        print("Addons do repositorio reembarcados: " + ", ".join(nome for nome in bridge_escolhidos))
    if keep_bridge:
        print("Ponte e bootstrap mantidos como estao no APK base (--keep-bridge)")
    for addon_dir in base_addons + extras:
        addon_id = ET.parse(addon_dir / "addon.xml").getroot().get("id")
        # a skin que virou skin padrao nao entra duas vezes (ja esta em skin.novatv)
        if default_skin is not None and addon_id == "skin.titan.bingie.mod":
            print(f"Addon extra {addon_id} ja embarcado como skin padrao: ignorado")
            continue
        if addon_id != addon_dir.name:
            raise SystemExit(f"Addon ID mismatch: {addon_dir.name} declares {addon_id}")
        if addon_id in bridge_ids:
            continue
        bridge_ids.append(addon_id)
        bridge_files.update(collect(addon_dir, f"assets/addons/{addon_id}/",
                                    strict=addon_dir in BRIDGE_ADDONS))

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
        skins_manifesto = [SKIN_ADDON_ID] + ([SKIN_CLASSIC_ID] if copia_classica else [])
        for addon_id in skins_manifesto + bridge_ids:
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
        if app_label:
            if "resources.arsc" not in names:
                raise SystemExit("APK sem resources.arsc: nao da para trocar o nome exibido")
            patcher = carregar_patcher()
            arsc, trocas = patcher.principal(src.read("resources.arsc"), "SMARTED-TV", app_label)
            replacements["resources.arsc"] = arsc
            print(f"Nome exibido: SMARTED-TV -> {app_label} "
                  f"({trocas} ocorrencia(s) no resources.arsc)")
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
                    if item.filename.startswith(SKIN_PREFIX) or item.filename.startswith(SKIN_CLASSIC_PREFIX):
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
    print("Skin padrao: " + f"{SKIN_ADDON_ID} ({SKIN_NAME} {SKIN_VERSION})")
    print("Skin classica: " + f"{SKIN_CLASSIC_ID} ({SKIN_CLASSIC_NAME} {SKIN_CLASSIC_VERSION})")
    print("Bridge addons: " + ", ".join(bridge_ids))
    print("Profile (assets/smarted/profile/) left untouched — launcher dex applies the default skin at first boot.")
    print("Run tools/kodi/verify-boot-integrity.py on the candidate before signing.")


if __name__ == "__main__":
    main()
