# -*- coding: utf-8 -*-
"""Anuncios do AdMob (abertura + video pre-roll) ligados ao Kodi.

O Kodi do APK e binario pronto: o SDK do AdMob vive no app `org.smartedtv.ads`
(pasta `android/smarted-ads`), aberto pelo Python via `StartAndroidActivity()`.
Os testes abaixo travam os dois lados da ponte:

  * o app Android sai com os IDs REAIS, landscape e com play-services-ads;
  * o Python liga o gancho de reproducao e mostra a abertura uma unica vez.
"""
import importlib.util
import os
import re
import shutil
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADS_DIR = ROOT / 'android' / 'smarted-ads'
MANIFEST = ADS_DIR / 'app' / 'src' / 'main' / 'AndroidManifest.xml'
ADS_JAVA = ADS_DIR / 'app' / 'src' / 'main' / 'java' / 'org' / 'smartedtv' / 'ads' / 'Ads.java'
APP_GRADLE = ADS_DIR / 'app' / 'build.gradle'
PY_MODULE = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'smart_ads.py'
SERVICE = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'service.py'

APP_ID = 'ca-app-pub-2066014755407744~5076693043'
UNIT_APP_OPEN = 'ca-app-pub-2066014755407744/4214378379'
UNIT_PREROLL = 'ca-app-pub-2066014755407744/3572039686'


class AdMobNoAppAndroidTest(unittest.TestCase):
    def setUp(self):
        self.manifest = MANIFEST.read_text()
        self.java = ADS_JAVA.read_text()
        self.gradle = APP_GRADLE.read_text()

    def test_application_id_real_no_manifesto(self):
        self.assertIn('com.google.android.gms.ads.APPLICATION_ID', self.manifest)
        self.assertIn(APP_ID, self.manifest)

    def test_dependencia_do_play_services_ads(self):
        self.assertRegex(self.gradle, r"com\.google\.android\.gms:play-services-ads:\d")

    def test_blocos_reais_de_anuncio(self):
        self.assertIn(UNIT_APP_OPEN, self.java)
        self.assertIn(UNIT_PREROLL, self.java)

    def test_as_duas_activities_em_landscape(self):
        for activity in ('AppOpenActivity', 'PreRollActivity'):
            bloco = re.search(r'<activity\b[^>]*%s[^>]*/>' % activity, self.manifest, re.S)
            self.assertIsNotNone(bloco, activity)
            self.assertIn('android:screenOrientation="sensorLandscape"', bloco.group(0))
            self.assertIn('android:exported="true"', bloco.group(0))

    def test_telas_forcam_landscape_e_nao_travem(self):
        base = (ADS_DIR / 'app/src/main/java/org/smartedtv/ads/AdActivity.java').read_text()
        self.assertIn('SCREEN_ORIENTATION_SENSOR_LANDSCAPE', base)
        # sem anuncio/erro, a tela se fecha sozinha: o usuario nunca fica preso
        self.assertIn('LIMITE_SEM_ANUNCIO', base)
        self.assertIn('FLAG_KEEP_SCREEN_ON', base)

    def test_abertura_usa_app_open_e_pre_roll_usa_video(self):
        abertura = (ADS_DIR / 'app/src/main/java/org/smartedtv/ads/AppOpenActivity.java').read_text()
        preroll = (ADS_DIR / 'app/src/main/java/org/smartedtv/ads/PreRollActivity.java').read_text()
        self.assertIn('AppOpenAd', abertura)
        self.assertIn('InterstitialAd', preroll)
        # nenhum dos dois pode prender a tela quando o anuncio falha
        for fonte in (abertura, preroll):
            self.assertIn('onAdFailedToLoad', fonte)
            self.assertIn('fechar()', fonte)

    def test_min_sdk_cobre_tv_box_antiga(self):
        self.assertIn('minSdk 21', self.gradle)
        self.assertIn('compileSdk 34', self.gradle)


def carregar_smart_ads(android=True):
    """Importa smart_ads com um xbmc de mentira (sem Kodi de verdade)."""
    chamadas = []
    fake_xbmc = types.ModuleType('xbmc')
    fake_xbmc.LOGINFO = 20
    fake_xbmc.LOGWARNING = 30
    fake_xbmc.getCondVisibility = lambda cond: bool(android)
    fake_xbmc.executebuiltin = lambda builtin: chamadas.append(builtin)

    class FakePlayer(object):
        tocando = False

        def isPlayingVideo(self):
            return FakePlayer.tocando

    fake_xbmc.Player = FakePlayer
    fake_vfs = types.ModuleType('xbmcvfs')
    fake_vfs.translatePath = lambda p: '/tmp/smarted-ads-test'
    fake_vfs.exists = os.path.exists   # a marca da abertura e um arquivo real
    antigos = {n: sys.modules.get(n) for n in ('xbmc', 'xbmcvfs')}
    sys.modules['xbmc'] = fake_xbmc
    sys.modules['xbmcvfs'] = fake_vfs
    try:
        spec = importlib.util.spec_from_file_location('smart_ads_teste', PY_MODULE)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
    finally:
        for nome, valor in antigos.items():
            if valor is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = valor
    return modulo, chamadas


class PontePythonTest(unittest.TestCase):
    def test_dispara_as_duas_telas_do_app_de_anuncios(self):
        modulo, chamadas = carregar_smart_ads()
        self.assertTrue(modulo.tocar_anuncio(modulo.ATIVIDADE_PREROLL))
        self.assertTrue(modulo.tocar_anuncio(modulo.ATIVIDADE_ABERTURA))
        # pacote (applicationId) e classe (namespace) sao coisas diferentes
        self.assertEqual(chamadas, [
            'StartAndroidActivity(%s,%s)' % (modulo.PACKAGE, modulo.ATIVIDADE_PREROLL),
            'StartAndroidActivity(%s,%s)' % (modulo.PACKAGE, modulo.ATIVIDADE_ABERTURA),
        ])
        self.assertEqual(modulo.PACKAGE, 'smartedtv.full')
        self.assertTrue(modulo.ATIVIDADE_PREROLL.startswith('org.smartedtv.ads.'))

    def test_pre_roll_respeita_intervalo(self):
        modulo, chamadas = carregar_smart_ads()
        self.assertTrue(modulo.mostrar_preroll(agora=1000.0))
        self.assertFalse(modulo.mostrar_preroll(agora=1010.0))   # zapping: nao repete
        self.assertTrue(modulo.mostrar_preroll(agora=1000.0 + modulo.PREROLL_INTERVALO + 1))

    def test_abertura_uma_vez_por_instalacao(self):
        shutil.rmtree('/tmp/smarted-ads-test', ignore_errors=True)
        self.addCleanup(shutil.rmtree, '/tmp/smarted-ads-test', True)
        modulo, chamadas = carregar_smart_ads()
        # primeira vez: mostra e grava a marca
        self.assertTrue(modulo.mostrar_abertura())
        self.assertTrue(modulo.abertura_ja_mostrada())
        self.assertEqual(len(chamadas), 1)
        # segunda vez: nem toca no builtin
        self.assertFalse(modulo.mostrar_abertura())
        self.assertEqual(len(chamadas), 1)

    def test_fora_do_android_nao_chama_nada(self):
        modulo, chamadas = carregar_smart_ads(android=False)
        self.assertFalse(modulo.tocar_anuncio(modulo.ATIVIDADE_PREROLL))
        self.assertIsNone(modulo.iniciar_monitor())
        self.assertEqual(chamadas, [])

    def test_gancho_escuta_o_player_do_kodi(self):
        fonte = PY_MODULE.read_text()
        self.assertIn('class MonitorPreRoll(_BasePlayer)', fonte)
        self.assertIn("getattr(xbmc, 'Player', object)", fonte)
        self.assertIn('def onPlay', fonte)
        self.assertIn('def onAVStarted', fonte)
        self.assertIn('isPlayingVideo', fonte)


class LigacaoNoBootTest(unittest.TestCase):
    def setUp(self):
        self.main = SERVICE.read_text()
        self.corpo = self.main[self.main.index('def main():'):]

    def test_servico_liga_os_anuncios(self):
        self.assertIn('import smart_ads', self.main)
        self.assertIn('smart_ads.iniciar_monitor(log)', self.corpo)
        self.assertIn('smart_ads.abertura_depois_do_boot', self.corpo)

    def test_abertura_depois_da_home_e_fora_da_linha_do_boot(self):
        # o pop-up so entra depois de skin e nos da Home prontos
        self.assertLess(self.corpo.index('ensure_home_nodes('),
                        self.corpo.index('smart_ads.abertura_depois_do_boot'))
        self.assertIn("name='ads-abertura'", self.corpo.replace('"', "'"))


class PacoteDoAppTest(unittest.TestCase):
    def pacote_do_arquivo(self):
        return (ADS_DIR / 'app-id.txt').read_text().strip()

    def test_pacote_do_python_e_o_application_id_do_app(self):
        arquivo = self.pacote_do_arquivo()
        gradle = APP_GRADLE.read_text()
        self.assertIn('app-id.txt', gradle, 'o Gradle deve ler app-id.txt')
        package_py = re.search(r"^PACKAGE = '([^']+)'", PY_MODULE.read_text(), re.M)
        self.assertIsNotNone(package_py)
        self.assertEqual(package_py.group(1), arquivo,
                         'PACKAGE do Python difere do applicationId do app')

    def test_arquivo_tem_um_pacote_valido(self):
        arquivo = self.pacote_do_arquivo()
        self.assertRegex(arquivo, r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$')

    def test_nunca_usa_o_pacote_do_kodi(self):
        gradle = APP_GRADLE.read_text()
        self.assertIn("pacotesProibidos = ['org.xbmc.kodi']", gradle)
        # e o pacote do Kodi nao pode aparecer como applicationId
        self.assertNotIn("applicationId 'org.xbmc.kodi'", gradle)
        fonte = PY_MODULE.read_text()
        self.assertNotIn("PACKAGE = 'org.xbmc.kodi'", fonte)

    def test_as_activities_ficam_no_namespace_do_app(self):
        # mudar o applicationId nao muda o nome das classes: a ponte continua
        # apontando para org.smartedtv.ads.AppOpenActivity / PreRollActivity
        fonte = PY_MODULE.read_text()
        self.assertIn("ATIVIDADE_ABERTURA = 'org.smartedtv.ads.AppOpenActivity'", fonte)
        self.assertIn("ATIVIDADE_PREROLL = 'org.smartedtv.ads.PreRollActivity'", fonte)


class NoBuildClassicoTest(unittest.TestCase):
    def test_fluxo_confere_os_anuncios_e_anexa_o_apk(self):
        fluxo = (ROOT / '.github/workflows/build-release-classica.yml').read_text()
        self.assertIn('smart_ads.iniciar_monitor', fluxo)     # confere o bootstrap embarcado
        self.assertIn('-ads', fluxo)                         # baixa o APK de anuncios
        self.assertIn('*Anuncios*', fluxo)                    # e anexa na mesma release

    def test_fluxo_de_anuncios_compila_com_a_mesma_chave(self):
        fluxo = (ROOT / '.github/workflows/build-ads-apk.yml').read_text()
        self.assertIn('play-services-ads', (ADS_DIR / 'app/build.gradle').read_text())
        self.assertIn('855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a', fluxo)
        self.assertIn('sensorLandscape', fluxo)


if __name__ == '__main__':
    unittest.main()
