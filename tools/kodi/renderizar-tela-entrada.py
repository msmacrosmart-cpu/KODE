#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Desenha a tela de entrada a partir do DialogWelcome.xml entregue.

Cada controle do XML e desenhado nas suas coordenadas, com as texturas do
addon e as fontes do tamanho declarado no Font.xml das skins — serve como prova
visual do que o APK abre, sem precisar de um aparelho. Nao e um mockup novo: o
que aparece vem do proprio XML e das texturas que vao no APK.

Uso:
    python3 tools/kodi/renderizar-tela-entrada.py --saida prova.png
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "kodi" / "addons" / "script.smartedtv.welcome"
MEDIA = ADDON / "resources" / "skins" / "Default" / "media"
LAYOUT = ADDON / "resources" / "skins" / "Default" / "1080i" / "DialogWelcome.xml"
FONTS_DIR = ROOT / "kodi" / "skin.estilo.personalizado" / "fonts"
# Copia da mesma fonte sem as tabelas de hinting: o FreeType deste ambiente
# rasteriza os glifos com defeito quando o hinting da Noto Sans esta presente
# (na TV o Kodi usa a fonte original do addon, sem alteracao alguma). Serve so
# para esta prova visual.
FONTE_PROVA = ROOT / "build_test" / "NotoSans-render.ttf"


def texto_de(no, tag, padrao=""):
    filho = no.find(tag)
    return (filho.text or padrao) if filho is not None and filho.text else padrao


def numero(no, tag, padrao=0):
    try:
        return float(texto_de(no, tag, ""))
    except ValueError:
        return padrao


def cor(valor, padrao=(255, 255, 255, 255)):
    valor = (valor or "").strip()
    if len(valor) == 8:
        try:
            return (int(valor[2:4], 16), int(valor[4:6], 16), int(valor[6:8], 16),
                    int(valor[0:2], 16))
        except ValueError:
            return padrao
    return padrao


def tamanhos_de_fonte(caminho_font_xml):
    tamanhos = {}
    if not caminho_font_xml.is_file():
        return tamanhos
    texto = caminho_font_xml.read_text(encoding="utf-8", errors="replace")
    for bloco in re.findall(r"<font>(.*?)</font>", texto, re.S):
        nome = re.search(r"<name>([^<]+)</name>", bloco)
        tamanho = re.search(r"<size>(\d+)</size>", bloco)
        if nome and tamanho and nome.group(1) not in tamanhos:
            tamanhos[nome.group(1)] = int(tamanho.group(1))
    return tamanhos


def fonte(nome, tamanhos):
    tamanho = tamanhos.get(nome) or 30
    caminho = FONTE_PROVA if FONTE_PROVA.is_file() else FONTS_DIR / "NotoSans-Regular.ttf"
    return ImageFont.truetype(str(caminho), tamanho)


def rotulo_variado(no):
    """`[CR]` e a quebra de linha do skinning do Kodi."""
    return texto_de(no, "label").replace("[CR]", "\n")


def desenhar_controle(imagem, no, pais, tamanhos, props):
    if no.tag != "control":
        return
    tipo = no.get("type") or ""
    x = numero(no, "left") + pais[0]
    y = numero(no, "top") + pais[1]
    largura = numero(no, "width")
    altura = numero(no, "height")

    if tipo == "group":
        visivel = texto_de(no, "visible")
        esperado = None
        if "welcome_dialog),ads" in visivel.replace(" ", ""):
            esperado = "ads"
        elif "welcome_dialog),status" in visivel.replace(" ", ""):
            esperado = "status"
        if esperado and props.get("welcome_dialog") != esperado:
            return
        for filho in no.findall("control"):
            desenhar_controle(imagem, filho, (x, y), tamanhos, props)
        return

    if tipo == "image":
        textura = texto_de(no, "texture")
        arquivo = MEDIA / textura
        if not textura or not arquivo.is_file():
            raise SystemExit("textura ausente no addon: %s" % textura)
        img = Image.open(arquivo).convert("RGBA")
        alvo = (int(largura), int(altura))
        if img.size != alvo:
            if texto_de(no, "aspectratio") in ("keep", "stretch"):
                img = img.resize(alvo, Image.LANCZOS)
            else:
                img = img.resize(alvo, Image.LANCZOS)
        imagem.alpha_composite(img, (int(x), int(y)))
        return

    if tipo == "label":
        rotulo = rotulo_variado(no)
        if not rotulo:
            return
        if rotulo.startswith("$INFO[Window.Property("):
            chave = rotulo[len("$INFO[Window.Property("):].rstrip(")]")
            rotulo = props.get(chave, "")
            if not rotulo:
                return
        f = fonte(texto_de(no, "font"), tamanhos)
        cor_texto = cor(texto_de(no, "textcolor"))
        alinhamento = (texto_de(no, "align") or "left").strip()
        alinhar_y = (texto_de(no, "aligny") or "top").strip()
        desenho = ImageDraw.Draw(imagem)
        finais = []
        for linha in rotulo.split("\n"):
            atual = ""
            for palavra in linha.split(" "):
                teste = (atual + " " + palavra).strip()
                if desenho.textlength(teste, font=f) <= largura or not atual:
                    atual = teste
                else:
                    finais.append(atual)
                    atual = palavra
            finais.append(atual)
        # Altura de linha = ascendente + descendente da fonte (o que o Kodi
        # reserva), nao o bitmap de cada string: assim o acento de "Ativação"
        # nao e cortado, e a linha nao "sobe" quando o texto tem acento.
        ascent, descent = f.getmetrics()
        passo = ascent + descent
        total = passo * len(finais) + 4 * (len(finais) - 1)
        topo = y + (altura - total) / 2 if alinhar_y == "center" else y
        for i, linha in enumerate(finais):
            w = desenho.textlength(linha, font=f)
            if alinhamento == "center":
                px = x + (largura - w) / 2
            elif alinhamento == "right":
                px = x + largura - w
            else:
                px = x
            # ancora "la": a linha de base fica na ascendente, sobra espaco
            # para o acento e para o descendente (igual ao Kodi)
            desenho.text((px, topo + i * (passo + 4)), linha, font=f,
                         fill=cor_texto, anchor="la")
        return

    if tipo == "textbox":
        rotulo = texto_de(no, "label")
        if rotulo.startswith("$INFO[Window.Property("):
            chave = rotulo[len("$INFO[Window.Property("):].rstrip(")]")
            rotulo = props.get(chave, "")
        if not rotulo:
            return
        f = fonte(texto_de(no, "font"), tamanhos)
        cor_texto = cor(texto_de(no, "textcolor"))
        desenho = ImageDraw.Draw(imagem)
        finais, atual = [], ""
        for palavra in rotulo.replace("[CR]", " ").split(" "):
            teste = (atual + " " + palavra).strip()
            if desenho.textlength(teste, font=f) <= largura or not atual:
                atual = teste
            else:
                finais.append(atual)
                atual = palavra
        finais.append(atual)
        passo = round(f.size * 1.35)
        topo = y
        for linha in finais:
            if topo + passo > y + altura:
                desenho.text((x, topo), "...", font=f, fill=cor_texto)
                break
            desenho.text((x, topo), linha, font=f, fill=cor_texto)
            topo += passo
        return

    if tipo in ("button", "edit"):
        textura = texto_de(no, "texturenofocus")
        # nos desenhos em repouso mostramos o estado sem foco
        arquivo = MEDIA / textura if textura else None
        if arquivo is not None and arquivo.is_file():
            img = Image.open(arquivo).convert("RGBA").resize(
                (int(largura), int(altura)), Image.LANCZOS)
            imagem.alpha_composite(img, (int(x), int(y)))
        rotulo = texto_de(no, "label")
        if rotulo.startswith("$INFO[Window.Property("):
            chave = rotulo[len("$INFO[Window.Property("):].rstrip(")]")
            rotulo = props.get(chave, "")
        if not rotulo:
            return
        f = fonte(texto_de(no, "font"), tamanhos)
        cor_texto = cor(texto_de(no, "textcolor"))
        desenho = ImageDraw.Draw(imagem)
        w = desenho.textlength(rotulo, font=f)
        caixa = desenho.textbbox((0, 0), rotulo, font=f)
        altura_texto = caixa[3] - caixa[1]
        if tipo == "edit":
            # o <edit> do Kodi alinha o texto a ESQUERDA, com padding interno;
            # centralizar aqui daria uma prova visual enganosa
            px = x + 14
        else:
            px = x + (largura - w) / 2
        desenho.text((px, y + (altura - altura_texto) / 2 - caixa[1]),
                     rotulo, font=f, fill=cor_texto)
        return


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path,
                        default=ROOT / "artifacts" / "tela-entrada-prova.png")
    parser.add_argument("--font-xml", type=Path,
                        default=ROOT / "kodi" / "skin.estilo.personalizado" / "xml" / "Font.xml")
    parser.add_argument("--dialogo", default="",
                        help="ades|status para desenhar um dos dialogos")
    parser.add_argument("--layout", type=Path, default=LAYOUT,
                        help="XML a desenhar (padrao: DialogWelcome.xml)")
    parser.add_argument("--resolucao", default="1920x1080",
                        help="1280x720, 1920x1080 ou 3840x2160")
    args = parser.parse_args(argv)

    layout = args.layout
    try:
        largura_saida, altura_saida = (int(v) for v in args.resolucao.lower().split("x"))
    except ValueError:
        raise SystemExit("--resolucao deve ser LARGURAxALTURA (ex.: 1280x720)")
    raiz = ET.parse(layout).getroot()
    tamanhos = tamanhos_de_fonte(args.font_xml)
    # os estilos wfNN declarados pelo injetor (nome = tamanho)
    for bloco in re.findall(r"<font>(.*?)</font>", args.font_xml.read_text(
            encoding="utf-8", errors="replace"), re.S):
        nome = re.search(r"<name>wf(\d+)</name>", bloco)
        if nome:
            tamanhos[nome.group(1) and "wf" + nome.group(1)] = int(nome.group(1))
    for nome in re.findall(r"<font>(wf\d+)</font>", layout.read_text(encoding="utf-8")):
        tamanhos.setdefault(nome, int(nome[2:]))

    props = {}
    if args.dialogo:
        props["welcome_dialog"] = args.dialogo
        props["welcome_status_title"] = "Código não ativado"
        # texto de propósito LONGO: e o pior caso do servidor real (mensagem de
        # erro com detalhe). A prova precisa mostrar que ele quebra e nao vaza.
        props["welcome_status_text"] = (
            "O serviço de validação não aceitou este código para o plano "
            "selecionado. Confira se digitou todas as letras e números, "
            "verifique se o código ainda não foi usado em outro aparelho e "
            "tente novamente em alguns instantes.")
        props["welcome_status_ok"] = "Tentar novamente"

    imagem = Image.new("RGBA", (1920, 1080), (0, 0, 0, 255))
    for controle in raiz.find("controls").findall("control"):
        desenhar_controle(imagem, controle, (0, 0), tamanhos, props)

    if (imagem.width, imagem.height) != (largura_saida, altura_saida):
        imagem = imagem.resize((largura_saida, altura_saida), Image.LANCZOS)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    imagem.convert("RGB").save(args.saida, quality=95)
    print("prova visual: %s (%dx%d, %s)" % (
        args.saida, imagem.width, imagem.height, layout.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
