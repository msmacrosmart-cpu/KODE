#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simula o boot do APK com a tela de entrada ANTES da Home.

Nao e um teste de interface: e a conferencia do encadeamento real que o Kodi
Omega 21.3 executa no boot, feito com stubs. Para cada etapa, o que este script
verifica e o que o codigo do Kodi faz (arquivos citados no comentario):

1. ``Startup.xml`` de cada skin do APK dispara a tela e NAO vai para a Home.
   Kodi: ``CSkinInfo::GetFirstWindow`` devolve ``WINDOW_STARTUP_ANIM`` quando a
   skin tem ``Startup.xml``; ``CApplication::Initialize`` ativa essa janela no
   lugar da Home.
2. O addon da tela esta no ``addon-manifest.xml`` e NAO tem linha no
   ``Addons33.db`` semeado — por isso ``CAddonDatabase::SyncInstalled`` insere a
   linha com ``enabled=1`` e o ``RunScript(<id>)`` do Startup.xml resolve
   (``CAddonMgr::GetAddon(..., OnlyEnabled::CHOICE_YES)``).
3. Texturas e fontes do ``DialogWelcome.xml`` existem na skin ativa, no
   conjunto de fontes do proprio addon ou no Font.xml da skin (o injetor
   declara font20/22/24/30).
4. O ``default.py`` roda com o dialogo do ZIP e, durante todo o periodo em que a
   janela esta na tela, NENHUM comando vai para a Home: o ``ReplaceWindow`` so
   acontece depois que ``doModal`` retorna.
5. Os botoes chamam o que ja existe no app (``vip.py``): 311 valida o codigo,
   120 abre o checkout, 121 compartilha, 312->906 abre a Home.

Uso:
    python3 tools/kodi/simular-boot-tela-entrada.py --apk build_test/bruto.apk
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sqlite3
import sys
import tempfile
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
HOME = "ReplaceWindow($INFO[System.StartupWindow])"
DB_PERFIL = "assets/smarted/profile/userdata/Database/Addons33.db"


# --------------------------------------------------------------------------
# 1. Startup.xml: a tela vem antes da Home
# --------------------------------------------------------------------------
def conferir_startup(z: zipfile.ZipFile) -> list:
    skins = sorted({n.split("/")[2] for n in z.namelist()
                    if re.fullmatch(r"assets/addons/[^/]+/xml/Startup\.xml", n)})
    assert skins, "nenhuma skin do APK tem Startup.xml"
    for nome in skins:
        texto = z.read("assets/addons/%s/xml/Startup.xml" % nome).decode("utf-8")
        raiz = ET.fromstring(texto.encode("utf-8"))
        acoes = [(e.text or "").strip() for e in raiz.findall("onload")]
        disparo = [a for a in acoes if "smartedtv_entrada," in a]
        assert len(disparo) == 1, (nome, acoes)
        assert "RunScript(%s)" % ADDON_ID in disparo[0], (nome, disparo)
        # nenhuma acao solta na Home: o unico ReplaceWindow e o seguro
        homes = [a for a in acoes if "ReplaceWindow" in a]
        assert not homes, (nome, homes)   # Startup.xml nao abre a Home: o addon abre
        seguros = [a for a in acoes if "seguro=1" in a and "RunScript" in a]
        assert len(seguros) == 1, (nome, acoes)
        assert seguros[0].startswith("RunScript(%s" % ADDON_ID), seguros
        assert acoes.index(disparo[0]) < acoes.index(seguros[0]), (nome, acoes)
        print("   %-26s dispara a tela; vigia proprio (sem ReplaceWindow)"
              % nome)
    return skins


# --------------------------------------------------------------------------
# 1b. Keymap: VOLTAR na Home reabre a tela de entrada
# --------------------------------------------------------------------------
KEYMAP = "assets/system/keymaps/zzz-smartedtv-voltar.xml"


def conferir_keymap(z: zipfile.ZipFile) -> None:
    """Sem esta secao <Home>, quem entra so para ver nao volta para o codigo."""
    assert KEYMAP in z.namelist(), "keymap de VOLTAR na Home ausente do APK"
    raiz = ET.fromstring(z.read(KEYMAP))
    janelas = [e.tag for e in raiz]
    assert janelas == ["Home"], janelas
    casa = raiz.find("Home")
    acoes = [(e.text or "").strip() for e in casa.iter()
             if e is not casa and e.tag not in ("keyboard", "remote")]
    assert acoes, "keymap da Home sem acao"
    for acao in acoes:
        assert acao == "RunScript(%s,voltar)" % ADDON_ID, acao
    teclas = {e.tag for e in casa.find("keyboard")}
    # KEYCODE_BACK do Android chega ao Kodi como XBMCK_BACKSPACE
    assert "backspace" in teclas, teclas
    # ordem alfabetica: o ultimo arquivo vence, o nosso tem de ser o ultimo
    do_sistema = sorted(n for n in z.namelist()
                        if re.fullmatch(r"assets/system/keymaps/[^/]+\.xml", n))
    assert do_sistema[-1] == KEYMAP, do_sistema[-3:]
    print("   %s: VOLTAR na Home reabre a tela (carregado por ultimo)"
          % KEYMAP.split("/")[-1])


# --------------------------------------------------------------------------
# 2. Addon habilitado: manifest + banco de addons semeado
# --------------------------------------------------------------------------
def conferir_addon_habilitado(z: zipfile.ZipFile) -> None:
    manifest = z.read("assets/system/addon-manifest.xml").decode("utf-8")
    ET.fromstring(manifest.encode("utf-8"))
    assert ">%s<" % ADDON_ID in manifest, "addon da tela fora do addon-manifest.xml"
    linha = [l for l in manifest.splitlines() if ADDON_ID in l][0].strip()
    print("   manifest: %s" % linha)

    # O perfil semeado nao pode ter linha propria: SyncInstalled insere com
    # enabled=1 (system e optional). Se a linha existisse desabilitada, o
    # RunScript por id falharia.
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
    assert not linhas, "perfil semeado ja tem linha para o addon: %r" % (linhas,)
    print("   %s: sem linha do addon -> nasce enabled=1" % DB_PERFIL)

    # o addon precisa carregar como xbmc.python.script
    addon_xml = ET.fromstring(z.read("assets/addons/%s/addon.xml" % ADDON_ID))
    pontos = [e.get("point") for e in addon_xml.findall("extension")]
    assert "xbmc.python.script" in pontos, pontos
    lib = [e.get("library") for e in addon_xml.findall("extension")
           if e.get("point") == "xbmc.python.script"][0]
    assert ("assets/addons/%s/%s" % (ADDON_ID, lib)) in z.namelist()
    print("   addon.xml: xbmc.python.script -> %s" % lib)


# --------------------------------------------------------------------------
# 3. Recursos usados pelo XML (texturas e fontes)
# --------------------------------------------------------------------------
def recursos_do_layout(raiz: ET.Element):
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


def conferir_recursos(z: zipfile.ZipFile, skin: str) -> None:
    raiz = ET.fromstring(z.read("assets/addons/%s/%s" % (ADDON_ID, LAYOUT)))
    texturas, fontes = recursos_do_layout(raiz)
    caixa = raiz.find("controls")
    assert caixa is not None, "layout sem <controls>"
    fundo = raiz.find(".//control[@id='1']")
    largura = int(fundo.find("width").text)
    altura = int(fundo.find("height").text)
    assert (largura, altura) == (1920, 1080), (largura, altura)

    presentes = {n.rsplit("/", 1)[-1] for n in z.namelist()
                 if n.startswith("assets/addons/%s/%s/" % (ADDON_ID, MEDIA))}
    ausentes = sorted(t for t in texturas if t not in presentes)
    assert not ausentes, "textura ausente no addon: %r" % ausentes
    print("   texturas do layout (%d): todas em %s/" % (len(texturas), MEDIA))

    font_xml = z.read("assets/addons/%s/xml/Font.xml" % skin).decode("utf-8")
    declaradas = set(re.findall(r"<name>([^<]+)</name>", font_xml))
    sem_fonte = sorted(f for f in fontes if f not in declaradas)
    assert not sem_fonte, "%s sem as fontes %r" % (skin, sem_fonte)
    # Para cada fonte do layout, pelo menos uma declaracao precisa apontar para
    # um .ttf que existe no addon da skin (o Kodi escolhe um fontset; os
    # arquivos ausentes que ja existiam antes da injecao nao sao nossos).
    blocos = re.findall(r"<font>(.*?)</font>", font_xml, re.S)
    arquivos = {n.rsplit("/", 1)[-1] for n in z.namelist()
                if n.startswith("assets/addons/%s/fonts/" % skin)}
    sem_arquivo = []
    for nome in sorted(fontes):
        referencias = set()
        for bloco in blocos:
            achado = re.search(r"<name>([^<]+)</name>", bloco)
            if achado and achado.group(1) == nome:
                referencias.update(
                    re.findall(r"<filename>([^<]+\.ttf)</filename>", bloco))
        if not referencias or not (referencias & arquivos):
            sem_arquivo.append((nome, sorted(referencias)))
    assert not sem_arquivo, "%s sem arquivo de fonte para %r" % (skin, sem_arquivo)
    print("   fontes do layout (%d): declaradas em %s/xml/Font.xml"
          % (len(fontes), skin))


# --------------------------------------------------------------------------
# 4. Execucao do default.py com o dialogo do ZIP
# --------------------------------------------------------------------------
class Simulacao(object):
    def __init__(self, apk: Path):
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
        # reproduz o Kodi: ReplaceWindow troca a janela corrente. Enquanto o
        # Startup.xml e a janela corrente, "System.StartupWindow" aponta para
        # a propria 12999 -> ReplaceWindow(Startup) NAO leva a Home nenhuma.
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
    """Mesma superficie do vip.py real (service.smarted.bootstrap)."""

    # constantes reais copiadas do vip.py do APK (links do app)
    CHECKOUT = "https://pay.cakto.com.br/nkvbegd_1323120"
    APK = "https://www.dropbox.com/scl/fi/.../SMARTEDTV-atual.apk"
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

    def compartilhar(self, texto=None):
        self.chamadas.append("compartilhar")
        return True

    def abrir_url(self, url, rotulo=None):
        self.chamadas.append("apk" if "APK" in (rotulo or "").upper() or
                             "apk" in (url or "").lower() else "url")
        return True

    def procurar_atualizacao(self):
        self.chamadas.append("atualizar")
        return True


def criar_modulos(sim: Simulacao, raiz_addon: Path, raiz_servico: Path):
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

        def getControl(self, controle):
            if controle == 310:
                campo = types.SimpleNamespace()
                campo.getText = lambda: self.props.get("_codigo", "")
                return campo
            return types.SimpleNamespace()
            campo = types.SimpleNamespace()
            campo.getText = lambda: self.props.get("_codigo", "")
            return campo

        def close(self):
            self.fechada = True
            sim.modal_ativo = False

        def doModal(self):
            # No Kodi, doModal so retorna quando a janela fecha. Aqui o loop
            # bloqueante e representado pela interacao roteirizada do teste.
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
    # Os modulos ficam em sys.modules enquanto a tela roda: o default.py faz
    # `import vip` dentro das acoes, exatamente como no Kodi. A limpeza acontece
    # em restaurar_modulos(), no fim do teste.
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
    print("   pasta da tela: %s" % modulo._pasta_da_tela())
    assert modulo._pasta_do_servico() is not None, "servico VIP nao encontrado"

    def interacao(janela):
        """O que o usuario faz enquanto a tela esta no ar."""
        assert (janela.xml_filename, janela.default_skin, janela.resolution) == (
            "DialogWelcome.xml", "Default", "1080i"), (janela.xml_filename,
                                                       janela.default_skin,
                                                       janela.resolution)
        assert sim.foco and sim.foco[0] == 310, sim.foco
        assert sim.properties.get("smartedtv.welcome.ativa") == "1"
        print("   abriu 1080i, foco no campo 310, vigia avisado")

        # 311: ativa o codigo pelo servidor (vip.validar)
        janela.props["_codigo"] = codigo_vip
        janela.onClick(311)
        assert sim.vip.codigos == [codigo_vip], sim.vip.codigos
        assert janela.getProperty("welcome_dialog") == "status", janela.props
        print("   311 -> vip.validar(%r) OK, aviso na tela" % codigo_vip)
        janela.onClick(955)  # fecha o aviso de "VIP ativado"
        assert janela.getProperty("welcome_dialog") == "", janela.props

        # 120/121/122/123: checkout, compartilhar, baixar APK e atualizar
        janela.onClick(120)
        janela.onClick(121)
        janela.onClick(122)
        janela.onClick(123)
        assert sim.vip.chamadas == ["checkout", "compartilhar", "apk", "atualizar"], \
            sim.vip.chamadas
        print("   120 -> checkout; 121 -> compartilhar; 122 -> baixar APK; "
              "123 -> atualizar OK")

        # contadores removidos do layout (seletor de aparelho e pilulas de
        # plano) nao podem ter acao: se alguem clicar, nada acontece
        antes = list(sim.vip.chamadas)
        for removido in (130, 131, 140, 141):
            janela.onClick(removido)
        assert sim.vip.chamadas == antes, sim.vip.chamadas
        assert janela.getProperty("welcome_dialog") == "", janela.props
        print("   130/131/140/141 (removidos) -> nenhum efeito OK")

        # 312 -> modal de confirmacao (905 volta, 906 confirma)
        janela.onClick(312)
        assert janela.getProperty("welcome_dialog") == "ads", janela.props
        janela.onClick(905)
        assert janela.getProperty("welcome_dialog") == "", janela.props
        janela.onClick(312)
        print("   312 -> modal de confirmacao (905 volta, 906 confirma) OK")

        # durante toda a vida da tela, nenhum comando vai para a Home
        assert not sim.home_durante_modal, sim.home_durante_modal
        assert sim.janela_atual == "Startup", sim.janela_atual
        print("   durante a tela: nenhum comando de janela para a Home")

        janela.onClick(906)
        assert janela.fechada

    sim.interacao = interacao
    abriu = modulo.abrir_tela_entrada()
    assert abriu and sim.janela is not None
    # A Home TEM de estar na tela agora: o bug da v7 (tela preta) era sair do
    # modal e nao ativar nenhuma janela.
    assert sim.janela_atual == "Home", (
        "tela preta: apos sair da tela a janela corrente e %r" % sim.janela_atual)
    assert "ActivateWindow(Home,return)" in sim.builtins, sim.builtins
    assert sim.properties.get("smartedtv.welcome.home") == "ok", sim.properties
    print("   906 -> Home aberta SOMENTE depois de a tela sair de cena")

    # Voltando com o botao Voltar: mesmo caminho, Home garantida.
    sim_volta = Simulacao(sim.apk)
    modulo_volta = carregar_default(sim_volta, ADDON,
                                    ROOT / "kodi" / "addons" / SERVICO)

    def so_voltar(janela):
        janela.onAction(92)          # ACTION_NAV_BACK

    sim_volta.interacao = so_voltar
    assert modulo_volta.abrir_tela_entrada() is True
    assert sim_volta.janela_atual == "Home", sim_volta.janela_atual
    restaurar_modulos(modulo_volta)
    print("   Voltar -> Home aberta tambem")

    # Caminho de falha: sem a tela, a Home ainda abre (nunca prende o boot).
    sim2 = Simulacao(sim.apk)
    modulo2 = carregar_default(sim2, ADDON, ROOT / "kodi" / "addons" / SERVICO)
    modulo2._pasta_da_tela = lambda: None
    assert modulo2.abrir_tela_entrada() is False
    assert sim2.janela_atual == "Home", sim2.janela_atual
    restaurar_modulos(modulo2)
    print("   falha na tela -> Home abre mesmo assim (boot nunca fica preso)")

    # Regressao do bug da v7: o AlarmClock do Startup.xml disparava em torno da
    # janela de startup (que ja morreu) e a Home nunca aparecia. O Startup.xml
    # nao tem mais ReplaceWindow nenhum — conferido em conferir_startup().
    sim3 = Simulacao(sim.apk)
    modulo3 = carregar_default(sim3, ADDON, ROOT / "kodi" / "addons" / SERVICO)
    # vigia: a tela nunca avisa que desenhou -> ele abre a Home sozinho
    sim3.interacao = None
    modulo3.abrir_tela_entrada = lambda: False
    modulo3.vigiar_inicializacao()
    assert sim3.janela_atual == "Home", sim3.janela_atual
    restaurar_modulos(modulo3)
    print("   vigia: tela nao desenhou -> Home aberta em %ds" % 8)

    # VOLTAR ja na Home (keymap): reabre a tela POR CIMA da Home, sem restart
    sim4 = Simulacao(sim.apk)
    modulo4 = carregar_default(sim4, ADDON, ROOT / "kodi" / "addons" / SERVICO)
    sim4.janela_atual = "Home"
    vistas = []

    def interacao_voltar(janela):
        vistas.append(janela.xml_filename)
        assert sim4.janela_atual == "Home", sim4.janela_atual
        # o campo abre vazio, pronto para quem tem codigo
        assert janela.props.get("_codigo", "") == ""
        janela.onClick(312)          # abre o dialogo de confirmacao
        janela.onClick(906)          # continua com anuncios
        vistas.append(sim4.janela_atual)

    sim4.interacao = interacao_voltar
    assert modulo4.voltar_para_a_tela() is True
    assert vistas == ["DialogWelcome.xml", "Home"], vistas
    assert not [b for b in sim4.builtins if b.startswith("RestartApp")], \
        sim4.builtins
    assert not [b for b in sim4.builtins if b.startswith("ReplaceWindow")], \
        sim4.builtins
    restaurar_modulos(modulo4)
    print("   VOLTAR na Home -> tela reaberta sobre a Home, sem reiniciar")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True,
                        help="APK com a tela injetada (build_test/bruto.apk)")
    args = parser.parse_args(argv)

    with zipfile.ZipFile(args.apk) as z:
        print("1. Startup.xml de cada skin")
        skins = conferir_startup(z)

        print("1b. Keymap de VOLTAR na Home")
        conferir_keymap(z)

        print("2. Addon da tela habilitado no boot")
        conferir_addon_habilitado(z)

        print("3. Recursos do DialogWelcome.xml (1920x1080)")
        for skin in skins:
            if "assets/addons/%s/xml/Font.xml" % skin not in z.namelist():
                print("   %s: sem Font.xml, ignorada" % skin)
                continue
            conferir_recursos(z, skin)

    print("4. Execucao da tela (stubs do Kodi)")
    sim = Simulacao(args.apk)
    modulo = carregar_default(sim, ADDON, ROOT / "kodi" / "addons" / SERVICO)
    conferir_execucao(sim, modulo)
    restaurar_modulos(modulo)

    print("\nOK: a tela abre antes da Home, usa os fluxos que ja existem no app")
    print("    e a Home so e aberta quando a tela sai de cena.")
    print("    VOLTAR na Home reabre a tela para quem tem codigo.")
    print("    (Simulacao com stubs: nao substitui um teste em Kodi real.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
