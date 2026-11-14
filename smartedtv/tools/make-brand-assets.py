#!/usr/bin/env python3
"""Gera os recursos de identidade SMARTEDTV a partir das artes oficiais da marca.

Entradas (obrigatórias — nunca inventadas nem redesenhadas):
  assets/brand/logo-oficial.jpg  Arte oficial 1600x1600 "S SMARTED-TV": campo preto puro,
                                 barra branca horizontal e selo circular com o monograma S.
                                 Origem: assets/brand/source/splash.jpg (material do Dropbox).
  assets/brand/mark.png          Recorte quadrado do selo (círculo + barra), recortado da arte
                                 oficial para uso em ícones pequenos.
  assets/brand/splash.png        Arte widescreen da abertura (16:9). Quando existe, ela é a
                                 tela de abertura do Android e da GUI: preenche o quadro
                                 inteiro, sem barras pretas. Sem ela, cai na arte quadrada.

Saídas (todas as medidas que o Kodi 21.3 lê no Android e na GUI):
  out/media/splash.jpg                   1920x1080  splash da GUI (special://xbmc/media/splash.jpg)
  out/media/applaunch_screen.png         1920x1080  splash nativo do Android (res/drawable/applaunch_screen)
  out/media/banner.png                    320x180   banner Android TV
  out/media/icon{256,120,80,48,32,16}.png           ícones internos do Kodi
  out/media/vendor_icon.png               128x128   ícone de fornecedor da skin
  out/media/vendor_logo.png               465x128   marca exibida na Home/Login da Estuary
  out/android-packaging-media/drawable-*/ic_launcher.png   launcher (36/48/72/96/144/192)
  out/android-packaging-media/drawable-xhdpi/banner.png

Decisão de design: em nenhum momento a arte é redesenhada. A barra branca horizontal
faz parte do lockup oficial, então o selo é usado completo (com a barra) e o fundo é
preto puro, exatamente o campo da arte original. Isso evita emendas e mantém a marca.

O script é determinístico: a mesma entrada gera os mesmos bytes.
"""
from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    print("Pillow não instalado. Rode: python3 -m pip install Pillow==11.3.0",
          file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "assets" / "brand"
OUT_MEDIA = ROOT / "out" / "media"
OUT_PACKAGING = ROOT / "out" / "android-packaging-media"

BLACK = (0, 0, 0)
LAUNCHER_SIZES = {"ldpi": 36, "mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}


def open_rgb(path: Path) -> Image.Image:
    if not path.is_file():
        raise SystemExit(f"Arte oficial ausente: {path}")
    return Image.open(path).convert("RGB")


def letterbox(art: Image.Image, width: int, height: int, scale: float) -> Image.Image:
    """Coloca a arte oficial sobre campo preto puro, sem cortar nada."""
    canvas = Image.new("RGB", (width, height), BLACK)
    side = int(min(width, height) * scale)
    scaled = art.resize((side, side), Image.LANCZOS)
    canvas.paste(scaled, ((width - side) // 2, (height - side) // 2))
    return canvas


def cover(art: Image.Image, width: int, height: int) -> Image.Image:
    """Preenche o quadro sem sobras: a arte widescreen vira a tela cheia."""
    alvo = width / height
    w, h = art.size
    if w / h > alvo:                       # mais larga que 16:9: corta as laterais
        nova_w = int(round(h * alvo))
        x = (w - nova_w) // 2
        recorte = (x, 0, x + nova_w, h)
    else:                                  # mais alta: corta em cima e embaixo
        nova_h = int(round(w / alvo))
        y = (h - nova_h) // 2
        recorte = (0, y, w, y + nova_h)
    return art.crop(recorte).resize((width, height), Image.LANCZOS)


def circle_mark(mark: Image.Image, size: int, pad_ratio: float = 0.0) -> Image.Image:
    """Ícone quadrado a partir do selo oficial; a barra do lockup é preservada."""
    canvas = Image.new("RGB", (size, size), BLACK)
    pad = int(size * pad_ratio)
    target = size - 2 * pad
    canvas.paste(mark.resize((target, target), Image.LANCZOS), ((size - target) // 2,) * 2)
    return canvas


def vendor_logo(mark: Image.Image, width: int, height: int) -> Image.Image:
    """Marca da Home da Estuary: selo oficial com transparência nas laterais."""
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    target = int(height * 0.98)
    canvas.paste(mark.resize((target, target), Image.LANCZOS), ((width - target) // 2, (height - target) // 2))
    return canvas


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def save_jpg(image: Image.Image, path: Path, quality: int = 95) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, format="JPEG", quality=quality, optimize=True)


def main() -> int:
    art = open_rgb(BRAND / "logo-oficial.jpg")
    mark = open_rgb(BRAND / "mark.png")

    # Tela de abertura: a arte widescreen manda; sem ela, a quadrada é emoldurada.
    splash_file = BRAND / "splash.png"
    if splash_file.is_file():
        splash = open_rgb(splash_file)

        def tela(width: int, height: int) -> Image.Image:
            return cover(splash, width, height)
    else:
        def tela(width: int, height: int) -> Image.Image:
            return letterbox(art, width, height, 1.0)

    # Splash GUI (1920x1080 JPG) e splash nativo Android (1920x1080 PNG)
    save_jpg(tela(1920, 1080), OUT_MEDIA / "splash.jpg")
    save_png(tela(1920, 1080), OUT_MEDIA / "applaunch_screen.png")

    # Banner Android TV (320x180) e ícones internos
    save_png(tela(320, 180), OUT_MEDIA / "banner.png")
    for size in (256, 120, 80, 48, 32, 16):
        save_png(circle_mark(mark, size), OUT_MEDIA / f"icon{size}x{size}.png")
    save_png(circle_mark(mark, 128), OUT_MEDIA / "vendor_icon.png")
    save_png(vendor_logo(mark, 465, 128), OUT_MEDIA / "vendor_logo.png")

    # Launcher Android em todas as densidades copiadas pelo packaging do Kodi
    for density, size in LAUNCHER_SIZES.items():
        save_png(circle_mark(mark, size, pad_ratio=0.02),
                 OUT_PACKAGING / f"drawable-{density}" / "ic_launcher.png")
    save_png(tela(320, 180), OUT_PACKAGING / "drawable-xhdpi" / "banner.png")

    print(f"Identidade SMARTEDTV gerada em {OUT_MEDIA} e {OUT_PACKAGING}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
