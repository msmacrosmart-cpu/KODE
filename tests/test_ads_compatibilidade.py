# -*- coding: utf-8 -*-
"""Anuncios: gatilho sem metadados, anti-duplicidade e VIP."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULO = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'smart_ads.py'


def carregar():
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGWARNING = 3
    xbmc.LOGERROR = 4
    xbmc.Player = object
    xbmc.executebuiltin = lambda *a, **k: None
    xbmc.getCondVisibility = lambda *a, **k: True
    xbmc.getInfoLabel = lambda *a, **k: ''
    xbmc.log = lambda *a, **k: None
    xbmcvfs = types.ModuleType('xbmcvfs')
    salvos = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcvfs')}
    sys.modules['xbmc'] = xbmc
    sys.modules['xbmcvfs'] = xbmcvfs
    spec = importlib.util.spec_from_file_location('smart_ads_teste', MODULO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo._salvos = salvos
    return modulo


class AnunciosTest(unittest.TestCase):
    def setUp(self):
        self.mod = carregar()
        self.mod.esquecer()
        self.chamadas = []
        self.mod.vip_ativo = lambda: False
        self.aviso_original = self.mod.tocar_anuncio_com_aviso
        self.mod.tocar_anuncio_com_aviso = (
            lambda atividade, log=None, uri='': self.chamadas.append(atividade) or True)

    def tearDown(self):
        for nome, antigo in self.mod._salvos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo

    def test_stream_sem_metadados_pede_anuncio_uma_vez_por_sessao(self):
        """Sem metadados (projetor/PVR) a sessao resolve o mesmo inicio.

        A frequencia e a de `ads_regra`: depois de um anuncio exibido passam
        2 minutos sem anuncio, mesmo que o conteudo mude (era o defeito do
        "anuncio a cada video"). A sessao continua evitando o anuncio dobrado
        do par onPlayBackStarted/onAVStarted.
        """
        intervalo = self.mod.ads_regra.INTERVALO
        # Alguns projetores/PVR nao entregam caminho/titulo (chave '?').
        self.assertTrue(self.mod.mostrar_preroll(
            chave='?', sessao=1, agora=100, intervalo=10))
        self.assertEqual(self.chamadas, [self.mod.ATIVIDADE_PREROLL])
        # onAVStarted do MESMO inicio nao pede o segundo anuncio.
        self.assertFalse(self.mod.mostrar_preroll(
            chave='?', sessao=1, agora=100, intervalo=10))
        self.assertEqual(len(self.chamadas), 1)
        # Sessao nova 20 s depois: ainda dentro dos 2 minutos, sem anuncio.
        self.assertFalse(self.mod.mostrar_preroll(
            chave='?', sessao=2, agora=120, intervalo=10))
        self.assertEqual(len(self.chamadas), 1)
        # Passados os 2 minutos, a sessao nova pede de novo (sem metadados).
        self.assertTrue(self.mod.mostrar_preroll(
            chave='?', sessao=3, agora=100 + intervalo + 5, intervalo=10))
        self.assertEqual(len(self.chamadas), 2)

    def test_vip_nao_recebe_anuncio(self):
        self.mod.vip_ativo = lambda: True
        self.assertFalse(self.mod.mostrar_preroll(
            chave='canal|Filme', sessao=1, agora=100, intervalo=10))
        self.assertEqual(self.chamadas, [])

    def test_aviso_na_tela_so_quando_o_builtin_foi_enviado(self):
        self.falhas = []
        self.mod.tocar_anuncio = lambda atividade, log=None, uri='': False
        self.mod.xbmc.executebuiltin = lambda *a, **k: self.falhas.append(a)
        self.aviso_original(
            self.mod.ATIVIDADE_PREROLL, log=lambda *a, **k: None)
        self.assertEqual(self.falhas, [])

    def test_monitor_chama_uma_vez_por_inicio(self):
        monitor = self.mod.MonitorPreRoll(log=None, intervalo=10)
        monitor._disparar = self.mod.tocar_anuncio_com_aviso
        self.mod._e_video = lambda _p: True
        # Este teste e sobre o GATILHO do anuncio, nao sobre a imagem do canal
        # ao vivo: sem o no-op, o caminho de `_vigiar_imagem` importava
        # `ao_vivo` com o xbmc falso e deixava o modulo contaminado para as
        # outras suites (o "canal" virava ao vivo e a retomada era ignorada).
        monitor._vigiar_imagem = lambda _c: None
        monitor._caminho = lambda: None
        monitor.onPlayBackStarted()
        monitor.onAVStarted()
        self.assertEqual(len(self.chamadas), 1)
        monitor.onPlayBackStopped()
        monitor.onPlayBackStarted()
        monitor.onAVStarted()
        # ...mas so depois do intervalo de 2 minutos (regra central): parar e
        # abrir outro video em seguida NAO gera anuncio.
        self.assertEqual(len(self.chamadas), 1)
        self.mod.ads_regra._MEMORIA.clear()      # passaram os 2 minutos
        monitor.onPlayBackStarted()
        monitor.onAVStarted()
        self.assertEqual(len(self.chamadas), 2)


if __name__ == '__main__':
    unittest.main()
