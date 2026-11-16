# -*- coding: utf-8 -*-
"""Tela de entrada do pacote `smartedtv-src` (Dropbox) integrada ao boot.

Sem Kodi real: confere que o layout reproduz o pacote (cores e QR Codes
byte a byte, geometria em 1920x1080), que o ``Startup.xml`` da skin-fonte abre
a tela em vez da Home, que o addon entra no APK como addon de sistema
registrado, e que as acoes da tela usam os fluxos que ja existem no app
(``vip.py``) — sem inventar endpoint.
"""
import hashlib
import importlib.util
import py_compile
import re
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
GERADOR = ROOT / 'tools' / 'kodi' / 'gerar-tela-entrada.py'
INJETOR = ROOT / 'tools' / 'kodi' / 'injetar-tela-entrada.py'
HOME = 'ReplaceWindow($INFO[System.StartupWindow])'

# Pacote entregue no Dropbox (smartedtv-src.zip): a tela no APK tem de ser esta.
PACOTE = ROOT / 'build_test' / 'src_novo' / 'smartedtv'
CSS = PACOTE / 'css' / 'styles.css'

# QR Codes do pacote, copiados byte a byte (nada e redesenhado).
QRS = {
    'qr_checkout.png': '779aea29e8eed647d4b2114c8d7bc3c8b469888ac9d52835b93f976fff4107e5',
    'qr_apk.png': '267c083fe18fe2893da7c71e3f38a5d02b990eaf3c56d645d46dfff3be346f52',
}

# IDs do pacote -> controles da tela (o D-pad percorre nesta ordem).
CONTROLES = {
    '120': 'Abrir checkout',
    '121': 'Compartilhar link',
    '122': 'Baixar APK (Android)',
    '123': 'ATUALIZAR APLICATIVO',
    '130': 'Android TV',
    '131': 'Celular',
    '140': '10 min',
    '141': '1 mês',
    '310': None,          # campo do codigo de ativacao
    '311': 'Ativar',
    '312': 'Continuar com anúncios',
    '905': 'Voltar',
    '906': 'Continuar com anúncios',
    '955': None,          # OK do dialogo de status
}


def _raiz():
    return ET.parse(LAYOUT).getroot()


def _controle(ident):
    achado = _raiz().find("./controls/control[@id='%s']" % ident)
    if achado is None:
        achado = _raiz().find(".//control[@id='%s']" % ident)
    return achado


def _textos(raiz=None):
    raiz = raiz if raiz is not None else _raiz()
    return ' '.join((no.text or '') for no in raiz.iter('label'))


class TelaDoPacoteTest(unittest.TestCase):
    """O que o usuario ve tem de ser o pacote do Dropbox, nada mesclado."""

    def test_qr_codes_sao_os_do_pacote_byte_a_byte(self):
        for nome, esperado in QRS.items():
            destino = MEDIA / nome
            self.assertTrue(destino.is_file(), 'QR ausente: %s' % nome)
            self.assertEqual(hashlib.sha256(destino.read_bytes()).hexdigest(),
                             esperado, 'QR alterado: %s' % nome)

    def test_qr_codes_batem_com_os_arquivos_do_pacote(self):
        for origem, destino in (('qr-checkout.png', 'qr_checkout.png'),
                                ('qr-apk.png', 'qr_apk.png')):
            self.assertEqual((PACOTE / 'assets' / origem).read_bytes(),
                             (MEDIA / destino).read_bytes(), origem)

    def test_textos_sao_os_do_pacote(self):
        textos = _textos()
        for esperado in ('SMARTEDTV', 'Ativação e assinatura', 'BEM-VINDO',
                         'Sua TV,', 'Sem anúncios', 'Indique e ganhe',
                         'Android TV', 'Celular', '10 min', '1 mês',
                         'Abrir checkout', 'Compartilhar link',
                         'Baixar APK (Android)', 'ATUALIZAR APLICATIVO',
                         'Ativar', 'Continuar com anúncios', 'Plano mensal'):
            self.assertIn(esperado, textos, esperado)

    def test_cores_vem_do_css_do_pacote(self):
        css = CSS.read_text(encoding='utf-8')
        tokens = dict(re.findall(r'--(ink|txt|mut):(#[0-9a-fA-F]{6})', css))
        self.assertEqual(tokens['ink'], '#f7f7f7')
        cores = {(no.text or '').strip() for no in _raiz().iter('textcolor')}
        self.assertIn('FF' + tokens['ink'][1:].upper(), cores)
        self.assertIn('FF' + tokens['txt'][1:].upper(), cores)
        self.assertIn('FF' + tokens['mut'][1:].upper(), cores)

    def test_layout_e_horizontal_16_9(self):
        """A tela e sempre deitada (paisagem); o modo retrato do CSS e ignorado."""
        css = CSS.read_text(encoding='utf-8')
        fonte = GERADOR.read_text(encoding='utf-8')
        self.assertIn('VW, VH = 1920.0, 1080.0', fonte)
        # o layout vertical do pacote nao aparece na traducao
        self.assertNotIn('@media (max-width: 900px)', _raiz().__str__())
        self.assertIn('@media (max-width: 900px)', css)

    def test_layout_e_1080p_e_ocupa_a_tela_toda(self):
        raiz = _raiz()
        self.assertEqual(raiz.tag, 'window')
        self.assertEqual(raiz.findtext('defaultcontrol'), '310')
        fundo = raiz.find("./controls/control[@id='1']")
        self.assertEqual(fundo.findtext('width'), '1920')
        self.assertEqual(fundo.findtext('height'), '1080')
        self.assertEqual(fundo.findtext('left'), '0')
        self.assertEqual(fundo.findtext('top'), '0')

    def test_controles_do_pacote_estao_presentes(self):
        ids = {c.get('id') for c in _raiz().iter('control')}
        for ident in CONTROLES:
            self.assertIn(ident, ids, ident)
        # os botoes mostram exatamente o texto do pacote
        for ident, rotulo in CONTROLES.items():
            if rotulo is None:
                continue
            controle = _controle(ident)
            texto = (controle.findtext('label') or '').strip()
            self.assertEqual(texto, rotulo, ident)

    def test_todas_as_texturas_existem_e_sao_png(self):
        texturas = set()
        for no in _raiz().iter():
            if no.tag in ('texture', 'texturefocus', 'texturenofocus'):
                nome = (no.text or '').strip()
                if nome:
                    texturas.add(nome)
        self.assertGreaterEqual(len(texturas), 20, sorted(texturas))
        for nome in sorted(texturas):
            arquivo = MEDIA / nome
            self.assertTrue(arquivo.is_file(), 'textura ausente: %s' % nome)
            self.assertEqual(arquivo.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')

    def test_nao_sobraram_restos_da_tela_anterior(self):
        """Troca total: nada da tela antiga (ZIP Omega) na interface."""
        layout = LAYOUT.read_text(encoding='utf-8')
        for antigo in ('qr_1.png', 'qr_2.png', 'welcome_background.png',
                       'dialog_panel.png', 'button_dark.png'):
            self.assertNotIn(antigo, layout, antigo)
        # e as texturas antigas nao ficam no addon
        for antigo in ('qr_1.png', 'qr_2.png', 'welcome_background.png',
                       'dialog_panel.png', 'button_dark.png', 'separator.png',
                       'overlay_black.png', 'edit_focus.png',
                       'edit_nofocus.png', 'white.png'):
            self.assertFalse((MEDIA / antigo).exists(), 'sobra: %s' % antigo)

    def test_media_so_tem_o_que_o_layout_usa(self):
        usadas = set()
        for no in _raiz().iter():
            if no.tag in ('texture', 'texturefocus', 'texturenofocus'):
                nome = (no.text or '').strip()
                if nome:
                    usadas.add(nome)
        no_disco = {p.name for p in MEDIA.glob('*.png')}
        self.assertEqual(no_disco, usadas, sorted(no_disco ^ usadas))

    def test_addon_abre_em_1080i_com_script(self):
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


class GeradorTest(unittest.TestCase):
    """A tela e reproduzivel a partir do pacote (nao e XML escrito a mao)."""

    def test_gerador_le_o_css_e_o_pacote(self):
        fonte = GERADOR.read_text(encoding='utf-8')
        self.assertIn('styles.css', fonte)
        self.assertIn('qr-checkout.png', fonte)
        self.assertIn('qr-apk.png', fonte)

    def test_geometria_bate_com_o_css(self):
        spec = importlib.util.spec_from_file_location('gerador_tela', GERADOR)
        gerador = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gerador)
        med = gerador.Medidas()
        # .screen{padding:2.0% 2.0%} -> 38 px
        self.assertEqual(med.pad, 38)
        # .grid{gap:1.3%} em 1844 px uteis -> 25 px
        self.assertEqual(med.col_gap, round(med.stage_w * 0.013 * med.k))
        # .top{height:9%}, .screen{gap:2.0%}: a grade fecha os 1080 px
        self.assertEqual(med.top_h, 90)
        self.assertEqual(med.barra_h, 113)
        self.assertEqual(med.grade_y, med.pad + med.top_h + med.gap)
        self.assertEqual(med.barra_y, med.grade_y + med.grade_h + med.gap)
        self.assertEqual(med.barra_y + med.barra_h, 1080 - med.pad)


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
        corpo = STARTUP_SKIN.read_text(encoding='utf-8')
        corpo = corpo.split('<window>', 1)[1]
        self.assertEqual(corpo.count('ReplaceWindow'), 1)

    def test_injetor_aplica_o_mesmo_startup_no_apk(self):
        spec = importlib.util.spec_from_file_location('injetor_startup', INJETOR)
        injetor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(injetor)
        original = ('<?xml version="1.0" encoding="UTF-8"?>\n<window>\n'
                    '\t<onload>ReplaceWindow($INFO[System.StartupWindow])</onload>\n'
                    '\t<controls />\n</window>\n')
        novo = injetor.patch_startup(original.encode()).decode()
        acoes = [(e.text or '').strip()
                 for e in ET.fromstring(novo.encode()).findall('onload')]
        self.assertEqual(len(acoes), 2, acoes)
        self.assertIn('RunScript(%s)' % ADDON_ID, acoes[0])
        self.assertIn(HOME, acoes[1])

    def test_startup_com_home_solta_e_recusado(self):
        spec = importlib.util.spec_from_file_location('injetor_recusa', INJETOR)
        injetor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(injetor)
        # com o disparo da tela, um ReplaceWindow solto tem de ser recusado
        quebrado = ('<?xml version="1.0" encoding="UTF-8"?>\n<window>\n'
                    '\t<onload>AlarmClock(smartedtv_entrada,RunScript(x),'
                    '00:00:00,silent)</onload>\n'
                    '\t<onload>ReplaceWindow($INFO[System.StartupWindow])</onload>\n'
                    '\t<controls />\n</window>\n')
        with self.assertRaises(SystemExit):
            injetor.validar_publicacao(quebrado.encode())


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
        if JanelaFake.falhar_modal:
            raise RuntimeError('GUI indisponivel')
        self.onInit()
        self.modal = True
        if JanelaFake.interacao is not None:
            JanelaFake.interacao(self)
        self.fechada = True


class VipFake(object):
    # constantes reais do vip.py do APK
    CHECKOUT = 'https://pay.cakto.com.br/nkvbegd_1323120'
    SITE = 'https://smartedtv-vip.lovable.app/'
    APK = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
           'SMARTEDTV-atual.apk')
    APK_GITHUB = ('https://github.com/msmacrosmart-cpu/KODE/releases/latest/'
                  'download/SMARTEDTV-atual.apk')

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

    def abrir_url(self, url, rotulo='link'):
        self.chamadas.append('url:%s' % (rotulo or ''))
        return True

    def procurar_atualizacao(self):
        self.chamadas.append('atualizar')
        return True


def _servico_com_vip(vip):
    pasta = Path(tempfile.mkdtemp(prefix='servico-'))
    (pasta / 'vip.py').write_text(
        'import sys\n'
        '_stub = sys.modules["_smarted_vip_stub"]\n'
        'def __getattr__(nome):\n'
        '    return getattr(_stub, nome)\n', encoding='utf-8')
    return pasta


def carregar_default(vip=None):
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
        spec = importlib.util.spec_from_file_location('welcome_teste',
                                                      ADDON / 'default.py')
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    finally:
        for nome, antigo in salvos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo
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

    def _com_interacao(self, acoes):
        def interacao(janela):
            janela.onInit()
            acoes(janela)
        JanelaFake.interacao = interacao
        self.assertTrue(self.modulo.abrir_tela_entrada())
        return JanelaFake.ultima

    def test_abre_com_o_layout_do_pacote_e_foca_o_codigo(self):
        janela = self._com_interacao(lambda j: None)
        self.assertEqual(janela.args, ('DialogWelcome.xml', str(ADDON),
                                       'Default', '1080i'))
        self.assertTrue(janela.modal)
        self.assertIn(310, janela.foco)
        self.assertIn('CancelAlarm(smartedtv_entrada_seguro,silent)',
                      self.xbmc.BUILTINS)
        self.assertEqual(self.xbmc.BUILTINS[-1], HOME)

    def test_home_so_depois_de_a_janela_fechar(self):
        observado = []

        def acoes(janela):
            janela.onClick(312)
            janela.onClick(906)
            observado.append(list(self.xbmc.BUILTINS))

        janela = self._com_interacao(acoes)
        self.assertTrue(janela.fechada)
        self.assertNotIn(HOME, observado[0])
        self.assertEqual(self.xbmc.BUILTINS.count(HOME), 1)

    def test_continuar_com_anuncios_pede_confirmacao(self):
        def acoes(janela):
            janela.onClick(312)
            assert janela.getProperty('welcome_dialog') == 'ads'
            janela.onClick(905)
            assert janela.getProperty('welcome_dialog') == ''
            janela.onClick(312)
            janela.onClick(906)
        janela = self._com_interacao(acoes)
        self.assertTrue(janela.fechada)
        self.assertEqual(self.xbmc.BUILTINS.count(HOME), 1)

    def test_voltar_fecha_o_dialogo_e_depois_a_janela(self):
        foco = []

        def acoes(janela):
            janela.onClick(312)
            janela.onAction(self.xbmcgui.ACTION_NAV_BACK)
            foco.append(janela.getProperty('welcome_dialog'))
            janela.onAction(self.xbmcgui.ACTION_PREVIOUS_MENU)

        janela = self._com_interacao(acoes)
        self.assertEqual(foco, [''])
        self.assertTrue(janela.fechada)
        self.assertEqual(self.xbmc.BUILTINS.count(HOME), 1)

    def test_311_ativa_o_codigo_pelo_servidor(self):
        def acoes(janela):
            janela.props['_codigo'] = 'SMARTED-99'
            janela.onClick(311)
            assert janela.getProperty('welcome_dialog') == 'status'
            janela.onClick(955)
        self._com_interacao(acoes)
        self.assertEqual(self.vip.codigos, ['SMARTED-99'])

    def test_120_a_123_usam_os_fluxos_existentes(self):
        def acoes(janela):
            for controle in (120, 121, 122, 123):
                janela.onClick(controle)
        self._com_interacao(acoes)
        self.assertEqual(self.vip.chamadas[0], 'checkout')
        self.assertEqual(self.vip.chamadas[1], 'compartilhar')
        self.assertTrue(self.vip.chamadas[2].startswith('url:'))
        self.assertEqual(self.vip.chamadas[3], 'atualizar')

    def test_122_e_123_nao_quebram_sem_ponte_android(self):
        """Fora do Android abrir_url devolve False: a tela avisa e segue."""
        def falhar(url, rotulo='link'):
            return False
        self.vip.abrir_url = falhar
        self.vip.procurar_atualizacao = lambda: False

        def acoes(janela):
            janela.onClick(122)
            assert janela.getProperty('welcome_dialog') == 'status'
            janela.onClick(955)
            janela.onClick(123)
            assert janela.getProperty('welcome_dialog') == 'status'
            janela.onClick(955)
        self._com_interacao(acoes)
        self.assertEqual(self.modulo._log.__module__, self.modulo.__name__)

    def test_140_e_141_escolhem_o_plano(self):
        def acoes(janela):
            janela.onClick(141)
            assert janela.plano == '1month'
            janela.onClick(140)
            assert janela.plano == '10min'
        self._com_interacao(acoes)

    def test_seletor_de_aparelho_nao_inventa_fluxo(self):
        def acoes(janela):
            janela.onClick(130)
            janela.onClick(131)
        self._com_interacao(acoes)
        self.assertEqual(self.vip.chamadas, [])
        self.assertEqual(self.vip.codigos, [])
        avisos = [m for nivel, m in self.xbmc.LOGS
                  if nivel == self.xbmc.LOGWARNING]
        self.assertTrue(all('sem fluxo no projeto' in m for m in avisos), avisos)
        self.assertTrue(any('16:9' in m for m in avisos), avisos)

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
        fonte = (ROOT / 'tools' / 'kodi' / 'build-release-apk.py').read_text(
            encoding='utf-8')
        self.assertIn('"script.smartedtv.welcome"', fonte)
        self.assertIn('BRIDGE_ADDONS', fonte)

    def test_bootstrap_nao_abre_mais_a_tela(self):
        fonte = SERVICE.read_text(encoding='utf-8')
        self.assertNotIn('tela_entrada', fonte)
        self.assertFalse((SERVICE_DIR / 'tela_entrada.py').exists())


class FontesDaTelaTest(unittest.TestCase):
    """A tela usa estilos wfNN (altura em px de 1080p) que a skin nao tem."""

    # Fontes publicadas pelas skins do APK atual (skin.novatv e
    # skin.smartedtv.classic) — conferido no proprio APK.
    FONTES_DA_SKIN = {
        'font10', 'font12', 'font13', 'font14', 'font11', 'font16',
        'font23_narrow', 'font25_narrow', 'font27', 'font27_narrow',
        'font32', 'font37', 'font45', 'font60', 'font_clock', 'font_flag',
        'font20_title', 'font25_title', 'font30_title', 'font32_title',
        'font36_title', 'font40_title', 'font45_title', 'font52_title',
        'font_MainMenu', 'WeatherTemp', 'Mono26',
    }

    def test_estilos_usados_e_declarados_pelo_injetor(self):
        raiz = _raiz()
        usadas = {(no.text or '').strip() for no in raiz.iter('font')}
        usadas.discard('')
        self.assertTrue(usadas)
        self.assertEqual(usadas, set(re.findall(r'wf\d+', ' '.join(usadas))))
        faltantes = sorted(usadas - self.FONTES_DA_SKIN)
        self.assertEqual(faltantes, sorted(usadas))

        spec = importlib.util.spec_from_file_location('injetor_fontes', INJETOR)
        injetor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(injetor)
        declaradas = dict(injetor.fontes_da_tela())
        self.assertEqual(declaradas, {nome: int(nome[2:]) for nome in usadas})

    def test_injetor_declara_sempre_a_mesma_fonte(self):
        fonte = INJETOR.read_text(encoding='utf-8')
        self.assertIn('NotoSans-Regular.ttf', fonte)


if __name__ == '__main__':
    unittest.main()
