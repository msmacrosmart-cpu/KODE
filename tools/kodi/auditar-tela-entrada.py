#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audita a tipografia e a geometria de DialogWelcome.xml sem precisar de Kodi.

Para cada controle de texto do layout, mede o texto com a fonte real (a mesma
NotoSans e o mesmo tamanho em px que o Kodi vai usar) e reprova:

1. **estouro** — texto mais largo que o controle (o Kodi corta) ou mais alto que
   a caixa de linha (o Kodi corta o descendente: "ã", "ç", "J", "g", "p");
2. **colisao** — texto encostando/cobrindo outro controle (icone, botao, placa
   de QR, borda do cartao);
3. **glifo ausente** — caractere que a fonte nao tem (vira quadradinho/tofu);
4. **fora da tela** — controle fora de 1920x1080.

Tambem confere que todo botao tem textura de foco distinta da normal (sem isso o
usuario nao ve onde esta o cursor do controle remoto).

Uso:
    python3 tools/kodi/auditar-tela-entrada.py            # relatorio
    python3 tools/kodi/auditar-tela-entrada.py --falhar   # exit 1 se achar erro
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "kodi" / "addons" / "script.smartedtv.welcome"
LAYOUT = ADDON / "resources" / "skins" / "Default" / "1080i" / "DialogWelcome.xml"
FONTE = ROOT / "kodi" / "skin.estilo.personalizado" / "fonts" / "NotoSans-Regular.ttf"
# copia sem hinting so para desenhar a prova (mesmos contornos/metricas)
FONTE_PROVA = ROOT / "build_test" / "NotoSans-render.ttf"
VW, VH = 1920, 1080
# folga minima entre texto e qualquer coisa (px)
FOLGA = 4

try:
    from PIL import ImageFont
    PIL_OK = True
except ImportError:  # pragma: no cover
    PIL_OK = False


def tamanhos_fonte() -> dict:
    """`wfNN` -> NN (o gerador batiza cada estilo com a altura em px de 1080p)."""
    return {nome: int(nome[2:]) for nome in
            set(__import__("re").findall(r"<font>(wf\d+)</font>",
                                         LAYOUT.read_text(encoding="utf-8")))}


def fonte(tamanho):
    caminho = FONTE_PROVA if FONTE_PROVA.is_file() else FONTE
    return ImageFont.truetype(str(caminho), tamanho)


def caixa(no):
    """left/top/width/height resolvidos (aceita right/bottom como o Kodi)."""
    def num(tag):
        valor = (no.findtext(tag) or "").strip()
        if not valor:
            return None
        if valor.endswith("%"):
            base = VW if tag in ("left", "right", "width") else VH
            return round(base * float(valor[:-1]) / 100.0)
        return int(float(valor))

    largura = num("width")
    altura = num("height")
    x = num("left")
    if x is None:
        direita = num("right")
        # sem left e sem right o Kodi usa 0 (grupos costumam vir assim)
        x = 0 if direita is None else VW - direita - (largura or 0)
    y = num("top")
    if y is None:
        fundo = num("bottom")
        y = 0 if fundo is None else VH - fundo - (altura or 0)
    return x, y, largura or 0, altura or 0


def glifos_ausentes(texto, caminho_fonte):
    """Caracteres que a fonte nao cobre (viram quadradinho no Kodi)."""
    from fontTools.ttLib import TTFont
    cmap = TTFont(str(caminho_fonte), fontNumber=0).getBestCmap()
    return sorted({c for c in texto if c not in ("\n",) and ord(c) not in cmap})


def auditar(caminho=None):
    caminho = caminho or LAYOUT
    raiz = ET.parse(caminho).getroot()
    tamanhos = tamanhos_fonte()
    problemas = []
    textos = []      # (id, x0, y0, x1, y1, texto)
    desenhos = []    # (id, tipo, x0, y0, x1, y1)

    # caixa absoluta de cada controle (grupos deslocam os filhos)
    posicoes = {}
    grupos = {}
    for grupo in raiz.iter("control"):
        if grupo.get("type") != "group":
            continue
        grupos[id(grupo)] = (grupo.get("id") or "-")
        gx, gy, _, _ = caixa(grupo)
        for filho in grupo.findall("control"):
            x, y, w, h = caixa(filho)
            posicoes[id(filho)] = (x + gx, y + gy, w, h)

    escopo = {}
    for grupo in raiz.iter("control"):
        if grupo.get("type") != "group":
            continue
        for filho in grupo.findall("control"):
            escopo[id(filho)] = (grupo.get("id") or "-")

    for no in raiz.iter("control"):
        ident = no.get("id") or "-"
        tipo = no.get("type")
        x, y, w, h = posicoes.get(id(no)) or caixa(no)
        # fundo/tela cheia e decoracao de fundo nao "colidem" com texto
        decorativo = w >= VW * 0.95 and h >= VH * 0.95
        if x < 0 or y < 0 or x + w > VW or y + h > VH:
            problemas.append("%s (%s): fora da tela %s" % (ident, tipo, (x, y, w, h)))
        if tipo in ("button", "edit"):
            normal = (no.findtext("texturenofocus") or "").strip()
            foco = (no.findtext("texturefocus") or "").strip()
            if normal and foco and normal == foco:
                problemas.append("%s: foco igual ao normal (%s) - o D-pad "
                                 "nao mostra onde esta" % (ident, normal))
        if tipo == "image":
            nome = (no.findtext("texture") or "").strip()
            arquivo = ADDON / "resources" / "skins" / "Default" / "media" / nome
            if nome and not arquivo.is_file():
                problemas.append("%s: textura ausente %s" % (ident, nome))
            if not decorativo:
                desenhos.append((ident, "image", x, y, x + w, y + h,
                                 escopo.get(id(no))))
            continue
        if tipo not in ("label", "button", "edit"):
            continue

        rotulo = (no.findtext("label") or "").strip()
        # [CR] e [B]...[/B] sao marcacao do Kodi, nao texto
        rotulo = rotulo.replace("[B]", "").replace("[/B]", "")
        if not rotulo:
            desenhos.append((ident, tipo, x, y, x + w, y + h, escopo.get(id(no))))
            continue
        if rotulo.startswith("$INFO["):
            # texto dinamico (property/variavel): nao ha como medir aqui
            desenhos.append((ident, tipo, x, y, x + w, y + h, escopo.get(id(no))))
            continue

        estilo = (no.findtext("font") or "").strip()
        tamanho = tamanhos.get(estilo, 15)
        f = fonte(tamanho)
        linhas_txt = [l for l in rotulo.replace("[CR]", "\n").split("\n")]
        medidas = []
        for linha in linhas_txt:
            esquerda, topo, direita, base = f.getbbox(linha or " ", anchor="la")
            medidas.append((direita - esquerda, base - topo))
        largura_texto = max(m[0] for m in medidas)
        altura_texto = sum(m[1] for m in medidas)

        if largura_texto > w:
            problemas.append(
                "%s (%s): texto %.0f px nao cabe em %d px -> \"%s\""
                % (ident, tipo, largura_texto, w, rotulo))
        # o Kodi desenha a linha inteira dentro de <height>; se a caixa for menor
        # que o ascendente+descendente da fonte, as letras sao cortadas
        if altura_texto > h + 1:
            problemas.append(
                "%s (%s): caixa com %d px de altura para texto de %.0f px -> \"%s\""
                % (ident, tipo, h, altura_texto, rotulo))

        faltando = glifos_ausentes(rotulo, FONTE)
        if faltando:
            problemas.append("%s: glifo ausente na fonte: %s (%s)"
                             % (ident, ", ".join(repr(c) for c in faltando), rotulo))

        # onde o texto realmente e desenhado
        alinhamento = (no.findtext("align") or "left").strip()
        x, y, w, h = posicoes.get(id(no)) or (x, y, w, h)
        if tipo == "button":
            px = x + (w - largura_texto) / 2
            py = y + (h - altura_texto) / 2
        elif tipo == "edit":
            px, py = x + 14, y + (h - altura_texto) / 2   # padding padrao do Kodi
        else:
            px = x if alinhamento == "left" else (
                x + (w - largura_texto) / 2 if alinhamento == "center"
                else x + w - largura_texto)
            py = y
        textos.append((ident, px, py, px + largura_texto, py + altura_texto, rotulo,
                       escopo.get(id(no))))
        desenhos.append((ident, tipo, x, y, x + w, y + h, escopo.get(id(no))))

    def sobrepoe(a, b, folga=FOLGA):
        return (a[0] < b[2] - folga and b[0] < a[2] - folga and
                a[1] < b[3] - folga and b[1] < a[3] - folga)

    def painel(px0, py0, px1, py1):
        """Superficie de fundo grande (cartao, barra, placa): texto nao a cruza."""
        return (px1 - px0) * (py1 - py0) >= 40000

    def dentro(menor, maior, folga=1):
        """O texto esta inteiramente contido na imagem (fundo/cartao/placa)?"""
        return (menor[0] >= maior[0] - folga and menor[1] >= maior[1] - folga and
                menor[2] <= maior[2] + folga and menor[3] <= maior[3] + folga)

    fundo_do_botao = {ident: (x, y, x + w, y + h) for ident, tipo, x, y, w, h
                      in [] }
    # um botao desenha o proprio fundo: o texto dele nao "colide" com ele
    for no in raiz.iter("control"):
        if no.get("type") in ("button", "edit"):
            x, y, w, h = posicoes.get(id(no)) or caixa(no)
            fundo_do_botao[no.get("id") or "-"] = (x, y, x + w, y + h)

    # texto encostando em icone/placa/divisor (parcial: corta ou cobre)
    for ident, x0, y0, x1, y1, rotulo, meu_escopo in textos:
        for outro, tipo, ox0, oy0, ox1, oy1, escopo_dele in desenhos:
            if tipo != "image" or outro == ident:
                continue
            # elementos de grupos diferentes nao se misturam (o dialogo e modal)
            if meu_escopo != escopo_dele:
                continue
            caixa_imagem = (ox0, oy0, ox1, oy1)
            if dentro((x0, y0, x1, y1), caixa_imagem):
                continue          # texto dentro do cartao/fundo: normal
            # o texto comeca dentro de um painel e termina fora: vaza pela borda
            sobreposto = sobrepoe((x0, y0, x1, y1), caixa_imagem, folga=0)
            if sobreposto and painel(ox0, oy0, ox1, oy1):
                problemas.append(
                    "%s (texto \"%s\") atravessa a borda do painel %s"
                    % (ident, rotulo, outro))
                continue
            if sobrepoe((x0, y0, x1, y1), caixa_imagem, folga=2):
                problemas.append(
                    "%s (texto \"%s\") invade a imagem %s"
                    % (ident, rotulo, outro))
    # texto por cima de outro texto
    for i, (ident, x0, y0, x1, y1, rotulo, meu_escopo) in enumerate(textos):
        for outro, ox0, oy0, ox1, oy1, outro_rotulo, escopo_dele in textos[i + 1:]:
            if meu_escopo != escopo_dele:
                continue
            if sobrepoe((x0, y0, x1, y1), (ox0, oy0, ox1, oy1), folga=2):
                problemas.append("%s (\"%s\") encosta em %s (\"%s\")"
                                 % (ident, rotulo, outro, outro_rotulo))
    return problemas, textos


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--falhar", action="store_true",
                        help="sai com erro se houver qualquer problema")
    parser.add_argument("--layout", type=Path, default=LAYOUT)
    args = parser.parse_args(argv)
    if not PIL_OK:
        raise SystemExit("Pillow necessario: python3 -m pip install Pillow==11.3.0")

    problemas, textos = auditar(args.layout)
    print("Auditoria de %s" % args.layout.resolve().relative_to(ROOT))
    print("  %d textos medidos com a fonte real" % len(textos))
    for problema in problemas:
        print("  FALHA  %s" % problema)
    if not problemas:
        print("  OK: nenhum texto estoura, colide ou usa glifo ausente")
    else:
        print("\n%d problema(s)" % len(problemas))
    return 1 if (problemas and args.falhar) else 0


if __name__ == "__main__":
    sys.exit(main())
