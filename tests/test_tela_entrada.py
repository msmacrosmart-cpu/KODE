# -*- coding: utf-8 -*-
"""Validação da tela inicial entregue no ZIP, já integrada ao SMARTEDTV.

Sem Kodi real: confere que o visual continua byte a byte igual ao ZIP, que
todas as imagens referenciadas existem e que a janela abre/fecha com setas,
OK e Voltar encaminhando para a Home existente — sem simular ações que o
projeto não implementa.
"""
import hashlib
import importlib.util
import py_compile
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / 'kodi' / 'addons' / 'script.smartedtv.welcome'
ADDON_ID = 'script.smartedtv.welcome'
LAYOUT = ADDON / 'resources' / 'skins' / 'Default' / '1080i' / 'DialogWelcome.xml'
MEDIA = ADDON / 'resources' / 'skins' / 'Default' / 'media'
SERVICE = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'service.py'
BUILD = ROOT / 'tools' / 'kodi' / 'build-release-apk.py'

# SHA-256 dos arquivos exatamente como vieram em SMARTEDTV_Kodi_Omega_Welcome.zip.
# default.py fica de fora: é o único arquivo adaptado (pontos de integração).
HASHES_ZIP = {
    'addon.xml': 'a607b7d8771d447b21cdb4ea69b8d572a4afa2ffdc864aa041700eb52eed2b9a',
    'README.txt': 'b973624b077a47498bf6abac58089e24e46fc41b11abd930e6eec7d490450e28',
    'resources/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'resources/skins/Default/1080i/DialogWelcome.xml': '41d3d7cfbbe514d9139806cfeef0706722457b7d140ff22365d1bcf97544d5fe',
    'resources/skins/Default/media/button_dark.png': 'a92b2e966d2e63205e5603e041356d03a1f2c984bbc81d6821c5697f28af0782',
    'resources/skins/Default/media/dialog_panel.png': 'f5d01c26eda92e8df45287b465233b2ff9ed41f2e4c3d17d298d5ecc6b0a6a72',
    'resources/skins/Default/media/edit_focus.png': 'fdba7d6a08804f39d9f7c86b7ce6f22db4057673fd225875a9b7c60b2eb8aa78',
    'resources/skins/Default/media/edit_nofocus.png': 'c61b5d7107f22c6b85b69cb098805bc4575fec7c4f011999f1d419a4341ebf1e',
    'resources/skins/Default/media/overlay_black.png': '332a498541645db23a4f3ebb9af0df4549e04fb740d32a41ce0d69e25fb54d31',
    'resources/skins/Default/media/qr_1.png': '11f24709a55fc410afb3b5970c14d244978236b4267e904b1cdaba58aa0251a2',
    'resources/skins/Default/media/qr_2.png': '3d91d28c9d883de50f16e6ef3bd103493c1b06907047543c734add95850fb2f2',
    'resources/skins/Default/media/separator.png': '34a65d050c31d42abe52063b1ed59c24fdd1ed09b09ca329cd1bc9442514ac4d',
    'resources/skins/Default/media/welcome_background.png': '84000614326f58e1174dfe09f4d4d15f2e8b36efe652fe9efcd9ade690238481',
    'resources/skins/Default/media/white.png': '0e78a200db09cfa819694aa27ee02e3ffa26b4bf2d372c8be7bde2309da0c4b5',
}


class FidelidadeAoZipTest(unittest.TestCase):
    def test_arquivos_visuais_identicos_ao_zip(self):
        for relativo, esperado in HASHES_ZIP.items():
            arquivo = ADDON / relativo
            self.assertTrue(arquivo.is_file(), 'arquivo ausente: %s' % relativo)
            self.assertEqual(hashlib.sha256(arquivo.read_bytes()).hexdigest(),
                             esperado, 'arquivo alterado: %s' % relativo)

    def test_layout_e_16x9_e_tem_os_controles_entregues(self):
        raiz = ET.parse(LAYOUT).getroot()
        self.assertEqual(raiz.tag, 'window')
        self.assertEqual(raiz.findtext('defaultcontrol'), '310')
        fundo = raiz.find("./controls/control[@id='1']")
        self.assertEqual(fundo.findtext('width'), '1920')
        self.assertEqual(fundo.findtext('height'), '1080')
        self.assertEqual(fundo.findtext('texture'), 'welcome_background.png')
        self.assertEqual(raiz.find("./controls/control[@id='32']").findtext('texture'),
                         'qr_1.png')
        self.assertEqual(raiz.find("./controls/control[@id='42']").findtext('texture'),
                         'qr_2.png')
        ids = {c.get('id') for c in raiz.iter('control')}
        for obrigatorio in ('312', '905', '906', '120', '121', '310', '311', '900'):
            self.assertIn(obrigatorio, ids)

    def test_todas_as_texturas_existem_e_sao_png(self):
        raiz = ET.parse(LAYOUT).getroot()
        texturas = set()
        for no in raiz.iter():
            if no.tag in ('texture', 'texturefocus', 'texturenofocus'):
                nome = (no.text or '').strip()
                if nome:
                    texturas.add(nome)
        self.assertEqual(len(texturas), 10, sorted(texturas))
        for nome in sorted(texturas):
            arquivo = MEDIA / nome
            self.assertTrue(arquivo.is_file(), 'textura ausente: %s' % nome)
            self.assertEqual(arquivo.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')

    def test_addon_e_script_kodi_21(self):
        raiz = ET.parse(ADDON / 'addon.xml').getroot()
        self.assertEqual(raiz.get('id'), ADDON_ID)
        self.assertEqual(raiz.find('./requires/import').get('addon'), 'xbmc.python')
        self.assertEqual(raiz.find('./requires/import').get('version'), '3.0.0')
        scripts = [e for e in raiz.findall('extension')
                   if e.get('point') == 'xbmc.python.script']
        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts[0].get('library'), 'default.py')

    def test_python_compila(self):
        with tempfile.TemporaryDirectory() as tmp:
            py_compile.compile(str(ADDON / 'default.py'),
                               cfile=str(Path(tmp) / 'welcome.pyc'), doraise=True)


class JanelaFake(object):
    ultima = None
    falhar_modal = False

    def __init__(self, *args, **kwargs):
        self.args = args
        self.props = {}
        self.foco = []
        self.fechada = False
        self.modal = False
        JanelaFake.ultima = self

    def setProperty(self, chave, valor):
        self.props[chave] = valor

    def clearProperty(self, chave):
        self.props.pop(chave, None)

    def getProperty(self, chave):
        return self.props.get(chave, '')

    def setFocusId(self, controle):
        self.foco.append(controle)

    def close(self):
        self.fechada = True

    def doModal(self):
        if JanelaFake.falhar_modal:
            raise RuntimeError('GUI indisponivel')
        self.modal = True


def carregar_default():
    """Carrega o default.py real com stubs mínimos de xbmc*."""
    xbmc = types.ModuleType('xbmc')
    xbmc.BUILTINS = []
    xbmc.LOGS = []
    xbmc.LOGWARNING = 3
    xbmc.LOGERROR = 4
    xbmc.log = lambda msg, level=1: xbmc.LOGS.append((level, msg))
    xbmc.executebuiltin = lambda cmd, wait=False: xbmc.BUILTINS.append(cmd)

    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.WindowXMLDialog = JanelaFake
    xbmcgui.ACTION_NAV_BACK = 92
    xbmcgui.ACTION_PREVIOUS_MENU = 10

    xbmcaddon = types.ModuleType('xbmcaddon')

    class Addon(object):
        def getAddonInfo(self, chave):
            return str(ADDON) if chave == 'path' else ''

    xbmcaddon.Addon = Addon

    salvos = {nome: sys.modules.get(nome)
              for nome in ('xbmc', 'xbmcgui', 'xbmcaddon')}
    sys.modules.update({'xbmc': xbmc, 'xbmcgui': xbmcgui, 'xbmcaddon': xbmcaddon})
    try:
        spec = importlib.util.spec_from_file_location('welcome_teste', ADDON / 'default.py')
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    finally:
        for nome, antigo in salvos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo
    return modulo, xbmc, xbmcgui


class CicloDeVidaTest(unittest.TestCase):
    def setUp(self):
        JanelaFake.ultima = None
        JanelaFake.falhar_modal = False
        self.modulo, self.xbmc, self.xbmcgui = carregar_default()

    def test_abre_com_o_layout_do_zip_e_foca_o_codigo(self):
        self.modulo.open_welcome()
        janela = JanelaFake.ultima
        self.assertIsNotNone(janela)
        self.assertEqual(janela.args, ('DialogWelcome.xml', str(ADDON), 'Default', '1080i'))
        self.assertTrue(janela.modal)
        janela.onInit()
        self.assertEqual(janela.foco, [310])

    def test_confirmacao_e_voltar_encaminham_para_a_home(self):
        self.modulo.open_welcome()
        janela = JanelaFake.ultima
        janela.onClick(312)                       # abre o modal de confirmação
        self.assertEqual(janela.getProperty('show_free_dialog'), 'true')
        self.assertIn(905, janela.foco)
        janela.onClick(905)                       # "Voltar" do modal
        self.assertEqual(janela.getProperty('show_free_dialog'), '')
        self.assertIn(312, janela.foco)
        self.assertFalse(janela.fechada)
        janela.onClick(906)                       # confirma modo gratuito
        self.assertTrue(janela.fechada)
        self.assertEqual(self.xbmc.BUILTINS, ['ActivateWindow(Home)'])

    def test_tecla_voltar_fechando_modal_e_janela(self):
        self.modulo.open_welcome()
        janela = JanelaFake.ultima
        janela.onClick(312)
        janela.onAction(self.xbmcgui.ACTION_NAV_BACK)
        self.assertEqual(janela.getProperty('show_free_dialog'), '')
        self.assertFalse(janela.fechada)
        self.assertEqual(self.xbmc.BUILTINS, [])
        janela.onAction(self.xbmcgui.ACTION_PREVIOUS_MENU)
        self.assertTrue(janela.fechada)
        self.assertEqual(self.xbmc.BUILTINS, ['ActivateWindow(Home)'])

    def test_acoes_sem_fluxo_nao_simulam_sucesso(self):
        self.modulo.open_welcome()
        janela = JanelaFake.ultima
        for controle in (120, 121, 311, 130, 131):
            janela.onClick(controle)
        self.assertFalse(janela.fechada)
        self.assertEqual(self.xbmc.BUILTINS, [])
        avisos = [msg for nivel, msg in self.xbmc.LOGS
                  if nivel == self.xbmc.LOGWARNING]
        self.assertEqual(len(avisos), 5)
        self.assertTrue(all('sem implementacao' in msg and 'nao simulada' in msg
                            for msg in avisos))

    def test_falha_ao_abrir_nao_interrompe_o_aplicativo(self):
        JanelaFake.falhar_modal = True
        self.modulo.open_welcome()                # não deve lançar exceção
        self.assertTrue(any(nivel == self.xbmc.LOGERROR
                            for nivel, _ in self.xbmc.LOGS))
        self.assertEqual(self.xbmc.BUILTINS, [])


class IntegracaoNoBootTest(unittest.TestCase):
    def test_bootstrap_abre_a_tela_uma_vez(self):
        fonte = SERVICE.read_text(encoding='utf-8')
        self.assertIn("WELCOME_ADDON = '%s'" % ADDON_ID, fonte)
        self.assertIn('def abrir_tela_entrada(monitor):', fonte)
        self.assertIn('RunScript(%s)', fonte)
        self.assertIn("name='welcome-entry'", fonte)
        self.assertEqual(fonte.count('entrada.start()'), 1)

    def test_addon_entra_no_apk(self):
        fonte = BUILD.read_text(encoding='utf-8')
        self.assertIn('"script.smartedtv.welcome"', fonte)
        self.assertIn('BRIDGE_ADDONS', fonte)


if __name__ == '__main__':
    unittest.main()
