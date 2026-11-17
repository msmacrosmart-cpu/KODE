#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mostra o mapa de botoes da tela de entrada (id -> rotulo -> acao).

Le os controles de ``DialogWelcome.xml`` e o ``onClick`` real do ``default.py``,
e cruza os dois. Serve para conferir, depois de trocar o desenho, se todo botao
tem acao e se toda acao tem botao — sem precisar ler XML nem Python.

Uso:
    python3 tools/kodi/mapear-botoes.py
    python3 tools/kodi/mapear-botoes.py --json    # saida para ferramenta
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "kodi" / "addons" / "script.smartedtv.welcome"
LAYOUT = ADDON / "resources" / "skins" / "Default" / "1080i" / "DialogWelcome.xml"
DEFAULT_PY = ADDON / "default.py"

# Acoes que o app suporta hoje (o que o default.py sabe executar).
ACOES_CONHECIDAS = (
    "abrir_checkout", "abrir_dropbox", "compartilhar", "baixar_apk",
    "atualizar", "ativar_codigo", "continuar com anuncios", "fechar_dialogo",
)


def controles_do_layout():
    """id -> (tipo, rotulo) dos controles clicaveis do XML."""
    raiz = ET.parse(LAYOUT).getroot()
    lista = {}
    for controle in raiz.iter("control"):
        tipo = controle.get("type")
        ident = controle.get("id")
        if not ident or tipo not in ("button", "radio", "edit"):
            continue
        rotulo = (controle.findtext("label") or "").strip()
        lista[ident] = (tipo, rotulo)
    return lista


def acoes_do_python():
    """Le do onClick quais ids o default.py trata e o que cada um chama.

    Percorre so o corpo de cada ramo (o ``elif`` seguinte fica no ``orelse``),
    para o mapa refletir o primeiro tratamento de cada id.
    """
    arvore = ast.parse(DEFAULT_PY.read_text(encoding="utf-8"))
    mapa = {}

    def ids_do_teste(teste):
        """Ids comparados com control_id (inclusive em `in (a, b)`)."""
        achados = []
        for no in ast.walk(teste):
            if not isinstance(no, ast.Constant):
                continue
            valor = no.value
            if isinstance(valor, bool):
                continue          # `if ativo:`/`getattr(..., False)` nao e id
            if isinstance(valor, int) or (isinstance(valor, str) and valor.isdigit()):
                achados.append(str(valor))
        return achados

    def chamadas_do_corpo(corpo):
        nomes = []
        for no in corpo:
            for sub in ast.walk(no):
                if not isinstance(sub, ast.Call):
                    continue
                alvo = sub.func
                if isinstance(alvo, ast.Attribute) and isinstance(alvo.value, ast.Name) \
                        and alvo.value.id == "self" and alvo.attr.startswith("_"):
                    nomes.append(alvo.attr)
                elif isinstance(alvo, ast.Attribute) and isinstance(alvo.value, ast.Name) \
                        and alvo.value.id == "self" and alvo.attr == "setProperty":
                    # 312 nao chama metodo: sobe a property que abre o dialogo
                    nomes.append("abre_dialogo")
                elif isinstance(alvo, ast.Name) and alvo.id.startswith("_"):
                    nomes.append(alvo.id)
        return nomes

    def percorrer(ramos):
        for ramo in ramos:
            if not isinstance(ramo, ast.If):
                continue
            # a cadeia elif fica em orelse: desce nela
            nomes = chamadas_do_corpo(ramo.body)
            for ident in ids_do_teste(ramo.test):
                atual = mapa.setdefault(ident, [])
                for nome in nomes:
                    if nome not in atual:
                        atual.append(nome)
            percorrer(ramo.orelse)
            percorrer(ramo.body)

    for no in arvore.body:
        if isinstance(no, ast.ClassDef):
            for membro in no.body:
                if isinstance(membro, ast.FunctionDef) and membro.name == "onClick":
                    percorrer(membro.body)
    return mapa


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="saida JSON")
    args = parser.parse_args(argv)

    if not LAYOUT.is_file() or not DEFAULT_PY.is_file():
        raise SystemExit("addon da tela nao encontrado em %s" % ADDON)

    controles = controles_do_layout()
    acoes = acoes_do_python()
    linhas = []
    for ident in sorted(controles, key=lambda v: int(v)):
        tipo, rotulo = controles[ident]
        tratado = acoes.get(ident, [])
        linhas.append({
            "id": ident,
            "tipo": tipo,
            "rotulo": rotulo,
            "acoes": tratado,
            "ok": bool(tratado) or tipo == "edit",
        })

    if args.json:
        print(json.dumps(linhas, ensure_ascii=False, indent=2))
        return 0

    largura = max((len(l["rotulo"]) for l in linhas), default=10)
    print("%-6s %-8s %-*s %s" % ("id", "tipo", largura, "rotulo", "acao no default.py"))
    print("-" * (6 + 9 + largura + 30))
    for linha in linhas:
        acao = ", ".join(linha["acoes"]) or ("(campo de texto)" if linha["tipo"] == "edit"
                                            else "SEM ACAO")
        marca = "" if linha["ok"] else "  <-- falta mapear"
        print("%-6s %-8s %-*s %s%s" % (linha["id"], linha["tipo"], largura,
                                       linha["rotulo"], acao, marca))

    sem_acao = [l["id"] for l in linhas if not l["ok"]]
    sobra = sorted(set(acoes) - set(controles), key=int)
    print()
    if sem_acao:
        print("Botoes sem acao: %s" % ", ".join(sem_acao))
    else:
        print("Todos os botoes do layout tem acao mapeada.")
    if sobra:
        print("Acoes no default.py sem controle no layout: %s" % ", ".join(sobra))
    print("Acoes que o app entende: %s" % ", ".join(ACOES_CONHECIDAS))
    return 0 if not sem_acao else 1


if __name__ == "__main__":
    sys.exit(main())
