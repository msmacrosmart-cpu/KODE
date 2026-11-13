#!/usr/bin/env python3
"""Reempacota um APK do Kodi trocando a pele das skins e a versão.

Estágio **ZIP** apenas: nada é decodificado nem recompilado. Tudo que não está
na lista de alterações é copiado byte a byte (libkodi.so, classes.dex, Python
embarcado, fontes, add-ons do sistema).

O que ele faz:

1. Injeta a Bingie Mod (``--bingie``) e suas dependências em
   ``assets/addons/<id>/`` e registra todas em ``assets/system/addon-manifest.xml``.
2. Aplica a paleta preto/branco/cinza nas duas skins, via
   ``tools/kodi/recolor-skin.py``:
      * na Bingie (a que entra agora);
      * no Estuary que já está dentro do APK.
3. Se houver ``guisettings.xml`` embarcado, aponta ``lookandfeel.skin`` para a
   Bingie, para ela já abrir aplicada.
4. Sobe ``versionName``/``versionCode`` no ``AndroidManifest.xml`` binário.

Uso:
    python3 tools/kodi/repack-skins.py BASE.apk NOVO.apk \\
        --bingie DIR --de-version 21.4.0 --para-version 21.4.1 \\
        --de-code 2104000 --para-code 2104001
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import shutil
import struct
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

AQUI = Path(__file__).resolve().parent
MANIFEST = "assets/system/addon-manifest.xml"
SIG = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$", re.I)

# Curvas de cor do Kodi: #AARRGGBB
COR = re.compile(r'(<color\s+name="([^"]+)"\s*>)([0-9A-Fa-f]{8})(\s*</color>)')


def carregar_recolor():
    caminho = AQUI / "recolor-skin.py"
    if not caminho.is_file():
        raise SystemExit(f"nao encontrei {caminho}")
    spec = importlib.util.spec_from_file_location("recolor_skin", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def coletar(pasta: Path, prefixo: str, estrito: bool) -> dict[str, bytes]:
    arquivos = sorted(
        p for p in pasta.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )
    if not arquivos:
        raise SystemExit(f"pasta vazia: {pasta}")
    dados: dict[str, bytes] = {}
    for p in arquivos:
        if p.is_symlink():
            raise SystemExit(f"symlink nao permitido: {p}")
        if estrito and p.suffix == ".xml":
            ET.parse(p)
        dados[prefixo + p.relative_to(pasta).as_posix()] = p.read_bytes()
    return dados


def neutralizar_xml(texto: str, recolor, limite: int) -> tuple[str, int]:
    """Aplica a paleta a um colors/defaults.xml já em memória."""
    trocas = 0

    def trocar(m: re.Match) -> str:
        nonlocal trocas
        abertura, nome, argb, fechamento = m.groups()
        r, g, b = int(argb[2:4], 16), int(argb[4:6], 16), int(argb[6:8], 16)
        nr, ng, nb = recolor.target_rgb(nome, r, g, b)
        novo = f"{argb[:2]}{nr:02X}{ng:02X}{nb:02X}"
        if novo.upper() != argb.upper():
            trocas += 1
        return abertura + novo + fechamento

    resultado = COR.sub(trocar, texto)

    for _, nome, argb, _ in COR.findall(resultado):
        r, g, b = int(argb[2:4], 16), int(argb[4:6], 16), int(argb[6:8], 16)
        if max(r, g, b) - min(r, g, b) > limite:
            raise SystemExit(f"cor saturada sobrou em {nome}={argb}")
    return resultado, trocas


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("base", type=Path, help="APK de origem (não é modificado)")
    p.add_argument("saida", type=Path, help="APK gerado, sem assinatura")
    p.add_argument("--bingie", type=Path, required=True,
                   help="pasta com skin.titan.bingie.mod e suas dependências")
    p.add_argument("--de-version", required=True)
    p.add_argument("--para-version", required=True)
    p.add_argument("--de-code", type=int, required=True)
    p.add_argument("--para-code", type=int, required=True)
    p.add_argument("--max-saturation", type=int, default=24)
    args = p.parse_args()

    if args.base.resolve() == args.saida.resolve():
        raise SystemExit("entrada e saida devem ser diferentes")
    if args.saida.exists():
        raise SystemExit(f"saida ja existe: {args.saida}")

    if len(args.para_version.encode("utf-16-le")) != len(args.de_version.encode("utf-16-le")):
        raise SystemExit(
            f"versionName {args.para_version!r} precisa ter "
            f"{len(args.de_version)} caracteres (igual a {args.de_version!r})"
        )

    recolor = carregar_recolor()
    novos: dict[str, bytes] = {}

    # ---------------------------------------------------------------- Bingie
    bingie = args.bingie / "skin.titan.bingie.mod"
    if not (bingie / "addon.xml").is_file():
        raise SystemExit(f"Bingie ausente em {bingie}")
    raiz = ET.parse(bingie / "addon.xml").getroot()
    if raiz.get("id") != "skin.titan.bingie.mod":
        raise SystemExit(f"id inesperado na Bingie: {raiz.get('id')}")

    for addon_dir in (bingie,):
        cores = addon_dir / "colors/defaults.xml"
        if cores.is_file():
            texto, n = neutralizar_xml(cores.read_text(encoding="utf-8"), recolor,
                                       args.max_saturation)
            cores.write_text(texto, encoding="utf-8")
            print(f"  Bingie: {n} cor(es) neutralizada(s)")

    novos.update(coletar(bingie, "assets/addons/skin.titan.bingie.mod/", estrito=False))

    deps: list[str] = []
    for filho in sorted(args.bingie.iterdir()):
        if filho.name == "skin.titan.bingie.mod" or not (filho / "addon.xml").is_file():
            continue
        addon_id = ET.parse(filho / "addon.xml").getroot().get("id")
        if addon_id != filho.name:
            raise SystemExit(f"{filho.name} declara id {addon_id}")
        novos.update(coletar(filho, f"assets/addons/{addon_id}/", estrito=False))
        deps.append(addon_id)
    print(f"  dependencias da Bingie: {len(deps)}")

    # ------------------------------------------------------- dentro do APK
    with zipfile.ZipFile(args.base) as src:
        nomes = {e.filename for e in src.infolist() if not e.is_dir()}

        # Estuary já embarcado: recolorir no lugar
        prefixo_est = "assets/addons/skin.estuary/"
        entradas_est = [n for n in nomes if n.startswith(prefixo_est)]
        if not entradas_est:
            raise SystemExit("skin.estuary nao encontrada no APK base")
        alvo = prefixo_est + "colors/defaults.xml"
        if alvo not in nomes:
            raise SystemExit("colors/defaults.xml do Estuary ausente")
        texto, n = neutralizar_xml(src.read(alvo).decode("utf-8"), recolor,
                                   args.max_saturation)
        novos[alvo] = texto.encode("utf-8")
        print(f"  Estuary: {n} cor(es) neutralizada(s)")

        # manifesto de add-ons
        # A skin padrao entra SEM optional: e ela que carrega a interface na
        # primeira execucao. As dependencias e o tema alternativo entram como
        # optional, para uma falha isolada deles nao impedir o Kodi de iniciar.
        manifesto = src.read(MANIFEST)
        novos_ids = ["skin.titan.bingie.mod"] + deps
        for addon_id in novos_ids:
            if f">{addon_id}<".encode() in manifesto:
                continue
            atributo = "" if addon_id == "skin.titan.bingie.mod" else ' optional="true"'
            manifesto = manifesto.replace(
                b"</addons>",
                f'  <addon{atributo}>{addon_id}</addon>\n</addons>'.encode(),
            )
        ET.fromstring(manifesto)
        novos[MANIFEST] = manifesto

        # skin padrão no userdata inicial, se houver
        for nome in sorted(nomes):
            if not nome.endswith("guisettings.xml") or not nome.startswith("assets/"):
                continue
            gs = src.read(nome).decode("utf-8")
            gs2 = re.sub(
                r'(<setting id="lookandfeel\.skin"[^>]*>)\s*skin\.estuary\s*(</setting>)',
                r"\1skin.titan.bingie.mod\2", gs)
            if gs2 != gs:
                novos[nome] = gs2.encode("utf-8")
                print(f"  skin padrao em {nome}")

        # ---------------------------------------------------- versão
        # O versionName normalmente NÃO está no AndroidManifest.xml: o Gradle o
        # referencia como @string/xbmc_version e o texto real vive no string
        # pool de resources.arsc. Por isso o manifesto só é alterado se a
        # string aparecer nele; senão a troca é feita no resources.arsc.
        binm = src.read("AndroidManifest.xml")
        va, vn = args.de_version.encode("utf-16le"), args.para_version.encode("utf-16le")
        ca, cn = struct.pack("<I", args.de_code), struct.pack("<I", args.para_code)

        trocas_versao: list[str] = []
        if binm.count(va) == 1:
            binm = binm.replace(va, vn)
            trocas_versao.append("versionName (manifesto)")
        if binm.count(ca) == 1:
            binm = binm.replace(ca, cn)
            trocas_versao.append("versionCode (manifesto)")
        elif binm.count(ca) > 1:
            raise SystemExit(f"versionCode {args.de_code} aparece {binm.count(ca)}x no manifesto")
        novos["AndroidManifest.xml"] = binm

        # versionName: procurar no resources.arsc e, se não estiver lá, nos
        # arquivos de strings compilados de res/ (o AAPT2 pode manter o valor
        # em res/values/strings.xml compilado em vez do pool global).
        if not any("versionName" in t for t in trocas_versao):
            alvos_arsc = [n for n in nomes if n == "resources.arsc"]
            for nome in alvos_arsc:
                bruto = src.read(nome)
                for codificacao, rotulo in (("utf-16-le", "utf-16"),
                                            ("utf-8", "utf-8")):
                    try:
                        alvo = args.de_version.encode(codificacao)
                        novo_ = args.para_version.encode(codificacao)
                    except UnicodeEncodeError:
                        continue
                    if len(alvo) != len(novo_):
                        continue
                    ocorrencias = bruto.count(alvo)
                    if ocorrencias == 1:
                        bruto = bruto.replace(alvo, novo_)
                        trocas_versao.append(f"versionName {rotulo} ({nome})")
                        break
                    if ocorrencias > 1:
                        raise SystemExit(
                            f"versionName {args.de_version} aparece {ocorrencias}x em {nome}")
                novos[nome] = bruto

        if not any("versionName" in t for t in trocas_versao):
            # último recurso: varrer todos os arquivos de recursos textuais
            candidatos = [n for n in nomes
                          if n.startswith("res/") and n.endswith(".xml")]
            for nome in candidatos:
                bruto = src.read(nome)
                alvo = args.de_version.encode("utf-16-le")
                if bruto.count(alvo) == 1:
                    novos[nome] = bruto.replace(alvo, args.para_version.encode("utf-16-le"))
                    trocas_versao.append(f"versionName utf-16 ({nome})")
                    break

        if not trocas_versao:
            raise SystemExit(
                "versao nao encontrada: nem no manifesto nem no resources.arsc "
                f"({args.de_version}/{args.de_code})")
        print("  versao trocada: " + ", ".join(trocas_versao))
        if not any("versionName" in t for t in trocas_versao):
            print("  ATENCAO: versionName nao alterado (só o code subiu); "
                  "o nome exibido continua " + args.de_version)

        # ------------------------------------------------------- escrever
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(args.saida, "w", allowZip64=True) as dst:
                vistos: set[str] = set()
                for item in src.infolist():
                    if item.is_dir() or SIG.fullmatch(item.filename):
                        continue
                    if item.filename in vistos:
                        raise SystemExit(f"entrada duplicada: {item.filename}")
                    vistos.add(item.filename)
                    if item.filename in novos:
                        dst.writestr(item, novos[item.filename])
                    else:
                        with src.open(item) as entrada, dst.open(item, "w") as saida:
                            shutil.copyfileobj(entrada, saida, 1024 * 1024)
                for nome, dados in novos.items():
                    if nome not in vistos:
                        dst.writestr(nome, dados, compress_type=zipfile.ZIP_DEFLATED)
        except BaseException:
            args.saida.unlink(missing_ok=True)
            raise

    digest = hashlib.sha256(args.saida.read_bytes()).hexdigest()
    print(f"\n{args.saida}: {args.saida.stat().st_size} bytes")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
