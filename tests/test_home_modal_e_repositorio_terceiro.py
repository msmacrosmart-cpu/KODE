# -*- coding: utf-8 -*-
"""Home recusada por dialogo modal e repositorio de terceiro no perfil.

Duas coisas que o kodi.log do projetor mostrou e que nao podem voltar:

1. "Activate of window '10000' refused because there are active modal dialogs"
   - o Kodi recusa abrir a Home quando existe dialogo modal na tela; era isso
   que deixava o app vivo, a tela de entrada fechada e nenhuma Home. O caminho
   da Home precisa fechar esses dialogos ANTES de pedir a janela.
2. O perfil traz repositorios de terceiros (redwizard, elementumorg,
   alado.tv, nostr-oneplay, vkkodi/One.repo) e o service.xbmc.versioncheck,
   que chama `uname` e estoura no Android. Cada um vira atualizacao falhando e
   "Add-on com erro" no projetor. Eles saem do perfil do aparelho, com o
   registro no log e o vinculo apagado do banco de addons.
"""
import ast
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WELCOME = RAIZ / 'kodi' / 'addons' / 'script.smartedtv.welcome' / 'default.py'


class HomeComDialogoModalTest(unittest.TestCase):
    """O caminho da Home fecha dialogo modal antes de pedir ActivateWindow."""

    def setUp(self):
        self.fonte = WELCOME.read_text(encoding='utf-8')
        self.arvore = ast.parse(self.fonte)

    def _funcao(self, nome):
        for no in ast.walk(self.arvore):
            if isinstance(no, ast.FunctionDef) and no.name == nome:
                return no
        raise AssertionError('funcao %s nao encontrada' % nome)

    def _comandos(self, funcao):
        """Sequencia de strings de executebuiltin dentro da funcao."""
        achados = []
        for no in ast.walk(funcao):
            if isinstance(no, ast.Call):
                for argumento in no.args:
                    if isinstance(argumento, ast.Constant) and isinstance(argumento.value, str):
                        achados.append(argumento.value)
        return achados

    def test_antes_do_activatewindow_a_tela_fecha_dialogos(self):
        funcao = self._funcao('_ir_para_home')
        comandos = self._comandos(funcao)
        posicoes_home = [i for i, c in enumerate(comandos) if c.startswith('ActivateWindow(Home')]
        posicoes_close = [i for i, c in enumerate(comandos) if c == 'Dialog.Close(all,true)']
        self.assertTrue(posicoes_home, 'o caminho da Home nao pede ActivateWindow')
        self.assertTrue(posicoes_close, 'falta fechar dialogo modal antes da Home')
        self.assertLess(min(posicoes_close), min(posicoes_home),
                        'Dialog.Close tem de vir ANTES do primeiro ActivateWindow(Home)')

    def test_o_motivo_esta_escrito_no_codigo(self):
        self.assertIn('modal', self.fonte.lower())
        self.assertIn("refused because there are active modal", self.fonte)


class ServicoLimpaPerfil(object):
    def __init__(self):
        self.home = tempfile.mkdtemp()
        self.kodi = os.path.join(self.home, '.kodi')
        self.addons = os.path.join(self.kodi, 'addons')
        self.database = os.path.join(self.kodi, 'userdata', 'Database')
        os.makedirs(self.addons)
        os.makedirs(self.database)
        for addon in ('repository.redwizard', 'repository.elementumorg',
                      'repository.alado.tv', 'One.repo',
                      'service.xbmc.versioncheck', 'repository.xbmc.org',
                      'plugin.video.youtube', 'plugin.program.openwizard',
                      'plugin.audio.mp3streams',
                      'plugin.video.BrazucaPlay.Matrix', 'script.module.requests'):
            os.makedirs(os.path.join(self.addons, addon))
            with open(os.path.join(self.addons, addon, 'addon.xml'), 'w') as saida:
                saida.write('<addon id="%s"><extension library="default.py"/></addon>' % addon)
            with open(os.path.join(self.addons, addon, 'default.py'), 'w') as saida:
                saida.write('# ok\n')
        import sqlite3
        self.banco = os.path.join(self.database, 'Addons33.db')
        conexao = sqlite3.connect(self.banco)
        conexao.execute('CREATE TABLE repo (id INTEGER PRIMARY KEY, addonID TEXT)')
        conexao.execute('CREATE TABLE addonlinkrepo (id INTEGER, addonID TEXT)')
        for addon in ('repository.redwizard', 'repository.elementumorg', 'One.repo'):
            conexao.execute('INSERT INTO repo (addonID) VALUES (?)', (addon,))
            conexao.execute('INSERT INTO addonlinkrepo (addonID) VALUES (?)', (addon,))
        conexao.commit()
        conexao.close()
        self.modulo = self._carregar()

    def _carregar(self):
        spec = importlib.util.spec_from_file_location(
            'simular_servico_perfil2', RAIZ / 'tools' / 'kodi' / 'simular-servico.py')
        ferramenta = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ferramenta)
        ok, dados = ferramenta.simular(str(RAIZ / 'kodi' / 'addons' /
                                            'service.smarted.bootstrap'))
        assert ok, dados.get('traceback')
        servico = sys.modules['service']
        traduzir = lambda caminho: caminho.replace('special://home', self.kodi)
        servico.xbmc.translatePath = traduzir
        # no aparelho as duas funcoes apontam para o mesmo lugar
        servico.xbmcvfs.translatePath = traduzir
        self.chamados = []
        servico.xbmc.executebuiltin = self.chamados.append
        return servico

    def limpar(self):
        shutil.rmtree(self.home, ignore_errors=True)


class PerfilSemTerceirosTest(unittest.TestCase):
    def setUp(self):
        self.aparelho = ServicoLimpaPerfil()

    def tearDown(self):
        self.aparelho.limpar()

    def test_repositorio_de_terceiro_sai_do_perfil(self):
        registros = []
        removidos = self.aparelho.modulo.limpar_repositorios_de_terceiros(registros.append)
        self.assertIn('repository.redwizard', removidos)
        self.assertIn('repository.elementumorg', removidos)
        self.assertIn('One.repo', removidos)
        self.assertIn('service.xbmc.versioncheck', removidos)
        # os nomes exatos das notificacoes reclamadas no projetor
        self.assertIn('plugin.video.youtube', removidos)
        self.assertIn('plugin.program.openwizard', removidos)
        self.assertIn('plugin.audio.mp3streams', removidos)
        restantes = sorted(os.listdir(self.aparelho.addons))
        self.assertIn('repository.xbmc.org', restantes)
        self.assertIn('plugin.video.BrazucaPlay.Matrix', restantes)
        self.assertIn('script.module.requests', restantes)
        self.assertNotIn('repository.redwizard', restantes)
        self.assertNotIn('plugin.video.youtube', restantes)
        self.assertNotIn('plugin.program.openwizard', restantes)
        self.assertTrue(any('retirados do perfil' in linha for linha in registros),
                        'a remocao precisa ficar registrada no log')

    def test_o_banco_de_addons_esquece_o_repositorio(self):
        self.aparelho.modulo.limpar_repositorios_de_terceiros()
        import sqlite3
        conexao = sqlite3.connect(self.aparelho.banco)
        try:
            sobraram = [l[0] for l in conexao.execute('SELECT addonID FROM repo')]
        finally:
            conexao.close()
        self.assertEqual([], sobraram,
                         'com o id no banco o Kodi continua tentando o repositorio')

    def test_pede_ao_kodi_para_reler_os_addons(self):
        self.aparelho.modulo.limpar_repositorios_de_terceiros()
        self.assertIn('UpdateLocalAddons()', self.aparelho.chamados)

    def test_roda_duas_vezes_sem_erro(self):
        self.aparelho.modulo.limpar_repositorios_de_terceiros()
        self.assertEqual([], self.aparelho.modulo.limpar_repositorios_de_terceiros())


if __name__ == '__main__':
    unittest.main()
