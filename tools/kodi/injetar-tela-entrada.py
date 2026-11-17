#!/usr/bin/env python3
"""Injeta a tela de entrada do ZIP num APK SMARTEDTV ja existente.

Nao troca skin, nao muda versao, nao recompila nada e nao recria interface.
Etapas que ja existem no APK sao puladas (nao falham).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import traceback
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON_DIR = ROOT / "kodi" / "addons" / "script.smartedtv.welcome"
ADDON_ID = ADDON_DIR.name
ADDON_PREFIX = "assets/addons/%s/" % ADDON_ID
MANIFEST = "assets/system/addon-manifest.xml"
PROFILE_PREFIX = "assets/smarted/profile/"
VIP_MODULO = "assets/addons/service.smarted.bootstrap/vip.py"
KEYMAP_ORIGEM = ROOT / "kodi" / "keymaps" / "smartedtv-voltar.xml"
KEYMAP_DESTINO = "assets/system/keymaps/zzz-smartedtv-voltar.xml"
SIG = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$", re.I)
FONTE_ARQUIVO = "NotoSans-Regular.ttf"


def dbg(msg):
    print("[DEBUG] %s" % msg, flush=True)


def fontes_da_tela(raiz=None):
    raiz = raiz or ROOT
    layout = (raiz / "kodi" / "addons" / ADDON_ID / "resources" / "skins" /
              "Default" / "1080i" / "DialogWelcome.xml")
    texto = layout.read_text(encoding="utf-8")
    nomes = sorted(set(re.findall(r"<font>(wf(\d+))</font>", texto)))
    if not nomes:
        raise SystemExit("DialogWelcome.xml sem estilos de fonte wfNN")
    return [(nome, int(tamanho)) for nome, tamanho in nomes]


FONTES_DA_TELA = None

STARTUP_NOVO = (
    "<onload>AlarmClock(smartedtv_entrada,"
    "RunScript(script.smartedtv.welcome),00:00:00,silent)</onload>\n"
    "\t<onload>RunScript(script.smartedtv.welcome,seguro=1)</onload>")


def patch_startup(dados):
    """Troca o salto direto para a Home pelo disparo da tela de entrada."""
    texto = dados.decode("utf-8")
    if "smartedtv_entrada" in texto:
        dbg("patch_startup: ja tem smartedtv_entrada, pulando")
        return dados
    # Tenta varios padroes de ReplaceWindow do StartupWindow
    padroes = [
        r"<onload[^>]*>\s*ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)\s*</onload>",
        r"<onload>\s*ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)\s*</onload>",
        r"<onload\s*/>\s*ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)",
        r"ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)",
    ]
    for i, padrao in enumerate(padroes):
        alvos = re.findall(padrao, texto, re.DOTALL)
        dbg("patch_startup: padro %d -> %d alvos" % (i, len(alvos)))
        if len(alvos) == 1:
            alvo = alvos[0]
            novo = texto.replace(alvo, STARTUP_NOVO, 1)
            ET.fromstring(novo.encode("utf-8"))
            return novo.encode("utf-8")
    # Se nao encontrou nenhum, tenta injetar no final antes de </startup>
    dbg("patch_startup: nenhum padro encontrado, tentando injecao manual")
    if "</startup>" in texto:
        novo = texto.replace("</startup>",
                             STARTUP_NOVO + "\n</startup>", 1)
        ET.fromstring(novo.encode("utf-8"))
        return novo.encode("utf-8")
    raise SystemExit("Startup.xml sem ReplaceWindow do StartupWindow")


def patch_fonts(dados):
    """Acrescenta fontes wfNN que faltam em cada fontset."""
    texto = dados.decode("utf-8")
    fontes = FONTES_DA_TELA if FONTES_DA_TELA is not None else fontes_da_tela()
    faltando = [(n, t) for n, t in fontes
                if "<name>%s</name>" % n not in texto]
    dbg("patch_fonts: faltando=%s" % [n for n, _ in faltando])
    if not faltando:
        return texto.encode("utf-8"), []
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
    return novo.encode("utf-8"), [n for n, _ in faltando]


def patch_manifest(dados):
    texto = dados.decode("utf-8")
    if ">%s<" % ADDON_ID in texto:
        dbg("patch_manifest: addon ja registrado, pulando")
        return dados
    if texto.count("</addons>") != 1:
        raise SystemExit("formato inesperado do addon-manifest.xml")
    novo = texto.replace(
        "</addons>",
        '  <addon optional="true">%s</addon>\n</addons>' % ADDON_ID, 1)
    ET.fromstring(novo)
    return novo.encode("utf-8")


def extrair_keymap():
    if not KEYMAP_ORIGEM.is_file():
        raise SystemExit("keymap ausente: %s" % KEYMAP_ORIGEM)
    dados = KEYMAP_ORIGEM.read_bytes()
    raiz = ET.fromstring(dados)
    if raiz.tag != "keymap":
        raise SystemExit("keymap sem <keymap>")
    janelas = [e.tag for e in raiz]
    if janelas != ["Home"]:
        raise SystemExit("keymap mexe em janelas alem da Home: %s" % janelas)
    return {KEYMAP_DESTINO: dados}


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--saida", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.apk.resolve() == args.saida.resolve():
        raise SystemExit("entrada e saida precisam ser diferentes")

    global FONTES_DA_TELA
    FONTES_DA_TELA = fontes_da_tela()
    extras = arquivos_do_addon()
    extras.update(extrair_keymap())
    vip_path = ROOT / "kodi" / "addons" / "service.smarted.bootstrap" / "vip.py"
    if vip_path.is_file():
        extras[VIP_MODULO] = vip_path.read_bytes()

    startups, fontes_alteradas, keymaps = [], [], []
    skins_com_font = []

    try:
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
                try:
                    if item.filename.startswith(PROFILE_PREFIX):
                        perfil[item.filename] = hashlib.sha256(dados).hexdigest()
                    elif item.filename == MANIFEST:
                        try:
                            dados = patch_manifest(dados)
                            dbg("addon-manifest.xml: %s registrado" % ADDON_ID)
                        except SystemExit as e:
                            dbg("patch_manifest pulado: %s" % e)
                    elif item.filename.startswith("assets/system/keymaps/"):
                        if item.filename == KEYMAP_DESTINO:
                            dbg("keymap ja existe no APK, pulando adicionar")
                        else:
                            destino.writestr(item, dados)
                            continue
                    elif re.fullmatch(r"assets/addons/[^/]+/xml/Startup\.xml", item.filename):
                        try:
                            dados = patch_startup(dados)
                            startups.append(item.filename)
                            dbg("%s: abre a tela antes da Home" % item.filename)
                        except SystemExit as e:
                            dbg("patch_startup pulado para %s: %s" % (item.filename, e))
                    elif re.fullmatch(r"assets/addons/([^/]+)/xml/Font\.xml", item.filename):
                        try:
                            dados, adicionadas = patch_fonts(dados)
                            fontes_alteradas.append(item.filename)
                            skins_com_font.append(item.filename.split("/")[1])
                            dbg("%s: %s declaradas" % (item.filename, "/".join(adicionadas)))
                        except SystemExit as e:
                            dbg("patch_fonts pulado para %s: %s" % (item.filename, e))
                    info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                    info.compress_type = item.compress_type
                    info.external_attr = item.external_attr
                    info.comment = item.comment
                    destino.writestr(info, dados)
                except Exception as e:
                    dbg("ERRO processando %s: %s" % (item.filename, e))
                    traceback.print_exc()
                    # Pula esta entrada, continua com a proxima
                    continue

            if MANIFEST not in nomes:
                raise SystemExit("APK atual sem %s" % MANIFEST)
            if not perfil:
                raise SystemExit("APK atual sem perfil semeado (assets/smarted/profile/)")
            if not startups:
                raise SystemExit("nenhum Startup.xml de skin encontrado no APK")
            if not fontes_alteradas:
                raise SystemExit("nenhum Font.xml de skin encontrado no APK")

            dbg("Loop principal: %d nomes, %d startups, %d fontes, %d perfil" % (
                len(nomes), len(startups), len(fontes_alteradas), len(perfil)))

            # Copia fonte NotoSans para pastas fonts/ das skins que nao tem
            FONTE_ORIGEM = ROOT / "kodi" / "skin.estilo.personalizado" / "fonts" / FONTE_ARQUIVO
            if FONTE_ORIGEM.is_file():
                fonte_dados = FONTE_ORIGEM.read_bytes()
                for skin in sorted(set(skins_com_font)):
                    font_dest = "assets/addons/%s/fonts/%s" % (skin, FONTE_ARQUIVO)
                    if font_dest not in nomes:
                        extras[font_dest] = fonte_dados
                        dbg("Copiando fonte para %s" % font_dest)

            dbg("Extras a gravar: %d arquivos" % len(extras))
            for nome in sorted(extras):
                if nome in nomes:
                    dbg("Extra ja existe no APK, pulando: %s" % nome)
                    continue
                if nome == KEYMAP_DESTINO:
                    keymaps.append(nome)
                    dbg("%s: VOLTAR na Home reabre a tela" % nome)
                info = zipfile.ZipInfo(nome, date_time=(2026, 11, 16, 13, 44, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o644 << 16
                destino.writestr(info, extras[nome])
                dbg("Gravado extra: %s" % nome)

        dbg("Zip de saida gravado, validacao final")

        with zipfile.ZipFile(args.saida) as conferido:
            for nome, resumo in perfil.items():
                if hashlib.sha256(conferido.read(nome)).hexdigest() != resumo:
                    raise SystemExit("perfil semeado alterado: %s" % nome)
            dbg("Perfil validado: %d arquivos" % len(perfil))
            for nome in extras:
                if nome not in nomes and nome not in conferido.namelist():
                    raise SystemExit("arquivo da tela ausente: %s" % nome)
            dbg("Extras validados: %d arquivos" % len(extras))
            if not keymaps:
                dbg("Keymap ja existia ou nao foi adicionado (pulado)")

        dbg("APK com a tela: %s (%d entradas, %d arquivos novos, %d Startup.xml, "
            "%d Font.xml, %d perfil intacto)"
            % (args.saida, len(nomes) + len(extras), len(extras), len(startups),
               len(fontes_alteradas), len(perfil)))
    except SystemExit as erro:
        traceback.print_exc()
        print("ERRO_FATAL: %s" % erro, file=sys.stderr)
        sys.exit(1)
    except Exception as erro:
        traceback.print_exc()
        print("ERRO_FATAL: %s" % erro, file=sys.stderr)
        sys.exit(1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
