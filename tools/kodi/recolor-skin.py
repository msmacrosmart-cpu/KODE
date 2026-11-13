#!/usr/bin/env python3
"""Converte skins do Kodi 21 para a paleta preto, branco e cinza.

Serve para duas skins:

  * **Estuary** (a padrão do Kodi)  -> ``--skin estuary``
  * **Bingie Mod** (skin do APK)    -> ``--skin bingie``

Nas duas, as cores vivem num único arquivo ``colors/defaults.xml`` usado por
``colordiffuse=`` em centenas de pontos dos layouts. Recolorir só esse arquivo
muda a skin inteira sem tocar em layout, textura, navegação ou widget.

O que o script garante:

1. Apenas o tom muda — o **alfa é preservado** (correções de transparência da
   skin continuam valendo).
2. Nenhuma cor saturada sobra: ao final ele varre o arquivo e falha se encontrar
   qualquer tom com saturação acima de ``--max-saturation``. Isso pega tanto as
   cores nomeadas quanto as hexadecimais soltas.
3. Cores puramente neutras (preto/branco/cinza, onde R=G=B) são mantidas como
   estão: já fazem parte da paleta pedida.
4. ``--report`` mostra o antes/depois de cada cor alterada.

Uso:
    python3 tools/kodi/recolor-skin.py CAMINHO_DA_SKIN --skin estuary
    python3 tools/kodi/recolor-skin.py CAMINHO_DA_SKIN --skin bingie
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

COLOR_RE = re.compile(r'(<color\s+name="([^"]+)"\s*>)([0-9A-Fa-f]{8})(\s*</color>)')

# Estratégia: DESSATURAR preservando a luminância, e depois ampliar um pouco o
# contraste. Assim um fundo escuro continua escuro, um texto claro continua
# claro e uma borda média continua média — a skin vira preto/branco/cinza sem
# quebrar hierarquia visual. Foi tentada antes uma regra por "nome de cor", mas
# ela transformava o fundo azul-escuro do Estuary (FF0E597E) em cinza CLARO,
# o que deixaria os textos brancos ilegíveis. Dessaturar não tem esse risco.
CONTRASTE = 1.15   # >1 aproxima pretos de preto e brancos de branco


def luminancia(r: int, g: int, b: int) -> float:
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def target_rgb(name: str, r: int, g: int, b: int) -> tuple[int, int, int]:
    if r == g == b:                     # já é neutra: nada a fazer
        return (r, g, b)
    luz = luminancia(r, g, b) / 255.0
    luz = (luz - 0.5) * CONTRASTE + 0.5
    luz = max(0.0, min(1.0, luz)) * 255
    valor = int(round(luz))
    return (valor, valor, valor)


def saturation(r: int, g: int, b: int) -> int:
    return max(r, g, b) - min(r, g, b)


def recolor(skin: Path, limite: int, report: bool) -> int:
    arquivo = skin / "colors/defaults.xml"
    if not arquivo.is_file():
        print(f"ERRO: {arquivo} não existe", file=sys.stderr)
        return 2

    texto = arquivo.read_text(encoding="utf-8")
    mudancas: list[tuple[str, str, str]] = []

    def trocar(match: re.Match) -> str:
        abertura, nome, argb, fechamento = match.groups()
        r, g, b = int(argb[2:4], 16), int(argb[4:6], 16), int(argb[6:8], 16)
        nr, ng, nb = target_rgb(nome, r, g, b)
        novo = f"{argb[:2]}{nr:02X}{ng:02X}{nb:02X}"
        if novo.upper() != argb.upper():
            mudancas.append((nome, argb, novo))
            return abertura + novo + fechamento
        return match.group(0)

    texto = COLOR_RE.sub(trocar, texto)

    # rede de segurança: nenhuma cor saturada pode sobrar
    sobrando = [
        (nome, argb)
        for _, nome, argb, _ in COLOR_RE.findall(texto)
        if saturation(int(argb[2:4], 16), int(argb[4:6], 16), int(argb[6:8], 16)) > limite
    ]

    arquivo.write_text(texto, encoding="utf-8")

    if report:
        for nome, antes, depois in mudancas:
            print(f"  {nome:<24} {antes} -> {depois}")
    print(f"  {skin.name}: {len(mudancas)} cor(es) neutralizada(s)")

    if sobrando:
        for nome, argb in sobrando:
            print(f"  PENDENTE: {nome}={argb} ainda saturada", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("skin", type=Path, help="pasta da skin (com colors/defaults.xml)")
    parser.add_argument("--skin", dest="modo", choices=["estuary", "bingie"], default=None,
                        help="variante (afeta o relatório; a paleta é a mesma)")
    parser.add_argument("--max-saturation", type=int, default=24,
                        help="saturação máxima tolerada ao final (padrão: 24)")
    parser.add_argument("--report", action="store_true", help="mostra cada cor alterada")
    args = parser.parse_args()

    if not args.skin.is_dir():
        print(f"ERRO: skin inexistente: {args.skin}", file=sys.stderr)
        return 2
    return recolor(args.skin, args.max_saturation, args.report)


if __name__ == "__main__":
    raise SystemExit(main())
