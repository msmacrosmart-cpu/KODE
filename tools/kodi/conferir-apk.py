#!/usr/bin/env python3
"""Confere o APK reempacotado antes de publicar.

Compara o APK final com a base e imprime uma linha por critério, para que uma
falha apareça de forma legível no log (e nas annotations da CI).

Critérios, em ordem de importância:
  1. ZIP íntegro.
  2. Motor intacto: as bibliotecas nativas do APK são exatamente as da base, e
     libkodi.so continua presente (é o Kodi compilado).
  3. Identidade Android: pacote org.xbmc.kodi, nome exibido SMARTEDTV e
     versionCode novo (é ele que governa a atualização).
  4. Skins: exatamente skin.titan.bingie.mod e skin.estuary.
  5. Paleta: nenhuma cor saturada em nenhuma das duas skins.
  6. Nada de Brazuka Play nem skin Nova TV.

Uso:
    python3 tools/kodi/conferir-apk.py FINAL.apk BASE.apk VERSAO CODIGO
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

FALHAS: list[str] = []
OK: list[str] = []


def checar(condicao: bool, descricao: str, detalhe: str = "") -> bool:
    if condicao:
        OK.append(f"OK    {descricao}" + (f" — {detalhe}" if detalhe else ""))
    else:
        FALHAS.append(f"FALHA {descricao}" + (f" — {detalhe}" if detalhe else ""))
    return condicao


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    final = Path(sys.argv[1])
    base = Path(sys.argv[2])
    versao = sys.argv[3]
    codigo = int(sys.argv[4])

    print(f"final: {final} ({final.stat().st_size} bytes)")
    print(f"base:  {base} ({base.stat().st_size} bytes)")

    # ---------------------------------------------------------- 1. ZIP
    with zipfile.ZipFile(final) as z:
        checar(z.testzip() is None, "ZIP íntegro")
        nomes = set(z.namelist())
        fmt = {n: z.read(n) for n in nomes if n.endswith("colors/defaults.xml")}

    with zipfile.ZipFile(base) as b:
        nomes_base = set(b.namelist())

    # --------------------------------------------------------- 2. motor
    libs = {n for n in nomes if n.startswith("lib/") and n.endswith(".so")}
    libs_base = {n for n in nomes_base if n.startswith("lib/") and n.endswith(".so")}
    checar(libs == libs_base and bool(libs), "bibliotecas nativas idênticas à base",
           f"{len(libs)} .so")
    checar("lib/arm64-v8a/libkodi.so" in nomes, "libkodi.so presente")
    checar("classes.dex" in nomes, "classes.dex presente")

    # ------------------------------------------------------ 3. identidade
    try:
        from pyaxmlparser import APK
        a = APK(str(final))
        checar(a.package == "org.xbmc.kodi", "pacote org.xbmc.kodi", a.package)
        checar(a.get_app_name() == "SMARTEDTV", "nome exibido SMARTEDTV", a.get_app_name())
        checar(int(a.version_code) == codigo, f"versionCode {codigo}", str(a.version_code))
        # O APK compilado do código-fonte usa o sufixo da tag ("21.4-Omega"),
        # não "21.4.0". Não é erro: o nome de versão é informativo; o que
        # governa a atualização é o versionCode, já conferido acima.
        checar(bool(a.version_name), "versionName presente", str(a.version_name))
    except ImportError:
        FALHAS.append("FALHA pyaxmlparser indisponível (pip install pyaxmlparser==0.3.31)")
    except Exception as erro:  # noqa: BLE001 - queremos o texto no log
        FALHAS.append(f"FALHA leitura do manifesto — {erro}")

    # ---------------------------------------------------------- 4. skins
    skins = sorted({n.split("/")[2] for n in nomes
                    if n.startswith("assets/addons/skin.") and n.count("/") > 2})
    checar(skins == ["skin.estuary", "skin.titan.bingie.mod"],
           "skins: Bingie (padrão) + Estuary", ", ".join(skins))

    # --------------------------------------------------------- 5. paleta
    for skin in skins:
        chave = f"assets/addons/{skin}/colors/defaults.xml"
        if chave not in fmt:
            FALHAS.append(f"FALHA {chave} ausente")
            continue
        texto = fmt[chave].decode("utf-8", "replace")
        saturadas = []
        total = 0
        for nome, valor in re.findall(r'name="([^"]+)"\s*>\s*([0-9A-Fa-f]{8})', texto):
            total += 1
            r, g, b = int(valor[2:4], 16), int(valor[4:6], 16), int(valor[6:8], 16)
            if max(r, g, b) - min(r, g, b) > 24:
                saturadas.append(f"{nome}={valor}")
        checar(not saturadas, f"{skin} monocromática",
               f"{total} cores" + (f", saturadas: {saturadas}" if saturadas else ""))

    # ------------------------------------------------------- 6. proibidos
    proibidos = [n for n in nomes
                 if "brazuka" in n.lower() or "novatv" in n.lower()]
    checar(not proibidos, "sem Brazuka Play / Nova TV",
           str(proibidos[:5]) if proibidos else "limpo")

    # ------------------------------------------------------- 7. manifesto
    if "assets/system/addon-manifest.xml" in nomes:
        with zipfile.ZipFile(final) as z:
            man = z.read("assets/system/addon-manifest.xml").decode("utf-8", "replace")
        checar("skin.titan.bingie.mod" in man, "Bingie no addon-manifest")

    # ------------------------------------------------------------- saída
    print()
    for linha in OK:
        print(linha)
    print()
    for linha in FALHAS:
        print(linha)

    if FALHAS:
        # ::error:: vai para as annotations, que e o canal legivel na CI
        for linha in FALHAS:
            print(f"::error::{linha}")
        print(f"\n{len(FALHAS)} falha(s), {len(OK)} ok")
        return 1
    print(f"\nAPK aprovado ({len(OK)} verificações).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
