# -*- coding: utf-8 -*-
"""APK ÚNICO (monólito): Kodi compilado do fonte com AdMob dentro.

O usuário pediu o fim do modelo de dois aplicativos: um só APK, pacote
`smartedtv.full`, com player + anúncios + catálogo. Estes testes travam:

  * a integração no código-fonte (Java, Gradle, manifesto, Install.cmake);
  * o conteúdo da linha clássica embarcado (skin.novatv + addons);
  * a ponte do Python apontando para DENTRO do app (sem plano B, que
    reiniciaria o próprio Kodi);
  * o workflow que compila e confere o APK antes de publicar.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'smartedtv' / 'tools' / 'integrate-monolith.py'
ADS_JAVA = ROOT / 'smartedtv' / 'tools' / 'ads-java'
WORKFLOW = ROOT / '.github' / 'workflows' / 'build-monolith.yml'
BRIDGE = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'smart_ads.py'

PACOTE = 'smartedtv.full'


def ler(caminho):
    return Path(caminho).read_text(encoding='utf-8')


class IntegracaoNoFonteTest(unittest.TestCase):
    def setUp(self):
        self.script = ler(SCRIPT)

    def test_pacote_unico_e_versao(self):
        self.assertIn(f'APP_PACKAGE = "{PACOTE}"', self.script)
        self.assertIn('VERSAO_NOME = "1.0.64"', self.script)
        self.assertIn('VERSAO_CODIGO = 2103050', self.script)
        # tem que ser maior que a 1.0.63 (2103049) para nao regredir instalacao
        self.assertGreater(2103050, 2103049)

    def test_gradle_ganha_o_admob_e_a_versao(self):
        self.assertIn("com.google.android.gms:play-services-ads:23.2.0", self.script)
        self.assertIn('versionCode @APP_VERSION_CODE_ANDROID@', self.script)
        self.assertIn('versionName "@APP_VERSION@"', self.script)

    def test_manifesto_ganha_application_id_e_as_telas(self):
        self.assertIn('ca-app-pub-2066014755407744~5076693043', self.script)
        self.assertIn('com.google.android.gms.permission.AD_ID', self.script)
        self.assertIn('android:screenOrientation="sensorLandscape"', self.script)
        self.assertIn('android:exported="true"', self.script)
        self.assertIn('android:noHistory="true"', self.script)

    def test_java_novo_entra_na_lista_do_install_cmake(self):
        # sem isto o Gradle nao compila as classes novas
        self.assertIn('cmake/scripts/android/Install.cmake', self.script)
        self.assertIn('package_files', self.script)
        self.assertIn('src/SmartAds.java', self.script)

    def test_app_name_do_kodi_continua_kodi(self):
        # trocar APP_NAME renomearia libkodi.so e o perfil .kodi
        self.assertIn('APP_NAME precisa continuar', self.script)

    def test_falha_alto_quando_o_upstream_muda(self):
        # nada de patch "no escuro": ocorrencia != 1 = erro
        self.assertIn('o upstream mudou', self.script)
        self.assertIn('ErroDePatch', self.script)


class ConteudoClassicoEmbarcadoTest(unittest.TestCase):
    def setUp(self):
        self.script = ler(SCRIPT)

    def test_skin_novatv_vira_a_padrao(self):
        self.assertIn('kodi/skin.estilo.personalizado', self.script)
        self.assertIn('SKIN_ID = "skin.novatv"', self.script)
        self.assertIn('estuary', self.script)  # fica como reserva
        self.assertIn('lookandfeel\\.skin', self.script)

    def test_addons_do_catalogo_entram_no_apk(self):
        for addon in ('plugin.video.smarted', 'service.smarted.bootstrap',
                      'resource.uisounds.silencio'):
            self.assertIn(addon, self.script)
        # duas listas: o que empacota e o que e de sistema
        self.assertIn('cmake/installdata/common/addons.txt', self.script)
        self.assertIn('system/addon-manifest.xml', self.script)

    def test_ponte_aponta_para_dentro_do_app(self):
        self.assertIn(f"ATIVIDADE_PREROLL = '{{APP_PACKAGE}}.PreRollActivity'", self.script)
        self.assertIn(f"ATIVIDADE_ABERTURA = '{{APP_PACKAGE}}.AppOpenActivity'", self.script)
        # plano B abriria o launcher do proprio Kodi (reiniciaria a interface)
        self.assertIn('tentar_plano_b=False', self.script)


class JavaEmbarcadoTest(unittest.TestCase):
    def test_pacote_do_template(self):
        for nome in ('SmartAds', 'AdTela', 'AppOpenActivity', 'PreRollActivity'):
            fonte = ler(ADS_JAVA / f'{nome}.java.in')
            self.assertTrue(fonte.startswith('package @APP_PACKAGE@;'), nome)

    def test_sem_buildconfig_nem_androidx(self):
        # o projeto do Kodi nao gera BuildConfig e nao precisa de androidx aqui
        for arquivo in ADS_JAVA.glob('*.java.in'):
            fonte = ler(arquivo)
            self.assertNotIn('BuildConfig', fonte, arquivo.name)
            self.assertNotIn('androidx.', fonte, arquivo.name)

    def test_ids_reais_do_admob(self):
        smart = ler(ADS_JAVA / 'SmartAds.java.in')
        self.assertIn('ca-app-pub-2066014755407744~5076693043', smart)
        self.assertIn('ca-app-pub-2066014755407744/4214378379', smart)
        self.assertIn('ca-app-pub-2066014755407744/3572039686', smart)

    def test_abertura_e_interstitial(self):
        abertura = ler(ADS_JAVA / 'AppOpenActivity.java.in')
        preroll = ler(ADS_JAVA / 'PreRollActivity.java.in')
        self.assertIn('AppOpenAd.load', abertura)
        self.assertIn('InterstitialAd.load', preroll)
        self.assertIn('.show(', abertura)
        self.assertIn('.show(', preroll)

    def test_horizontal_e_sem_prender_o_usuario(self):
        base = ler(ADS_JAVA / 'AdTela.java.in')
        self.assertIn('SCREEN_ORIENTATION_SENSOR_LANDSCAPE', base)
        self.assertIn('LIMITE_SEM_ANUNCIO', base)
        self.assertIn('FLAG_KEEP_SCREEN_ON', base)
        self.assertIn('Toast.makeText', base)


class WorkflowDoMonolitoTest(unittest.TestCase):
    def setUp(self):
        self.fluxo = ler(WORKFLOW)

    def test_compila_do_fonte_na_branch_certa(self):
        self.assertIn('branches: [arena/7dedf371-kode]', self.fluxo)
        self.assertIn('KODI_TAG: 21.3-Omega', self.fluxo)
        self.assertIn('make -C "$RUNNER_TEMP/kodi-build" -j2', self.fluxo)
        self.assertIn('make -C "$RUNNER_TEMP/kodi-build" apk', self.fluxo)

    def test_roda_a_integracao_antes_de_compilar(self):
        self.assertIn('integrate-monolith.py', self.fluxo)
        self.assertIn('--brand-dir smartedtv/out', self.fluxo)
        self.assertIn('--language-addon', self.fluxo)

    def test_confere_o_apk_unico_antes_de_publicar(self):
        for marca in ("package: name='%s'",
                      '.PreRollActivity', '.AppOpenActivity',
                      'ca-app-pub-2066014755407744~5076693043',
                      'assets/addons/skin.novatv/addon.xml',
                      'plugin.video.smarted',
                      "ATIVIDADE_PREROLL = 'smartedtv.full.PreRollActivity'"):
            self.assertIn(marca, self.fluxo)
        # o pacote comparado é o do env PACOTE (smartedtv.full)
        self.assertIn('PACOTE: smartedtv.full', self.fluxo)
        # o prefixo das dependências tem subdiretório por alvo (regressão real:
        # exigir $RUNNER_TEMP/xbmc-depends/lib derrubou dois runs)
        self.assertIn('xbmc-depends/*-android-*', self.fluxo)
        self.assertNotIn('test -d "$RUNNER_TEMP/xbmc-depends/lib"', self.fluxo)
        # a conferência é bloqueante (sem continue-on-error)
        bloco = self.fluxo.split('10. Conferir o monolito')[1].split('- name:')[0]
        self.assertNotIn('continue-on-error', self.fluxo.split('10. Conferir o monolito')[1])

    def test_publica_com_assinatura_da_linha(self):
        self.assertIn('TAG_DESTINO: v1.0.64-unificado', self.fluxo)
        self.assertIn('dropbox/smarted-tv-test.jks', self.fluxo)
        self.assertIn('855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a', self.fluxo)

    def test_usa_a_receita_que_ja_compilou(self):
        self.assertIn('ndk;$NDK_VERSION', self.fluxo)
        self.assertIn('cmakebuildsys', self.fluxo)
        self.assertIn('timeout-minutes: 300', self.fluxo)


class ScriptFalhaComFonteInvalidoTest(unittest.TestCase):
    """O script não pode aplicar patch em árvore que não é o Kodi."""

    def test_pasta_vazia_falha_com_mensagem(self):
        import tempfile
        with tempfile.TemporaryDirectory() as pasta:
            saida = subprocess.run(
                [sys.executable, str(SCRIPT), pasta],
                capture_output=True, text=True)
        self.assertNotEqual(saida.returncode, 0)
        self.assertIn('nao parece ser o codigo-fonte do Kodi', saida.stderr + saida.stdout)


class PonteDoRepositorioContinuaValidaTest(unittest.TestCase):
    """A ponte original (app externo) não pode ser quebrada pelo monólito."""

    def test_ponte_do_repositorio_intacta(self):
        ponte = ler(BRIDGE)
        self.assertIn("PACKAGE = 'smartedtv.full'", ponte)
        self.assertIn("ATIVIDADE_PREROLL = 'org.smartedtv.ads.PreRollActivity'", ponte)
        # o patch do monólito é feito numa CÓPIA dentro do fonte
        self.assertNotIn('smartedtv.full.PreRollActivity', ponte)


if __name__ == '__main__':
    unittest.main()
