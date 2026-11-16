# -*- coding: utf-8 -*-
"""Executa a tela do ZIP fora do Kodi (simulação do boot real).

Cria um ``xbmc``/``xbmcgui``/``xbmcvfs`` falsos, mas com o MESMO comportamento
que importa para a abertura:

* as texturas são resolvidas como no Kodi (``<pasta do XML>`` + ``media``), e
  qualquer textura ausente é registrada como falha;
* as fontes do XML são conferidas contra o Font.xml da skin ativa, como o
  ``GUIFontManager::GetFont`` (que cai em font13 quando o nome não existe);
* ``getInfoLabel('Window(10000).Property(...)')`` reflete a propriedade marcada
  no ``onInit``, que é o sinal usado pelo serviço de boot para confirmar que a
  tela entrou no ar.

Uso: ``python3 tools/kodi/simular-boot-tela-entrada.py [--apk APK]``
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import types
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "kodi" / "addons" / "script.smartedtv.welcome"
LAYOUT = "resources/skins/Default/1080i/DialogWelcome.xml"


class Simulacao(object):
    """Estado observável da execução (o equivalente ao log do Kodi)."""

    def __init__(self):
        self.logs = []
        self.builtins = []
        self.properties = {}
        self.texturas_ausentes = []
        self.fontes_ausentes = []
        self.foco = []
        self.janela = None

    def log(self, mensagem, nivel=1):
        self.logs.append(mensagem)


def criar_modulos(sim, raiz_addon):
    xbmc = types.ModuleType("xbmc")
    xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
    xbmc.log = sim.log
    xbmc.executebuiltin = lambda cmd, wait=False: sim.builtins.append(cmd)

    def get_info_label(expressao):
        m = re.match(r"Window\(10000\)\.Property\(([^)]+)\)", expressao or "")
        if m:
            return sim.properties.get(m.group(1), "")
        return ""

    xbmc.getInfoLabel = get_info_label
    xbmc.getCondVisibility = lambda cond: True

    class Monitor(object):
        def abortRequested(self):
            return False

        def waitForAbort(self, segundos):
            return False

    xbmc.Monitor = Monitor

    xbmcaddon = types.ModuleType("xbmcaddon")

    class Addon(object):
        def getAddonInfo(self, chave):
            return str(raiz_addon) if chave == "path" else ""

    xbmcaddon.Addon = Addon

    xbmcvfs = types.ModuleType("xbmcvfs")
    xbmcvfs.translatePath = lambda p: p
    xbmcvfs.exists = lambda p: Path(p).exists()

    xbmcgui = types.ModuleType("xbmcgui")
    xbmcgui.ACTION_NAV_BACK = 92
    xbmcgui.ACTION_PREVIOUS_MENU = 10

    class Janela(object):
        def __init__(self, *args, **kwargs):
            pass

        def setProperty(self, chave, valor):
            sim.properties[chave] = valor

    xbmcgui.Window = Janela

    class WindowXMLDialog(object):
        def __init__(self, xml_filename, script_path, default_skin, resolution):
            self.xml_filename = xml_filename
            self.script_path = script_path
            self.default_skin = default_skin
            self.resolution = resolution
            self.props = {}
            sim.janela = self

        def setProperty(self, chave, valor):
            self.props[chave] = valor

        def clearProperty(self, chave):
            self.props.pop(chave, None)

        def getProperty(self, chave):
            return self.props.get(chave, "")

        def setFocusId(self, controle):
            sim.foco.append(controle)

        def close(self):
            self.fechada = True

        def doModal(self):
            self.onInit()

    xbmcgui.WindowXMLDialog = WindowXMLDialog
    return {"xbmc": xbmc, "xbmcgui": xbmcgui, "xbmcaddon": xbmcaddon,
            "xbmcvfs": xbmcvfs}


def analisar_layout(raiz_addon, skin_fonts):
    """Confere texturas e fontes do XML, como o Kodi ao montar a janela."""
    caminho_xml = raiz_addon / LAYOUT
    raiz = ET.parse(caminho_xml).getroot()
    media = raiz_addon / "resources" / "skins" / "Default" / "media"
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
    ausentes = sorted(t for t in texturas if not (media / t).is_file())
    sem_fonte = sorted(f for f in fontes if f not in skin_fonts)
    return raiz, texturas, fontes, ausentes, sem_fonte


def fontes_da_skin(zip_apk, skin="skin.novatv"):
    if not zip_apk:
        return None
    with zipfile.ZipFile(zip_apk) as z:
        texto = z.read("assets/addons/%s/xml/Font.xml" % skin).decode("utf-8")
    return set(re.findall(r"<name>([^<]+)</name>", texto))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, default=None,
                        help="APK (opcional) para conferir as fontes da skin")
    args = parser.parse_args(argv)

    sim = Simulacao()
    modulos = criar_modulos(sim, ADDON)
    salvos = {nome: sys.modules.get(nome) for nome in modulos}
    sys.modules.update(modulos)
    try:
        spec = importlib.util.spec_from_file_location("welcome_sim", ADDON / "default.py")
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        caminho = modulo._caminho_da_tela()
        print("1. caminho da tela:", caminho)
        assert caminho == str(ADDON), caminho
        modulo.open_welcome()
    finally:
        for nome, antigo in salvos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    janela = sim.janela
    print("2. janela criada:", janela is not None)
    assert janela is not None
    print("3. parametros do dialogo:", janela.xml_filename, janela.default_skin,
          janela.resolution)
    assert (janela.xml_filename, janela.default_skin, janela.resolution) == (
        "DialogWelcome.xml", "Default", "1080i")
    print("4. foco inicial:", sim.foco)
    assert sim.foco == [310]

    print("5. sinal de abertura (Window 10000):",
          sim.properties.get("smartedtv.welcome.ativa"))
    assert sim.properties.get("smartedtv.welcome.ativa") == "1"

    skin_fonts = fontes_da_skin(args.apk) if args.apk else None
    raiz, texturas, fontes, ausentes, sem_fonte = analisar_layout(
        ADDON, skin_fonts or set())
    print("6. texturas do layout (%d) presentes:" % len(texturas), not ausentes)
    if ausentes:
        print("   AUSENTES:", ausentes)
    print("7. fontes do layout:", sorted(fontes))
    if skin_fonts is None:
        print("   (sem --apk: fontes da skin não conferidas)")
    else:
        print("   ausentes no Font.xml da skin:", sem_fonte or "nenhuma")
    assert not ausentes
    if skin_fonts is not None:
        assert not sem_fonte

    print("8. dimensões:", raiz.find(".//control[@id='1']/width").text + "x" +
          raiz.find(".//control[@id='1']/height").text)
    print("9. builtins executados:", sim.builtins)
    print("10. QR Codes: qr_1.png=%d bytes, qr_2.png=%d bytes" % (
        (ADDON / "resources/skins/Default/media/qr_1.png").stat().st_size,
        (ADDON / "resources/skins/Default/media/qr_2.png").stat().st_size))
    print("\nOK: a tela do ZIP carrega, foca o campo de código e sinaliza abertura.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
