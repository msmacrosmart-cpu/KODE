# SMARTED-TV 1.0.62 (linha clássica) — anúncios realmente abrem + diagnóstico

Base: **1.0.61 clássica**. Só o **service.smarted.bootstrap** muda (1.0.11 → 1.0.12).
Junto vai o **APK de anúncios 1.0.2**, em modo de teste e com logs.

## O bug que causava o "sem anúncios"

A ponte chamava `StartAndroidActivity(pacote, classe)`. Mas no Kodi (v20+) a ordem é:

```
StartAndroidActivity(package, intent, dataType, dataURI, flags, extras, action, category, className)
```

O **className é o nono parâmetro**. No formato antigo o Kodi montava um intent com
`action = "org.smartedtv.ads.PreRollActivity"`, **sem componente** → o Android não
encontrava atividade, o Kodi engolia o erro e **nada abria**. Não era falta de
inventário: **o anúncio nunca era pedido**.

Agora:

```
StartAndroidActivity(smartedtv.full,,,,,,,,org.smartedtv.ads.PreRollActivity)
```

## O que vem nesta versão

1. **Ponte corrigida** (9 parâmetros) + log `[SmartAds]` no `kodi.log` a cada disparo.
2. **APK de anúncios 1.0.2** com:
   - **modo de teste** (`ADS_TESTE=true`) usando os blocos oficiais do Google
     (`.../9257395921` abertura, `.../1033173712` vídeo) — sempre preenchem;
   - **logs com a tag `SmartAds`** em cada etapa: abertura da tela, carregamento, bloco
     usado, `onAdLoaded`, `onAdImpression`, `onAdClicked`, `onAdFailedToLoad` com
     **código numérico**, domínio, mensagem, `responseId` e causa;
   - **painel de erro na própria TV** (modo de teste): código do AdMob escrito na tela
     por ~9 s, para diagnosticar sem adb;
   - `<queries>` para `org.xbmc.kodi` (visibilidade Android 11+) — o start entre apps é
     por componente explícito, que já não dependia disso.
3. **Pacotes**: Kodi continua `org.xbmc.kodi`; anúncios `smartedtv.full`; classes das
   activities em `org.smartedtv.ads.*` e exportadas (conferido com `aapt2`).

## Como homologar em 3 passos

1. Instale `SMARTEDTV-Anuncios-1.0.2.apk` e o `SMARTED-TV-v1.0.62-arm64.apk`.
2. Abra o Kodi: o pop-up de abertura deve aparecer com a etiqueta *Test Ad*.
   Dê play em um canal: o vídeo de teste deve cobrir a tela e o conteúdo já começa atrás.
3. Se algo não aparecer, abra a tela (o painel de erro mostra o código) ou rode
   `adb logcat -s SmartAds`.

O guia completo está em `docs/DIAGNOSTICO-ANUNCIOS.md` (tabela de códigos 0/1/2/3/8).

## Conferência automática

- **Kodi**: falha o build se a ponte perder os 9 campos, se a classe não estiver no último
  parâmetro, se faltar o prefixo `[SmartAds]`, se o pacote da ponte divergir de
  `android/smarted-ads/app-id.txt`, ou se player/skin/anúncios regredirem.
- **Anúncios**: falha se faltar o bloco de teste correspondente no dex, a tag `SmartAds`,
  o `APPLICATION_ID`, as activities em `sensorLandscape`, ou a assinatura da linha.

## CONFERÊNCIA DO ARQUIVO PUBLICADO

Lido dos APKs **baixados da release** (`docs/comparacao-1.0.62.txt`):

| Arquivo | Pacote / versão | Tamanho | sha256 |
|---|---|---|---|
| `SMARTED-TV-v1.0.62-arm64.apk` | `org.xbmc.kodi` · 1.0.62 / 2103048 | 242.222.254 B | `5fe9024e0a487c9f8f53b4b9e40469623753ec56308c27c0d7019276ef74964f` |
| `SMARTEDTV-Anuncios-1.0.2.apk` | `smartedtv.full` · 1.0.2 / 3 | 5.006.759 B | `cb6405ceb54deeba0a2b7de96a7abb76d593868067b9bfd103c30bbdb7395886` |
| base `v1.0.61` (conferida no download) | `org.xbmc.kodi` · 1.0.61 / 2103047 | 242.222.254 B | `f4d1a2038fd4ddac17564cb284aab108d7df3185e638bf118c96c1ef3ffb9629` |

- Diff do ZIP contra a 1.0.61: **0 entradas novas, 0 removidas**; só
  `service.smarted.bootstrap/smart_ads.py` mudou (6.925 → 7.951 B). Nada mais no APK do Kodi.
- **11/11** checagens de anúncio OK no APK do Kodi, incluindo `builtin com 9 parametros`,
  `className no ultimo parametro` e `logs com tag SmartAds`.
- **9/9** de velocidade OK e skin sem regressão.
- No APK de anúncios publicado: pacote **`smartedtv.full`**, versão 1.0.2/3, os **dois blocos
  de teste do Google** no dex e a tag **`SmartAds`** presente.
