#!/usr/bin/env python3
"""Aplica a identidade SMARTED-TV a uma árvore decodificada pelo Apktool."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
WHITE, BG, GRAY = (245,245,245), (14,14,14), (144,144,144)

def icon(size):
    scale = 4
    im = Image.new('RGB', (size * scale, size * scale), BG)
    d = ImageDraw.Draw(im)
    w = size * scale
    # Anel quadrado e um S geométrico em negativo: legível também em tamanho pequeno.
    d.rounded_rectangle((w*.08,w*.08,w*.92,w*.92), radius=int(w*.18), outline=WHITE, width=max(2,int(w*.035)))
    pts = [(0.72,0.27),(0.39,0.27),(0.28,0.38),(0.28,0.48),(0.39,0.57),(0.61,0.57),(0.61,0.65),(0.30,0.65),(0.30,0.74),(0.64,0.74),(0.73,0.65),(0.73,0.55),(0.63,0.47),(0.40,0.47),(0.40,0.37),(0.72,0.37)]
    d.polygon([(int(x*w),int(y*w)) for x,y in pts], fill=WHITE)
    return im.resize((size,size), Image.Resampling.LANCZOS)

def poster(size, transparent=False):
    w,h=size
    im=Image.new('RGBA',size,(0,0,0,0) if transparent else BG+(255,))
    d=ImageDraw.Draw(im)
    mark_size=int(min(h*.50,w*.22))
    word_size=max(8,int(min(h*.20, w*.115)))
    font=ImageFont.truetype(FONT,word_size)
    label='SMARTED-TV'
    box=d.textbbox((0,0),label,font=font)
    text_width=box[2]-box[0]
    # Arranjo horizontal para banner e vendor logo, vertical para splash.
    if w/h < 2.5:
        mark_size=int(min(h*.40,w*.18)); total=text_width
        if total>w*.85:
            font=ImageFont.truetype(FONT,max(8,int(word_size*w*.85/total)))
            box=d.textbbox((0,0),label,font=font); text_width=box[2]-box[0]
        x=(w-mark_size)//2; y=int(h*.23)
        im.paste(icon(mark_size).convert('RGBA'),(x,y))
        d.text(((w-text_width)/2,h*.70-(box[3]-box[1])/2-box[1]),label,font=font,fill=WHITE+(255,))
    else:
        max_text=w*.65
        if text_width>max_text:
            font=ImageFont.truetype(FONT,max(8,int(word_size*max_text/text_width)))
            box=d.textbbox((0,0),label,font=font); text_width=box[2]-box[0]
        gap=int(h*.13); total=mark_size+gap+text_width
        x=int((w-total)/2); y=(h-mark_size)//2
        im.paste(icon(mark_size).convert('RGBA'),(x,y))
        d.text((x+mark_size+gap,(h-(box[3]-box[1]))/2-box[1]),label,font=font,fill=WHITE+(255,))
    return im

def main():
    p=argparse.ArgumentParser();p.add_argument('decoded',type=Path);args=p.parse_args(); root=args.decoded
    values=root/'res/values/strings.xml'
    text=values.read_text(encoding='utf-8')
    for name in ('app_name','search_hint'):
        old=f'<string name="{name}">Kodi</string>'
        if old not in text: raise ValueError(f'Valor esperado ausente: {name}')
        text=text.replace(old,f'<string name="{name}">SMARTED-TV</string>')
    values.write_text(text,encoding='utf-8')
    for path in sorted((root/'res').glob('drawable-*/ic_launcher.png')):
        size=Image.open(path).size
        if size[0]!=size[1]: raise ValueError(f'Ícone inesperado: {path}')
        icon(size[0]).save(path)
    media=root/'assets/media'
    for path in sorted(media.glob('icon*x*.png')) + [media/'vendor_icon.png']:
        size=Image.open(path).size
        if size[0]!=size[1]: raise ValueError(f'Ícone inesperado: {path}')
        icon(size[0]).save(path)
    for path in [root/'res/drawable-xhdpi/banner.png',media/'banner.png',media/'vendor_logo.png',root/'res/drawable/applaunch_screen.png',root/'res/drawable-xxxhdpi/applaunch_screen.png',media/'applaunch_screen.png',media/'splash.jpg']:
        with Image.open(path) as original: size=original.size
        im=poster(size,transparent=path.name=='vendor_logo.png')
        if path.suffix.lower()=='.jpg': im.convert('RGB').save(path,quality=95)
        else: im.save(path)
    yml=root/'apktool.yml'; y=yml.read_text();
    if 'versionCode: 2103000' not in y or 'versionName: 21.3' not in y: raise ValueError('Versão inesperada')
    y=y.replace('versionCode: 2103000','versionCode: 2103001').replace('versionName: 21.3','versionName: 1.0.15')
    yml.write_text(y)
    palette=root/'assets/addons/skin.estuary/colors/defaults.xml'; palette.write_bytes((Path(__file__).resolve().parents[2]/'kodi/skin/defaults.xml').read_bytes())
    for path in (root/'assets/addons/skin.estuary/extras/home-images').glob('*.jpg'):
        with Image.open(path) as original: im=original.convert('L').convert('RGB')
        im.save(path,quality=95)
    print('SMARTED-TV: identidade, paleta e versionCode aplicados')
if __name__=='__main__': main()
