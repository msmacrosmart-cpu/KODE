# -*- coding: utf-8 -*-
"""Pré-roll: disparo com espera de foco e retomada exata do MESMO player.

Usa um player falso: nenhum teste aqui prova exibição de anúncio num aparelho;
o recibo é o arquivo .returned escrito pelo Java (AdBreak) depois de o Main
voltar a frente — é isso que libera o vídeo.
"""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'


def carregar_ad_return(pasta):
    xbmc = types.ModuleType('xbmc')
    xbmc.Monitor = type('Monitor', (object,), {
        'waitForAbort': lambda self, t=0: False, 'abortRequested': lambda self: False})
    def rpc(payload):
        metodo = __import__('json').loads(payload)['method']
        if metodo == 'Player.GetActivePlayers':
            return '{"result": [{"playerid": 1, "type": "video"}]}'
        if metodo == 'Player.GetProperties':
            return ('{"result": {"speed": 1, "canpause": true, "canseek": true,'
                    ' "live": false}}')
        return '{"result": "OK"}'
    xbmc.executeJSONRPC = rpc
    xbmc.getInfoLabel = lambda rotulo: 'Canal A' if 'Channel' in rotulo else ''
    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda p: pasta
    salvos = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcvfs')}
    sys.modules.update(xbmc=xbmc, xbmcvfs=xbmcvfs)
    spec = importlib.util.spec_from_file_location('ad_return_teste', BASE / 'ad_return.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo._salvos = salvos
    return modulo


class PlayerFalso:
    def __init__(self):
        self.pausas, self.buscas, self.tocou = [], [], []
        self.tempo = 120.0
        self.arquivo = 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=1&url=filme'
        self.tocando = True

    def isPlayingVideo(self):
        return self.tocando

    def getPlayingFile(self):
        return self.arquivo

    def getTime(self):
        return self.tempo

    def seekTime(self, segundos):
        self.buscas.append(segundos)
        self.tempo = segundos

    def play(self, caminho, item=None):
        self.tocou.append(caminho)

    def getPlayingItem(self):
        return None


class RetornoDoAnuncioTest(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.mod = carregar_ad_return(self.pasta)
        self.player = PlayerFalso()

    def tearDown(self):
        for nome, antigo in self.mod._salvos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    def test_vod_pausa_uma_vez_e_volta_na_mesma_posicao(self):
        video = self.mod.KodiVideo(self.player)
        video.hold()
        self.assertTrue(video.can_pause and video.can_seek)
        self.assertEqual(video.position, 120.0)
        self.player.tempo = 120.0
        video.release()
        self.assertEqual(self.player.buscas, [])  # já estava na posição
        self.assertFalse(self.player.tocou)       # nunca reabre o filme

    def test_volta_para_a_posicao_que_o_anuncio_avancou(self):
        video = self.mod.KodiVideo(self.player)
        video.hold()
        self.player.tempo = 3.0          # SDK mexeu no player por trás
        video.release()
        self.assertEqual(self.player.buscas, [120.0])

    def test_stream_sem_pausa_nao_e_pausado_e_nao_reabre_o_vod(self):
        video = self.mod.KodiVideo(self.player)
        video.can_pause = False
        video.live = True                # canal ao vivo sem timeshift
        video.hold()
        video.release()
        self.assertEqual(self.player.buscas, [])
        self.assertFalse(self.player.tocou)

    def test_quando_o_player_morreu_a_retomada_nao_inventa_posicao(self):
        video = self.mod.KodiVideo(self.player)
        video.hold()
        self.player.tocando = False
        video.release()
        self.assertEqual(self.player.buscas, [])

    def test_breaks_so_libera_com_o_arquivo_returned_do_java(self):
        breaks = self.mod.Breaks()
        video = self.mod.KodiVideo(self.player)
        token = {}

        def abrir(t):
            token['t'] = t
            return True

        self.assertTrue(breaks.start(video, abrir))
        stem = os.path.join(self.pasta, 'temp', 'smarted-ad', token['t'])
        self.assertTrue(os.path.isfile(stem + '.pending'))
        # o Java renomeia pending -> open ao abrir a activity; depois -> returned
        os.rename(stem + '.pending', stem + '.open')
        os.rename(stem + '.open', stem + '.returned')
        import time
        for _ in range(50):
            if not breaks.current:
                break
            time.sleep(0.02)
        self.assertIsNone(breaks.current)
        self.assertFalse(os.path.exists(stem + '.returned'))

    def test_sem_disparo_o_video_e_liberado_na_hora(self):
        breaks = self.mod.Breaks()
        video = self.mod.KodiVideo(self.player)
        self.assertFalse(breaks.start(video, lambda t: False))
        self.assertIsNone(breaks.current)

    def test_replay_do_retorno_nao_gera_outro_preroll(self):
        breaks = self.mod.Breaks()
        breaks.replay = (self.player.arquivo + '|Canal A', 'Canal A',
                         __import__('time').monotonic() + 5)
        self.assertTrue(breaks.is_replay(self.player.arquivo, 'Canal A'))
        self.assertFalse(breaks.is_replay(self.player.arquivo, 'Canal A'))


if __name__ == '__main__':
    unittest.main()
