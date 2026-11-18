# -*- coding: utf-8 -*-
"""Saida limpa: Quit nativo pela tela de entrada, sem matar processo."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MENU = ROOT / 'kodi' / 'skin.novatv' / 'xml' / 'ShutdownMenu.xml'
MENU_ATIVO = ROOT / 'kodi' / 'skin.novatv' / 'xml' / 'DialogButtonMenu.xml'
WELCOME = ROOT / 'kodi' / 'addons' / 'script.smartedtv.welcome' / 'default.py'


class SaidaLimpaTest(unittest.TestCase):
    def test_menu_energia_sai_pela_tela_de_entrada(self):
        for caminho in (MENU_ATIVO, MENU):
            raiz = ET.parse(caminho).getroot()
            sair = raiz.find(".//control[@id='3504']")
            self.assertIsNotNone(sair, caminho)
            self.assertEqual(
                (sair.findtext('onclick') or '').strip(),
                'RunScript(script.smartedtv.welcome,sair)', caminho)
            self.assertEqual((sair.findtext('visible') or '').strip(), 'true',
                             caminho)
            # Reiniciar passa pela tela para limpar as marcas ANTES do
            # RestartApp (restart com estado sujo = Home preta).
            reiniciar = raiz.find(".//control[@id='3508']")
            self.assertEqual((reiniciar.findtext('onclick') or '').strip(),
                             'RunScript(script.smartedtv.welcome,reiniciar)',
                             caminho)

    def test_reiniciar_limpa_o_estado_antes_do_restartapp(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        trecho = fonte[fonte.index('def reiniciar_aplicativo'):]
        trecho = trecho[:trecho.index('\ndef ', 1)]
        self.assertIn('CancelAlarm(smartedtv_home_seguro', trecho)
        self.assertIn('_limpar_guarda_de_saida()', trecho)
        self.assertIn("executebuiltin('RestartApp')", trecho)
        self.assertLess(trecho.index('_limpar_guarda_de_saida()'),
                        trecho.index("executebuiltin('RestartApp')"))

    def test_saida_tem_guarda_para_processo_reutilizado(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        self.assertIn('def _soltar_processo_se_quit_travar', fonte)
        self.assertIn('os._exit(0)', fonte)
        self.assertIn('System.Platform.Android', fonte)
        self.assertNotIn('os.kill', fonte)
        self.assertNotIn("executebuiltin('Shutdown", fonte)
        self.assertNotIn("executebuiltin('Kill", fonte)

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


class GuildaDeSaidaNaoMataSessaoNovaTest(unittest.TestCase):
    """Tela preta + app saindo sozinho ao REABRIR logo depois de sair.

    Causa encontrada: o ultimo recurso da saida era um thread com sleep(15) e
    os._exit(0). Se o Android reabria o app antes dos 15 s (ou reutilizava o
    processo Python), o thread antigo matava a sessao NOVA. Agora o recurso e
    um AlarmClock do Kodi + arquivo-marca da saida com o instante.
    """

    def test_saida_nao_usa_thread_dormindo_nem_mata_por_conta_propria(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        trecho = fonte[fonte.index('def sair_do_aplicativo'):]
        self.assertNotIn('threading.Thread', trecho)
        self.assertNotIn('os._exit', trecho)
        self.assertIn('AlarmClock(smartedtv_sair_guarda', trecho)
        self.assertIn('_marcar_saida(', trecho)

    def test_guarda_confere_o_token_da_sessao_antes_de_encerrar(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        trecho = fonte[fonte.index('def _soltar_processo_se_quit_travar'):]
        trecho = trecho[:trecho.index('\ndef ', 1)]
        self.assertIn('_instante_de_saida()', trecho)
        self.assertIn('abs(desde - float(token)) > 1.0', trecho)
        self.assertLess(trecho.index('_instante_de_saida()'),
                        trecho.index('os._exit'))

    def test_boot_cancela_o_guarda_da_saida_anterior(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        trecho = fonte[fonte.index('def _limpar_guarda_de_saida'):]
        trecho = trecho[:trecho.index('\ndef ', 1)]
        self.assertIn('CancelAlarm(smartedtv_sair_guarda', trecho)
        self.assertIn('JANELA_SAIDA', trecho)
        self.assertIn('_limpar_marca_de_saida()', trecho)
        # chamada na ida para a Home (todo caminho de boot passa por ali)
        home = fonte[fonte.index('def _ir_para_home'):]
        self.assertIn('_limpar_guarda_de_saida()', home[:2000])
