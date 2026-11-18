# -*- coding: utf-8 -*-
"""TV ao vivo com tela preta; filmes e séries continuam normais.

Relato do usuário: "o app está dando tela preta nos canais de TV ao vivo,
somente filmes e séries está ok".

O que estes testes travam:

1. a retomada de posição depois do anúncio **não** faz seek em canal contínuo
   (em VOD continua fazendo, exatamente como antes);
2. canal sem `videowidth`/codec de vídeo (só áudio ou nada) faz o app trocar o
   perfil de vídeo uma vez e reabrir o canal, gravando a escolha para o boot;
3. o boot seguinte já começa no perfil aprendido;
4. filme/série nunca entra no caminho do ao vivo.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'


def carregar(nome, caminho, xbmc=None, xbmcvfs=None):
    salvos = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcvfs')}
    if xbmc is not None:
        sys.modules['xbmc'] = xbmc
    if xbmcvfs is not None:
        sys.modules['xbmcvfs'] = xbmcvfs
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo, salvos


def restaurar(salvos):
    for nome, antigo in salvos.items():
        if antigo is None:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = antigo


class KodiAoVivo(object):
    """Kodi mínimo: labels configuráveis e builtins registrados."""

    def __init__(self, labels=None, live=False, rpc=None):
        self.labels = labels or {}
        self.live = live
        self.builtins = []
        self.logs = []
        self.rpc_calls = []
        self.rpc = rpc or {}
        self.settings = {}
        self.LOGWARNING, self.LOGINFO = 3, 1

    def getInfoLabel(self, rotulo):
        return self.labels.get(rotulo, '')

    def getCondVisibility(self, condicao):
        if condicao == 'VideoPlayer.Content(live)':
            return self.live
        return False

    def executebuiltin(self, comando):
        self.builtins.append(comando)

    def executeJSONRPC(self, payload):
        pedido = json.loads(payload)
        self.rpc_calls.append((pedido['method'], pedido.get('params')))
        if self.rpc.get('erro'):
            return json.dumps({'error': {'code': -1}})
        if pedido['method'] == 'Player.GetActivePlayers':
            return json.dumps({'result': [{'playerid': 1, 'type': 'video'}]})
        if pedido['method'] == 'Settings.SetSettingValue':
            self.settings[pedido['params']['setting']] = pedido['params']['value']
            return json.dumps({'result': 'OK'})
        if pedido['method'] == 'Settings.GetSettingValue':
            return json.dumps({'result': {
                'value': self.settings.get(pedido['params']['setting'])}})
        return json.dumps({'result': 'OK'})

    def log(self, mensagem, nivel=1):
        self.logs.append(mensagem)


class Player(object):
    def __init__(self, arquivo, tocando=True):
        self.arquivo = arquivo
        self.tocando = tocando

    def isPlayingVideo(self):
        return self.tocando

    def getPlayingFile(self):
        return self.arquivo

    def getTime(self):
        return 0.0


class AoVivoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='aovivo-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _vfs(self):
        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: self.tmp if 'profile' in p else p
        os.makedirs(os.path.join(self.tmp, 'addon_data',
                                 'service.smarted.bootstrap'), exist_ok=True)
        return vfs

    def _carregar(self, kodi):
        return carregar('ao_vivo_teste', BASE / 'ao_vivo.py', kodi, self._vfs())[0]

    # -------------------------------------------------------------- deteccao
    def test_reconhece_canal_continuo(self):
        modulo = self._carregar(KodiAoVivo())
        for caminho in ('https://cdn.exemplo/canal/index.m3u8?token=1',
                        'https://cdn.exemplo/canal.ts',
                        'plugin://plugin.video.BrazucaPlay.Matrix/?mode=11&url=canal',
                        'https://exemplo/aovivo/brasil'):
            self.assertTrue(modulo.eh_ao_vivo(caminho), caminho)

    def test_filme_e_serie_nao_sao_ao_vivo(self):
        modulo = self._carregar(KodiAoVivo())
        for caminho in ('https://cdn.exemplo/filme.mp4',
                        'https://cdn.exemplo/serie/t1e1.mkv',
                        'plugin://plugin.video.BrazucaPlay.Matrix/?mode=1&url=filme'):
            self.assertFalse(modulo.eh_ao_vivo(caminho), caminho)

    def test_pvr_conta_como_ao_vivo(self):
        modulo = self._carregar(KodiAoVivo(live=True))
        self.assertTrue(modulo.eh_ao_vivo('pvr://channels/tv/1'))

    # ---------------------------------------------------- imagem x sem imagem
    def test_imagem_por_largura_ou_codec(self):
        kodi = KodiAoVivo({'Player.Process(videowidth)': '1280'})
        self.assertTrue(self._carregar(kodi).tem_imagem())
        kodi = KodiAoVivo({'Player.Process(videocodec)': 'h264'})
        self.assertTrue(self._carregar(kodi).tem_imagem())
        kodi = KodiAoVivo({'Player.Process(audiocodec)': 'aac'})
        self.assertFalse(self._carregar(kodi).tem_imagem())
        self.assertTrue(self._carregar(kodi).tem_audio())

    def test_sem_imagem_troca_perfil_e_reabre_uma_vez(self):
        kodi = KodiAoVivo({'Player.Process(audiocodec)': 'aac'})
        modulo = self._carregar(kodi)
        player = Player('https://cdn.exemplo/canal/index.m3u8')
        estado = modulo.vigiar(player, 'https://cdn.exemplo/canal/index.m3u8',
                               espera=2.0)
        self.assertEqual(estado, 'reaberto')
        perfis = [p for p in kodi.rpc_calls
                  if p[0] == 'Settings.SetSettingValue'
                  and p[1]['setting'] == 'videoplayer.usemediacodecsurface']
        self.assertEqual(len(perfis), 1, kodi.rpc_calls)
        self.assertFalse(perfis[0][1]['value'])
        self.assertTrue(any(b.startswith('PlayMedia(') for b in kodi.builtins),
                        kodi.builtins)
        self.assertTrue(modulo.fallback_ligado())

    def test_ja_sem_surface_nao_reabre_de_novo(self):
        kodi = KodiAoVivo({'Player.Process(audiocodec)': 'aac'})
        modulo = self._carregar(kodi)
        modulo.marcar_fallback()
        player = Player('https://cdn.exemplo/canal/index.m3u8')
        estado = modulo.vigiar(player, 'https://cdn.exemplo/canal/index.m3u8',
                               espera=2.0)
        self.assertEqual(estado, 'sem-imagem')
        self.assertEqual([b for b in kodi.builtins if b.startswith('PlayMedia')], [])

    def test_com_imagem_nao_mexe_em_nada(self):
        kodi = KodiAoVivo({'Player.Process(videowidth)': '1920'})
        modulo = self._carregar(kodi)
        player = Player('https://cdn.exemplo/canal/index.m3u8')
        self.assertEqual(modulo.vigiar(player, player.arquivo, espera=2.0), 'ok')
        self.assertEqual(kodi.builtins, [])
        self.assertEqual(kodi.rpc_calls, [])

    def test_filme_nao_entra_no_vigia(self):
        kodi = KodiAoVivo({'Player.Process(audiocodec)': 'aac'})
        modulo = self._carregar(kodi)
        player = Player('https://cdn.exemplo/filme.mp4')
        self.assertEqual(modulo.vigiar(player, player.arquivo, espera=2.0),
                         'ignorado')
        self.assertEqual(kodi.builtins, [])
        self.assertEqual(kodi.rpc_calls, [])

    def test_perfil_aprendido_vale_no_boot(self):
        kodi = KodiAoVivo({'Player.Process(audiocodec)': 'aac'})
        modulo = self._carregar(kodi)
        modulo.marcar_fallback()
        # No Kodi a pasta do addon esta no sys.path; aqui expomos o modulo com
        # o mesmo nome que o performance.py procura.
        sys.modules['ao_vivo'] = modulo
        performance, salvos = carregar('performance_teste',
                                       BASE / 'performance.py', kodi,
                                       self._vfs())
        try:
            self.assertTrue(performance.perfil_ja_aprendido())
            aplicados, falhas = performance.apply_settings(
                lambda metodo, params=None: json.loads(
                    kodi.executeJSONRPC(json.dumps(
                        {'jsonrpc': '2.0', 'id': 1, 'method': metodo,
                         'params': params or {}}))),
                None, '')
        finally:
            restaurar(salvos)
        sys.modules.pop('ao_vivo', None)
        usados = dict((p[1]['setting'], p[1]['value'])
                      for p in kodi.rpc_calls
                      if p[0] == 'Settings.SetSettingValue')
        self.assertIs(usados.get('videoplayer.usemediacodecsurface'), False,
                      usados)
        self.assertIn('videoplayer.usemediacodecsurface', aplicados)
        self.assertEqual(falhas, [])


class RetomadaAoVivoTest(unittest.TestCase):
    """A volta do anúncio não pode buscar posição em canal contínuo."""

    def setUp(self):
        self.kodi = KodiAoVivo({'VideoPlayer.ChannelName': 'Canal A'})
        self.ad_return, self.salvos = carregar(
            'ad_return_teste', BASE / 'ad_return.py', self.kodi, None)
        self.ao_vivo = carregar('ao_vivo_teste', BASE / 'ao_vivo.py',
                                self.kodi)[0]

    def tearDown(self):
        restaurar(self.salvos)
        sys.modules.pop('ao_vivo', None)

    def _armar(self, player):
        sys.modules['ao_vivo'] = self.ao_vivo
        retomada = self.ad_return.Retomada()
        return retomada, retomada.armar(player)

    def test_canal_ao_vivo_nao_recebe_seek(self):
        player = Player('https://cdn.exemplo/canal/index.m3u8')
        retomada, estado = self._armar(player)
        self.assertTrue(estado['ao_vivo'])
        self.assertIsNone(retomada.corrigir(player, dict(estado, posicao=42.0)))
        self.assertEqual([p for p in self.kodi.rpc_calls
                          if p[0] == 'Player.Seek'], [])

    def test_filme_continua_retomando_na_posicao(self):
        player = Player('https://cdn.exemplo/filme.mp4')
        retomada, estado = self._armar(player)
        self.assertFalse(estado['ao_vivo'])

        class PlayerPerdido(Player):
            def getTime(self):
                return 12.0

        alvo = retomada.corrigir(PlayerPerdido(player.arquivo),
                                 dict(estado, posicao=600.0))
        self.assertEqual(alvo, 600.0)
        seeks = [p for p in self.kodi.rpc_calls if p[0] == 'Player.Seek']
        self.assertEqual(len(seeks), 1)
        self.assertEqual(seeks[0][1]['value']['seconds'], 600.0)


if __name__ == '__main__':
    unittest.main()
