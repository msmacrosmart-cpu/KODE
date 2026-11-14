# SMARTEDTV Ads (AdMob nativo) + instalador do app principal

App Android leve, **duas funcoes no mesmo APK**:

1. **Anuncios** — mostra o App Open e o video pre-roll do AdMob em cima do Kodi
   (a ponte e o `StartAndroidActivity` do Python, explicada abaixo).
2. **Instalador** — e o **primeiro** app que o usuario instala: ao abrir, verifica
   se o app principal (`org.xbmc.kodi`) esta no aparelho e, se nao estiver, baixa
   o APK e abre a instalacao. Se ja estiver, apenas abre o SMARTEDTV.

A separacao continua necessaria porque o Kodi do APK e **binario pronto**
(NativeActivity): injetar `play-services-ads` nele exigiria recompilar o Kodi
inteiro, o que esta fora do fluxo de reempacotamento deste repositorio.

## Ordem de instalacao (o usuario instala UM arquivo so)

```
SMARTEDTV-Anuncios-<versao>.apk   ->  abre o icone  ->  baixa e instala o SMARTEDTV
                                                  ->  depois o Kodi volta a chamar o app
```

## Fluxo do instalador

```
icone do app (sem data)
        |
        v
LauncherActivity  --(data "smartedtv://ads...")-->  PreRollActivity / AppOpenActivity
        |                                            (ponte do Kodi, intacta)
        v
Kodi instalado e versionCode >= minimo?
   sim -> abre o SMARTEDTV (getLaunchIntentForPackage)
   nao -> BoasVindasActivity
             |
             +-- DownloadManager (242 MB, pasta privada do app, com progresso)
             +-- ao terminar: FileProvider -> intent de instalacao do Android
             +-- Android 8+: pede "instalar apps desconhecidos" para este app
```

## Onde fica o link do APK principal

Fonte unica: **`android/smarted-ads/apk-url.txt`**

```
url=https://github.com/.../releases/download/v1.0.63-classica/SMARTED-TV-v1.0.63-arm64.apk
codigo=2103049
```

- `url` — link **direto do anexo** da release (o DownloadManager segue o
  redirecionamento do GitHub para a CDN).
- `codigo` — `versionCode` minimo aceito. Se o Kodi instalado estiver abaixo
  disso, a tela oferece **atualizar** em vez de "abrir".

O Gradle transforma isso em `BuildConfig.APK_URL` / `BuildConfig.APK_CODIGO_MINIMO`
e o `checkAdMob` recusa o build se o link nao for `https://….apk` ou se o
manifesto nao tiver a permissao/FileProvider/tela de boas-vindas.
O CI (`build-ads-apk.yml`, passo `0b`) tambem confere se **a release e o anexo do
link existem** antes de compilar — link quebrado falha o build, nao o usuario.

Para apontar para outra versao sem editar o arquivo:

```
gradle -PapkUrl=https://…/SMARTED-TV-v1.0.64-arm64.apk -PapkCodigo=2103050 …
```

## Arquivos

| Arquivo | Papel |
|---|---|
| `Kodi.java` | sabe se `org.xbmc.kodi` esta instalado, em que versao, e abre |
| `Instalador.java` | `DownloadManager`, progresso, FileProvider, intent de instalacao, permissao |
| `BoasVindasActivity.java` | tela horizontal de boas-vindas/progresso/erro (nada de AdMob) |
| `LauncherActivity.java` | roteia: data URI = anuncio; icone = instalador ou Kodi |
| `Ads.java`, `AdActivity.java`, `AppOpenActivity`, `PreRollActivity` | AdMob (intactos) |
| `res/xml/file_paths.xml` | caminho que o FileProvider pode entregar ao instalador |

## Anuncios (inalterado)

| Tela | Bloco AdMob | Quando aparece |
|---|---|---|
| `AppOpenActivity` | `ca-app-pub-2066014755407744/4214378379` | uma vez, logo depois de a Home carregar |
| `PreRollActivity` | `ca-app-pub-2066014755407744/3572039686` | ao dar play em canal, filme ou serie |

Ponte (bootstrap 1.0.13+, 9 parametros, `intent` nunca vazio):

```
StartAndroidActivity(smartedtv.full,smartedtv.ads.PREROLL,,,,,,,org.smartedtv.ads.PreRollActivity)
```

Plano B (data URI no launcher do app):

```
StartAndroidActivity(smartedtv.full,android.intent.action.MAIN,,smartedtv://ads/preroll,,,,,org.smartedtv.ads.LauncherActivity)
```

## Build

`.github/workflows/build-ads-apk.yml` — Gradle + `play-services-ads` +
`androidx.core` (so o FileProvider), assinado com a mesma chave da linha.
O APK final passa por conferencia de pacote, AdMob, `sensorLandscape` nas 4 telas,
link do APK principal no dex e **limite de 10 MB**.

Logs: `adb logcat -s SmartAds` (tudo sai com essa tag: instalacao, download,
progresso, ponte e AdMob).
