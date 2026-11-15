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
import sys

VERIFICADOR = Path(__file__).resolve().parents[1] / "smartedtv/tools/verify-monolito-apk.py"

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
        self.assertIn('VERSAO_NOME = "1.0.72"', self.script)
        self.assertIn('VERSAO_CODIGO = 2103058', self.script)
        # tem que ser maior que a 1.0.63 (2103049) para nao regredir instalacao
        self.assertGreater(2103058, 2103053)

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
        # a verificação virou um script próprio (relatório completo), chamado
        # pelo passo 10 com o pacote/versão vindos do env
        self.assertIn('smartedtv/tools/verify-monolito-apk.py', self.fluxo)
        self.assertIn('--pacote "$PACOTE" --versao "$VERSAO" --codigo "$CODIGO"',
                      self.fluxo)
        self.assertIn('--relatorio', self.fluxo)
        # o relatório da verificação fica no repositório (log do runner não basta)
        self.assertIn('docs/verificacao-apk.txt', self.fluxo)
        # o APK sobe como artifact: dá para reconferir sem recompilar
        self.assertIn('actions/upload-artifact@v4', self.fluxo)
        self.assertIn('apk-unificado-${{ env.VERSAO }}', self.fluxo)
        # e a verificação continua bloqueante
        self.assertNotIn('continue-on-error', self.fluxo.split('10. Conferir o monolito')[1])
        self.assertIn('exit $RC', self.fluxo)

    def test_verificador_nao_morre_no_primeiro_erro(self):
        codigo = (Path('smartedtv/tools/verify-monolito-apk.py')).read_text(encoding='utf-8')
        # todas as checagens rodam; só o fim decide o código de saída
        self.assertIn('self.erros', codigo)
        self.assertIn('return 1 if rel.erros else 0', codigo)
        # APPLICATION_ID existe só no manifesto: não pode ser obrigatório no dex
        self.assertNotIn('rel.exige(ADS_APP_ID.encode() in dex', codigo)

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


class VerificadorDoApkTest(unittest.TestCase):
    """O verificador do APK precisa rodar TODAS as checagens e dizer tudo.

    Regressão real: a primeira versão parava no primeiro erro e exigia o
    APPLICATION_ID dentro do dex (ele só existe no manifesto), derrubando dois
    builds de 2 h já com o APK pronto.
    """

    def _apk(self, tmp, com_tudo=True):
        import zipfile
        apk = Path(tmp) / "fake.apk"
        addons = ["skin.novatv", "skin.smartedtv.classic", "plugin.video.smarted",
                  "service.smarted.bootstrap", "resource.uisounds.silencio"]
        with zipfile.ZipFile(apk, "w") as z:
            for addon in addons + ["script.smartedtv.ajustes"]:
                z.writestr(f"assets/addons/{addon}/addon.xml", "<addon/>")
            z.writestr("assets/addons/skin.novatv/xml/Home.xml",
                       "<control><label>Ajustes</label>"
                       "<onclick>RunAddon(script.smartedtv.ajustes)</onclick></control>")
            # a skin precisa vir completa (>=800 arquivos, media/ com as imagens)
            for i in range(900):
                z.writestr(f"assets/addons/skin.novatv/media/img{i}.png", b"p")
            z.writestr("assets/addons/skin.novatv/media/DefaultAddon.png", b"p")
            for nome in ("catalogue.py", "navigation.py", "search.py"):
                z.writestr(f"assets/addons/plugin.video.smarted/{nome}", b"#")
            for i in range(12):
                z.writestr(f"assets/addons/plugin.video.smarted/mod{i}.py", b"#")
            z.writestr("assets/system/addon-manifest.xml",
                       "<addons><addon>skin.novatv</addon>"
                       "<addon>script.smartedtv.ajustes</addon></addons>")
            z.writestr("assets/media/splash.jpg", b"x")
            z.writestr("assets/media/applaunch_screen.png", b"x")
            z.writestr("res/AB.png", b"x")
            z.writestr("lib/arm64-v8a/libkodi.so", b"\x7fELF")
            z.writestr("classes.dex", (b"ca-app-pub-2066014755407744/4214378379 "
                                       b"ca-app-pub-2066014755407744/3572039686 "
                                       b"AppOpenActivity PreRollActivity SmartAds "
                                       b"perfilSmarted .kodi.antigo- smarted-seed.log "
                       b"Licenca adsPermitidos AbrirUrlActivity CompartilharActivity "
                       b"BoasVindas iniciarKodi "
                                       b"com/google/android/gms/ads"))
            z.writestr("assets/addons/script.smartedtv.ajustes/vipmenu.py",
                       "BASE = 'plugin://script.smartedtv.ajustes/'\n")
            z.writestr("assets/addons/script.smartedtv.ajustes/addon.xml",
                       '<addon id="script.smartedtv.ajustes"><extension '
                       'point="xbmc.python.pluginsource" library="vipmenu.py"/></addon>')
            z.writestr("assets/addons/script.smartedtv.ajustes/resources/qrcode.png",
                       b"\x89PNG\r\n\x1a\n" + b"0" * 2000)
            z.writestr("assets/addons/service.smarted.bootstrap/retomar.py",
                       "def encerrar():\n    pass\n")
            z.writestr("assets/addons/service.smarted.bootstrap/skin_setup.py",
                       "def ensure_shortcuts(log=None):\n    return []\n"
                       "URL = 'plugin://script.smartedtv.ajustes/'\n")
            z.writestr("assets/addons/service.smarted.bootstrap/vip.py",
                       "VALIDAR_URIS = ('https://smartedtv-vip.lovable.app/api/validar',)\n")
            z.writestr("assets/addons/plugin.video.smarted/default.py",
                       "# rota vip\nif route == 'vip':\n    pass\n"
                       "MENU = 'plugin://script.smartedtv.ajustes/'\n")
            z.writestr("assets/addons/service.smarted.bootstrap/smart_ads.py",
                       "ATIVIDADE_PREROLL = 'smartedtv.full.PreRollActivity'\n"
                       "ATIVIDADE_ABERTURA = 'smartedtv.full.AppOpenActivity'\n"
                       "tentar_plano_b=False\n")
            registro = b"a" * 64 + b"\t10\tuserdata/guisettings.xml\n"
            z.writestr("assets/smarted/profile-manifest.txt", registro)
            z.writestr("assets/smarted/profile/userdata/guisettings.xml",
                       '<settings><setting id="lookandfeel.skin" default="true">skin.estuary</setting></settings>')
            z.writestr("assets/smarted/profile/userdata/sources.xml", "<sources/>")
            for i in range(60):
                z.writestr("assets/smarted/profile/addons/x%d.xml" % i, b"y")
            z.writestr("assets/smarted/profile/addons/plugin.video.BrazucaPlay.Matrix/addon.xml",
                       b"<addon/>")
        return apk

    def _aapt2(self, tmp):
        caminho = Path(tmp) / "aapt2"
        caminho.write_text("""#!/bin/sh
if [ "$2" = badging ]; then
  echo "package: name='smartedtv.full' versionCode='2103058' versionName='1.0.72'"
elif [ "$2" = resources ]; then
  echo "drawable/progresswhite type=drawable"
elif [ "$2" = xmltree ] && [ "$4" = "res/layout/activity_splash.xml" ]; then
  echo '    A: android:id(0x010100d0)=@0x7f080054'
  echo '    A: android:progressDrawable(0x0101012c)=@0x7f070001'
  echo '    A: android:visibility(0x010100dc)=2'
else
  echo '    A: android:name(0x01010003)=".AppOpenActivity"'
  echo '    A: android:name(0x01010003)=".PreRollActivity"'
  echo '    A: android:screenOrientation(0x0101001e)=0x6'
  echo '    A: android:value(0x01010024)="ca-app-pub-2066014755407744~5076693043"'
  echo '    A: android:name(0x01010003)="com.google.android.gms.permission.AD_ID"'
  echo '    A: android:name(0x01010003)="android.hardware.touchscreen"'
  echo '    A: android:name(0x01010003)="android.software.leanback"'
  echo '    A: android:name(0x01010003)="android.intent.category.LEANBACK_LAUNCHER"'
fi
""", encoding="utf-8")
        caminho.chmod(0o755)
        return caminho

    def test_apk_completo_passa(self):
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            apk = self._apk(tmp)
            aapt2 = self._aapt2(tmp)
            import hashlib, zipfile
            with zipfile.ZipFile(apk) as z:
                sha = hashlib.sha256(z.read("assets/smarted/profile-manifest.txt")).hexdigest()
            proc = subprocess.run(
                [sys.executable, str(VERIFICADOR), str(apk), "--aapt2", str(aapt2),
                 "--manifesto-base-sha", sha],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("obrigatórias com falha: 0", proc.stdout)
            # APPLICATION_ID no dex é aviso, não erro (ele vive no manifesto)
            self.assertIn("aviso APPLICATION_ID no dex", proc.stdout)

    def test_apk_sem_a_skin_falha_e_mostra_o_resto(self):
        import subprocess, tempfile, zipfile
        with tempfile.TemporaryDirectory() as tmp:
            apk = self._apk(tmp)
            # reescreve o zip sem a skin
            origem = zipfile.ZipFile(apk)
            itens = {n: origem.read(n) for n in origem.namelist()
                     if not n.startswith("assets/addons/skin.novatv/")}
            origem.close()
            with zipfile.ZipFile(apk, "w") as z:
                for nome, dados in itens.items():
                    z.writestr(nome, dados)
            aapt2 = self._aapt2(tmp)
            import hashlib, zipfile
            with zipfile.ZipFile(apk) as z:
                sha = hashlib.sha256(z.read("assets/smarted/profile-manifest.txt")).hexdigest()
            proc = subprocess.run(
                [sys.executable, str(VERIFICADOR), str(apk), "--aapt2", str(aapt2),
                 "--manifesto-base-sha", sha],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("FALHA addon skin.novatv", proc.stdout)
            # não parou no primeiro erro: avaliou o dex também
            self.assertIn("classe SmartAds", proc.stdout)


class RestauracaoDaBaseEstavelTest(unittest.TestCase):
    """A base da linha estavel (perfil semeado) volta para dentro do APK.

    Regressão real da 1.0.65: o monólito abria com perfil limpo, então o
    catálogo perdia as categorias (Doramas, Animes, Novelas, Desenhos) porque
    `plugin.video.smarted` só delega para o `plugin.video.BrazucaPlay.Matrix`,
    que vivia no perfil semeado.
    """

    def setUp(self):
        self.script = Path('smartedtv/tools/integrate-monolith.py').read_text(encoding='utf-8')
        self.fluxo = Path('.github/workflows/build-monolith.yml').read_text(encoding='utf-8')
        self.injecao = Path('smartedtv/tools/inject-base-estavel.py').read_text(encoding='utf-8')
        self.seeder = Path('smartedtv/tools/ads-java/SeedBase.java.in').read_text(encoding='utf-8')

    def test_seeder_entra_no_apk_e_no_install_cmake(self):
        self.assertIn('"SeedBase"', self.script)
        self.assertIn('SeedBase.pronto(this)', Path(
            'smartedtv/tools/integrate-monolith.py').read_text(encoding='utf-8'))

    def test_seeder_so_age_sem_perfil_e_confere_hash(self):
        # um perfil que JÁ é da base nunca é mexido (Brazuca + guisettings)
        self.assertIn('perfilSmarted(kodi)', self.seeder)
        self.assertIn('plugin.video.BrazucaPlay.Matrix/addon.xml', self.seeder)
        # um .kodi que não é da base (Kodi recém-instalado / build antigo do app)
        # é guardado, não apagado, e a base entra no lugar
        self.assertIn('.kodi.antigo-" + System.currentTimeMillis()', self.seeder)
        self.assertIn('jaTentei', self.seeder)          # sem laço de splash
        self.assertIn('smarted-seed.log', self.seeder)  # rastro para diagnóstico
        # manifesto fixo da base estavel, igual ao launcher antigo
        self.assertIn('1447de816a44ecc11c42c2c315cf20e61c9baa037e914a13293711cf152d1ede',
                      self.seeder)
        # staging + rename atomico (nunca escreve direto em .kodi)
        self.assertIn('.smarted-seed-', self.seeder)
        self.assertIn('renameTo(alvo)', self.seeder)
        # a skin da base (Estuary) vira skin.novatv
        self.assertIn('skin.novatv', self.seeder)
        # nada de texto na tela (pedido do usuario)
        self.assertNotIn('setText(', self.seeder)

    def test_injecao_recusa_base_errada(self):
        self.assertIn('assets/smarted/profile-manifest.txt', self.injecao)
        self.assertIn('MANIFESTO', self.injecao)
        self.assertIn('não vou duplicar', self.injecao)     # já existe = erro
        self.assertIn('.SF', self.injecao)                  # assinatura antiga sai
        self.assertIn('zipalign', self.fluxo)               # realinhar depois
        self.assertIn('apksigner" sign', self.fluxo)        # reassinar depois

    def test_fluxo_baixa_a_base_e_confere_o_manifesto(self):
        # a base é o APK de referência do dono do app (Dropbox), não uma cópia nossa
        self.assertIn('BASE_URL: "https://www.dropbox.com/scl/fi/', self.fluxo)
        self.assertIn('SMARTEDTV.apk', self.fluxo)
        self.assertIn('assets/smarted/profile-manifest.txt', self.fluxo)
        self.assertIn('--manifesto-base-sha', self.fluxo)
        self.assertIn('inject-base-estavel.py', self.fluxo)

    def test_splash_branco_sem_texto_e_sem_corte(self):
        layout_ok = 'progresswhite' in self.script and 'centerInside' in self.script
        self.assertTrue(layout_ok)
        self.assertIn('android:visibility="gone"', self.script)
        self.assertIn('mSplash.mProgress.setVisibility(View.INVISIBLE)', self.script)
        # o patch remove as chamadas que escondem a barra
        self.assertIn('chamadas que escondiam a barra', self.script)


class InjecaoDaBaseTest(unittest.TestCase):
    """A injeção troca skin/plugin pelos do APK estável, mas NUNCA o smart_ads.

    Regressão da 1.0.67: as entradas substituídas eram marcadas como
    "existentes" e o injetor abortava com "colisão de entrada" nos 222 nomes
    que a skin já tinha no APK novo.
    """

    def test_skin_e_plugin_do_estavel_e_admob_preservado(self):
        import hashlib
        import subprocess
        import sys
        import tempfile
        import zipfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            base = tmp / "base.apk"
            novo = tmp / "novo.apk"
            saida = tmp / "saida.apk"
            manifesto = b"perfil-de-teste\n"
            sha = hashlib.sha256(manifesto).hexdigest()

            with zipfile.ZipFile(base, "w") as z:
                z.writestr("assets/smarted/profile-manifest.txt", manifesto)
                z.writestr("assets/smarted/profile/userdata/guisettings.xml", b"<s/>")
                z.writestr("assets/addons/skin.novatv/addon.xml", b"skin-estavel")
                z.writestr("assets/addons/skin.novatv/media/a.png", b"img-estavel")
                z.writestr("assets/addons/plugin.video.smarted/catalogue.py", b"cat-estavel")
                z.writestr("assets/addons/service.smarted.bootstrap/smart_ads.py", b"ads-estavel")

            with zipfile.ZipFile(novo, "w") as z:
                z.writestr("assets/addons/skin.novatv/addon.xml", b"skin-nosso")
                z.writestr("assets/addons/plugin.video.smarted/catalogue.py", b"cat-nosso")
                z.writestr("assets/addons/service.smarted.bootstrap/smart_ads.py", b"ads-nosso")
                z.writestr("classes.dex", b"dex")
                z.writestr("META-INF/CERT.SF", b"assinatura-antiga")

            proc = subprocess.run(
                [sys.executable, "smartedtv/tools/inject-base-estavel.py",
                 "--apk", str(novo), "--base", str(base),
                 "--saida", str(saida), "--manifesto-sha", sha],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

            with zipfile.ZipFile(saida) as z:
                nomes = set(z.namelist())
                self.assertEqual(z.read("assets/addons/skin.novatv/addon.xml"), b"skin-estavel")
                self.assertEqual(z.read("assets/addons/skin.novatv/media/a.png"), b"img-estavel")
                self.assertEqual(z.read("assets/addons/plugin.video.smarted/catalogue.py"),
                                 b"cat-estavel")
                self.assertEqual(
                    z.read("assets/addons/service.smarted.bootstrap/smart_ads.py"),
                    b"ads-nosso")           # AdMob é nosso, não da base
                self.assertIn("classes.dex", nomes)
                self.assertNotIn("META-INF/CERT.SF", nomes)
                self.assertIn("assets/smarted/profile/userdata/guisettings.xml", nomes)
            self.assertNotIn("colisão", proc.stdout or "")   # o bug da 1.0.67


class ProducaoTest(unittest.TestCase):
    """Regras de produção: anúncio real, D-pad bloqueado, VIP pela Cakto."""

    def setUp(self):
        self.ads = Path('smartedtv/tools/ads-java')
        self.texto = {p.stem.replace('.java', ''): p.read_text(encoding='utf-8')
                      for p in self.ads.glob('*.java.in')}

    def test_modo_de_teste_desligado_no_build(self):
        smart = self.texto['SmartAds']
        self.assertIn('private static boolean teste = false;', smart)
        # os blocos de teste do Google continuam existindo, mas só por intent
        self.assertIn('UNIT_APP_OPEN_TESTE', smart)
        self.assertIn('smartedtv://ads?teste=0', smart)

    def test_licenca_vip_desliga_os_anuncios(self):
        tela = self.texto['AdTela']
        self.assertIn('SmartAds.adsPermitidos(this)', tela)
        self.assertIn('Licenca.ativa(', self.texto['SmartAds'])
        licenca = self.texto['Licenca']
        self.assertIn('vip.json', licenca)
        self.assertIn('service.smarted.bootstrap', licenca)
        self.assertIn('"ativo"', licenca)       # falha segura: sem arquivo = sem VIP

    def test_dpad_nao_alcanca_o_anuncio(self):
        tela = self.texto['AdTela']
        for tecla in ('KEYCODE_DPAD_UP', 'KEYCODE_DPAD_DOWN', 'KEYCODE_DPAD_CENTER',
                      'KEYCODE_ENTER', 'KEYCODE_BUTTON_A'):
            self.assertIn(tecla, tela)
        self.assertIn('FOCUS_BLOCK_DESCENDANTS', tela)
        self.assertIn('setFocusable(false)', tela)
        self.assertIn('LIMITE_COM_ANUNCIO', tela)   # TV não fica presa
        # as duas telas de anúncio aplicam o bloqueio quando o anúncio aparece
        for nome in ('AppOpenActivity', 'PreRollActivity'):
            self.assertIn('anuncioNaTela()', self.texto[nome])

    def test_compartilhar_e_abrir_link(self):
        self.assertIn('ACTION_SEND', self.texto['CompartilharActivity'])
        self.assertIn('ACTION_VIEW', self.texto['AbrirUrlActivity'])

    def test_monolito_embarca_as_telas_novas_e_o_menu(self):
        script = Path('smartedtv/tools/integrate-monolith.py').read_text(encoding='utf-8')
        for classe in ('Licenca', 'CompartilharActivity', 'AbrirUrlActivity'):
            self.assertIn(f'"{classe}"', script)
        self.assertIn('script.smartedtv.ajustes', script)
        self.assertIn('LEANBACK_LAUNCHER', script)
        self.assertIn('android.hardware.touchscreen', script)

    def test_menu_de_ajustes_do_app(self):
        addon = Path('kodi/addons/script.smartedtv.ajustes/default.py').read_text(encoding='utf-8')
        self.assertIn('Deseja assistir sem anúncios?', addon)
        self.assertIn('Já tenho um código de ativação', addon)
        self.assertIn('Compartilhar aplicativo', addon)
        self.assertIn('Configurações do Kodi', addon)

    def test_vip_aponta_para_cakto_e_site(self):
        vip = Path('kodi/addons/service.smarted.bootstrap/vip.py').read_text(encoding='utf-8')
        self.assertIn("CHECKOUT = 'https://pay.cakto.com.br/nkvbegd_1323120'", vip)
        self.assertIn("SITE = 'https://smartedtv-vip.lovable.app/'", vip)
        self.assertIn('smartedtv.full.AbrirUrlActivity', vip)
        self.assertIn('smartedtv.full.CompartilharActivity', vip)

    def test_brazuca_dependencias_ausentes_viram_opcionais(self):
        repair = Path('kodi/addons/service.smarted.bootstrap/repair.py').read_text(encoding='utf-8')
        self.assertIn('def desbloquear_dependencias', repair)
        self.assertIn('inputstream.ffmpegdirect', repair)
        self.assertIn('script.module.inputstreamhelper', repair)
        self.assertIn("optional=\"true\"", repair)
        self.assertIn('def habilitar', repair)

    def test_home_patch_do_botao_ajustes(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "inj", Path('smartedtv/tools/inject-base-estavel.py'))
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        exemplo = (b'<control type="button" id="9112"><width>320</width>'
                   b'<label>Ajustes</label><onclick>ActivateWindow(Settings)</onclick></control>')
        novo, quantos = modulo.AJUSTES.subn(modulo.AJUSTES_NOVO, exemplo)
        self.assertEqual(quantos, 1)
        self.assertIn(b"RunAddon(script.smartedtv.ajustes)", novo)
        self.assertNotIn(b"ActivateWindow(Settings)", novo)


class BoasVindasTest(unittest.TestCase):
    """Tela de ativacao a cada abertura, intersticial por troca, QR e saida limpa."""

    def setUp(self):
        self.ads = Path('smartedtv/tools/ads-java')
        self.texto = {p.stem.replace('.java', ''): p.read_text(encoding='utf-8')
                      for p in self.ads.glob('*.java.in')}

    def test_tela_antes_do_anuncio_de_abertura(self):
        tela = self.texto['BoasVindas']
        self.assertIn('Deseja assistir sem anúncios?', tela)
        self.assertIn('pay.cakto.com.br/nkvbegd_1323120', tela)
        self.assertIn('Já tenho um código', tela)
        self.assertIn('Digite o código aqui', tela)      # campo sempre visivel
        self.assertIn('Compartilhar aplicativo', tela)
        self.assertIn('Licenca.validar(', tela)          # valida no servidor
        # a splash so abre o Kodi depois que essa tela fecha
        self.assertIn('BoasVindas.mostrar(activity)', self.texto['SeedBase'])
        self.assertIn('BoasVindas.mostrar(alvo)', self.texto['SeedBase'])
        self.assertIn('public static void iniciarKodi', self.texto['SeedBase'])

    def test_tela_aparece_em_toda_abertura(self):
        tela = self.texto['BoasVindas']
        # a regra "uma vez por versao" saiu: sem flag persistida, sem arquivo
        for proibido in ('jaMostrou', 'welcome.json', 'marcar(', 'getSharedPreferences'):
            self.assertNotIn(proibido, tela)
        self.assertIn('private static volatile boolean aberta', tela)

    def test_codigo_com_um_clique_e_layout_responsivo(self):
        tela = self.texto['BoasVindas']
        self.assertIn('setOnFocusChangeListener', tela)
        self.assertIn('showSoftInput', tela)              # 1a acao abre o teclado
        self.assertIn('requestFocus();', tela)
        self.assertIn('Configuration.ORIENTATION_LANDSCAPE', tela)
        self.assertIn('LinearLayout.HORIZONTAL', tela)    # 2 colunas deitado
        self.assertIn('LinearLayout.VERTICAL', tela)      # 1 coluna em pe
        self.assertIn('ScrollView', tela)                 # cabe em TV e celular

    def test_qr_de_compartilhamento_no_app(self):
        import struct
        tela = self.texto['BoasVindas']
        self.assertIn('script.smartedtv.ajustes/resources/qrcode.png', tela)
        self.assertIn('BitmapFactory.decodeStream', tela)
        self.assertIn('getAssets().open(QR)', tela)
        qr = Path('kodi/addons/script.smartedtv.ajustes/resources/qrcode.png')
        self.assertTrue(qr.is_file())
        dados = qr.read_bytes()
        self.assertGreater(len(dados), 1000)
        self.assertEqual(dados[:8], b'\x89PNG\r\n\x1a\n')
        largura, altura = struct.unpack('>II', dados[16:24])   # IHDR
        self.assertEqual((largura, altura), (512, 512))

    def test_atalhos_vip_e_compartilhar(self):
        skin = Path('kodi/addons/service.smarted.bootstrap/skin_setup.py').read_text(encoding='utf-8')
        self.assertIn('def ensure_shortcuts', skin)
        self.assertIn("(9, 'VIP'", skin)
        self.assertIn("(10, 'Compartilhar'", skin)
        self.assertIn('Skin.SetString(smarted_nav_%d,%s)', skin)
        servico = Path('kodi/addons/service.smarted.bootstrap/service.py').read_text(encoding='utf-8')
        self.assertIn('ensure_shortcuts(log=log)', servico)
        # a barra usa 1..8 (navigation.SLOTS) e limpa o resto: 9/10 sao nossos
        nav = Path('kodi/addons/plugin.video.smarted/navigation.py').read_text(encoding='utf-8')
        self.assertIn('SLOTS = 8', nav)
        # o menu mora no add-on de ajustes: a pasta do plugin.video.smarted do
        # APK é substituída pela do APK estável (inject-base-estavel.py)
        self.assertIn('plugin://script.smartedtv.ajustes/', skin)
        vipmenu = Path('kodi/addons/script.smartedtv.ajustes/vipmenu.py').read_text(encoding='utf-8')
        for acao in ("'comprar'", "'codigo'", "'compartilhar'", "'qrcode'", "'continuar'"):
            self.assertIn(acao, vipmenu)
        self.assertIn('xbmcplugin.addDirectoryItem', vipmenu)
        self.assertIn('ShowPicture(', vipmenu)
        addon = Path('kodi/addons/script.smartedtv.ajustes/addon.xml').read_text(encoding='utf-8')
        self.assertIn('xbmc.python.pluginsource', addon)
        self.assertIn('library="vipmenu.py"', addon)
        plugin = Path('kodi/addons/plugin.video.smarted/default.py').read_text(encoding='utf-8')
        self.assertIn("route == 'vip'", plugin)          # redireciona para o menu
        self.assertIn('plugin://script.smartedtv.ajustes/', plugin)

    def test_qr_no_menu_de_ajustes(self):
        ajustes = Path('kodi/addons/script.smartedtv.ajustes/default.py').read_text(encoding='utf-8')
        self.assertIn('def _mostrar_qr', ajustes)
        self.assertIn('Mostrar QR Code', ajustes)
        self.assertIn('ShowPicture(', ajustes)

    def test_ativacao_por_codigo_tenta_as_rotas_do_site(self):
        licenca = self.texto['Licenca']
        self.assertIn('VALIDAR_URIS', licenca)
        self.assertIn('/api/validar', licenca)
        self.assertIn('vip-endpoint.txt', licenca)        # override sem recompilar
        self.assertIn('startsWith("{")', licenca)          # HTML da SPA nao vale
        vip = Path('kodi/addons/service.smarted.bootstrap/vip.py').read_text(encoding='utf-8')
        self.assertIn('VALIDAR_URIS', vip)
        self.assertIn('def rotas()', vip)
        self.assertIn('/api/validar', vip)

    def test_ponto_de_retomada_e_saida_limpa(self):
        retomar = Path('kodi/addons/service.smarted.bootstrap/retomar.py').read_text(encoding='utf-8')
        self.assertIn('Player.GetItem', retomar)
        self.assertIn('Player.GetProperties', retomar)
        self.assertIn("'command': 'stop'", retomar)
        self.assertIn('def encerrar', retomar)
        self.assertIn('StartOffset', retomar)
        self.assertIn('class MonitorRetomar', retomar)
        self.assertIn('def onAbortRequested', retomar)
        servico = Path('kodi/addons/service.smarted.bootstrap/service.py').read_text(encoding='utf-8')
        self.assertIn('retomar.iniciar(log)', servico)
        # o fechamento ficou a cargo do Kodi: nada de finish/kill em onStop
        tela = self.texto['AdTela']
        self.assertIn('public void onBackPressed()', tela)
        self.assertNotIn('public void onUserLeaveHint', tela)
        self.assertNotIn('protected void onStop', tela)
        self.assertIn('activity.isFinishing()', self.texto['SeedBase'])
        self.assertIn('activity.isDestroyed()', self.texto['SeedBase'])
        self.assertNotIn('killProcess', self.texto['SeedBase'])

