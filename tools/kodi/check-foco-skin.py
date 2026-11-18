#!/usr/bin/env python3
"""Audita a navegacao por d-pad de uma janela de skin.

O d-pad do Kodi segue duas regras (xbmc 21.2-Omega):

* ``CGUIBaseContainer::OnUp/OnDown`` tenta primeiro mover DENTRO do container
  (``MoveUp``/``MoveDown``); se nao houver item naquela direcao cai para
  ``CGUIControl::Navigate``, que usa o ``<onup>/<ondown>/<onleft>/<onright>``
  do controle e, sem eles, a posicao geometrica na tela.
* ``CGUIWindow::OnMove`` recusa focar um controle que ja esta no caminho
  (``moveHistory``): ``<onup>`` apontando para o proprio controle nao anda.

Logo, um controle "travado" (o que o cliente relata como "o d-pad nao funciona")
e aquele em que, com o container no limite, nenhuma direcao leva a outro
controle focavel. Este script monta o grafo e aponta:

* ``SEM SAIDA``  -> controle focavel sem nenhuma seta/geometria para outro;
* ``INALCANCAVEL`` -> controle focavel que nenhum caminho alcanca a partir do
  ``<defaultcontrol>`` (a barra inferior/ajustes fica inacessivel assim).
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

# Só estes tipos recebem foco pelo d-pad. 'image', 'label' e 'group' só
# entram no grafo quando declaram navegação própria (imagefocus etc.), então
# ficam de fora para não gerar "SEM SAIDA" falso em fundo/decoracao.
FOCAVEIS = {'button', 'radiobutton', 'togglebutton', 'spincontrol', 'list',
            'panel', 'grouplist', 'fixedlist', 'wraplist', 'textbox', 'edit',
            'slider', 'mover', 'colorbutton'}
# tipos que RECEBEM foco e se movem por dentro (container)
CONTAINERS = {'list', 'panel', 'grouplist', 'fixedlist', 'wraplist'}
DIRECOES = ('up', 'down', 'left', 'right')
TAGS_NAV = {'onup': 'up', 'ondown': 'down', 'onleft': 'left', 'onright': 'right'}


def _num(texto):
    try:
        return int(str(texto).strip())
    except (TypeError, ValueError):
        return 0


def _nav(controle):
    """{direcao: [ids]} das setas declaradas (varias por condicao)."""
    mapa = {d: [] for d in DIRECOES}
    for filho in controle:
        if filho.tag in TAGS_NAV and filho.text:
            alvo = _num(filho.text)
            if alvo:
                mapa[TAGS_NAV[filho.tag]].append(alvo)
    return mapa


def controles(elem, dentro_de=None):
    """(id, tipo, pai, elemento) de todo controle com id."""
    achados = []
    for filho in elem:
        if filho.tag == 'control':
            ident = filho.get('id')
            tipo = (filho.tag == 'control' and (filho.get('type') or '').strip()) or ''
            if tipo in FOCAVEIS and ident:
                achados.append((str(ident), tipo, dentro_de and str(dentro_de), filho))
            elif tipo in CONTAINERS:
                # container sem id (grupo) ainda tem filhos focaveis
                pass
            achados.extend(controles(filho, filho.get('id') or dentro_de))
        elif filho.tag in ('itemlayout', 'focusedlayout', 'content'):
            # layouts e itens de panel/grouplist nao participam do grafo de foco
            continue
        elif filho.tag == 'control' and (filho.get('type') or '') not in FOCAVEIS:
            continue
        elif filho.tag == 'include':
            achados.extend(controles_expandidos(filho))
        else:
            achados.extend(controles(filho, dentro_de))
    return achados


INCLUDES = {}


def carrega_includes(caminho):
    """Le Includes.xml da mesma pasta da skin (define <itemlayout> reutilizado)."""
    INCLUDES.clear()
    pasta = os.path.dirname(os.path.abspath(caminho))
    arquivo = os.path.join(pasta, 'Includes.xml')
    if not os.path.isfile(arquivo):
        return
    try:
        raiz = ET.parse(arquivo).getroot()
    except ET.ParseError:
        return
    for include in raiz.findall('include'):
        nome = include.get('name')
        if nome:
            INCLUDES[nome] = include


def controles_expandidos(include_tag):
    """Controles do <include> referenciado (so os que tem id proprio)."""
    alvo = (include_tag.text or '').strip()
    achados = []
    define = INCLUDES.get(alvo)
    if define is not None:
        achados.extend(controles(define))
        return achados
    padrao = include_tag.get('content')
    if padrao:
        achados.extend(controles(include_tag))
    return achados


def vistas(raiz):
    """Ids declarados em <views>: trocar de vista nao passa pelo d-pad."""
    alvo = raiz.find('views')
    if alvo is None or not (alvo.text or '').strip():
        return set()
    return {parte.strip() for parte in alvo.text.split(',') if parte.strip()}


def audita(caminho, defaultcontrol=None):
    carrega_includes(caminho)
    raiz = ET.parse(caminho).getroot()
    padrao = defaultcontrol
    for filho in raiz:
        if filho.tag == 'defaultcontrol' and filho.text:
            padrao = _num(filho.text)
    vistos = {}
    for ident, tipo, pai, elem in controles(raiz):
        # controle dentro de grouplist/panel e item do container: nao e no do grafo
        if pai and vistos.get(pai, ('', ''))[0] in ('grouplist', 'panel', 'list'):
            continue
        vistos[ident] = (tipo, pai, elem)
    arestas = {}
    for ident, (tipo, pai, elem) in vistos.items():
        nav = _nav(elem)
        destinos = set()
        for direcao in DIRECOES:
            # ids sao strings no grafo: comparar int com str marcava como
            # INALCANCAVEL um controle que qualquer seta ja alcancava.
            destinos.update(str(alvo) for alvo in nav[direcao] if str(alvo) != ident)
        if tipo in CONTAINERS:
            # movimento por dentro do container: sempre existe (nao e beco sem saida,
            # mas tambem nao basta: precisa de uma seta para SAIR no limite)
            pass
        arestas[ident] = destinos
    # alcance a partir do defaultcontrol
    alcancados = set()
    fila = ([str(padrao)] if padrao else []) + sorted(vistas(raiz))
    while fila:
        atual = fila.pop()
        if atual in alcancados:
            continue
        alcancados.add(atual)
        fila.extend(a for a in arestas.get(atual, ()) if a not in alcancados)
    problemas = []
    for ident, (tipo, pai, elem) in sorted(vistos.items()):
        if not arestas.get(ident):
            problemas.append(('SEM SAIDA', ident, tipo))
        elif ident not in alcancados:
            problemas.append(('INALCANCAVEL', ident, tipo))
    return padrao, vistos, arestas, alcancados, problemas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('xml', nargs='+')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    falhou = False
    for caminho in args.xml:
        padrao, vistos, arestas, alcancados, problemas = audita(caminho)
        if not args.quiet:
            print('\n== %s (defaultcontrol=%s, %d controles focaveis, %d alcancaveis)'
                  % (caminho, padrao, len(vistos), len(alcancados)))
            for ident, (tipo, _pai, _elem) in sorted(vistos.items()):
                print('  %-6s %-12s -> %s' % (ident, tipo,
                                              ','.join(sorted(str(a) for a in arestas.get(ident, ()))) or '(-)'))
        for motivo, ident, tipo in problemas:
            print('::%s::%s %s (%s)' % ('error' if motivo == 'SEM SAIDA' else 'warning',
                                        motivo, ident, tipo))
            falhou = True
    return 1 if falhou else 0


if __name__ == '__main__':
    sys.exit(main())
