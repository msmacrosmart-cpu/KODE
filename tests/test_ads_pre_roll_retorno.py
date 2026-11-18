# -*- coding: utf-8 -*-
"""Anúncio: ponto de retomada antes do disparo e volta exata ao mesmo conteúdo.

Nenhum teste aqui prova exibição de anúncio num aparelho: o caminho de volta é
observado no player (posição/canal), que é o mesmo em celular, TV, box,
projetor e stick. O que se verifica é que o vídeo não recomeça do zero e que a
volta não gera outro pré-roll.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'


class Rpc(object):
    def __init__(self):
        self.chamadas = []

    def __call__(self, payload):
        import json
        pedido = json.loads(payload)
        self.chamadas.append((pedido['method'], pedido.get('params')))
        if pedido['method'] == 'Player.GetActivePlayers':
            return '{"result": [{"playerid": 1, "type": "video"}]}'
        return '{"result": "OK"}'

    def buscas(self):
        return [p['value']['seconds'] for m, p in self.chamadas if m == 'Player.Seek']


def carregar():
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGWARNING = 3
    xbmc.rpc = Rpc()
    xbmc.executeJSONRPC = lambda payload: xbmc.rpc(payload)
    estado = {'canal': 'Canal A', 'pausado': False}
    xbmc.getInfoLabel = lambda rotulo: estado['canal'] if 'Channel' in rotulo else ''
    xbmc.getCondVisibility = lambda cond: estado['pausado'] if 'Paused' in cond else False
    xbmc.log = lambda *a, **k: None
    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda p: '/tmp'
    salvos = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcvfs')}
    sys.modules.update(xbmc=xbmc, xbmcvfs=xbmcvfs)
    spec = importlib.util.spec_from_file_location('ad_return_teste', BASE / 'ad_return.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo._xbmc = xbmc
    modulo._estado = estado
    modulo._salvos = salvos
    return modulo


class PlayerFalso(object):
    def __init__(self):
        self.arquivo = 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=1&url=filme'
        self.tocando = True
        self.tempo = 754.0
        self.buscas = []

    def isPlayingVideo(self):
        return self.tocando

    def getPlayingFile(self):
        return self.arquivo

    def getTime(self):
        return self.tempo

    def seekTime(self, segundos):
        self.buscas.append(segundos)
        self.tempo = segundos


class RetomadaTest(unittest.TestCase):
    def setUp(self):
        self.mod = carregar()
        self.player = PlayerFalso()
        self.retomada = self.mod.Retomada()

    def tearDown(self):
        for nome, antigo in self.mod._salvos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    def test_arma_com_posicao_e_canal(self):
        estado = self.retomada.armar(self.player)
        self.assertEqual(estado['posicao'], 754.0)
        self.assertEqual(estado['canal'], 'Canal A')
        self.assertIs(self.retomada.guardado(), estado)

    def test_volta_no_mesmo_ponto_nao_mexe_no_video(self):
        self.retomada.armar(self.player)
        self.assertIsNone(self.retomada.corrigir(self.player, self.retomada.guardado()))
        self.assertEqual(self.player.buscas + self.mod._xbmc.rpc.buscas(), [])

    def test_video_que_recomecou_volta_para_a_posicao(self):
        self.retomada.armar(self.player)
        self.player.tempo = 0.0           # o Kodi reiniciou o item
        self.retomada.corrigir(self.player, self.retomada.guardado())
        self.assertEqual(self.player.buscas + self.mod._xbmc.rpc.buscas(), [754.0])

    def test_outro_canal_nao_e_retomado(self):
        self.retomada.armar(self.player)
        self.mod._estado['canal'] = 'Canal B'
        self.assertFalse(self.retomada.mesmo_conteudo(self.player.arquivo, 'Canal B'))

    def test_volta_do_anuncio_e_reconhecida_uma_vez(self):
        self.retomada.armar(self.player)
        self.retomada.consumir(self.player)
        self.assertTrue(self.retomada.e_volta(self.player.arquivo, 'Canal A'))
        self.assertFalse(self.retomada.e_volta(self.player.arquivo, 'Canal A'))

    def test_stop_durante_o_anuncio_cancela_a_retomada(self):
        self.retomada.armar(self.player)
        self.retomada.cancelar()
        self.assertIsNone(self.retomada.guardado())

    def test_vigia_espera_o_player_voltar_e_corrige(self):
        self.retomada.armar(self.player)
        estado = self.retomada.guardado()
        self.player.tocando = False       # anúncio na frente
        import threading
        def volta():
            import time
            time.sleep(1.2)
            self.player.tocando = True
            self.player.tempo = 2.0
        threading.Thread(target=volta, daemon=True).start()
        self.retomada.VIGIA_MAXIMO = 6
        self.retomada.vigiar(self.player, estado)
        self.assertEqual(self.player.buscas + self.mod._xbmc.rpc.buscas(), [754.0])


if __name__ == '__main__':
    unittest.main()
