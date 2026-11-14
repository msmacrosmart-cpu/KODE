# SMARTED-TV 1.0.60 (linha clássica) — anúncios AdMob + player rápido

Base: **1.0.59 clássica** (sha256 `5e3dc5c36be6b630ced417f2feab85af6507c2d00b7c2e86256f6491d08cf51b`).
O Kodi não foi recompilado: reempacotamos o APK e trocamos só o **service.smarted.bootstrap**
(1.0.9 → 1.0.10). Skin 1.0.18, cache e ajustes de velocidade da 1.0.59 mantidos.

## Como os anúncios funcionam

O Kodi do APK é um **binário pronto** (`NativeActivity`). Não existe forma de injetar
`play-services-ads` dentro dele sem recompilar o Kodi inteiro do código-fonte (toolchain NDK,
horas de build) — e qualquer "remendo" de dex/manifesto sem os recursos do SDK quebraria o app.

A integração foi feita do jeito que funciona de verdade:

- **App nativo Android** `org.smartedtv.ads` (pasta `android/smarted-ads`, Java + Gradle,
  `com.google.android.gms:play-services-ads:23.2.0`), assinado com a **mesma chave** da linha.
- **Ponte com o Python**: o Kodi abre as telas de anúncio com o builtin nativo
  `StartAndroidActivity(org.smartedtv.ads,org.smartedtv.ads.PreRollActivity)` — sem
  `adb`, sem root, sem add-on exótico.
- As duas telas forçam `android:screenOrientation="sensorLandscape"` **no manifesto e no
  código**, tela cheia imersiva, `FLAG_KEEP_SCREEN_ON`. Se o anúncio não carregar (sem
  inventário/sem rede), a tela se fecha sozinha em **20 s** — o usuário nunca fica preso.

| Gatilho | Tela | Bloco AdMob |
|---|---|---|
| Abertura do app | `AppOpenActivity` | `ca-app-pub-2066014755407744/4214378379` |
| Antes de canal/filme/série | `PreRollActivity` | `ca-app-pub-2066014755407744/3572039686` |

APPLICATION_ID no manifesto: `ca-app-pub-2066014755407744~5076693043`.

### Gatilho 1 — abertura (uma única vez)
O serviço de boot espera a Home terminar de desenhar (`ensure_skin` + `ensure_home_nodes`),
espera 6 s, e só então abre o pop-up — **uma vez por instalação** (marca gravada em
`userdata/addon_data/service.smarted.bootstrap/ads-abertura.txt`). Se o usuário já estiver
assistindo algo nesse momento, o pop-up é adiado e não aparece.

### Gatilho 2 — vídeo pre-roll (canal, filme e série)
O gancho é o próprio `xbmc.Player`, então vale para **qualquer** reprodução — canal de TV,
filme ou série, venha do Brazuca Play ou de outro add-on: `onPlay` dispara a Intent nativa,
o anúncio cobre a tela **enquanto o player faz o buffer atrás**, e ao fechar o vídeo já está
pronto. `onAVStarted` cobre os streams que só disparam lá; um intervalo mínimo
(`PREROLL_INTERVALO`, 120 s) evita anúncio em sequência no zapping.

## Instalação (são 2 APKs)

1. `SMARTED-TV-v1.0.60-arm64.apk` — o Kodi SMARTEDTV (como sempre).
2. `SMARTEDTV-Anuncios-*.apk` — o app de anúncios. Instale junto, **na mesma ordem ou antes**;
   fica sem ícone de launcher (é aberto só pelo Kodi).

Sem o segundo APK, o Kodi funciona normalmente: o builtin simplesmente não abre nada.

## Conferência automática no build

O workflow `build-release-classica.yml` falha o build se, dentro do APK publicado:

- `versionName`/`versionCode` não forem `1.0.60` / `2103046`;
- o `performance.py` perder `buffermode 1`, `memorysize 52428800`, `readfactor 20.0`,
  marker `smartedtv-performance-v2`, `memorysize 48`, `readfactor 2000`, `adjustrefreshrate 0`;
- o `service.py` voltar a aplicar performance depois do nav-check;
- o `smart_ads.py` embarcado perder `org.smartedtv.ads`, `AppOpenActivity`,
  `PreRollActivity`, `StartAndroidActivity(%s,%s)`, `MonitorPreRoll` ou
  `smart_ads.iniciar_monitor` no serviço;
- a skin regredir (1.0.18, `9201 top=570 h=194`, `9203 top=822 h=194`, `9202` ausente,
  painel `CC121212`, foco `FF1E1E1E`).

E o workflow `build-ads-apk.yml` falha se o APK de anúncios não sair com o APPLICATION_ID no
manifesto, os dois blocos no dex, as duas activities em `sensorLandscape`, sem
`play-services-ads`, ou assinado com certificado diferente de
`855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`.
