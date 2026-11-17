# Entrega v15 — instalação sem “Aplicativo não instalado”

**APK:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.85-tela-inicial-v15/SMARTEDTV-atual-com-tela-inicial-v15.apk  
**Tamanho:** 250.491.255 bytes (~239 MiB)  
**SHA-256:** `860edc71067547e87c6e6671984977699d9c1a5c74857b3c87e01c78eaa15fe3`  
**Release:** https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.85-tela-inicial-v15  
**Versão:** `1.0.85` / `versionCode 2103071`  
**Commit:** `9133c89` — run `44115861632`, todos os passos verdes.

## O que foi corrigido

### 1. VersionCode maior que todas as versões anteriores

`1.0.83` → `1.0.85` e `versionCode 2103069` → **`2103071`**. Agora o Android
trata como **atualização** por cima da v12, v13 e v14; MIUI, Samsung, Android TV
e Fire OS não recusam mais por “mesmo código”.

### 2. `android:debuggable` desligado

O APK base do Kodi vinha com `android:debuggable="true"`. O Play Protect
costuma classificar build de desenvolvedor como suspeita e **cancelar a
instalação sem explicar** (“Aplicativo não instalado”). O passo **6c** agora
localiza o atributo no AXML binário e troca **somente o inteiro do valor**
`true` → `false`, sem mexer em offsets, strings ou no resto do manifesto.
`testOnly`, se existir, também é desligado.

O mesmo passo continua trocando `versionName`/`versionCode` (string de mesmo
tamanho + inteiro little-endian), então nada é decodificado/recriado com
apktool. O APK é alinhado e assinado com o **mesmo certificado**
(`855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`).

## O que não mudou

- `applicationId` `smartedtv.full`;
- perfil, addons, dados e VIP preservados ao atualizar;
- tela de entrada normal no celular e `DialogWelcomeTV.xml` em TV/box/projetor/
  stick;
- campo 310 como `defaultcontrol`, teclado real do Kodi, D-pad e VOLTAR;
- um anúncio por troca de conteúdo, nenhum para VIP, app-open uma vez;
- ativação VIP somente por `POST /api/public/validar-codigo` com `active:true`.

## Se ainda recusar a instalação

1. **Fontes desconhecidas** ligadas para o app que abre o APK (navegador,
   gerenciador de arquivos ou Downloader).
2. **Play Protect**: “Mais detalhes” → **“Instalar mesmo assim”**; se não
   aparecer, desligue temporariamente “Verificar apps com o Play Protect”.
3. **Assinatura diferente**: se o aparelho tem um SMARTEDTV antigo de outra
   chave (APK do Dropbox, build de teste), desinstale-o antes — isso apaga os
   dados e o VIP precisa ser reativado.
4. **Espaço**: libere pelo menos **1 GB** (APK + instalação do Kodi).
5. **Download íntegro**: confira o SHA-256 acima; baixe direto do GitHub, sem
   WhatsApp/Telegram.

Passo a passo por aparelho em `docs/instalar-apk.md`.

## Provas do build

- `static-check`: 215 XML, 63 scripts;
- `TVBoxStickTest`: 3 testes;
- passo 6: injeção byte a byte, perfil intacto e só arquivos esperados;
- passo 6c: `1.0.85` / `2103071` e **`debuggable=false`** conferidos no AXML;
- passo 7: `apksigner verify --print-certs` com o certificado `855de171...`;
- não houve execução em aparelho real neste ambiente.
