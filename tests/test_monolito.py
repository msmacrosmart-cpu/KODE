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
        self.assertIn('VERSAO_NOME = "1.0.68"', self.script)
        self.assertIn('VERSAO_CODIGO = 2103054', self.script)
        # tem que ser maior que a 1.0.63 (2103049) para nao regredir instalacao
        self.assertGreater(2103054, 2103053)

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
            for addon in addons:
                z.writestr(f"assets/addons/{addon}/addon.xml", "<addon/>")
            # a skin precisa vir completa (>=800 arquivos, media/ com as imagens)
            for i in range(900):
                z.writestr(f"assets/addons/skin.novatv/media/img{i}.png", b"p")
            z.writestr("assets/addons/skin.novatv/media/DefaultAddon.png", b"p")
            for nome in ("catalogue.py", "default.py", "navigation.py", "search.py"):
                z.writestr(f"assets/addons/plugin.video.smarted/{nome}", b"#")
            for i in range(12):
                z.writestr(f"assets/addons/plugin.video.smarted/mod{i}.py", b"#")
            z.writestr("assets/system/addon-manifest.xml",
                       "<addons><addon>skin.novatv</addon></addons>")
            z.writestr("assets/media/splash.jpg", b"x")
            z.writestr("assets/media/applaunch_screen.png", b"x")
            z.writestr("res/AB.png", b"x")
            z.writestr("lib/arm64-v8a/libkodi.so", b"\x7fELF")
            z.writestr("classes.dex", (b"ca-app-pub-2066014755407744/4214378379 "
                                       b"ca-app-pub-2066014755407744/3572039686 "
                                       b"AppOpenActivity PreRollActivity SmartAds "
                                       b"perfilSmarted .kodi.antigo- smarted-seed.log "
                                       b"com/google/android/gms/ads"))
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
  echo "package: name='smartedtv.full' versionCode='2103054' versionName='1.0.68'"
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
