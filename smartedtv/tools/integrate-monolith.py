#!/usr/bin/env python3
"""APK UNICO: integra o AdMob e o conteudo da linha classica DENTRO do Kodi.

Roda no codigo-fonte do Kodi 21.3-Omega (clonado pelo workflow) e transforma o
build em um monolito:

    applicationId  smartedtv.full      (era org.xbmc.kodi)
    versao         1.0.70 / 2103056
    anuncios       AppOpenActivity + PreRollActivity dentro do app (AdMob nativo)
    conteudo       skin.novatv + plugin.video.smarted + service.smarted.bootstrap
                   + resource.uisounds.silencio (o mesmo pacote da linha classica)

Nada de app auxiliar: as telas de anuncio sao atividades do proprio APK, abertas
pelo builtin StartAndroidActivity com o className interno. O Python do bootstrap
fala com o mesmo processo.

O script falha de forma explicita quando o upstream muda de formato (nada de
patch "no escuro").

Uso:
    python3 integrate-monolith.py /caminho/kodi-src [--repo .] [--brand-dir ...]
                                  [--language-addon ...]
"""
from __future__ import annotations

import argparse
import bisect
import importlib.util
import re
import shutil
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

APP_PACKAGE = "smartedtv.full"
VERSAO_NOME = "1.0.70"
VERSAO_CODIGO = 2103056

ADS_APP_ID = "ca-app-pub-2066014755407744~5076693043"
PLAY_SERVICES_ADS = "com.google.android.gms:play-services-ads:23.2.0"

JAVA_ADS = ["SmartAds", "AdTela", "AppOpenActivity", "PreRollActivity", "SeedBase",
            "Licenca", "CompartilharActivity", "AbrirUrlActivity", "BoasVindas"]

SKIN_ORIGEM = "kodi/skin.estilo.personalizado"
SKIN_ID = "skin.novatv"
SKIN_ID_ORIGEM = "skin.estilo.personalizado"
SKIN_NOME = "SMARTED"
SKIN_VERSAO = "2.2.3"
SKIN_CLASSICA_ID = "skin.smartedtv.classic"
SKIN_CLASSICA_NOME = "SMARTED Classica"
SKIN_CLASSICA_VERSAO = "1.0.18"

ADDONS = ["plugin.video.smarted", "service.smarted.bootstrap", "resource.uisounds.silencio",
          "script.smartedtv.ajustes"]

ATIVIDADES = [
    ("AppOpenActivity", "abertura"),
    ("PreRollActivity", "video"),
]

# Telas de apoio (não são anúncio): abrir link externo e compartilhar o app.
# Precisam existir no mesmo APK porque o Kodi chama as duas pelo builtin
# StartAndroidActivity, que só aceita classes do próprio pacote aqui.
ATIVIDADES_APOIO = [
    ("AbrirUrlActivity", "abrir link (checkout/site)"),
    ("CompartilharActivity", "compartilhar aplicativo"),
]


class ErroDePatch(RuntimeError):
    pass


_PATCH_SOURCE = None


def patch_source():
    """Carrega smartedtv/tools/patch-source.py (o nome tem hifen: nao e importavel)."""
    global _PATCH_SOURCE
    if _PATCH_SOURCE is None:
        caminho = Path(__file__).resolve().parent / "patch-source.py"
        if not caminho.is_file():
            raise ErroDePatch(f"patch-source.py ausente em {caminho}")
        spec = importlib.util.spec_from_file_location("patch_source_mod", caminho)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        _PATCH_SOURCE = modulo
    return _PATCH_SOURCE


def ler(caminho: Path) -> str:
    if not caminho.is_file():
        raise ErroDePatch(f"arquivo ausente: {caminho}")
    return caminho.read_text(encoding="utf-8")


def escrever(caminho: Path, texto: str) -> None:
    caminho.write_text(texto, encoding="utf-8")


def trocar(caminho: Path, antigo: str, novo: str, descricao: str) -> None:
    texto = ler(caminho)
    if novo in texto:
        print(f"  --  {descricao}: ja aplicado")
        return
    ocorrencias = texto.count(antigo)
    if ocorrencias != 1:
        raise ErroDePatch(
            f"{descricao}: esperava 1 ocorrencia de {antigo!r} em {caminho.name}, "
            f"achei {ocorrencias} (o upstream mudou)"
        )
    escrever(caminho, texto.replace(antigo, novo, 1))
    print(f"  ok  {descricao}")


# ---------------------------------------------------------------------------
# 1. Identidade e applicationId
# ---------------------------------------------------------------------------
def patch_version_txt(src: Path) -> None:
    caminho = src / "version.txt"
    texto = ler(caminho)

    pacote = re.search(r"^APP_PACKAGE (\S+)$", texto, re.MULTILINE)
    nome = re.search(r"^APP_NAME (\S+)$", texto, re.MULTILINE)
    if not pacote or not nome:
        raise ErroDePatch("version.txt sem APP_NAME/APP_PACKAGE")
    if nome.group(1) != "Kodi":
        raise ErroDePatch(
            f"APP_NAME inesperado: {nome.group(1)!r}. APP_NAME precisa continuar 'Kodi' "
            "para libkodi.so e o perfil .kodi funcionarem"
        )
    if pacote.group(1) not in ("org.xbmc.kodi", APP_PACKAGE):
        raise ErroDePatch(f"APP_PACKAGE inesperado: {pacote.group(1)!r}")

    texto = re.sub(r"^APP_PACKAGE \S+$", f"APP_PACKAGE {APP_PACKAGE}", texto, count=1,
                   flags=re.MULTILINE)
    for chave, valor in (("COMPANY_NAME", "SMARTEDTV"), ("DEV_NAME", "SMARTEDTV")):
        if re.search(rf"^{chave} ", texto, re.MULTILINE):
            texto = re.sub(rf"^{chave} .*$", f"{chave} {valor}", texto, count=1,
                           flags=re.MULTILINE)
    escrever(caminho, texto)
    print(f"  ok  version.txt: APP_PACKAGE = {APP_PACKAGE} (APP_NAME segue 'Kodi')")


def patch_android_strings(src: Path) -> None:
    """Nome visivel SMARTEDTV + splash. Reaproveita o patch da linha fonte."""
    ps = patch_source()
    strings = src / "tools/android/packaging/xbmc/strings.xml.in"
    java = src / "tools/android/packaging/xbmc/src/Main.java.in"
    if strings.is_file() and "@APP_NAME@" not in strings.read_text(encoding="utf-8"):
        print("  --  strings.xml.in: nome ja aplicado")
    else:
        ps.patch_android_app_name(src)
    if java.is_file() and "SMARTEDTV" in java.read_text(encoding="utf-8"):
        print("  --  Java do Android: nome ja aplicado")
    else:
        ps.patch_android_java(src)


# ---------------------------------------------------------------------------
# 2. Gradle: versao, nome do APK e a dependencia do AdMob
# ---------------------------------------------------------------------------
def patch_build_gradle(src: Path) -> None:
    caminho = src / "tools/android/packaging/xbmc/build.gradle.in"
    trocar(caminho, "        versionCode @APP_VERSION_CODE_ANDROID@",
           f"        versionCode {VERSAO_CODIGO}",
           "build.gradle.in: versionCode do APK unico")
    trocar(caminho, '        versionName "@APP_VERSION@"',
           f'        versionName "{VERSAO_NOME}"',
           "build.gradle.in: versionName do APK unico")
    trocar(caminho,
           "dependencies {\n"
           "    // New support library to for channels/programs development.\n"
           "    implementation 'androidx.tvprovider:tvprovider:1.1.0-alpha01'\n",
           "dependencies {\n"
           "    // SmartAds: AdMob NATIVO dentro do app (o Kodi nao abre mais app externo)\n"
           f"    implementation '{PLAY_SERVICES_ADS}'\n"
           "    // New support library to for channels/programs development.\n"
           "    implementation 'androidx.tvprovider:tvprovider:1.1.0-alpha01'\n",
           "build.gradle.in: dependencia do play-services-ads")


# ---------------------------------------------------------------------------
# 3. Manifesto: permissao, APPLICATION_ID e as duas atividades de anuncio
# ---------------------------------------------------------------------------
def patch_manifest(src: Path) -> None:
    caminho = src / "tools/android/packaging/xbmc/AndroidManifest.xml.in"
    texto = ler(caminho)

    if "com.google.android.gms.permission.AD_ID" not in texto:
        trocar(caminho,
               '    <uses-permission android:name="android.permission.RECORD_AUDIO" />\n',
               '    <uses-permission android:name="android.permission.RECORD_AUDIO" />\n'
               '    <uses-permission android:name="com.google.android.gms.permission.AD_ID" />\n',
               "AndroidManifest.xml.in: permissao AD_ID")

    texto = ler(caminho)
    if ADS_APP_ID not in texto:
        marcador = '        android:requestLegacyExternalStorage="true">\n'
        bloco = (
            marcador
            + "\n        <!-- AdMob: sem esta meta-data o SDK nao sobe -->\n"
            + '        <meta-data\n'
            + '            android:name="com.google.android.gms.ads.APPLICATION_ID"\n'
            + f'            android:value="{ADS_APP_ID}" />\n'
        )
        trocar(caminho, marcador, bloco, "AndroidManifest.xml.in: APPLICATION_ID do AdMob")

    texto = ler(caminho)
    if "PreRollActivity" not in texto:
        marcador = "    </application>"
        atividades = []
        for classe, rotulo in ATIVIDADES:
            atividades.append(
                f"\n        <!-- anuncio {rotulo}: aberto pelo StartAndroidActivity da ponte -->\n"
                f'        <activity\n'
                f'            android:name=".{classe}"\n'
                '            android:configChanges="orientation|screenSize|screenLayout|'
                'keyboard|keyboardHidden|navigation|uiMode"\n'
                '            android:excludeFromRecents="true"\n'
                '            android:exported="true"\n'
                '            android:noHistory="true"\n'
                '            android:screenOrientation="sensorLandscape"\n'
                '            android:theme="@android:style/Theme.Black.NoTitleBar.Fullscreen" />\n'
            )
        trocar(caminho, marcador, "".join(atividades) + "\n" + marcador,
               "AndroidManifest.xml.in: AppOpenActivity + PreRollActivity (sensorLandscape)")

    texto = ler(caminho)
    if "AbrirUrlActivity" not in texto:
        marcador = "    </application>"
        apoio = []
        for classe, rotulo in ATIVIDADES_APOIO:
            apoio.append(
                f"\n        <!-- {rotulo}: chamada pelo add-on do Kodi -->\n"
                f'        <activity\n'
                f'            android:name=".{classe}"\n'
                '            android:configChanges="orientation|screenSize|screenLayout|'
                'keyboard|keyboardHidden|navigation|uiMode"\n'
                '            android:excludeFromRecents="true"\n'
                '            android:exported="true"\n'
                '            android:noHistory="true"\n'
                '            android:theme="@android:style/Theme.Translucent.NoTitleBar" />\n'
            )
        trocar(caminho, marcador, "".join(apoio) + "\n" + marcador,
               "AndroidManifest.xml.in: AbrirUrlActivity + CompartilharActivity")

    # TV x celular: declarar que o app nao exige toque e que tambem roda em TV.
    # Sem isto a Play Store trata o app como "exige touchscreen" e esconde de
    # Android TV / TV Box; com required=false ele aparece nos dois.
    texto = ler(caminho)
    if "android.hardware.touchscreen" not in texto:
        marcador = '    <uses-permission android:name="android.permission.INTERNET" />'
        if marcador in texto:
            bloco = (marcador + "\n\n"
                     "    <!-- TV e celular: o mesmo APK roda nos dois -->\n"
                     '    <uses-feature android:name="android.hardware.touchscreen"'
                     ' android:required="false" />\n'
                     '    <uses-feature android:name="android.software.leanback"'
                     ' android:required="false" />\n'
                     '    <uses-feature android:name="android.hardware.gamepad"'
                     ' android:required="false" />\n')
            trocar(caminho, marcador, bloco, "AndroidManifest.xml.in: touchscreen/leanback opcionais")

    texto = ler(caminho)
    if "LEANBACK_LAUNCHER" not in texto:
        marcador = '<category android:name="android.intent.category.LAUNCHER" />'
        if marcador in texto:
            trocar(caminho, marcador,
                   marcador + '\n                '
                   '<category android:name="android.intent.category.LEANBACK_LAUNCHER" />',
                   "AndroidManifest.xml.in: launcher de Android TV")
        else:
            print("  --  AndroidManifest.xml.in: sem categoria LAUNCHER para duplicar")

    # sanidade: o manifest tem que continuar valido como XML com os @VARS@ trocados
    teste = (ler(caminho)
             .replace("@APP_PACKAGE@", APP_PACKAGE)
             .replace("@APP_VERSION_CODE_ANDROID@", str(VERSAO_CODIGO))
             .replace("@APP_VERSION@", VERSAO_NOME))
    teste = re.sub(r'android:name="@string/[^"]*"', 'android:name="x"', teste)
    teste = re.sub(r"@(drawable|string|style|xml|color)/[A-Za-z0-9_.]+", "generated", teste)
    teste = teste.replace("<!-- BEGIN_INCLUDE(manifest) -->", "")
    ET.fromstring(teste)
    print("  ok  AndroidManifest.xml.in: XML valido depois das inclusoes")


# ---------------------------------------------------------------------------
# 4. Java das telas de anuncio (entram no APK unico)
# ---------------------------------------------------------------------------
def copiar_java_ads(src: Path) -> None:
    origem = Path(__file__).resolve().parent / "ads-java"
    destino = src / "tools/android/packaging/xbmc/src"
    for classe in JAVA_ADS:
        fonte = origem / f"{classe}.java.in"
        if not fonte.is_file():
            raise ErroDePatch(f"template ausente: {fonte}")
        shutil.copy2(fonte, destino / fonte.name)
        print(f"  ok  src/{fonte.name}")


def patch_install_cmake(src: Path) -> None:
    """O Install.cmake lista arquivo por arquivo: sem isto o Java nao entra."""
    caminho = src / "cmake/scripts/android/Install.cmake"
    texto = ler(caminho)
    if "src/SmartAds.java" in texto:
        print("  --  Install.cmake: Java dos anuncios ja listado")
        return
    marcador = "                  src/Splash.java\n"
    if marcador not in texto:
        raise ErroDePatch("Install.cmake sem 'src/Splash.java' na lista package_files")
    novos = "".join(f"                  src/{classe}.java\n" for classe in JAVA_ADS)
    escrever(caminho, texto.replace(marcador, marcador + novos, 1))
    print(f"  ok  Install.cmake: {len(JAVA_ADS)} arquivos Java na lista package_files")


# ---------------------------------------------------------------------------
# 4b. Splash: barra branca limpa, sem textos, logo widescreen centralizada
# ---------------------------------------------------------------------------
LAYOUT_SPLASH = """<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@android:color/black" >

    <!-- arte widescreen inteira, centralizada, sem corte -->
    <ImageView
        android:id="@+id/imageView1"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:adjustViewBounds="true"
        android:scaleType="centerInside"
        android:src="@drawable/applaunch_screen" />

    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:layout_gravity="bottom"
        android:orientation="vertical"
        android:paddingLeft="96dp"
        android:paddingRight="96dp"
        android:paddingBottom="44dp" >

        <ProgressBar
            android:id="@+id/progressBar1"
            style="?android:attr/progressBarStyleHorizontal"
            android:layout_width="match_parent"
            android:layout_height="3dp"
            android:indeterminate="true"
            android:indeterminateDrawable="@drawable/progresswhite"
            android:progressDrawable="@drawable/progresswhite" />

        <!-- o Kodi escreve aqui; fica invisivel de proposito -->
        <TextView
            android:id="@+id/textView1"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:visibility="gone" />
    </LinearLayout>

</FrameLayout>
"""

DRAWABLE_BARRA = """<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android" >

    <!-- trilho discreto -->
    <item android:id="@android:id/background">
        <shape>
            <corners android:radius="2dip" />
            <solid android:color="#33FFFFFF" />
        </shape>
    </item>

    <!-- progresso branco puro -->
    <item android:id="@android:id/progress">
        <clip>
            <shape>
                <corners android:radius="2dip" />
                <solid android:color="#FFFFFFFF" />
            </shape>
        </clip>
    </item>

</layer-list>
"""


def patch_splash(src: Path) -> None:
    """Troca a barra azul padrao por uma branca e tira o texto de status."""
    layout = src / "tools/android/packaging/xbmc/res/layout/activity_splash.xml"
    original = ler(layout)
    if "progresswhite" in original:
        print("  --  splash: barra branca ja aplicada")
    else:
        if 'android:id="@+id/progressBar1"' not in original:
            raise ErroDePatch("activity_splash.xml sem progressBar1 (upstream mudou)")
        if "progresscolor" not in original:
            raise ErroDePatch("activity_splash.xml nao usa progresscolor (upstream mudou)")
        escrever(layout, LAYOUT_SPLASH)
        print("  ok  splash: barra branca, sem texto, arte centralizada sem corte")

    drawable = src / "tools/android/packaging/xbmc/res/drawable/progresswhite.xml"
    drawable.parent.mkdir(parents=True, exist_ok=True)
    escrever(drawable, DRAWABLE_BARRA)
    print("  ok  res/drawable/progresswhite.xml (branco puro)")

    # a barra nao pode mais ser escondida pelo codigo do Kodi
    java = src / "tools/android/packaging/xbmc/src/Splash.java.in"
    texto = ler(java)
    esconder = [
        "          mSplash.mProgress.setVisibility(View.INVISIBLE);\n",
        "        mProgress.setVisibility(View.INVISIBLE);\n",
    ]
    removidos = 0
    for linha in esconder:
        while linha in texto:
            texto = texto.replace(linha, "", 1)
            removidos += 1
    escrever(java, texto)
    print(f"  ok  Splash.java: {removidos} chamadas que escondiam a barra removidas")

    # texto de status nunca aparece (fica no layout como gone; nao religamos)
    if "mTextView.setVisibility(View.VISIBLE)" in texto:
        raise ErroDePatch("Splash.java passou a mostrar o texto de status")


def patch_seed_no_splash(src: Path) -> None:
    """A base estavel (perfil semeado) entra antes do Kodi abrir."""
    java = src / "tools/android/packaging/xbmc/src/Splash.java.in"
    texto = ler(java)
    if "SeedBase.pronto" in texto:
        print("  --  Splash.java: semente da base ja chamada")
        return
    antigo = """  protected void startXBMC()
  {
    // Run @APP_NAME@
    Intent intent = getIntent();"""
    novo = """  protected void startXBMC()
  {
    // Base da linha classica: instala o perfil semeado UMA vez, antes de abrir
    // o Kodi. Enquanto copia, a splash fica na tela; no fim este metodo e
    // chamado de novo e o app abre normalmente.
    if (!@APP_PACKAGE@.SeedBase.pronto(this))
      return;

    startXBMCNow();
  }

  private void startXBMCNow()
  {
    // Run @APP_NAME@
    Intent intent = getIntent();"""
    if antigo not in texto:
        raise ErroDePatch("Splash.java: startXBMC com formato inesperado")
    escrever(java, texto.replace(antigo, novo, 1))
    print("  ok  Splash.java: base estavel instalada antes de abrir o Kodi")


# ---------------------------------------------------------------------------
# 5. Conteudo da linha classica (skin + addons) dentro do fonte
# ---------------------------------------------------------------------------
def copiar_addon(origem: Path, destino: Path) -> None:
    if not (origem / "addon.xml").is_file():
        raise ErroDePatch(f"addon sem addon.xml: {origem}")
    if destino.is_dir():
        shutil.rmtree(destino)
    shutil.copytree(origem, destino)
    print(f"  ok  addons/{destino.name}")


def instalar_skin(repo: Path, src: Path) -> None:
    origem = repo / SKIN_ORIGEM
    destino = src / "addons" / SKIN_ID
    if not (origem / "addon.xml").is_file():
        raise ErroDePatch(f"skin ausente no repositorio: {origem}")
    if destino.is_dir():
        shutil.rmtree(destino)
    shutil.copytree(origem, destino)

    addon_xml = destino / "addon.xml"
    raiz = ET.parse(addon_xml).getroot()
    if raiz.get("id") != SKIN_ID_ORIGEM:
        raise ErroDePatch(f"skin com id inesperado: {raiz.get('id')!r}")
    raiz.set("id", SKIN_ID)
    raiz.set("name", SKIN_NOME)
    raiz.set("provider-name", SKIN_NOME)
    raiz.set("version", SKIN_VERSAO)
    addon_xml.write_bytes(ET.tostring(raiz, encoding="UTF-8", xml_declaration=True))
    print(f"  ok  addons/{SKIN_ID} (skin padrao da linha classica, versao {SKIN_VERSAO})")

    # copia classica opcional, com o mesmo conteudo e outro id
    classica = src / "addons" / SKIN_CLASSICA_ID
    if classica.is_dir():
        shutil.rmtree(classica)
    shutil.copytree(destino, classica)
    raiz = ET.parse(classica / "addon.xml").getroot()
    raiz.set("id", SKIN_CLASSICA_ID)
    raiz.set("name", SKIN_CLASSICA_NOME)
    raiz.set("provider-name", SKIN_CLASSICA_NOME)
    raiz.set("version", SKIN_CLASSICA_VERSAO)
    (classica / "addon.xml").write_bytes(ET.tostring(raiz, encoding="UTF-8", xml_declaration=True))
    print(f"  ok  addons/{SKIN_CLASSICA_ID} (alternativa em Ajustes > Aparencia)")


def patch_smart_ads(src: Path) -> None:
    """A ponte passa a apontar para as classes DENTRO do proprio APK."""
    caminho = src / "addons/service.smarted.bootstrap/smart_ads.py"
    texto = ler(caminho)
    trocas = [
        (re.compile(r"^ATIVIDADE_ABERTURA = .*$", re.MULTILINE),
         f"ATIVIDADE_ABERTURA = '{APP_PACKAGE}.AppOpenActivity'"),
        (re.compile(r"^ATIVIDADE_PREROLL = .*$", re.MULTILINE),
         f"ATIVIDADE_PREROLL = '{APP_PACKAGE}.PreRollActivity'"),
        # plano B (launcher com data URI) nao existe aqui: o proprio Kodi E o
        # app, entao abrir o launcher dele reiniciaria a interface
        (re.compile(r"tentar_plano_b=True"), "tentar_plano_b=False"),
    ]
    for padrao, novo in trocas:
        if not padrao.search(texto):
            raise ErroDePatch(f"smart_ads.py: nao achei {padrao.pattern!r}")
        texto = padrao.sub(novo, texto)
    escrever(caminho, texto)
    print("  ok  smart_ads.py: classes internas (smartedtv.full.*) e sem plano B")


def registrar_addons(src: Path, ids: list[str]) -> None:
    """addons.txt (o que entra no APK) + addon-manifest.xml (o que e de sistema)."""
    caminho = src / "cmake/installdata/common/addons.txt"
    linhas = ler(caminho).splitlines()
    for addon_id in ids:
        entrada = f"addons/{addon_id}/*"
        if entrada in linhas:
            continue
        posicao = bisect.bisect_left(linhas, entrada)
        linhas.insert(posicao, entrada)
    escrever(caminho, "\n".join(linhas) + "\n")
    print(f"  ok  cmake/installdata/common/addons.txt: {len(ids)} addons entram no APK")

    manifesto = src / "system/addon-manifest.xml"
    texto = ler(manifesto)
    for addon_id in ids:
        if f"<addon>{addon_id}</addon>" in texto:
            continue
        texto = texto.replace("</addons>", f"  <addon>{addon_id}</addon>\n</addons>", 1)
    escrever(manifesto, texto)
    print("  ok  system/addon-manifest.xml: addons marcados como de sistema")


def patch_skin_padrao(src: Path) -> None:
    caminho = src / "system/settings/settings.xml"
    texto = ler(caminho)
    if f"<default>{SKIN_ID}</default>" in texto:
        print(f"  --  settings.xml: skin padrao ja e {SKIN_ID}")
        return
    bloco = re.search(
        r'(<setting id="lookandfeel\.skin".*?)<default>skin\.estuary</default>',
        texto, re.DOTALL)
    if not bloco:
        raise ErroDePatch("settings.xml: nao achei o default de lookandfeel.skin")
    texto = (texto[:bloco.start()]
             + bloco.group(1) + f"<default>{SKIN_ID}</default>"
             + texto[bloco.end():])
    escrever(caminho, texto)
    print(f"  ok  settings.xml: skin padrao = {SKIN_ID} (Estuary fica de reserva)")


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=Path, help="arvore do Kodi 21.3-Omega")
    ap.add_argument("--repo", type=Path, default=Path.cwd(), help="raiz deste repositorio")
    ap.add_argument("--brand-dir", type=Path, help="saida do make-brand-assets.py")
    ap.add_argument("--language-addon", type=Path, help="resource.language.pt_br")
    args = ap.parse_args()

    src = args.src.resolve()
    repo = args.repo.resolve()
    if not (src / "version.txt").is_file():
        raise ErroDePatch(f"{src} nao parece ser o codigo-fonte do Kodi")

    print(f"APK unico {APP_PACKAGE} {VERSAO_NOME} ({VERSAO_CODIGO})")
    patch_version_txt(src)
    patch_android_strings(src)
    patch_build_gradle(src)
    patch_manifest(src)
    copiar_java_ads(src)
    patch_install_cmake(src)
    patch_splash(src)
    patch_seed_no_splash(src)

    instalar_skin(repo, src)
    for addon in ADDONS:
        copiar_addon(repo / "kodi" / "addons" / addon, src / "addons" / addon)
    patch_smart_ads(src)
    registrar_addons(src, [SKIN_ID, SKIN_CLASSICA_ID] + ADDONS)
    patch_skin_padrao(src)

    ps = patch_source()
    if args.language_addon:
        ps.install_language(src, args.language_addon)
    if args.brand_dir:
        ps.patch_media(src, args.brand_dir)

    # conferencias finais (falham o build antes de gastar 1 hora compilando)
    version = ler(src / "version.txt")
    assert f"APP_PACKAGE {APP_PACKAGE}" in version, "applicationId nao aplicado"
    manifest = ler(src / "tools/android/packaging/xbmc/AndroidManifest.xml.in")
    assert ADS_APP_ID in manifest and "PreRollActivity" in manifest
    gradle = ler(src / "tools/android/packaging/xbmc/build.gradle.in")
    assert PLAY_SERVICES_ADS in gradle, "dependencia do AdMob ausente"
    assert str(VERSAO_CODIGO) in gradle and VERSAO_NOME in gradle
    cmake = ler(src / "cmake/scripts/android/Install.cmake")
    for classe in JAVA_ADS:
        assert f"src/{classe}.java" in cmake, f"{classe} fora do Install.cmake"
    for addon_id in [SKIN_ID, SKIN_CLASSICA_ID] + ADDONS:
        assert (src / "addons" / addon_id / "addon.xml").is_file(), f"addon {addon_id}"
        assert f"addons/{addon_id}/*" in ler(src / "cmake/installdata/common/addons.txt")
    ads = ler(src / "addons/service.smarted.bootstrap/smart_ads.py")
    assert f"ATIVIDADE_PREROLL = '{APP_PACKAGE}.PreRollActivity'" in ads
    splash = ler(src / "tools/android/packaging/xbmc/res/layout/activity_splash.xml")
    assert "progresswhite" in splash and "centerInside" in splash
    assert 'android:visibility="gone"' in splash
    splash_java = ler(src / "tools/android/packaging/xbmc/src/Splash.java.in")
    assert "SeedBase.pronto(this)" in splash_java and "startXBMCNow" in splash_java
    assert "mSplash.mProgress.setVisibility(View.INVISIBLE)" not in splash_java

    print("\nTudo aplicado. O build agora gera o APK unico:", APP_PACKAGE)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ErroDePatch as erro:
        print(f"::error::{erro}", file=sys.stderr)
        raise SystemExit(1)
