# SMARTEDTV 1.0.114 — TV ao vivo com imagem, anúncio por dispositivo e pasta em cinza

**APK:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.114-universal/SMARTEDTV-universal.apk
**Tamanho:** 287.262.352 bytes
**SHA-256:** `34e4d1667b09b63f2baa507ddd9f68eab1e863f5d600597dd1e68d768106dbae`
**Commit:** `0ebf666` · **Pipeline:** run `44356256293` (SUCCESS)
**Versão no APK:** `1.0.114` / versionCode `2103100` · cert `855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a` (mesma chave) · SDK 21, arm64-v8a + armeabi-v7a, v1/v2/v3

## 1. Tela preta nos canais de TV ao vivo (o pedido desta rodada)

**Causa raiz (a única que é código nosso):** a volta do anúncio devolvia o vídeo
para a posição guardada com `Player.Seek`. Em filme/série isso é certo (VOD tem
duração e ponto de retomada). Em canal ao vivo o ponto guardado fica **fora da
janela disponível** da transmissão: o Kodi busca no passado que não existe mais
e o player fica sem quadro (preto, às vezes com som) até trocar de canal.
Mesmo mecanismo na troca de canal logo após um pré-roll.

**Correções:**
- `ad_return.py`: canal contínuo (`m3u8`, `ts`, `mode=11` do Brazuca, PVR) **nunca**
  recebe seek. Filme/série mantém a retomada exata de antes.
- `ad_return.py`: se o fluxo cair enquanto a tela do anúncio está na frente, o
  canal é **reaberto no ponto atual** da transmissão.
- `ao_vivo.py` (novo): depois de abrir um canal, confere se existe imagem
  (`Player.Process(videowidth)` / `videocodec`). Sem imagem, desliga MediaCodec
  Surface, reabre o canal **uma vez** e grava a escolha em
  `userdata/addon_data/service.smarted.bootstrap/ao-vivo-sem-surface.txt`.
- `performance.py`: o boot seguinte já começa no perfil aprendido — o aparelho
  não repete a tela preta a cada abertura.
- Filme/série não entram em nenhum desses caminhos.

## 2. Anúncio por dispositivo

- Celular/tablet: **AdMob** como sempre (activity `PreRollActivity`/`AppOpenActivity`).
- TV / TV Box / projetor / Fire Stick: **sem activity AdMob** (era o que deixava
  o player preto em tela grande). O ponto de entrada do VAST é `abrir_anuncio_vast()`
  em `smart_ads.py`, com `VAST_TAG_PADRAO` vazio de propósito.
- **Limitação real:** o SDK Google IMA não está compilado neste APK (não há fonte
  Java dele no repositório, e `verify.py` recusa dex/lib alterados). VAST com
  D-pad e botão oficial de pular **só existe depois de compilar o IMA no app
  Android**. Hoje: em tela grande o vídeo começa sem anúncio, e nenhum aparelho
  que funcionava foi prejudicado.

## 3. Bloco branco na tela de pastas

`MyVideoNav.xml` (nas duas skins, idênticas): card da lista `B3FFFFFF` →
`F2262626` e foco `FFFFFFFF` → `FF3A3A3A`. O XML passou a ser injetado no APK
(`SKIN_ARQUIVOS` no `atualizar-apk-v17.py`) — antes só a Home era trocada.

## Testes deste build

- `tests/test_ao_vivo.py` (11) e `tests/test_ads_por_dispositivo.py` (14) entram no
  pipeline via `tests.test_projetor_addons` (35 testes): sem falha.
- `tools/kodi/static-check.py`: 229 XML válidos, 72 scripts.
- Suíte completa: 428 testes, 25 falhas — **as mesmas do baseline** anterior, nenhuma nova.
- AVD API 30: atualização arm64, instalação limpa armv7, LAUNCHER + LEANBACK,
  3 reaberturas com imagem, `pm install -r -d` aceito.

## O que ainda depende do seu aparelho

Não há TV/celular físico aqui. O log que fecha o diagnóstico de imagem é
`userdata/kodi.log` na parte `[AoVivo]` e `[SmartAds] TV ao vivo`:
- se aparecer `imagem ok` → canal com quadro;
- se aparecer `canal sem imagem ... audio=sim/nao` → o aparelho trocou para o
  perfil sem Surface e reabriu o canal (§1).
