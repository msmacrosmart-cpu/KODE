#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera a variante TV/Box/Projetor/Stick da tela de entrada.

A tela normal e desenhada para 1920x1080 de ponta a ponta. TVs e boxes
costumam aplicar overscan (cortam ~5% de cada borda), o que comia o logo no
topo e a linha do codigo no rodape. Esta variante mantem todo o desenho e os
textos, mas:

  * desce o logo/titulo/subtitulo 20 px e recua o bloco da esquerda 62 px;
  * sobe a barra do codigo para 880 e a linha de botoes para 892;
  * recua a barra e os textos do rodape para dentro dos 5% laterais;
  * troca a dica do codigo por uma instrucao de controle remoto.

Nada e escalado (as fontes continuam as mesmas, sem risco de estourar texto).
O default.py escolhe esta variante quando detecta TV/box/projetor/stick.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGEM = (ROOT / "kodi" / "addons" / "script.smartedtv.welcome" /
          "resources" / "skins" / "Default" / "1080i" / "DialogWelcome.xml")
DESTINO = ORIGEM.with_name("DialogWelcomeTV.xml")

TOPO = {"10", "11", "12"}
# id -> novo topo (a barra/linha inteira sobe para dentro da area segura)
RODAPE = {
    "6": "880",      # barra de fundo
    "60": "892",     # "Já é assinante?"
    "61": "929",     # dica (trocada abaixo)
    "62": "894",     # divisor
    "310": "892",    # campo do código
    "311": "892",    # Ativar
    "312": "892",    # Assistir com anúncios
}
# id -> nova esquerda (o overscan lateral de 5% cortava o logo e os textos)
ESQUERDA = {
    "10": "100",
    "11": "185",
    "12": "185",
    "6": "96",
    "60": "100",
    "61": "100",
}
DICA_TV = "Use as setas e OK do controle."


def main() -> int:
    arvore = ET.parse(ORIGEM)
    raiz = arvore.getroot()
    for controle in raiz.iter("control"):
        ident = controle.get("id")
        topo = controle.find("top")
        if topo is None or ident is None:
            continue
        if ident in TOPO:
            topo.text = str(int(topo.text or "0") + 20)
        elif ident in RODAPE:
            topo.text = RODAPE[ident]
        esquerda = controle.find("left")
        if esquerda is not None and ident in ESQUERDA:
            esquerda.text = ESQUERDA[ident]
        if ident == "6":
            largura = controle.find("width")
            if largura is not None:
                largura.text = "1728"
        if ident == "61":
            rotulo = controle.find("label")
            if rotulo is not None:
                rotulo.text = DICA_TV
    ET.indent(arvore, space="  ")
    arvore.write(DESTINO, encoding="UTF-8", xml_declaration=True)
    print("gerado: %s" % DESTINO)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
