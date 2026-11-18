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

    def test_saida_nao_encerra_o_proprio_processo(self):
        """Fechar e nao abrir mais: o guarda que matava o processo saiu."""
        fonte = WELCOME.read_text(encoding='utf-8')
        self.assertIn('def nao_encerrar_o_processo', fonte)
        self.assertNotIn('os._exit(', fonte)
        self.assertNotIn('os.kill(', fonte)
        self.assertNotIn("executebuiltin('Shutdown", fonte)
        self.assertNotIn("executebuiltin('Kill", fonte)
        self.assertNotIn("executebuiltin('RestartApp')", _trecho(fonte, 'def sair_do_aplicativo'))

    def test_saida_fecha_janelas_e_pede_quit_nativo(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        trecho = _trecho(fonte, 'def sair_do_aplicativo')
        self.assertIn('Dialog.Close(all,true)', trecho)
        self.assertIn("'Quit'", trecho)
        self.assertNotIn('os.kill', trecho)
        self.assertNotIn('executebuiltin(\'Kill', trecho)
        self.assertNotIn('executebuiltin(\'Shutdown', trecho)


if __name__ == '__main__':
    unittest.main()


def _trecho(fonte, inicio):
    """Do inicio do def ate o proximo def de mesmo nivel."""
    trecho = fonte[fonte.index(inicio):]
    return trecho[:trecho.index('\ndef ', 1)] if '\ndef ' in trecho[1:] else trecho


class ReaberturaDepoisDeSairTest(unittest.TestCase):
    """App fechado volta a abrir: sem matar processo e direto na Home."""

    def test_boot_reconhece_reabertura_e_vai_para_a_home(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        self.assertIn('def _veio_de_uma_saida', fonte)
        # a marca da saida e consumida no boot (senao a proxima saida herdaria
        # uma marca vencida) e o desvio para a Home passa pela ativacao
        abertura = _trecho(fonte, 'def abrir_tela_entrada')
        self.assertIn('_limpar_marca_de_saida()', abertura)
        self.assertIn('ativacao_concluida()', abertura)
        self.assertIn('_ir_para_home', abertura)

    def test_abertura_normal_nao_repete_a_tela_de_ativacao(self):
        """Kodi normal: a tela de ativacao e de primeira abertura."""
        fonte = WELCOME.read_text(encoding='utf-8')
        self.assertIn('MARCA_ENTRADA_VISTA', fonte)
        self.assertIn('def entrada_ja_vista', fonte)
        self.assertIn('def marcar_entrada_vista', fonte)
        # a marca e gravada SO no sucesso da ativacao por codigo; sair pela
        # tela (inclusive pelo caminho gratuito, com anuncios) nao libera a Home
        sucesso = _trecho(fonte, 'def _concluir_validacao')
        self.assertIn('marcar_entrada_vista()', sucesso)
        sair = _trecho(fonte, 'def _sair(')
        self.assertNotIn('marcar_entrada_vista()', sair)
        livre = _trecho(fonte, 'def _modo_gratuito(')
        self.assertNotIn('marcar_entrada_vista()', livre)
        # e o boot decide pela ativacao ANTES de abrir a tela
        abertura = _trecho(fonte, 'def abrir_tela_entrada')
        self.assertIn('ativacao_concluida()', abertura)
        self.assertLess(abertura.index('ativacao_concluida()'),
                        abertura.index('_pasta_da_tela()'))
        # a decisao exige a licenca, nao apenas o arquivo-marca
        decisao = _trecho(fonte, 'def ativacao_concluida')
        self.assertIn('vip.ativa()', decisao)
        # a marca e apenas registro: nao pode ser a unica condicao da Home
        self.assertNotIn('return entrada_ja_vista()', decisao)
        self.assertNotIn('entrada_ja_vista() or', decisao)

    def test_marca_de_saida_sobrevive_ao_processo(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        marca = _trecho(fonte, 'def _marcar_saida')
        self.assertIn('xbmcvfs.File', marca)
        self.assertIn('os.getpid()', marca)


class GuildaDeSaidaNaoMataSessaoNovaTest(unittest.TestCase):
    """Tela preta + app saindo sozinho ao REABRIR logo depois de sair.

    Causa encontrada: o ultimo recurso da saida era um thread com sleep(15) e
    os._exit(0). Se o Android reabria o app antes dos 15 s (ou reutilizava o
    processo Python), o thread antigo matava a sessao NOVA. Agora o recurso e
    um AlarmClock do Kodi + arquivo-marca da saida com o instante.
    """

    def test_saida_nao_usa_thread_dormindo_nem_mata_por_conta_propria(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        trecho = _trecho(fonte, 'def sair_do_aplicativo')
        self.assertNotIn('threading.Thread', trecho)
        self.assertNotIn('os._exit', trecho)
        self.assertIn('_marcar_saida(', trecho)
        # a marca fica gravada ANTES do Quit: o proximo boot sabe que reabriu
        self.assertLess(trecho.index('_marcar_saida('), trecho.index("'Quit'"))

    def test_alarme_da_saida_nao_dispara_o_vigia_de_boot(self):
        """`seguro_quit` contem 'seguro': na ordem antiga abria o vigia de boot."""
        fonte = WELCOME.read_text(encoding='utf-8')
        trecho = fonte[fonte.index("argumentos = [a.lower()"):]
        self.assertLess(trecho.index("a.startswith('seguro_quit')"),
                        trecho.index("if any('seguro' in a for a in argumentos)"))
        # e o alarme que chamava isso nao e mais armado na saida
        saida = _trecho(fonte, 'def sair_do_aplicativo')
        self.assertNotIn('AlarmClock(smartedtv_sair_guarda', saida)
        self.assertIn("'Quit'", saida)

    def test_boot_limpa_a_marca_da_saida_anterior(self):
        fonte = WELCOME.read_text(encoding='utf-8')
        trecho = _trecho(fonte, 'def _limpar_guarda_de_saida')
        self.assertIn('CancelAlarm(smartedtv_sair_guarda', trecho)
        self.assertIn('_limpar_marca_de_saida()', trecho)
        # chamada na ida para a Home (todo caminho de boot passa por ali)
        home = fonte[fonte.index('def _ir_para_home'):]
        self.assertIn('_limpar_guarda_de_saida()', home[:2000])
