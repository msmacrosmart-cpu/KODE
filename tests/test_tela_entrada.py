# -*- coding: utf-8 -*-
"""Tela de entrada do ZIP integrada ao boot do SMARTEDTV (antes da Home).

Sem Kodi real: confere que o visual continua byte a byte igual ao ZIP, que o
``Startup.xml`` da skin-fonte abre a tela em vez da Home, que o addon entra no
APK como addon de sistema registrado, e que as acoes da tela usam os fluxos que
ja existem no app (``vip.py``) — sem inventar endpoint.
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
SERVICE_DIR = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
SERVICE = SERVICE_DIR / 'service.py'
STARTUP_SKIN = ROOT / 'kodi' / 'skin.estilo.personalizado' / 'xml' / 'Startup.xml'
BUILD = ROOT / 'tools' / 'kodi' / 'build-release-apk.py'
INJETOR = ROOT / 'tools' / 'kodi' / 'injetar-tela-entrada.py'
HOME = 'ReplaceWindow($INFO[System.StartupWindow])'

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


# --------------------------------------------------------------------------
# Integração no boot: Startup.xml da skin-fonte (e o do APK via injetor)
# --------------------------------------------------------------------------
class StartupAntesDaHomeTest(unittest.TestCase):
    def _acoes(self, caminho):
        raiz = ET.fromstring(caminho.read_bytes())
        return [(e.text or '').strip() for e in raiz.findall('onload')]

    def test_startup_da_skin_fonte_dispara_a_tela(self):
        acoes = self._acoes(STARTUP_SKIN)
        self.assertEqual(len(acoes), 2, acoes)
        self.assertIn('RunScript(%s)' % ADDON_ID, acoes[0])
        self.assertIn('smartedtv_entrada,', acoes[0])
        self.assertIn('smartedtv_entrada_seguro', acoes[1])
        self.assertIn(HOME, acoes[1])
        # nada de Home solta: o salto original foi substituido, sobrando apenas
        # o ReplaceWindow do seguro (o outro esta no comentario do XML)
        corpo = STARTUP_SKIN.read_text(encoding='utf-8')
        corpo = corpo.split('<window>', 1)[1]
        self.assertEqual(corpo.count('ReplaceWindow'), 1)

    def test_injetor_aplica_o_mesmo_startup_no_apk(self):
        spec = importlib.util.spec_from_file_location('injetor_startup', INJETOR)
        injetor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(injetor)
        original = ('<?xml version="1.0" encoding="UTF-8"?>\n<window>\n'
                    '\t<onload>%s</onload>\n\t<controls />\n</window>\n' % HOME)
        novo = injetor.patch_startup(original.encode()).decode()
        acoes = [(e.text or '').strip()
                 for e in ET.fromstring(novo.encode()).findall('onload')]
        self.assertEqual(acoes, [
            'AlarmClock(smartedtv_entrada,RunScript(%s),00:00:00,silent)' % ADDON_ID,
            'AlarmClock(smartedtv_entrada_seguro,'
            'ReplaceWindow($INFO[System.StartupWindow]),00:00:30,silent)'])

    def test_startup_com_home_solta_e_recusado(self):
        spec = importlib.util.spec_from_file_location('injetor_guard', INJETOR)
        injetor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(injetor)
        ruim = ('<window><onload>AlarmClock(smartedtv_entrada,'
                'RunScript(%s),00:00:00,silent)</onload>'
                '<onload>%s</onload></window>' % (ADDON_ID, HOME)).encode()
        with self.assertRaises(SystemExit):
            injetor.validar_publicacao(ruim)


# --------------------------------------------------------------------------
# Ações da tela: reutilizam o que já existe no app
# --------------------------------------------------------------------------
class JanelaFake(object):
    ultima = None
    falhar_modal = False
    interacao = None

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

    def getControl(self, controle):
        if controle != 310:
            raise KeyError(controle)
        campo = types.SimpleNamespace()
        campo.getText = lambda: self.props.get('_codigo', '')
        return campo

    def close(self):
        self.fechada = True

    def doModal(self):
        # como no Kodi: onInit ao montar, e o retorno so quando a janela fecha
        if JanelaFake.falhar_modal:
            raise RuntimeError('GUI indisponivel')
        self.onInit()
        self.modal = True
        if JanelaFake.interacao is not None:
            JanelaFake.interacao(self)
        self.fechada = True


class VipFake(object):
    CHECKOUT = 'x'
    SITE = 'y'

    def __init__(self):
        self.chamadas = []
        self.codigos = []

    def ativa(self):
        return False

    def validar(self, codigo):
        self.codigos.append(codigo)
        return (False, 'codigo invalido')

    def abrir_checkout(self):
        self.chamadas.append('checkout')
        return True

    def compartilhar(self, texto=None):
        self.chamadas.append('compartilhar')
        return True


def _servico_com_vip(vip):
    """Pasta do service.smarted.bootstrap com o vip.py real trocado pelo stub.

    O addon do ZIP importa `vip` da pasta do serviço (é o módulo de licença que
    já existe no APK). Aqui a pasta é temporária e o vip.py só encaminha para o
    stub, para o teste observar as chamadas.
    """
    pasta = Path(tempfile.mkdtemp(prefix='servico-'))
    (pasta / 'vip.py').write_text(
        'import sys\n'
        '_stub = sys.modules["_smarted_vip_stub"]\n'
        'def __getattr__(nome):\n'
        '    return getattr(_stub, nome)\n', encoding='utf-8')
    return pasta


def carregar_default(vip=None):
    """Carrega o default.py real com stubs mínimos de xbmc*."""
    vip = vip or VipFake()
    servico = _servico_com_vip(vip)
    xbmc = types.ModuleType('xbmc')
    xbmc.BUILTINS = []
    xbmc.LOGS = []
    xbmc.LOGINFO = 1
    xbmc.LOGWARNING = 3
    xbmc.LOGERROR = 4
    xbmc.log = lambda msg, level=1: xbmc.LOGS.append((level, msg))
    xbmc.executebuiltin = lambda cmd, wait=False: xbmc.BUILTINS.append(cmd)

    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.WindowXMLDialog = JanelaFake
    xbmcgui.ACTION_NAV_BACK = 92
    xbmcgui.ACTION_PREVIOUS_MENU = 10
    xbmcgui.INPUT_ALPHANUM = 0
    xbmcgui.NOTIFICATION_INFO = 0

    class Window(object):
        def __init__(self, *args):
            pass

        def setProperty(self, chave, valor):
            xbmc.LOGS.append(('prop', chave))

    class Dialog(object):
        def ok(self, *args):
            xbmc.LOGS.append(('ok', args))

        def notification(self, *args):
            pass

        def input(self, *args, **kwargs):
            return ''

    xbmcgui.Window = Window
    xbmcgui.Dialog = Dialog

    xbmcaddon = types.ModuleType('xbmcaddon')

    class Addon(object):
        def __init__(self, ident=None):
            self.ident = ident

        def getAddonInfo(self, chave):
            if chave != 'path':
                return ''
            return str(servico if self.ident else ADDON)

    xbmcaddon.Addon = Addon

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda p: p
    xbmcvfs.exists = lambda p: Path(p).exists()

    nomes = ('xbmc', 'xbmcgui', 'xbmcaddon', 'xbmcvfs', 'vip')
    salvos = {nome: sys.modules.get(nome) for nome in nomes}
    sys.modules.update({'xbmc': xbmc, 'xbmcgui': xbmcgui, 'xbmcaddon': xbmcaddon,
                        'xbmcvfs': xbmcvfs, 'vip': vip,
                        '_smarted_vip_stub': vip})
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
    # o vip.py da pasta temporaria encaminha para este stub; ele precisa
    # continuar registrado enquanto os testes chamarem o default.py
    sys.modules['_smarted_vip_stub'] = vip
    return modulo, xbmc, xbmcgui


class CicloDeVidaTest(unittest.TestCase):
    def setUp(self):
        JanelaFake.ultima = None
        JanelaFake.falhar_modal = False
        JanelaFake.interacao = None
        self.vip = VipFake()
        self.modulo, self.xbmc, self.xbmcgui = carregar_default(self.vip)
        self.addCleanup(sys.modules.pop, '_smarted_vip_stub', None)
        self.addCleanup(sys.modules.pop, 'vip', None)

    def test_abre_com_o_layout_do_zip_e_foca_o_codigo(self):
        self.assertTrue(self.modulo.abrir_tela_entrada())
        janela = JanelaFake.ultima
        self.assertIsNotNone(janela)
        self.assertEqual(janela.args, ('DialogWelcome.xml', str(ADDON),
                                       'Default', '1080i'))
        self.assertTrue(janela.modal)
        self.assertIn(310, janela.foco)
        self.assertIn('CancelAlarm(smartedtv_entrada_seguro,silent)',
                      self.xbmc.BUILTINS)
        # a Home só depois de a janela sair de cena
        self.assertEqual(self.xbmc.BUILTINS[-1], HOME)

    def test_home_so_depois_de_a_janela_fechar(self):
        observado = []

        def interacao(janela):
            janela.onInit()
            janela.onClick(312)
            janela.onClick(906)
            observado.append(list(self.xbmc.BUILTINS))

        JanelaFake.interacao = interacao
        self.modulo.abrir_tela_entrada()
        durante = observado[0]
        self.assertTrue(JanelaFake.ultima.fechada)
        self.assertNotIn(HOME, durante)
        self.assertEqual(self.xbmc.BUILTINS.count(HOME), 1)

    def test_voltar_fecha_modal_e_depois_a_janela(self):
        foco = []

        def interacao(janela):
            janela.onInit()
            janela.onClick(312)
            janela.onAction(self.xbmcgui.ACTION_NAV_BACK)
            foco.append((janela.getProperty('show_free_dialog'), janela.fechada))
            janela.onAction(self.xbmcgui.ACTION_PREVIOUS_MENU)

        JanelaFake.interacao = interacao
        self.modulo.abrir_tela_entrada()
        self.assertEqual(foco, [('', False)])
        self.assertTrue(JanelaFake.ultima.fechada)
        self.assertEqual(self.xbmc.BUILTINS.count(HOME), 1)

    def test_310_ativa_o_codigo_pelo_servidor(self):
        def interacao(janela):
            janela.onInit()
            janela.props['_codigo'] = 'SMARTED-99'
            janela.onClick(311)

        JanelaFake.interacao = interacao
        self.modulo.abrir_tela_entrada()
        self.assertEqual(self.vip.codigos, ['SMARTED-99'])

    def test_120_e_121_usam_checkout_e_compartilhar_existentes(self):
        def interacao(janela):
            janela.onInit()
            janela.onClick(120)
            janela.onClick(121)

        JanelaFake.interacao = interacao
        self.modulo.abrir_tela_entrada()
        self.assertEqual(self.vip.chamadas, ['checkout', 'compartilhar'])

    def test_acoes_sem_fluxo_no_app_nao_abrem_nada(self):
        def interacao(janela):
            janela.onInit()
            janela.onClick(130)   # seletor de aparelho do ZIP: só registro
            janela.onClick(131)

        JanelaFake.interacao = interacao
        self.modulo.abrir_tela_entrada()
        self.assertEqual(self.vip.chamadas, [])
        self.assertEqual(self.vip.codigos, [])
        avisos = [msg for nivel, msg in self.xbmc.LOGS if nivel == self.xbmc.LOGWARNING]
        self.assertTrue(all('sem fluxo no projeto' in msg for msg in avisos), avisos)

    def test_sem_a_tela_a_home_ainda_abre(self):
        JanelaFake.falhar_modal = True
        self.modulo.abrir_tela_entrada()
        self.assertTrue(any(nivel == self.xbmc.LOGERROR
                            for nivel, _ in self.xbmc.LOGS))
        self.assertEqual(self.xbmc.BUILTINS.count(HOME), 1)

    def test_tela_ausente_nao_prende_o_boot(self):
        self.modulo._pasta_da_tela = lambda: None
        self.assertFalse(self.modulo.abrir_tela_entrada())
        self.assertEqual(self.xbmc.BUILTINS.count(HOME), 1)


class IntegracaoNoApkTest(unittest.TestCase):
    def test_addon_entra_no_apk_como_addon_de_sistema(self):
        fonte = BUILD.read_text(encoding='utf-8')
        self.assertIn('"script.smartedtv.welcome"', fonte)
        self.assertIn('BRIDGE_ADDONS', fonte)

    def test_bootstrap_nao_abre_mais_a_tela(self):
        """Quem abre a tela é o Startup.xml, antes da Home — não o serviço."""
        fonte = SERVICE.read_text(encoding='utf-8')
        self.assertNotIn('tela_entrada', fonte)
        self.assertFalse((SERVICE_DIR / 'tela_entrada.py').exists())


class FontesDaTelaTest(unittest.TestCase):
    """O layout do ZIP usa fontes que as skins do app não declaravam."""

    # Fontes publicadas pelas skins do APK atual (skin.novatv e
    # skin.smartedtv.classic) — conferido no próprio APK.
    FONTES_DA_SKIN = {
        'font10', 'font12', 'font13', 'font14', 'font11', 'font16',
        'font23_narrow', 'font25_narrow', 'font27', 'font27_narrow',
        'font32', 'font37', 'font45', 'font60', 'font_clock', 'font_flag',
        'font20_title', 'font25_title', 'font30_title', 'font32_title',
        'font36_title', 'font40_title', 'font45_title', 'font52_title',
        'font_MainMenu', 'WeatherTemp', 'Mono26',
    }

    def test_fontes_que_faltavam_sao_declaradas_pelo_injetor(self):
        raiz = ET.parse(LAYOUT).getroot()
        usadas = {(no.text or '').strip() for no in raiz.iter('font')}
        usadas.discard('')
        self.assertTrue(usadas)
        faltantes = sorted(usadas - self.FONTES_DA_SKIN)
        self.assertEqual(faltantes, ['font20', 'font22', 'font24', 'font30'])

        spec = importlib.util.spec_from_file_location(
            'injetor_fontes', INJETOR)
        injetor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(injetor)
        declaradas = dict(injetor.FONTES_DA_TELA)
        for nome in faltantes:
            self.assertIn(nome, declaradas)
            self.assertEqual(declaradas[nome], int(nome.replace('font', '')))


if __name__ == '__main__':
    unittest.main()
