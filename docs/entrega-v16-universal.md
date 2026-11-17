# Entrega v16 — APK universal 32-bit + 64-bit

**APK:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.86-tela-inicial-v16/SMARTEDTV-atual-com-tela-inicial-v16-universal.apk  
**Tamanho:** 285.599.139 bytes (~272 MiB)  
**SHA-256:** `596a8d020f07f63cbcb8a3674251b656afe226fe53d1d58d6ff0acb9b5ff6360`  
**Release:** https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.86-tela-inicial-v16  
**Versão:** `1.0.86` / `versionCode 2103072`  
**Build:** commit `cbba1e2` — run `44125720251` (os dois jobs verdes: compilação armv7 e montagem universal).

## O que mudou

O APK agora tem **as duas ABIs**:

- `lib/arm64-v8a/` — Android 64 bits;
- `lib/armeabi-v7a/` — Android 32 bits.

O Android escolhe sozinho a ABI correta na instalação. Isso resolve o caso de
aparelhos **32-bit** (Android 8/9/10/11 antigos, boxes, alguns sticks e
projetores) que recebiam “Aplicativo não instalado” porque a build anterior era
somente arm64.

## Por que não bastava copiar as libs do Kodi oficial

O `libkodi.so` chama, em tempo de execução:

```
FindClass("<APP_PACKAGE>/Main")
FindClass("<APP_PACKAGE>/XBMCSettingsContentObserver")
FindClass("<APP_PACKAGE>/XBMCInputDeviceListener")
```

O APK é `smartedtv.full`; o Kodi oficial é `org.xbmc.kodi`. Copiar as libs
armv7 oficiais faria o app fechar com `ClassNotFoundException`/`UnsatisfiedLinkError`.

Por isso o workflow `build-armv7-universal.yml` **compila o Kodi 21.3-Omega**
para `arm-linux-androideabi` com:

```
APP_PACKAGE smartedtv.full
```

no `version.txt`, usando a mesma receita do build arm64 (SDK 34, build-tools
33.0.1, NDK 21.4.7075529, `tools/depends` + `cmakebuildsys`). Depois extrai
`lib/armeabi-v7a/*.so` e junta ao APK v15 com
`tools/kodi/adicionar-abi-apk.py`, mantendo `lib/arm64-v8a/` intacto.

## O que foi preservado

- `applicationId` `smartedtv.full`;
- **mesma assinatura**
  (`855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`);
- perfil, addons, tela de entrada, VIP e dados do usuário;
- `android:debuggable=false` e `testOnly` ausente (Play Protect);
- tela normal no celular e `DialogWelcomeTV.xml` em TV/box/projetor/stick;
- campo 310 como `defaultcontrol`, teclado do Kodi, D-pad e VOLTAR;
- um anúncio por troca de conteúdo, nenhum para VIP, app-open uma vez.

O `versionCode` subiu de `2103071` (v15) para **`2103072`**: instala por cima da
v12, v13, v14 e v15 sem desinstalar e sem perder o VIP.

## Como instalar

1. Baixe o APK direto do GitHub (sem WhatsApp/Telegram; eles truncam).
2. Autorize **“instalar apps desconhecidos”** para o navegador/gerenciador/
   Downloader.
3. Se o **Play Protect** avisar, toque em **“Mais detalhes” → “Instalar mesmo
   assim”**.
4. Se houver uma versão antiga assinada com **outra chave** (APK do Dropbox ou
   build de teste), desinstale-a antes — isso apaga dados e o VIP precisa ser
   reativado.
5. Libere ~1,5 GB livres (o APK tem 272 MiB e o Kodi extrai/addons ocupam
   espaço).

Passo a passo por aparelho: `docs/instalar-apk.md`.

## Provas do build

- `libkodi.so` armv7 contém o pacote `smartedtv` (conferido no passo 9 do job
  de compilação) — é a garantia de que o JNI acha as classes Java;
- o APK final contém exatamente **uma** `lib/arm64-v8a/libkodi.so` e **uma**
  `lib/armeabi-v7a/libkodi.so` (passo 3 do job universal);
- `versionName 1.0.86` / `versionCode 2103072` (passo 3);
- `apksigner verify --print-certs` com o certificado `855de171...` (passo 4);
- **não houve execução em aparelho real 32-bit** neste ambiente. A validação é
  estática (ABIs, manifesto, assinatura e conteúdo das libs).
