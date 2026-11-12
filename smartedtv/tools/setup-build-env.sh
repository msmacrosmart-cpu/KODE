#!/usr/bin/env bash
# Prepara o ambiente de compilação do SMARTEDTV (Kodi 21.3-Omega -> Android arm64).
#
# Roda em Ubuntu 22.04+ (x86_64). Instala EXATAMENTE as versões que a
# docs/README.Android.md do Kodi 21.3 e o build de referência do projeto usam:
#   - JDK 17 (Temurin)
#   - Android SDK: platforms;android-34, build-tools;33.0.1
#   - NDK 21.4.7075529
#   - Gradle 8.3 (via wrapper do próprio Kodi)
#
# Nada é atualizado "por gosto": subir qualquer uma dessas versões quebra o build
# do Kodi 21.3 (o NDK 26+, por exemplo, removeu o toolchain que o Kodi usa).
#
# Uso:  ./smartedtv/tools/setup-build-env.sh
# Saída: relatório em smartedtv/build/env-report.txt
set -euo pipefail

ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$HOME/android-sdk}"
ANDROID_NDK_VERSION="${ANDROID_NDK_VERSION:-21.4.7075529}"
CMDLINE_TOOLS_VERSION="11076708"   # commandlinetools 12.0 (estável com sdkmanager)
REPORT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/build"
mkdir -p "$REPORT_DIR"

log() { printf '\n== %s\n' "$*"; }

log "1/6 Pacotes de sistema (dependências do Kodi, lista do README.Android)"
sudo apt-get update -qq
sudo apt-get install -y -qq \
  autoconf automake bison build-essential curl flex gawk git gperf \
  lib32stdc++6 lib32z1 lib32z1-dev libcurl4-openssl-dev unzip zip zlib1g-dev \
  libtool pkg-config cmake python3 python3-pip openjdk-17-jdk-headless

log "2/6 JDK 17"
java -version 2>&1 | head -3

log "3/6 Android SDK + cmdline-tools $CMDLINE_TOOLS_VERSION"
if [ ! -d "$ANDROID_SDK_ROOT/cmdline-tools/latest" ]; then
  mkdir -p "$ANDROID_SDK_ROOT/cmdline-tools"
  tmp="$(mktemp -d)"
  curl -fsSL -o "$tmp/tools.zip" \
    "https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS_VERSION}_latest.zip"
  unzip -q "$tmp/tools.zip" -d "$tmp/unpacked"
  mv "$tmp/unpacked/cmdline-tools" "$ANDROID_SDK_ROOT/cmdline-tools/latest"
  rm -rf "$tmp"
fi
export ANDROID_HOME="$ANDROID_SDK_ROOT"
export ANDROID_SDK_ROOT
export PATH="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH"

yes | sdkmanager --licenses >/dev/null 2>&1 || true

log "4/6 SDK/NDK nas versões do Kodi 21.3"
sdkmanager --install \
  "platform-tools" \
  "platforms;android-34" \
  "build-tools;33.0.1" \
  "ndk;${ANDROID_NDK_VERSION}" >/dev/null

test -d "$ANDROID_SDK_ROOT/ndk/${ANDROID_NDK_VERSION}" || {
  echo "NDK ${ANDROID_NDK_VERSION} não instalado" >&2; exit 1; }

log "5/6 Gradle (wrapper 8.3 vem do fonte do Kodi; apenas o cache é preparado)"
echo "Gradle é distribuído pelo wrapper em tools/android/packaging/gradlew (8.3)."
echo "O primeiro build baixa a distribuição para \$HOME/.gradle."

log "6/6 Relatório do ambiente"
{
  echo "# Ambiente de compilação SMARTEDTV"
  echo "gerado: $(date -u +%FT%TZ)"
  echo "host:   $(uname -srm)"
  echo
  echo "## Ferramentas"
  echo "gcc:        $(gcc --version | head -1)"
  echo "cmake:      $(cmake --version | head -1)"
  echo "make:       $(make --version | head -1)"
  echo "python3:    $(python3 --version)"
  echo "java:       $(java -version 2>&1 | head -1)"
  echo "javac:      $(javac -version 2>&1 | head -1)"
  echo "sdkmanager: $(sdkmanager --version 2>/dev/null | head -1)"
  echo
  echo "## SDK"
  echo "ANDROID_SDK_ROOT=$ANDROID_SDK_ROOT"
  echo "platforms:   $(ls "$ANDROID_SDK_ROOT/platforms" 2>/dev/null | tr '\n' ' ')"
  echo "build-tools: $(ls "$ANDROID_SDK_ROOT/build-tools" 2>/dev/null | tr '\n' ' ')"
  echo "ndk:         $(ls "$ANDROID_SDK_ROOT/ndk" 2>/dev/null | tr '\n' ' ')"
} | tee "$REPORT_DIR/env-report.txt"

log "Ambiente pronto. Relatório: $REPORT_DIR/env-report.txt"
