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
        # Grade de referencia: 8 px uteis na escala da TV. Todo respiro e um
        # multiplo dela, para nada ficar "quase alinhado" com nada.
        self.pad = 56                        # margem da tela
        self.gap = 32                        # entre cabecalho, grade e barra
        self.largura = int(VW) - 2 * self.pad
        self.col_gap = 28                    # entre os tres cartoes
        self.col_w = int((self.largura - 2 * self.col_gap) / 3)
        self.top_h = 96                      # altura do cabecalho
        self.barra_h = 104                   # altura da barra de ativacao
        self.grade_y = self.pad + self.top_h + self.gap
        self.grade_h = int(VH) - self.pad - self.barra_h - self.gap - self.grade_y
        self.barra_y = self.grade_y + self.grade_h + self.gap
        self.card_pad = 32                   # respiro interno do cartao
        self.card_inner = self.col_w - 2 * self.card_pad
        self.qr_plate = 320
        self.qr_img = self.qr_plate - 48     # sobra branca em volta do QR
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


_FONTE_CACHE = {}


def _fonte_medida(tamanho):
    if tamanho not in _FONTE_CACHE:
        _FONTE_CACHE[tamanho] = fonte(tamanho)
    return _FONTE_CACHE[tamanho]


def largura_texto(texto, tamanho):
    return _fonte_medida(tamanho).getlength(texto)


def altura_texto(texto, tamanho):
    """Altura real da linha (ascendente+descendente), o que o Kodi desenha."""
    caixa = _fonte_medida(tamanho).getbbox(texto or "Ágjy")
    return caixa[3] - caixa[1]


def altura_linha(tamanho):
    """Caixa segura para uma linha: cobre acentos e descendentes."""
    return altura_texto("ÁÉÍÓÚÇÃÕgjpqyJ", tamanho)


def quebrar_em_linhas(texto, tamanho, largura):
    """Quebra o texto por palavra respeitando a largura real em px.

    O Kodi nao quebra linha em <label> (so em <textbox>/<wrapmultiline>); por
    isso cada linha vira um controle proprio, com a altura medida da fonte.
    """
    linhas = []
    for paragrafo in texto.replace("[CR]", "\n").split("\n"):
        atual = ""
        for palavra in paragrafo.split(" "):
            teste = (atual + " " + palavra).strip()
            if atual and largura_texto(teste, tamanho) > largura:
                linhas.append(atual)
                atual = palavra
            else:
                atual = teste
        linhas.append(atual)
    return linhas


def xml_texto(cid, x, y, largura, texto, fonte_nome, tamanho, cor,
              align="left", entrelinha=1.32):
    """Um <label> por linha, com a altura exata da fonte.

    Devolve (controles, altura_total). Assim nenhuma letra fica cortada em cima
    ou embaixo e nada estoura a largura do cartao.
    """
    controles = []
    linhas = quebrar_em_linhas(texto, tamanho, largura)
    passo = round(tamanho * entrelinha)
    h_linha = altura_linha(tamanho)
    for i, linha in enumerate(linhas):
        controles.append(xml_label(cid + i, x, y + i * passo, largura, h_linha,
                                   linha, fonte_nome, cor, align=align))
    return controles, (len(linhas) - 1) * passo + h_linha


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
    retangulo((180, b), r, (0, 0, 0, 0)).save(MEDIA / "btn_quiet.png")  # dialogo: Voltar
    foco_ghost = retangulo((180, b), r, rgba("#ffffff"))
    foco_ghost.save(MEDIA / "btn_ghost_focus.png")
    retangulo((180, b), r, rgba("#ffffff")).save(MEDIA / "btn_primary_focus.png")
    # (o "quiet" focado usa btn_ghost_focus.png: fundo branco, igual ao CSS)
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

    # sombra/escurecimento atras do dialogo: garante que nada da tela apareca
    # por tras do texto (o Kodi nao tem blur; o CSS usa backdrop-filter)
    retangulo((760, 352), round(rem(1.2) * med.k) + 8,
              rgba("#000000", 0xB0 / 255), None, 0,
              sombra=(round(rem(1.4) * med.k), 120)).save(MEDIA / "scrim.png")

    # (as texturas do seletor "Android TV / Celular" e das pilulas "10 min /
    #  1 mes" nao existem mais: os controles sairam do layout)

    # chip do cabecalho dos cartoes
    chip_h = 28
    retangulo((120, chip_h), chip_h // 2, CHIP_BG, CHIP_LINE, 1).save(MEDIA / "chip.png")

    # moldura do QR Code: retangulo branco de cantos RETOS.
    # Desenhada ja no tamanho em que vai aparecer (o `stretch` antigo pegava uma
    # placa de 80 px com raio e multiplicava o raio por 4 -> aquele canto
    # arredondado exagerado). 1 px de sobra branca em volta do QR.
    MOLDURA_QR = med.qr_plate
    retangulo((MOLDURA_QR, MOLDURA_QR), 0, rgba("#ffffff")).save(
        MEDIA / "qr_plate.png")

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

    # (os icones dos botoes sairam do layout: os botoes mostram so o texto)

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
              cor_foco=None, border=0, pad_x=0):
    """Botao da skin; `pad_x` empurra o texto (usado nos botoes com icone)."""
    el = ET.Element("control", {"type": "button", "id": str(cid)})
    for tag, valor in (("left", x), ("top", y), ("width", w), ("height", h)):
        ET.SubElement(el, tag).text = str(valor)
    if pad_x:
        # o <button> do Kodi centraliza o texto na area util: `margin` encolhe a
        # area a esquerda, empurrando o texto para longe do icone
        ET.SubElement(el, "margin").text = "0,0,0,%d" % pad_x
    # Centralizacao pedida no desenho (flex + align/justify center): declarada
    # no XML em vez de depender do padrao da skin, que pode variar.
    ET.SubElement(el, "align").text = "center"
    ET.SubElement(el, "aligny").text = "center"
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

    # --- topo: so a marca, alinhada a esquerda com respiro -----------------
    # (o seletor "Android TV / Celular" saiu: a tela e 16:9 fixa, o seletor nao
    #  levava a lugar nenhum e poluia o canto direito)
    logo = 64
    topo_y = med.pad + (med.top_h - logo) // 2
    controles.append(xml_imagem(10, med.pad, topo_y, logo, logo, "logo.png"))

    marca_x = med.pad + logo + 20      # respiro entre logo e nome
    h1 = med.fontes["h1"]
    sub = med.fontes["sub"]
    lh1, lsub = altura_linha(h1), altura_linha(sub)
    respiro_marca = 6
    bloco = lh1 + respiro_marca + lsub
    # alinha o bloco de duas linhas com o centro do logo (nada de 2 px tortos)
    bloco_y = topo_y + (logo - bloco) // 2
    controles.append(xml_label(11, marca_x, bloco_y, 460, lh1,
                               "SMARTEDTV", estilos["h1"], ink))
    controles.append(xml_label(12, marca_x, bloco_y + lh1 + respiro_marca, 460, lsub,
                               "Ativação e assinatura", estilos["sub"], mut))

    # --- grade dos cartoes -----------------------------------------------
    xs = [med.pad, med.pad + med.col_w + med.col_gap,
          med.pad + 2 * (med.col_w + med.col_gap)]
    for i, x in enumerate(xs):
        controles.append(xml_imagem(20 + i, x, med.grade_y, med.col_w, med.grade_h,
                                    "card.png", "stretch"))

    # Linha de base comum: TODAS as acoes primarias terminam na mesma altura,
    # com o mesmo respiro da borda de baixo do cartao.
    btn_h = med.btn_h
    cta_y = med.grade_y + med.grade_h - med.card_pad - btn_h
    topo = med.grade_y + med.card_pad          # topo util do conteudo do cartao
    interno = med.card_inner

    # cartao 1 — boas-vindas
    c1 = xs[0] + med.card_pad
    lh_eyebrow = altura_linha(med.fontes["eyebrow"])
    y = topo
    controles.append(xml_imagem(24, c1, y + lh_eyebrow // 2 - 1, 24, 2,
                                "eyebrow_line.png"))
    controles.append(xml_label(25, c1 + 24 + 12, y, interno - 36, lh_eyebrow,
                               "BEM-VINDO", estilos["eyebrow"], mut))
    y += lh_eyebrow + 24

    h3 = med.fontes["h3"]
    lh3 = altura_linha(h3)
    passo_h3 = round(h3 * 1.12)      # entrelinha do titulo (2 linhas)
    for i, linha in enumerate(("Sua TV,", "do seu jeito.")):
        controles.append(xml_label(26 + i, c1, y + i * passo_h3, interno, lh3,
                                   linha, estilos["h3"], ink))
    y += passo_h3 + lh3 + 18

    textos, altura_par = xml_texto(
        28, c1, y, interno,
        "Ative o VIP com um código ou continue gratuitamente com anúncios.",
        estilos["body"], med.fontes["body"], txt, entrelinha=1.42)
    controles.extend(textos)

    # beneficios: ancorados logo acima da acao, com respiro previsivel
    itens = ("Canais ao vivo, sem travar", "Sem anúncios com o VIP ativo",
             "Ativação em poucos segundos")
    li = med.fontes["li"]
    li_h = max(altura_linha(li) + 2, texturas["tick"] + 4)
    # O vazio entre o paragrafo e a acao e distribuido nos intervalos da lista
    # (limitado): a lista "respira" e o cartao nao fica com um buraco no meio.
    topo_lista = y + altura_par + 28
    fundo_lista = cta_y - 40
    livre = fundo_lista - topo_lista - len(itens) * li_h
    gap_item = int(clamp(18, livre / max(1, len(itens) - 1), 40))
    bloco_h = len(itens) * li_h + (len(itens) - 1) * gap_item
    lista_y = topo_lista + max(0, (fundo_lista - topo_lista - bloco_h) // 2)
    if lista_y < y + altura_par + 24:
        raise SystemExit("cartao 1 sem espaco para a lista (%d)" % lista_y)
    for i, item in enumerate(itens):
        ly = lista_y + i * (li_h + gap_item)
        controles.append(xml_imagem(30 + i, c1, ly + (li_h - texturas["tick"]) // 2,
                                    texturas["tick"], texturas["tick"], "tick.png"))
        controles.append(xml_label(34 + i, c1 + texturas["tick"] + 16,
                                   ly + (li_h - altura_linha(li)) // 2,
                                   interno - texturas["tick"] - 16,
                                   altura_linha(li), item, estilos["li"], txt))

    # acao principal do cartao 1 (largura cheia, como nos outros cartoes)
    pad_botao = 22
    texto_atualizar = "ATUALIZAR APLICATIVO"
    largura_txt = largura_texto(texto_atualizar, med.fontes["btn"])
    # Botao so com texto (sem icone): largura = texto + respiro dos dois lados.
    atualizar_w = round(largura_txt + 2 * pad_botao)
    atualizar_w = max(atualizar_w, round(interno * 0.72))
    atualizar_w = min(atualizar_w, interno)
    ax = c1 + (interno - atualizar_w) // 2
    controles.append(xml_botao(123, ax, cta_y, atualizar_w, btn_h,
                               texto_atualizar, estilos["btn"], ink,
                               "btn_ghost.png", "btn_ghost_focus.png",
                               cor_foco=escuro, border=med.raio_btn))

    # cabecalho de cartao com indicador opcional a direita
    lh2 = altura_linha(med.fontes["h2"])
    chip_h = med.fontes["chip"] + 16
    chip_pad = 14

    def cabecalho(cid, cx, titulo, chip=None, chip_id=None):
        controles.append(xml_label(cid, cx, topo, interno, lh2, titulo,
                                  estilos["h2"], ink))
        if not chip:
            return
        cw = round(largura_texto(chip, med.fontes["chip"]) + 2 * chip_pad)
        chip_x = cx + interno - cw
        chip_y = topo + (lh2 - chip_h) // 2        # centralizado com o titulo
        controles.append(xml_imagem(chip_id, chip_x, chip_y, cw, chip_h,
                                    "chip.png", "stretch"))
        controles.append(xml_label(chip_id + 1, chip_x,
                                   chip_y + (chip_h - altura_linha(med.fontes["chip"])) // 2,
                                   cw, altura_linha(med.fontes["chip"]), chip,
                                   estilos["chip"], txt, align="center"))

    # cartao 2 — assinatura (QR do checkout)
    x2, c2 = xs[1], xs[1] + med.card_pad
    cabecalho(40, c2, "Sem anúncios", "Plano mensal", 41)

    hint = med.fontes["hint"]
    lh_hint = altura_linha(hint)
    passo_hint = round(hint * 1.38)
    hint_h = passo_hint + lh_hint                  # duas linhas medidas
    dica2 = ("Aponte a câmera de outro celular.\n"
             "Valor e condições aparecem no checkout.")
    dica3 = ("Aponte a câmera e envie o link\ndo app a quem quiser.")

    # Cada cartao tem UMA linha de acoes na base (dois botoes lado a lado no
    # cartao 3). Assim os tres cartoes terminam na mesma altura, os dois QR
    # Codes ficam na mesma linha e nenhuma dica encosta em botao.
    gap_botoes = 12
    hint2_y = cta_y - 24 - hint_h                  # dica 2 logo acima da acao
    hint3_y = hint2_y                              # simetria entre os cartoes
    area_topo = topo + lh2 + 24                    # abaixo do cabecalho
    # QR no tamanho NORMAL (o mesmo em que o pacote entrega a imagem), sem
    # esticar nem ampliar. A moldura e so uma linha branca de 1 px em volta
    # (BORDA_QR), com cantos retos.
    BORDA_QR = 1
    livre = (hint2_y - 24) - area_topo
    qr_img = min(med.qr_img, interno, livre - 2 * BORDA_QR)
    qr_img -= qr_img % 2                           # par: centraliza sem .5 px
    if qr_img < 200:
        raise SystemExit("QR Code pequeno demais (%d)" % qr_img)
    prato = qr_img + 2 * BORDA_QR
    qr_off = BORDA_QR

    def qr(cid, cx, cartao_x, topo_livre, altura_livre, textura):
        py = topo_livre + (altura_livre - prato) // 2
        px = cartao_x + (med.col_w - prato) // 2
        controles.append(xml_imagem(cid, px, py, prato, prato, "qr_plate.png",
                                    "stretch"))
        controles.append(xml_imagem(cid + 1, px + qr_off, py + qr_off, qr_img,
                                    qr_img, textura, "keep"))

    qr(43, c2, x2, area_topo, livre, "qr_checkout.png")
    dicas, _ = xml_texto(45, c2, hint2_y, interno, dica2, estilos["hint"], hint,
                         mut, align="center", entrelinha=1.38)
    controles.extend(dicas)
    controles.append(xml_botao(120, c2, cta_y, interno, btn_h, "Abrir checkout",
                               estilos["btn"], ink, "btn_ghost.png",
                               "btn_ghost_focus.png", cor_foco=escuro,
                               border=med.raio_btn))

    x3, c3 = xs[2], xs[2] + med.card_pad
    cabecalho(50, c3, "Indique e ganhe")
    qr(53, c3, x3, area_topo, livre, "qr_apk.png")
    dicas3, _ = xml_texto(55, c3, hint3_y, interno, dica3, estilos["hint"], hint,
                          mut, align="center", entrelinha=1.38)
    controles.extend(dicas3)
    meia = (interno - gap_botoes) // 2
    controles.append(xml_botao(121, c3, cta_y, meia, btn_h, "Compartilhar link",
                               estilos["btn"], ink, "btn_ghost.png",
                               "btn_ghost_focus.png", cor_foco=escuro,
                               border=med.raio_btn))
    texto_baixar = "Baixar APK (Android)"
    baixar_w = interno - gap_botoes - meia
    bx3 = c3 + meia + gap_botoes
    baixar_y = cta_y
    controles.append(xml_botao(122, bx3, baixar_y, baixar_w, btn_h, texto_baixar,
                               estilos["btn"], ink, "btn_ghost.png",
                               "btn_ghost_focus.png", cor_foco=escuro,
                               border=med.raio_btn))

    # --- barra de ativacao VIP --------------------------------------------
    # Painel proprio, isolado da grade por um respiro fixo (med.gap). Dentro
    # dele, tudo fica na mesma linha de centro: texto, campo, Ativar e o link.
    barra_y = med.barra_y
    pad_barra = 28
    controles.append(xml_imagem(6, med.pad, barra_y, med.largura, med.barra_h,
                                "bar.png", "stretch"))
    bx0 = med.pad + pad_barra
    bdir = med.pad + med.largura - pad_barra        # borda util direita
    by = barra_y + (med.barra_h - btn_h) // 2       # centro vertical da barra

    barh3, barp = med.fontes["barh3"], med.fontes["barp"]
    lh_barh3, lh_barp = altura_linha(barh3), altura_linha(barp)
    respiro_copy = 6
    bloco_copy = lh_barh3 + respiro_copy + lh_barp
    copy_w = 400
    copy_y = barra_y + (med.barra_h - bloco_copy) // 2
    controles.append(xml_label(60, bx0, copy_y, copy_w, lh_barh3,
                               "Já é assinante? Ative seu VIP", estilos["barh3"], ink))
    controles.append(xml_label(61, bx0, copy_y + lh_barh3 + respiro_copy, copy_w,
                               lh_barp, "Digite o código que você recebeu.",
                               estilos["barp"], mut))

    pad_pill = 24
    # Botao secundario da barra: mesmo vidro/pill dos outros botoes (nao e mais
    # um texto solto), com a mesma altura do "Ativar" ao lado.
    gratis_txt = "Assistir com anúncios"
    gratis_w = round(largura_texto(gratis_txt, med.fontes["bar_btn"]) + 2 * pad_pill)
    gratis_x = bdir - gratis_w
    div_x = gratis_x - 28
    ativar_txt = "Ativar"
    ativar_w = round(largura_texto(ativar_txt, med.fontes["btn"]) + 2 * pad_pill)
    ativar_x = div_x - 28 - ativar_w
    field_x = bx0 + copy_w + 32
    field_w = ativar_x - 12 - field_x

    controles.append(xml_imagem(62, div_x, by + 2, 2, btn_h - 4, "divider.png",
                                "stretch"))
    controles.append(xml_botao(312, gratis_x, by, gratis_w, btn_h, gratis_txt,
                               estilos["bar_btn"], ink, "btn_ghost.png",
                               "btn_ghost_focus.png", cor_foco=escuro,
                               border=med.raio_btn))

    edit = ET.Element("control", {"type": "edit", "id": "310"})
    for tag, valor in (("left", field_x), ("top", by), ("width", field_w),
                       ("height", btn_h)):
        ET.SubElement(edit, tag).text = str(valor)
    ET.SubElement(edit, "label").text = "Código de ativação"
    ET.SubElement(edit, "font").text = estilos["field"]
    ET.SubElement(edit, "textcolor").text = "FFFFFFFF"
    ET.SubElement(edit, "disabledcolor").text = "FF747474"
    ET.SubElement(edit, "texturefocus", {"border": str(med.raio_btn)}).text = "field_focus.png"
    ET.SubElement(edit, "texturenofocus", {"border": str(med.raio_btn)}).text = "field.png"
    controles.append(edit)
    controles.append(xml_botao(311, ativar_x, by, ativar_w, btn_h, ativar_txt,
                               estilos["btn"], escuro, "btn_primary.png",
                               "btn_primary_focus.png", border=med.raio_btn))

    # --- legenda inferior -------------------------------------------------
    # legenda: abaixo da barra e acima da margem inferior; se nao couber, nao
    # desenha (melhor sem legenda do que legenda por cima do painel)
    legenda_h = altura_linha(11)
    legenda_y = med.barra_y + med.barra_h + 8
    if legenda_y + legenda_h > 1080 - med.pad:
        legenda_y = None      # `.legend` do CSS: -27px, fora da area util
    if legenda_y is not None:
        controles.append(xml_label(70, 0, legenda_y, 1920, legenda_h,
                                   "Android TV  ·  16:9  ·  tela única, sem rolagem  ·  setas/Enter navegam (D-pad)",
                                   estilos["legend"], "FF767676", align="center"))

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
    # o dialogo tem fundo proprio e fica POR CIMA da tela (z-order): fica opaco
    # o bastante para o QR nao "vazar" atras do texto
    grupo.append(xml_imagem(908, dialogo_x - 6, dialogo_y - 6, dialogo_w + 12,
                            dialogo_h + 12, "scrim.png", "stretch"))
    grupo.append(xml_imagem(902, dialogo_x, dialogo_y, dialogo_w, dialogo_h,
                            "dialog.png", "stretch"))
    grupo.append(xml_label(903, dialogo_x + 38, dialogo_y + 33, dialogo_w - 76,
                           altura_linha(med.fontes["h2"]),
                           "Continuar com anúncios?", estilos["h2"], ink))
    linhas_dialogo, altura_dialogo = xml_texto(
        910, dialogo_x + 38, dialogo_y + 83, dialogo_w - 76, corpo,
        estilos["field"], med.fontes["field"], txt, entrelinha=1.4)
    grupo.extend(linhas_dialogo)
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
    grupo2.append(xml_imagem(958, dialogo_x - 6, dialogo_y - 6, dialogo_w + 12,
                             dialogo_h + 12, "scrim.png", "stretch"))
    grupo2.append(xml_imagem(952, dialogo_x, dialogo_y, dialogo_w, dialogo_h,
                             "dialog.png", "stretch"))
    # Titulo e mensagem vem do servidor (podem ser longos): cada um vira uma
    # caixa de texto com quebra automatica do proprio Kodi, para nunca cortar
    # nem invadir o botao. `<textbox>` quebra linha e corta com "..." sozinho.
    titulo = ET.Element("control", {"type": "textbox", "id": "953"})
    for tag, valor in (("left", dialogo_x + 38), ("top", dialogo_y + 30),
                       ("width", dialogo_w - 76), ("height", 42)):
        ET.SubElement(titulo, tag).text = str(valor)
    ET.SubElement(titulo, "label").text = "$INFO[Window.Property(welcome_status_title)]"
    ET.SubElement(titulo, "font").text = estilos["h2"]
    ET.SubElement(titulo, "textcolor").text = ink
    grupo2.append(titulo)

    corpo_status = ET.Element("control", {"type": "textbox", "id": "954"})
    for tag, valor in (("left", dialogo_x + 38), ("top", dialogo_y + 82),
                       ("width", dialogo_w - 76), ("height", 104)):
        ET.SubElement(corpo_status, tag).text = str(valor)
    ET.SubElement(corpo_status, "label").text = "$INFO[Window.Property(welcome_status_text)]"
    ET.SubElement(corpo_status, "font").text = estilos["field"]
    ET.SubElement(corpo_status, "textcolor").text = txt
    grupo2.append(corpo_status)
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
