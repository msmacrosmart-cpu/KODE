#!/usr/bin/env python3
"""Desenha a tela do ZIP (DialogWelcome.xml) exatamente como o Kodi mostraria.

Não é um mockup novo: cada controle do XML entregue é renderizado nas mesmas
coordenadas, com as mesmas texturas do ZIP (``resources/skins/Default/media``) e
os mesmos tamanhos de fonte resolvidos pelo Font.xml da skin. Serve como prova
visual do que o APK abre, sem precisar de um dispositivo.

Uso: python3 tools/kodi/renderizar-tela-entrada.py --saida prova.png
"""
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "kodi" / "addons" / "script.smartedtv.welcome"
MEDIA = ADDON / "resources" / "skins" / "Default" / "media"
LAYOUT = ADDON / "resources" / "skins" / "Default" / "1080i" / "DialogWelcome.xml"
TEXTO_EXTRA = ROOT / "kodi" / "skin.novatv" / "fonts" / "Regular.ttf"
FONTE_SISTEMA = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def texto_de(no, tag, padrao=""):
    filho = no.find(tag)
    return (filho.text or padrao) if filho is not None and filho.text else padrao


def numero(no, tag, padrao=0):
    valor = texto_de(no, tag, "")
    try:
        return float(valor)
    except ValueError:
        return padrao


def fonte_tamanho(caminho_font_xml, nome):
    if caminho_font_xml and caminho_font_xml.is_file():
        texto = caminho_font_xml.read_text(encoding="utf-8", errors="replace")
        for bloco in re.findall(r"<font>(.*?)</font>", texto, re.S):
            if "<name>%s</name>" % nome in bloco:
                m = re.search(r"<size>(\d+)</size>", bloco)
                if m:
                    return int(m.group(1))
    return None


def cor(valor, padrao=(255, 255, 255, 255)):
    valor = (valor or "").strip()
    if len(valor) == 8:
        try:
            return (int(valor[2:4], 16), int(valor[4:6], 16), int(valor[6:8], 16),
                    int(valor[0:2], 16))
        except ValueError:
            return padrao
    if len(valor) == 6:
        try:
            return (int(valor[0:2], 16), int(valor[2:4], 16), int(valor[4:6], 16), 255)
        except ValueError:
            return padrao
    return padrao


def carregar_fonte(nome, tamanhos):
    caminho = TEXTO_EXTRA if TEXTO_EXTRA.is_file() else FONTE_SISTEMA
    return ImageFont.truetype(str(caminho), tamanhos.get(nome) or 30)


def desenhar_controle(imagem, no, pais, tamanhos):
    """Renderiza um controle do XML (recursivo para os grupos)."""
    if no.tag != "control":
        return
    tipo = no.get("type") or ""
    x = numero(no, "left") + pais[0]
    y = numero(no, "top") + pais[1]
    largura = numero(no, "width")
    altura = numero(no, "height")
    if tipo == "image":
        textura = texto_de(no, "texture")
        arquivo = MEDIA / textura
        if textura and arquivo.is_file():
            img = Image.open(arquivo).convert("RGBA")
            if largura and altura and (img.width, img.height) != (largura, altura):
                if texto_de(no, "aspectratio") == "keep":
                    img.thumbnail((int(largura), int(altura)), Image.LANCZOS)
                else:
                    img = img.resize((int(largura), int(altura)), Image.LANCZOS)
            imagem.alpha_composite(img, (int(x), int(y)))
        return
    if tipo == "label":
        rotulo = texto_de(no, "label")
        if not rotulo:
            return
        fonte = carregar_fonte(texto_de(no, "font"), tamanhos)
        cor_texto = cor(texto_de(no, "textcolor"))
        alinhamento = (texto_de(no, "align") or "left").strip()
        alinhar_y = (texto_de(no, "aligny") or "top").strip()
        desenho = ImageDraw.Draw(imagem)
        linhas = rotulo.split("\n")
        # quebra simples por palavra respeitando a largura declarada
        finais = []
        for linha in linhas:
            atual = ""
            for palavra in linha.split(" "):
                teste = (atual + " " + palavra).strip()
                if desenho.textlength(teste, font=fonte) <= largura or not atual:
                    atual = teste
                else:
                    finais.append(atual)
                    atual = palavra
            finais.append(atual)
        alturas = [desenho.textbbox((0, 0), l, font=fonte)[3] for l in finais]
        total = sum(alturas) + 4 * (len(finais) - 1)
        if alinhar_y == "center":
            topo = y + (altura - total) / 2 if altura else y
        else:
            topo = y
        for linha, h in zip(finais, alturas):
            w = desenho.textlength(linha, font=fonte)
            if alinhamento == "center":
                px = x + (largura - w) / 2
            elif alinhamento == "right":
                px = x + largura - w
            else:
                px = x
            desenho.text((px, topo), linha, font=fonte, fill=cor_texto)
            topo += h + 4
        return
    if tipo in ("button", "edit"):
        if tipo == "edit":
            arquivo = MEDIA / (texto_de(no, "texturenofocus") or "edit_nofocus.png")
            if arquivo.is_file():
                img = Image.open(arquivo).convert("RGBA").resize((int(largura), int(altura)))
                imagem.alpha_composite(img, (int(x), int(y)))
        elif texto_de(no, "texturenofocus"):
            arquivo = MEDIA / texto_de(no, "texturenofocus")
            if arquivo.is_file():
                img = Image.open(arquivo).convert("RGBA").resize((int(largura), int(altura)))
                imagem.alpha_composite(img, (int(x), int(y)))
        rotulo = texto_de(no, "label")
        fonte = carregar_fonte(texto_de(no, "font"), tamanhos)
        cor_texto = cor(texto_de(no, "textcolor"), (255, 255, 255, 255))
        desenho = ImageDraw.Draw(imagem)
        w = desenho.textlength(rotulo, font=fonte)
        desenho.text((x + (largura - w) / 2, y + (altura - fonte.size) / 2 - 2),
                     rotulo, font=fonte, fill=cor_texto)
        return
    if tipo == "group":
        visivel = no.find("visible")
        if visivel is not None:
            # o modal só aparece com a propriedade show_free_dialog=true
            return
        for filho in no.findall("control"):
            desenhar_controle(imagem, filho, (x, y), tamanhos)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=ROOT / "artifacts" / "tela-entrada-prova.png")
    parser.add_argument("--font-xml", type=Path, default=ROOT / "kodi" / "skin.novatv" / "xml" / "Font.xml")
    args = parser.parse_args(argv)

    import xml.etree.ElementTree as ET

    raiz = ET.parse(LAYOUT).getroot()
    tamanhos = {}
    if args.font_xml.is_file():
        texto = args.font_xml.read_text(encoding="utf-8", errors="replace")
        for bloco in re.findall(r"<font>(.*?)</font>", texto, re.S)[:64]:
            nome = re.search(r"<name>([^<]+)</name>", bloco)
            tamanho = re.search(r"<size>(\d+)</size>", bloco)
            if nome and tamanho and nome.group(1) not in tamanhos:
                tamanhos[nome.group(1)] = int(tamanho.group(1))

    # as 4 fontes novas que o injetor declara no Font.xml da skin
    tamanhos.setdefault("font20", 20)
    tamanhos.setdefault("font22", 22)
    tamanhos.setdefault("font24", 24)
    tamanhos.setdefault("font30", 30)

    imagem = Image.new("RGBA", (1920, 1080), (0, 0, 0, 255))
    for controle in raiz.find("controls").findall("control"):
        desenhar_controle(imagem, controle, (0, 0), tamanhos)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    imagem.convert("RGB").save(args.saida, quality=95)
    print("prova visual: %s (%dx%d)" % (args.saida, imagem.width, imagem.height))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
