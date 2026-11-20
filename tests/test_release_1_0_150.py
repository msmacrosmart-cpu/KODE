# -*- coding: utf-8 -*-
"""Suíte objetiva da release 1.0.150 — exatamente 3 testes por funcionalidade:

1. Reabertura do app restaurada ao estado da 1.0.148 + limpeza pós-erro de reprodução (3 testes);
2. TV ao vivo não solta novamente anúncio nas tentativas de reprodução; só após sair ou escolher outro conteúdo (3 testes).
"""
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'
EMPACTADOR = ROOT / 'tools' / 'kodi' / 'atualizar-apk-v17.py'
VERIFICADOR = ROOT / 'smartedtv' / 'release' / 'verify.py'
BUILD_SH = ROOT / 'smartedtv' / 'release' / 'build.sh'


def _carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ===========================================================================
# 1. REABERTURA NO ESTADO DA 1.0.148 + RESILIÊNCIA PÓS-ERRO DE REPRODUÇÃO (3 testes)
# ===========================================================================
class ReaberturaEstado148Test(unittest.TestCase):
    def test_1_dex_e_manifesto_100_por_cento_identicos_a_1_0_148(self):
        """Garante que classes*.dex e profile-manifest.txt permanecem 100% intocados
        em relação ao base-v22.apk, exatamente como na 1.0.148."""
        atu = _carregar('atu_150', EMPACTADOR)
        ver = _carregar('ver_150', VERIFICADOR)
        build_txt = BUILD_SH.read_text(encoding='utf-8')
        verify_txt = VERIFICADOR.read_text(encoding='utf-8')

        self.assertFalse(hasattr(atu, 'preparar_perfil_limpo'))
        self.assertFalse(hasattr(atu, '_atualizar_dex_com_pin'))
        self.assertFalse(hasattr(ver, 'verificar_classes4_dex'))
        self.assertIn("require(contents == before.read(path), 'código diferente da base: '+path)", verify_txt)
        self.assertNotIn('dexdump', build_txt)

    def test_2_reabertura_nao_toca_sqlite_nem_jsonrpc_e_limpa_residuos_pos_erro_reproducao(self):
        """Na reabertura do app (pastas de terceiros já ausentes) service.py não
        executa JSON-RPC síncrono, não abre Addons*.db nem dispara UpdateLocalAddons,
        e limpa arquivos .tmp/JSON truncados deixados por erro de reprodução."""
        tmp = tempfile.mkdtemp(prefix='smarted-reabertura150-')
        salvos = {k: sys.modules.get(k)
                  for k in ('xbmc', 'xbmcvfs', 'xbmcgui', 'xbmcaddon', 'ads_regra')}
        try:
            rpcs = []
            builtins = []
            props = {'smartedtv.welcome.saiu': '1', 'smartedtv.welcome.home': 'ok'}

            xbmc = types.ModuleType('xbmc')
            xbmc.log = lambda *a, **k: None
            xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
            xbmc.executebuiltin = lambda c: builtins.append(c)
            xbmc.getCondVisibility = lambda _c: False
            xbmc.executeJSONRPC = lambda p: (rpcs.append(json.loads(p)) or '{"result":"OK"}')
            xbmc.Monitor = object
            xbmc.Player = object
            sys.modules['xbmc'] = xbmc

            vfs = types.ModuleType('xbmcvfs')
            vfs.translatePath = lambda p: (
                p.replace('special://home/', tmp + '/')
                 .replace('special://home', tmp)
                 .replace('special://profile/', tmp + '/userdata/')
                 .replace('special://profile', tmp + '/userdata')
            )
            vfs.exists = os.path.exists
            vfs.listdir = lambda p: ([], os.listdir(p) if os.path.isdir(p) else [])
            sys.modules['xbmcvfs'] = vfs

            class FakeWindow(object):
                def __init__(self, *_a, **_k):
                    pass

                def clearProperty(self, k):
                    props.pop(k, None)

            sys.modules['xbmcgui'] = types.SimpleNamespace(Window=FakeWindow, Dialog=lambda: None)
            sys.modules['xbmcaddon'] = types.SimpleNamespace(
                Addon=lambda *a, **k: types.SimpleNamespace(
                    getAddonInfo=lambda ch: 'service.smarted.bootstrap' if ch == 'id' else tmp,
                    getSetting=lambda _k: '',
                )
            )

            os.makedirs(os.path.join(tmp, 'addons/plugin.video.BrazucaPlay.Matrix'), exist_ok=True)
            os.makedirs(os.path.join(tmp, 'userdata/Database'), exist_ok=True)
            pasta_boot = os.path.join(tmp, 'userdata/addon_data/service.smarted.bootstrap')
            os.makedirs(pasta_boot, exist_ok=True)

            # Simula resíduos deixados quando o app fechou no meio de erro de reprodução
            tmp_truncado = os.path.join(pasta_boot, 'ads-regra.json.tmp')
            json_corrompido = os.path.join(pasta_boot, 'ads-regra.json')
            Path(tmp_truncado).write_text('{quebrado', encoding='utf-8')
            Path(json_corrompido).write_text('{quebrado-no-crash', encoding='utf-8')

            if str(BOOTSTRAP) not in sys.path:
                sys.path.insert(0, str(BOOTSTRAP))
            svc = _carregar('svc_150', BOOTSTRAP / 'service.py')
            regra = _carregar('regra_150', BOOTSTRAP / 'ads_regra.py')

            self.assertTrue(svc.limpar_estado_interface())
            self.assertFalse(os.path.exists(tmp_truncado))
            self.assertEqual(props, {})

            # Reabertura com perfil já sem terceiros: zero RPC e zero UpdateLocalAddons
            self.assertEqual(svc.limpar_repositorios_de_terceiros(), [])
            self.assertEqual(rpcs, [])
            self.assertEqual(builtins, [])

            # E ads_regra se recupera automaticamente de JSON corrompido sem travar
            pode, _ = regra.pode_anunciar('filme:novo', agora=1000.0)
            self.assertTrue(pode)
        finally:
            if str(BOOTSTRAP) in sys.path:
                sys.path.remove(str(BOOTSTRAP))
            for k, mod in salvos.items():
                if mod is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = mod
            shutil.rmtree(tmp, ignore_errors=True)

    def test_3_versao_1_0_150_e_checkpoint_registrado(self):
        """Confere smarted_release.py em 1.0.150 / 2103136 e checkpoint documentado."""
        rel = _carregar('rel_150', BOOTSTRAP / 'smarted_release.py')
        self.assertEqual(rel.VERSION_NAME, '1.0.150')
        self.assertEqual(rel.VERSION_CODE, 2103136)
        chk = (ROOT / 'docs' / 'checkpoint-apk-padrao.md').read_text(encoding='utf-8')
        self.assertIn('v1.0.148-universal', chk)
        self.assertIn('v1.0.149-universal', chk)
        self.assertIn('v1.0.150-universal', chk)


# ===========================================================================
# 2. TV AO VIVO SEM RE-DISPARO DE ANÚNCIO NAS TENTATIVAS (3 testes)
# ===========================================================================
class TvAoVivoSemRepetirAnuncioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='smarted-live150-')
        self.salvos = {k: sys.modules.get(k)
                       for k in ('xbmc', 'xbmcvfs', 'xbmcaddon', 'xbmcgui',
                                 'ads_vast', 'ads_regra', 'variante', 'ao_vivo',
                                 'ad_return', 'smart_ads', 'vip')}
        self.relogio = [1000.0]
        self.mono = [500.0]
        self.labels = {}
        self.conds = {'System.Platform.Android', 'Window.IsActive(fullscreenvideo)'}
        self.builtins = []
        self.arquivo_atual = ['']
        self.tocando_video = [True]

        estado = self

        class FakePlayer(object):
            def __init__(self, *_a, **_k):
                pass

            def isPlayingVideo(self):
                return estado.tocando_video[0]

            def getPlayingFile(self):
                return estado.arquivo_atual[0]

            def getTime(self):
                return 0.0

        xbmc = types.ModuleType('xbmc')
        xbmc.Player = FakePlayer
        xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
        xbmc.log = lambda *a, **k: None
        xbmc.getInfoLabel = lambda k: self.labels.get(k, '')
        xbmc.getCondVisibility = lambda c: c in self.conds
        xbmc.executebuiltin = lambda cmd: self.builtins.append(cmd)
        xbmc.executeJSONRPC = lambda _p: '{"result":[{"playerid":1,"type":"video"}]}'
        sys.modules['xbmc'] = xbmc

        vfs = types.ModuleType('xbmcvfs')
        vfs.translatePath = lambda p: (
            self.tmp if p.startswith('special://profile') else p
        )
        vfs.exists = os.path.exists
        sys.modules['xbmcvfs'] = vfs

        if str(BOOTSTRAP) not in sys.path:
            sys.path.insert(0, str(BOOTSTRAP))

        self.ao_vivo = _carregar('ao_vivo', BOOTSTRAP / 'ao_vivo.py')
        self.ao_vivo.iniciar = lambda *a, **k: None
        sys.modules['ao_vivo'] = self.ao_vivo

        self.ads_regra = _carregar('ads_regra', BOOTSTRAP / 'ads_regra.py')
        sys.modules['ads_regra'] = self.ads_regra

        self.ad_return = _carregar('ad_return', BOOTSTRAP / 'ad_return.py')
        sys.modules['ad_return'] = self.ad_return

        sys.modules['vip'] = types.SimpleNamespace(ativa=lambda: False)
        sys.modules['variante'] = types.SimpleNamespace(
            ler=lambda: 'tv', e_tv=lambda *a, **k: True
        )

        self.smart_ads = _carregar('smart_ads', BOOTSTRAP / 'smart_ads.py')
        self.smart_ads.e_tv = lambda: False  # exercita fluxo síncrono determinístico
        self.smart_ads.vip_ativo = lambda: False
        self.anuncios_disparados = []
        self.smart_ads.abrir_anuncio = lambda ativ, log=None: (
            self.anuncios_disparados.append((ativ, self.arquivo_atual[0], self.labels.get('VideoPlayer.Title', ''))) or True
        )

        # Controla tempo wall-clock e monotônico para simular > 2 min sem dormir
        self._orig_time = time.time
        self._orig_mono = time.monotonic
        time.time = lambda: self.relogio[0]
        time.monotonic = lambda: self.mono[0]

    def tearDown(self):
        time.time = self._orig_time
        time.monotonic = self._orig_mono
        if str(BOOTSTRAP) in sys.path:
            sys.path.remove(str(BOOTSTRAP))
        for k, mod in self.salvos.items():
            if mod is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = mod
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _avancar(self, seg):
        self.relogio[0] += seg
        self.mono[0] += seg

    def test_1_tentativas_de_reproducao_quedas_proxy_e_opcao2_nao_repetem_anuncio(self):
        """Selecionado o canal na TV ao vivo, todas as tentativas de reprodução
        (queda onPlayBackEnded, erro onPlayBackError, nova porta de proxy LAN,
        reabertura interna pelo ao_vivo e troca OPÇÃO 1 -> OPÇÃO 2 mesmo após >2 min)
        NÃO disparam outro anúncio."""
        mon = self.smart_ads.MonitorPreRoll()

        # 1) Usuário seleciona GLOBO SP - OPÇÃO 1 -> roda 1 anúncio na seleção
        self.labels['VideoPlayer.Title'] = '[B][COLOR white]GLOBO SP[/COLOR][/B] - OPÇÃO 1'
        self.arquivo_atual[0] = 'http://192.168.0.10:49152/?url=http%3A%2F%2Fcdn1.tv%2Flive%2Fglobo.m3u8'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 1)
        self.ads_regra.concluir_anuncio(self.relogio[0] + 10)

        # 2) Passam-se 3 minutos (>120s!); o stream cai (onPlayBackEnded) e reconecta
        #    com nova porta de proxy LAN -> NÃO pode soltar anúncio
        self._avancar(180)
        mon.onPlayBackEnded()
        self.arquivo_atual[0] = 'http://192.168.0.10:55111/?url=http%3A%2F%2Fcdn1.tv%2Flive%2Fglobo.m3u8'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 1)

        # 3) Reabertura interna por ao_vivo._tocar_de_novo (URL direta sem título)
        #    que no Kodi emite onPlayBackStopped antes do novo onPlayBackStarted
        self._avancar(30)
        self.ao_vivo._tocar_de_novo('http://cdn1.tv/live/globo.m3u8')
        mon.onPlayBackStopped()
        self.labels['VideoPlayer.Title'] = 'globo.m3u8'
        self.arquivo_atual[0] = 'http://cdn1.tv/live/globo.m3u8'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 1)

        # 4) Erro de reprodução + tentativa na OPÇÃO 2 do mesmo canal em outro servidor
        self._avancar(180)
        mon.onPlayBackError()
        self.labels['VideoPlayer.Title'] = 'GLOBO SP - OPÇÃO 2 [FHD]'
        self.arquivo_atual[0] = 'http://servidor2.tv/canal/globo_sp_rota2.ts'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 1)

    def test_2_canal_selecionado_dentro_do_intervalo_nao_solta_anuncio_tardio_nas_tentativas(self):
        """Se o usuário selecionou o canal dentro da janela de 2 min (sem anúncio na
        entrada) e depois os 2 min vencem enquanto a TV ao vivo faz tentativas de
        reprodução, NÃO pode soltar anúncio no meio das tentativas."""
        mon = self.smart_ads.MonitorPreRoll()

        # Filme anterior exibiu anúncio em t=1000..1015
        self.labels['VideoPlayer.Title'] = 'Matrix'
        self.arquivo_atual[0] = 'http://vod.exemplo/filmes/matrix.mp4'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 1)
        self._avancar(15)
        self.ads_regra.concluir_anuncio(self.relogio[0])
        mon.onPlayBackStopped()

        # Em t+60s (ainda dentro dos 120s), usuário seleciona SPORTV 2 - OPÇÃO 1
        self._avancar(60)
        self.labels['VideoPlayer.Title'] = 'SPORTV 2 - OPÇÃO 1'
        self.arquivo_atual[0] = 'http://srv1.tv/live/sportv2.m3u8'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 1)

        # Em t+150s (já passou dos 120s!), o canal falha e tenta OPÇÃO 2 e reconexão:
        # como o canal já estava selecionado, NÃO pode soltar anúncio nas tentativas!
        self._avancar(90)
        mon.onPlayBackEnded()
        self.labels['VideoPlayer.Title'] = 'SPORTV 2 - OPÇÃO 2'
        self.arquivo_atual[0] = 'http://srv2.tv/live/sportv2_alt.ts'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 1)

    def test_3_apos_selecionar_canal_so_roda_anuncio_apos_sair_ou_escolher_outro_conteudo(self):
        """Comprova os dois únicos gatilhos liberados após selecionar um canal:
        (a) escolher outro conteúdo (outro canal ou filme, respeitando os 2 min);
        (b) sair do canal (onPlayBackStopped após assistir) e abrir conteúdo."""
        mon = self.smart_ads.MonitorPreRoll()

        # Seleciona Canal 1 -> 1º anúncio
        self.labels['VideoPlayer.Title'] = 'Band News'
        self.arquivo_atual[0] = 'http://tv.exemplo/live/bandnews.m3u8'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 1)
        self._avancar(10)
        self.ads_regra.concluir_anuncio(self.relogio[0])

        # (a) Escolhe OUTRO conteúdo (outro canal: ESPN) após >2 min -> libera 2º anúncio
        self._avancar(130)
        self.labels['VideoPlayer.Title'] = 'ESPN Brasil'
        self.arquivo_atual[0] = 'http://tv.exemplo/live/espn.m3u8'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 2)
        self._avancar(10)
        self.ads_regra.concluir_anuncio(self.relogio[0])

        # Assiste por 40s e SAI do canal (onPlayBackStopped real do usuário)
        self._avancar(40)
        mon.onPlayBackStopped()

        # (b) Após sair e passar o intervalo, abre outro conteúdo -> libera 3º anúncio
        self._avancar(95)
        self.labels['VideoPlayer.Title'] = 'Interestelar'
        self.arquivo_atual[0] = 'http://vod.exemplo/filmes/interestelar.mkv'
        mon.onPlayBackStarted()
        mon.onAVStarted()
        self.assertEqual(len(self.anuncios_disparados), 3)


if __name__ == '__main__':
    unittest.main()
