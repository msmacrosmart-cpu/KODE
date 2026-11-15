#!/usr/bin/env python3
"""Injeta a BASE ESTÁVEL (perfil semeado) no APK unificado.

A linha clássica funcionava porque o APK levava dentro de si o perfil já
customizado — skin, menus, fontes do catálogo e, principalmente, o
``plugin.video.BrazucaPlay.Matrix`` instalado. Sem isso, o catálogo abre sem as
categorias (Doramas, Animes, Novelas, Desenhos), porque ``plugin.video.smarted``
só delega para o Brazuca.

Este script copia ``assets/smarted/**`` do APK estável (1.0.63 clássica) para o
APK novo:

  * confere o SHA-256 de ``assets/smarted/profile-manifest.txt`` contra o valor
    fixo — o mesmo que o seeder do app valida em tempo de execução;
  * não sobrescreve nada: o APK novo não pode já ter ``assets/smarted``;
  * preserva byte a byte todas as outras entradas (dex, libs, recursos, addons),
    inclusive o tipo de compressão de cada uma;
  * remove as assinaturas antigas (META-INF/*.SF|*.RSA|*.DSA|*.MF) — o APK
    precisa ser assinado de novo depois (zipalign + apksigner).

Uso:
    python3 inject-base-estavel.py --apk novo.apk --base estavel.apk --saida out.apk
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

MANIFESTO = "assets/smarted/profile-manifest.txt"

# Pastas que sao SUBSTITUIDAS pelo conteudo do APK estavel (o resto e nosso).
# Motivo (diff real 1.0.63 x 1.0.65): a skin.novatv do nosso build ia com 222
# arquivos e a estavel tinha 934 (faltavam as 712 imagens de media/) — a Home
# abria sem icones/abas. E o plugin.video.smarted tinha 7 arquivos diferentes.
SUBSTITUIR = (
    "assets/addons/skin.novatv/",
    "assets/addons/plugin.video.smarted/",
)
PREFIXO = "assets/smarted/"
SHA_ESPERADO = "1447de816a44ecc11c42c2c315cf20e61c9baa037e914a13293711cf152d1ede"
ASSINATURAS = (".SF", ".RSA", ".DSA", ".MF")


def sha256(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def ler_base(base: Path, esperado: str) -> tuple[dict[str, bytes], int, str]:
    """Lê assets/smarted/** do APK estável e valida o manifesto."""
    if not base.is_file():
        raise SystemExit(f"APK da base estável ausente: {base}")
    itens: dict[str, bytes] = {}
    with zipfile.ZipFile(base) as z:
        nomes = [n for n in z.namelist() if n.startswith(PREFIXO) and not n.endswith("/")]
        if MANIFESTO not in nomes:
            raise SystemExit(
                f"o APK estável não tem {MANIFESTO} — base errada"
            )
        manifesto = z.read(MANIFESTO)
        digest = sha256(manifesto)
        if digest != esperado:
            raise SystemExit(
                f"manifesto do perfil não confere: {digest} (esperado {esperado})"
            )
        for nome in nomes:
            itens[nome] = z.read(nome)

        # skin e plugin: vêm inteiros do APK estável
        substituidas = 0
        for info in z.infolist():
            nome = info.filename
            if nome.endswith("/") or not nome.startswith(SUBSTITUIR):
                continue
            if nome not in itens:
                itens[nome] = z.read(nome)
                substituidas += 1
    print(f"  {substituidas} arquivos de skin/plugin substituídos pelos do APK estável")
    return itens, len(itens), digest


def escrever(apk: Path, saida: Path, extras: dict[str, bytes]) -> tuple[int, int, int]:
    """Reescreve o APK preservando todas as entradas e acrescentando os extras."""
    total, removidas, adicionadas, substituidos = 0, 0, 0, 0
    with zipfile.ZipFile(apk) as origem, zipfile.ZipFile(
        saida, "w", zipfile.ZIP_DEFLATED
    ) as destino:
        escritas = set()  # só o que realmente foi para o APK novo
        for info in origem.infolist():
            nome = info.filename
            if nome.startswith(PREFIXO):
                raise SystemExit(f"o APK novo já tem {nome} — não vou duplicar")
            if nome.startswith(SUBSTITUIR):
                substituidos += 1
                continue
            if nome.startswith("META-INF/") and nome.upper().endswith(ASSINATURAS):
                removidas += 1
                continue
            novo = zipfile.ZipInfo(nome, date_time=info.date_time)
            novo.compress_type = info.compress_type
            novo.external_attr = info.external_attr
            novo.internal_attr = info.internal_attr
            novo.create_system = info.create_system
            destino.writestr(novo, origem.read(nome))
            escritas.add(nome)
            total += 1
        for nome, dados in sorted(extras.items()):
            # os nomes da skin/plugin que vieram da base FORAM descartados do
            # nosso APK de propósito — não são colisão.
            if nome in escritas:
                raise SystemExit(f"colisão de entrada: {nome}")
            destino.writestr(nome, dados, compress_type=zipfile.ZIP_DEFLATED)
            adicionadas += 1
    return total, removidas, adicionadas, substituidos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apk", required=True, type=Path, help="APK novo (compilado)")
    ap.add_argument("--base", required=True, type=Path, help="APK estável (linha clássica)")
    ap.add_argument("--saida", required=True, type=Path)
    ap.add_argument("--manifesto-sha", default=SHA_ESPERADO)
    args = ap.parse_args()

    extras, quantos, digest = ler_base(args.base, args.manifesto_sha)
    print(f"base estável: {args.base.name}")
    print(f"  manifesto {digest[:16]}… confere")
    print(f"  {quantos} arquivos sob {PREFIXO} "
          f"({sum(len(v) for v in extras.values()) / 1048576.0:.1f} MB)")

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as tmp:
        temporario = Path(tmp.name)
    try:
        total, removidas, adicionadas, substituidos = escrever(args.apk, temporario, extras)
        shutil.move(str(temporario), args.saida)
    finally:
        if temporario.exists():
            temporario.unlink()
    print(f"  {total} entradas preservadas, {removidas} assinaturas antigas removidas, "
          f"{adicionadas} entradas da base acrescentadas, "
          f"{substituidos} entradas nossas trocadas pelas do APK estável")
    print(f"APK com base estável: {args.saida} "
          f"({args.saida.stat().st_size / 1048576.0:.1f} MB)")
    print("assinatura removida de propósito: zipalign + apksigner vêm depois")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
