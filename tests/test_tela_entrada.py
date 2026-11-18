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
import textwrap
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
DEFAULT_PY = ADDON / 'default.py'
INJETOR = ROOT / 'tools' / 'kodi' / 'injetar-tela-entrada.py'
# A Home agora e aberta pelo proprio addon (a v7 usava ReplaceWindow do
# Startup.xml, que disparava em torno da janela de startup -> tela preta).
HOME = 'ActivateWindow(Home)'

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
    '310': None,          # campo do codigo de ativacao
    '311': 'Ativar',
    '312': 'Assistir com anúncios',
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
                         'Abrir checkout', 'Compartilhar link',
                         'Baixar APK (Android)', 'ATUALIZAR APLICATIVO',
                         'Ativar', 'Assistir com anúncios', 'Plano mensal'):
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


class TipografiaTest(unittest.TestCase):
    """Nenhuma letra por cima de botao/icone, nada cortado, nada de tofu."""

    AUDITOR = ROOT / 'tools' / 'kodi' / 'auditar-tela-entrada.py'

    def test_auditoria_sem_problemas(self):
        spec = importlib.util.spec_from_file_location('auditor_tela',
                                                      self.AUDITOR)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        problemas, textos = modulo.auditar()
        self.assertEqual(problemas, [], '\n'.join(problemas))
        self.assertGreaterEqual(len(textos), 25)

    def test_todo_layout_tem_altura_de_fonte_medida(self):
        """<label> com altura menor que a fonte corta acento e descendente."""
        raiz = _raiz()
        tamanhos = {nome: int(nome[2:]) for nome in
                    set(re.findall(r'<font>(wf\d+)</font>',
                                   LAYOUT.read_text(encoding='utf-8')))}
        for no in raiz.iter('control'):
            if no.get('type') != 'label':
                continue
            tamanho = tamanhos[(no.findtext('font') or 'wf15').strip()]
            altura = int(no.findtext('height') or 0)
            self.assertGreaterEqual(altura, round(tamanho * 1.05),
                                    (no.get('id'), altura, tamanho))

    def test_nenhum_texto_usa_cr_literal(self):
        """[CR] so vale dentro de <textbox>; em <label> viraria texto na tela."""
        raiz = _raiz()
        for no in raiz.iter('control'):
            if no.get('type') != 'textbox':
                self.assertNotIn('[CR]', no.findtext('label') or '',
                                 no.get('id'))

    def test_dialogo_tem_fundo_solido_proprio(self):
        """O texto do dialogo nao pode competir com o QR/cartao atras."""
        raiz = _raiz()
        for grupo in ('900', '950'):
            no = raiz.find(".//control[@id='%s']" % grupo)
            texturas = [(c.findtext('texture') or '').strip()
                        for c in no.findall('control')
                        if c.get('type') == 'image']
            self.assertIn('scrim.png', texturas, grupo)
            self.assertIn('dialog.png', texturas, grupo)

    def test_textos_dinamicos_usam_textbox(self):
        """Titulo/mensagem do servidor podem ser longos: <textbox> quebra."""
        raiz = _raiz()
        for ident in ('953', '954'):
            no = raiz.find('.//control[@id="%s"]' % ident)
            self.assertEqual(no.get('type'), 'textbox', ident)


class MapaDeBotoesTest(unittest.TestCase):
    """A ferramenta de mapeamento tem de continuar fechando (id <-> acao)."""

    MAPEADOR = ROOT / 'tools' / 'kodi' / 'mapear-botoes.py'

    def test_todo_botao_tem_acao_e_toda_acao_tem_botao(self):
        spec = importlib.util.spec_from_file_location('mapeador',
                                                      self.MAPEADOR)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)

        controles = modulo.controles_do_layout()
        acoes = modulo.acoes_do_python()
        sem_acao = sorted((ident for ident in controles
                           if ident not in acoes
                           and controles[ident][0] != 'edit'), key=int)
        self.assertEqual(sem_acao, [], sem_acao)
        self.assertEqual(sorted(set(acoes) - set(controles)), [])
        # os ids citados no contrato do documento existem no layout
        for ident in ('310', '311', '120', '121', '122', '123',
                      '312', '905', '906', '955'):
            self.assertIn(ident, controles, ident)

    def test_saida_json_da_ferramenta(self):
        import json
        import subprocess
        saida = subprocess.run([sys.executable, str(self.MAPEADOR), '--json'],
                               capture_output=True, text=True, check=True)
        dados = json.loads(saida.stdout)
        self.assertTrue(dados)
        for linha in dados:
            self.assertTrue(linha['ok'], linha)


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
        # Grade de 8 px: margem 56, respiro 32, entre cartoes 28. O CSS do
        # pacote pedia 2%/1.3%, mas a tela publicada (v5) usa a grade de Smart
        # TV; o XML entregue vem da v5 (medido no APK) e o gerador desenha a
        # mesma linguagem para as proximas mudancas.
        self.assertEqual(med.pad, 56)
        self.assertEqual(med.gap, 32)
        self.assertEqual(med.col_gap, 28)
        self.assertEqual(med.top_h, 96)
        self.assertEqual(med.barra_h, 104)
        self.assertEqual(med.grade_y, med.pad + med.top_h + med.gap)
        self.assertEqual(med.barra_y, med.grade_y + med.grade_h + med.gap)
        self.assertEqual(med.barra_y + med.barra_h, 1080 - med.pad)


class StartupAntesDaHomeTest(unittest.TestCase):
    def _acoes(self, caminho):
        raiz = ET.fromstring(caminho.read_bytes())
        return [(e.text or '').strip() for e in raiz.findall('onload')]

    def test_startup_da_skin_fonte_dispara_a_tela(self):
        acoes = self._acoes(STARTUP_SKIN)
        self.assertEqual(len(acoes), 3, acoes)
        self.assertIn('RunScript(%s)' % ADDON_ID, acoes[0])
        self.assertIn('smartedtv_entrada,', acoes[0])
        # o seguro agora e um processo proprio do addon (nao um AlarmClock,
        # que disparava em torno da janela de startup e deixava tela preta)
        self.assertIn('RunScript(script.smartedtv.welcome,seguro=1)', acoes[1])
        # ultimo recurso do proprio Kodi: falha do addon nao pode deixar o app
        # sem interface (ActivateWindow(Home), nunca ReplaceWindow do startup)
        self.assertIn('smartedtv_home_seguro', acoes[2])
        self.assertIn('ActivateWindow(Home)', acoes[2])
        corpo = STARTUP_SKIN.read_text(encoding='utf-8')
        corpo = corpo.split('<window>', 1)[1]
        self.assertEqual(corpo.count('ReplaceWindow'), 0)

    def test_janela_de_boot_desenha_espera_em_vez_de_preto(self):
        """A janela de startup vazia era a tela preta do boot."""
        raiz = ET.fromstring(STARTUP_SKIN.read_bytes())
        controles = raiz.findall('controls')
        self.assertEqual(len(controles), 1, 'um <controls> por janela')
        labels = [(e.text or '').strip() for e in controles[0].iter('label')]
        self.assertIn('Carregando', labels)
        self.assertIn('SMARTEDTV', labels)
        fundos = [c for c in controles[0].iter('control')
                  if (c.findtext('texture') or '').endswith('pb_white.png')]
        self.assertTrue(fundos, 'sem fundo solido = tela preta')
        # a espera nao pode depender de addon, rede ou imagem externa
        for c in controles[0].iter('texture'):
            self.assertNotIn('$INFO', c.text or '')
            self.assertNotIn('http', c.text or '')

    def test_injetor_aplica_o_mesmo_startup_no_apk(self):
        spec = importlib.util.spec_from_file_location('injetor_startup', INJETOR)
        injetor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(injetor)
        original = ('<?xml version="1.0" encoding="UTF-8"?>\n<window>\n'
                    '\t<onload>ReplaceWindow($INFO[System.StartupWindow])</onload>\n'
                    '\t<controls />\n</window>\n')
        novo = injetor.patch_startup(original.encode()).decode()
        raiz = ET.fromstring(novo.encode())
        acoes = [(e.text or '').strip() for e in raiz.findall('onload')]
        self.assertEqual(len(acoes), 3, acoes)
        self.assertIn('RunScript(%s)' % ADDON_ID, acoes[0])
        self.assertIn('seguro=1', acoes[1])
        self.assertIn('smartedtv_home_seguro', acoes[2])
        self.assertNotIn('ReplaceWindow', novo)
        # o injetor tambem deixa a espera desenhada e nunca dois <controls>
        self.assertEqual(len(raiz.findall('controls')), 1)
        self.assertEqual(novo.count('<controls'), 1)
        labels = [(e.text or '').strip() for e in raiz.iter('label')]
        self.assertIn('Carregando', labels)
        self.assertTrue(injetor.validar_startup(novo.encode()))

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
            injetor.validar_startup(quebrado.encode())


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

    def getFocusId(self):
        return self.foco[-1] if self.foco else None

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
    DROPBOX_URL = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
                   'SMARTEDTV-atual.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j'
                   '&st=p1m6ebvg&dl=0')
    APK = DROPBOX_URL.replace('&dl=0', '&dl=1')
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

    def abrir_dropbox(self):
        self.chamadas.append('dropbox')
        return True

    def compartilhar(self, texto=None):
        self.chamadas.append('compartilhar')
        return True

    def abrir_url(self, url, rotulo='link'):
        self.chamadas.append('url:%s:%s' % (rotulo or '', url))
        return True

    def open_apk_download(self):
        self.chamadas.append('url:download do APK:%s' % self.APK)
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
    xbmc.PROPS = {}
    xbmc.LOGS = []
    xbmc.LOGINFO = 1
    xbmc.LOGWARNING = 3
    xbmc.LOGERROR = 4
    xbmc.log = lambda msg, level=1: xbmc.LOGS.append((level, msg))
    xbmc.JANELA = {'atual': 'Startup'}

    def _builtin(cmd, wait=False):
        xbmc.BUILTINS.append(cmd)
        if cmd.startswith('ReplaceWindow('):
            alvo = cmd[len('ReplaceWindow('):-1]
            if alvo == '$INFO[System.StartupWindow]':
                alvo = 'Startup' if xbmc.JANELA['atual'] == 'Startup' else 'Home'
            xbmc.JANELA['atual'] = alvo
        elif cmd.startswith('ActivateWindow(Home'):
            xbmc.JANELA['atual'] = 'Home'
        elif cmd.startswith('RestartApp'):
            xbmc.JANELA['atual'] = 'Startup'

    xbmc.executebuiltin = _builtin
    xbmc.sleep = lambda ms: None
    xbmc.getInfoLabel = lambda exp: (xbmc.JANELA['atual']
                                     if exp == 'System.CurrentWindow' else '')

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
            xbmc.PROPS[chave] = valor

        def clearProperty(self, chave):
            xbmc.PROPS.pop(chave, None)

        def getProperty(self, chave):
            return xbmc.PROPS.get(chave, '')

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
        self.assertEqual(self.xbmc.PROPS.get('smartedtv.welcome.ativa'), '1')
        self.assertEqual(self.xbmc.PROPS.get('smartedtv.welcome.home'), 'ok')
        self.assertEqual(self.xbmc.JANELA['atual'], 'Home')

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
        self.assertEqual(self.vip.chamadas[1], 'dropbox')
        self.assertTrue(self.vip.chamadas[2].startswith('url:download do APK:'))
        self.assertEqual(self.vip.chamadas[3], 'atualizar')

    def test_121_abre_o_dropbox_verdadeiro_do_qr(self):
        def acoes(janela):
            janela.onClick(121)
        self._com_interacao(acoes)
        self.assertEqual(self.vip.chamadas, ['dropbox'])

    def test_122_e_123_nao_quebram_sem_ponte_android(self):
        """Fora do Android abrir_url devolve False: a tela avisa e segue."""
        def falhar(url, rotulo='link'):
            return False
        self.vip.abrir_url = falhar
        self.vip.open_apk_download = lambda: False
        self.vip.abrir_dropbox = lambda: False
        self.vip.procurar_atualizacao = lambda: False
        # sem ponte Android o proprio builtin levanta erro: a tela avisa
        executar = self.xbmc.executebuiltin

        def sem_bridge(comando, wait=False):
            if comando.startswith('StartAndroidActivity('):
                raise RuntimeError('Android bridge ausente')
            return executar(comando, wait)

        self.xbmc.executebuiltin = sem_bridge

        def acoes(janela):
            janela.onClick(122)
            assert janela.getProperty('welcome_dialog') == 'status'
            janela.onClick(955)
            janela.onClick(123)
            assert janela.getProperty('welcome_dialog') == 'status'
            janela.onClick(955)
        self._com_interacao(acoes)
        self.assertEqual(self.modulo._log.__module__, self.modulo.__name__)

    def test_foco_dos_dois_botoes_de_anuncio_e_visualmente_exclusivo(self):
        """O botao da direita nao pode parecer selecionado sem estar.

        btn_primary.png e btn_primary_focus.png eram o MESMO arquivo: o
        "Continuar com anuncios" (textura primaria) ficava branco sempre e
        parecia focado junto com o Voltar. Agora o normal e escuro e somente o
        foco fica branco.
        """
        media = ADDON / 'resources' / 'skins' / 'Default' / 'media'
        normal = (media / 'btn_primary.png').read_bytes()
        foco = (media / 'btn_primary_focus.png').read_bytes()
        self.assertNotEqual(normal, foco)
        raiz = ET.parse(LAYOUT).getroot()
        for ident in ('905', '906'):
            c = raiz.find(".//control[@id='%s']" % ident)
            self.assertTrue((c.findtext('texturefocus') or '').strip())
            self.assertTrue((c.findtext('texturenofocus') or '').strip())
        b906 = raiz.find(".//control[@id='906']")
        self.assertIn('btn_primary.png', b906.findtext('texturenofocus'))
        self.assertIn('btn_primary_focus.png', b906.findtext('texturefocus'))
        self.assertEqual((b906.findtext('textcolor') or '').strip().upper(),
                         'FFF7F7F7')
        self.assertEqual((b906.findtext('focusedcolor') or '').strip().upper(),
                         'FF080808')

    def test_dpad_continua_depois_de_abrir_o_dialogo_de_anuncios(self):
        """O foco nao pode ficar no controle coberto pelo overlay."""
        vistos = []

        def acoes(janela):
            janela.onClick(312)
            vistos.append(janela.getFocusId())
            # simula o foco perdido (controle invisivel/reload de propriedade)
            janela.foco = []
            janela.onAction(1)          # seta esquerda
            vistos.append(janela.getFocusId())
            janela.onAction(2)          # seta direita, agora ja navega
            vistos.append(janela.getFocusId())

        self._com_interacao(acoes)
        self.assertEqual(vistos[0], 905)
        self.assertEqual(vistos[1], 905)
        self.assertIn(vistos[2], (905, 906))

    def test_foco_volta_ao_botao_312_ao_fechar_o_dialogo(self):
        vistos = []

        def acoes(janela):
            janela.onClick(312)
            janela.onClick(905)
            vistos.append(janela.getFocusId())

        self._com_interacao(acoes)
        self.assertEqual(vistos, [312])

    def test_dialogo_de_status_recupera_o_foco_955(self):
        vistos = []

        def acoes(janela):
            janela.props['_codigo'] = 'SMARTED-99'
            janela.onClick(311)
            vistos.append(janela.getFocusId())
            janela.foco = []
            janela.onAction(3)          # seta para cima
            vistos.append(janela.getFocusId())

        self._com_interacao(acoes)
        self.assertEqual(vistos, [955, 955])

    def test_botoes_dos_dialogos_tem_navegacao_explicita(self):
        """Sem onleft/onright/onup/ondown o D-pad procura controles atras do overlay."""
        raiz = ET.parse(LAYOUT).getroot()
        for ident in ('905', '906', '955'):
            controle = raiz.find(".//control[@id='%s']" % ident)
            self.assertIsNotNone(controle, ident)
            for tag in ('onleft', 'onright', 'onup', 'ondown'):
                self.assertTrue((controle.findtext(tag) or '').strip(),
                                '%s sem %s' % (ident, tag))

    def test_sair_usa_quit_nativo_e_limpa_as_marcas(self):
        modulo, xbmc, _ = carregar_default()
        xbmc.BUILTINS.clear()
        xbmc.PROPS.update({'smartedtv.welcome.saiu': '1',
                           'smartedtv.welcome.home': 'ok',
                           'smartedtv.welcome.voltar': '1'})
        self.assertTrue(modulo.sair_do_aplicativo())
        self.assertEqual(xbmc.BUILTINS[-1], 'Quit')
        self.assertNotIn('RestartApp', xbmc.BUILTINS)
        self.assertFalse([b for b in xbmc.BUILTINS
                          if b.startswith(('Shutdown', 'Kill'))])
        self.assertEqual(xbmc.PROPS, {})

    def test_controles_removidos_nao_existem_mais(self):
        """Seletor de aparelho e pilulas de plano sairam do layout e do codigo."""
        ids = {c.get('id') for c in _raiz().iter('control')}
        for ident in ('130', '131', '140', '141'):
            self.assertNotIn(ident, ids, ident)
        fonte = DEFAULT_PY.read_text(encoding='utf-8')
        for ident in ('130', '131', '140', '141'):
            self.assertNotIn('control_id == %s' % ident, fonte)
        # a tela nao tem mais escolha de plano: so campo + Ativar
        self.assertNotIn('welcome_plan', fonte)

    def test_voltar_na_home_reabre_a_tela_sem_reiniciar(self):
        """Pedido do usuário: VOLTAR na Home volta para a tela (quem tem código)."""
        self.xbmc.JANELA['atual'] = 'Home'
        aberta = []
        JanelaFake.interacao = lambda j: (aberta.append(j.args),
                                          j.onClick(312), j.onClick(906))
        self.assertTrue(self.modulo.voltar_para_a_tela())
        self.assertEqual(aberta[0][0], 'DialogWelcome.xml')
        # a Home ja estava carregada: continua na Home, sem RestartApp
        self.assertEqual(self.xbmc.JANELA['atual'], 'Home')
        self.assertFalse([b for b in self.xbmc.BUILTINS
                          if b.startswith('RestartApp')], self.xbmc.BUILTINS)
        self.assertFalse([b for b in self.xbmc.BUILTINS
                          if b.startswith('ReplaceWindow')], self.xbmc.BUILTINS)
        self.assertEqual(self.xbmc.PROPS.get('smartedtv.welcome.home'), 'ok')

    def test_voltar_na_home_preserva_a_licenca(self):
        """Quem ja ativou continua ativo; a tela e que nao guarda estado."""
        self.xbmc.JANELA['atual'] = 'Home'
        self.vip.licenca = {'ativo': True, 'codigo': 'TESTE-CF9CB49C05EA'}
        JanelaFake.interacao = lambda j: j.onAction(92)   # VOLTAR na tela
        self.modulo.voltar_para_a_tela()
        # nada de validacao/rede ao abrir a tela: a licenca fica como estava
        self.assertEqual(self.vip.codigos, [])
        self.assertEqual(self.vip.chamadas, [])
        self.assertEqual(self.vip.licenca['codigo'], 'TESTE-CF9CB49C05EA')

    def test_voltar_na_home_devolve_o_campo_vazio(self):
        """O campo abre vazio, pronto para quem tem um codigo novo."""
        self.xbmc.JANELA['atual'] = 'Home'
        vistos = []
        JanelaFake.interacao = lambda j: (vistos.append(
            j.getControl(310).getText()), j.onAction(92))
        self.modulo.voltar_para_a_tela()
        self.assertEqual(vistos, [''])

    def test_voltar_duas_vezes_nao_empilha_telas(self):
        """Duas teclas seguidas nao abrem duas telas por cima da Home."""
        self.xbmc.JANELA['atual'] = 'Home'
        abertas = []

        def segura(janela):
            abertas.append(1)
            # enquanto a tela esta no ar, outro VOLTAR chega pelo keymap
            self.assertFalse(self.modulo.voltar_para_a_tela())
            janela.onAction(92)

        JanelaFake.interacao = segura
        self.assertTrue(self.modulo.voltar_para_a_tela())
        self.assertEqual(len(abertas), 1)
        # a trava e liberada quando a tela sai de cena
        self.assertEqual(self.xbmc.PROPS.get('smartedtv.welcome.voltar'), None)

    def test_voltar_sem_a_tela_nao_derruba_nada(self):
        """Se a pasta da tela sumir, VOLTAR na Home so registra e a Home fica."""
        self.xbmc.JANELA['atual'] = 'Home'
        self.modulo._pasta_da_tela = lambda: None
        self.assertFalse(self.modulo.voltar_para_a_tela())
        self.assertEqual(self.xbmc.JANELA['atual'], 'Home')

    def test_argumento_voltar_escolhe_o_modo_certo(self):
        """O keymap chama RunScript(...,voltar): modo proprio, sem vigia de boot."""
        fonte = (ADDON / 'default.py').read_text(encoding='utf-8')
        modulo = types.ModuleType('welcome_argv')
        modulo.__file__ = str(ADDON / 'default.py')
        modulo.__name__ = '__main__'
        chamadas = []
        modulo.__dict__['sys'] = sys
        modulo.__dict__['ARG_VOLTAR'] = 'voltar'
        modulo.__dict__['ARG_SAIR'] = 'sair'
        modulo.__dict__['ARG_REINICIAR'] = 'reiniciar'
        modulo.__dict__['voltar_para_a_tela'] = \
            lambda: chamadas.append('voltar')
        modulo.__dict__['sair_do_aplicativo'] = \
            lambda: chamadas.append('sair')
        modulo.__dict__['reiniciar_aplicativo'] = \
            lambda: chamadas.append('reiniciar')
        modulo.__dict__['vigiar_inicializacao'] = \
            lambda: chamadas.append('vigia')
        modulo.__dict__['abrir_tela_entrada'] = \
            lambda: chamadas.append('boot')
        codigo = textwrap.dedent(
            fonte.split("if __name__ == '__main__':", 1)[1])
        argv = sys.argv
        try:
            for args, esperado in (('voltar', 'voltar'),
                                   ('seguro=1', 'vigia'),
                                   ('sair', 'sair'),
                                   ('reiniciar', 'reiniciar'),
                                   ('', 'boot')):
                chamadas[:] = []
                sys.argv = ['default.py'] + ([args] if args else [])
                exec(compile(codigo, 'default.py', 'exec'), modulo.__dict__)
                self.assertEqual(chamadas, [esperado], args)
        finally:
            sys.argv = argv

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


class BotoesAndroidTest(unittest.TestCase):
    """IDs 120 e 121 tem de SAIR do Kodi pelo navegador do Android.

    Quando o vip.py responde False (sem ponte Android, por exemplo), a tela
    usa o builtin direto. Aqui conferimos a ordem REAL dos parametros:
    StartAndroidActivity(package,intent,dataType,dataURI). A versao anterior
    mandava a action no campo do pacote e nenhum navegador abria.
    """

    CHECKOUT = ('StartAndroidActivity(,android.intent.action.VIEW,,'
                'https://pay.cakto.com.br/nkvbegd_1323120)')
    DROPBOX = ('StartAndroidActivity(,android.intent.action.VIEW,,'
               'https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
               'SMARTEDTV-atual.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j'
               '&st=p1m6ebvg&dl=0)')
    APK = ('StartAndroidActivity(,android.intent.action.VIEW,,'
           'https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
           'SMARTEDTV-atual.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j'
           '&st=p1m6ebvg&dl=1)')

    def setUp(self):
        JanelaFake.ultima = None
        JanelaFake.falhar_modal = False
        JanelaFake.interacao = None
        self.vip = VipFake()
        # forca o caminho de fallback (builtin direto da tela)
        self.vip.abrir_checkout = lambda: False
        self.vip.abrir_dropbox = lambda: False
        self.vip.compartilhar = lambda *a, **k: False
        self.vip.open_apk_download = lambda: False
        self.vip.abrir_url = lambda *a, **k: False
        self.vip.procurar_atualizacao = lambda: False
        self.modulo, self.xbmc, self.xbmcgui = carregar_default(self.vip)
        self.addCleanup(sys.modules.pop, '_smarted_vip_stub', None)
        self.addCleanup(sys.modules.pop, 'vip', None)

    def _clique(self, controle):
        def interacao(janela):
            janela.onInit()
            janela.onClick(controle)
        JanelaFake.interacao = interacao
        self.modulo.abrir_tela_entrada()
        return JanelaFake.ultima

    def test_120_checkout_abre_o_navegador_com_a_ordem_certa(self):
        janela = self._clique(120)
        self.assertIn(self.CHECKOUT, self.xbmc.BUILTINS)
        self.assertFalse([b for b in self.xbmc.BUILTINS
                          if b.startswith('StartAndroidActivity(android.')])
        self.assertFalse([b for b in self.xbmc.BUILTINS
                          if b.startswith('PlayMedia(')], self.xbmc.BUILTINS)
        self.assertEqual(janela.getProperty('welcome_dialog'), '')

    def test_121_dropbox_abre_o_navegador_com_o_link_verdadeiro(self):
        self._clique(121)
        self.assertIn(self.DROPBOX, self.xbmc.BUILTINS)
        self.assertFalse([b for b in self.xbmc.BUILTINS
                          if b.startswith('PlayMedia(')], self.xbmc.BUILTINS)

    def test_122_baixa_o_apk_pelo_navegador(self):
        self._clique(122)
        self.assertIn(self.APK, self.xbmc.BUILTINS)

    def test_toque_longo_no_121_preserva_o_compartilhamento(self):
        def acoes(janela):
            janela.setFocusId(121)
            janela.onAction(117)          # ACTION_CONTEXT_MENU (toque longo)
        JanelaFake.interacao = lambda j: (j.onInit(), acoes(j))
        self.modulo.abrir_tela_entrada()
        envios = [b for b in self.xbmc.BUILTINS
                  if b.startswith('StartAndroidActivity(,android.intent.action.SEND,')]
        self.assertEqual(len(envios), 1, self.xbmc.BUILTINS)
        self.assertIn('android.intent.extra.TEXT', envios[0])


class TVBoxStickTest(unittest.TestCase):
    """A mesma tela precisa funcionar em TV/box/projetor/stick (overscan)."""

    TV = ADDON / 'resources' / 'skins' / 'Default' / '1080i' / 'DialogWelcomeTV.xml'

    def test_variante_tv_tem_area_segura_e_o_campo_310(self):
        self.assertTrue(self.TV.is_file(), 'DialogWelcomeTV.xml ausente')
        raiz = ET.parse(self.TV).getroot()
        self.assertEqual(raiz.findtext('defaultcontrol'), '310')
        for ident in ('10', '11', '12'):
            topo = int(raiz.find(".//control[@id='%s']/top" % ident).text)
            self.assertGreaterEqual(topo, 60, 'logo/titulo no overscan: %s' % ident)
        for ident in ('6', '60', '61', '310', '311', '312'):
            controle = raiz.find(".//control[@id='%s']" % ident)
            topo = int(controle.findtext('top'))
            altura = int(controle.findtext('height') or '0')
            self.assertLessEqual(topo + altura, 1000,
                                 'linha do codigo no overscan: %s' % ident)
        self.assertIn('setas', raiz.find(".//control[@id='61']/label").text.lower())
        # 5% de overscan lateral: nada de texto/logo antes de x=96
        for ident in ('10', '60', '61'):
            esquerda = int(raiz.find(".//control[@id='%s']/left" % ident).text)
            self.assertGreaterEqual(esquerda, 96, 'texto no overscan: %s' % ident)

    def test_detecta_tv_por_resolucao_e_nao_por_celular(self):
        modulo, xbmc, _ = carregar_default()
        xbmc.getCondVisibility = lambda consulta: True
        xbmc.getInfoLabel = lambda info: (
            '1920x1080 @ 60.00 Hz - Fullscreen'
            if info == 'System.ScreenResolution' else '')
        self.assertTrue(modulo._parece_tv())
        # Projetor antigo 4:3/16:10 tambem e tela grande, mas nao e celular.
        for resolucao in ('1024x768 @ 60.00 Hz - Fullscreen',
                          '1280x800 @ 60.00 Hz - Fullscreen',
                          '3840x2160 @ 60.00 Hz - Fullscreen'):
            xbmc.getInfoLabel = lambda info, r=resolucao: (
                r if info == 'System.ScreenResolution' else '')
            self.assertTrue(modulo._parece_tv(), resolucao)
        xbmc.getInfoLabel = lambda info: (
            '2400x1080 @ 60.00 Hz - Fullscreen'
            if info == 'System.ScreenResolution' else '')
        self.assertFalse(modulo._parece_tv())

    def test_escolhe_o_xml_da_variante(self):
        modulo, _, _ = carregar_default()
        modulo._modo_tv = lambda: True
        self.assertEqual(modulo._xml_da_tela(str(ADDON)), 'DialogWelcomeTV.xml')
        modulo._modo_tv = lambda: False
        self.assertEqual(modulo._xml_da_tela(str(ADDON)), 'DialogWelcome.xml')
