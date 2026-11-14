# SMARTED-TV 1.0.61 (linha clássica) — anúncios com o pacote `smartedtv.full`

Base: **1.0.60 clássica** (sha256 `79ff859b7a37eb634d5d864bfb36240029128b27cabfd5f6f44aa628df0d65dc`).
Só o **service.smarted.bootstrap** muda (1.0.10 → 1.0.11). Skin 1.0.18, player rápido
(buffermode 1 / 50 MB / readfactor 20x) e visual intactos.

## O que mudou

O app de anúncios passou a usar o `applicationId` **`smartedtv.full`** (antes
`org.smartedtv.ads`), para casar com o aplicativo cadastrado no console do AdMob.
Nada mais mudou no comportamento: mesmos blocos, mesmas telas, mesma orientação.

| Peça | Valor |
|---|---|
| `applicationId` do app de anúncios | `smartedtv.full` |
| Pacote das **classes** (activities) | `org.smartedtv.ads` (não muda) |
| Ponte usada pelo Kodi | `StartAndroidActivity(smartedtv.full,org.smartedtv.ads.PreRollActivity)` |
| APPLICATION_ID AdMob | `ca-app-pub-2066014755407744~5076693043` |
| Bloco abertura | `ca-app-pub-2066014755407744/4214378379` |
| Bloco vídeo (pre-roll) | `ca-app-pub-2066014755407744/3572039686` |

O `applicationId` (nome do pacote no Android) e o nome das classes são coisas
separadas: o Kodi chama `StartAndroidActivity(pacote, classe)`, então a ponte leva os
dois — pacote `smartedtv.full`, classe `org.smartedtv.ads.PreRollActivity`. Por isso o
`namespace` do módulo ficou como está e só o pacote mudou.

> **Por que não `org.xbmc.kodi`:** esse é o pacote do próprio Kodi. O Android não aceita
> dois apps com o mesmo pacote — com a mesma assinatura da linha, o instalador tentaria
> **substituir/remover o Kodi** e recusaria pela versão (o app de anúncios está na
> `versionCode 2`, o Kodi na `2103047`). O build agora tem uma trava que quebra de
> propósito se alguém apontar o app de anúncios para o pacote do Kodi.

## Instalação

1. `SMARTED-TV-v1.0.61-arm64.apk` — o Kodi SMARTEDTV (atualiza por cima do 1.0.60).
2. `SMARTEDTV-Anuncios-1.0.1.apk` — o app de anúncios com o pacote novo.

⚠️ O app de anúncios mudou de pacote: `smartedtv.full` é um **app novo** para o Android.
Se o `SMARTEDTV-Anuncios-1.0.0.apk` (pacote antigo) estiver instalado, pode desinstalá-lo
depois de instalar o 1.0.1 — os dois convivem sem conflito, mas o Kodi só chama o 1.0.1
(que é o `smartedtv.full`). Ordem recomendada: instale o anúncios primeiro, depois o Kodi.

## Conferência automática

- **APK de anúncios:** pacote lido de `android/smarted-ads/app-id.txt` e conferido no
  APK final; `APPLICATION_ID` no manifesto; os dois blocos no dex; as duas activities
  com `screenOrientation=6` (`sensorLandscape`) lidas por `aapt2`; assinatura com o
  certificado `855de171…0951a`; e o build **falha** se o pacote for `org.xbmc.kodi`.
- **APK do Kodi:** falha se `versionName`/`versionCode` não forem `1.0.61`/`2103047`, se a
  ponte no `smart_ads.py` embarcado não apontar para o pacote de `app-id.txt`, se as
  classes das activities mudarem, se as checagens de player/skin/anúncios regredirem.

## CONFERÊNCIA DO ARQUIVO PUBLICADO

Lido dos APKs **baixados das releases** (`docs/comparacao-1.0.61.txt`):

| Arquivo | Pacote / versão | Tamanho | sha256 |
|---|---|---|---|
| `SMARTED-TV-v1.0.61-arm64.apk` | `org.xbmc.kodi` · 1.0.61 / 2103047 | 242.222.254 B | `f4d1a2038fd4ddac17564cb284aab108d7df3185e638bf118c96c1ef3ffb9629` |
| `SMARTEDTV-Anuncios-1.0.1.apk` | **`smartedtv.full`** · 1.0.1 / 2 | 5.002.663 B | `a75c656292b131df88edc42c9bb18c6ce1e278a47d886c87518ec8c339beeb4e` |
| base `v1.0.60` (conferida de novo) | `org.xbmc.kodi` · 1.0.60 / 2103046 | 242.222.254 B | `79ff859b7a37eb634d5d864bfb36240029128b27cabfd5f6f44aa628df0d65dc` |

- Diff do ZIP contra a 1.0.60: **0 entradas novas, 0 removidas**, e **só**
  `service.smarted.bootstrap/smart_ads.py` mudou (6.542 → 6.925 B — comentários e o
  `PACKAGE = 'smartedtv.full'`). Binário do Kodi, dex, perfil, skin e player intactos.
- 8/8 checagens de anúncio **OK** no APK do Kodi, incluindo **`pacote smartedtv.full na ponte`**.
- 9/9 checagens de velocidade **OK**; skin sem regressão (`9201@570 h194`, `9203@822 h194`,
  9202 ausente, `CC121212`, `FF1E1E1E`).
- O APK de anúncios anexado na release foi lido de novo no CI: **pacote `smartedtv.full`**,
  versão 1.0.1 / 2 — é exatamente o valor de `android/smarted-ads/app-id.txt`.
