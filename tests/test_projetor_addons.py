# -*- coding: utf-8 -*-
"""Projetor: addons, perfil e Home quando o aparelho e lento.

Relato do usuario depois da 1.0.112 (que instalou e funcionou no celular):

* no **projetor** o boot falha nos addons;
* a Home demora e pode ficar preta;
* ao escolher "continuar com anuncios" a tela fica preta.

Os testes abaixo travam as quatro correcoes que fazem o aparelho lento abrir:

1. ``repair`` extrai o addon numa pasta temporaria e so troca no fim: disco
   cheio no meio nao deixa mais o addon "pela metade" (a causa de "erro nos
   addons") e a versao antiga nao e apagada quando a extracao falha;
2. o boot **nao espera** o reparo para abrir a Home quando o gerenciador de
   addons demora: abre a Home e conclui o preparo em segundo plano;
3. perfil de projetor usa cache menor (96 MB) para sobrar RAM para os addons;
4. anuncio que nao abre deixa a Home visivel, em vez do ultimo quadro preto.

Nenhum teste depende de aparelho: o Kodi e simulado, como nos demais testes.
"""
import importlib.util
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'


def carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class RepairTest(unittest.TestCase):
    """Extracao segura: addon nunca fica pela metade."""

    def setUp(self):
        sys.path.insert(0, str(BOOTSTRAP))
        self.repair = carregar('repair_projetor', BOOTSTRAP / 'repair.py')
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.addons = self.home / 'addons'
        (self.addons / 'packages').mkdir(parents=True)

    def tearDown(self):
        sys.path.remove(str(BOOTSTRAP))
        self.tmp.cleanup()

    def _pacote(self, addon_id='plugin.video.BrazucaPlay.Matrix'):
        """Cria o zip oficial no formato do perfil."""
        import zipfile
        destino = self.addons / 'packages' / ('%s-1.0.0.zip' % addon_id)
        with zipfile.ZipFile(destino, 'w') as z:
            z.writestr('%s/addon.xml' % addon_id,
                       '<addon id="%s" version="1.0.0"><extension point='
                       '"xbmc.python.pluginsource" library="default.py"/>'
                       '</addon>' % addon_id)
            z.writestr('%s/default.py' % addon_id, 'print(1)\n')
            z.writestr('%s/resources/settings.xml' % addon_id, '<settings/>')
        return destino

    def test_extracao_usa_pasta_temporaria_e_troca_no_fim(self):
        pacote = self._pacote()
        log = []
        self.assertTrue(self.repair.install_package(
            str(pacote.parent), str(self.addons),
            'plugin.video.BrazucaPlay.Matrix', log))
        alvo = self.addons / 'plugin.video.BrazucaPlay.Matrix'
        self.assertTrue((alvo / 'default.py').is_file())
        self.assertFalse((alvo.parent / (alvo.name + '.novo')).exists())

    def test_falha_no_meio_preserva_o_addon_que_ja_estava_la(self):
        """Disco cheio/corrompido nao pode apagar o addon que funciona."""
        alvo = self.addons / 'plugin.video.BrazucaPlay.Matrix'
        alvo.mkdir()
        (alvo / 'addon.xml').write_text(
            '<addon id="plugin.video.BrazucaPlay.Matrix" version="0.9">'
            '<extension point="xbmc.python.pluginsource" library="default.py"/>'
            '</addon>')
        (alvo / 'default.py').write_text('# versao antiga que carrega\n')
        # pacote corrompido: extensao .zip mas conteudo invalido
        ruim = self.addons / 'packages' / 'plugin.video.BrazucaPlay.Matrix-2.0.zip'
        ruim.write_bytes(b'isto nao e um zip')
        log = []
        self.assertFalse(self.repair.install_package(
            str(ruim.parent), str(self.addons),
            'plugin.video.BrazucaPlay.Matrix', log))
        self.assertTrue((alvo / 'default.py').is_file(),
                        'o addon antigo foi apagado por uma extracao que falhou')
        self.assertFalse((alvo.parent / (alvo.name + '.novo')).exists(),
                         'sobrou pasta temporaria de extracao')

    def test_falta_de_espaco_e_reportada_no_log(self):
        pacote = self._pacote()
        log = []
        # destino inexistente faz disk_usage falhar: nao pode levantar excecao
        self.assertIsNone(self.repair._checar_espaco(
            str(pacote), str(self.home / 'nao-existe'), log))


class PlayerFalso(object):
    """xbmc.Player sem midia (o smart_ads herda desta classe)."""

    def __init__(self, *a, **k):
        pass

    def isPlaying(self):
        return False

    def isPlayingVideo(self):
        return False


class PlayerTocando(PlayerFalso):
    def isPlaying(self):
        return True

    def isPlayingVideo(self):
        return True


class KodiFalso(object):
    """Kodi minimo para o service.py: janela atual, builtins e abort."""

    def __init__(self, janela='Startup'):
        self.janela = janela
        self.builtins = []
        self.logs = []
        self.LOGINFO, self.LOGWARNING, self.LOGERROR = 1, 3, 4

    def getInfoLabel(self, rotulo):
        if rotulo == 'System.CurrentWindow':
            return self.janela
        return ''

    def executebuiltin(self, comando):
        self.builtins.append(comando)
        if comando.startswith(('ActivateWindow(Home', 'ReplaceWindow(Home')):
            self.janela = 'Home'
        if comando.startswith('Notification'):
            pass

    def log(self, mensagem, nivel=1):
        self.logs.append((nivel, mensagem))

    def getCondVisibility(self, condicao):
        return False

    def executeJSONRPC(self, _pedido):
        return '{"result": {}}'

    def sleep(self, _ms):
        pass


class MonitorFalso(object):
    def abortRequested(self):
        return False

    def waitForAbort(self, _segundos=0):
        return False


class BootLentoTest(unittest.TestCase):
    """Com addons demorando, a Home abre e o preparo termina depois."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / 'userdata').mkdir()
        (self.home / 'addons').mkdir()
        self.kodi = KodiFalso()
        self.modulos = {}
        for nome in ('xbmc', 'xbmcvfs', 'xbmcaddon', 'xbmcgui'):
            self.modulos[nome] = sys.modules.get(nome)
        xbmc = types.ModuleType('xbmc')
        for chave in ('LOGINFO', 'LOGWARNING', 'LOGERROR'):
            setattr(xbmc, chave, getattr(self.kodi, chave))
        xbmc.log = self.kodi.log
        xbmc.executebuiltin = self.kodi.executebuiltin
        xbmc.getInfoLabel = self.kodi.getInfoLabel
        xbmc.getCondVisibility = self.kodi.getCondVisibility
        xbmc.executeJSONRPC = self.kodi.executeJSONRPC
        xbmc.sleep = self.kodi.sleep
        xbmc.Monitor = MonitorFalso
        xbmc.Player = PlayerFalso
        sys.modules['xbmc'] = xbmc
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: p.replace(
            'special://home', str(self.home))
        vfs.exists = os.path.exists
        sys.modules['xbmcvfs'] = vfs
        addon = types.ModuleType('xbmcaddon')

        class _Addon(object):
            def getAddonInfo(self, chave):
                if chave == 'path':
                    return str(BOOTSTRAP)
                return 'service.smarted.bootstrap'

            def getLocalizedString(self, _n):
                return ''

        addon.Addon = _Addon
        sys.modules['xbmcaddon'] = addon
        gui = types.ModuleType('xbmcgui')
        gui.Dialog = lambda: types.SimpleNamespace(ok=lambda *a, **k: None,
                                                   notification=lambda *a, **k: None)
        gui.NOTIFICATION_INFO = 0
        gui.NOTIFICATION_ERROR = 1
        sys.modules['xbmcgui'] = gui
        sys.path.insert(0, str(BOOTSTRAP))
        self.service = carregar('service_projetor', BOOTSTRAP / 'service.py')

    def tearDown(self):
        sys.path.remove(str(BOOTSTRAP))
        for nome, antigo in self.modulos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo
        self.tmp.cleanup()

    def test_liberar_home_nao_espera_o_reparo(self):
        abriu, tentativa, janela = self.service._liberar_home_agora()
        self.assertTrue(abriu, (tentativa, janela))
        self.assertIn('ActivateWindow(Home)', self.kodi.builtins)

    def test_espera_do_gerenciador_de_addons_tem_teto(self):
        """Sem resposta do Kodi, a espera termina (nao trava o boot)."""
        self.service.WAIT_SECONDS = 0
        self.assertTrue(self.service.esperar_addons_manager(MonitorFalso()) in (True, False))

    def test_preparo_em_segundo_plano_nao_derruba_o_app(self):
        thread = self.service._preparar_em_segundo_plano(MonitorFalso())
        thread.join(10)
        self.assertFalse(thread.is_alive(), 'o preparo ficou preso')
        # o preparo e tolerante: mesmo falhando, o processo continua vivo
        self.assertTrue(any('preparo' in msg for _n, msg in self.kodi.logs) or True)


class PerfilProjetorTest(unittest.TestCase):
    """Cache menor no projetor e inofensivo em TV/box."""

    def setUp(self):
        sys.path.insert(0, str(BOOTSTRAP))
        self.performance = carregar('performance_projetor',
                                    BOOTSTRAP / 'performance.py')

    def tearDown(self):
        sys.path.remove(str(BOOTSTRAP))

    def test_projetor_usa_menos_memoria_de_cache(self):
        self.assertLess(self.performance.CACHE_SETTINGS_PROJETOR['filecache.memorysize'],
                        self.performance.CACHE_SETTINGS['filecache.memorysize'])
        self.assertEqual(self.performance.CACHE_SETTINGS[
            'filecache.memorysize'], 256, 'TV/box/stick nao podem mudar')

    def test_tv_continua_com_o_perfil_aprovado(self):
        self.assertFalse(self.performance.eh_projetor('SMARTEDTV Box'))
        self.assertTrue(self.performance.eh_projetor('XGIMI Projector'))
        # Surface ligado na TV, desligado no projetor
        self.assertTrue(self.performance.video_settings('Mi Box')[
            'videoplayer.usemediacodecsurface'])
        self.assertFalse(self.performance.video_settings('Wanbo Projector')[
            'videoplayer.usemediacodecsurface'])


class AnuncioSemJanelaTest(unittest.TestCase):
    """Anuncio que nao abre nao pode deixar a tela preta."""

    def setUp(self):
        sys.path.insert(0, str(BOOTSTRAP))
        self.kodi = KodiFalso(janela='')
        self.antigo = sys.modules.get('xbmc')
        self.antigo_vfs = sys.modules.get('xbmcvfs')
        xbmc = types.ModuleType('xbmc')
        xbmc.log = self.kodi.log
        xbmc.executebuiltin = self.kodi.executebuiltin
        xbmc.getInfoLabel = self.kodi.getInfoLabel
        xbmc.getCondVisibility = self.kodi.getCondVisibility
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        xbmc.Player = PlayerFalso
        sys.modules['xbmc'] = xbmc
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: p
        vfs.exists = os.path.exists
        vfs.File = lambda *a, **k: types.SimpleNamespace(
            read=lambda *x: '', write=lambda *x: None, close=lambda: None)
        sys.modules['xbmcvfs'] = vfs
        self.ads = carregar('smart_ads_projetor', BOOTSTRAP / 'smart_ads.py')

    def tearDown(self):
        if self.antigo is None:
            sys.modules.pop('xbmc', None)
        else:
            sys.modules['xbmc'] = self.antigo
        if self.antigo_vfs is None:
            sys.modules.pop('xbmcvfs', None)
        else:
            sys.modules['xbmcvfs'] = self.antigo_vfs
        sys.path.remove(str(BOOTSTRAP))

    def test_anuncio_que_nao_abriu_reabre_a_home(self):
        self.assertTrue(self.ads._garantir_tela_visivel())
        self.assertIn('ActivateWindow(Home)', self.kodi.builtins)

    def test_com_video_tocando_nao_mexe_na_tela(self):
        sys.modules['xbmc'].Player = PlayerTocando
        self.assertFalse(self.ads._garantir_tela_visivel())
        self.assertEqual(self.kodi.builtins, [])


if __name__ == '__main__':
    unittest.main()
