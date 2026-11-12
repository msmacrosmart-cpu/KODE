# Alterações aplicadas ao código-fonte do Kodi 21.3-Omega

Lista completa, arquivo por arquivo, do que `smartedtv/tools/patch-source.py`
altera. Nada fora desta lista é modificado no upstream.

Total: **25 arquivos** (10 de código/texto + 15 de imagem).

## 1. Texto e identificação

### 1.1 `version.txt`
```diff
-COMPANY_NAME XBMC Foundation
-DEV_NAME Team Kodi
+COMPANY_NAME SMARTEDTV
+DEV_NAME SMARTEDTV
-VERSION_MINOR 3
-VERSION_TAG
-VERSION_CODE 21.3.0
+VERSION_MINOR 4
+VERSION_TAG Omega
+VERSION_CODE 21.4.0
-PACKAGE_DESCRIPTION Kodi is an open source (GPL) software media center for …
+PACKAGE_DESCRIPTION SMARTEDTV is an open source (GPL) media center for …
```
**Não alterado:** `APP_NAME Kodi`, `APP_PACKAGE org.xbmc.kodi`, `ADDON_API 21.3.0`,
`ADDON_REPOS`, `PACKAGE_IDENTITY`. Ver `RELATORIO-INTEGRIDADE.md` §5.

Consequências: `versionName` 21.3 → 21.4; `versionCode` 2103000 → **2104000**;
`GetSuffix()` deixa de ser vazio (a janela de informações e o JSON-RPC continuam
consistentes).

### 1.2 `tools/android/packaging/xbmc/strings.xml.in`
```diff
-    <string name="app_name">@APP_NAME@</string>
-    <string name="search_hint">@APP_NAME@</string>
+    <string name="app_name">SMARTEDTV</string>
+    <string name="search_hint">SMARTEDTV</string>
```
Este é o texto que o Android mostra no launcher, na lista de apps da Android TV,
em "Recentes" e nas configurações do sistema. O `AndroidManifest.xml` continua
apontando para `@string/app_name`, e `android.app.lib_name` continua `kodi`.

### 1.3 `tools/android/packaging/xbmc/src/Splash.java.in`
```diff
-  private static final String TAG = "@APP_NAME@";
+  private static final String TAG = "SMARTEDTV";
-          dialog.setMessage("@APP_NAME@ requires access to your device media and files …");
+          dialog.setMessage("SMARTEDTV requires access to your device media and files …");
-          mSplash.mTextView.setText("Starting @APP_NAME@...");
+          mSplash.mTextView.setText("Starting SMARTEDTV...");
```
Afeta: o texto sob a barra de progresso da splash nativa, o diálogo de permissão
de armazenamento e as tags no logcat.

### 1.4 `tools/android/packaging/xbmc/src/Main.java.in`
```diff
-  private static final String TAG = "@APP_NAME@";
+  private static final String TAG = "SMARTEDTV";
```

### 1.5 `addons/resource.language.en_gb/resources/strings.po`
8 `msgid`/`msgstr` alterados:

| String | Antes | Depois |
|---|---|---|
| #9 | Kodi media center | SMARTEDTV media center |
| #482 | About Kodi | About SMARTEDTV |
| #6 | Kodi GIT | SMARTEDTV GIT |
| #20009 | Use Kodi | Use SMARTEDTV |
| #19209 | Kodi virtual backend | SMARTEDTV virtual backend |
| — | Use Kodi virtual keyboard | Use SMARTEDTV virtual keyboard |
| — | Kodi virtual keyboard | SMARTEDTV virtual keyboard |
| — | When you need to enter some text, Kodi virtual keyboard … | … SMARTEDTV … |
| #6197 | Kodi is brought to you with love from the Kodi Foundation … | SMARTEDTV is an open source media center. Thank you for using our software! |

### 1.6 `addons/resource.language.pt_br/resources/strings.po`
(pt-BR oficial, incluído por §2.1)

| Antes | Depois |
|---|---|
| Sobre o Kodi | Sobre o SMARTEDTV |
| Usar Kodi | Usar SMARTEDTV |
| Kodi backend virtual | SMARTEDTV backend virtual |
| Kodi é oferecido a você com amor pela Fundação Kodi … | SMARTEDTV é um media center de código aberto. Obrigado por usar nosso software! |

### 1.7 `system/settings/settings.xml`
```diff
         <setting id="services.devicename" type="string" label="1271" help="36321">
           <level>0</level>
-          <default>Kodi</default>
+          <default>SMARTEDTV</default>
```
Nome padrão do aparelho em zeroconf/UPnP/AirPlay — o que aparece na TV ao
descobrir o servidor.

### 1.8 `addons/skin.estuary/addon.xml`
```diff
-<summary lang="en_GB">Estuary skin by phil65. (Kodi&apos;s default skin)</summary>
+<summary lang="en_GB">Estuary skin by phil65. (SMARTEDTV default skin)</summary>
-<summary lang="en_US">… (Kodi&apos;s default skin)</summary>
+<summary lang="en_US">… (SMARTEDTV default skin)</summary>
-<summary lang="pt_BR">… (skin padrão do Kodi)</summary>
+<summary lang="pt_BR">… (skin padrão do SMARTEDTV)</summary>
```
Único metadado editado da skin. Nenhum XML de layout, textura ou menu da Estuary
foi tocado.

## 2. Código C++ (nome de exibição na GUI)

### 2.1 `xbmc/CompileInfo.h`
```diff
   static const char* GetAppName();
+  static const char* GetDisplayName(); // nome de exibição (identidade SMARTEDTV)
```

### 2.2 `xbmc/CompileInfo.cpp.in`
```diff
 const char* CCompileInfo::GetAppName()
 {
   return "@APP_NAME@";
 }
 
+const char* CCompileInfo::GetDisplayName()
+{
+  return "SMARTEDTV";
+}
```

### 2.3 `xbmc/utils/SystemInfo.h`
```diff
   static const std::string& GetAppName(void); // the same name as CCompileInfo::GetAppName()…
+  /*! \brief Nome de exibição do aplicativo (identidade visual SMARTEDTV).
+      Usado apenas em textos de interface; não afeta caminhos nem User-Agent. */
+  static const std::string& GetDisplayName();
```

### 2.4 `xbmc/utils/SystemInfo.cpp`
```diff
 const std::string& CSysInfo::GetAppName(void) { … }
+
+const std::string& CSysInfo::GetDisplayName(void)
+{
+  static const std::string displayName(CCompileInfo::GetDisplayName());
+
+  return displayName;
+}
```

### 2.5 `xbmc/windows/GUIWindowSystemInfo.cpp`
```diff
-      SET_CONTROL_LABEL(52, CSysInfo::GetAppName() + " " + CSysInfo::GetVersion());
+      SET_CONTROL_LABEL(52, CSysInfo::GetDisplayName() + " " + CSysInfo::GetVersion());
```
Resultado na tela Configurações → Informações do sistema: **`SMARTEDTV 21.4.0
(21.4.0) Git:…`**.

`GetAppName()` permanece `"Kodi"` e continua sendo usado onde é identificador
técnico: User-Agent HTTP, CDDB, JSON-RPC `Application.GetProperties("name")`,
nome do pacote para add-ons (`kodi_get_compile_info`) e logs do motor.

## 3. Imagens (todas derivadas da arte oficial, sem redesenho)

| Arquivo | Dimensão | Papel |
|---|---|---|
| `media/splash.jpg` | 1920×1080 | splash da GUI (`CUtil::GetSplashPath`) |
| `media/applaunch_screen.png` | 1920×1080 | splash nativa do Android (`R.drawable.applaunch_screen`) |
| `media/banner.png` | 320×180 | banner Android TV (`android:banner`) |
| `media/vendor_logo.png` | 465×128 (RGBA) | marca na Home e na tela de login |
| `media/vendor_icon.png` | 128×128 | ícone de fornecedor |
| `media/icon256x256.png` | 256×256 | ícone de notificação de evento |
| `media/icon120x120.png` | 120×120 | ícone interno |
| `media/icon80x80.png` | 80×80 | ícone de recomendação no Android |
| `media/icon48x48.png` | 48×48 | ícone interno |
| `media/icon32x32.png` | 32×32 | ícone interno |
| `media/icon16x16.png` | 16×16 | ícone interno |
| `tools/android/packaging/media/drawable-ldpi/ic_launcher.png` | 36×36 | launcher |
| `…/drawable-mdpi/ic_launcher.png` | 48×48 | launcher |
| `…/drawable-hdpi/ic_launcher.png` | 72×72 | launcher |
| `…/drawable-xhdpi/ic_launcher.png` | 96×96 | launcher |
| `…/drawable-xxhdpi/ic_launcher.png` | 144×144 | launcher |
| `…/drawable-xxxhdpi/ic_launcher.png` | 192×192 | launcher |
| `…/drawable-xhdpi/banner.png` | 320×180 | banner (densidade TV) |

Fonte única: `smartedtv/assets/brand/logo-oficial.jpg` (arte oficial 1600×1600,
campo preto puro). `mark.png` é o recorte do selo circular da mesma arte.

## 4. Idioma (inclusão, não alteração)

- `addons/resource.language.pt_br/` — copiado de `xbmc/repo-resources` branch
  `omega` (addon oficial, versão 11.0.109).
- `cmake/installdata/common/addons.txt` — `addons/resource.language.pt_br/*`
  adicionado em ordem alfabética para entrar no APK.

Motivo: o Kodi embarca só `en_gb`; o público do projeto é brasileiro.

## 5. Verificação das alterações

```bash
# diff completo contra o upstream
diff -rq <kodi-src> <kodi-patchado>

# guardas automáticas
python3 smartedtv/tools/patch-source.py <kodi-src>
#  - aborta se APP_NAME != Kodi
#  - aborta se APP_PACKAGE != org.xbmc.kodi
#  - aborta se ADDON_API != 21.3.0
#  - aborta se qualquer âncora de código não existir (upstream mudou)
#  - é idempotente
```

## 6. O que NÃO foi alterado (amostra)

- Nenhum arquivo dentro de `addons/skin.estuary/xml/` (todos os 40+ layouts).
- `addons/skin.estuary/media/Textures.xbt`.
- `AndroidManifest.xml.in` (permissões, activities, intent-filters, `lib_name`).
- `tools/android/packaging/xbmc/build.gradle.in` (AGP, signingConfigs).
- Qualquer `plugins/`, `xbmc/addons/`, `xbmc/cores/`, `xbmc/settings/` fora do
  listado em §2.
- `system/addon-manifest.xml` (nenhum add-on adicionado ou removido).
- `patches/kodi-21.3-native-android-keyboard.patch` (não aplicado nesta etapa).
