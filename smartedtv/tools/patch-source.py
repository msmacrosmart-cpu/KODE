#!/usr/bin/env python3
"""Aplica a identidade visual SMARTEDTV ao código-fonte do Kodi 21.3-Omega.

Roda DEPOIS de `git clone --branch 21.3-Omega` e ANTES de compilar. É idempotente
e falha de forma explícita quando o upstream muda de formato — nada é aplicado
"no escuro".

## Decisão central: marca visível sem renomear o produto interno

O Kodi deriva VÁRIAS coisas de `APP_NAME` no `version.txt`:

    APP_NAME Kodi  ->  libkodi.so            (SONAME carregado pelo MainActivity)
                   ->  assets/addons/kodi.binary.*
                   ->  diretório de perfil .kodi  (SettingsComponent: HOME + "." + APP_NAME)
                   ->  python3.11 / pacotes site-packages
                   ->  variáveis KODI_HOME, KODI_BIN_HOME, KODI_DATA …

Trocar `APP_NAME` para SMARTEDTV renomearia `libkodi.so` e o perfil `.kodi`,
quebrando a compatibilidade de dados e o carregamento da biblioteca nativa — o
usuário pediu explicitamente para NÃO alterar identificadores internos nem
caminhos. Por isso o patch mantém `APP_NAME` (e `APP_NAME_LC`) intactos e
substitui **apenas os textos de exibição**, nos pontos onde o Kodi mostra o nome:

| Onde o usuário vê        | Como o Kodi obtém o texto         | Correção cirúrgica |
|--------------------------|-----------------------------------|--------------------|
| Nome do app no launcher  | `strings.xml @APP_NAME@`           | `strings.xml.in` → SMARTEDTV |
| "Starting <nome>…" splash| `Splash.java.in` `@APP_NAME@`      | texto fixo SMARTEDTV |
| Diálogo de permissões     | `Splash.java.in` `@APP_NAME@`     | texto fixo SMARTEDTV |
| Tag de log (logcat)       | `Splash/Main @APP_NAME@`          | SMARTEDTV |
| Tela inicial (Home)       | strings #9 "Kodi media center"     | SMARTEDTV media center |
| Tela "Sobre"/sistema      | strings #482 + `GUIWindowSystemInfo` | SMARTEDTV + versão |
| Nome padrão do aparelho   | settings `services.devicename`     | SMARTEDTV |
| Splash GUI                | media/splash.jpg                   | arte oficial |
| Splash nativo Android     | media/applaunch_screen.png         | arte oficial |
| Ícones / launcher / banner| media/*.png + packaging media      | arte oficial |
| Marca na Home/Login       | media/vendor_logo.png              | arte oficial |

`GUIWindowSystemInfo` monta o rótulo como `GetAppName() + " " + GetVersion()`;
o patch troca essa única linha por `CSysInfo::GetDisplayName()`, uma função nova
em `SystemInfo` que devolve o nome de exibição, para que a tela de informações
mostre "SMARTEDTV 21.4.0" sem mexer em `GetAppName()` (usado em logs, User-Agent
e caminhos).

## Preservado de propósito

- `APP_PACKAGE org.xbmc.kodi` → Application ID, permissões, assinatura e a
  possibilidade de atualizar a instalação existente.
- `APP_NAME_LC kodi` → `libkodi.so`, `kodi.binary.*`, `python3.11`, `KODI_*`,
  diretório `.kodi` (mesmo perfil do Kodi oficial, sem migração de dados).
- `ADDON_API 21.3.0` → compatibilidade com add-ons e repositórios existentes.
- Ids de addon, namespaces Java, `ADDON_REPOS`.

Uso:
    python3 patch-source.py /caminho/kodi-src [--brand-dir ...] [--language-addon ...]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Identidade
# ---------------------------------------------------------------------------
BRAND_NAME = "SMARTEDTV"
BRAND_DISPLAY_VERSION = "21.4.0"
BRAND_VERSION_MAJOR = "21"
BRAND_VERSION_MINOR = "4"
BRAND_VERSION_CODE = "21.4.0"   # -> 2104000 no Android (cmake/scripts/android/Install.cmake)
BRAND_VERSION_TAG = "Omega"     # mantém o ciclo Omega; GetSuffix() != vazio
BRAND_COMPANY = "SMARTEDTV"

# APP_NAME e APP_NAME_LC NÃO são alterados (ver docstring). O guard abaixo garante isso.
EXPECTED_APP_NAME = "Kodi"
EXPECTED_APP_PACKAGE = "org.xbmc.kodi"

# Textos visíveis que citam o produto (msgid = texto em en_gb)
STRING_REPLACEMENTS_EN = {
    "Kodi media center": "SMARTEDTV media center",
    "About Kodi": "About SMARTEDTV",
    "Kodi GIT": "SMARTEDTV GIT",
    "Use Kodi": "Use SMARTEDTV",
    "Kodi virtual backend": "SMARTEDTV virtual backend",
    "Use Kodi virtual keyboard": "Use SMARTEDTV virtual keyboard",
    "Kodi virtual keyboard": "SMARTEDTV virtual keyboard",
    "When you need to enter some text, Kodi virtual keyboard will show up instead of the built-in tvOS keyboard":
        "When you need to enter some text, SMARTEDTV virtual keyboard will show up instead of the built-in tvOS keyboard",
    "Kodi is brought to you with love from the Kodi Foundation, a 501(c)(3) nonprofit organization. Thank you for using our software!":
        "SMARTEDTV is an open source media center. Thank you for using our software!",
}

STRING_REPLACEMENTS_PT = {
    "Sobre o Kodi": "Sobre o SMARTEDTV",
    "Usar Kodi": "Usar SMARTEDTV",
    "Kodi backend virtual": "SMARTEDTV backend virtual",
    "Kodi é oferecido a você com amor pela Fundação Kodi, uma organização sem fins lucrativos 501(c)(3). Obrigado por usar nosso software!":
        "SMARTEDTV é um media center de código aberto. Obrigado por usar nosso software!",
}

# Strings #9 e #482 aparecem na Home e na tela "Sobre": garante consistência
# mesmo que alguém traduza por cima depois.
PO_MSGTXT_OVERRIDES = {en: None for en in ()}  # placeholder para manter o mapa explícito
PO_OVERRIDES = {
    9: ("Kodi media center", "SMARTEDTV media center"),
    482: ("About Kodi", "About SMARTEDTV"),
}


class PatchError(RuntimeError):
    pass


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def replace_once(path: Path, old: str, new: str, description: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise PatchError(
            f"{description}: esperava 1 ocorrência em {path.relative_to(path.parents[-1])}, "
            f"encontrei {count}. O upstream mudou; revise o patch.\n--- trecho ---\n{old[:200]}"
        )
    write(path, text.replace(old, new))
    print(f"  ok  {description}")


# ---------------------------------------------------------------------------
# 1. version.txt — versão e metadados (APP_NAME preservado!)
# ---------------------------------------------------------------------------
def patch_version_txt(src: Path) -> None:
    path = src / "version.txt"
    if not path.is_file():
        raise PatchError(f"version.txt ausente em {src}")
    text = read(path)

    name = re.search(r"^APP_NAME (\S+)$", text, re.MULTILINE)
    package = re.search(r"^APP_PACKAGE (\S+)$", text, re.MULTILINE)
    if not name or not package:
        raise PatchError("version.txt sem APP_NAME/APP_PACKAGE")
    if name.group(1) != EXPECTED_APP_NAME:
        raise PatchError(
            f"APP_NAME inesperado: {name.group(1)!r} (esperado {EXPECTED_APP_NAME!r}). "
            "Este patch foi escrito para 21.3-Omega."
        )
    if package.group(1) != EXPECTED_APP_PACKAGE:
        raise PatchError(f"APP_PACKAGE inesperado: {package.group(1)!r}")

    updates = {
        "VERSION_MAJOR": BRAND_VERSION_MAJOR,
        "VERSION_MINOR": BRAND_VERSION_MINOR,
        "VERSION_CODE": BRAND_VERSION_CODE,
        "VERSION_TAG": BRAND_VERSION_TAG,
        "COMPANY_NAME": BRAND_COMPANY,
        "DEV_NAME": BRAND_COMPANY,
    }
    lines = text.splitlines()
    seen = set()
    out = []
    for line in lines:
        key = line.split(" ", 1)[0] if line.strip() else ""
        if key in updates:
            out.append(f"{key} {updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    if seen != set(updates):
        raise PatchError(f"version.txt sem as chaves: {sorted(set(updates) - seen)}")

    text = "\n".join(out) + "\n"
    text = re.sub(
        r"^PACKAGE_DESCRIPTION .*$",
        "PACKAGE_DESCRIPTION SMARTEDTV is an open source (GPL) media center for playing "
        "videos, music, pictures, games and more.",
        text, count=1, flags=re.MULTILINE,
    )
    write(path, text)
    print(f"  ok  version.txt: versão {BRAND_DISPLAY_VERSION} (Android 2104000), "
          f"empresa SMARTEDTV")
    print(f"  ok  version.txt: APP_NAME={EXPECTED_APP_NAME} e APP_PACKAGE={EXPECTED_APP_PACKAGE} "
          f"preservados (libkodi.so e perfil .kodi intactos)")

    api = re.search(r"^ADDON_API (\S+)$", text, re.MULTILINE)
    if not api or api.group(1) != "21.3.0":
        raise PatchError("ADDON_API mudou — a compatibilidade com add-ons seria afetada")


# ---------------------------------------------------------------------------
# 2. Nome visível do app Android (launcher, TV, "Recentes")
# ---------------------------------------------------------------------------
def patch_android_app_name(src: Path) -> None:
    path = src / "tools/android/packaging/xbmc/strings.xml.in"
    text = read(path)
    if "@APP_NAME@" not in text:
        raise PatchError("strings.xml.in sem @APP_NAME@")
    # Só os textos de exibição; o identificador @APP_NAME@ do manifest continua igual.
    text = text.replace(
        '<string name="app_name">@APP_NAME@</string>',
        f'<string name="app_name">{BRAND_NAME}</string>',
    ).replace(
        '<string name="search_hint">@APP_NAME@</string>',
        f'<string name="search_hint">{BRAND_NAME}</string>',
    )
    if "@APP_NAME@" in text:
        raise PatchError("strings.xml.in: sobrou @APP_NAME@ além dos textos esperados")
    write(path, text)
    print(f"  ok  strings.xml.in: app_name e search_hint = {BRAND_NAME} "
          f"(Application ID continua org.xbmc.kodi)")


# ---------------------------------------------------------------------------
# 3. Splash nativa: "Starting …", diálogos e tag de log
# ---------------------------------------------------------------------------
def patch_android_java(src: Path) -> None:
    splash = src / "tools/android/packaging/xbmc/src/Splash.java.in"
    replace_once(
        splash,
        "mSplash.mTextView.setText(\"Starting @APP_NAME@...\");",
        f'mSplash.mTextView.setText("Starting {BRAND_NAME}...");',
        "Splash.java.in: texto de inicialização",
    )
    replace_once(
        splash,
        'dialog.setMessage("@APP_NAME@ requires access to your device media and files to function. '
        'Please allow this via the following dialogue box or @APP_NAME@ will exit.");',
        f'dialog.setMessage("{BRAND_NAME} requires access to your device media and files to function. '
        f'Please allow this via the following dialogue box or {BRAND_NAME} will exit.");',
        "Splash.java.in: diálogo de permissões",
    )
    replace_once(
        splash,
        'private static final String TAG = "@APP_NAME@";',
        f'private static final String TAG = "{BRAND_NAME}";',
        "Splash.java.in: tag de log",
    )
    main = src / "tools/android/packaging/xbmc/src/Main.java.in"
    replace_once(
        main,
        'private static final String TAG = "@APP_NAME@";',
        f'private static final String TAG = "{BRAND_NAME}";',
        "Main.java.in: tag de log",
    )


# ---------------------------------------------------------------------------
# 4. Nome de exibição na GUI (tela de informações do sistema)
# ---------------------------------------------------------------------------
def patch_system_info_window(src: Path) -> None:
    """Acrescenta GetDisplayName() e usa na janela de informações.

    Não altera GetAppName() (usado em User-Agent, logs e caminhos).
    """
    header = src / "xbmc/CompileInfo.h"
    replace_once(
        header,
        "  static const char* GetAppName();",
        "  static const char* GetAppName();\n"
        "  static const char* GetDisplayName(); // nome de exibição (identidade SMARTEDTV)",
        "CompileInfo.h: declaração de GetDisplayName",
    )
    impl = src / "xbmc/CompileInfo.cpp.in"
    replace_once(
        impl,
        'const char* CCompileInfo::GetAppName()\n{\n  return "@APP_NAME@";\n}',
        'const char* CCompileInfo::GetAppName()\n{\n  return "@APP_NAME@";\n}\n\n'
        'const char* CCompileInfo::GetDisplayName()\n{\n  return "%s";\n}' % BRAND_NAME,
        "CompileInfo.cpp.in: GetDisplayName()",
    )

    # SystemInfo: expõe o nome de exibição (usado pela GUI)
    sysinfo_h = src / "xbmc/utils/SystemInfo.h"
    text = read(sysinfo_h)
    marker = "  static const std::string& GetAppName(void);"
    if marker not in text:
        raise PatchError("SystemInfo.h: âncora GetAppName não encontrada")
    original_line = (
        "  static const std::string& GetAppName(void); "
        "// the same name as CCompileInfo::GetAppName(), but const ref to std::string"
    )
    if original_line not in text:
        raise PatchError("SystemInfo.h: linha de GetAppName com comentário não encontrada")
    text = text.replace(
        original_line,
        original_line + "\n"
        "  /*! \\brief Nome de exibição do aplicativo (identidade visual SMARTEDTV).\n"
        "      Usado apenas em textos de interface; não afeta caminhos nem User-Agent. */\n"
        "  static const std::string& GetDisplayName();",
        1,
    )
    write(sysinfo_h, text)
    print("  ok  SystemInfo.h: declaração de GetDisplayName")

    sysinfo_cpp = src / "xbmc/utils/SystemInfo.cpp"
    replace_once(
        sysinfo_cpp,
        "const std::string& CSysInfo::GetAppName(void)\n{\n"
        "  assert(CCompileInfo::GetAppName() != NULL);\n"
        "  static const std::string appName(CCompileInfo::GetAppName());\n\n"
        "  return appName;\n}",
        "const std::string& CSysInfo::GetAppName(void)\n{\n"
        "  assert(CCompileInfo::GetAppName() != NULL);\n"
        "  static const std::string appName(CCompileInfo::GetAppName());\n\n"
        "  return appName;\n}\n\n"
        "const std::string& CSysInfo::GetDisplayName(void)\n{\n"
        "  static const std::string displayName(CCompileInfo::GetDisplayName());\n\n"
        "  return displayName;\n}",
        "SystemInfo.cpp: implementação de GetDisplayName",
    )

    # Janela de informações do sistema: <nome> <versão>
    replace_once(
        src / "xbmc/windows/GUIWindowSystemInfo.cpp",
        'SET_CONTROL_LABEL(52, CSysInfo::GetAppName() + " " + CSysInfo::GetVersion());',
        'SET_CONTROL_LABEL(52, CSysInfo::GetDisplayName() + " " + CSysInfo::GetVersion());',
        "GUIWindowSystemInfo.cpp: exibe o nome de marca",
    )


# ---------------------------------------------------------------------------
# 5. Nome padrão do dispositivo
# ---------------------------------------------------------------------------
def patch_device_name(src: Path) -> None:
    replace_once(
        src / "system/settings/settings.xml",
        '<setting id="services.devicename" type="string" label="1271" help="36321">\n'
        "          <level>0</level>\n"
        "          <default>Kodi</default>",
        '<setting id="services.devicename" type="string" label="1271" help="36321">\n'
        "          <level>0</level>\n"
        f"          <default>{BRAND_NAME}</default>",
        "settings.xml: nome padrão do dispositivo",
    )


# ---------------------------------------------------------------------------
# 6. Strings do produto (msgid = texto de origem)
# ---------------------------------------------------------------------------
def patch_po(path: Path, replacements: dict[str, str], label: str) -> int:
    if not path.is_file():
        print(f"  --  {label}: {path.name} ausente (ignorado)")
        return 0
    text = read(path)
    total = 0
    for old, new in replacements.items():
        pattern = re.compile(r'^(msg(?:id|str)) "' + re.escape(old) + r'"$', re.MULTILINE)
        text, n = pattern.subn(lambda m, new=new: f'{m.group(1)} "{new}"', text)
        total += n
    if total:
        write(path, text)
    print(f"  ok  {label}: {total} ocorrência(s) de marca atualizadas")
    return total


def patch_product_strings(src: Path) -> None:
    patch_po(src / "addons/resource.language.en_gb/resources/strings.po",
             STRING_REPLACEMENTS_EN, "strings.po en_gb")
    for candidate in (
        src / "addons/resource.language.pt_br/resources/language/resource.language.pt_br/strings.po",
        src / "addons/resource.language.pt_br/resources/strings.po",
    ):
        if candidate.is_file():
            patch_po(candidate, STRING_REPLACEMENTS_PT, "strings.po pt_br")
            break


# ---------------------------------------------------------------------------
# 7. Skin padrão: descrição visível em Complementos > Skins
# ---------------------------------------------------------------------------
def patch_skin_description(src: Path) -> None:
    path = src / "addons/skin.estuary/addon.xml"
    text = read(path)
    before = text
    text = text.replace("(Kodi&apos;s default skin)", f"({BRAND_NAME} default skin)")
    text = text.replace("(skin padrão do Kodi)", f"(skin padrão do {BRAND_NAME})")
    if text == before:
        raise PatchError("skin.estuary/addon.xml: nenhuma descrição com 'Kodi' encontrada")
    if "(Kodi&apos;s default skin)" in text:
        raise PatchError("skin.estuary/addon.xml: sobrou descrição 'Kodi'")
    write(path, text)
    print("  ok  skin.estuary/addon.xml: descrição da skin sem 'Kodi'")


# ---------------------------------------------------------------------------
# 7b. Paleta do Estuary: preto, branco e cinza
# ---------------------------------------------------------------------------
# O Estuary centraliza as cores em addons/skin.estuary/colors/defaults.xml, usado
# via colordiffuse= em 350+ pontos dos layouts. Recolorir SÓ esse arquivo muda a
# skin inteira sem tocar em layout, textura ou navegação.
#
# Nomes e valores de alfa são preservados; apenas os tons. O azul do Estuary
# (FF0E597E) vira grafite, o verde-água (FF12A0C7) vira cinza claro de foco e o
# âmbar de seleção (FFFFB70F) vira branco.
ESTUARY_PALETTE = {
    "primary_background":   "FF1A1A1A",  # fundo principal: grafite escuro
    "secondary_background": "332A2A2A",  # sobreposição: cinza translúcido
    "dialog_tint":          "FF1A2123",  # mantido (já é quase preto)
    "background":           "FF000000",  # preto puro
    "bg_image":             "FF8C8C8C",  # cinza neutro
    "bg_overlay":           "30000000",  # véu preto sobre fanart
    "black":                "FF000000",
    "white":                "FFEDEDED",  # branco levemente suavizado
    "grey":                 "FF9E9E9E",
    "blue":                 "FFBFBFBF",  # não usado como azul: cinza claro
    "red":                  "FF8A8A8A",  # sem vermelho: cinza
    "button_focus":         "FFB3B3B3",  # foco: cinza claro (era verde-água)
    "button_alt_focus":     "80B3B3B3",
    "text_shadow":          "22000000",
    "border_alpha":         "60FFFFFF",
    "disabled":             "40FFFFFF",
    "selected":             "FFFFFFFF",  # seleção: branco (era âmbar)
    "invalid":              "FF6E6E6E",
}


def patch_estuary_palette(src: Path) -> None:
    """Converte o Estuary para a paleta preto/branco/cinza."""
    path = src / "addons/skin.estuary/colors/defaults.xml"
    if not path.is_file():
        raise PatchError(f"arquivo de cores do Estuary ausente: {path}")
    text = read(path)
    changed = 0
    for name, value in ESTUARY_PALETTE.items():
        pattern = re.compile(rf'(<color name="{re.escape(name)}">)([0-9A-Fa-f]{{8}})(</color>)')
        new_text, count = pattern.subn(rf'\g<1>{value}\g<3>', text)
        if count == 0:
            raise PatchError(f"cor '{name}' não encontrada em {path.name}")
        text = new_text
        changed += count
    # nenhuma cor fora da paleta pode sobrar com tom saturado
    for leftover in re.findall(r'<color name="([^"]+)">([0-9A-Fa-f]{8})</color>', text):
        nome, rgba = leftover
        r, g, b = int(rgba[2:4], 16), int(rgba[4:6], 16), int(rgba[6:8], 16)
        if max(r, g, b) - min(r, g, b) > 24:
            raise PatchError(f"cor saturada remanescente: {nome}={rgba}")
    write(path, text)
    print(f"  ok  skin.estuary/colors/defaults.xml: {changed} cores para preto/branco/cinza")


# ---------------------------------------------------------------------------
# 8. Recursos visuais oficiais
# ---------------------------------------------------------------------------
MEDIA_FILES = (
    "splash.jpg", "applaunch_screen.png", "banner.png",
    "vendor_icon.png", "vendor_logo.png",
    "icon256x256.png", "icon120x120.png", "icon80x80.png",
    "icon48x48.png", "icon32x32.png", "icon16x16.png",
)


def patch_media(src: Path, brand_dir: Path) -> None:
    media = src / "media"
    packaging = src / "tools/android/packaging/media"
    if not (brand_dir / "media").is_dir():
        raise PatchError(f"pasta de identidade ausente: {brand_dir / 'media'}")

    for name in MEDIA_FILES:
        source = brand_dir / "media" / name
        if not source.is_file():
            raise PatchError(f"recurso de identidade ausente: {source}")
        shutil.copy2(source, media / name)
    print(f"  ok  media/: {len(MEDIA_FILES)} recursos oficiais da marca aplicados")

    for drawable in sorted((brand_dir / "android-packaging-media").glob("drawable-*")):
        target = packaging / drawable.name
        target.mkdir(parents=True, exist_ok=True)
        for png in sorted(drawable.glob("*.png")):
            shutil.copy2(png, target / png.name)
    print("  ok  tools/android/packaging/media: ícones do launcher e banner Android TV")


# ---------------------------------------------------------------------------
# 9. Idioma pt_BR embarcado (opcional)
# ---------------------------------------------------------------------------
def install_language(src: Path, addon_dir: Path) -> None:
    target = src / "addons/resource.language.pt_br"
    if target.is_dir():
        print("  --  resource.language.pt_br já presente no fonte")
    else:
        if not addon_dir.is_dir():
            raise PatchError(f"addon pt_BR não encontrado em {addon_dir}")
        shutil.copytree(addon_dir, target)
        print("  ok  addons/resource.language.pt_br copiado do repositório oficial")

    manifest = src / "cmake/installdata/common/addons.txt"
    text = read(manifest)
    entry = "addons/resource.language.pt_br/*"
    if entry not in text:
        lines = text.splitlines()
        position = next(
            (i for i, line in enumerate(lines)
             if line.startswith("addons/resource.language.") and line > entry),
            len(lines),
        )
        lines.insert(position, entry)
        write(manifest, "\n".join(lines) + "\n")
        print("  ok  cmake/installdata/common/addons.txt: pt_BR entra no APK")


def install_bingie(src: Path, addons_dir: Path) -> None:
    """Embarca a skin Bingie Mod + dependências e a define como skin padrão.

    O Kodi carrega ``lookandfeel.skin`` na inicialização; se a skin falhar, ele
    cai no ``<default>`` do settings.xml (Application.cpp:756). Por isso:
      * a Bingie vira o valor PADRÃO, para já abrir aplicada na primeira execução;
      * o Estuary continua no APK, como rede de segurança se a Bingie quebrar.
    """
    target_skin = src / "addons/skin.titan.bingie.mod"
    if not (addons_dir / "skin.titan.bingie.mod/addon.xml").is_file():
        raise PatchError(f"skin Bingie ausente em {addons_dir}")

    copiados = []
    for origem in sorted(addons_dir.iterdir()):
        if not origem.is_dir():
            raise PatchError(f"entrada inesperada no diretório de addons: {origem}")
        destino = src / "addons" / origem.name
        if destino.exists():
            raise PatchError(f"addon já presente no fonte: {origem.name}")
        shutil.copytree(origem, destino)
        copiados.append(origem.name)

    # manifesto de instalação: cada add-on precisa entrar no APK
    manifest = src / "cmake/installdata/common/addons.txt"
    text = read(manifest)
    entradas = [f"addons/{nome}/*" for nome in copiados]
    linhas = text.splitlines()
    for entrada in entradas:
        if entrada in linhas:
            continue
        posicao = next(
            (i for i, linha in enumerate(linhas)
             if linha.startswith("addons/") and linha > entrada),
            len(linhas),
        )
        linhas.insert(posicao, entrada)
    write(manifest, "\n".join(linhas) + "\n")
    print(f"  ok  {len(copiados)} add-ons da Bingie embarcados ({', '.join(copiados[:3])}...)")

    # skin padrão
    settings = src / "system/settings/settings.xml"
    text = read(settings)
    antigo = "<setting id=\"lookandfeel.skin\" type=\"addon\" label=\"166\" help=\"36103\">"
    if antigo not in text:
        raise PatchError("settings.xml: seção lookandfeel.skin não encontrada")
    trecho_ini = text.index(antigo)
    trecho_fim = text.index("</setting>", trecho_ini)
    bloco = text[trecho_ini:trecho_fim]
    if "<default>skin.estuary</default>" not in bloco:
        raise PatchError("settings.xml: default da skin não é skin.estuary")
    bloco_novo = bloco.replace("<default>skin.estuary</default>",
                               "<default>skin.titan.bingie.mod</default>")
    text = text[:trecho_ini] + bloco_novo + text[trecho_fim:]
    write(settings, text)
    print("  ok  settings.xml: skin padrão = skin.titan.bingie.mod (Estuary fica como fallback)")

    # registro: a skin precisa constar no addon-manifest para ser ativável
    addon_manifest = src / "system/addon-manifest.xml"
    text = read(addon_manifest)
    if "skin.titan.bingie.mod" not in text:
        linha = "  <addon>skin.titan.bingie.mod</addon>"
        marcador = "  <addon>skin.estuary</addon>"
        if marcador in text:
            text = text.replace(marcador, marcador + "\n" + linha, 1)
        else:
            text = text.replace("</addons>", linha + "\n</addons>", 1)
        write(addon_manifest, text)
        print("  ok  system/addon-manifest.xml: skin Bingie registrada")
    else:
        print("  --  system/addon-manifest.xml: skin Bingie já registrada")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="árvore do Kodi 21.3-Omega")
    parser.add_argument("--brand-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "out",
                        help="saída de make-brand-assets.py")
    parser.add_argument("--language-addon", type=Path, default=None,
                        help="pasta resource.language.pt_br do repo oficial (opcional)")
    parser.add_argument("--bingie-dir", type=Path, default=None,
                        help="addons da skin Bingie já extraídos (tools/kodi/fetch-bingie-addons.py)")
    args = parser.parse_args()

    src: Path = args.source.resolve()
    if not (src / "version.txt").is_file():
        print(f"não parece uma árvore do Kodi: {src}", file=sys.stderr)
        return 2

    print(f"Aplicando identidade {BRAND_NAME} em {src}\n")
    try:
        patch_version_txt(src)
        patch_android_app_name(src)
        patch_android_java(src)
        patch_system_info_window(src)
        patch_device_name(src)
        patch_product_strings(src)
        patch_skin_description(src)
        patch_estuary_palette(src)
        patch_media(src, args.brand_dir.resolve())
        if args.language_addon:
            install_language(src, args.language_addon.resolve())
        if args.bingie_dir:
            install_bingie(src, args.bingie_dir.resolve())
    except PatchError as error:
        print(f"\nERRO: {error}", file=sys.stderr)
        return 1
    print(f"\nIdentidade {BRAND_NAME} aplicada. libkodi.so, .kodi, ADDON_API e "
          f"org.xbmc.kodi permanecem intactos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
