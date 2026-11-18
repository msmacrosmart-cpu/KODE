#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simula o boot do APK com a tela de entrada ANTES da Home.

Nao e um teste de interface: e a conferencia do encadeamento real que o Kodi
Omega 21.3 executa no boot, feito com stubs.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sqlite3
import sys
import tempfile
import traceback
import types
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON_ID = "script.smartedtv.welcome"
ADDON = ROOT / "kodi" / "addons" / ADDON_ID
SERVICO = "service.smarted.bootstrap"
LAYOUT = "resources/skins/Default/1080i/DialogWelcome.xml"
MEDIA = "resources/skins/Default/media"
DB_PERFIL = "assets/smarted/profile/userdata/Database/Addons33.db"


def dbg(msg):
    print("[DEBUG] %s" % msg, flush=True)


def conferir_startup(z):
    skins = sorted({n.split("/")[2] for n in z.namelist()
                    if re.fullmatch(r"assets/addons/[^/]+/xml/Startup\.xml", n)})
    if not skins:
        raise SystemExit("nenhuma skin do APK tem Startup.xml")
    for nome in skins:
        texto = z.read("assets/addons/%s/xml/Startup.xml" % nome).decode("utf-8")
        raiz = ET.fromstring(texto.encode("utf-8"))
        acoes = [(e.text or "").strip() for e in raiz.findall("onload")]
        disparo = [a for a in acoes if "smartedtv_entrada," in a]
        if len(disparo) != 1:
            raise SystemExit("Startup.xml %s: disparo invalido %r" % (nome, acoes))
        if "RunScript(%s)" % ADDON_ID not in disparo[0]:
            raise SystemExit("Startup.xml %s: sem RunScript do addon" % nome)
        homes = [a for a in acoes if "ReplaceWindow" in a]
        if homes:
            raise SystemExit("Startup.xml %s: tem ReplaceWindow %r" % (nome, homes))
        seguros = [a for a in acoes if "seguro=1" in a and "RunScript" in a]
        if len(seguros) != 1:
            raise SystemExit("Startup.xml %s: seguro invalido %r" % (nome, acoes))
        if seguros[0].startswith("RunScript(%s" % ADDON_ID) is False:
            raise SystemExit("Startup.xml %s: seguro nao e do addon" % nome)
        if acoes.index(disparo[0]) >= acoes.index(seguros[0]):
            raise SystemExit("Startup.xml %s: ordem errada %r" % (nome, acoes))
        # Ultimo recurso sem Python: se o addon da tela sumir, a Home abre.
        alarmes = [a for a in acoes if "smartedtv_home_seguro" in a]
        if len(alarmes) != 1 or "ActivateWindow(Home)" not in alarmes[0]:
            raise SystemExit("Startup.xml %s: sem alarme de seguro da Home %r"
                             % (nome, acoes))
        # A janela de startup tem de DESENHAR: vazia = tela preta no boot.
        controlls = raiz.findall("controls")
        if len(controlls) != 1:
            raise SystemExit("Startup.xml %s: %d <controls>"
                             % (nome, len(controlls)))
        labels = [(e.text or "").strip() for e in controlls[0].iter("label")]
        if "Carregando" not in labels:
            raise SystemExit("Startup.xml %s: janela de boot sem espera visivel"
                             % nome)
        if not [c for c in controlls[0].iter("control")
                if (c.findtext("texture") or "").endswith("pb_white.png")]:
            raise SystemExit("Startup.xml %s: janela de boot sem fundo" % nome)
        dbg("   %-26s dispara a tela; espera desenhada; seguro da Home" % nome)
    return skins


KEYMAP = "assets/system/keymaps/zzz-smartedtv-voltar.xml"


def conferir_keymap(z):
    if KEYMAP not in z.namelist():
        raise SystemExit("keymap de VOLTAR na Home ausente do APK")
    raiz = ET.fromstring(z.read(KEYMAP))
    janelas = [e.tag for e in raiz]
    if janelas != ["Home"]:
        raise SystemExit("keymap mexe em janelas alem da Home: %s" % janelas)
    casa = raiz.find("Home")
    acoes = [(e.text or "").strip() for e in casa.iter()
             if e is not casa and e.tag not in ("keyboard", "remote")]
    if not acoes:
        raise SystemExit("keymap da Home sem acao")
    for acao in acoes:
        if acao != "RunScript(%s,voltar)" % ADDON_ID:
            raise SystemExit("acao inesperada no keymap: %r" % acao)
    teclas = {e.tag for e in casa.find("keyboard")}
    if "backspace" not in teclas:
        raise SystemExit("keymap sem <backspace>: %r" % teclas)
    do_sistema = sorted(n for n in z.namelist()
                        if re.fullmatch(r"assets/system/keymaps/[^/]+\.xml", n))
    if do_sistema and do_sistema[-1] != KEYMAP:
        raise SystemExit("keymap nao e o ultimo: %s" % do_sistema[-3:])
    dbg("   %s: VOLTAR na Home reabre a tela (carregado por ultimo)" % KEYMAP.split("/")[-1])


def conferir_addon_habilitado(z):
    manifest = z.read("assets/system/addon-manifest.xml").decode("utf-8")
    ET.fromstring(manifest.encode("utf-8"))
    if ">%s<" % ADDON_ID not in manifest:
        raise SystemExit("addon da tela fora do addon-manifest.xml")
    linha = [l for l in manifest.splitlines() if ADDON_ID in l][0].strip()
    dbg("   manifest: %s" % linha)

    dados = z.read(DB_PERFIL)
    arquivo = tempfile.mktemp(suffix=".db")
    Path(arquivo).write_bytes(dados)
    try:
        con = sqlite3.connect(arquivo)
        linhas = list(con.execute(
            "SELECT addonID, enabled, origin FROM installed WHERE addonID = ?",
            (ADDON_ID,)))
        con.close()
    finally:
        os.unlink(arquivo)
    if linhas:
        raise SystemExit("perfil semeado ja tem linha para o addon: %r" % (linhas,))
    dbg("   %s: sem linha do addon -> nasce enabled=1" % DB_PERFIL)

    addon_xml = ET.fromstring(z.read("assets/addons/%s/addon.xml" % ADDON_ID))
    pontos = [e.get("point") for e in addon_xml.findall("extension")]
    if "xbmc.python.script" not in pontos:
        raise SystemExit("addon.xml sem xbmc.python.script: %s" % pontos)
    lib = [e.get("library") for e in addon_xml.findall("extension")
           if e.get("point") == "xbmc.python.script"][0]
    if ("assets/addons/%s/%s" % (ADDON_ID, lib)) not in z.namelist():
        raise SystemExit("addon.xml: biblioteca %s ausente" % lib)
    dbg("   addon.xml: xbmc.python.script -> %s" % lib)


def recursos_do_layout(raiz):
    texturas, fontes = set(), set()
    for no in raiz.iter():
        if no.tag in ("texture", "texturefocus", "texturenofocus"):
            nome = (no.text or "").strip()
            if nome:
                texturas.add(nome)
        elif no.tag == "font":
            nome = (no.text or "").strip()
            if nome:
                fontes.add(nome)
    return texturas, fontes


def conferir_recursos(z, skin):
    raiz = ET.fromstring(z.read("assets/addons/%s/%s" % (ADDON_ID, LAYOUT)))
    texturas, fontes = recursos_do_layout(raiz)
    caixa = raiz.find("controls")
    if caixa is None:
        raise SystemExit("layout sem <controls>")
    fundo = raiz.find(".//control[@id='1']")
    if fundo is None:
        raise SystemExit("layout sem controle de fundo id=1")
    largura = int(fundo.find("width").text)
    altura = int(fundo.find("height").text)
    if (largura, altura) != (1920, 1080):
        raise SystemExit("layout nao e 1920x1080: %sx%s" % (largura, altura))

    presentes = {n.rsplit("/", 1)[-1] for n in z.namelist()
                 if n.startswith("assets/addons/%s/%s/" % (ADDON_ID, MEDIA))}
    ausentes = sorted(t for t in texturas if t not in presentes)
    if ausentes:
        raise SystemExit("textura ausente no addon: %r" % ausentes)
    dbg("   texturas do layout (%d): todas em %s/" % (len(texturas), MEDIA))

    font_xml = z.read("assets/addons/%s/xml/Font.xml" % skin).decode("utf-8")
    declaradas = set(re.findall(r"<name>([^<]+)</name>", font_xml))
    sem_fonte = sorted(f for f in fontes if f not in declaradas)
    if sem_fonte:
        raise SystemExit("%s sem as fontes %r" % (skin, sem_fonte))
    dbg("   fontes do layout (%d): declaradas em %s/xml/Font.xml" % (len(fontes), skin))


class Simulacao(object):
    def __init__(self, apk):
        self.apk = apk
        self.builtins = []
        self.logs = []
        self.properties = {}
        self.foco = []
        self.janela = None
        self.home_durante_modal = []
        self.modal_ativo = False
        self.interacao = None
        self.vip = None
        self.relogio = 0.0
        self.janela_atual = "Startup"

    def log(self, mensagem, nivel=1):
        self.logs.append(mensagem)

    def dormir(self, ms):
        self.relogio += (ms or 0) / 1000.0

    def builtin(self, comando, *args, **kwargs):
        self.builtins.append(comando)
        if self.modal_ativo and "ReplaceWindow" in comando:
            self.home_durante_modal.append(comando)
        if comando.startswith("ReplaceWindow("):
            alvo = comando[len("ReplaceWindow("):-1]
            if alvo == "$INFO[System.StartupWindow]":
                alvo = "Startup" if self.janela_atual == "Startup" else "Home"
            self.janela_atual = alvo
        elif comando.startswith("ActivateWindow(Home"):
            self.janela_atual = "Home"
        elif comando.startswith("RestartApp"):
            self.janela_atual = "Startup"


class VipFalso(object):
    CHECKOUT = "https://pay.cakto.com.br/nkvbegd_1323120"
    DROPBOX_URL = ("https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/"
                   "SMARTEDTV-atual.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j"
                   "&st=p1m6ebvg&dl=0")
    APK = DROPBOX_URL.replace("&dl=0", "&dl=1")
    APK_GITHUB = ("https://github.com/msmacrosmart-cpu/KODE/releases/latest/"
                  "download/SMARTEDTV-atual.apk")

    def __init__(self, sim):
        self.sim = sim
        self.chamadas = []
        self.codigos = []

    def ativa(self):
        return False

    def estado(self):
        return {}

    def validar(self, codigo):
        self.codigos.append(codigo)
        return (True, "VIP ativado ate 2026-12-31.")

    def abrir_checkout(self):
        self.chamadas.append("checkout")
        return True

    def abrir_dropbox(self):
        self.chamadas.append("dropbox")
        return True

    def compartilhar(self, texto=None):
        self.chamadas.append("compartilhar")
        return True

    def open_apk_download(self):
        self.chamadas.append("apk")
        return True

    def abrir_url(self, url, rotulo=None):
        self.chamadas.append("apk" if "APK" in (rotulo or "").upper() or
                             "apk" in (url or "").lower() else "url")
        return True

    def procurar_atualizacao(self):
        self.chamadas.append("atualizar")
        return True


def criar_modulos(sim, raiz_addon, raiz_servico):
    xbmc = types.ModuleType("xbmc")
    xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
    xbmc.log = sim.log
    xbmc.executebuiltin = sim.builtin
    sim.janela_atual = "Startup"
    xbmc.getInfoLabel = lambda exp: (sim.janela_atual
                                     if exp == "System.CurrentWindow" else "")
    xbmc.getCondVisibility = lambda cond: True
    xbmc.sleep = lambda ms: sim.dormir(ms)

    class Monitor(object):
        def abortRequested(self):
            return False

        def waitForAbort(self, segundos):
            return False

    xbmc.Monitor = Monitor

    xbmcaddon = types.ModuleType("xbmcaddon")

    class Addon(object):
        def __init__(self, ident=None):
            self.ident = ident

        def getAddonInfo(self, chave):
            if chave != "path":
                return ""
            if self.ident == SERVICO:
                return str(raiz_servico)
            return str(raiz_addon)

    xbmcaddon.Addon = Addon

    xbmcvfs = types.ModuleType("xbmcvfs")
    xbmcvfs.translatePath = lambda p: p
    xbmcvfs.exists = lambda p: Path(p).exists()

    xbmcgui = types.ModuleType("xbmcgui")
    xbmcgui.ACTION_NAV_BACK = 92
    xbmcgui.ACTION_PREVIOUS_MENU = 10
    xbmcgui.INPUT_ALPHANUM = 0
    xbmcgui.NOTIFICATION_INFO = 0

    class Janela(object):
        def __init__(self, *args, **kwargs):
            pass

        def setProperty(self, chave, valor):
            sim.properties[chave] = valor

    class Dialog(object):
        def ok(self, *args):
            sim.log("dialog.ok: %r" % (args,))

        def notification(self, *args):
            sim.log("dialog.notification: %r" % (args,))

        def input(self, *args, **kwargs):
            return ""

    class WindowXMLDialog(object):
        def __init__(self, xml_filename, script_path, default_skin, resolution):
            self.xml_filename = xml_filename
            self.script_path = script_path
            self.default_skin = default_skin
            self.resolution = resolution
            self.props = {}
            self.fechada = False
            sim.janela = self

        def setProperty(self, chave, valor):
            self.props[chave] = valor

        def clearProperty(self, chave):
            self.props.pop(chave, None)

        def getProperty(self, chave):
            return self.props.get(chave, "")

        def setFocusId(self, controle):
            sim.foco.append(controle)

        def getFocusId(self):
            return sim.foco[-1] if sim.foco else 0

        def getControl(self, controle):
            if controle == 310:
                campo = types.SimpleNamespace()
                campo.getText = lambda: self.props.get("_codigo", "")
                return campo
            return types.SimpleNamespace()

        def close(self):
            self.fechada = True
            sim.modal_ativo = False

        def doModal(self):
            self.onInit()
            sim.modal_ativo = True
            try:
                if sim.interacao is not None:
                    sim.interacao(self)
            finally:
                if not self.fechada:
                    self.close()

    xbmcgui.Window = Janela
    xbmcgui.Dialog = Dialog
    xbmcgui.WindowXMLDialog = WindowXMLDialog
    return {"xbmc": xbmc, "xbmcgui": xbmcgui, "xbmcaddon": xbmcaddon,
            "xbmcvfs": xbmcvfs}


def carregar_default(sim, raiz_addon, raiz_servico):
    modulos = criar_modulos(sim, raiz_addon, raiz_servico)
    salvos = {nome: sys.modules.get(nome) for nome in modulos}
    salvos[SERVICO] = sys.modules.get("vip")
    vip = VipFalso(sim)
    sys.modules.update(modulos)
    sys.modules["vip"] = vip
    sim.vip = vip
    spec = importlib.util.spec_from_file_location(
        "welcome_sim", raiz_addon / "default.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo._modulos_salvos = salvos
    return modulo


def restaurar_modulos(modulo):
    for nome, antigo in getattr(modulo, "_modulos_salvos", {}).items():
        if antigo is None:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = antigo


def conferir_execucao(sim, modulo, codigo_vip="SMARTED-1234"):
    assert modulo._pasta_da_tela() == str(ADDON), modulo._pasta_da_tela()
    dbg("   pasta da tela: %s" % modulo._pasta_da_tela())
    if modulo._pasta_do_servico() is None:
        raise SystemExit("servico VIP nao encontrado")

    def interacao(janela):
        assert (janela.xml_filename, janela.default_skin, janela.resolution) == (
            "DialogWelcome.xml", "Default", "1080i"), (janela.xml_filename,
                                                       janela.default_skin,
                                                       janela.resolution)
        if not sim.foco or sim.foco[0] != 310:
            raise SystemExit("foco nao esta no campo 310: %r" % sim.foco)
        if sim.properties.get("smartedtv.welcome.ativa") != "1":
            raise SystemExit("vigia nao foi avisado: %r" % sim.properties)
        dbg("   abriu 1080i, foco no campo 310, vigia avisado")

        janela.props["_codigo"] = codigo_vip
        janela.onClick(311)
        if sim.vip.codigos != [codigo_vip]:
            raise SystemExit("vip.codigos inesperado: %r" % sim.vip.codigos)
        if janela.getProperty("welcome_dialog") != "status":
            raise SystemExit("dialogo nao abriu: %r" % janela.props)
        dbg("   311 -> vip.validar(%r) OK, aviso na tela" % codigo_vip)
        janela.onClick(955)
        if janela.getProperty("welcome_dialog") != "":
            raise SystemExit("dialogo nao fechou: %r" % janela.props)

        janela.onClick(120)
        janela.onClick(121)
        janela.onClick(122)
        janela.onClick(123)
        esperado = ["checkout", "dropbox", "apk", "atualizar"]
        if sim.vip.chamadas != esperado:
            raise SystemExit("chamadas inesperadas: %r" % sim.vip.chamadas)
        dbg("   120 -> checkout; 121 -> Dropbox; 122 -> baixar APK; "
            "123 -> atualizar OK")

        antes = list(sim.vip.chamadas)
        for removido in (130, 131, 140, 141):
            janela.onClick(removido)
        if sim.vip.chamadas != antes:
            raise SystemExit("botoes removidos tiveram efeito: %r" % sim.vip.chamadas)
        if janela.getProperty("welcome_dialog") != "":
            raise SystemExit("dialogo nao esta vazio: %r" % janela.props)
        dbg("   130/131/140/141 (removidos) -> nenhum efeito OK")

        janela.onClick(312)
        if janela.getProperty("welcome_dialog") != "ads":
            raise SystemExit("dialogo ads nao abriu: %r" % janela.props)
        janela.onClick(905)
        if janela.getProperty("welcome_dialog") != "":
            raise SystemExit("dialogo nao fechou com 905: %r" % janela.props)
        janela.onClick(312)
        dbg("   312 -> modal de confirmacao (905 volta, 906 confirma) OK")

        if sim.home_durante_modal:
            raise SystemExit("comando para a Home durante a modal: %r" %
                             sim.home_durante_modal)
        if sim.janela_atual != "Startup":
            raise SystemExit("janela nao e Startup: %r" % sim.janela_atual)
        dbg("   durante a tela: nenhum comando de janela para a Home")

        janela.onClick(906)
        if not janela.fechada:
            raise SystemExit("janela nao fechou com 906")

    sim.interacao = interacao
    abriu = modulo.abrir_tela_entrada()
    if not abriu or sim.janela is None:
        raise SystemExit("abrir_tela_entrada retornou False")
    if sim.janela_atual != "Home":
        raise SystemExit(
            "tela preta: apos sair da tela a janela e %r" % sim.janela_atual)
    if "ActivateWindow(Home)" not in sim.builtins:
        raise SystemExit("ActivateWindow(Home) nao chamado: %r"
                         % sim.builtins)
    if sim.properties.get("smartedtv.welcome.home") != "ok":
        raise SystemExit("marca home nao e ok: %r" % sim.properties)
    dbg("   906 -> Home aberta SOMENTE depois de a tela sair de cena")

    # Voltar na Home
    sim_volta = Simulacao(sim.apk)
    modulo_volta = carregar_default(sim_volta, ADDON,
                                    ROOT / "kodi" / "addons" / SERVICO)

    def so_voltar(janela):
        janela.onAction(92)

    sim_volta.interacao = so_voltar
    if modulo_volta.abrir_tela_entrada() is not True:
        raise SystemExit("voltar_para_a_tela retornou False")
    if sim_volta.janela_atual != "Home":
        raise SystemExit("voltar: janela nao e Home: %r" % sim_volta.janela_atual)
    restaurar_modulos(modulo_volta)
    dbg("   Voltar -> Home aberta tambem")

    # Caminho de falha
    sim2 = Simulacao(sim.apk)
    modulo2 = carregar_default(sim2, ADDON, ROOT / "kodi" / "addons" / SERVICO)
    modulo2._pasta_da_tela = lambda: None
    if modulo2.abrir_tela_entrada() is not False:
        raise SystemExit("abrir_tela_entrada deveria retornar False")
    if sim2.janela_atual != "Home":
        raise SystemExit("falha: janela nao e Home: %r" % sim2.janela_atual)
    restaurar_modulos(modulo2)
    dbg("   falha na tela -> Home abre mesmo assim")

    # Vigia
    sim3 = Simulacao(sim.apk)
    modulo3 = carregar_default(sim3, ADDON, ROOT / "kodi" / "addons" / SERVICO)
    sim3.interacao = None
    modulo3.abrir_tela_entrada = lambda: False
    modulo3.vigiar_inicializacao()
    if sim3.janela_atual != "Home":
        raise SystemExit("vigia: janela nao e Home: %r" % sim3.janela_atual)
    restaurar_modulos(modulo3)
    dbg("   vigia: tela nao desenhou -> Home aberta em 8s")

    # VOLTAR ja na Home
    sim4 = Simulacao(sim.apk)
    modulo4 = carregar_default(sim4, ADDON, ROOT / "kodi" / "addons" / SERVICO)
    sim4.janela_atual = "Home"
    vistas = []

    def interacao_voltar(janela):
        vistas.append(janela.xml_filename)
        if sim4.janela_atual != "Home":
            raise SystemExit("voltar: janela nao e Home durante interacao")
        if janela.props.get("_codigo", "") != "":
            raise SystemExit("voltar: campo nao esta vazio")
        janela.onClick(312)
        janela.onClick(906)
        vistas.append(sim4.janela_atual)

    sim4.interacao = interacao_voltar
    if modulo4.voltar_para_a_tela() is not True:
        raise SystemExit("voltar_para_a_tela retornou False")
    if vistas != ["DialogWelcome.xml", "Home"]:
        raise SystemExit("voltar: vistas inesperadas %r" % vistas)
    if any(b.startswith("RestartApp") for b in sim4.builtins):
        raise SystemExit("voltar: RestartApp chamado: %r" % sim4.builtins)
    if any(b.startswith("ReplaceWindow") for b in sim4.builtins):
        raise SystemExit("voltar: ReplaceWindow chamado: %r" % sim4.builtins)
    restaurar_modulos(modulo4)
    dbg("   VOLTAR na Home -> tela reaberta sobre a Home, sem reiniciar")

    dbg("\nOK: a tela abre antes da Home, usa os fluxos que ja existem no app")
    dbg("    e a Home so e aberta quando a tela sai de cena.")
    dbg("    VOLTAR na Home reabre a tela para quem tem codigo.")
    dbg("    (Simulacao com stubs: nao substitui um teste em Kodi real.)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True,
                        help="APK com a tela injetada (build_test/bruto.apk)")
    args = parser.parse_args(argv)

    try:
        with zipfile.ZipFile(args.apk) as z:
            dbg("1. Startup.xml de cada skin")
            skins = conferir_startup(z)

            dbg("1b. Keymap de VOLTAR na Home")
            conferir_keymap(z)

            dbg("2. Addon da tela habilitado no boot")
            conferir_addon_habilitado(z)

            dbg("3. Recursos do DialogWelcome.xml (1920x1080)")
            for skin in skins:
                if "assets/addons/%s/xml/Font.xml" % skin not in z.namelist():
                    dbg("   %s: sem Font.xml, ignorada" % skin)
                    continue
                conferir_recursos(z, skin)

        dbg("4. Execucao da tela (stubs do Kodi)")
        sim = Simulacao(args.apk)
        modulo = carregar_default(sim, ADDON,
                                  ROOT / "kodi" / "addons" / SERVICO)
        conferir_execucao(sim, modulo)
        restaurar_modulos(modulo)
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
