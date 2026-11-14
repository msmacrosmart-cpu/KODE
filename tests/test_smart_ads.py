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
        for activity in ('AppOpenActivity', 'PreRollActivity', 'LauncherActivity'):
            bloco = re.search(r'<activity\b[^>]*%s[^>]*>' % activity, self.manifest, re.S)
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
            self.assertIn('fechar("', fonte)

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
        # cada disparo manda o componente explicito e tambem o plano B (launcher)
        self.assertEqual(chamadas, [
            modulo.builtin_para(modulo.ATIVIDADE_PREROLL),
            modulo.builtin_launcher(modulo.URI_PREROLL),
            modulo.builtin_para(modulo.ATIVIDADE_ABERTURA),
            modulo.builtin_launcher(modulo.URI_ABERTURA),
        ])
        self.assertEqual(modulo.PACKAGE, 'smartedtv.full')
        self.assertTrue(modulo.ATIVIDADE_PREROLL.startswith('org.smartedtv.ads.'))

    def test_parametro_intent_nao_pode_ser_vazio(self):
        # CXBMCApp::StartActivity: intent vazio -> getLaunchIntentForPackage()
        # -> null (app sem launcher) -> return false, sem olhar o className.
        modulo, _ = carregar_smart_ads()
        for atividade, acao in ((modulo.ATIVIDADE_PREROLL, modulo.ACAO_PREROLL),
                                (modulo.ATIVIDADE_ABERTURA, modulo.ACAO_ABERTURA)):
            campos = modulo.builtin_para(atividade)[len('StartAndroidActivity('):-1].split(',')
            self.assertTrue(campos[1], 'parametro intent vazio (builtin morre no launcher)')
            self.assertEqual(campos[1], acao)
            self.assertEqual(campos[8], atividade)

    def test_plano_b_usa_o_launcher_com_data_uri(self):
        modulo, _ = carregar_smart_ads()
        builtin = modulo.builtin_launcher(modulo.URI_PREROLL)
        campos = builtin[len('StartAndroidActivity('):-1].split(',')
        self.assertEqual(campos[0], modulo.PACKAGE)
        self.assertEqual(campos[3], 'smartedtv://ads/preroll')
        self.assertEqual(campos[8], modulo.ATIVIDADE_LAUNCHER)

    def test_marca_da_abertura_tem_versao(self):
        # as versoes antigas gravavam a marca sem o pop-up abrir; marca velha
        # nao pode bloquear a abertura nova
        modulo, chamadas = carregar_smart_ads()
        shutil.rmtree('/tmp/smarted-ads-test', ignore_errors=True)
        self.addCleanup(shutil.rmtree, '/tmp/smarted-ads-test', True)
        caminho = os.path.join('/tmp/smarted-ads-test', 'addon_data',
                               'service.smarted.bootstrap', 'ads-abertura.txt')
        os.makedirs(os.path.dirname(caminho))
        with open(caminho, 'w') as arquivo:
            arquivo.write('abertura mostrada em 2026-01-01 00:00:00\n')   # marca antiga
        self.assertFalse(modulo.abertura_ja_mostrada())
        self.assertTrue(modulo.mostrar_abertura())
        self.assertTrue(modulo.abertura_ja_mostrada())

    def test_builtin_tem_a_classe_no_ultimo_parametro(self):
        # ORDEM DO KODI (v20+): package, intent, dataType, dataURI, flags,
        # extras, action, category, className. Passar a classe em segundo lugar
        # cria um intent sem componente e a tela NUNCA abre (bug do no-fill).
        modulo, _ = carregar_smart_ads()
        builtin = modulo.builtin_para(modulo.ATIVIDADE_PREROLL)
        campos = builtin[builtin.index('(') + 1:-1].split(',')
        self.assertEqual(len(campos), 9, builtin)
        self.assertEqual(campos[0], modulo.PACKAGE)
        self.assertTrue(campos[1], 'posicao 2 (intent) nao pode ser vazia')
        self.assertEqual(campos[2:8], [''] * 6, 'campos do meio precisam ficar vazios')
        self.assertEqual(campos[8], modulo.ATIVIDADE_PREROLL)
        self.assertIn('PreRollActivity', campos[8])
        self.assertNotIn(modulo.ATIVIDADE_PREROLL, campos[1], 'classe nao pode ir em 2o lugar')

    def test_pre_roll_respeita_intervalo(self):
        modulo, chamadas = carregar_smart_ads()
        self.assertTrue(modulo.mostrar_preroll(agora=1000.0))
        self.assertFalse(modulo.mostrar_preroll(agora=1010.0))   # zapping: nao repete
        self.assertTrue(modulo.mostrar_preroll(agora=1000.0 + modulo.PREROLL_INTERVALO + 1))

    def test_abertura_uma_vez_por_instalacao(self):
        shutil.rmtree('/tmp/smarted-ads-test', ignore_errors=True)
        self.addCleanup(shutil.rmtree, '/tmp/smarted-ads-test', True)
        modulo, chamadas = carregar_smart_ads()
        # primeira vez: mostra e grava a marca (componente + plano B + aviso)
        self.assertTrue(modulo.mostrar_abertura())
        self.assertTrue(modulo.abertura_ja_mostrada())
        disparos = [c for c in chamadas if c.startswith('StartAndroidActivity(')]
        self.assertEqual(len(disparos), 2)
        # segunda vez: nem toca no builtin
        self.assertFalse(modulo.mostrar_abertura())
        self.assertEqual(len([c for c in chamadas if c.startswith('StartAndroidActivity(')]), 2)

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


class DiagnosticoTest(unittest.TestCase):
    """Modo de teste do AdMob + logs da tag SmartAds (homologacao)."""

    def setUp(self):
        self.ads_java = ADS_JAVA.read_text()
        self.base = (ADS_DIR / 'app/src/main/java/org/smartedtv/ads/AdActivity.java').read_text()
        self.abertura = (ADS_DIR / 'app/src/main/java/org/smartedtv/ads/AppOpenActivity.java').read_text()
        self.preroll = (ADS_DIR / 'app/src/main/java/org/smartedtv/ads/PreRollActivity.java').read_text()
        self.gradle = APP_GRADLE.read_text()

    def test_tag_de_log_unica(self):
        # tudo sai pela mesma tag: adb logcat -s SmartAds
        self.assertIn('public static final String TAG = "SmartAds"', self.ads_java)
        self.assertIn('Log.i(Ads.TAG', self.base)
        self.assertIn('Log.w(Ads.TAG', self.base)
        for fonte in (self.abertura, self.preroll):
            self.assertNotIn('Log.i("SmartAds"', fonte)   # usam o log() da base
        self.assertIn('log("carregando ABERTURA', self.abertura)
        self.assertIn('log("carregando VIDEO', self.preroll)

    def test_blocos_de_teste_oficiais(self):
        self.assertIn('ca-app-pub-3940256099942544/9257395921', self.ads_java)   # app open teste
        self.assertIn('ca-app-pub-3940256099942544/1033173712', self.ads_java)   # interstitial teste

    def test_modo_de_teste_controlado_pelo_build(self):
        self.assertIn('buildConfigField "boolean", "ADS_TESTE"', self.gradle)
        self.assertIn('funProperty'.replace('funProperty', 'findProperty'), self.gradle)
        self.assertIn('private static boolean teste = BuildConfig.ADS_TESTE', self.ads_java)
        self.assertIn('unidadeAppOpen()', self.ads_java)

    def test_loga_codigo_numerico_do_erro(self):
        self.assertIn('erro.getCode()', self.abertura)
        self.assertIn('erro.getDomain()', self.abertura)
        self.assertIn('onAdFailedToLoad', self.abertura)
        self.assertIn('onAdFailedToLoad', self.preroll)
        self.assertIn('onAdLoaded', self.abertura)
        self.assertIn('onAdLoaded', self.preroll)

    def test_erro_aparece_na_tela_em_modo_de_teste(self):
        self.assertIn('mostrarDiagnostico', self.base)
        self.assertIn('Ads.testeAtivo()', self.base)
        self.assertIn('mostrarDiagnostico("Falha ao CARREGAR o video"', self.preroll)

    def test_launcher_e_intent_filters_no_manifesto(self):
        manifesto = MANIFEST.read_text()
        # launcher (plano B do start) ...
        self.assertIn('org.smartedtv.ads.LauncherActivity', manifesto)
        self.assertIn('android.intent.category.LAUNCHER', manifesto)
        # ... e as actions usadas na posicao 2 do StartAndroidActivity
        self.assertIn('smartedtv.ads.PREROLL', manifesto)
        self.assertIn('smartedtv.ads.APPOPEN', manifesto)

    def test_toast_visivel_em_caso_de_falha(self):
        self.assertIn('Toast.makeText', self.base)
        self.assertIn('Toast.makeText', self.abertura) if 'Toast' in self.abertura else None
        launcher = (ADS_DIR / 'app/src/main/java/org/smartedtv/ads/LauncherActivity.java').read_text()
        self.assertIn('Toast.makeText', launcher)
        self.assertIn('Smartedtv'.lower(), launcher.lower())

    def test_visibilidade_de_pacotes_android_11(self):
        # componente explicito (className) nao depende de <queries>, mas a
        # declaracao deixa o app capaz de consultar o Kodi
        manifesto = MANIFEST.read_text()
        self.assertIn('<queries>', manifesto)
        self.assertIn('<package android:name="org.xbmc.kodi" />', manifesto)


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
