# -*- coding: utf-8 -*-
"""Suite dedicada da v1.0.153: regra exata de reentrada apos 2 minutos."""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRegraReentradaApos2Minutos(unittest.TestCase):
    """3 testes validando Filme 1 -> Filme 4 -> Filme 1 apos 2 minutos."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='smarted153-')
        self.addon_data = os.path.join(self.tmp, 'addon_data', 'service.smarted.bootstrap')
        os.makedirs(self.addon_data, exist_ok=True)
        self._saved_path = list(sys.path)
        sys.path.insert(0, str(BOOTSTRAP))

        self.playing = False
        self.playing_file = ''
        self.labels = {}
        self.ad_count = 0

        env = self
        xbmc = types.ModuleType('xbmc')
        xbmc.LOGINFO = 1
        xbmc.LOGWARNING = 3

        class PlayerBase(object):
            def isPlaying(self):
                return env.playing
            def isPlayingVideo(self):
                return env.playing
            def getPlayingFile(self):
                return env.playing_file
            def getTime(self):
                return 10.0

        xbmc.Player = PlayerBase
        xbmc.Monitor = object
        xbmc.getInfoLabel = lambda k: env.labels.get(k, '')
        xbmc.getCondVisibility = lambda c: True if 'fullscreenvideo' in c.lower() else False
        xbmc.executebuiltin = lambda cmd: None
        xbmc.executeJSONRPC = lambda p: json.dumps({'result': [{'playerid': 1, 'type': 'video'}]})
        xbmc.log = lambda *a, **k: None

        xbmcvfs = types.ModuleType('xbmcvfs')
        xbmcvfs.translatePath = lambda p: (
            env.tmp if p == 'special://profile'
            else os.path.join(env.tmp, p[len('special://profile/'):]) if p.startswith('special://profile/')
            else p
        )
        xbmcvfs.exists = lambda p: os.path.exists(xbmcvfs.translatePath(p))

        vip_mod = types.ModuleType('vip')
        vip_mod.ativa = lambda: False

        self._patcher = patch.dict(sys.modules, {'xbmc': xbmc, 'xbmcvfs': xbmcvfs, 'vip': vip_mod})
        self._patcher.start()

        self.ao_vivo = _load_module('ao_vivo', BOOTSTRAP / 'ao_vivo.py')
        self.ads_regra = _load_module('ads_regra', BOOTSTRAP / 'ads_regra.py')
        self.ad_return = _load_module('ad_return', BOOTSTRAP / 'ad_return.py')
        sys.modules['ao_vivo'] = self.ao_vivo
        sys.modules['ads_regra'] = self.ads_regra
        sys.modules['ad_return'] = self.ad_return
        self.smart_ads = _load_module('smart_ads', BOOTSTRAP / 'smart_ads.py')
        sys.modules['smart_ads'] = self.smart_ads

        self.smart_ads.e_tv = lambda: True
        self.smart_ads.android = lambda: False

    def tearDown(self):
        self._patcher.stop()
        sys.path[:] = self._saved_path
        for m in ('smart_ads', 'ads_regra', 'ad_return', 'ao_vivo', 'vip'):
            sys.modules.pop(m, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_1_filme_1_depois_filme_4_depois_filme_1_anuncia_nos_tres(self):
        """Fluxo exato citado pelo usuario:
        Filme 1 (anuncio + assiste ate o fim sem novo anuncio) ->
        apos 2 min entra no Filme 4 (anuncio de novo) ->
        apos 2 min entra no Filme 1 de novo (anuncio novamente!).
        """
        def fake_ad(*a, **k):
            self.ad_count += 1
            return True

        self.smart_ads.abrir_anuncio = fake_ad
        mon = self.smart_ads.MonitorPreRoll()
        mon._vigiar_imagem = lambda *a, **k: None

        # 1) Entra no Filme 1 em t=1000s -> anuncio #1
        self.playing = True
        self.playing_file = 'https://cdn.exemplo/filme1.mp4'
        self.labels['VideoPlayer.Title'] = 'Filme 1'
        with patch('time.time', return_value=1000.0):
            mon.onPlayBackStarted()
            mon.onAVStarted()
        self.assertEqual(self.ad_count, 1)

        # Retorno do anuncio ao Filme 1 + permanece assistindo mesmo apos 30 min -> SEM anuncio no meio!
        with patch('time.time', return_value=1015.0):
            mon.onPlayBackStarted()
            mon.onAVStarted()
        mon._ate_ignorar_volta_vast = 0.0
        with patch('time.time', return_value=2800.0):
            mon.onAVStarted()
        self.assertEqual(self.ad_count, 1)

        # Sai do Filme 1 (Voltar / Quadrado -> Stop)
        mon.onPlayBackStopped()

        # 2) Apos 2 minutos, entra no Filme 4 -> anuncio #2!
        self.playing = True
        self.playing_file = 'https://cdn.exemplo/filme4.mp4'
        self.labels['VideoPlayer.Title'] = 'Filme 4'
        with patch('time.time', return_value=2950.0):
            mon.onPlayBackStarted()
            mon.onAVStarted()
        self.assertEqual(self.ad_count, 2)
        mon._ate_ignorar_volta_vast = 0.0

        # Sai do Filme 4 (Voltar / Quadrado -> Stop)
        mon.onPlayBackStopped()

        # 3) Apos mais 2 minutos, entra no Filme 1 DE NOVO -> anuncio #3!
        self.playing = True
        self.playing_file = 'https://cdn.exemplo/filme1.mp4'
        self.labels['VideoPlayer.Title'] = 'Filme 1'
        with patch('time.time', return_value=3100.0):
            mon.onPlayBackStarted()
            mon.onAVStarted()
        self.assertEqual(self.ad_count, 3)

    def test_2_dentro_dos_2_minutos_sair_e_entrar_nao_repete_anuncio(self):
        self.smart_ads.abrir_anuncio = lambda *a, **k: setattr(self, 'ad_count', self.ad_count + 1) or True
        mon = self.smart_ads.MonitorPreRoll()
        mon._vigiar_imagem = lambda *a, **k: None

        self.playing = True
        self.playing_file = 'https://cdn.exemplo/filme1.mp4'
        self.labels['VideoPlayer.Title'] = 'Filme 1'
        with patch('time.time', return_value=1000.0):
            mon.onPlayBackStarted()
            mon.onAVStarted()
        self.assertEqual(self.ad_count, 1)
        mon._ate_ignorar_volta_vast = 0.0
        mon.onPlayBackStopped()

        # Reentra no Filme 1 ou no Filme 4 com apenas 45s (< 120s) -> toca direto!
        for arq, tit, inst in (
            ('https://cdn.exemplo/filme1.mp4', 'Filme 1', 1045.0),
            ('https://cdn.exemplo/filme4.mp4', 'Filme 4', 1090.0),
        ):
            self.playing = True
            self.playing_file = arq
            self.labels['VideoPlayer.Title'] = tit
            with patch('time.time', return_value=inst):
                mon.onPlayBackStarted()
                mon.onAVStarted()
            self.assertEqual(self.ad_count, 1)
            mon.onPlayBackStopped()

    def test_3_atualizacao_ignora_e_limpa_lista_antiga_anunciados_do_disco(self):
        # Simula ads-regra.json deixado por versoes anteriores com 3 filmes travados
        arq_json = os.path.join(self.addon_data, 'ads-regra.json')
        with open(arq_json, 'w') as fh:
            json.dump({
                'ultimo_anuncio': 1000.0,
                'anunciados': [
                    'https://cdn.exemplo/filme1.mp4|Filme 1',
                    'https://cdn.exemplo/filme2.mp4|Filme 2',
                    'https://cdn.exemplo/filme3.mp4|Filme 3',
                ],
            }, fh)

        self.smart_ads.abrir_anuncio = lambda *a, **k: setattr(self, 'ad_count', self.ad_count + 1) or True
        mon = self.smart_ads.MonitorPreRoll()
        mon._vigiar_imagem = lambda *a, **k: None

        self.playing = True
        self.playing_file = 'https://cdn.exemplo/filme1.mp4'
        self.labels['VideoPlayer.Title'] = 'Filme 1'
        with patch('time.time', return_value=1200.0):
            mon.onPlayBackStarted()
            mon.onAVStarted()
        self.assertEqual(self.ad_count, 1)

        with open(arq_json) as fh:
            gravado = json.load(fh)
        self.assertNotIn('anunciados', gravado)


if __name__ == '__main__':
    unittest.main()
