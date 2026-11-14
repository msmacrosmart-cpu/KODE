# APK único (monólito): Kodi + AdMob no mesmo pacote

Decisão: **fim do app auxiliar**. Um só APK, pacote `smartedtv.full`, com o
player compilado do código-fonte, os anúncios dentro do app e o conteúdo da
linha clássica. Instalou um arquivo, acabou.

## Como o build funciona

```
xbmc/xbmc @ 21.3-Omega
        │
        ├─ integrate-monolith.py       (smartedtv/tools)
        │     1. version.txt: APP_PACKAGE smartedtv.full   (APP_NAME segue "Kodi" → libkodi.so e .kodi intactos)
        │     2. Gradle: versionCode 2103050 / versionName 1.0.64
        │                + implementation play-services-ads:23.2.0
        │     3. Manifesto: permissão AD_ID, meta-data APPLICATION_ID,
        │                AppOpenActivity + PreRollActivity (sensorLandscape, exported)
        │     4. Java: SmartAds / AdTela / AppOpenActivity / PreRollActivity
        │                copiados para tools/android/packaging/xbmc/src/
        │                E listados no cmake/scripts/android/Install.cmake
        │                (sem essa lista o Java não entra no APK)
        │     5. Conteúdo: skin.novatv (+ skin.smartedtv.classic), plugin.video.smarted,
        │                service.smarted.bootstrap, resource.uisounds.silencio
        │                → addons/ + installdata/common/addons.txt + system/addon-manifest.xml
        │     6. settings.xml: skin padrão = skin.novatv
        │     7. smart_ads.py: classes internas (smartedtv.full.*) e plano B desligado
        │
        ├─ tools/depends → cmakebuildsys → make -j2 → make apk
        │
        └─ conferência bloqueante (aapt2 + dex + assets) → release
```

Workflow: `.github/workflows/build-monolith.yml` (tag `v1.0.64-unificado`,
arquivo `SMARTEDTV-1.0.64-unificado-arm64-v8a.apk`).

## Por que o `APP_NAME` não muda

O Kodi deriva `libkodi.so`, `assets/addons/kodi.binary.*`, o perfil `.kodi` e as
variáveis `KODI_*` do `APP_NAME`. Trocar para SMARTEDTV renomearia tudo isso e
quebraria o carregamento da biblioteca nativa e os dados do usuário. O que muda
é só o **applicationId** (identidade do app no Android) e os textos de exibição.

## A ponte dos anúncios, agora interna

Antes (dois apps): `StartAndroidActivity(smartedtv.full, ação, …, org.smartedtv.ads.PreRollActivity)`.

Agora (um app): o mesmo builtin, apontando para dentro:

```
StartAndroidActivity(smartedtv.full,smartedtv.ads.PREROLL,,,,,,,smartedtv.full.PreRollActivity)
StartAndroidActivity(smartedtv.full,smartedtv.ads.APPOPEN,,,,,,,smartedtv.full.AppOpenActivity)
```

- o plano B (data URI no launcher) fica **desligado**: o launcher do pacote é o
  próprio Kodi, abriria a interface de novo;
- o vídeo continua carregando atrás do anúncio, porque é o mesmo processo;
- desinstalar o app de anúncios não quebra mais nada — ele não existe.

## Modo de teste do AdMob

Ligado por padrão (`SmartAds.teste = true`), usando os blocos de teste do Google.
Para produção: `smartedtv/tools/ads-java/SmartAds.java.in` → `teste = false`
(e recompilar). Em tempo de execução, o próprio `StartAndroidActivity` pode
mandar `smartedtv://ads?teste=0`.

## O que a conferência do CI exige antes de publicar

| Checagem | Onde |
| --- | --- |
| `package: name='smartedtv.full'` | aapt2 badging |
| versionName 1.0.64 / versionCode 2103050 | aapt2 badging |
| `.AppOpenActivity`, `.PreRollActivity` | aapt2 xmltree |
| APPLICATION_ID + permissão `AD_ID` | aapt2 xmltree |
| `sensorLandscape` nas telas de anúncio | aapt2 xmltree |
| blocos do AdMob + classes + SDK + tag `SmartAds` | dex |
| `assets/addons/skin.novatv`, `plugin.video.smarted`, bootstrap, uisounds | ZIP |
| ponte apontando para dentro e sem plano B | smart_ads.py embarcado |

Se qualquer uma falhar, o APK não é publicado.

## Riscos e o que observar

1. **Tempo**: build completo ~1h30 num runner (dependências + Kodi + Gradle).
2. **Disco**: a receita já limpa o runner porque o build passa de 14 GB.
3. **Primeira instalação**: outro applicationId, então não atualiza por cima do
   `org.xbmc.kodi` antigo — são apps diferentes, podem conviver.
4. **Conteúdo**: o catálogo é literalmente o mesmo addon da linha clássica
   (`plugin.video.smarted`), com a skin e o `service.smarted.bootstrap` que já
   rodam hoje. Se algo do catálogo depender do perfil antigo (`.kodi`), a
   primeira abertura recria — vale testar a Home e as categorias na TV.
