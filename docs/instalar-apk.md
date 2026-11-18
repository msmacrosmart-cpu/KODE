# Instalar o SMARTEDTV (celular, TV, box, projetor e stick)

**Versão atual: v20 universal única (1.0.90 / 2103076, v1+v2+v3, 32 e 64 bits)**

https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.90-universal-v20/SMARTEDTV-atual-v20-universal.apk

Tamanho: 285.488.378 bytes · SHA-256:
`3fbc702f4ed329b0b67666049902855b241e99672d3df42e18fcec69c150149f`

Pacote `smartedtv.full`, minSdk 21, targetSdk 34, ABIs `arm64-v8a` e
`armeabi-v7a`, assinatura v1+v2+v3 com o certificado `855de171...`.

**Pacote de download limpo (recomendado):**  
https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.88-reabertura-v18-download

- APK direto: https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.88-reabertura-v18-download/SMARTEDTV-atual-v18-reabertura-universal.apk
- ZIP com CRC: https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.88-reabertura-v18-download/SMARTEDTV-atual-v18-reabertura-universal.apk.zip

APK: **285.488.380 bytes** · SHA-256 `b09cc6cfd7123a6a94163f92b1c85b0fb5907dce7bfbc486ed1ecb373014924e`  
ZIP: **285.488.618 bytes** · SHA-256 `d987140f5689412b97d8aa153a1d0a0f0bab4cf835a2e2b4c37c5d6b6aaf3b0b`

O APK e o ZIP foram baixados de volta do GitHub e verificados no CI: ZIP íntegro,
`zipalign` OK, assinatura v1/v2/v3 válida, pacote `smartedtv.full`, minSdk 21,
targetSdk 34, ABIs `arm64-v8a` e `armeabi-v7a`.

O APK é grande (~250 MB) e é instalado **fora da Play Store**. A mensagem
genérica **“Aplicativo não instalado”** quase sempre é uma destas causas —
nenhuma delas é vírus ou APK corrompido:

| Causa | Como resolver |
|---|---|
| **Mesmo `versionCode` da versão instalada** | A v18 é `2103074`; se o aparelho já tem a v18, o Android pode recusar. |
| **Assinatura diferente da versão instalada** | Só desinstale **depois de exportar/copiar o perfil**; a desinstalação apaga dados e VIP local. |
| **ABI incompatível (x86/outra)** | A v18 tem `arm64-v8a` e `armeabi-v7a`; um projetor/box x86 não instala. |
| **“Instalar apps desconhecidos” desligado** | Autorize o navegador/gerenciador/Downloader que está abrindo o APK. |
| **Play Protect bloqueando** | Toque em **“Mais detalhes” → “Instalar mesmo assim”** (ou desligue a verificação temporariamente). |
| **Pouco espaço** | Libere pelo menos **1,5 GB**; o APK + instalação do Kodi ocupam bastante. |
| **Aparelho 32-bit (armeabi-v7a)** | Use a **v18 universal**: ela tem `lib/armeabi-v7a` e `lib/arm64-v8a`. |

> A v18 foi assinada com a **mesma chave** da v12…v17
> (`855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`), então
> instalar por cima de uma delas **preserva perfil, addons e VIP**. Só desinstale
> se a versão instalada veio de outra chave (por exemplo, um APK antigo do
> Dropbox ou um build de teste).
>
> **Antes de desinstalar:** copie a pasta de dados do app para pendrive/nuvem
> (`Android/data/smartedtv.full`, quando acessível) ou use o backup do Kodi.
> A desinstalação apaga o perfil local; a ativação VIP precisará ser refeita.

> **Instalação no projetor (v19):** se a v18 não instalou, use as variantes
> `arm64`, `arm32`, `universal` e `v2` da release
> [v1.0.89-instalacao-v19](https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.89-instalacao-v19).
> Todas têm o mesmo pacote/assinatura e `versionCode 2103075`; veja
> `docs/entrega-v19-instalacao.md`.

## 1. Conferir o arquivo baixado

Tamanho e SHA-256 da v18 estão na página da release. No Windows (PowerShell):

```powershell
Get-FileHash .\SMARTEDTV-atual-v18-reabertura-universal.apk -Algorithm SHA256
```

No Linux/macOS:

```bash
sha256sum SMARTEDTV-atual-v18-reabertura-universal.apk
```

O resultado tem de ser exatamente
`b09cc6cfd7123a6a94163f92b1c85b0fb5907dce7bfbc486ed1ecb373014924e`.
Se não bater, o download veio incompleto ou truncado: baixe de novo **direto do
GitHub**, sem passar por WhatsApp/Telegram/gerenciadores que comprimem arquivos.
Em aparelho com pouca memória, use o **Downloader** ou copie por pendrive.

### 1.1. Descobrir o motivo real pelo ADB (quando possível)

No PC com ADB e o aparelho liberado:

```bash
adb install -r SMARTEDTV-atual-v18-reabertura-universal.apk
```

O código devolvido pelo Android aponta a causa:

| Código | Significado | Ação |
|---|---|---|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | assinatura diferente da versão instalada | exportar o perfil e só então desinstalar |
| `INSTALL_FAILED_VERSION_DOWNGRADE` | `versionCode` menor/igual | confirmar que baixou a v18 (`2103074`) |
| `INSTALL_FAILED_INSUFFICIENT_STORAGE` | falta espaço | liberar ~1,5 GB |
| `INSTALL_FAILED_INVALID_APK` | arquivo truncado/corrompido | conferir SHA-256 e baixar de novo |
| `INSTALL_FAILED_NO_MATCHING_ABIS` | aparelho x86 ou ABI não incluída | informar o modelo/ABI; precisa de build x86 |
| `INSTALL_PARSE_FAILED_NO_CERTIFICATES` | APK sem assinatura válida | baixar novamente; não rezipar o APK |

Sem ADB, anote o **texto completo** da mensagem (TV/box costuma esconder atrás
de “Mais detalhes”).

## 2. Celular / tablet

1. Baixe o APK pelo navegador (Chrome, Firefox etc.).
2. Ao abrir, o Android pede para autorizar o navegador:
   **Configurações → Apps → Acesso especial → Instalar apps desconhecidos →
   Navegador → Permitir**.
3. Se aparecer **Play Protect** (“app não verificado”), escolha
   **“Instalar mesmo assim”**.
4. Se já existe uma versão antiga assinada com outra chave, o Android mostra
   “Aplicativo não instalado”; desinstale a antiga e repita.
5. Abra o app e aguarde a tela de ativação.

## 3. TV Android / Box / Projetor

1. Ligue **Fontes desconhecidas** para o app que vai instalar (Downloader,
   File Manager ou navegador):
   **Configurações → Segurança → Instalar apps desconhecidos**.
2. Instale pelo **Downloader** (loja da TV) com o link da release, ou copie o
   APK para um pendrive e abra pelo gerenciador de arquivos.
3. No controle remoto: **setas** navegam, **OK** confirma, **VOLTAR** volta.
   O campo do código já começa selecionado; OK abre o teclado do Kodi.
4. Se a imagem ficar cortada nas bordas, use
   **Configurações → Sistema → Vídeo → Calibrar tela** no Kodi (a v13/v14 já
   recua a tela 5% para a maioria das TVs).

## 4. Fire TV Stick

1. **Configurações → Meu Fire TV → Opções do desenvolvedor → Instalar apps
   desconhecidos → Downloader → Ligar**.
2. Instale o **Downloader** na loja da Amazon, abra e digite o link da release.
3. Se aparecer “App not installed”:
   - confira o espaço livre (**Configurações → Meu Fire TV → Armazenamento**);
   - desinstale uma versão antiga do SMARTEDTV se existir;
   - baixe de novo (o Downloader às vezes deixa arquivo parcial).
4. O Fire OS não tem Google Play: os anúncios do AdMob podem não preencher; a
   tela de anúncio fecha sozinha e o app continua. O VIP funciona normalmente.

## 5. Compatibilidade do APK

A **v18** é universal:

- **minSdk 21** (Android 5.0) — instala em **Android 8, 9, 10, 11, 12, 13, 14 e 15**;
- **targetSdk 34**;
- **ABIs: `arm64-v8a` (64-bit) e `armeabi-v7a` (32-bit)** no mesmo APK;
- `debuggable: false`, `testOnly` ausente;
- assinado com o certificado `855de171...`.

O Android escolhe a ABI sozinho. Para conferir qual o aparelho usa:

- app **AIDA64** ou **Device Info**: procure “ABI”/“CPU”;
- ou no PC com adb: `adb shell getprop ro.product.cpu.abilist`.

Se aparecer `arm64-v8a`, `armeabi-v7a` ou os dois, a v18 instala. As builds
v12–v15 eram somente arm64; por isso falhavam em aparelho 32-bit.

## 6. O que **não** é o problema

- O APK é **assinado** e a assinatura foi conferida no build
  (`apksigner verify --print-certs`) com o mesmo certificado da v12.
- Na v15 o `android:debuggable` foi **desligado** no manifesto (o APK base do
  Kodi vinha `debuggable=true`, e o Play Protect costuma cancelar build de
  desenvolvedor com a mensagem genérica “Aplicativo não instalado”).
- O app **não pede root**, não instala serviço escondido e não altera o sistema.
- “Aplicativo não instalado” **não** é o app fechando: ele nem chegou a ser
  instalado; é o instalador do Android recusando o pacote.

Se depois de tudo a instalação continuar falhando, mande:

- modelo do aparelho e versão do Android/Fire OS;
- **texto exato** da mensagem;
- se já havia outra versão do SMARTEDTV instalada;
- o SHA-256 do arquivo que você baixou.
