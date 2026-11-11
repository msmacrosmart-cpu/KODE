#!/usr/bin/env python3
"""Gera os ícones de Ajustes da skin Brazuka Play (glifos brancos 256x256).

Os ícones seguem o mesmo padrão dos que já existiam em
``media/icons/settings`` (glifo branco sobre fundo transparente, 256x256),
para que nenhuma opção de Ajustes fique sem ícone no Kodi.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "kodi" / "skin.estilo.personalizado" / "media" / "icons" / "settings"
SIZE = 1024          # desenha grande e reduz (antialias)
FINAL = 256
COLOR = (255, 255, 255, 255)


def canvas():
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return image, ImageDraw.Draw(image)


def fit(image, target=SIZE, margin=0.08):
    """Recorta o glifo e centraliza ocupando ~(1-2*margin) do quadro."""
    bbox = image.split()[-1].getbbox()
    if not bbox:
        return image
    image = image.crop(bbox)
    side = int(max(image.size) / (1 - 2 * margin))
    canvas_img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas_img.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    return canvas_img.resize((target, target), Image.LANCZOS)


def save(image, name):
    image = fit(image)
    image = image.resize((FINAL, FINAL), Image.LANCZOS)
    TARGET.mkdir(parents=True, exist_ok=True)
    image.save(TARGET / name, optimize=True)
    print("gerado", TARGET / name)


def video():
    """Play dentro de um retângulo arredondado (Vídeo)."""
    img, d = canvas()
    d.rounded_rectangle([90, 190, 934, 834], radius=90, outline=COLOR, width=44)
    d.polygon([(430, 380), (430, 644), (660, 512)], fill=COLOR)
    save(img, "video.png")


def music():
    """Nota musical (Música)."""
    img, d = canvas()
    d.rectangle([600, 170, 656, 660], fill=COLOR)
    d.rectangle([600, 170, 860, 226], fill=COLOR)
    d.ellipse([470, 600, 660, 760], fill=COLOR)
    d.ellipse([730, 540, 900, 690], fill=COLOR)
    d.rectangle([600, 560, 830, 660], fill=COLOR)
    save(img, "music.png")


def photos():
    """Montanha + sol dentro de moldura (Fotos)."""
    img, d = canvas()
    d.rounded_rectangle([100, 190, 924, 834], radius=70, outline=COLOR, width=44)
    d.ellipse([230, 300, 380, 450], fill=COLOR)
    d.polygon([(150, 790), (420, 470), (620, 720), (740, 590), (880, 790)], fill=COLOR)
    save(img, "photos.png")


def appearance():
    """Paleta de pintura (Aparência)."""
    img, d = canvas()
    d.ellipse([110, 190, 850, 830], outline=COLOR, width=44)
    for x, y in ((300, 380), (470, 320), (650, 400)):
        d.ellipse([x - 46, y - 46, x + 46, y + 46], fill=COLOR)
    d.ellipse([420, 560, 640, 780], outline=COLOR, width=36)
    save(img, "appearance.png")


def energy():
    """Power (Energia)."""
    img, d = canvas()
    d.arc([170, 190, 854, 874], start=118, end=242, fill=COLOR, width=56)
    d.rectangle([488, 130, 536, 560], fill=COLOR)
    save(img, "energy.png")


def diagnostics():
    """Chave inglesa (Diagnóstico)."""
    img, d = canvas()
    d.ellipse([300, 150, 720, 570], outline=COLOR, width=52)
    d.polygon([(600, 430), (760, 590), (900, 850), (800, 900), (640, 640), (520, 520)], fill=COLOR)
    save(img, "diagnostics.png")


def main():
    video()
    music()
    photos()
    appearance()
    energy()
    diagnostics()


if __name__ == "__main__":
    main()
