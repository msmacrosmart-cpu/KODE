#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera a tela de entrada do SMARTEDTV a partir do pacote `smartedtv-src`.

A tela entregue em `smartedtv-src.zip` e HTML/CSS/JS; o app roda Kodi, que so
desenha XML + texturas. Este gerador faz a traducao SEM redesenhar nada: le os
valores do proprio `css/styles.css` (cores, raios, gradientes, tamanhos em
rem/vw/vh/clamp) e os reaproveita

* nas texturas PNG (fundo, cartoes de vidro, botoes, pilulas, placa do QR,
  logo, icone de check) — desenhadas com os mesmos gradientes e raios; e
* no `DialogWelcome.xml` (1920x1080), com as posicoes calculadas pelo box model
  do CSS para uma viewport de 1920x1080.

Os QR Codes sao copiados byte a byte do pacote (assets/qr-checkout.png e
assets/qr-apk.png).

Uso:
    python3 tools/kodi/gerar-tela-entrada.py --origem build_test/src_novo/smartedtv
"""
from __future__ import annotations

import argparse
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

try:  # Pillow so e necessario para gerar texturas (ver Medidas, usado em testes)
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    PIL_DISPONIVEL = True
except ImportError:  # pragma: no cover - ambiente sem Pillow
    PIL_DISPONIVEL = False

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "kodi" / "addons" / "script.smartedtv.welcome"
MEDIA = ADDON / "resources" / "skins" / "Default" / "media"
LAYOUT = ADDON / "resources" / "skins" / "Default" / "1080i" / "DialogWelcome.xml"
FONTE = "NotoSans-Regular.ttf"
SKIN_FONTS = ROOT / "kodi" / "skin.estilo.personalizado" / "fonts" / FONTE

# ---------------------------------------------------------------- viewport
# A tela e SEMPRE horizontal (16:9, 1920x1080). O pacote tem um layout retrato
# so para celular em pe; o app roda em TV/aparelho deitado, entao essa parte do
# CSS nao e traduzida (e o seletor "Celular" do pacote e apenas visual).
VW, VH = 1920.0, 1080.0
assert round(VW / VH, 4) == round(16 / 9, 4), "a tela de entrada e 16:9"
SCALE = 4  # supersampling das texturas


def clamp(lo, v, hi):
    return max(lo, min(v, hi))


def rem(v):
    return v * 16.0


def vw(v):
    return v * VW / 100.0


def vh(v):
    return v * VH / 100.0


def rgba(valor, alfa=1.0):
    """`#rrggbb` + alfa (0..1) -> tupla RGBA do Pillow."""
    valor = valor.lstrip("#")
    r, g, b = (int(valor[i:i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, int(round(alfa * 255)))


# ------------------------------------------------ tokens do css/styles.css
INK = rgba("#f7f7f7")
TXT = rgba("#bcbcbc")
MUT = rgba("#838383")
LINE = rgba("#ffffff", 0.11)
GLASS_A = rgba("#ffffff", 0.085)
GLASS_B = rgba("#ffffff", 0.028)
CHIP_BG = rgba("#ffffff", 0x0D / 255)
CHIP_LINE = rgba("#ffffff", 0x24 / 255)
GHOST_BG = rgba("#ffffff", 0x0B / 255)
BTN_LINE = rgba("#ffffff", 0x2B / 255)
FIELD_BG = rgba("#000000", 0.4)
FIELD_LINE = rgba("#ffffff", 0x26 / 255)
DIALOG_TOP = rgba("#181818")
DIALOG_BOTTOM = rgba("#0d0d0d")
DIALOG_LINE = rgba("#ffffff", 0x24 / 255)
QUIET_TXT = rgba("#d6d6d6")
LEGEND = rgba("#666666")
PLACEHOLDER = rgba("#747474")


# ------------------------------------------------------------------ medidas
class Medidas(object):
    """Box model do CSS resolvido para 1920x1080 (ver tools/kodi/gerar-*.py)."""

    def __init__(self):
        self.stage_w = min(VW, (VH - 42) * 16 / 9)
        self.k = VW / self.stage_w          # stage -> 1920
        self.pad = round(self.stage_w * 0.02 * self.k)
        self.gap = self.pad
        self.largura = int(VW) - 2 * self.pad
        self.col_gap = round(self.stage_w * 0.013 * self.k)
        self.col_w = int((self.largura - 2 * self.col_gap) / 3)
        self.top_h = 90
        self.barra_h = 113
        self.grade_y = self.pad + self.top_h + self.gap
        self.grade_h = int(VH) - self.pad - self.barra_h - self.gap - self.grade_y
        self.barra_y = self.grade_y + self.grade_h + self.gap
        self.card_pad = 13
        self.card_inner = self.col_w - 2 * self.card_pad
        self.qr_plate = 303
        self.qr_img = 270
        self.raio_card = round(rem(1.5) * self.k)
        self.raio_btn = round(rem(0.65) * self.k)
        self.raio_pill = None
        self.fontes = {
            "h1": round(rem(2.0) * self.k),
            "sub": round(rem(0.9) * self.k),
            "seg": round(rem(1.0) * self.k),
            "h2": round(rem(1.55) * self.k),
            "chip": round(rem(0.8) * self.k),
            "eyebrow": round(rem(0.8) * self.k),
            "h3": round(rem(2.55) * self.k),
            "body": round(rem(1.25) * self.k),
            "li": round(rem(1.1) * self.k),
            "hint": round(rem(0.9) * self.k),
            "btn": round(rem(1.0) * self.k),
            "barh3": round(rem(1.35) * self.k),
            "barp": round(rem(0.9) * self.k),
            "field": round(rem(1.0) * self.k),
            "plan": round(rem(0.8) * self.k),
            "bar_btn": round(rem(0.9) * self.k),
            "legend": 11,
        }
        self.btn_h = round(clamp(rem(2.5), vh(5.1), rem(3.6)) * self.k)
        self.seg_h = round(round(self.fontes["seg"] * 1.2) + 2 * round(rem(0.7) * self.k) + 2 * round(rem(0.25) * self.k))
        self.plan_h = round(round(self.fontes["plan"] * 1.2) + 2 * round(rem(0.55) * self.k) + 2 * round(rem(0.25) * self.k))


# ------------------------------------------------------------- utilidades
def fonte(tamanho):
    return ImageFont.truetype(str(SKIN_FONTS), tamanho)


def largura_texto(texto, tamanho):
    return fonte(tamanho).getlength(texto)


def _gradiente_vertical(tamanho, topo, base):
    w, h = tamanho
    img = Image.new("RGBA", (1, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = tuple(int(round(topo[i] + (base[i] - topo[i]) * t)) for i in range(4))
    return img.resize((w, h), Image.BILINEAR)


def retangulo(tamanho, raio, fundo=None, borda=None, largura_borda=1, sombra=None):
    """Retangulo arredondado com antialiasing (desenho em 4x)."""
    w, h = tamanho
    up = Image.new("RGBA", (w * SCALE, h * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(up)
    caixa = (0, 0, w * SCALE - 1, h * SCALE - 1)
    if fundo is not None:
        if isinstance(fundo, tuple):
            d.rounded_rectangle(caixa, radius=raio * SCALE, fill=fundo)
        else:
            mascara = Image.new("L", (w * SCALE, h * SCALE), 0)
            ImageDraw.Draw(mascara).rounded_rectangle(
                caixa, radius=raio * SCALE, fill=255)
            grad = fundo.resize((w * SCALE, h * SCALE), Image.BILINEAR)
            up.paste(grad, (0, 0), mascara)
            d = ImageDraw.Draw(up)
    if sombra:
        desfoque, alfa = sombra
        camada = Image.new("RGBA", (w * SCALE, h * SCALE), (0, 0, 0, 0))
        ImageDraw.Draw(camada).rounded_rectangle(
            caixa, radius=raio * SCALE, fill=(0, 0, 0, alfa))
        camada = camada.filter(ImageFilter.GaussianBlur(desfoque * SCALE))
        base = Image.new("RGBA", up.size, (0, 0, 0, 0))
        base.alpha_composite(camada)
        base.alpha_composite(up)
        up = base
        d = ImageDraw.Draw(up)
        if fundo is not None:
            if isinstance(fundo, tuple):
                d.rounded_rectangle(caixa, radius=raio * SCALE, fill=fundo)
            else:
                mascara = Image.new("L", up.size, 0)
                ImageDraw.Draw(mascara).rounded_rectangle(
                    caixa, radius=raio * SCALE, fill=255)
                up.paste(fundo.resize(up.size, Image.BILINEAR), (0, 0), mascara)
                d = ImageDraw.Draw(up)
    if borda is not None:
        d.rounded_rectangle(caixa, radius=raio * SCALE, outline=borda,
                            width=largura_borda * SCALE)
    return up.resize((w, h), Image.LANCZOS)


def texto_centralizado(tamanho, texto, tamanho_fonte, cor):
    w, h = tamanho
    up = Image.new("RGBA", (w * SCALE, h * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(up)
    f = ImageFont.truetype(str(SKIN_FONTS), tamanho_fonte * SCALE)
    caixa = d.textbbox((0, 0), texto, font=f)
    x = (w * SCALE - (caixa[2] - caixa[0])) / 2 - caixa[0]
    y = (h * SCALE - (caixa[3] - caixa[1])) / 2 - caixa[1]
    d.text((x, y), texto, font=f, fill=cor)
    return up.resize((w, h), Image.LANCZOS)


def icone(tamanho, caminho, cor=(255, 255, 255, 255), espessura=2.4):
    """Icone de traco no estilo dos SVGs do pacote (stroke, 24x24)."""
    w = h = tamanho
    up = Image.new("RGBA", (w * SCALE, h * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(up)
    k = w * SCALE / 24.0
    e = max(1, int(round(espessura * k)))
    bolinha = e // 2

    def linha(a, b):
        d.line([a[0] * k, a[1] * k, b[0] * k, b[1] * k], fill=cor, width=e)
        for p in (a, b):
            d.ellipse([p[0] * k - bolinha, p[1] * k - bolinha,
                       p[0] * k + bolinha, p[1] * k + bolinha], fill=cor)

    for trecho in caminho:
        linha(trecho[0], trecho[1])
    return up.resize((w, h), Image.LANCZOS)


# --------------------------------------------------------------- texturas
def gerar_fundo(med: Medidas) -> Image.Image:
    """`radial-gradient(115% 95% at 10% -10%, …)` + os dois brilhos do CSS."""
    # gradiente radial eliptico desenhado em mascara 8 bits (rapido e fiel)
    centro = (-0.10 * VW, -0.10 * VH)
    raio = (1.15 * VW, 0.95 * VH)
    mascara = Image.new("L", (int(VW), int(VH)), 255)
    px = mascara.load()
    for y in range(int(VH)):
        dy = (y - centro[1]) / raio[1]
        for x in range(int(VW)):
            dx = (x - centro[0]) / raio[0]
            d = (dx * dx + dy * dy) ** 0.5
            if d <= 0.48:
                v = 0
            elif d >= 1.0:
                v = 255
            else:
                v = int(round((d - 0.48) / 0.52 * 255))
            px[x, y] = v
    claro = Image.new("RGBA", (int(VW), int(VH)), (0x18, 0x18, 0x18, 255))
    escuro = Image.new("RGBA", (int(VW), int(VH)), rgba("#0a0a0c"))
    base = Image.composite(escuro, claro, mascara)
    fundo = Image.new("RGBA", (int(VW), int(VH)), rgba("#050505"))
    fundo.paste(base, (0, 0), mascara.point(lambda v: 255))

    for (cx, cy, w, h, alfa) in ((-0.10 * VW, -0.24 * VH, 0.42 * VW, 0.42 * VH, 0.08),
                                 (1.10 * VW, 1.18 * VH, 0.36 * VW, 0.36 * VH, 0.05)):
        brilho = Image.new("RGBA", fundo.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(brilho)
        passos = 48
        for i in range(passos, 0, -1):
            t = i / passos
            r = min(w, h) / 2 * t
            a = int(255 * alfa * (1 - t) ** 1.6)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, a))
        brilho = brilho.filter(ImageFilter.GaussianBlur(rem(4) * med.k))
        fundo.alpha_composite(brilho)
    return fundo


def gerar_cartao(med: Medidas) -> Image.Image:
    """`.card`: vidro com gradiente, borda 1px e realce interno no topo."""
    cartao = retangulo((med.col_w, med.grade_h), med.raio_card,
                       _gradiente_vertical((med.col_w, med.grade_h), GLASS_A, GLASS_B),
                       LINE, 1)
    realce = Image.new("RGBA", cartao.size, (0, 0, 0, 0))
    mascara = Image.new("L", cartao.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, cartao.width - 1, cartao.height - 1), radius=med.raio_card, fill=255)
    linha = Image.new("RGBA", cartao.size, (0, 0, 0, 0))
    ImageDraw.Draw(linha).line([(med.raio_card, 1), (cartao.width - med.raio_card, 1)],
                               fill=(255, 255, 255, 0x12), width=1)
    realhe = Image.composite(linha, Image.new("RGBA", cartao.size, (0, 0, 0, 0)), mascara)
    cartao.alpha_composite(realhe)
    return cartao


def gerar_barra(med: Medidas) -> Image.Image:
    return retangulo((med.largura, med.barra_h), round(rem(1.2) * med.k),
                     _gradiente_vertical((med.largura, med.barra_h),
                                         rgba("#ffffff", 0x13 / 255),
                                         rgba("#ffffff", 0x05 / 255)),
                     LINE, 1)


def gerar_texturas(med: Medidas) -> dict:
    MEDIA.mkdir(parents=True, exist_ok=True)
    saida = {}

    fundo = gerar_fundo(med)
    fundo.convert("RGB").save(MEDIA / "bg.png", optimize=True)
    saida["bg"] = fundo.size

    cartao = gerar_cartao(med)
    cartao.save(MEDIA / "card.png", optimize=True)
    saida["card"] = cartao.size

    barra = gerar_barra(med)
    barra.save(MEDIA / "bar.png", optimize=True)
    saida["bar"] = barra.size

    r = med.raio_btn
    b = med.btn_h
    # botoes: normal (vidro), primario (branco), quieto (transparente) e focados
    retangulo((180, b), r, GHOST_BG, BTN_LINE, 1).save(MEDIA / "btn_ghost.png")
    retangulo((180, b), r, _gradiente_vertical((180, b), rgba("#ffffff"), rgba("#ebebeb"))).save(
        MEDIA / "btn_primary.png")
    retangulo((180, b), r, (0, 0, 0, 0)).save(MEDIA / "btn_quiet.png")
    foco_ghost = retangulo((180, b), r, rgba("#ffffff"))
    foco_ghost.save(MEDIA / "btn_ghost_focus.png")
    retangulo((180, b), r, rgba("#ffffff")).save(MEDIA / "btn_primary_focus.png")
    # "quiet" focado: o CSS troca para fundo branco tambem
    retangulo((180, b), r, rgba("#ffffff")).save(MEDIA / "btn_quiet_focus.png")
    saida["botao"] = (180, b)

    # campo de codigo
    retangulo((240, b), r, FIELD_BG, FIELD_LINE, 1).save(MEDIA / "field.png")
    campo_foco = retangulo((240, b), r, FIELD_BG, rgba("#aaaaaa"), 1)
    anel = Image.new("RGBA", campo_foco.size, (0, 0, 0, 0))
    ImageDraw.Draw(anel).rounded_rectangle(
        (1, 1, campo_foco.width - 2, campo_foco.height - 2), radius=r,
        outline=rgba("#ffffff", 0x55 / 255), width=2)
    campo_foco.alpha_composite(anel)
    campo_foco.save(MEDIA / "field_focus.png")

    # pilulas: container e pilula ativa (raio = altura/2)
    for nome, altura, ativo in (("seg", med.seg_h, False), ("seg_active", med.seg_h, True),
                                ("plan", med.plan_h, False), ("plan_active", med.plan_h, True)):
        raio = altura // 2
        if ativo:
            img = retangulo((altura * 3, altura), raio,
                            _gradiente_vertical((altura * 3, altura),
                                                rgba("#ffffff"), rgba("#e8e8e8")))
        else:
            img = retangulo((altura * 3, altura), raio, GHOST_BG, LINE, 1)
        img.save(MEDIA / ("%s.png" % nome))

    # chip do cabecalho dos cartoes
    chip_h = 28
    retangulo((120, chip_h), chip_h // 2, CHIP_BG, CHIP_LINE, 1).save(MEDIA / "chip.png")

    # placa branca do QR Code
    retangulo((80, 80), round(rem(0.6) * med.k), rgba("#ffffff")).save(MEDIA / "qr_plate.png")

    # check do item de lista
    tick = med.fontes["li"] + 5
    img = Image.new("RGBA", (tick, tick), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, tick - 1, tick - 1], fill=rgba("#ffffff", 0x14 / 255),
              outline=rgba("#ffffff", 0x29 / 255), width=1)
    m = tick / 24.0
    d.line([(6 * m, 12.4 * m), (10.2 * m, 16.6 * m), (18 * m, 7.4 * m)],
           fill=rgba("#ffffff"), width=max(1, int(round(2.6 * m))), joint="curve")
    img.resize((tick * SCALE, tick * SCALE), Image.LANCZOS).resize((tick, tick), Image.LANCZOS).save(
        MEDIA / "tick.png")
    saida["tick"] = tick

    # logo (mesmo glifo da marca: quadrado prata + triangulo escuro)
    logo = Image.new("RGBA", (68 * SCALE, 68 * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(logo)
    grad = _gradiente_vertical((68 * SCALE, 68 * SCALE),
                               rgba("#ffffff"), rgba("#bdbdbd")).resize(
        (68 * SCALE, 68 * SCALE))
    mascara = Image.new("L", logo.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, logo.width - 1, logo.height - 1), radius=17 * SCALE, fill=255)
    logo.paste(grad, (0, 0), mascara)
    d = ImageDraw.Draw(logo)
    d.rounded_rectangle((0, 0, logo.width - 1, logo.height - 1),
                        radius=17 * SCALE, outline=(255, 255, 255, 60), width=SCALE)
    kk = 68 * SCALE / 64.0
    d.polygon([(26 * kk, 20.5 * kk), (26 * kk, 43.5 * kk), (45.5 * kk, 32 * kk)],
              fill=rgba("#090909"))
    logo.resize((68, 68), Image.LANCZOS).save(MEDIA / "logo.png")

    # linha do eyebrow, divisor da barra
    linha = Image.new("RGBA", (23, 2), rgba("#ffffff", 0x8C / 255))
    linha.save(MEDIA / "eyebrow_line.png")
    Image.new("RGBA", (2, 40), rgba("#ffffff", 0x25 / 255)).save(MEDIA / "divider.png")

    # camadas dos dialogos
    overlay = Image.new("RGBA", (int(VW), int(VH)), (0, 0, 0, 170))
    overlay.save(MEDIA / "overlay.png")
    painel = retangulo((160, 120), round(rem(1.2) * med.k),
                       _gradiente_vertical((160, 120), DIALOG_TOP, DIALOG_BOTTOM),
                       DIALOG_LINE, 1)
    painel.save(MEDIA / "dialog.png")

    # icones das acoes (traco branco, como os SVGs do pacote)
    icone(20, [((21, 12), (12, 12))])
    refresh = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    up = Image.new("RGBA", (20 * SCALE, 20 * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(up)
    kk = 20 * SCALE / 24.0
    e = max(1, int(round(2.4 * kk)))
    d.arc([4 * kk, 4 * kk, 20 * kk, 20 * kk], start=-60, end=300, fill=rgba("#ffffff"),
          width=e)
    d.line([(20 * kk, 3 * kk), (20.4 * kk, 9 * kk), (14.4 * kk, 8.6 * kk)],
           fill=rgba("#ffffff"), width=e)
    up.resize((20, 20), Image.LANCZOS).save(MEDIA / "icon_refresh.png")
    down = Image.new("RGBA", (20 * SCALE, 20 * SCALE), (0, 0, 0, 0))
    d = ImageDraw.Draw(down)
    kk = 20 * SCALE / 24.0
    e = max(1, int(round(2.4 * kk)))
    d.line([(12 * kk, 3 * kk), (12 * kk, 15 * kk)], fill=rgba("#ffffff"), width=e)
    d.line([(7 * kk, 10 * kk), (12 * kk, 15 * kk), (17 * kk, 10 * kk)],
           fill=rgba("#ffffff"), width=e, joint="curve")
    d.line([(5 * kk, 21 * kk), (19 * kk, 21 * kk)], fill=rgba("#ffffff"), width=e)
    down.resize((20, 20), Image.LANCZOS).save(MEDIA / "icon_download.png")
    return saida


# -------------------------------------------------------------------- XML
def xml_label(cid, x, y, w, h, texto, fonte_nome, cor, align="left", aligny="top"):
    el = ET.Element("control", {"type": "label", "id": str(cid)})
    for tag, valor in (("left", x), ("top", y), ("width", w), ("height", h)):
        ET.SubElement(el, tag).text = str(valor)
    ET.SubElement(el, "label").text = texto
    ET.SubElement(el, "font").text = fonte_nome
    ET.SubElement(el, "textcolor").text = cor
    if align != "left":
        ET.SubElement(el, "align").text = align
    if aligny != "top":
        ET.SubElement(el, "aligny").text = aligny
    return el


def xml_imagem(cid, x, y, w, h, textura, aspecto=None):
    el = ET.Element("control", {"type": "image", "id": str(cid)})
    for tag, valor in (("left", x), ("top", y), ("width", w), ("height", h)):
        ET.SubElement(el, tag).text = str(valor)
    ET.SubElement(el, "texture").text = textura
    if aspecto:
        ET.SubElement(el, "aspectratio").text = aspecto
    return el


def xml_botao(cid, x, y, w, h, rotulo, fonte_nome, cor_texto, normal, foco,
              cor_foco=None, border=0):
    el = ET.Element("control", {"type": "button", "id": str(cid)})
    for tag, valor in (("left", x), ("top", y), ("width", w), ("height", h)):
        ET.SubElement(el, tag).text = str(valor)
    ET.SubElement(el, "label").text = rotulo
    ET.SubElement(el, "font").text = fonte_nome
    ET.SubElement(el, "textcolor").text = cor_texto
    ET.SubElement(el, "focusedcolor").text = cor_foco or cor_texto
    atributos = {"border": str(border)} if border else {}
    ET.SubElement(el, "texturefocus", atributos).text = foco
    ET.SubElement(el, "texturenofocus", atributos).text = normal
    return el


def indentar(el, nivel=0):
    if len(el):
        el.text = "\n" + "  " * (nivel + 1)
        for filho in el:
            filho.tail = "\n" + "  " * (nivel + 1)
            indentar(filho, nivel + 1)
        ultimo = el[-1]
        ultimo.tail = "\n" + "  " * nivel
    return el


def main(argv=None):
    if not PIL_DISPONIVEL:
        raise SystemExit(
            "Pillow e necessario para gerar as texturas: "
            "python3 -m pip install Pillow==11.3.0")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origem", type=Path, required=True,
                        help="pasta smartedtv/ do pacote smartedtv-src")
    args = parser.parse_args(argv)
    origem = args.origem

    med = Medidas()
    print("layout: pad=%(pad)d col=%(col_w)d grade=%(grade_h)d barra=%(barra_h)d" % vars(med))

    texturas = gerar_texturas(med)
    print("texturas:", len(texturas))

    # QR Codes: copia byte a byte do pacote
    shutil.copyfile(origem / "assets" / "qr-checkout.png", MEDIA / "qr_checkout.png")
    shutil.copyfile(origem / "assets" / "qr-apk.png", MEDIA / "qr_apk.png")
    print("QR Codes copiados do pacote")

    # estilos de fonte: um nome por tamanho usado (o Kodi so conhece o que a
    # skin declara; o injetor acrescenta exatamente esta lista em cada skin)
    estilos = {}
    for chave, tamanho in med.fontes.items():
        estilos[chave] = "wf%d" % tamanho
    unicos = sorted({t for t in med.fontes.values()})

    win = ET.Element("window")
    ET.SubElement(win, "defaultcontrol", {"always": "true"}).text = "310"
    coords = ET.SubElement(win, "coordinates")
    ET.SubElement(coords, "system").text = "1"
    ET.SubElement(coords, "posx").text = "0"
    ET.SubElement(coords, "posy").text = "0"
    controles = ET.SubElement(win, "controls")

    mut = "FF838383"
    txt = "FFBCBCBC"
    ink = "FFF7F7F7"
    escuro = "FF080808"

    # fundo
    controles.append(xml_imagem(1, 0, 0, 1920, 1080, "bg.png"))

    # --- topo: marca + seletor de aparelho -------------------------------
    topo_y = med.pad + (med.top_h - 68) // 2
    controles.append(xml_imagem(10, med.pad, topo_y, 68, 68, "logo.png"))

    marca_x = med.pad + 68 + 17
    h1_y = topo_y + 2
    controles.append(xml_label(11, marca_x, h1_y, 400, med.fontes["h1"] + 8,
                               "SMARTEDTV", estilos["h1"], ink))
    sub_y = h1_y + med.fontes["h1"] + 8 + 7
    controles.append(xml_label(12, marca_x, sub_y, 400, med.fontes["sub"] + 6,
                               "Ativação e assinatura", estilos["sub"], mut))

    seg_txt = ["Android TV", "Celular"]
    seg_pad_x = round(rem(1.5) * med.k)
    seg_larg = [round(largura_texto(t, med.fontes["seg"]) + 2 * seg_pad_x) for t in seg_txt]
    seg_w = sum(seg_larg) + 2 * round(rem(0.25) * med.k) + round(rem(0.25) * med.k)
    seg_x = med.pad + med.largura - seg_w
    seg_y = med.pad + (med.top_h - med.seg_h) // 2
    controles.append(xml_imagem(13, seg_x, seg_y, seg_w, med.seg_h, "seg.png", "stretch"))
    bx = seg_x + round(rem(0.25) * med.k)
    controles.append(xml_botao(130, bx, seg_y + round(rem(0.25) * med.k), seg_larg[0],
                               med.seg_h - 2 * round(rem(0.25) * med.k), seg_txt[0],
                               estilos["seg"], escuro, "seg_active.png", "seg_active.png",
                               border=(med.seg_h // 2)))
    bx += seg_larg[0] + round(rem(0.25) * med.k)
    controles.append(xml_botao(131, bx, seg_y + round(rem(0.25) * med.k), seg_larg[1],
                               med.seg_h - 2 * round(rem(0.25) * med.k), seg_txt[1],
                               estilos["seg"], txt, "seg.png", "seg_active.png",
                               cor_foco=escuro, border=(med.seg_h // 2)))

    # --- grade dos cartoes -----------------------------------------------
    xs = [med.pad, med.pad + med.col_w + med.col_gap,
          med.pad + 2 * (med.col_w + med.col_gap)]
    for i, x in enumerate(xs):
        controles.append(xml_imagem(20 + i, x, med.grade_y, med.col_w, med.grade_h,
                                    "card.png", "stretch"))

    c1 = xs[0] + med.card_pad
    interno = med.card_inner
    topo = med.grade_y + med.card_pad

    # cartao 1 — boas-vindas
    y = topo + 2
    controles.append(xml_imagem(24, c1, y + 5, 23, 2, "eyebrow_line.png"))
    controles.append(xml_label(25, c1 + 29, y, interno - 29, med.fontes["eyebrow"] + 4,
                               "BEM-VINDO", estilos["eyebrow"], mut))
    y += med.fontes["eyebrow"] + 4 + 12 + 12
    for i, linha in enumerate(("Sua TV,", "do seu jeito.")):
        controles.append(xml_label(26 + i, c1, y + i * round(med.fontes["h3"] * 1.09),
                                   interno, round(med.fontes["h3"] * 1.12),
                                   linha, estilos["h3"], ink))
    y += 2 * round(med.fontes["h3"] * 1.09) + 8
    controles.append(xml_label(28, c1, y, interno, round(med.fontes["body"] * 2.9),
                               "Ative o VIP com um código ou continue gratuitamente com anúncios.",
                               estilos["body"], txt))
    y += round(med.fontes["body"] * 2.9) + 14

    btn_y = med.grade_y + med.card_pad + med.grade_h - 2 * med.card_pad - med.btn_h

    # `.list{margin:auto 0 6%}`: a lista fica logo acima do botao, com o vazio
    # entre ela e o paragrafo (como no flex do CSS)
    itens = ("Canais ao vivo, sem travar", "Sem anúncios com o VIP ativo",
             "Ativação em poucos segundos")
    gap_item = round(rem(1.6) * med.k)
    li_h = max(med.fontes["li"] + 6, texturas["tick"] + 4)
    bloco_h = 3 * li_h + 2 * gap_item
    lista_y = btn_y - round(med.grade_h * 0.06) - bloco_h
    assert lista_y > y, (lista_y, y)
    for i, item in enumerate(itens):
        ly = lista_y + i * (li_h + gap_item)
        controles.append(xml_imagem(30 + i, c1 + 4, ly + (li_h - texturas["tick"]) // 2,
                                    texturas["tick"], texturas["tick"], "tick.png"))
        controles.append(xml_label(34 + i, c1 + 4 + texturas["tick"] + 13,
                                   ly + (li_h - (med.fontes["li"] + 6)) // 2,
                                   interno - texturas["tick"] - 17, med.fontes["li"] + 6,
                                   item, estilos["li"], txt))
    atualizar_w = round(largura_texto("ATUALIZAR APLICATIVO", med.fontes["btn"]) + 2 * round(rem(1.2) * med.k) + 8 + 20)
    ax = c1 + (interno - atualizar_w) // 2
    controles.append(xml_botao(123, ax, btn_y, atualizar_w, med.btn_h,
                               "ATUALIZAR APLICATIVO", estilos["btn"], ink,
                               "btn_ghost.png", "btn_ghost_focus.png",
                               cor_foco=escuro, border=med.raio_btn))
    inicio_texto = ax + (atualizar_w - largura_texto("ATUALIZAR APLICATIVO", med.fontes["btn"])) / 2
    icone_x = round(inicio_texto - 8 - 20)
    controles.append(xml_imagem(124, icone_x, btn_y + (med.btn_h - 20) // 2, 20, 20,
                                "icon_refresh.png"))

    # cartao 2 — assinatura (QR do checkout)
    x2 = xs[1]
    c2 = x2 + med.card_pad
    head_y = topo + 2
    controles.append(xml_label(40, c2, head_y, interno - 150, med.fontes["h2"] + 8,
                               "Sem anúncios", estilos["h2"], ink))
    chip_txt = "Plano mensal"
    chip_w = round(largura_texto(chip_txt, med.fontes["chip"]) + 2 * round(rem(0.8) * med.k))
    chip_h = med.fontes["chip"] + 15
    chip_x = c2 + interno - chip_w
    controles.append(xml_imagem(41, chip_x, head_y + 2, chip_w, chip_h, "chip.png", "stretch"))
    controles.append(xml_label(42, chip_x, head_y + 2 + (chip_h - med.fontes["chip"]) // 2 - 1,
                               chip_w, med.fontes["chip"] + 4, chip_txt, estilos["chip"], txt,
                               align="center"))

    hint_h = round(med.fontes["hint"] * 2.83)
    hint_y = btn_y - 14 - hint_h
    prato = med.qr_plate
    area_topo = head_y + chip_h + 14
    prato_y = area_topo + (hint_y - 14 - area_topo - prato) // 2
    prato_x = x2 + (med.col_w - prato) // 2
    controles.append(xml_imagem(43, prato_x, prato_y, prato, prato, "qr_plate.png", "stretch"))
    qr_off = (prato - med.qr_img) // 2
    controles.append(xml_imagem(44, prato_x + qr_off, prato_y + qr_off, med.qr_img,
                                med.qr_img, "qr_checkout.png", "keep"))
    controles.append(xml_label(45, c2, hint_y, interno, hint_h,
                               "Aponte a câmera de outro celular.[CR]Valor e condições aparecem no checkout.",
                               estilos["hint"], mut, align="center"))
    controles.append(xml_botao(120, c2, btn_y, interno, med.btn_h, "Abrir checkout",
                               estilos["btn"], ink, "btn_ghost.png", "btn_ghost_focus.png",
                               cor_foco=escuro, border=med.raio_btn))

    # cartao 3 — indicação (QR do app)
    x3 = xs[2]
    c3 = x3 + med.card_pad
    controles.append(xml_label(50, c3, head_y, interno - 120, med.fontes["h2"] + 8,
                               "Indique e ganhe", estilos["h2"], ink))
    chip2 = "Compartilhar"
    chip2_w = round(largura_texto(chip2, med.fontes["chip"]) + 2 * round(rem(0.8) * med.k))
    chip2_x = c3 + interno - chip2_w
    controles.append(xml_imagem(51, chip2_x, head_y + 2, chip2_w, chip_h, "chip.png", "stretch"))
    controles.append(xml_label(52, chip2_x, head_y + 2 + (chip_h - med.fontes["chip"]) // 2 - 1,
                               chip2_w, med.fontes["chip"] + 4, chip2, estilos["chip"], txt,
                               align="center"))

    baixar_y = btn_y
    share_y = btn_y - med.btn_h - 8
    hint3_y = share_y - 14 - hint_h
    area3_topo = head_y + chip_h + 14
    prato3_y = area3_topo + (hint3_y - 14 - area3_topo - prato) // 2
    prato3_x = x3 + (med.col_w - prato) // 2
    controles.append(xml_imagem(53, prato3_x, prato3_y, prato, prato, "qr_plate.png", "stretch"))
    controles.append(xml_imagem(54, prato3_x + qr_off, prato3_y + qr_off, med.qr_img,
                                med.qr_img, "qr_apk.png", "keep"))
    controles.append(xml_label(55, c3, hint3_y, interno, hint_h,
                               "Aponte a câmera e envie o link[CR]do app a quem quiser.",
                               estilos["hint"], mut, align="center"))
    controles.append(xml_botao(121, c3, share_y, interno, med.btn_h, "Compartilhar link",
                               estilos["btn"], ink, "btn_ghost.png", "btn_ghost_focus.png",
                               cor_foco=escuro, border=med.raio_btn))
    texto_baixar = "Baixar APK (Android)"
    baixar_w = round(largura_texto(texto_baixar, med.fontes["btn"]) + 2 * round(rem(1.2) * med.k) + 8 + 20)
    bx3 = c3 + (interno - baixar_w) // 2
    controles.append(xml_botao(122, bx3, baixar_y, baixar_w, med.btn_h, texto_baixar,
                               estilos["btn"], QUIET_TXT_HEX, "btn_quiet.png",
                               "btn_quiet_focus.png", cor_foco=escuro, border=med.raio_btn))
    inicio3 = bx3 + (baixar_w - largura_texto(texto_baixar, med.fontes["btn"])) / 2
    icone3_x = round(inicio3 - 8 - 20)
    controles.append(xml_imagem(125, icone3_x, baixar_y + (med.btn_h - 20) // 2, 20, 20,
                                "icon_download.png"))

    # --- barra de ativacao -----------------------------------------------
    barra_y = med.barra_y
    py = round(1842 * 0.015)
    px = round(1842 * 0.016)
    by = barra_y + py
    bx0 = med.pad + px
    inner_bar = med.largura - 2 * px
    copy_w = round(inner_bar * 0.28)
    # `.bar{background:linear-gradient(180deg,#ffffff13,#ffffff05);border:1px solid
    # var(--line);border-radius:1.2rem}`: o painel de vidro da barra
    controles.append(xml_imagem(6, med.pad, barra_y, med.largura, med.barra_h,
                                "bar.png", "stretch"))
    controles.append(xml_label(60, bx0, by + 2, copy_w, med.fontes["barh3"] + 8,
                               "Já é assinante? Ative seu VIP", estilos["barh3"], ink))
    controles.append(xml_label(61, bx0, by + 2 + med.fontes["barh3"] + 12, copy_w,
                               med.fontes["barp"] + 6, "Digite o código que você recebeu.",
                               estilos["barp"], mut))

    gap_bar = round(1842 * 0.015)
    form_x = bx0 + copy_w + gap_bar
    form_dir = bx0 + inner_bar - gap_bar
    gratis_txt = "Continuar com anúncios"
    gratis_w = min(round(inner_bar * 0.22),
                   round(largura_texto(gratis_txt, med.fontes["bar_btn"]) + 2 * round(rem(1.2) * med.k)))
    gratis_x = form_dir - gratis_w
    div_x = gratis_x - gap_bar
    form_dir = div_x - gap_bar

    controles.append(xml_imagem(62, div_x, by + 4, 2, med.btn_h - 8, "divider.png", "stretch"))
    controles.append(xml_botao(312, gratis_x, by, gratis_w, med.btn_h, gratis_txt,
                               estilos["bar_btn"], QUIET_TXT_HEX, "btn_quiet.png",
                               "btn_quiet_focus.png", cor_foco=escuro, border=med.raio_btn))

    ativar_txt = "Ativar"
    ativar_w = round(largura_texto(ativar_txt, med.fontes["btn"]) + 2 * round(rem(1.2) * med.k))
    ativar_x = form_dir - ativar_w
    field_w = ativar_x - 11 - (form_x + 0)          # preenchido depois de medir o plan
    plan_txt = ["10 min", "1 mês"]
    plan_pad = round(rem(0.9) * med.k)
    plan_larg = [round(largura_texto(t, med.fontes["plan"]) + 2 * plan_pad) for t in plan_txt]
    plan_w = sum(plan_larg) + 2 * round(rem(0.25) * med.k) + round(rem(0.25) * med.k)
    controles.append(xml_imagem(63, form_x, by + (med.btn_h - med.plan_h) // 2, plan_w,
                                med.plan_h, "plan.png", "stretch"))
    px0 = form_x + round(rem(0.25) * med.k)
    ph = med.plan_h - 2 * round(rem(0.25) * med.k)
    # o plano ativo e o que esta em foco (mesma linguagem do D-pad no Kodi);
    # a pilula branca do pacote aparece no item escolhido
    controles.append(xml_botao(140, px0, by + (med.btn_h - ph) // 2, plan_larg[0], ph,
                               plan_txt[0], estilos["plan"], txt, "plan.png",
                               "plan_active.png", cor_foco=escuro, border=ph // 2))
    px0 += plan_larg[0] + round(rem(0.25) * med.k)
    controles.append(xml_botao(141, px0, by + (med.btn_h - ph) // 2, plan_larg[1], ph,
                               plan_txt[1], estilos["plan"], txt, "plan.png",
                               "plan_active.png", cor_foco=escuro, border=ph // 2))

    field_x = form_x + plan_w + 11
    field_w = ativar_x - 11 - field_x
    edit = ET.Element("control", {"type": "edit", "id": "310"})
    for tag, valor in (("left", field_x), ("top", by), ("width", field_w),
                       ("height", med.btn_h)):
        ET.SubElement(edit, tag).text = str(valor)
    ET.SubElement(edit, "label").text = "Código de ativação"
    ET.SubElement(edit, "font").text = estilos["field"]
    ET.SubElement(edit, "textcolor").text = "FFFFFFFF"
    ET.SubElement(edit, "disabledcolor").text = "FF747474"
    ET.SubElement(edit, "texturefocus", {"border": str(med.raio_btn)}).text = "field_focus.png"
    ET.SubElement(edit, "texturenofocus", {"border": str(med.raio_btn)}).text = "field.png"
    controles.append(edit)
    controles.append(xml_botao(311, ativar_x, by, ativar_w, med.btn_h, ativar_txt,
                               estilos["btn"], escuro, "btn_primary.png",
                               "btn_primary_focus.png", border=med.raio_btn))

    # --- legenda inferior -------------------------------------------------
    controles.append(xml_label(70, 0, 1046, 1920, 22,
                               "Android TV  ·  16:9  ·  tela única, sem rolagem  ·  setas/Enter navegam (D-pad)",
                               estilos["legend"], "FF666666", align="center"))

    # --- dialogo: continuar com anuncios ---------------------------------
    grupo = ET.SubElement(controles, "control", {"type": "group", "id": "900"})
    ET.SubElement(grupo, "visible").text = (
        "String.IsEqual(Window.Property(welcome_dialog),ads)")
    grupo.append(xml_imagem(901, 0, 0, 1920, 1080, "overlay.png"))
    dialogo_w = 708
    dialogo_x = (1920 - dialogo_w) // 2
    corpo = ("Você vai ver anúncios durante o uso. Para removê-los,[CR]"
             "assine pelo checkout ou ative um código VIP quando quiser.")
    dialogo_h = 300
    dialogo_y = (1080 - dialogo_h) // 2
    grupo.append(xml_imagem(902, dialogo_x, dialogo_y, dialogo_w, dialogo_h,
                            "dialog.png", "stretch"))
    grupo.append(xml_label(903, dialogo_x + 38, dialogo_y + 33, dialogo_w - 76, 40,
                           "Continuar com anúncios?", estilos["h2"], ink))
    grupo.append(xml_label(904, dialogo_x + 38, dialogo_y + 83, dialogo_w - 76, 100,
                           corpo, estilos["field"], txt))
    grupo.append(xml_botao(905, dialogo_x + 38, dialogo_y + 205, 300, med.btn_h, "Voltar",
                           estilos["btn"], ink, "btn_quiet.png", "btn_ghost_focus.png",
                           cor_foco=escuro, border=med.raio_btn))
    grupo.append(xml_botao(906, dialogo_x + 348, dialogo_y + 205, 322, med.btn_h,
                           "Continuar com anúncios", estilos["bar_btn"], escuro,
                           "btn_primary.png", "btn_primary_focus.png",
                           border=med.raio_btn))

    # --- dialogo: resultado (dinamico) -----------------------------------
    grupo2 = ET.SubElement(controles, "control", {"type": "group", "id": "950"})
    ET.SubElement(grupo2, "visible").text = (
        "String.IsEqual(Window.Property(welcome_dialog),status)")
    grupo2.append(xml_imagem(951, 0, 0, 1920, 1080, "overlay.png"))
    grupo2.append(xml_imagem(952, dialogo_x, dialogo_y, dialogo_w, dialogo_h,
                             "dialog.png", "stretch"))
    grupo2.append(xml_label(953, dialogo_x + 38, dialogo_y + 33, dialogo_w - 76, 40,
                            "$INFO[Window.Property(welcome_status_title)]",
                            estilos["h2"], ink))
    grupo2.append(xml_label(954, dialogo_x + 38, dialogo_y + 83, dialogo_w - 76, 100,
                            "$INFO[Window.Property(welcome_status_text)]",
                            estilos["field"], txt))
    grupo2.append(xml_botao(955, dialogo_x + dialogo_w - 38 - 322, dialogo_y + 205, 322,
                            med.btn_h, "$INFO[Window.Property(welcome_status_ok)]",
                            estilos["bar_btn"], escuro, "btn_primary.png",
                            "btn_primary_focus.png", border=med.raio_btn))

    indentar(win)
    texto = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(win, encoding="unicode") + "\n"
    LAYOUT.write_text(texto, encoding="utf-8")
    ET.fromstring(texto.encode("utf-8"))
    print("XML:", LAYOUT.relative_to(ROOT), "| fontes:", ", ".join(estilos[k] for k in
                                                                  ("h1", "h2", "h3", "btn")))
    print("fontes necessarias:", ",".join("wf%d" % t for t in unicos))
    return 0


QUIET_TXT_HEX = "FFD6D6D6"


if __name__ == "__main__":
    raise SystemExit(main())
