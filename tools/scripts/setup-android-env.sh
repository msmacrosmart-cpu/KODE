#!/usr/bin/env bash
# =============================================================================
#  setup-android-env.sh — instala TODO o ambiente de build do SmartED-TV
# -----------------------------------------------------------------------------
#  Instala (de forma idempotente, só o que falta):
#    • JDK 17 (Temurin)
#    • Android SDK: cmdline-tools, platform-tools, platforms;android-35,
#      build-tools;35.0.0 (aapt2, apksigner, zipalign)
#    • local.properties apontando o sdk.dir
#    • Ferramentas auxiliares: curl, unzip, git
#
#  Uso:
#    sudo bash tools/scripts/setup-android-env.sh        # instala tudo
#    bash tools/scripts/setup-android-env.sh --no-sudo   # sem root (CI/containers)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

SDK_DIR="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [[ -z "$SDK_DIR" ]]; then
  if [[ -d "/usr/local/lib/android/sdk" ]]; then
    SDK_DIR="/usr/local/lib/android/sdk"          # runner do GitHub Actions
  else
    SDK_DIR="$PROJECT_DIR/.android-sdk"
  fi
fi
JDK_DIR="${JDK_HOME:-$PROJECT_DIR/.jdk17}"
CMDLINE_TOOLS_VERSION="11076708"          # commandlinetools-linux-11076708
COMPILE_SDK="35"

BUILD_TOOLS="35.0.0"
NO_SUDO=0
[[ "${1:-}" == "--no-sudo" ]] && NO_SUDO=1

SUDO="sudo"
if [[ "$NO_SUDO" == "1" || "$(id -u)" == "0" ]]; then SUDO=""; fi

say() { printf '\n\033[1;36m[+] %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[!] %s\033[0m\n' "$*"; }

have() { command -v "$1" >/dev/null 2>&1; }

# ───────────────────────────────────────────────────────────────
# 0) Pacotes base
# ───────────────────────────────────────────────────────────────
install_base_pkgs() {
  if have curl && have unzip && have git; then return; fi
  say "Instalando pacotes base (curl, unzip, git)"
  if have apt-get; then
    $SUDO apt-get update -y
    $SUDO apt-get install -y --no-install-recommends curl unzip git ca-certificates
  elif have dnf; then
    $SUDO dnf install -y curl unzip git ca-certificates
  elif have yum; then
    $SUDO yum install -y curl unzip git ca-certificates
  elif have pacman; then
    $SUDO pacman -Sy --noconfirm curl unzip git ca-certificates
  else
    warn "Gerenciador de pacotes não suportado — garanta curl/unzip/git manualmente."
  fi
}

# ───────────────────────────────────────────────────────────────
# 1) JDK 17
# ───────────────────────────────────────────────────────────────
java_major() {
  local j="${1:-java}"
  "$j" -version 2>&1 | sed -n 's/.*version "\([0-9]*\).*/\1/p' | head -1
}

install_jdk() {
  # Já existe um JDK 17+ no sistema?
  if have java && [[ "$(java_major java)" -ge 17 ]]; then
    JAVA_HOME_REAL="$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")"
    say "JDK 17+ já instalado: $JAVA_HOME_REAL"
    export JAVA_HOME="$JAVA_HOME_REAL"
    return
  fi

  # JDK portátil já baixado?
  if [[ -x "$JDK_DIR/bin/java" ]]; then
    say "JDK portátil encontrado em $JDK_DIR"
    export JAVA_HOME="$JDK_DIR"
    return
  fi

  # Tenta gerenciador de pacotes
  if have apt-get; then
    say "Instalando OpenJDK 17 via apt-get"
    $SUDO apt-get update -y
    $SUDO apt-get install -y --no-install-recommends openjdk-17-jdk-headless && {
      export JAVA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")"
      return
    } || warn "apt falhou, tentando JDK portátil (Adoptium)"
  fi

  # Fallback: Temurin tarball do GitHub (funciona onde apt não tem JDK)
  say "Baixando Temurin JDK 17 (portátil) em $JDK_DIR"
  mkdir -p "$JDK_DIR"
  local api="https://api.github.com/repos/adoptium/temurin17-binaries/releases/latest"
  local url
  url="$(curl -fsSL "$api" \
        | grep -o '"browser_download_url": *"[^"]*OpenJDK17U-jdk_x64_linux_hotspot[^"]*tar.gz"' \
        | head -1 | sed 's/.*"\(https[^"]*\)"/\1/')"
  if [[ -z "$url" ]]; then
    warn "Não foi possível descobrir a URL do JDK 17. Instale openjdk-17 manualmente."
    exit 1
  fi
  curl -fL --retry 3 -o /tmp/jdk17.tar.gz "$url"
  tar -xzf /tmp/jdk17.tar.gz -C "$JDK_DIR" --strip-components=1
  rm -f /tmp/jdk17.tar.gz
  export JAVA_HOME="$JDK_DIR"
}

# ───────────────────────────────────────────────────────────────
# 2) Android SDK
# ───────────────────────────────────────────────────────────────
install_android_sdk() {
  export ANDROID_HOME="$SDK_DIR"
  export ANDROID_SDK_ROOT="$SDK_DIR"
  mkdir -p "$SDK_DIR"

  # ── 1) Onde está o sdkmanager? ────────────────────────────────
  if ! command -v sdkmanager >/dev/null 2>&1; then
    if [[ -x "$SDK_DIR/cmdline-tools/latest/bin/sdkmanager" ]]; then
      echo "[i] cmdline-tools já presentes em $SDK_DIR"
    else
      say "Baixando Android command-line tools ($CMDLINE_TOOLS_VERSION)"
      mkdir -p "$SDK_DIR/cmdline-tools"
      curl -fL --retry 3 -o /tmp/cmdline-tools.zip \
        "https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS_VERSION}_latest.zip"
      rm -rf /tmp/cmdline-tools-unz && mkdir -p /tmp/cmdline-tools-unz
      unzip -q /tmp/cmdline-tools.zip -d /tmp/cmdline-tools-unz
      rm -rf "$SDK_DIR/cmdline-tools/latest"
      mv /tmp/cmdline-tools-unz/cmdline-tools "$SDK_DIR/cmdline-tools/latest"
      rm -rf /tmp/cmdline-tools.zip /tmp/cmdline-tools-unz
    fi
  fi

  export PATH="$SDK_DIR/cmdline-tools/latest/bin:$SDK_DIR/platform-tools:$SDK_DIR/build-tools/$BUILD_TOOLS:$PATH"

  # ── 2) Pacotes: instala só o que falta (nunca apaga o que existe) ──
  local installed
  installed="$(sdkmanager --list_installed 2>/dev/null || true)"

  need_pkgs=()
  grep -q "build-tools;$BUILD_TOOLS" <<< "$installed" || need_pkgs+=("build-tools;$BUILD_TOOLS")
  grep -q "platforms;android-$COMPILE_SDK" <<< "$installed" || need_pkgs+=("platforms;android-$COMPILE_SDK")
  grep -q "platform-tools" <<< "$installed" || need_pkgs+=("platform-tools")

  if [[ ${#need_pkgs[@]} -eq 0 ]]; then
    say "Android SDK completo (build-tools $BUILD_TOOLS, platform $COMPILE_SDK, platform-tools)"
  else
    say "Aceitando licenças do Android SDK"
    yes | sdkmanager --licenses >/dev/null 2>&1 || true
    say "Instalando pacotes faltantes: ${need_pkgs[*]}"
    sdkmanager --install "${need_pkgs[@]}" >/dev/null
  fi

  say "Componentes instalados:"
  sdkmanager --list_installed 2>/dev/null | sed 's/^/    /'
}

write_local_properties() {
  say "Gravando local.properties (sdk.dir)"
  echo "sdk.dir=$SDK_DIR" > "$PROJECT_DIR/local.properties"
}

persist_env_hints() {
  cat <<EOF

────────────────────────────────────────────────────────────
 Ambiente pronto. Para usar nesta sessão:

   export JAVA_HOME="$JAVA_HOME"
   export ANDROID_HOME="$SDK_DIR"
   export ANDROID_SDK_ROOT="$SDK_DIR"
   export PATH="\$JAVA_HOME/bin:\$ANDROID_HOME/platform-tools:\$ANDROID_HOME/build-tools/$BUILD_TOOLS:\$ANDROID_HOME/cmdline-tools/latest/bin:\$PATH"

 Build:
   ./gradlew assembleRelease
   # APK: app/build/outputs/apk/release/app-release.apk

 Ou simplesmente:
   ./tools/scripts/build-release.sh
────────────────────────────────────────────────────────────
EOF
  if [[ -n "${GITHUB_ENV:-}" ]]; then
    {
      echo "JAVA_HOME=$JAVA_HOME"
      echo "ANDROID_HOME=$SDK_DIR"
      echo "ANDROID_SDK_ROOT=$SDK_DIR"
      echo "PATH=$JAVA_HOME/bin:$SDK_DIR/cmdline-tools/latest/bin:$SDK_DIR/platform-tools:$SDK_DIR/build-tools/$BUILD_TOOLS:$PATH"
    } >> "$GITHUB_ENV"
  fi
}

install_base_pkgs
install_jdk
install_android_sdk
write_local_properties
persist_env_hints

say "Verificação final"
java -version 2>&1 | sed 's/^/    /'
"$SDK_DIR/build-tools/$BUILD_TOOLS/aapt2" version 2>/dev/null | sed 's/^/    aapt2 /' || true
"$SDK_DIR/build-tools/$BUILD_TOOLS/apksigner" --version | sed 's/^/    apksigner /' || true
echo "    ANDROID_HOME=$SDK_DIR"
