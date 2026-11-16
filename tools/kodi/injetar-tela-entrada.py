#!/usr/bin/env python3
"""Injeta a tela inicial do ZIP num APK SMARTEDTV ja existente.

Nao troca skin, nao muda versao, nao recompila nada e nao recria interface:
todas as entradas do APK original sao copiadas como estao (exceto as
assinaturas META-INF, que sao refeitas depois). O que e acrescentado/ajustado:

* ``assets/addons/script.smartedtv.welcome/`` — os 15 arquivos do ZIP, byte a
  byte iguais (layout, imagens e QR Codes originais);
* ``assets/addons/service.smarted.bootstrap/tela_entrada.py`` — modulo do
  servico de boot que ja existe no APK; abre/confirma a tela sem depender do
  banco de addons do Kodi;
* ``assets/addons/service.smarted.bootstrap/service.py`` — 2 linhas: o import
  do modulo e o disparo da thread ``welcome-entry``;
* ``assets/system/addon-manifest.xml`` — registro do addon da tela;
* ``Font.xml`` das skins do projeto — apenas nomes de fonte NOVOS que o layout
  do ZIP usa (font20/font22/font24/font30) e que faltavam no app; sem isso o
  Kodi cai em font13 e a tela nao fica 100% formatada. Nenhuma fonte existente
  e alterada e nenhuma outra tela usa esses nomes.

O perfil semeado ``assets/smarted/profile/`` e intocado: o dex confere o SHA-256
de cada arquivo dele contra o profile-manifest.

Uso:
    python3 tools/kodi/injetar-tela-entrada.py --apk ATUAL.apk --saida BRUTO.apk
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON_DIR = ROOT / "kodi" / "addons" / "script.smartedtv.welcome"
BOOTSTRAP_DIR = ROOT / "kodi" / "addons" / "service.smarted.bootstrap"
ADDON_ID = ADDON_DIR.name
ADDON_PREFIX = "assets/addons/%s/" % ADDON_ID
BOOTSTRAP = "assets/addons/service.smarted.bootstrap/service.py"
MODULO = "assets/addons/service.smarted.bootstrap/tela_entrada.py"
MANIFEST = "assets/system/addon-manifest.xml"
PROFILE_PREFIX = "assets/smarted/profile/"
SIG = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$", re.I)

# Fontes usadas por DialogWelcome.xml que nao existem nas skins do APK. Sao
# apenas nomes novos, com o mesmo arquivo de fonte e o mesmo estilo das vizinhas.
FONTES_DA_TELA = [
    ("font20", 20),
    ("font22", 22),
    ("font24", 24),
    ("font30", 30),
]
SKINS = ("skin.novatv", "skin.smartedtv.classic", "skin.estuary")

HOOK_IMPORT = "from tela_entrada import abrir_tela_entrada\n"

HOOK_CALL = '''    entrada = threading.Thread(target=abrir_tela_entrada,
                               args=(monitor, log),
                               name='welcome-entry')
    entrada.daemon = True
    entrada.start()
'''


def arquivos_do_addon():
    arquivos = {}
    for caminho in sorted(ADDON_DIR.rglob("*")):
        if not caminho.is_file() or "__pycache__" in caminho.parts or caminho.suffix == ".pyc":
            continue
        arquivos[ADDON_PREFIX + caminho.relative_to(ADDON_DIR).as_posix()] = caminho.read_bytes()
    if len(arquivos) != 15:
        raise SystemExit("addon da tela incompleto: %d arquivos (esperado 15)" % len(arquivos))
    return arquivos


def patch_service(dados: bytes) -> bytes:
    texto = dados.decode("utf-8")
    if "tela_entrada import abrir_tela_entrada" in texto:
        raise SystemExit("service.py do APK ja tem o gancho da tela de entrada")
    ancora_import = "import xbmcvfs\n"
    ancora_main = "def main():\n    monitor = xbmc.Monitor()\n"
    if texto.count(ancora_import) != 1 or texto.count(ancora_main) != 1:
        raise SystemExit("ancoras de import/main() nao encontradas no service.py do APK")
    if not re.search(r"^import threading$", texto, re.M):
        raise SystemExit("service.py do APK nao importa threading")
    texto = texto.replace(ancora_import, ancora_import + HOOK_IMPORT, 1)
    texto = texto.replace(ancora_main, ancora_main + "\n" + HOOK_CALL + "\n", 1)
    compile(texto, BOOTSTRAP, "exec")  # nunca entregar Python quebrado
    return texto.encode("utf-8")


def patch_manifest(dados: bytes) -> bytes:
    texto = dados.decode("utf-8")
    if ">%s<" % ADDON_ID in texto:
        raise SystemExit("addon ja registrado no addon-manifest.xml")
    if texto.count("</addons>") != 1:
        raise SystemExit("formato inesperado do addon-manifest.xml")
    novo = texto.replace(
        "</addons>",
        '  <addon optional="true">%s</addon>\n</addons>' % ADDON_ID, 1)
    ET.fromstring(novo)
    return novo.encode("utf-8")


def patch_fonts(dados: bytes) -> bytes:
    """Acrescenta font20/font22/font24/font30 em cada fontset, sem tocar no resto."""
    texto = dados.decode("utf-8")
    for nome, _tamanho in FONTES_DA_TELA:
        if "<name>%s</name>" % nome in texto:
            raise SystemExit("a skin ja declara %s; nada a corrigir" % nome)
    blocos = []
    for nome, tamanho in FONTES_DA_TELA:
        blocos.append(
            "\t\t<font>\n"
            "\t\t\t<name>%s</name>\n"
            "\t\t\t<filename>NotoSans-Regular.ttf</filename>\n"
            "\t\t\t<size>%d</size>\n"
            "\t\t\t<style>lighten</style>\n"
            "\t\t</font>\n" % (nome, tamanho))
    inserir = "".join(blocos)
    total_fontsets = texto.count("</fontset>")
    if total_fontsets < 1:
        raise SystemExit("Font.xml sem fontset")
    # declara as fontes antes de cada </fontset>, sem mexer em nada mais
    novo = texto.replace("</fontset>", inserir + "</fontset>")
    ET.fromstring(novo.encode("utf-8"))
    for nome, _ in FONTES_DA_TELA:
        if novo.count("<name>%s</name>" % nome) != total_fontsets:
            raise SystemExit("falha ao declarar %s em todos os fontsets" % nome)
        if "<name>%s</name>" % nome in dados.decode("utf-8"):
            raise SystemExit("%s ja existia na skin" % nome)
    return novo.encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path, help="APK atual (integro)")
    parser.add_argument("--saida", required=True, type=Path, help="APK com a tela injetada, sem assinar")
    args = parser.parse_args(argv)
    if args.apk.resolve() == args.saida.resolve():
        raise SystemExit("entrada e saida precisam ser diferentes")

    extras = arquivos_do_addon()
    extras[MODULO] = (BOOTSTRAP_DIR / "tela_entrada.py").read_bytes()
    compile(extras[MODULO].decode("utf-8"), MODULO, "exec")
    fontes_alteradas = []

    with zipfile.ZipFile(args.apk) as origem, \
            zipfile.ZipFile(args.saida, "w", allowZip64=True) as destino:
        nomes = set()
        perfil = {}
        for item in origem.infolist():
            if item.is_dir() or SIG.fullmatch(item.filename):
                continue
            if item.filename in nomes:
                raise SystemExit("entrada duplicada no APK: %s" % item.filename)
            nomes.add(item.filename)
            dados = origem.read(item)
            if item.filename.startswith(PROFILE_PREFIX):
                perfil[item.filename] = hashlib.sha256(dados).hexdigest()
            if item.filename == BOOTSTRAP:
                dados = patch_service(dados)
                print("  service.py: import + thread welcome-entry")
            elif item.filename == MANIFEST:
                dados = patch_manifest(dados)
                print("  addon-manifest.xml: %s registrado" % ADDON_ID)
            else:
                m = re.fullmatch(r"assets/addons/([^/]+)/xml/Font\.xml", item.filename)
                if m and m.group(1) in SKINS:
                    dados = patch_fonts(dados)
                    fontes_alteradas.append(item.filename)
                    print("  %s: font20/font22/font24/font30 declaradas" % item.filename)
            info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            info.compress_type = item.compress_type
            info.external_attr = item.external_attr
            info.comment = item.comment
            destino.writestr(info, dados)

        for obrigatorio in (BOOTSTRAP, MANIFEST):
            if obrigatorio not in nomes:
                raise SystemExit("APK atual sem %s" % obrigatorio)
        if not perfil:
            raise SystemExit("APK atual sem perfil semeado (assets/smarted/profile/)")
        if not fontes_alteradas:
            raise SystemExit("nenhum Font.xml das skins do projeto encontrado no APK")

        for nome, dados in extras.items():
            if nome in nomes:
                raise SystemExit("arquivo ja presente no APK: %s" % nome)
            info = zipfile.ZipInfo(nome, date_time=(2026, 11, 16, 13, 44, 0))
            # sem compressao, como os demais addons de sistema do APK: o Kodi
            # le assets/addons direto do APK e align-apk.py realinha as entradas
            # stored a 4 bytes antes da assinatura.
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            destino.writestr(info, dados)

    with zipfile.ZipFile(args.saida) as conferido:
        for nome, resumo in perfil.items():
            if hashlib.sha256(conferido.read(nome)).hexdigest() != resumo:
                raise SystemExit("perfil semeado alterado: %s" % nome)
        for nome in extras:
            if nome not in conferido.namelist():
                raise SystemExit("arquivo da tela ausente: %s" % nome)

    print("APK com a tela: %s (%d entradas, %d arquivos novos, %d Font.xml, perfil intacto)"
          % (args.saida, len(nomes) + len(extras), len(extras),
             len(fontes_alteradas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
