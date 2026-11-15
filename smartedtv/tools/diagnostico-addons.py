#!/usr/bin/env python3
"""Diagnóstico estático dos add-ons do perfil (Brazuca Play e dependências).

Extrai de um APK tudo o que está em ``assets/smarted/profile/addons/**``, compila
cada ``.py`` com o Python do runner (sintaxe) e confere:

* ``addon.xml``: id, versão, ``xbmc.python`` exigido e dependências;
* dependências declaradas que NÃO estão no perfil nem nos add-ons do APK;
* arquivos que o add-on espera em ``addon_data`` (``settings.xml``, dbs...);
* uso de APIs que mudaram no Kodi 20/21 (``translatePath`` sem xbmcvfs,
  ``xbmc.translatePath``, ``sys.setdefaultencoding``, ``py2`` prints...);
* ``__pycache__`` de outra versão do Python dentro do add-on.

Uso:
    python3 diagnostico-addons.py --apk base.apk --saida docs/brazuca-diagnostico.txt
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

PREFIXO = "assets/smarted/profile/addons/"

# APIs que quebram ou reclamam no Kodi 20/21
API_SUSPEITA = (
    (rb"xbmc\.translatePath", "xbmc.translatePath (removido; usar xbmcvfs.translatePath)"),
    (rb"sys\.setdefaultencoding", "sys.setdefaultencoding (não existe no Python 3)"),
    (rb"xbmc\.LOGNOTICE\b", "xbmc.LOGNOTICE (removido no Kodi 20)"),
    (rb"urllib2\.", "urllib2 (Python 2)"),
    (rb"import\s+urllib2", "urllib2 (Python 2)"),
    (rb"print\s+['\"]", "print sem parênteses (Python 2)"),
    (rb"\.iteritems\(\)", ".iteritems() (Python 2)"),
    (rb"unicode\(", "unicode() (Python 2)"),
    (rb"basestring", "basestring (Python 2)"),
)


def ler_addon_xml(texto: bytes) -> dict:
    info = {"id": "", "version": "", "requires": [], "python": ""}
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError as erro:
        info["erro"] = str(erro)
        return info
    info["id"] = raiz.get("id", "")
    info["version"] = raiz.get("version", "")
    for req in raiz.iter("import"):
        addon = req.get("addon", "")
        versao = req.get("version", "")
        info["requires"].append((addon, versao))
        if addon == "xbmc.python":
            info["python"] = versao
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apk", required=True, type=Path)
    ap.add_argument("--saida", required=True, type=Path)
    args = ap.parse_args()

    linhas: list[str] = []
    add = linhas.append

    with zipfile.ZipFile(args.apk) as z:
        nomes = z.namelist()
        addons = sorted({n[len(PREFIXO):].split("/")[0] for n in nomes
                         if n.startswith(PREFIXO) and len(n) > len(PREFIXO)})
        do_apk = sorted({n.split("/")[2] for n in nomes
                         if n.startswith("assets/addons/") and n.count("/") > 2})

        add("# Add-ons do perfil — diagnóstico estático\n")
        add(f"APK: `{args.apk.name}`")
        add(f"addons do perfil: {len(addons)} | addons do APK: {len(do_apk)}\n")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            for nome in nomes:
                if nome.startswith(PREFIXO) and not nome.endswith("/"):
                    destino = tmp / nome[len(PREFIXO):]
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    destino.write_bytes(z.read(nome))

            metadados = {}
            for pasta in sorted(p for p in tmp.iterdir() if p.is_dir()):
                alvo = pasta / "addon.xml"
                if alvo.is_file():
                    metadados[pasta.name] = ler_addon_xml(alvo.read_bytes())

            disponiveis = set(metadados) | set(do_apk)

            add("## Sintaxe (py_compile) e APIs suspeitas\n")
            total_py = 0
            for pasta in sorted(p for p in tmp.rglob("*") if p.suffix == ".py"):
                total_py += 1
                proc = subprocess.run([sys.executable, "-m", "py_compile", str(pasta)],
                                      capture_output=True, text=True)
                if proc.returncode != 0:
                    add(f"* **ERRO DE SINTAXE** `{pasta.relative_to(tmp)}`")
                    for linha in (proc.stderr or "").strip().splitlines()[-4:]:
                        add(f"      {linha}")
                dados = pasta.read_bytes()
                for padrao, motivo in API_SUSPEITA:
                    if re.search(padrao, dados):
                        achado = re.search(padrao, dados).group(0).decode("utf-8", "replace")
                        add(f"* `{pasta.relative_to(tmp)}`: {motivo} — `{achado}`")
            add(f"\n{total_py} arquivos .py compilados\n")

            add("## Dependências\n")
            for nome, info in sorted(metadados.items()):
                faltando = [req for req, _ in info["requires"]
                            if req not in disponiveis and req not in
                            ("xbmc.python", "xbmc.gui", "xbmc.metadata", "kodi.ui")]
                marca = "OK" if not faltando else "FALTA " + ", ".join(faltando)
                add(f"* `{info['id'] or nome}` v{info['version']} "
                    f"(python {info['python'] or '?'}) — {marca}")
                if info.get("erro"):
                    add(f"    addon.xml inválido: {info['erro']}")

            add("\n## Brazuca Play em detalhe\n")
            brazuca = tmp / "plugin.video.BrazucaPlay.Matrix"
            if not brazuca.is_dir():
                add("* (não está no perfil deste APK)")
            else:
                arquivos = sorted(p.relative_to(brazuca) for p in brazuca.rglob("*") if p.is_file())
                add(f"* {len(arquivos)} arquivos")
                for rel in arquivos:
                    add(f"    - {rel}")
                dados = (brazuca / "addon.xml")
                if dados.is_file():
                    add("* addon.xml:")
                    for linha in dados.read_text(encoding="utf-8", errors="replace").splitlines():
                        add(f"      {linha.strip()[:150]}")

            add("\n## addon_data que o perfil traz\n")
            dados_prefixo = "assets/smarted/profile/userdata/addon_data/"
            for nome in sorted(n for n in nomes if n.startswith(dados_prefixo)):
                add(f"* {nome[len(dados_prefixo):]}")

            add("\n## __pycache__ embarcado (versão do Python)\n")
            caches = sorted({n.split("/")[-1].split(".")[-2] for n in nomes
                             if "__pycache__" in n and n.endswith(".pyc")})
            add("* tags: " + (", ".join(caches) or "(nenhuma)"))

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"relatório: {args.saida} ({args.saida.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
