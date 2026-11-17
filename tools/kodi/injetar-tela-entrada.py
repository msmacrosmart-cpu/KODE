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
   ``RunScript(<id>)`` do Startup.xml funcionar;
5. ``assets/system/keymaps/zzz-smartedtv-voltar.xml`` — VOLTAR na Home reabre a
   tela de entrada (``RunScript(script.smartedtv.welcome,voltar)``). O prefixo
   ``zzz-`` poe o arquivo por ultimo na ordem alfabetica que o Kodi usa, entao
   nenhum keymap do app sobrescreve essa secao.

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
# Keymap de VOLTAR na Home (ver kodi/keymaps/smartedtv-voltar.xml). O diretorio
# tem de ser assets/system/keymaps: e o special://xbmc/system/keymaps/ do motor.
KEYMAP_ORIGEM = ROOT / "kodi" / "keymaps" / "smartedtv-voltar.xml"
KEYMAP_DESTINO = "assets/system/keymaps/zzz-smartedtv-voltar.xml"
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
    "\t<onload>RunScript(script.smartedtv.welcome,seguro=1)</onload>")


def validar_publicacao(dados: bytes) -> None:
    """Recusa um Startup.xml que carregue a Home antes da tela.

    O Startup.xml NAO pode ter ReplaceWindow nenhum: ele dispara a tela e o
    seguro; quem abre a Home e o proprio addon (depois de a tela sair de cena).
    Um ReplaceWindow aqui apontaria de volta para a janela de startup, que ja
    saiu de cena no instante do disparo — o resultado seria tela preta.
    """
    texto = dados.decode("utf-8")
    if "smartedtv_entrada," not in texto:
        raise SystemExit("Startup.xml sem o disparo da tela de entrada")
    if "ReplaceWindow" in texto:
        raise SystemExit("Startup.xml com ReplaceWindow: a Home e aberta pelo addon")
    if "RunScript(script.smartedtv.welcome,seguro=1)" not in texto:
        raise SystemExit("Startup.xml sem o seguro de inicializacao da tela")
    ET.fromstring(texto.encode("utf-8"))


def extrair_keymap() -> dict:
    """Keymap que faz VOLTAR (na Home) reabrir a tela de entrada."""
    if not KEYMAP_ORIGEM.is_file():
        raise SystemExit("keymap ausente: %s" % KEYMAP_ORIGEM)
    dados = KEYMAP_ORIGEM.read_bytes()
    validar_keymap(dados)
    return {KEYMAP_DESTINO: dados}


def validar_keymap(dados: bytes) -> None:
    """Confere o contrato: so <Home>, e VOLTAR chamando o addon da tela."""
    texto = dados.decode("utf-8")
    raiz = ET.fromstring(texto.encode("utf-8"))
    if raiz.tag != "keymap":
        raise SystemExit("keymap sem <keymap>")
    janelas = [e.tag for e in raiz]
    if janelas != ["Home"]:
        raise SystemExit("keymap mexe em janelas alem da Home: %s" % janelas)
    casa = raiz.find("Home")
    dispositivos = ("keyboard", "remote", "mouse", "gamepad", "joystick")
    acoes = [(e.text or "").strip() for e in casa.iter()
             if e is not casa and e.tag not in dispositivos]
    if not acoes:
        raise SystemExit("keymap da Home sem acao")
    for acao in acoes:
        if acao != "RunScript(%s,voltar)" % ADDON_ID:
            raise SystemExit("acao inesperada no keymap: %r" % acao)
    teclas = [e.tag for e in casa.find("keyboard")]
    # KEYCODE_BACK do Android chega ao Kodi como XBMCK_BACKSPACE
    if "backspace" not in teclas:
        raise SystemExit("keymap sem <backspace> (o VOLTAR do Android)")


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
        # as fontes ja estao declaradas nesta skin: nada a corrigir
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
    extras.update(extrair_keymap())
    # vip.py: modulo de licenca que faz os botoes da tela funcionarem
    vip_path = ROOT / "kodi" / "addons" / "service.smarted.bootstrap" / "vip.py"
    if vip_path.is_file():
        extras[VIP_MODULO] = vip_path.read_bytes()
    startups, fontes_alteradas, keymaps = [], [], []
    skins_com_font = []  # skins que tiveram Font.xml processado

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
                if item.filename.startswith("assets/system/keymaps/"):
                    # o app pode ja ter keymap com este nome: recusa em vez de
                    # sobrescrever (o nosso entra como arquivo novo)
                    if item.filename == KEYMAP_DESTINO:
                        raise SystemExit("APK ja tem %s" % KEYMAP_DESTINO)
                if re.fullmatch(r"assets/addons/[^/]+/xml/Startup\.xml", item.filename):
                    dados = patch_startup(dados)
                    startups.append(item.filename)
                    print("  %s: abre a tela antes da Home" % item.filename)
                m = re.fullmatch(r"assets/addons/([^/]+)/xml/Font\.xml", item.filename)
                if m:
                    dados, adicionadas = patch_fonts(dados)
                    fontes_alteradas.append(item.filename)
                    skins_com_font.append(m.group(1))
                    print("  %s: %s declaradas"
                          % (item.filename, "/".join(adicionadas)))
            info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            info.compress_type = item.compress_type
            info.external_attr = item.external_attr
            info.comment = item.comment
            destino.writestr(info, dados)

        if MANIFEST not in nomes:
            raise SystemExit("APK atual sem %s" % MANIFEST)
        if not perfil:
            raise SystemExit("APK atual sem perfil semeado (assets/smarted/profile/)")
        if not startups:
            raise SystemExit("nenhum Startup.xml de skin encontrado no APK")
        if not fontes_alteradas:
            raise SystemExit("nenhum Font.xml de skin encontrado no APK")

        # Garante que o arquivo de fonte referenciado pelo Font.xml (NotoSans-
        # Regular.ttf) exista na pasta fonts/ de cada skin. O simulador confere
        # que o .ttf declarado realmente esta no APK; sem ele o Kodi cai em
        # font13 e a tela fica fora de escala.
        FONTE_ORIGEM = ROOT / "kodi" / "skin.estilo.personalizado" / "fonts" / FONTE_ARQUIVO
        if FONTE_ORIGEM.is_file():
            fonte_dados = FONTE_ORIGEM.read_bytes()
            for skin in sorted(set(skins_com_font)):
                font_dest = "assets/addons/%s/fonts/%s" % (skin, FONTE_ARQUIVO)
                if font_dest not in nomes:
                    extras[font_dest] = fonte_dados

        for nome, dados in extras.items():
            if nome in nomes:
                raise SystemExit("arquivo ja presente no APK: %s" % nome)
            if nome == KEYMAP_DESTINO:
                keymaps.append(nome)
                print("  %s: VOLTAR na Home reabre a tela" % nome)
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
        if not keymaps:
            raise SystemExit("keymap de VOLTAR na Home nao entrou no APK")
        validar_keymap(conferido.read(KEYMAP_DESTINO))

    print("APK com a tela: %s (%d entradas, %d arquivos novos, %d Startup.xml, "
          "%d Font.xml, %d keymap, perfil intacto)"
          % (args.saida, len(nomes) + len(extras), len(extras), len(startups),
             len(fontes_alteradas), len(keymaps)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
