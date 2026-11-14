# SMARTEDTV Ads (AdMob nativo)

App Android minimo (Java) que mostra os anuncios do AdMob em cima do Kodi.
Existe separado porque o Kodi do APK e **binario pronto** (NativeActivity):
adicionar `play-services-ads` dentro dele exigiria recompilar o Kodi inteiro
do codigo-fonte (horas de toolchain NDK), o que esta fora do fluxo de
reempacotamento deste repositorio.

A ponte com o Python e o builtin do proprio Kodi:

```
StartAndroidActivity(org.smartedtv.ads,org.smartedtv.ads.PreRollActivity)
```

| Tela | Bloco AdMob | Quando aparece |
|---|---|---|
| `AppOpenActivity` | `.../4214378379` | uma vez, logo depois de a Home carregar |
| `PreRollActivity` | `.../3572039686` | ao dar play em canal, filme ou serie |

Ambas forcam `sensorLandscape`, tela cheia e se fecham sozinhas em 20 s se o
anuncio nao carregar — o usuario nunca fica preso.

Build: `.github/workflows/build-ads-apk.yml` (Gradle + play-services-ads,
assinado com a mesma chave da linha SMARTED-TV).
