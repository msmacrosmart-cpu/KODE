# SmartED-TV — KODE

App de IPTV para **Android TV / TV Box** (layout MakroTV) com menu de Configurações completo (TV Eminem) e player Media3/ExoPlayer.

- Kotlin + Jetpack Compose · minSdk 23 · targetSdk 35
- APK release gerado automaticamente pelo GitHub Actions a cada push/tag.

---

## 1) Instalar o ambiente de build (1 comando)

O ambiente necessário é: **JDK 17** + **Android SDK** (`platform-tools`, `platforms;android-35`, `build-tools;35.0.0` — que trazem `aapt2`, `apksigner`, `zipalign`) + `curl/unzip/git`.

### Linux / WSL / container (recomendado)

```bash
git clone https://github.com/msmacrosmart-cpu/KODE.git && cd KODE

# instala TUDO que falta (idempotente: pode rodar quantas vezes quiser)
sudo bash tools/scripts/setup-android-env.sh

# (sem root / dentro de CI/container, onde o SDK já existe)
bash tools/scripts/setup-android-env.sh --no-sudo
```

O script:
1. instala pacotes base (`curl`, `unzip`, `git`, `ca-certificates`);
2. garante **JDK 17** (usa o do sistema se já houver ≥17; senão tenta `apt/dnf/yum/pacman`; se falhar, baixa o **Temurin 17 portátil** em `.jdk17/`);
3. instala o **Android SDK** em `$ANDROID_HOME` (ou `.android-sdk/`): `cmdline-tools`, `platform-tools`, `platforms;android-35`, `build-tools;35.0.0`, aceitando as licenças;
4. grava o **`local.properties`** com `sdk.dir=...`;
5. imprime os `export` prontos e, em CI, exporta via `$GITHUB_ENV`.

### Exports para adicionar no `~/.bashrc` (sessão atual)

```bash
export JAVA_HOME="$HOME/.jdk17"                                  # ou o JDK 17 do sistema
export ANDROID_HOME="$PWD/.android-sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/35.0.0:$PATH"
```

### macOS (Homebrew)

```bash
brew install --cask temurin@17 android-commandlinetools
export ANDROID_HOME="$HOME/Library/Android/sdk"
sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"
echo "sdk.dir=$ANDROID_HOME" > local.properties
```

### Windows (PowerShell, sem WSL)

```powershell
winget install EclipseAdoptium.Temurin.17.JDK
winget install Google.AndroidStudio           # ou apenas cmdline-tools
# depois, no "cmdline-tools\bin":
sdkmanager --licenses
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"
" sdk.dir=$env:LOCALAPPDATA\Android\Sdk" -replace '^ ' | Out-File -Encoding ascii local.properties
```

### Verificar / testar o ambiente

```bash
java -version                 # deve dizer 17.x
sdkmanager --list_installed   # deve listar platforms;android-35 e build-tools;35.0.0
./gradlew --version           # Gradle 8.10.2 + JVM 17
```

---

## 2) Gerar o APK

```bash
# build + assinatura (gera release-keystore.jks se não existir)
./tools/scripts/build-release.sh

# atalho equivalente
./gradlew assembleRelease
```

Saída: `app/build/outputs/apk/release/app-release.apk`

Instalar no dispositivo:

```bash
adb connect 192.168.0.10:5555     # TV Box
adb install -r app/build/outputs/apk/release/app-release.apk
```

Keystore/versão customizados (opcional):

```bash
export KEYSTORE_PATH=/caminho/release-keystore.jks
export KEYSTORE_PASSWORD=... KEY_ALIAS=smartedtv KEY_PASSWORD=...
export VERSION_CODE=2 VERSION_NAME=1.0.1
./tools/scripts/build-release.sh
```

---

## 3) CI: `.github/workflows/build.yml` (builda sempre)

O workflow `Build APK (SmartED-TV)` roda em **push** (`main`, `arena/**`), **tags `v*`**, **pull request** e **workflow_dispatch**, e:

1. `actions/setup-java` → Temurin 17 (com cache Gradle);
2. `android-actions/setup-android` → `platforms;android-35`, `build-tools;35.0.0`;
3. `tools/scripts/setup-android-env.sh --no-sudo` → completa o que faltar (mesmo script do ambiente local);
4. `./gradlew assembleRelease` → gera o APK;
5. `apksigner`/`zipalign` → assina e verifica;
6. **artifact** `SmartED-TV-apk` (90 dias) + **GitHub Release** `v<run_number>` com o `.apk` anexado (download direto).

Disparar manualmente:

```bash
gh workflow run build.yml -f create_release=true -f version_name=1.0.1
gh run watch                    # acompanhar
```

Criar uma release versionada (tag):

```bash
git tag v1.0.1 && git push origin v1.0.1
```

---

---

## UI (layout enviado pelo usuário)

O app usa o pacote de design `smarted-tv-layout` (Kotlin + Compose), sempre em **paisagem (horizontal)**,
com referência de medidas **1672 x 941**:

- `ui/components/SmartedScaffold.kt` — fundo preto em vidro, área branca com curvas (`whitePath`), menu lateral de vidro (4 botões), cápsulas de título/relógio e painel Kodi (hambúrguer ou tecla MENU)
- `ui/components/Content.kt` — `MediaItem`, `FocusCard`, grades de pôsteres e listas com foco D-pad
- `ui/screens/Screens.kt` — Canais, Filmes, Séries, Navegar, Addons, Arquivos, Configurações, diálogo Sair
- `ui/theme/Smarted.kt` — tokens (preto, vidro, branco, tinta) e a referência 1672x941

Para ajustar curvas/posições: `whitePath` (r1=55, r2=70) e `offset(94, 7)` do hambúrguer.

## Escopo: app focado em Kodi (não IPTV)

Menu completo (hambúrguer ☰ / tecla MENU), com roteamento para todas as 12 seções:
Vídeos · Música · Programas · Rádio · Jogos · Imagens · Clima · Favoritos · Add-ons · Arquivos · Configurações · Sair

Configurações seguem o padrão do Kodi — **sem** conta/servidor/expiração de IPTV:
Interface · Aparência (skin) · Idioma e região · Player de vídeo · Aceleração de hardware ·
Saída de áudio · Legendas · Fontes de mídia · Atualizar biblioteca · Cache · Armazenamento ·
Rede e internet · Nome do dispositivo · Sobre.

## Releases / download direto

| O que | Aonde |
|---|---|
| **Download direto do APK (última versão)** | https://github.com/msmacrosmart-cpu/KODE/releases/latest/download/SmartED-TV-1.0.10-universal.apk |
| Página de todas as releases | https://github.com/msmacrosmart-cpu/KODE/releases |
| Artefatos de cada build (90 dias) | aba **Actions** → run → *Artifacts* |

Release só é publicada quando você **empurra uma tag `v*`** ou roda o workflow manualmente com `create_release=true`:

```bash
git tag v1.0.4 && git push origin v1.0.4                       # publica release v1.0.4
gh workflow run build.yml -f create_release=true -f version_name=1.0.4
```

## Estrutura do projeto

```
KODE/
├── .github/workflows/build.yml        # CI: build + assinatura + release
├── app/src/main/java/com/smarted/tv/
│   ├── MainActivity.kt
│   ├── data/model/Models.kt
│   ├── ui/screens/AppScreen.kt        # Dashboard, Canais, Filmes, Séries, Addons, Pastas, Config, Sair
│   ├── ui/components/                 # TvNavigationRail, SmartEDFocusable, GlassPanel, ScreenHeader
│   ├── ui/player/PlayerActivity.kt    # ExoPlayer (HLS/MP4)
│   ├── ui/theme/                      # Color.kt, Theme.kt
│   └── viewmodel/MainTvViewModel.kt
├── tools/scripts/
│   ├── setup-android-env.sh           # instala JDK 17 + Android SDK (usado local e no CI)
│   ├── install-deps.sh                # atalho compatível → setup-android-env.sh
│   └── build-release.sh               # build + assinatura do APK
└── gradle/wrapper/                    # Gradle 8.10.2
```

## Referências
- Layout base: MakroTV.XtreamYT
- Configurações: TV Eminem
- Arquitetura: IPTV-Native

## Atualizar sem desinstalar

Todas as versões são assinadas com a **mesma chave** (`tools/keystore/release-keystore.jks`),
por isso o Android aceita instalar por cima:

- **Pelo app:** Configurações › Atualizações › *Procurar atualização* › *Baixar e atualizar*.
  O app consulta o manifest `update.json` da última release, baixa o APK universal, confere o
  **SHA-256** e abre o instalador do sistema.
- **Manual:** instale o `.apk` universal novo por cima do atual (`adb install -r`).

Se algum dia o Android recusar com `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, a chave mudou — verifique
`tools/keystore/release-keystore.jks` e o secret `ANDROID_KEYSTORE_BASE64`.

