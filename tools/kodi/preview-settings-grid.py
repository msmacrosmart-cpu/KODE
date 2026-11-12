#!/usr/bin/env python3
"""Prévia offline da grade de Ajustes (não é screenshot do Kodi).

Lê ``Settings.xml`` + o include ``SettingsTile`` e desenha a tela usando as
mesmas coordenadas/âncoras da skin, para conferir visualmente que nada é
cortado em 1920x1080 (16:9) e em 2400x1080 (20:9, o canvas real do aparelho).

Uso: python3 tools/kodi/preview-settings-grid.py [SAIDA.png] [--width 2400]
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SKIN = ROOT / 'kodi' / 'skin.estilo.personalizado'
XML = SKIN / 'xml'

BG = (14, 14, 14)
CARD = (30, 30, 30)
FOCUS = (245, 245, 245)
WHITE = (255, 255, 255)
DARK = (12, 12, 12)
MUTED = (150, 150, 150)

FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')


def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    path = FONT_DIR / name
    return ImageFont.truetype(str(path), size) if path.is_file() else ImageFont.load_default()


def num(node, tag, default=None):
    value = node.findtext(tag)
    return int(value) if value and value.isdigit() else default


def tile_geometry():
    includes = ET.parse(XML / 'Includes.xml').getroot()
    tile = includes.find(".//include[@name='SettingsTile']")
    layout = tile.find('itemlayout')
    return int(layout.get('width')), int(layout.get('height'))


def icon_image(rel, size, tint=WHITE):
    path = SKIN / 'media' / rel
    if not path.is_file():
        return Image.new('RGBA', (size, size), (0, 0, 0, 0))
    glyph = Image.open(path).convert('RGBA')
    alpha = glyph.getchannel('A').resize((size, size), Image.LANCZOS)
    out = Image.new('RGBA', (size, size), tint +(0,))
    out.putalpha(alpha)
    return out


def wrapped(draw, text, fnt, max_width):
    words, lines, current = text.split(), [], ''
    for word in words:
        candidate = (current + ' ' + word).strip()
        if draw.textlength(candidate, font=fnt) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render(width=2400, height=1080, out_path=None, focus_index=4):
    window = ET.parse(XML / 'Settings.xml').getroot()
    panel = window.find(".//control[@id='9000']")
    left = num(panel, 'left', 60)
    top = num(panel, 'top', 148)
    right = num(panel, 'right', 60)
    bottom = num(panel, 'bottom', 40)
    gap = num(panel, 'itemgap', 18)
    tile_w, tile_h = tile_geometry()

    panel_w = width - left - right
    panel_h = height - top - bottom
    columns = max(1, (panel_w + gap) // (tile_w + gap))

    items = [(i.findtext('label') or '', i.findtext('icon') or '')
             for i in panel.findall('./content/item')]

    image = Image.new('RGB', (width, height), BG)
    draw = ImageDraw.Draw(image)

    # cabeçalho
    def pill(x, y, w, h, text, filled=False):
        draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2,
                               fill=CARD if not filled else WHITE)
        fnt = font(24, bold=True)
        tw = draw.textlength(text, font=fnt)
        draw.text((x + (w - tw) / 2, y + h / 2), text, font=fnt,
                  fill=WHITE if not filled else DARK, anchor='lm')

    pill(60, 40, 150, 52, 'Voltar')
    draw.text((240, 66), 'AJUSTES', font=font(34, bold=True), fill=WHITE, anchor='lm')
    pill(width - 60 - 180, 40, 180, 52, 'Buscar')

    divider_y = 108
    for control in window.iter('control'):
        if control.get('type') == 'image' and num(control, 'top') == 108:
            divider_y = 108
            break
    draw.line([(60, divider_y), (width - 60, divider_y)], fill=(48, 48, 48))

    label_font = font(22)
    for index, (text, icon) in enumerate(items):
        row, column = divmod(index, columns)
        x = left + column * (tile_w + gap)
        y = top + row * (tile_h + gap)
        focused = index == focus_index
        draw.rounded_rectangle([x, y, x + tile_w, y + tile_h], radius=18,
                               fill=FOCUS if focused else CARD)
        glyph = icon_image(icon, 76, tint=DARK if focused else WHITE)
        image.paste(glyph, (x + (tile_w - 76) // 2, y + 22), glyph)
        lines = wrapped(draw, text, label_font, tile_w - 28)[:2]
        total = len(lines) * 26
        ty = y + 108 + max(0, (52 - total) // 2)
        for line in lines:
            draw.text((x + tile_w / 2, ty), line, font=label_font,
                      fill=DARK if focused else WHITE, anchor='ma')
            ty += 26

    meta = 'previa offline: %dx%d, %d colunas x %d linhas, tile %dx%d' % (
        width, height, columns, (len(items) + columns - 1) // columns, tile_w, tile_h)
    draw.text((60, height - 18), meta, font=font(16), fill=MUTED, anchor='lb')

    out_path = Path(out_path or (ROOT / 'docs' / ('preview-ajustes-%dx%d.png' % (width, height))))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)
    return out_path, meta


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    width = 2400
    if '--width' in sys.argv:
        width = int(sys.argv[sys.argv.index('--width') + 1])
    for w in ([width] if '--width' in sys.argv else [1920, 2400]):
        path, meta = render(width=w, out_path=args[0] if args else None)
        print(path, '|', meta)
