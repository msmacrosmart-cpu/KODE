#!/usr/bin/env python3
"""Fotografa o APK de referência do usuário (o build que funcionava).

Não altera nada: só abre o ZIP, o manifesto e o dex e escreve um relatório com
tudo o que o injetor precisa saber — versão, perfil embutido, skin, menu,
idioma, splash e se já existe algum anúncio.

Uso:
    python3 inspecionar-base.py --apk referencia.apk --saida docs/base-dropbox.txt
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import zipfile
from collections import Counter
from pathlib import Path

# pastas que interessam (prefixo -> rótulo)
PASTAS = {
    "assets/addons/": "addons",
    "assets/smarted/": "perfil smarted",
    "assets/userdata/": "userdata",
    "assets/.kodi/": "perfil .kodi",
    "assets/python3": "python",
    "assets/system/": "system",
    "assets/media/": "media",
    "res/": "recursos compilados",
    "lib/": "libs nativas",
    "META-INF/": "assinatura",
}


def tamanho(n: int) -> str:
    return f"{n:,} bytes ({n / 1048576.0:.1f} MB)".replace(",", ".")


def badging(aapt2: str | None, apk: Path) -> str:
    if not aapt2:
        return "(aapt2 indisponível)"
    saida = []
    for args in (["dump", "badging"], ["dump", "xmltree", "--file", "AndroidManifest.xml"]):
        try:
            proc = subprocess.run([aapt2, *args, str(apk)], capture_output=True, text=True)
            saida.append(proc.stdout or proc.stderr)
        except Exception as erro:  # noqa: BLE001
            saida.append(f"(erro: {erro})")
    return "\n".join(saida)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", required=True, type=Path)
    ap.add_argument("--aapt2", default=None)
    ap.add_argument("--saida", required=True, type=Path)
    args = ap.parse_args()

    apk = args.apk
    linhas: list[str] = []
    add = linhas.append

    bruto = apk.read_bytes()
    add("# APK de referência (Dropbox) — inspeção\n")
    add(f"arquivo: `{apk.name}`")
    add(f"tamanho: {tamanho(len(bruto))}")
    add(f"sha256: `{hashlib.sha256(bruto).hexdigest()}`")
    add("")

    with zipfile.ZipFile(apk) as z:
        infos = [i for i in z.infolist() if not i.filename.endswith("/")]
        nomes = [i.filename for i in infos]

        add(f"## Conteúdo\n\n{len(infos)} arquivos\n\n")
        contagem = Counter()
        for nome in nomes:
            for prefixo, rotulo in PASTAS.items():
                if nome.startswith(prefixo):
                    contagem[rotulo] += 1
                    break
            else:
                contagem["(outros)"] += 1
        add("| grupo | arquivos |")
        add("|---|---|")
        for rotulo, quantos in contagem.most_common():
            add(f"| {rotulo} | {quantos} |")
        add("")

        # skin e catálogo
        skin = [n for n in nomes if n.startswith("assets/addons/skin.novatv/")]
        skin_media = [n for n in skin if "/media/" in n]
        add("## Skin e catálogo\n")
        add(f"* `assets/addons/skin.novatv/`: **{len(skin)}** arquivos ({len(skin_media)} em media/)")
        for alvo in (
            "assets/addons/skin.novatv/addon.xml",
            "assets/addons/skin.novatv/settings.xml",
            "assets/addons/plugin.video.smarted/addon.xml",
            "assets/addons/plugin.video.smarted/catalogue.py",
            "assets/addons/service.smarted.bootstrap/smart_ads.py",
        ):
            if alvo in nomes:
                dados = z.read(alvo).decode("utf-8", "replace")
                add(f"* `{alvo}` — {len(dados)} bytes:")
                for linha in dados.splitlines()[:12]:
                    add(f"      {linha.strip()[:160]}")
        add("")

        plugins = sorted({n.split("/")[2] for n in nomes
                          if n.startswith("assets/addons/") and n.count("/") > 2})
        add(f"## Addons ({len(plugins)})\n")
        add(", ".join(plugins))
        add("")

        # skin ativa / perfil
        add("## Skin ativa e perfil\n")
        guis = [n for n in nomes if n.endswith("guisettings.xml")]
        add(f"guisettings.xml encontrados: {guis or '(nenhum)'}")
        for nome in guis:
            texto = z.read(nome).decode("utf-8", "replace")
            for linha in texto.splitlines():
                if "lookandfeel.skin" in linha or "lookandfeel.font" in linha:
                    add(f"    {nome}: {linha.strip()[:120]}")
        for sonda, rotulo in (
            ("addon_data/skin.novatv", "ajustes da skin.novatv"),
            ("skinshortcuts", "menus/atalhos (skinshortcuts)"),
            ("favourites.xml", "favoritos"),
            ("sources.xml", "fontes"),
            ("playlists", "playlists"),
            ("profiles.xml", "perfis do Kodi"),
        ):
            achados = [n for n in nomes if sonda in n]
            add(f"* {rotulo}: {len(achados)} arquivo(s)")
            for nome in achados[:6]:
                add(f"    - {nome}")
        add("")

        # splash dentro de assets
        add("## Splash em assets\n")
        for nome in nomes:
            if "splash" in nome.lower() or "applaunch" in nome.lower():
                info = z.getinfo(nome)
                add(f"* {nome} — {tamanho(info.file_size)}")
        add("")

        # anuncios
        add("## Anúncios já presentes?\n")
        marcas = [b"ca-app-pub-", b"AppOpenActivity", b"PreRollActivity", b"com/google/android/gms/ads"]
        for info in infos:
            if not info.filename.endswith((".dex", ".xml", ".py", ".json")) and \
               info.filename not in ("AndroidManifest.xml",):
                continue
            if info.file_size > 60 * 1048576:
                continue
            dados = z.read(info.filename)
            achados = [m.decode() for m in marcas if m in dados]
            if achados:
                add(f"* `{info.filename}`: {', '.join(achados)}")
        add("")

        # amostra do perfil (se houver)
        perfil = [n for n in nomes if n.startswith(("assets/smarted/", "assets/userdata/", "assets/.kodi/"))]
        if perfil:
            add(f"## Amostra do perfil embutido ({len(perfil)} arquivos)\n")
            for nome in perfil[:25]:
                add(f"* {nome}")
            add("")

    add("## aapt2\n\n```")
    add(badging(args.aapt2, apk)[:6000])
    add("```")

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"relatório: {args.saida} ({args.saida.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
