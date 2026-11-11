#!/usr/bin/env python3
"""Desenha a Home (layout Aurora) a partir do XML da skin, para conferir
geometria sem abrir o Kodi: sobreposição, cortes e o que exige rolagem.

Uso: python3 tools/kodi/preview-home-layout.py [saida.png]
Gera PNGs em docs/ (1920x1080 e 2400x1080) e imprime um relatório.
"""
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    raise SystemExit('Pillow ausente: pip install --break-system-packages pillow')

ROOT = Path(__file__).resolve().parents[2]
XML = ROOT / 'kodi/skin.estilo.personalizado/xml/Home.xml'
AURORA = ('!Skin.String(home_layout,blade)', '!Skin.String(home_layout,top10)',
          '!Skin.String(home_layout,sports)')
ROTULOS = {'9200': 'TV ao vivo', '9201': 'Filmes (LANÇAMENTOS)', '9202': 'Séries',
           '9203': 'Séries recentes', '9204': 'Filmes — biblioteca', '9205': 'Séries — biblioteca',
           '9300': 'hero: Assistir / Trailer / Info'}


def num(elemento, tag, padrao=0):
    valor = elemento.findtext(tag)
    if not valor:
        return padrao
    valor = valor.strip().rstrip('%')
    try:
        return int(valor)
    except ValueError:
        return padrao


def aurora_controls(root):
    """Controles do bloco Aurora (o layout ativo), na ordem do arquivo."""
    for grupo in root.iter('control'):
        if grupo.get('type') != 'group':
            continue
        vis = grupo.findtext('visible') or ''
        if grupo.find('animation') is None and 'home_layout' not in vis:
            continue
    alvo = None
    for grupo in root.iter('control'):
        if grupo.get('type') == 'group' and grupo.find('animation') is not None:
            alvo = grupo
            break
    return alvo


def desenhar(grupo, largura, saida):
    escala = largura / 1920.0
    altura = int(1080 * escala)
    imagem = Image.new('RGB', (largura, altura), (12, 12, 12))
    pincel = ImageDraw.Draw(imagem)
    rolagem = {}

    def caixa(controle, cor, rotulo):
        top = num(controle, 'top', -1)
        if top < 0:
            return
        esq = num(controle, 'left', 60)
        altura_c = num(controle, 'height', 40)
        largura_c = num(controle, 'width', 1800)
        x0, y0 = esq * escala, top * escala
        x1, y1 = (esq + largura_c) * escala, (top + altura_c) * escala
        pincel.rectangle([x0, y0, x1, y1], outline=cor, width=2)
        if rotulo:
            pincel.text((x0 + 6, y0 + 4), rotulo, fill=cor)

    for controle in grupo.iter('control'):
        cid = controle.get('id')
        tipo = controle.get('type')
        if cid in ('9300', '9301', '9302', '9303'):
            caixa(controle, (240, 200, 90), ROTULOS.get(cid, '') if cid == '9300' else '')
        elif tipo == 'list' and cid in ROTULOS:
            caixa(controle, (120, 200, 255), ROTULOS[cid])
            rolagem[cid] = num(controle, 'top', 0) + num(controle, 'height', 0)
    for cid, topo in sorted(rolagem.items()):
        if topo > 1080:
            pincel.text((20, altura - 26), 'precisa de rolagem: ' + ', '.join(
                c for c, t in sorted(rolagem.items()) if t > 1080), fill=(255, 120, 120))
            break
    pincel.text((20, 8), 'Home Aurora — %dx%d (escala %.2f)' % (largura, altura, escala), fill=(230, 230, 230))
    imagem.save(saida)
    return rolagem


def main(argv):
    saida = Path(argv[1]) if len(argv) > 1 else ROOT / 'docs/preview-home-1920.png'
    root = ET.parse(XML).getroot()
    grupo = aurora_controls(root)
    if grupo is None:
        raise SystemExit('grupo Aurora (com animações) não encontrado em Home.xml')
    saida.parent.mkdir(parents=True, exist_ok=True)
    medidas = desenhar(grupo, 1920, saida)
    alternativa = saida.with_name(saida.stem.replace('1920', '2400') + saida.suffix)
    desenhar(grupo, 2400, alternativa)
    print('desenho salvo: %s e %s' % (saida, alternativa))
    fora = {c: t for c, t in medidas.items() if t > 1080}
    print('linhas que exigem rolagem:', ', '.join(sorted(fora)) or 'nenhuma')
    # sobreposição entre linhas
    ordenadas = sorted(medidas.items(), key=lambda par: par[1])
    anterior = None
    for cid, fim in ordenadas:
        if anterior and fim - 150 < anterior[1]:
            print('ATENÇÃO: %s pode sobrepor %s' % (cid, anterior[0]))
        anterior = (cid, fim)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
