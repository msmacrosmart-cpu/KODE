# -*- coding: utf-8 -*-
"""IDs 120/121 no vip.py: navegador externo do Android, sem abrir no Kodi.

Confere a ordem real do builtin do Kodi:
``StartAndroidActivity(package,intent,dataType,dataURI[,flags,extras])``.
Package vazio = intent implicito (o Android escolhe o navegador padrao).
"""
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'vip.py'
ADDON = ROOT / 'kodi' / 'addons' / 'script.smartedtv.welcome'

CHECKOUT = 'https://pay.cakto.com.br/nkvbegd_1323120'
DROPBOX = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
           'SMARTEDTV-atual.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j'
           '&st=p1m6ebvg&dl=0')
APK = DROPBOX.replace('&dl=0', '&dl=1')


def carregar_vip():
    xbmc = types.ModuleType('xbmc')
    xbmc.BUILTINS = []
    xbmc.LOGINFO = 1
    xbmc.LOGWARNING = 3
    xbmc.LOGERROR = 4
    xbmc.LOGS = []
    xbmc.log = lambda msg, level=1: xbmc.LOGS.append((level, msg))
    xbmc.executebuiltin = lambda cmd: xbmc.BUILTINS.append(cmd)
    xbmc.getCondVisibility = lambda cond: False

    xbmcaddon = types.ModuleType('xbmcaddon')

    class Addon(object):
        def __init__(self, ident=None):
            self.ident = ident

        def getAddonInfo(self, chave):
            return 'service.smarted.bootstrap' if chave == 'id' else ''

    xbmcaddon.Addon = Addon

    class Dialog(object):
        def ok(self, *args):
            pass

        def notification(self, *args):
            pass

    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.Dialog = Dialog
    xbmcgui.NOTIFICATION_INFO = 0
    xbmcgui.NOTIFICATION_ERROR = 1

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda p: p
    xbmcvfs.exists = lambda p: False

    nomes = ('xbmc', 'xbmcgui', 'xbmcaddon', 'xbmcvfs')
    salvos = {nome: sys.modules.get(nome) for nome in nomes}
    sys.modules.update({'xbmc': xbmc, 'xbmcgui': xbmcgui,
                        'xbmcaddon': xbmcaddon, 'xbmcvfs': xbmcvfs})
    try:
        spec = importlib.util.spec_from_file_location('vip_teste', VIP)
        modulo = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(VIP.parent)] + sys.path):
            spec.loader.exec_module(modulo)
    finally:
        for nome, antigo in salvos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo
    return modulo, xbmc


class VipBotoesAndroidTest(unittest.TestCase):
    def setUp(self):
        self.vip, self.xbmc = carregar_vip()

    def test_enderecos_saem_do_projeto(self):
        self.assertEqual(self.vip.CHECKOUT, CHECKOUT)
        # o link do Dropbox e o mesmo do QR qr_apk.png (com rlkey; sem ele o
        # link /scl/fi/ nao abre). Nao e um endereco inventado.
        self.assertEqual(self.vip.DROPBOX_URL, DROPBOX)
        self.assertIn('rlkey=yp1ijxk6fdtcqm93gzi24ig5j', self.vip.DROPBOX_URL)
        self.assertEqual(self.vip.APK, APK)

    def test_120_abre_o_checkout_no_navegador(self):
        self.assertTrue(self.vip.abrir_checkout())
        self.assertEqual(self.xbmc.BUILTINS,
                         ['StartAndroidActivity(,android.intent.action.VIEW,,%s)'
                          % CHECKOUT])

    def test_121_abre_o_dropbox_no_navegador(self):
        self.assertTrue(self.vip.abrir_dropbox())
        self.assertEqual(self.xbmc.BUILTINS,
                         ['StartAndroidActivity(,android.intent.action.VIEW,,%s)'
                          % DROPBOX])

    def test_122_baixa_o_apk_direto(self):
        self.assertTrue(self.vip.open_apk_download())
        self.assertEqual(self.xbmc.BUILTINS,
                         ['StartAndroidActivity(,android.intent.action.VIEW,,%s)'
                          % APK])

    def test_nenhum_comando_coloca_a_action_no_lugar_do_pacote(self):
        for funcao in (self.vip.abrir_checkout, self.vip.abrir_dropbox,
                       self.vip.open_apk_download):
            funcao()
        for comando in self.xbmc.BUILTINS:
            self.assertTrue(comando.startswith(
                'StartAndroidActivity(,android.intent.action.VIEW,,'), comando)
            self.assertNotIn('StartAndroidActivity(android.intent', comando)
            self.assertNotIn('PlayMedia(', comando)

    def test_compartilhar_usa_action_send_com_extras(self):
        self.assertTrue(self.vip.compartilhar())
        comando = self.xbmc.BUILTINS[-1]
        self.assertTrue(comando.startswith(
            'StartAndroidActivity(,android.intent.action.SEND,'), comando)
        self.assertIn('android.intent.extra.TEXT', comando)
        self.assertIn(APK, comando)

    def test_layout_tem_os_dois_botoes(self):
        import xml.etree.ElementTree as ET
        raiz = ET.parse(ADDON / 'resources' / 'skins' / 'Default' / '1080i' /
                        'DialogWelcome.xml').getroot()
        for ident, rotulo in (('120', 'Abrir checkout'),
                              ('121', 'Compartilhar link')):
            controle = raiz.find(".//control[@id='%s']" % ident)
            self.assertIsNotNone(controle, ident)
            self.assertEqual((controle.findtext('label') or '').strip(),
                             rotulo, ident)
            self.assertEqual(controle.get('type'), 'button')


if __name__ == '__main__':
    unittest.main()
