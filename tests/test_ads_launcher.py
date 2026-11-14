# -*- coding: utf-8 -*-
"""App de anuncios como LAUNCHER/INSTALADOR leve do SMARTEDTV.

Regras que estes testes travam (o usuario pediu exatamente isto):

  * o app de anuncios e a porta de entrada, leve (~10 MB no maximo);
  * ao abrir, ele verifica se o app principal (`org.xbmc.kodi`) esta instalado;
  * se nao estiver, mostra boas-vindas, baixa o APK principal de um link direto
    e dispara a instalacao na tela do Android;
  * se estiver, abre o SMARTEDTV normalmente;
  * a ponte do AdMob (`StartAndroidActivity` -> PreRoll/AppOpen) fica intacta:
    so o data URI `smartedtv://ads...` roteia para anuncio.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADS_DIR = ROOT / 'android' / 'smarted-ads'
PACOTE_JAVA = ADS_DIR / 'app' / 'src' / 'main' / 'java' / 'org' / 'smartedtv' / 'ads'
MANIFEST = ADS_DIR / 'app' / 'src' / 'main' / 'AndroidManifest.xml'
FILE_PATHS = ADS_DIR / 'app' / 'src' / 'main' / 'res' / 'xml' / 'file_paths.xml'
APK_URL_TXT = ADS_DIR / 'apk-url.txt'
APP_GRADLE = ADS_DIR / 'app' / 'build.gradle'
WORKFLOW = ROOT / '.github' / 'workflows' / 'build-ads-apk.yml'


def ler(nome):
    return (PACOTE_JAVA / (nome + '.java')).read_text()


class LinkDoApkPrincipalTest(unittest.TestCase):
    """O endereco do APK principal tem uma fonte unica e e verificavel."""

    def setUp(self):
        self.texto = APK_URL_TXT.read_text()
        self.campos = {}
        self.urls = []
        for linha in self.texto.splitlines():
            linha = linha.strip()
            if not linha or linha.startswith('#') or '=' not in linha:
                continue
            chave, valor = linha.split('=', 1)
            chave, valor = chave.strip(), valor.strip()
            if chave == 'url':
                self.urls.append(valor)
            else:
                self.campos[chave] = valor

    def test_link_direto_https_do_apk(self):
        for url in self.urls:
            self.assertTrue(url.startswith('https://'), url)
            self.assertIn('.apk', url)
            # nunca a PAGINA do arquivo: tem que ser o download direto
            self.assertNotIn('dl=0', url, url)

    def test_nenhum_link_de_release_privada(self):
        # anexo de repositorio privado responde 404 para quem nao esta logado
        # (era exatamente o erro na TV). O link do GitHub so vale em repo publico.
        for url in self.urls:
            if '/releases/download/' in url:
                self.fail('link de release do GitHub no apk-url.txt: se o repositorio '
                          'for privado ele responde 404 na TV. Use hospedagem publica '
                          '(Dropbox ?dl=1, servidor proprio). Link: %s' % url)

    def test_pagina_de_reserva_para_o_navegador(self):
        # se todos os links diretos falharem, o app abre esta pagina
        pagina = self.campos['pagina']
        self.assertTrue(pagina.startswith('https://'), pagina)

    def test_link_entrega_o_arquivo_certo(self):
        # o nome do arquivo tem que ser o do APK principal (nao o do app de anuncios)
        for url in self.urls:
            self.assertIn('SMARTED', url.upper())
            self.assertNotIn('Anuncios', url)

    def test_sem_login_para_baixar(self):
        # Dropbox: ?dl=1 entrega os bytes; qualquer outro host: nada de login
        url = self.urls[0]
        if 'dropbox.com' in url:
            self.assertIn('dl=1', url)

    def test_codigo_minimo_do_kodi(self):
        codigo = int(self.campos['codigo'])
        self.assertGreater(codigo, 2000000)
        # o codigo do link tem que casar com o da versao publicada
        self.assertEqual(codigo, 2103049)

    def test_gradle_gera_buildconfig_a_partir_do_arquivo(self):
        gradle = APP_GRADLE.read_text()
        self.assertIn("rootProject.file('apk-url.txt')", gradle)
        self.assertIn('buildConfigField "String", "APK_URLS"', gradle)
        self.assertIn('buildConfigField "String", "APK_URL"', gradle)
        self.assertIn('buildConfigField "String", "APK_PAGINA"', gradle)
        self.assertIn('buildConfigField "int", "APK_CODIGO_MINIMO"', gradle)
        # o CI pode sobrescrever o endereco sem editar o arquivo
        self.assertIn("findProperty('apkUrls')", gradle)


class VerificacaoDoKodiTest(unittest.TestCase):
    def setUp(self):
        self.kodi = ler('Kodi')

    def test_confere_o_pacote_do_app_principal(self):
        self.assertIn('PACOTE = "org.xbmc.kodi"', self.kodi)
        self.assertIn('getPackageInfo', self.kodi)
        self.assertIn('NameNotFoundException', self.kodi)

    def test_versioncode_nas_duas_apis(self):
        self.assertIn('getLongVersionCode', self.kodi)
        self.assertIn('VERSION_CODES.P', self.kodi)

    def test_abre_o_smart_edtv_pelo_launcher_do_sistema(self):
        self.assertIn('getLaunchIntentForPackage', self.kodi)
        self.assertIn('getLeanbackLaunchIntentForPackage', self.kodi)

    def test_instalado_mas_velho_oferece_atualizar(self):
        self.assertIn('desatualizado', self.kodi)
        self.assertIn('CODIGO_MINIMO', self.kodi)


class DownloadEInstalacaoTest(unittest.TestCase):
    def setUp(self):
        self.instalador = ler('Instalador')

    def test_varios_links_com_fallback(self):
        # anexo de repositorio privado responde 404 para quem nao esta logado:
        # o app precisa poder tentar o proximo endereco
        self.assertIn('BuildConfig.APK_URLS', self.instalador)
        self.assertIn('avancarUrl', self.instalador)
        self.assertIn('temProximoUrl', self.instalador)
        self.assertIn('urlAtual', self.instalador)

    def test_traduz_o_http_404(self):
        self.assertIn('HTTP ', self.instalador)
        self.assertIn('release privada', self.instalador)
        self.assertIn('case 404', self.instalador)

    def test_usa_o_downloadmanager_do_sistema(self):
        # 242 MB nao podem passar pela memoria do app
        self.assertIn('DownloadManager', self.instalador)
        self.assertIn('dm.enqueue', self.instalador)

    def test_baixa_na_pasta_privada_do_app(self):
        self.assertIn('setDestinationInExternalFilesDir', self.instalador)
        self.assertNotIn('setDestinationInExternalPublicDir', self.instalador)

    def test_instala_por_content_uri(self):
        self.assertIn('FileProvider.getUriForFile', self.instalador)
        self.assertIn("MIME_APK = \"application/vnd.android.package-archive\"", self.instalador)
        self.assertIn('FLAG_GRANT_READ_URI_PERMISSION', self.instalador)
        # file:// estoura FileUriExposedException no Android 7+
        self.assertNotIn('Uri.fromFile', self.instalador)

    def test_pede_permissao_de_instalar_apps_desconhecidos(self):
        self.assertIn('canRequestPackageInstalls', self.instalador)
        self.assertIn('ACTION_MANAGE_UNKNOWN_APP_SOURCES', self.instalador)

    def test_acompanha_progresso_e_falhas(self):
        for coluna in ('COLUMN_BYTES_DOWNLOADED_SO_FAR', 'COLUMN_TOTAL_SIZE_BYTES',
                       'COLUMN_STATUS', 'COLUMN_REASON'):
            self.assertIn(coluna, self.instalador)
        self.assertIn('ERROR_INSUFFICIENT_SPACE', self.instalador)

    def test_nao_rebaixa_o_que_ja_esta_no_aparelho(self):
        self.assertIn('jaBaixado', self.instalador)


class TelaDeBoasVindasTest(unittest.TestCase):
    def setUp(self):
        self.tela = ler('BoasVindasActivity')

    def test_baixa_sozinho_na_primeira_abertura(self):
        self.assertIn('baixarSozinho', self.tela)
        self.assertIn('ESPERA_ANTES_DE_BAIXAR', self.tela)

    def test_tem_barra_de_progresso_e_estados(self):
        self.assertIn('ProgressBar', self.tela)
        self.assertIn('progressBarStyleHorizontal', self.tela)
        for marca in ('Baixando', 'Instalar agora', 'Tentar de novo'):
            self.assertIn(marca, self.tela)

    def test_abre_a_instalacao_ao_terminar(self):
        self.assertIn('Instalador.instalar(this)', self.tela)

    def test_saida_pelo_navegador_quando_tudo_falha(self):
        # botao "Abrir no navegador" -> pagina da release (apk-url.txt, pagina=)
        self.assertIn('abrirNoNavegador', self.tela)
        self.assertIn('Instalador.PAGINA', self.tela)
        self.assertIn('Intent.ACTION_VIEW', self.tela)

    def test_pula_sozinho_para_o_proximo_link(self):
        self.assertIn('pulouDeLink', self.tela)
        self.assertIn('Instalador.avancarUrl(this)', self.tela)

    def test_sempre_horizontal_e_sem_apagar_a_tela(self):
        self.assertIn('SCREEN_ORIENTATION_SENSOR_LANDSCAPE', self.tela)
        self.assertIn('FLAG_KEEP_SCREEN_ON', self.tela)

    def test_nao_mexe_no_admob(self):
        self.assertNotIn('MobileAds', self.tela)
        self.assertNotIn('AdRequest', self.tela)


class LauncherRoteiaSemQuebrarAPonteTest(unittest.TestCase):
    def setUp(self):
        self.launcher = ler('LauncherActivity')
        self.manifest = MANIFEST.read_text()

    def test_data_uri_da_ponte_vai_para_anuncio(self):
        self.assertIn('URI_ADS = "smartedtv://ads"', self.launcher)
        self.assertIn('startsWith(URI_ADS)', self.launcher)
        self.assertIn('PreRollActivity.class', self.launcher)
        self.assertIn('AppOpenActivity.class', self.launcher)

    def test_icone_do_app_vai_para_o_instalador_ou_para_o_kodi(self):
        self.assertIn('BoasVindasActivity.class', self.launcher)
        self.assertIn('Kodi.instalado(this)', self.launcher)
        self.assertIn('Kodi.abrir(this)', self.launcher)
        # o icone do app NUNCA abre anuncio
        self.assertIn('ehAnuncio', self.launcher)

    def test_activity_de_anuncio_continua_exportada_e_horizontal(self):
        for activity in ('PreRollActivity', 'AppOpenActivity', 'LauncherActivity'):
            bloco = re.search(r'<activity\b[^>]*%s[^>]*>' % activity, self.manifest, re.S)
            self.assertIsNotNone(bloco, activity)
            self.assertIn('android:screenOrientation="sensorLandscape"', bloco.group(0))
            self.assertIn('android:exported="true"', bloco.group(0))

    def test_boas_vindas_e_interna_e_horizontal(self):
        bloco = re.search(r'<activity\b[^>]*BoasVindasActivity[^>]*>', self.manifest, re.S)
        self.assertIsNotNone(bloco)
        self.assertIn('android:screenOrientation="sensorLandscape"', bloco.group(0))
        # so o LauncherActivity abre esta tela (o Kodi nunca cai aqui)
        self.assertIn('android:exported="false"', bloco.group(0))


class ManifestoDoInstaladorTest(unittest.TestCase):
    def setUp(self):
        self.manifest = MANIFEST.read_text()

    def test_permissao_de_instalar_apk(self):
        self.assertIn('android.permission.REQUEST_INSTALL_PACKAGES', self.manifest)

    def test_file_provider_privado(self):
        self.assertIn('androidx.core.content.FileProvider', self.manifest)
        self.assertIn('${applicationId}.arquivos', self.manifest)
        self.assertIn('android:grantUriPermissions="true"', self.manifest)
        self.assertIn('@xml/file_paths', self.manifest)

    def test_caminhos_do_file_provider(self):
        caminhos = FILE_PATHS.read_text()
        self.assertIn('<external-files-path', caminhos)
        self.assertIn('path="Download/"', caminhos)

    def test_visibilidade_do_pacote_do_kodi(self):
        self.assertIn('<package android:name="org.xbmc.kodi" />', self.manifest)

    def test_manifesto_continua_valido(self):
        from xml.etree import ElementTree
        ElementTree.fromstring(MANIFEST.read_text())

    def test_quatro_activities_com_orientacao_horizontal(self):
        self.assertEqual(self.manifest.count('android:screenOrientation="sensorLandscape"'), 4)


class BuildDoAppTest(unittest.TestCase):
    def setUp(self):
        self.gradle = APP_GRADLE.read_text()

    def test_fileprovider_vem_do_androidx_core(self):
        self.assertRegex(self.gradle, r"androidx\.core:core:\d")

    def test_checkadmob_trava_o_instalador(self):
        self.assertIn('REQUEST_INSTALL_PACKAGES', self.gradle)
        self.assertIn('@xml/file_paths', self.gradle)
        self.assertIn('apk-url.txt sem', self.gradle)


class WorkflowDoAppTest(unittest.TestCase):
    def setUp(self):
        self.fluxo = WORKFLOW.read_text()

    def test_versao_nova(self):
        self.assertIn('VERSAO_ADS: "1.0.6"', self.fluxo)
        self.assertIn('CODIGO_ADS: "7"', self.fluxo)
        self.assertIn('TAG_ADS: v1.0.6-ads', self.fluxo)

    def test_baixa_o_apk_do_link_antes_de_publicar(self):
        # garante que o link entrega MESMO o org.xbmc.kodi na versao minima
        self.assertIn('0c. Baixar o APK do link', self.fluxo)
        self.assertIn("apk.package != 'org.xbmc.kodi'", self.fluxo)

    def test_le_o_apk_url_e_confere_a_release(self):
        self.assertIn('apk-url.txt', self.fluxo)
        self.assertIn('-PapkUrls="$APK_URLS"', self.fluxo)
        self.assertIn("'gh', 'release', 'view'", self.fluxo)

    def test_avisa_quando_o_link_exige_login(self):
        # o CI checa o link SEM token: anexo de repo privado da 404
        self.assertIn('sem login: repositorio privado', self.fluxo)
        self.assertIn("'404', '403', '401'", self.fluxo)

    def test_confere_a_logica_do_instalador_antes_de_compilar(self):
        self.assertIn('4b. Conferir a logica do instalador', self.fluxo)
        for marca in ('BoasVindasActivity', 'FileProvider.getUriForFile',
                      'canRequestPackageInstalls', 'org.xbmc.kodi'):
            self.assertIn(marca, self.fluxo)

    def test_confere_o_apk_final_e_o_limite_de_10mb(self):
        self.assertIn('REQUEST_INSTALL_PACKAGES', self.fluxo)
        self.assertIn('passou de 10 MB', self.fluxo)
        self.assertIn("contem(dex, url_apk)", self.fluxo)

    def test_ordem_de_instalacao_nas_notas(self):
        self.assertIn('e o primeiro app', self.fluxo)


if __name__ == '__main__':
    unittest.main()
