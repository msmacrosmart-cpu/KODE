# -*- coding: utf-8 -*-
"""Suite dedicada da v1.0.152: 3 testes por funcionalidade solicitada."""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
BRIDGE = ROOT / 'kodi' / 'addons' / 'plugin.video.smarted'


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeKodiEnv(object):
    def __init__(self, profile_dir, tv=False):
        self.profile_dir = profile_dir
        self.tv = tv
        self.playing = False
        self.playing_file = ''
        self.time_pos = 0.0
        self.labels = {}
        self.paused = False
        self.fullscreen = True
        self.builtins = []
        self.logs = []
        self.ad_count = 0

    def make_modules(self):
        env = self
        xbmc = types.ModuleType('xbmc')
        xbmc.LOGINFO = 1
        xbmc.LOGWARNING = 3

        class PlayerBase(object):
            def __init__(self):
                pass

            def isPlaying(self):
                return env.playing

            def isPlayingVideo(self):
                return env.playing

            def getPlayingFile(self):
                return env.playing_file

            def getTime(self):
                return env.time_pos

            def seekTime(self, s):
                env.time_pos = float(s)

        xbmc.Player = PlayerBase
        xbmc.Monitor = object
        xbmc.getInfoLabel = lambda k: env.labels.get(k, '')

        def cond(c):
            if 'Paused' in c:
                return env.paused
            if 'fullscreenvideo' in c.lower():
                return env.fullscreen
            if c == 'VideoPlayer.Content(live)':
                return False
            if 'Android' in c:
                return False
            return False

        xbmc.getCondVisibility = cond

        def builtin(cmd):
            env.builtins.append(cmd)
            if cmd.startswith('PlayMedia('):
                alvo = cmd[len('PlayMedia("'):-2] if 'PlayMedia("' in cmd else cmd[10:-1]
                env.playing = True
                env.playing_file = alvo

        xbmc.executebuiltin = builtin

        def rpc(payload):
            req = json.loads(payload)
            if req['method'] == 'Player.GetActivePlayers':
                if env.playing:
                    return json.dumps({'result': [{'playerid': 1, 'type': 'video'}]})
                return json.dumps({'result': []})
            return json.dumps({'result': 'OK'})

        xbmc.executeJSONRPC = rpc
        xbmc.log = lambda msg, lvl=1: env.logs.append(msg)

        xbmcvfs = types.ModuleType('xbmcvfs')

        def translate(p):
            if p == 'special://profile':
                return env.profile_dir
            if p.startswith('special://profile/'):
                return os.path.join(env.profile_dir, p[len('special://profile/'):])
            return p

        xbmcvfs.translatePath = translate
        xbmcvfs.exists = lambda p: os.path.exists(translate(p))

        xbmcgui = types.ModuleType('xbmcgui')
        xbmcgui.Window = lambda *a, **k: types.SimpleNamespace(
            getProperty=lambda *x: '', setProperty=lambda *x: None, clearProperty=lambda *x: None
        )
        return {'xbmc': xbmc, 'xbmcvfs': xbmcvfs, 'xbmcgui': xbmcgui}


class TestFuncionalidade1AnunciosTvAoVivo(unittest.TestCase):
    """3 testes: TV ao vivo (canal + anuncio + retorno ao canal) e troca rapida."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='smarted152-')
        os.makedirs(os.path.join(self.tmp, 'addon_data', 'service.smarted.bootstrap'), exist_ok=True)
        self._saved_sys_path = list(sys.path)
        sys.path.insert(0, str(BOOTSTRAP))

    def tearDown(self):
        sys.path[:] = self._saved_sys_path
        for mod_name in ('smart_ads', 'ads_regra', 'ad_return', 'ao_vivo', 'vip'):
            sys.modules.pop(mod_name, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _boot(self, tv=False):
        env = FakeKodiEnv(self.tmp, tv=tv)
        mods = env.make_modules()
        vip_mod = types.ModuleType('vip')
        vip_mod.ativa = lambda: False
        mods['vip'] = vip_mod
        patcher = patch.dict(sys.modules, mods)
        patcher.start()
        self.addCleanup(patcher.stop)

        ao_vivo = _load_module('ao_vivo', BOOTSTRAP / 'ao_vivo.py')
        ads_regra = _load_module('ads_regra', BOOTSTRAP / 'ads_regra.py')
        ad_return = _load_module('ad_return', BOOTSTRAP / 'ad_return.py')
        sys.modules['ao_vivo'] = ao_vivo
        sys.modules['ads_regra'] = ads_regra
        sys.modules['ad_return'] = ad_return
        smart_ads = _load_module('smart_ads', BOOTSTRAP / 'smart_ads.py')
        sys.modules['smart_ads'] = smart_ads

        smart_ads.e_tv = lambda: tv
        smart_ads.android = lambda: False
        smart_ads._vigiar_imagem = lambda *a, **k: None
        return env, smart_ads, ads_regra, ad_return

    def test_1_1_celular_box_canal_anuncio_retorno_ao_canal_sem_repetir(self):
        env, smart_ads, ads_regra, _ = self._boot(tv=False)

        def fake_abrir_anuncio(atividade, log=None, uri=''):
            env.ad_count += 1
            # Enquanto o anuncio AdMob abre na frente, o stream continuo cai
            env.playing = False
            mon.onPlayBackEnded()
            return True

        smart_ads.abrir_anuncio = fake_abrir_anuncio
        mon = smart_ads.MonitorPreRoll(log=lambda m, *a: env.logs.append(m))
        mon._vigiar_imagem = lambda *a, **k: None

        # 1) Abre Canal 1 via proxy local temporario (porta fechada no retorno)
        env.playing = True
        env.playing_file = 'http://192.168.0.15:59123/?url=http%3A%2F%2Fcdn.exemplo%2Fglobo.m3u8'
        env.labels['VideoPlayer.ChannelName'] = 'Globo HD'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(env.ad_count, 1)

        # 2) Vigia de retorno detecta queda pos-anuncio e reabre a URL real do canal
        retomada = mon._retomada()
        estado = retomada.guardado()
        self.assertIsNotNone(estado)
        with patch('time.sleep', return_value=None):
            clock = [100.0]
            def fake_mono():
                clock[0] += 0.6
                return clock[0]
            with patch('time.monotonic', side_effect=fake_mono):
                retomada.vigiar(mon, estado)

        # Canal reaberto na URL real direta (fora do proxy morto)
        self.assertTrue(env.playing)
        self.assertEqual(env.playing_file, 'http://cdn.exemplo/globo.m3u8')

        # 3) Kodi dispara onPlayBackStarted + onAVStarted no retorno ao canal -> SEM 2o anuncio!
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(env.ad_count, 1)

    def test_1_2_tv_vast_canal_anuncio_retorno_e_reconexao_sem_repetir(self):
        env, smart_ads, _, _ = self._boot(tv=True)

        def fake_vast(atividade, log=None, uri=''):
            env.ad_count += 1
            # VAST restaura o canal na URL real desencapsulada do proxy
            env.playing = True
            env.playing_file = 'http://cdn.exemplo/sportv.m3u8'
            return True

        smart_ads.abrir_anuncio = fake_vast
        mon = smart_ads.MonitorPreRoll(log=lambda m, *a: env.logs.append(m))
        mon._vigiar_imagem = lambda *a, **k: None

        env.playing = True
        env.playing_file = 'http://192.168.0.15:59124/?url=http%3A%2F%2Fcdn.exemplo%2Fsportv.m3u8'
        env.labels['VideoPlayer.Title'] = 'SporTV'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(env.ad_count, 1)

        # Retorno do VAST + segunda tentativa de reconexao do mesmo canal -> 0 anuncios extras
        mon.onPlayBackStarted()
        mon.onAVStarted()
        mon.onPlayBackEnded()
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(env.ad_count, 1)

        # Apertar Voltar/Quadrado (Stop) encerra a sessao de forma limpa
        mon.onPlayBackStopped()
        self.assertIsNone(mon.ultimo_caminho)

    def test_1_3_troca_de_canais_segue_mesma_regra_de_filmes_e_series(self):
        env, smart_ads, ads_regra, _ = self._boot(tv=True)
        smart_ads.abrir_anuncio = lambda *a, **k: setattr(env, 'ad_count', env.ad_count + 1) or True
        mon = smart_ads.MonitorPreRoll(log=lambda m, *a: env.logs.append(m))
        mon._vigiar_imagem = lambda *a, **k: None

        # Canal 1 dispara anuncio e conclui retorno
        env.playing = True
        env.playing_file = 'http://cdn.exemplo/canal1.m3u8'
        env.labels['VideoPlayer.Title'] = 'Canal 1'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(env.ad_count, 1)

        # Troca imediata para Canal 2 (< 2 min): toca direto sem atraso e sem anuncio
        env.playing_file = 'http://cdn.exemplo/canal2.m3u8'
        env.labels['VideoPlayer.Title'] = 'Canal 2'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(env.ad_count, 1)

        # Apos expirar o intervalo de 2 min, troca para Canal 3 -> dispara anuncio igual a VOD!
        futuro = time.time() + ads_regra.INTERVALO + 5
        mon._ate_ignorar_volta_vast = 0.0
        env.playing_file = 'http://cdn.exemplo/canal3.m3u8'
        env.labels['VideoPlayer.Title'] = 'Canal 3'
        with patch('time.time', return_value=futuro):
            mon.onPlayBackStarted()
            mon.onAVStarted()
        self.assertEqual(env.ad_count, 2)


class TestFuncionalidade2GradesHome30Itens(unittest.TestCase):
    """3 testes: grades da Home com ate 30 filmes e 30 series na mesma pasta."""

    def test_2_1_home_xml_nas_duas_skins_tem_limit_30_e_sao_identicas(self):
        home_a = (ROOT / 'kodi/skin.estilo.personalizado/xml/Home.xml').read_bytes()
        home_b = (ROOT / 'kodi/skin.novatv/xml/Home.xml').read_bytes()
        self.assertEqual(home_a, home_b)
        raiz = ET.fromstring(home_a)
        c9201 = raiz.find(".//control[@id='9201']/content")
        c9203 = raiz.find(".//control[@id='9203']/content")
        self.assertEqual(c9201.get('limit'), '30')
        self.assertEqual(c9201.text, 'plugin://plugin.video.smarted/?route=recent-movies')
        self.assertEqual(c9203.get('limit'), '30')
        self.assertEqual(c9203.text, 'plugin://plugin.video.smarted/?route=recent-series')

    def test_2_2_entrega_30_filmes_e_30_series_quando_pasta_tem_35_itens(self):
        routes = _load_module('routes', BRIDGE / 'routes.py')
        added_movies, added_series = [], []

        class Info(object):
            def __getattr__(self, k):
                return lambda *a, **kw: None

        class Item(object):
            def __init__(self, label=''):
                self.label = label
            def setArt(self, *a): pass
            def getVideoInfoTag(self): return Info()
            def setProperty(self, *a): pass

        def make_movie(i):
            return {
                'label': 'Filme %d' % i,
                'url': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=16&url=f%d' % i,
                'title': 'Filme %d' % i, 'folder': False, 'playable': True,
                'thumbnail': 'p.jpg', 'fanart': 'f.jpg', 'plot': 'ok', 'year': 2026,
            }

        def make_series(i):
            return {
                'category': 'Séries', 'title': 'Série %d' % i, 'thumb': 't.jpg',
                'fanart': 'f.jpg', 'description': 'ok',
                'url': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=6&url=s%d' % i,
                'release_date': '2026-10-%02d' % ((i % 28) + 1),
            }

        cat_mod = types.SimpleNamespace(
            recent_movies=lambda rpc, limit=10: [make_movie(i) for i in range(limit + 5)]
        )
        search_mod = types.SimpleNamespace(
            SOURCES=[('Séries', 'https://example.invalid')],
            recent_series=lambda limit=10: ([make_series(i) for i in range(limit)], []),
        )
        plugin_movies = types.SimpleNamespace(
            SORT_METHOD_UNSORTED=0, setContent=lambda *a: None, addSortMethod=lambda *a: None,
            addDirectoryItem=lambda h, u, it, **kw: added_movies.append(u),
            endOfDirectory=lambda *a, **kw: None,
        )
        xbmc_mod = types.SimpleNamespace(executeJSONRPC=lambda _: '{}', LOGWARNING=2, LOGINFO=1, log=lambda *a: None)
        vfs_mod = types.SimpleNamespace(translatePath=lambda p: 'relative/no-cache')

        with patch.dict(sys.modules, {
            'routes': routes, 'catalogue': cat_mod, 'search': search_mod,
            'xbmcgui': types.SimpleNamespace(ListItem=Item),
            'xbmcplugin': plugin_movies, 'xbmc': xbmc_mod, 'xbmcvfs': vfs_mod,
        }):
            main = _load_module('smarted_default_30', BRIDGE / 'default.py')
            main.recent_movies(1)
            self.assertEqual(len(added_movies), 30)

            plugin_movies.addDirectoryItem = lambda h, u, it, **kw: added_series.append(u)
            main.recent_series(2)
            self.assertEqual(len(added_series), 30)

    def test_2_3_pasta_com_18_itens_entrega_os_18_e_valida_cache(self):
        routes = _load_module('routes', BRIDGE / 'routes.py')
        added_movies = []

        class Info(object):
            def __getattr__(self, k):
                return lambda *a, **kw: None

        class Item(object):
            def __init__(self, label=''): pass
            def setArt(self, *a): pass
            def getVideoInfoTag(self): return Info()
            def setProperty(self, *a): pass

        movies_18 = [{
            'label': 'Filme %d' % i,
            'url': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=16&url=f%d' % i,
            'title': 'Filme %d' % i, 'folder': False, 'playable': True,
            'thumbnail': 'p.jpg', 'fanart': 'f.jpg', 'plot': '', 'year': 2026,
        } for i in range(18)]

        series_18 = ([{
            'category': 'Séries', 'title': 'Série %d' % i, 'thumb': 't.jpg',
            'fanart': 'f.jpg', 'description': '',
            'url': 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=6&url=s%d' % i,
            'release_date': '2026-09-%02d' % (i + 1),
        } for i in range(18)], [])

        cat_mod = types.SimpleNamespace(recent_movies=lambda rpc, limit=10: list(movies_18))
        plugin_mod = types.SimpleNamespace(
            SORT_METHOD_UNSORTED=0, setContent=lambda *a: None, addSortMethod=lambda *a: None,
            addDirectoryItem=lambda h, u, it, **kw: added_movies.append(u),
            endOfDirectory=lambda *a, **kw: None,
        )
        xbmc_mod = types.SimpleNamespace(executeJSONRPC=lambda _: '{}', LOGWARNING=2, LOGINFO=1, log=lambda *a: None)
        vfs_mod = types.SimpleNamespace(translatePath=lambda p: 'relative/no-cache')

        with patch.dict(sys.modules, {
            'routes': routes, 'catalogue': cat_mod,
            'xbmcgui': types.SimpleNamespace(ListItem=Item),
            'xbmcplugin': plugin_mod, 'xbmc': xbmc_mod, 'xbmcvfs': vfs_mod,
        }):
            main = _load_module('smarted_default_18', BRIDGE / 'default.py')
            self.assertTrue(main._movie_cache_ok(movies_18))
            self.assertTrue(main._series_cache_ok(series_18))
            main.recent_movies(1)
            self.assertEqual(len(added_movies), 18)


class TestFuncionalidade3VoltarEQuadradoFinalizamConteudo(unittest.TestCase):
    """3 testes: Voltar e Quadrado param reproducao sem segundo plano."""

    def test_3_1_keymap_player_mapeia_voltar_e_quadrado_para_stop(self):
        caminho = ROOT / 'kodi/keymaps/smartedtv-player.xml'
        self.assertTrue(caminho.is_file())
        raiz = ET.fromstring(caminho.read_bytes())
        self.assertEqual(raiz.tag, 'keymap')

        for janela in ('FullscreenVideo', 'FullscreenLiveTV', 'Visualisation'):
            bloco = raiz.find(janela)
            self.assertIsNotNone(bloco, janela)
            for tag in ('backspace', 'browser_back', 'escape', 'stop', 'x'):
                self.assertEqual(bloco.findtext('keyboard/%s' % tag), 'Stop', (janela, tag))
            for tag in ('back', 'stop'):
                self.assertEqual(bloco.findtext('remote/%s' % tag), 'Stop', (janela, tag))
            for tag in ('B', 'back', 'X'):
                self.assertEqual(bloco.findtext('gamepad/%s' % tag), 'Stop', (janela, tag))

        for janela in ('VideoOSD', 'MusicOSD'):
            bloco = raiz.find(janela)
            self.assertIsNotNone(bloco, janela)
            self.assertEqual(bloco.findtext('keyboard/stop'), 'Stop')
            self.assertEqual(bloco.findtext('remote/stop'), 'Stop')
            self.assertEqual(bloco.findtext('gamepad/X'), 'Stop')

    def test_3_2_touch_back_osd_e_botao_quadrado_603_executam_stop(self):
        inc_a = (ROOT / 'kodi/skin.estilo.personalizado/xml/Includes.xml').read_text(encoding='utf-8')
        inc_b = (ROOT / 'kodi/skin.novatv/xml/Includes.xml').read_text(encoding='utf-8')
        self.assertEqual(inc_a, inc_b)

        raiz = ET.fromstring(inc_a.encode('utf-8'))
        touch_back = raiz.find(".//include[@name='TouchBackOSDButton']/control[@id='799']")
        self.assertIsNotNone(touch_back)
        acoes = [el.text.strip() for el in touch_back.findall('onclick') if el.text]
        self.assertIn('PlayerControl(Stop)', acoes)
        self.assertNotIn('Action(FullScreen)', acoes)

        osd = ET.fromstring((ROOT / 'kodi/skin.estilo.personalizado/xml/VideoOSD.xml').read_bytes())
        quadrado = osd.find(".//control[@id='603']")
        self.assertIsNotNone(quadrado)
        self.assertEqual(quadrado.findtext('onclick'), 'PlayerControl(Stop)')

    def test_3_3_empacotador_inclui_zzy_player_antes_de_zzz_voltar_home(self):
        atualizador = _load_module('atualizar_v17_152', ROOT / 'tools/kodi/atualizar-apk-v17.py')
        extras = atualizador.arquivos_do_servico()
        self.assertIn('assets/system/keymaps/zzy-smartedtv-player.xml', extras)
        self.assertIn('assets/system/keymaps/zzz-smartedtv-voltar.xml', extras)
        sistema = sorted([
            'assets/system/keymaps/gamepad.xml',
            'assets/system/keymaps/keyboard.xml',
            'assets/system/keymaps/remote.xml',
            'assets/system/keymaps/touchscreen.xml',
            * [k for k in extras if k.startswith('assets/system/keymaps/')],
        ])
        self.assertEqual(sistema[-2], 'assets/system/keymaps/zzy-smartedtv-player.xml')
        self.assertEqual(sistema[-1], 'assets/system/keymaps/zzz-smartedtv-voltar.xml')
        # zzz-smartedtv-voltar.xml permanece exclusivo para <Home>
        voltar_xml = ET.fromstring(extras['assets/system/keymaps/zzz-smartedtv-voltar.xml'])
        self.assertEqual([e.tag for e in voltar_xml], ['Home'])


if __name__ == '__main__':
    unittest.main()
