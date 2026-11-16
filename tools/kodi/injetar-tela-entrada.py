#!/usr/bin/env python3
"""Injeta a tela de entrada do ZIP num APK SMARTEDTV ja existente.

Nao troca skin, nao muda versao, nao recompila nada e nao recria interface:
todas as entradas do APK original sao copiadas como estao (exceto as assinaturas
META-INF, que sao refeitas depois). O que muda:

1. ``assets/addons/script.smartedtv.welcome/`` — os 15 arquivos do ZIP, byte a
   byte (layout, imagens e QR Codes originais);
2. ``Startup.xml`` das skins do APK — e o ponto que o Kodi executa ANTES da
   Home (WINDOW_STARTUP_ANIM, aberto por CApplication::Initialize no lugar da
   Home). O arquivo passa a disparar a tela do ZIP em vez de ir direto para a
   Home; a Home so e criada quando a tela conclui;
3. ``Font.xml`` das skins — apenas nomes de fonte NOVOS usados pelo layout do
   ZIP (font20/font22/font24/font30), que faltavam no app; sem eles o Kodi cai
   em font13 e a tela nao fica 100% formatada;
4. ``addon-manifest.xml`` — registro do addon da tela (``optional="true"``,
   igual aos outros addons do app): e o que garante, no Kodi Omega 21, que a
   linha nova do banco de addons nasce com ``enabled=1``, condicao para o
   ``RunScript(<id>)`` do Startup.xml funcionar.

O perfil semeado ``assets/smarted/profile/`` e intocado: o dex confere o SHA-256
de cada arquivo dele contra o profile-manifest. O ``service.py`` do APK tambem
nao e alterado.

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
ADDON_ID = ADDON_DIR.name
ADDON_PREFIX = "assets/addons/%s/" % ADDON_ID
MANIFEST = "assets/system/addon-manifest.xml"
PROFILE_PREFIX = "assets/smarted/profile/"
# Modulo de licenca VIP que ja existe no APK (usado pelos botoes da tela).
VIP_MODULO = "assets/addons/service.smarted.bootstrap/vip.py"
SIG = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$", re.I)

# Fontes usadas por DialogWelcome.xml: o gerador da tela nomeia cada estilo
# `wf<tamanho>` (o tamanho em px de 1080p medido do CSS do pacote). Só as que
# faltarem em cada skin são declaradas; sem elas o Kodi cai em font13 e a tela
# sai fora de escala.
FONTE_ARQUIVO = "NotoSans-Regular.ttf"


def fontes_da_tela(raiz=None):
    """Le do próprio DialogWelcome.xml quais estilos wfNN a tela usa."""
    raiz = raiz or ROOT
    layout = (raiz / "kodi" / "addons" / ADDON_ID / "resources" / "skins" /
              "Default" / "1080i" / "DialogWelcome.xml")
    texto = layout.read_text(encoding="utf-8")
    nomes = sorted(set(re.findall(r"<font>(wf(\d+))</font>", texto)))
    if not nomes:
        raise SystemExit("DialogWelcome.xml sem estilos de fonte wfNN")
    return [(nome, int(tamanho)) for nome, tamanho in nomes]


FONTES_DA_TELA = None  # preenchido em main() a partir do XML (ver fontes_da_tela)

STARTUP_ANTIGO = "<onload>ReplaceWindow($INFO[System.StartupWindow])</onload>"
# RunScript pelo ID do addon: o Kodi resolve o caminho real (no Android os
# addons do APK ficam em special://xbmc, nao em special://home). Para o ID
# resolver, o addon precisa estar habilitado no banco: ele entra no
# addon-manifest.xml na forma que os outros addons do app ja usam
# (optional="true"). CAddonDatabase::SyncInstalled marca enabled=1 em toda linha
# NOVA (system ou optional) - e a linha deste addon nao existe no perfil
# semeado, conferido aqui. Nao usamos <addon> obrigatorio de proposito:
# CAddonMgr::Init() aborta o Kodi inteiro (LOGFATAL) se um addon obrigatorio do
# manifest nao carregar, e a tela nao vale derrubar o app.
STARTUP_NOVO = (
    "<onload>AlarmClock(smartedtv_entrada,"
    "RunScript(script.smartedtv.welcome),00:00:00,silent)</onload>\n"
    "\t<onload>AlarmClock(smartedtv_entrada_seguro,"
    "ReplaceWindow($INFO[System.StartupWindow]),00:00:30,silent)</onload>")


def validar_publicacao(dados: bytes) -> None:
    """Recusa um Startup.xml que carregue a Home antes da tela."""
    texto = dados.decode("utf-8")
    if "smartedtv_entrada," not in texto:
        raise SystemExit("Startup.xml sem o disparo da tela de entrada")
    # o unico ReplaceWindow permitido e o seguro de 30 s
    if texto.count("ReplaceWindow") != 1:
        raise SystemExit("Startup.xml com ReplaceWindow indevido")
    if "smartedtv_entrada_seguro" not in texto.split("ReplaceWindow")[0]:
        raise SystemExit("ReplaceWindow do Startup.xml nao pertence ao seguro")
    ET.fromstring(texto.encode("utf-8"))


def arquivos_do_addon():
    arquivos = {}
    for caminho in sorted(ADDON_DIR.rglob("*")):
        if not caminho.is_file() or "__pycache__" in caminho.parts or caminho.suffix == ".pyc":
            continue
        arquivos[ADDON_PREFIX + caminho.relative_to(ADDON_DIR).as_posix()] = caminho.read_bytes()
    for obrigatorio in ("addon.xml", "default.py",
                        "resources/skins/Default/1080i/DialogWelcome.xml",
                        "resources/skins/Default/media/bg.png",
                        "resources/skins/Default/media/qr_checkout.png",
                        "resources/skins/Default/media/qr_apk.png"):
        if ADDON_PREFIX + obrigatorio not in arquivos:
            raise SystemExit("addon da tela incompleto: falta %s" % obrigatorio)
    return arquivos


def patch_startup(dados: bytes) -> bytes:
    """Troca o salto direto para a Home pelo disparo da tela de entrada."""
    texto = dados.decode("utf-8")
    if "smartedtv_entrada" in texto:
        raise SystemExit("Startup.xml do APK ja abre a tela de entrada")
    if texto.count(STARTUP_ANTIGO) != 1:
        raise SystemExit("Startup.xml inesperado (sem o ReplaceWindow original)")
    novo = texto.replace(STARTUP_ANTIGO, STARTUP_NOVO, 1)
    dados_novos = novo.encode("utf-8")
    validar_publicacao(dados_novos)
    return dados_novos


def patch_fonts(dados: bytes) -> bytes:
    """Acrescenta, em cada fontset, as fontes do layout que a skin nao declara."""
    texto = dados.decode("utf-8")
    fontes = FONTES_DA_TELA if FONTES_DA_TELA is not None else fontes_da_tela()
    faltando = [(nome, tamanho) for nome, tamanho in fontes
                if "<name>%s</name>" % nome not in texto]
    if not faltando:
        raise SystemExit("a skin ja declara as fontes do layout; nada a corrigir")
    blocos = []
    for nome, tamanho in faltando:
        blocos.append(
            "\t\t<font>\n"
            "\t\t\t<name>%s</name>\n"
            "\t\t\t<filename>%s</filename>\n"
            "\t\t\t<size>%d</size>\n"
            "\t\t\t<style>lighten</style>\n"
            "\t\t</font>\n" % (nome, FONTE_ARQUIVO, tamanho))
    inserir = "".join(blocos)
    total_fontsets = texto.count("</fontset>")
    if total_fontsets < 1:
        raise SystemExit("Font.xml sem fontset")
    novo = texto.replace("</fontset>", inserir + "</fontset>")
    ET.fromstring(novo.encode("utf-8"))
    for nome, _ in faltando:
        if novo.count("<name>%s</name>" % nome) != total_fontsets:
            raise SystemExit("falha ao declarar %s em todos os fontsets" % nome)
    # as fontes que a skin ja tinha continuam todas declaradas
    for nome in re.findall(r"<name>([^<]+)</name>", texto):
        if nome not in [n for n, _ in faltando] and "<name>%s</name>" % nome not in novo:
            raise SystemExit("fonte original %s desapareceu do Font.xml" % nome)
    return novo.encode("utf-8"), [n for n, _ in faltando]


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path, help="APK atual (integro)")
    parser.add_argument("--saida", required=True, type=Path,
                        help="APK com a tela injetada, sem assinar")
    args = parser.parse_args(argv)
    if args.apk.resolve() == args.saida.resolve():
        raise SystemExit("entrada e saida precisam ser diferentes")

    global FONTES_DA_TELA
    FONTES_DA_TELA = fontes_da_tela()
    extras = arquivos_do_addon()
    startups, fontes_alteradas = [], []

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
            if item.filename == MANIFEST:
                dados = patch_manifest(dados)
                print("  addon-manifest.xml: %s registrado" % ADDON_ID)
            else:
                if re.fullmatch(r"assets/addons/[^/]+/xml/Startup\.xml", item.filename):
                    dados = patch_startup(dados)
                    startups.append(item.filename)
                    print("  %s: abre a tela antes da Home" % item.filename)
                m = re.fullmatch(r"assets/addons/([^/]+)/xml/Font\.xml", item.filename)
                if m:
                    dados, adicionadas = patch_fonts(dados)
                    fontes_alteradas.append(item.filename)
                    print("  %s: %s declaradas"
                          % (item.filename, "/".join(adicionadas)))
            info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            info.compress_type = item.compress_type
            info.external_attr = item.external_attr
            info.comment = item.comment
            destino.writestr(info, dados)

        for obrigatorio in (MANIFEST, VIP_MODULO):
            if obrigatorio not in nomes:
                raise SystemExit("APK atual sem %s" % obrigatorio)
        if not perfil:
            raise SystemExit("APK atual sem perfil semeado (assets/smarted/profile/)")
        if not startups:
            raise SystemExit("nenhum Startup.xml de skin encontrado no APK")
        if not fontes_alteradas:
            raise SystemExit("nenhum Font.xml de skin encontrado no APK")

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

    print("APK com a tela: %s (%d entradas, %d arquivos novos, %d Startup.xml, "
          "%d Font.xml, perfil intacto)"
          % (args.saida, len(nomes) + len(extras), len(extras), len(startups),
             len(fontes_alteradas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
