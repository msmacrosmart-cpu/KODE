# -*- coding: utf-8 -*-
"""Saida limpa: Quit nativo pela tela de entrada, sem matar processo."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / 'kodi' / 'skin.novatv' / 'xml' / 'ShutdownMenu.xml'
WELCOME = ROOT / 'kodi' / 'addons' / 'script.smartedtv.welcome' / 'default.py'


class SaidaLimpaTest(unittest.TestCase):
    def test_menu_energia_sai_pela_tela_de_entrada(self):
        raiz = ET.parse(MENU).getroot()
        sair = raiz.find(".//control[@id='3504']")
        self.assertIsNotNone(sair)
        self.assertEqual(
            (sair.findtext('onclick') or '').strip(),
            'RunScript(script.smartedtv.welcome,sair)')
        self.assertEqual((sair.findtext('visible') or '').strip(), 'true')
        reiniciar = raiz.find(".//control[@id='3508']")
        self.assertIn('RestartApp', reiniciar.findtext('onclick') or '')

    def test_saida_fecha_janelas_e_pede_quit_nativo(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        trecho = fonte[fonte.index('def sair_do_aplicativo'):]
        trecho = trecho[:trecho.index('\ndef ', 1)] if '\ndef ' in trecho[1:] else trecho
        self.assertIn('Dialog.Close(all,true)', trecho)
        self.assertIn("'Quit'", trecho)
        self.assertNotIn('os.kill', trecho)
        self.assertNotIn('executebuiltin(\'Kill', trecho)
        self.assertNotIn('executebuiltin(\'Shutdown', trecho)


if __name__ == '__main__':
    unittest.main()
