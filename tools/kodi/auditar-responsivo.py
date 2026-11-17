#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audita a tela de entrada nas resolucoes de TV sem abrir o Kodi.

O layout e um unico desenho de referencia 1920x1080 (``<coordinates><system>1``).
O Kodi escala coordenadas E fontes pelo fator da tela, portanto a proporcao se
mantem em 1280x720, 1920x1080 e 3840x2160. Este script confere exatamente isso
no XML entregue:

* nenhum controle sai da tela em nenhuma das tres resolucoes;
* os QR Codes continuam quadrados (largura == altura) e com ``keep``;
* o campo 310, Ativar (311) e Assistir com anuncios (312) continuam dentro da
  area visivel;
* os botoes nao ficam menores que 36 px de altura em 720p (alvo de D-pad);
* os dialogos 905/906/955 tem navegacao explicita nas quatro direcoes;
* as texturas de fundo cobrem a tela inteira.

Nao substitui um teste em aparelho: e a prova geometrica do XML que vai no APK.
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAYOUTS = (
    ROOT / 'kodi/addons/script.smartedtv.welcome/resources/skins/Default/1080i/DialogWelcome.xml',
    ROOT / 'kodi/addons/script.smartedtv.welcome/resources/skins/Default/1080i/DialogWelcomeTV.xml',
)
RESOLUCOES = ((1280, 720), (1920, 1080), (3840, 2160))
BASE = (1920.0, 1080.0)
ALTURA_MINIMA_BOTAO = 36.0


def caixa(no, base=(1920.0, 1080.0)):
    def num(tag):
        valor = (no.findtext(tag) or '').strip()
        if not valor:
            return None
        if valor.endswith('%'):
            ref = base[0] if tag in ('left', 'right', 'width') else base[1]
            return ref * float(valor[:-1]) / 100.0
        return float(valor)

    largura = num('width') or 0.0
    altura = num('height') or 0.0
    x = num('left')
    if x is None:
        direita = num('right')
        x = 0.0 if direita is None else base[0] - direita - largura
    y = num('top')
    if y is None:
        fundo = num('bottom')
        y = 0.0 if fundo is None else base[1] - fundo - altura
    return x, y, largura, altura


def controles(raiz):
    """(id, tipo, x, y, w, h, no) com o deslocamento dos grupos."""
    saida = []
    for grupo in raiz.iter('control'):
        if grupo.get('type') != 'group':
            continue
        gx, gy, _, _ = caixa(grupo)
        for filho in grupo.findall('control'):
            x, y, w, h = caixa(filho)
            saida.append((filho.get('id') or '-', filho.get('type') or '',
                          x + gx, y + gy, w, h, filho))
    for no in raiz.find('controls').findall('control'):
        if no.get('type') == 'group':
            continue
        x, y, w, h = caixa(no)
        saida.append((no.get('id') or '-', no.get('type') or '',
                      x, y, w, h, no))
    return saida


def auditar_layout(caminho, resolucoes=RESOLUCOES, falhas=None):
    falhas = falhas if falhas is not None else []
    raiz = ET.parse(caminho).getroot()
    nome = caminho.name
    itens = controles(raiz)

    for largura, altura in resolucoes:
        sx, sy = largura / BASE[0], altura / BASE[1]
        for ident, tipo, x, y, w, h, no in itens:
            if x < -0.5 or y < -0.5 or x + w > BASE[0] + 0.5 or y + h > BASE[1] + 0.5:
                falhas.append('%s %dx%d: controle %s fora do desenho (%s,%s,%s,%s)'
                              % (nome, largura, altura, ident, x, y, w, h))
            if tipo == 'button' and h * sy < ALTURA_MINIMA_BOTAO:
                falhas.append('%s %dx%d: botao %s com %.1f px de altura (< %.0f)'
                              % (nome, largura, altura, ident, h * sy,
                                 ALTURA_MINIMA_BOTAO))
            textura = (no.findtext('texture') or '').strip()
            if textura.startswith('qr_'):
                if abs(w - h) > 0.5:
                    falhas.append('%s: %s nao e quadrado (%sx%s)'
                                  % (nome, ident, w, h))
                if (no.findtext('aspectratio') or '').strip() != 'keep':
                    falhas.append('%s: %s sem aspectratio keep' % (nome, ident))

    for ident in ('310', '311', '312'):
        achado = [i for i in itens if i[0] == ident]
        if not achado:
            falhas.append('%s: controle obrigatorio %s ausente' % (nome, ident))
            continue
        x, y, w, h = achado[0][2:6]
        if x < 0 or y < 0 or x + w > BASE[0] or y + h > BASE[1]:
            falhas.append('%s: %s fora da area visivel' % (nome, ident))

    for ident in ('905', '906', '955'):
        achado = [i for i in itens if i[0] == ident]
        if not achado:
            falhas.append('%s: botao de dialogo %s ausente' % (nome, ident))
            continue
        no = achado[0][6]
        for tag in ('onleft', 'onright', 'onup', 'ondown'):
            if not (no.findtext(tag) or '').strip():
                falhas.append('%s: %s sem %s' % (nome, ident, tag))

    # A barra do codigo nao pode ficar por cima dos tres cartoes (isso
    # escondia a borda dos botoes 123/120/121/122).
    barra = [i for i in itens if i[0] == '6']
    cartoes = [i for i in itens if i[0] in ('20', '21', '22')]
    if barra and cartoes:
        _, _, bx, by, bw, bh, _ = barra[0]
        for ident, _, cx, cy, cw, ch, _ in cartoes:
            if by < cy + ch - 0.5 and cy < by + bh - 0.5 and \
                    bx < cx + cw - 0.5 and cx < bx + bw - 0.5:
                falhas.append('%s: barra 6 sobrepoe o cartao %s'
                              % (nome, ident))

    fundo = [i for i in itens if i[0] == '1']
    if fundo:
        x, y, w, h = fundo[0][2:6]
        if not (x <= 0.5 and y <= 0.5 and w >= BASE[0] - 0.5 and h >= BASE[1] - 0.5):
            falhas.append('%s: fundo nao cobre 1920x1080' % nome)

    return falhas, len(itens)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--falhar', action='store_true')
    args = parser.parse_args(argv)
    falhas, total = [], 0
    for caminho in LAYOUTS:
        if not caminho.is_file():
            falhas.append('layout ausente: %s' % caminho)
            continue
        _, quantidade = auditar_layout(caminho, falhas=falhas)
        total += quantidade
    print('Auditoria responsiva: %d layouts, %d controles, resolucoes %s'
          % (len(LAYOUTS), total,
             ', '.join('%dx%d' % r for r in RESOLUCOES)))
    for falha in falhas:
        print('  FALHA  %s' % falha)
    if not falhas:
        print('  OK: 720p/1080p/4K sem corte, QR quadrado e botoes >= %.0f px'
              % ALTURA_MINIMA_BOTAO)
    return 1 if (falhas and args.falhar) else 0


if __name__ == '__main__':
    sys.exit(main())
