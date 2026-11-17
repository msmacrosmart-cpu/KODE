# Instalar o SMARTEDTV (celular, TV, box, projetor e stick)

**Versão atual: v16 universal (1.0.86 / 2103072, 32 e 64 bits)**  
https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.86-tela-inicial-v16/SMARTEDTV-atual-com-tela-inicial-v16-universal.apk  
SHA-256: `596a8d020f07f63cbcb8a3674251b656afe226fe53d1d58d6ff0acb9b5ff6360`

O APK é grande (~250 MB) e é instalado **fora da Play Store**. A mensagem
genérica **“Aplicativo não instalado”** quase sempre é uma destas causas —
nenhuma delas é vírus ou APK corrompido:

| Causa | Como resolver |
|---|---|
| **Mesmo `versionCode` da versão instalada** | Use a v16 universal (1.0.86 / 2103072) ou desinstale a anterior antes. |
| **Assinatura diferente da versão instalada** | Desinstale a versão antiga (perde dados e VIP) e instale de novo. |
| **“Instalar apps desconhecidos” desligado** | Autorize o navegador/gerenciador/Downloader que está abrindo o APK. |
| **Play Protect bloqueando** | Toque em **“Mais detalhes” → “Instalar mesmo assim”** (ou desligue a verificação temporariamente). |
| **Pouco espaço** | Libere pelo menos **1,5 GB**; o APK + instalação do Kodi ocupam bastante. |
| **Aparelho 32-bit (armeabi-v7a)** | Use a **v16 universal**: ela tem `lib/armeabi-v7a` e `lib/arm64-v8a`. |

> A v16 foi assinada com a **mesma chave** da v12/v13
> (`855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`), então
> instalar por cima da v12/v13 **preserva perfil, addons e VIP**. Só desinstale
> se a versão que está no aparelho veio de outra chave (por exemplo, um APK
> antigo do Dropbox ou de outro build).

## 1. Conferir o arquivo baixado

Tamanho e SHA-256 da v14 estão na página da release. No Windows (PowerShell):

```powershell
Get-FileHash .\SMARTEDTV-atual-com-tela-inicial-v14.apk -Algorithm SHA256
```

No Linux/macOS:

```bash
sha256sum SMARTEDTV-atual-com-tela-inicial-v14.apk
```

Se o hash não bater, o download veio incompleto: baixe de novo **direto do
GitHub**, sem passar por WhatsApp/Telegram (eles comprimem/truncam arquivos).

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

A **v16** é universal:

- **minSdk 21** (Android 5.0) — instala em **Android 8, 9, 10, 11, 12, 13, 14 e 15**;
- **targetSdk 34**;
- **ABIs: `arm64-v8a` (64-bit) e `armeabi-v7a` (32-bit)** no mesmo APK;
- `debuggable: false`, `testOnly` ausente;
- assinado com o certificado `855de171...`.

O Android escolhe a ABI sozinho. Para conferir qual o aparelho usa:

- app **AIDA64** ou **Device Info**: procure “ABI”/“CPU”;
- ou no PC com adb: `adb shell getprop ro.product.cpu.abilist`.

Se aparecer `arm64-v8a`, `armeabi-v7a` ou os dois, a v16 instala. As builds
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
