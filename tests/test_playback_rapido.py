# -*- coding: utf-8 -*-
"""Partida rapida do player (1.0.59): cache curto, leitura 20x e boot sem I/O.

O que abre o player e o Brazuca Play (o resolve e dele). O que este projeto
controla — e o que os testes abaixo travam — e o caminho do player no Kodi:
quanto o Kodi espera de buffer, em que velocidade le os trechos, se troca de
modo de video ao abrir e se alguma tarefa nossa disputa a rede no clique.
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi/addons/service.smarted.bootstrap'
PERF = BOOTSTRAP / 'performance.py'
SERVICE = BOOTSTRAP / 'service.py'
BUILD = ROOT / 'tools/kodi/build-release-apk.py'
FLUXO = ROOT / '.github/workflows/build-release-classica.yml'


def modulo_performance():
    sys.path.insert(0, str(BOOTSTRAP))
    try:
        import performance
    finally:
        sys.path.pop(0)
    return performance


class AdvancedSettingsTest(unittest.TestCase):
    def setUp(self):
        self.performance = modulo_performance()

    def test_buffer_curto_para_o_primeiro_frame(self):
        corpo = self.performance.ADVANCED_TEMPLATE
        # 1 = cache so de stream da internet (nao segura arquivo local nem tudo)
        self.assertIn('<buffermode>1</buffermode>', corpo)
        # 50 MB: enche rapido (antes eram 256 MB e o play esperava encher)
        self.assertIn('<memorysize>52428800</memorysize>', corpo)
        # 20x o bitrate (antes 10x)
        self.assertIn('<readfactor>20.0</readfactor>', corpo)

    def test_timeouts_de_rede_curtos(self):
        corpo = self.performance.ADVANCED_TEMPLATE
        self.assertIn('<curlclienttimeout>15</curlclienttimeout>', corpo)
        self.assertIn('<curllowspeedtime>20</curllowspeedtime>', corpo)

    def test_marker_novo_para_trocar_o_arquivo_antigo(self):
        # o arquivo gravado por builds antigas tem outro marker: e reescrito
        self.assertEqual(self.performance.MARKER, 'smartedtv-performance-v2')


class SettingsDoPlayerTest(unittest.TestCase):
    def setUp(self):
        self.performance = modulo_performance()

    def test_cache_e_leitura(self):
        cache = self.performance.CACHE_SETTINGS
        self.assertEqual(cache['filecache.buffermode'], 1)
        self.assertEqual(cache['filecache.memorysize'], 48)   # menor valor cheio da lista
        self.assertEqual(cache['filecache.readfactor'], 2000)  # 20x

    def test_sem_troca_de_modo_de_video_ao_abrir(self):
        # cada ajuste de Hz custa 1-3 s de tela preta antes do primeiro frame
        self.assertEqual(self.performance.VIDEO_SETTINGS['videoplayer.adjustrefreshrate'], 0)
        self.assertTrue(self.performance.VIDEO_SETTINGS['videoplayer.usemediacodec'])
        self.assertTrue(self.performance.VIDEO_SETTINGS['videoplayer.usemediacodecsurface'])


class BootSemDisputaTest(unittest.TestCase):
    def setUp(self):
        self.fonte = SERVICE.read_text(encoding='utf-8')
        self.main = self.fonte[self.fonte.index('def main():'):]

    def test_performance_antes_do_nav_check(self):
        self.assertLess(self.main.index('performance = apply_performance()'),
                        self.main.index('validar_navegacao_depois_do_boot'))

    def test_nav_check_em_segundo_plano(self):
        self.assertIn('NAV_CHECK_DELAY', self.fonte)
        self.assertIn("name='nav-check'", self.fonte.replace('"', "'"))
        self.assertIn('daemon = True', self.main)
        # a varredura de pastas nao pode voltar para a linha do boot
        self.assertNotIn('navegacao = rodar_validacao_navegacao(log)',
                         self.main.split('def validar_navegacao_depois_do_boot')[0])

    def test_nav_check_respeita_reproducao(self):
        trecho = self.fonte[self.fonte.index('def validar_navegacao_depois_do_boot'):
                            self.fonte.index('def main():')]
        self.assertIn('_tocando_video()', trecho)
        self.assertIn('isPlayingVideo()', self.fonte)


class FluxoDeBuildTest(unittest.TestCase):
    def test_build_reembarca_o_bootstrap(self):
        script = BUILD.read_text(encoding='utf-8')
        self.assertIn('--bridge-addons', script)
        fluxo = FLUXO.read_text(encoding='utf-8')
        self.assertIn('--bridge-addons service.smarted.bootstrap', fluxo)

    def test_fluxo_parte_da_1_0_58_e_publica_1_0_59(self):
        fluxo = FLUXO.read_text(encoding='utf-8')
        self.assertIn('--from-version 1.0.58', fluxo)
        self.assertIn('ece4fb03cde87beb7fb351c3683c1cb5f834eb6270783daf97429eaca7cee6cf', fluxo)
        self.assertIn('VERSAO_NOVA: "1.0.59"', fluxo)
        self.assertIn('CODIGO_NOVO: "2103045"', fluxo)
        self.assertIn('v1.0.59-classica', fluxo)


if __name__ == '__main__':
    unittest.main()
