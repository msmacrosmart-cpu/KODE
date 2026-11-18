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
SERVICO_DIR = ROOT / "kodi" / "addons" / "service.smarted.bootstrap"
VIP_MODULO = "assets/addons/service.smarted.bootstrap/vip.py"
SMART_ADS_MODULO = "assets/addons/service.smarted.bootstrap/smart_ads.py"
RELEASE_MODULO = "assets/addons/service.smarted.bootstrap/smarted_release.py"
MODULOS_SUBSTITUIDOS = (VIP_MODULO, SMART_ADS_MODULO, RELEASE_MODULO)
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

# O Startup.xml tambem DESENHA uma espera (fundo + marca + "Carregando"):
# janela de startup vazia = tela preta enquanto o Python/addons sobem. O
# terceiro alarme (smartedtv_home_seguro) e o ultimo recurso do proprio Kodi:
# se o addon da tela estiver desabilitado/corrompido, a Home abre em 25 s.
STARTUP_NOVO = (
    "<onload>AlarmClock(smartedtv_entrada,"
    "RunScript(script.smartedtv.welcome),00:00:00,silent)</onload>\n"
    "\t<onload>RunScript(script.smartedtv.welcome,seguro=1)</onload>\n"
    "\t<onload>AlarmClock(smartedtv_home_seguro,ActivateWindow(Home),"
    "00:00:25,silent)</onload>\n"
    "\t<controls>\n"
    "\t\t<control type=\"image\"><left>0</left><top>0</top>"
    "<width>100%</width><height>100%</height>"
    "<texture colordiffuse=\"pb_dark\">pb_white.png</texture></control>\n"
    "\t\t<control type=\"label\"><left>0</left><top>470</top>"
    "<width>100%</width><height>56</height><font>font13</font>"
    "<textcolor>pb_white</textcolor><align>center</align>"
    "<aligny>center</aligny><label>SMARTEDTV</label></control>\n"
    "\t\t<control type=\"label\"><left>0</left><top>534</top>"
    "<width>100%</width><height>36</height><font>font12</font>"
    "<textcolor>pb_muted</textcolor><align>center</align>"
    "<aligny>center</aligny><label>Carregando</label></control>\n"
    "\t</controls>")


def _espera_controls():
    """Bloco <controls> da espera (usado em toda skin)."""
    corpo = STARTUP_NOVO.split("<controls>", 1)[1]
    if not corpo.rstrip().endswith("</controls>"):
        raise SystemExit("Startup.xml: espera sem </controls>")
    return "<controls>" + corpo.rstrip()[:-len("</controls>")] + "</controls>"


def _com_espera(texto):
    """Deixa um unico <controls> (o da espera) e devolve o novo XML."""
    corpo = _espera_controls()
    # Os <onload> novos entram no lugar do salto antigo; o <controls> antigo
    # (vazio, self-closing ou com conteudo da skin) e trocado pelo da espera.
    achado = re.search(r"<controls\b[^>]*/>|<controls\b[^>]*>.*?</controls>",
                       texto, re.DOTALL)
    if achado:
        return texto[:achado.start()] + corpo + texto[achado.end():]
    return texto.replace("</window>", "\t" + corpo + "\n</window>", 1)


def patch_startup(dados):
    """Troca o salto direto para a Home pelo disparo da tela de entrada.

    Vale para TODA skin do APK, inclusive a reserva (skin.estuary). Se a skin
    padrao ficasse com o `ReplaceWindow($INFO[System.StartupWindow])` antigo e
    fosse ativada por algum perfil antigo, o app abriria no preto: hoje o
    simulador de boot exige o Startup.xml novo em todas as skins.
    """
    texto = dados.decode("utf-8")
    if "smartedtv_entrada" in texto:
        dbg("patch_startup: ja tem smartedtv_entrada, pulando")
        validar_startup(dados)
        return dados
    # Os <onload> da espera entram no lugar do salto antigo.
    so_onloads = STARTUP_NOVO.split("<controls>", 1)[0].rstrip()
    padroes = [
        r"<onload[^>]*>\s*ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)\s*</onload>",
        r"<onload\s*/>\s*ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)",
        r"ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)",
    ]
    for i, padrao in enumerate(padroes):
        alvos = re.findall(padrao, texto, re.DOTALL)
        dbg("patch_startup: padrao %d -> %d alvos" % (i, len(alvos)))
        if len(alvos) != 1:
            continue
        novo = _com_espera(texto.replace(alvos[0], so_onloads, 1))
        validar_startup(novo.encode("utf-8"))
        return novo.encode("utf-8")
    raise SystemExit("Startup.xml fora do formato esperado (sem ReplaceWindow)")


def validar_startup(dados):
    """Confere o Startup.xml que vai ao APK. Levanta SystemExit se faltar algo.

    Regras (as mesmas do simulador de boot e do teste unitario):
    * exatamente um disparo da tela e um vigia `seguro=1`, nessa ordem;
    * nenhum ReplaceWindow do StartupWindow (era a tela preta do boot);
    * um unico <controls>, com espera DESENHADA: fundo e o aviso "Carregando";
    * alarme de seguranca do proprio Kodi (`smartedtv_home_seguro`).
    """
    raiz = ET.fromstring(dados)
    if raiz.tag != "window":
        raise SystemExit("Startup.xml sem <window>")
    acoes = [(e.text or "").strip() for e in raiz.findall("onload")]
    disparo = [a for a in acoes if "smartedtv_entrada," in a]
    if len(disparo) != 1:
        raise SystemExit("Startup.xml: disparo da tela invalido %r" % acoes)
    seguros = [a for a in acoes if "seguro=1" in a and "RunScript" in a]
    if len(seguros) != 1:
        raise SystemExit("Startup.xml: vigia do boot invalido %r" % acoes)
    if [a for a in acoes if "ReplaceWindow" in a]:
        raise SystemExit("Startup.xml: ReplaceWindow do startup nao pode voltar")
    alarmes = [a for a in acoes if "smartedtv_home_seguro" in a]
    if len(alarmes) != 1:
        raise SystemExit("Startup.xml: sem alarme de seguranca para a Home")
    controles = raiz.findall("controls")
    if len(controles) != 1:
        raise SystemExit("Startup.xml: precisa de exatamente um <controls>")
    labels = [(e.text or "").strip() for e in controles[0].iter("label")]
    if "Carregando" not in labels:
        raise SystemExit("Startup.xml: janela de boot sem a espera 'Carregando'")
    fundo = [e for e in controles[0].iter("control")
             if (e.findtext("texture") or "").strip().endswith("pb_white.png")]
    if not fundo:
        raise SystemExit("Startup.xml: janela de boot sem fundo (tela preta)")
    return True


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
    for modulo in MODULOS_SUBSTITUIDOS:
        caminho = ROOT / modulo.replace("assets/addons/", "kodi/addons/")
        if caminho.is_file():
            extras[modulo] = caminho.read_bytes()

    startups, fontes_alteradas, keymaps = [], [], []
    skins_com_font = []

    try:
        with zipfile.ZipFile(args.apk) as origem, \
                zipfile.ZipFile(args.saida, "w", allowZip64=True) as destino:
            nomes = set()
            perfil = {}
            _origem = set(origem.namelist())
            if ADDON_PREFIX + "default.py" in _origem:
                raise SystemExit("APK base ja tinha a tela: %s" % ADDON_PREFIX)
            if "assets/addons/service.smarted.bootstrap/service.py" not in _origem:
                raise SystemExit("APK base sem "
                                 "assets/addons/service.smarted.bootstrap/service.py")
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
                    elif item.filename in MODULOS_SUBSTITUIDOS:
                        # O APK base tem copias antigas de vip.py/smart_ads.py
                        # (com a classe errada do anuncio e a validacao antiga).
                        # Elas NAO sao copiadas: as versoes do repositorio entram
                        # no fim e substituem as antigas.
                        dbg("%s do APK base sera substituido pela versao do "
                            "repositorio" % item.filename.rsplit("/", 1)[-1])
                        continue
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
                            # Skin que nao segue o formato do Startup.xml: o
                            # build nao publica. O log mostra o motivo real.
                            dbg("patch_startup FALHOU em %s: %s"
                                % (item.filename, e))
                            raise SystemExit("%s: %s" % (item.filename, e))
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
                if nome in nomes and nome not in MODULOS_SUBSTITUIDOS:
                    dbg("Extra ja existe no APK, pulando: %s" % nome)
                    continue
                if nome in MODULOS_SUBSTITUIDOS and nome in nomes:
                    dbg("%s: substituindo a versao antiga do APK base"
                        % nome.rsplit("/", 1)[-1])
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
            for modulo in MODULOS_SUBSTITUIDOS:
                if modulo in extras:
                    if conferido.read(modulo) != extras[modulo]:
                        raise SystemExit("%s do APK difere do repositorio" % modulo)
                    dbg("%s validado byte a byte com o repositorio"
                        % modulo.rsplit("/", 1)[-1])
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
        # preserva a mensagem para os testes/CI (o codigo de saida continua != 0)
        sys.exit(str(erro) or 1)
    except Exception as erro:
        traceback.print_exc()
        print("ERRO_FATAL: %s" % erro, file=sys.stderr)
        sys.exit(str(erro) or 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
