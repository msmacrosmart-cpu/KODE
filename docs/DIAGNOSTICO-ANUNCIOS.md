# Diagnóstico dos anúncios (SMARTEDTV Ads + AdMob)

Guia rápido para homologar os anúncios: onde olhar, o que cada erro significa e como
separar "a ponte não funciona" de "a conta não tem inventário".

## 0. O bug que existia (corrigido no 1.0.62)

A ponte chamava:

```
StartAndroidActivity(smartedtv.full,org.smartedtv.ads.PreRollActivity)
```

Mas a assinatura do builtin do Kodi (v20+) é:

```
StartAndroidActivity(package, intent, dataType, dataURI, flags, extras, action, category, className)
```

O **className é o nono parâmetro**. No formato antigo, o Kodi interpretava a classe como
*action* e montava um intent **sem componente** → o Android não achava atividade nenhuma →
nada abria, e o Kodi engolia o erro. Resultado: **"sem anúncios"**, mesmo com inventário.

Agora a ponte monta os 9 campos:

```
StartAndroidActivity(smartedtv.full,,,,,,,,org.smartedtv.ads.PreRollActivity)
```

## 1. Pacotes (nada de conflito)

| Peça | Pacote | Observação |
|---|---|---|
| Kodi | `org.xbmc.kodi` | inalterado (o APK principal continua o mesmo app) |
| App de anúncios | `smartedtv.full` | classes em `org.smartedtv.ads.*` |

- A abertura entre pacotes diferentes é feita por **componente explícito**
  (`className`). O filtro de visibilidade do Android 11+ (`<queries>`) afeta consultas
  (`resolveActivity`, `queryIntentActivities`, `getPackageInfo`) — **não** o start
  explícito. Ainda assim, o app de anúncios declara
  `<queries><package android:name="org.xbmc.kodi"/></queries>`, e as duas activities são
  `android:exported="true"` (conferido com `aapt2` no CI).
- Restrição de "start de background": quem dispara é o Kodi **em primeiro plano**, então
  não há bloqueio de background-activity-start.

## 2. Modo de teste (isolando inventário x ponte)

O APK de anúncios sai com `ADS_TESTE=true` por padrão (build `-PadsTeste=false` desliga).
Com teste ligado ele usa os **blocos oficiais do Google**, que sempre preenchem:

| Tela | Bloco usado em teste |
|---|---|
| Abertura | `ca-app-pub-3940256099942544/9257395921` |
| Vídeo | `ca-app-pub-3940256099942544/1033173712` |

Leitura do resultado:

- **Aparece anúncio de teste** → ponte OK. Se o bloco real não preenche, é conta/inventário
  (conferir no console: app aprovado, unidade nova, `app-ads.txt`, política).
- **Não aparece nada** e o painel de diagnóstico aparece → ponte OK e o SDK respondeu erro
  (o código estará na tela). Ver tabela abaixo.
- **Não aparece nada e o Kodi volta na hora** → a ponte não chegou a abrir a tela
  (ver `kodi.log`, linha `[SmartAds] disparando ...`).

## 3. Onde estão os logs

**No Kodi** (`kodi.log`, visível em *Configurações → Registro de eventos*):

```
[SmartAds] disparando StartAndroidActivity(smartedtv.full,,,,,,,,org.smartedtv.ads.PreRollActivity) -> smartedtv.full/org.smartedtv.ads.PreRollActivity
```

**No Android (logcat)** — tudo com a tag `SmartAds`:

```
adb logcat -c
adb logcat -s SmartAds
```

O que aparece em sequência:

```
SmartAds: PreRollActivity: aberta | pacote=smartedtv.full versao=1.0.2(3) teste=true android=12 intent={...}
SmartAds: PreRollActivity: carregando VIDEO unidade=ca-app-pub-3940256099942544/1033173712 (teste=true)
SmartAds: PreRollActivity: onAdLoaded VIDEO | responseId=... adapters=1
SmartAds: PreRollActivity: onAdShowedFullScreenContent VIDEO (anuncio na tela)
SmartAds: PreRollActivity: onAdImpression VIDEO (impressao contabilizada)
SmartAds: PreRollActivity: onAdDismissedFullScreenContent VIDEO
SmartAds: PreRollActivity: fechando (video encerrado)
```

Em falha:

```
SmartAds: PreRollActivity: onAdFailedToLoad ... codigo=3 dominio=com.google.android.gms.ads
   mensagem=No fill. responseId=... causa=...
```

## 4. Códigos de erro do AdMob

| Código | Nome | O que costuma ser |
|---|---|---|
| 0 | `ERROR_CODE_INTERNAL_ERROR` | erro do SDK/anúncio inválido |
| 1 | `ERROR_CODE_INVALID_REQUEST` | bloco inválido, tamanho errado, app/unidade incompatíveis |
| 2 | `ERROR_CODE_NETWORK_ERROR` | sem rede/DNS no aparelho |
| 3 | `ERROR_CODE_NO_FILL` | **sem inventário** — conta sem anúncio para esse perfil/região/unidade nova |
| 8 | `ERROR_CODE_APP_ID_MISSING` | faltou `com.google.android.gms.ads.APPLICATION_ID` no manifesto |

## 5. Sem adb? O erro aparece na TV

Em modo de teste, qualquer falha desenha um painel escuro na própria tela por ~9 s com
o **código numérico**, domínio, mensagem, `responseId` e a versão/pacote do app. Tire foto
e me mande — dá para diagnosticar sem computador.

## 6. Voltar para os anúncios reais

Quando a homologação terminar: build com `ADS_TESTE=false`
(workflow `build-ads-apk.yml`, variável `ADS_TESTE`), nova versão do APK de anúncios e
mesma ponte — nada mais muda.
