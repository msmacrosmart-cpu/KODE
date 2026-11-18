# -*- coding: utf-8 -*-
"""Reabertura do app: tela preta e app saindo sozinho.

Reproduz, fora do aparelho, o ciclo real de USUARIO:

    abre -> Home -> sai (menu Energia) -> abre de novo em segundos

com a semântica que o Kodi executa (AlarmClock, CancelAlarm, Quit, janela
10000, xbmcvfs sobre o perfil). Foi assim que o defeito apareceu:

1. a janela de startup (Startup.xml) era VAZIA — nada desenhado enquanto o
   Python subia: tela preta;
2. o último recurso da saída era um thread com `sleep(15)` + `os._exit(0)`.
   Reabrindo antes dos 15 s — ou com o processo Python reutilizado — o thread
   antigo matava a sessão NOVA: tela preta e app "fechando sozinho";
3. o cache da barra era gravado direto no arquivo: encerrar no meio deixava
   JSON truncado e a Home seguinte abria sem os botões.

Não substitui aparelho/emulador, mas falha se qualquer um desses três voltar.
"""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TELA = ROOT / 'kodi' / 'addons' / 'script.smartedtv.welcome' / 'default.py'
STARTUP = ROOT / 'kodi' / 'skin.estilo.personalizado' / 'xml' / 'Startup.xml'
NAVEGACAO = ROOT / 'kodi' / 'addons' / 'plugin.video.smarted' / 'navigation.py'


class KodiDeMentira(object):
    """Kodi mínimo: alarmes, builtins, janela 10000 e propriedades."""

    def __init__(self, perfil):
        self.perfil = perfil
        self.alarmes = {}
        self.builtins = []
        self.props = {}
        self.janela_atual = 'Startup'
        self.logs = []
        self.instante = 1000.0

    # --- tempo -------------------------------------------------------------
    def avancar(self, segundos):
        """Passa o tempo e devolve os alarmes que venceram (sem executar)."""
        alvo = self.instante + segundos
        vencidos = []
        while True:
            prontos = [(nome, h) for nome, h in self.alarmes.items()
                       if h['quando'] <= alvo]
            if not prontos:
                break
            nome, h = min(prontos, key=lambda item: item[1]['quando'])
            self.instante = h['quando']
            del self.alarmes[nome]
            vencidos.append((nome, h['comando']))
        self.instante = alvo
        return vencidos

    def relogio(self):
        return self.instante


def carregar_modulo(kodi):
    """Carrega default.py com xbmc/xbmcgui/xbmcvfs/xbmcaddon de mentira."""

    def traduzir(caminho):
        return (caminho.replace('special://profile/', kodi.perfil + '/')
                       .replace('special://home/', kodi.perfil + '/home/'))

    xbmc = types.ModuleType('xbmc')
    xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
    xbmc.log = lambda msg, level=1: kodi.logs.append((level, msg))

    def builtin(cmd, wait=False):
        kodi.builtins.append(cmd)
        if cmd.startswith('AlarmClock('):
            corpo = cmd[len('AlarmClock('):-1]
            if corpo.endswith(',silent'):
                corpo = corpo[:-len(',silent')]
            # horário é sempre H:MM ou H:MM:SS; o que vem antes é nome+comando
            horario = corpo.rsplit(',', 1)[1]
            resto = corpo.rsplit(',', 1)[0]
            nome, comando = resto.split(',', 1)
            quando = horario
            try:
                h, m, s = [int(x) for x in quando.split(':')]
            except ValueError:
                h, m, s = 0, 0, 0
            kodi.alarmes[nome] = {
                'comando': comando,
                'quando': kodi.instante + h * 3600 + m * 60 + s}
        elif cmd.startswith('CancelAlarm('):
            kodi.alarmes.pop(cmd[len('CancelAlarm('):-1].split(',')[0], None)
        elif cmd.startswith('ActivateWindow(Home'):
            kodi.janela_atual = 'Home'
        elif cmd == 'Quit':
            kodi.janela_atual = 'SamdoProcesso'

    xbmc.executebuiltin = builtin
    xbmc.sleep = lambda ms: None
    xbmc.getCondVisibility = lambda cond: 'Android' in cond
    xbmc.getInfoLabel = lambda exp: (kodi.janela_atual
                                     if exp == 'System.CurrentWindow' else '')

    class Player(object):
        def isPlaying(self):
            return False

    xbmc.Player = Player

    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.ACTION_NAV_BACK = 92
    xbmcgui.ACTION_PREVIOUS_MENU = 10
    xbmcgui.INPUT_ALPHANUM = 0
    xbmcgui.NOTIFICATION_INFO = 0
    xbmcgui.WindowXMLDialog = object

    class Window(object):
        def __init__(self, *args):
            pass

        def setProperty(self, chave, valor):
            kodi.props[chave] = valor

        def clearProperty(self, chave):
            kodi.props.pop(chave, None)

        def getProperty(self, chave):
            return kodi.props.get(chave, '')

    xbmcgui.Window = Window
    xbmcgui.Dialog = type('Dialog', (object,), {
        'ok': lambda self, *a: None, 'notification': lambda self, *a: None,
        'input': lambda self, *a, **k: ''})

    xbmcaddon = types.ModuleType('xbmcaddon')

    class Addon(object):
        def __init__(self, *a):
            pass

        def getAddonInfo(self, chave):
            return str(TELA.parent) if chave == 'path' else ''

    xbmcaddon.Addon = Addon

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = traduzir
    xbmcvfs.exists = lambda p: os.path.exists(traduzir(p))

    def mkdirs(p):
        os.makedirs(traduzir(p), exist_ok=True)
        return True

    class Arquivo(object):
        def __init__(self, caminho, modo='r'):
            self.caminho = traduzir(caminho)
            self.modo = modo
            self.handle = None

        def write(self, dados):
            if self.handle is None:
                pasta = os.path.dirname(self.caminho)
                if pasta:
                    os.makedirs(pasta, exist_ok=True)
                self.handle = open(self.caminho, self.modo)
            self.handle.write(dados)
            return True

        def read(self):
            modo = 'rb' if 'b' in self.modo else 'r'
            with open(self.caminho, modo) as stream:
                return stream.read()

        def close(self):
            if self.handle is not None:
                self.handle.close()
                self.handle = None

    xbmcvfs.mkdirs = mkdirs
    xbmcvfs.File = Arquivo
    xbmcvfs.delete = lambda p: (os.remove(traduzir(p)) or True)

    modulos = {'xbmc': xbmc, 'xbmcgui': xbmcgui, 'xbmcaddon': xbmcaddon,
               'xbmcvfs': xbmcvfs, 'vip': types.ModuleType('vip')}
    salvos = {nome: sys.modules.get(nome) for nome in modulos}
    sys.modules.update(modulos)
    try:
        spec = importlib.util.spec_from_file_location('welcome_reabertura', TELA)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    finally:
        for nome, anterior in salvos.items():
            if anterior is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anterior
    # tempo controlado: o módulo usa time.time() para a marca da saída
    modulo.time = types.SimpleNamespace(
        time=lambda: kodi.instante + 1_700_000_000,
        sleep=lambda s: None)
    modulo.os.getpid = lambda: 4242
    return modulo, kodi


class ReaberturaTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.perfil = self.temp.name
        self.kodi = KodiDeMentira(self.perfil)
        self.modulo, self.kodi = carregar_modulo(self.kodi)

    def test_janela_de_boot_nunca_fica_preta(self):
        raiz = ET.parse(STARTUP).getroot()
        controles = raiz.find('controls')
        self.assertIsNotNone(controles)
        self.assertGreaterEqual(len(list(controles)), 3)
        labels = [(e.text or '').strip() for e in controles.iter('label')]
        self.assertIn('SMARTEDTV', labels)
        self.assertIn('Carregando', labels)
        # fundo desenhado: sem isto a janela e o preto puro
        fundos = [c for c in controles.iter('control')
                  if (c.findtext('texture') or '').endswith('pb_white.png')]
        self.assertTrue(fundos)
        # e nada que so o addon poderia resolver
        for info in controles.iter('label'):
            self.assertNotIn('$INFO', info.text or '')

    def test_startup_tem_ultimo_recurso_sem_python(self):
        raiz = ET.parse(STARTUP).getroot()
        acoes = [(e.text or '').strip() for e in raiz.findall('onload')]
        seguros = [a for a in acoes if 'smartedtv_home_seguro' in a]
        self.assertEqual(len(seguros), 1)
        self.assertIn('ActivateWindow(Home)', seguros[0])
        # e o script cancela esse alarme quando a Home abre
        fonte = TELA.read_text(encoding='utf-8')
        self.assertIn("CancelAlarm(%s,silent)' % ALARME_SEGURO", fonte)

    def test_sair_e_reabrir_nao_mata_a_sessao_nova(self):
        """O bug do usuário: sai, abre de novo e a tela fica preta/sai.

        Antes: o guarda da saída (sleep 15 + os._exit) sobrevivia à reabertura
        e encerrava a sessão nova. Agora ele é um AlarmClock que o boot novo
        cancela ao encontrar a marca de saída recente.
        """
        # 1ª sessão: sai pelo menu Energia
        self.modulo.sair_do_aplicativo()
        self.assertIn('Quit', self.kodi.builtins)
        self.assertEqual(self.kodi.janela_atual, 'SamdoProcesso')
        alarme = [c for c in self.kodi.builtins
                  if c.startswith('AlarmClock(smartedtv_sair_guarda,')]
        self.assertEqual(len(alarme), 1)
        # HH:MM:SS — "00:15" seria quinze MINUTOS e nao segundos
        self.assertIn(',00:00:15,', alarme[0])
        self.assertIn('smartedtv_sair_guarda', self.kodi.alarmes)
        self.assertTrue(os.path.exists(
            os.path.join(self.perfil, 'addon_data', 'script.smartedtv.welcome',
                         'smarted-saindo')))
        # 2ª sessão: o app é reaberto 3 s depois (processo reutilizado)
        self.kodi.instante += 3
        self.kodi.janela_atual = 'Startup'
        self.modulo._limpar_guarda_de_saida()
        # comum: o alarme antigo já não existe
        self.assertNotIn('smartedtv_sair_guarda', self.kodi.alarmes)
        # pior caso: o alarme do Kodi dispara de qualquer forma
        self.modulo._soltar_processo_se_quit_travar(15, token=1000.0)
        vencidos = self.kodi.avancar(20)
        # nenhum alarme desta sessão vai encerrar nada
        self.assertFalse([c for _n, c in vencidos if 'seguro_quit' in c])
        # nada de "app saindo sozinho": a sessão nova continua viva
        self.assertEqual(self.kodi.janela_atual, 'Startup')
        self.assertEqual([b for b in self.kodi.builtins if b == 'Quit'], ['Quit'])
        # a marca foi limpa: a próxima saída grava outra
        self.assertFalse(os.path.exists(
            os.path.join(self.perfil, 'addon_data', 'script.smartedtv.welcome',
                         'smarted-saindo')))

    def test_abrir_a_tela_ja_desarma_o_guarda_da_sessao_anterior(self):
        """Nenhum caminho de abertura pode herdar o guarda armado."""
        self.modulo.sair_do_aplicativo()
        self.assertIn('smartedtv_sair_guarda', self.kodi.alarmes)
        self.kodi.instante += 3
        self.modulo.abrir_tela_entrada()
        self.assertNotIn('smartedtv_sair_guarda', self.kodi.alarmes)

    def test_guarda_ainda_encerra_quando_a_saida_realmente_trava(self):
        """Se ninguém reabriu, o último recurso continua funcionando."""
        self.modulo.sair_do_aplicativo()
        instante = self.modulo._instante_de_saida()
        self.assertTrue(instante)
        encerrou = []

        def falso_exit(code):
            encerrou.append(code)
            raise SystemExit(code)

        self.modulo.os._exit = falso_exit
        with self.assertRaises(SystemExit):
            self.modulo._soltar_processo_se_quit_travar(15, token=instante)
        self.assertEqual(encerrou, [0])

    def test_home_nova_cancela_o_alarme_de_seguranca(self):
        self.modulo._ir_para_home('teste')
        self.assertIn('CancelAlarm(smartedtv_home_seguro,silent)',
                      self.kodi.builtins)
        # e abriu a Home de verdade
        self.assertIn('ActivateWindow(Home)', self.kodi.builtins)
        self.assertEqual(self.kodi.janela_atual, 'Home')


class CacheDaBarraTest(unittest.TestCase):
    def _modulo(self):
        salvos = sys.path[:]
        sys.path.insert(0, str(NAVEGACAO.parent))
        try:
            spec = importlib.util.spec_from_file_location('nav_reabertura',
                                                          NAVEGACAO)
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
        finally:
            sys.path[:] = salvos
        return modulo

    def test_gravacao_e_atomica_e_truncado_e_descartado(self):
        modulo = self._modulo()
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, 'navegacao.json')
            entradas = [{'label': 'Filmes', 'url': 'u', 'playable': False,
                         'origem': 'menu'}]
            self.assertTrue(modulo.save_cache(caminho, entradas, 'menu'))
            self.assertEqual(modulo.load_cache(caminho), entradas)
            self.assertFalse(os.path.exists(caminho + '.tmp'))
            # simula encerramento no meio da gravação
            with open(caminho, 'w', encoding='utf-8') as stream:
                stream.write('{"data": "2026-11-18", "entr')
            self.assertIsNone(modulo.load_cache(caminho))
            self.assertFalse(os.path.exists(caminho))


if __name__ == '__main__':
    unittest.main()
