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
                      'plugin.audio.mp3streams', 'audioencoder.kodi.builtin.aac',
                      'plugin.video.BrazucaPlay.Matrix', 'script.module.requests'):
            os.makedirs(os.path.join(self.addons, addon))
            if addon == 'service.xbmc.versioncheck':
                corpo = ('<addon id="%s"><requires>'
                         '<import addon="audioencoder.kodi.builtin.aac" version="1.0.2"/>'
                         '</requires><extension library="default.py"/></addon>' % addon)
            else:
                corpo = ('<addon id="%s"><extension library="default.py"/></addon>' % addon)
            with open(os.path.join(self.addons, addon, 'addon.xml'), 'w') as saida:
                saida.write(corpo)
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
        self.assertNotIn('repository.elementumorg', removidos)
        self.assertIn('One.repo', removidos)
        self.assertIn('service.xbmc.versioncheck', removidos)
        # os nomes exatos das notificacoes reclamadas no projetor
        self.assertIn('plugin.video.youtube', removidos)
        self.assertIn('plugin.program.openwizard', removidos)
        self.assertIn('plugin.audio.mp3streams', removidos)
        restantes = sorted(os.listdir(self.aparelho.addons))
        self.assertIn('repository.xbmc.org', restantes)
        self.assertIn('repository.elementumorg', restantes)
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

    def test_limpeza_repetida_ate_o_perfil_ficar_limpo(self):
        """O Kodi reabre no MESMO boot os addons de servico antigos.

        Medido no projetor: a limpeza apagava YouTube/OpenWizard e o Kodi, que
        leu a lista antes, reabria os dois no mesmo boot ->
        [plugin.video.youtube] ModuleNotFoundError: youtube_plugin.kodion.items.*
        [COLOR limegreen]OpenWizard: [First Run] Skipping Save Data Settings
        Por isso a limpeza roda em rodadas ate nao sobrar terceiro.
        """
        servico = self.aparelho.modulo
        rodadas = []

        class Monitor(object):
            def abortRequested(self):
                return False

            def waitForAbort(self, segundos):
                return False

        original = servico.limpar_repositorios_de_terceiros
        real = original

        def limpar(log=None):
            rodadas.append(1)
            if len(rodadas) == 1:
                # o Kodi recria a pasta do YouTube antes da 2a rodada
                caminho = os.path.join(self.aparelho.addons, 'plugin.video.youtube')
                os.makedirs(caminho, exist_ok=True)
                return []
            return real(log)

        servico.limpar_repositorios_de_terceiros = limpar
        try:
            registros = []
            servico.garantir_perfil_sem_terceiros(Monitor(), registros.append)
        finally:
            servico.limpar_repositorios_de_terceiros = original
        self.assertGreaterEqual(len(rodadas), 2,
                                'a limpeza precisa repetir ate ficar limpo')
        self.assertFalse(os.path.isdir(os.path.join(
            self.aparelho.addons, 'plugin.video.youtube')))
        self.assertTrue(any('perfil limpo' in linha for linha in registros),
                        'cada rodada precisa ficar no log')

    def test_estagio_de_semeadura_com_terceiros_e_apagado(self):
        """O APK instala o perfil por um estagio .smarted-seed-*; se ele sobra,
        o YouTube/OpenWizard voltam a ser carregados dali."""
        estagio = os.path.join(self.aparelho.kodi, '.smarted-seed-teste')
        for addon in ('plugin.video.youtube', 'plugin.program.openwizard'):
            os.makedirs(os.path.join(estagio, 'addons', addon))
        # um estagio sem terceiros (rascunho normal) NAO pode ser apagado
        limpo = os.path.join(self.aparelho.kodi, '.smarted-seed-limpo')
        os.makedirs(os.path.join(limpo, 'addons', 'skin.novatv'))
        registros = []
        removidos = self.aparelho.modulo.limpar_repositorios_de_terceiros(
            registros.append)
        self.assertIn('.smarted-seed-teste', removidos)
        self.assertFalse(os.path.isdir(estagio))
        self.assertTrue(os.path.isdir(limpo), 'rascunho sem terceiros fica')

    def test_dependencia_obrigatoria_do_aparelho_nunca_sai(self):
        """O log do projetor provou: sem o audioencoder o Kodi nao inicia.

        critical: addon 'audioencoder.kodi.builtin.aac' not installed or not enabled.
        critical: CServiceManager::InitStageTwo: Unable to start CAddonMgr
        """
        registros = []
        removidos = self.aparelho.modulo.limpar_repositorios_de_terceiros(
            registros.append)
        self.assertNotIn('audioencoder.kodi.builtin.aac', removidos)
        self.assertTrue(os.path.isdir(os.path.join(
            self.aparelho.addons, 'audioencoder.kodi.builtin.aac')),
            'audioencoder nao existe no perfil: o Kodi nao inicia sem ele')
        protegidos = self.aparelho.modulo.dependencias_obrigatorias(
            self.aparelho.addons)
        self.assertIn('audioencoder.kodi.builtin.aac', protegidos)

    def test_limpeza_de_addon_quebrado_respeita_a_dependencia(self):
        # addon sem addon.xml, mas declarado como dependencia obrigatoria
        pasta = os.path.join(self.aparelho.addons, 'xbmc.python')
        os.makedirs(pasta)
        self.aparelho.modulo.limpar_addons_quebrados()
        self.assertTrue(os.path.isdir(pasta),
                        'dependencia obrigatoria sem arquivo nao pode ser apagada')

    def test_roda_duas_vezes_sem_erro(self):
        self.aparelho.modulo.limpar_repositorios_de_terceiros()
        self.assertEqual([], self.aparelho.modulo.limpar_repositorios_de_terceiros())


if __name__ == '__main__':
    unittest.main()
