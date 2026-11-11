"""Teste funcional do Brazuca Play fora do Kodi.

Prova que o addon entregue no perfil inicia e lista o menu principal (o sintoma
relatado era a interface abrir vazia com erro no addon). Roda apenas quando um
perfil real é informado, porque depende dos arquivos do APK base:

    SMARTED_PROFILE=/caminho/do/.kodi python3 -m unittest tests.test_brazucaplay_runtime

O harness usa stubs de ``xbmc*`` e não acessa a rede para montar o menu.
"""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tests' / 'kodi_plugin_stubs' / 'run_plugin.py'
PROFILE = os.environ.get('SMARTED_PROFILE', '')
MENU = ['TV AO VIVO', 'FILMES', 'SÉRIES', 'DESENHOS', 'DORAMAS', 'ANIMES',
        'NOVELAS', 'CONFIGURAÇÕES', 'VERIFICAR UPDATES']


@unittest.skipUnless(PROFILE and Path(PROFILE).is_dir(),
                     'defina SMARTED_PROFILE com um perfil .kodi semeado')
class BrazucaPlayRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = subprocess.run(
            [sys.executable, str(RUNNER), PROFILE],
            capture_output=True, text=True, timeout=600)
        cls.output = cls.result.stdout

    def test_plugin_executa_sem_excecao(self):
        self.assertIn('RUN OK', self.output, self.output[-2000:])
        self.assertNotIn('EXCEPTION', self.output)

    def test_menu_principal_fica_completo(self):
        for label in MENU:
            self.assertIn(label, self.output, 'item ausente: %s' % label)

    def test_nao_mostra_erro_de_dados(self):
        # nenhuma notificação de falha ao carregar o conteúdo principal
        self.assertNotIn('Erro ao Carregar os dados', self.output)


if __name__ == '__main__':
    unittest.main()
