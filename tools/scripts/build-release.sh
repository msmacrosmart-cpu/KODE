#!/bin/bash
# =============================================================================
# Script de build do APK release - SmartED-TV
# Uso: ./tools/scripts/build-release.sh
# Pré-requisito: ./tools/scripts/setup-android-env.sh já executado
# =============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

KEYSTORE="$PROJECT_DIR/release-keystore.jks"
KEY_ALIAS="smartedtv"
KEYSTORE_PASS="${KEYSTORE_PASSWORD:-smartedtv123}"
KEY_PASS="${KEY_PASSWORD:-smartedtv123}"
BUILD_TOOLS_VERSION="${BUILD_TOOLS_VERSION:-35.0.0}"

echo "============================================================"
echo "  Build APK Release - SmartED-TV"
echo "============================================================"

# ── Ambiente ──
if [ -z "$JAVA_HOME" ] && [ -x "$PROJECT_DIR/.jdk17/bin/java" ]; then
    export JAVA_HOME="$PROJECT_DIR/.jdk17"
fi
if [ -n "$JAVA_HOME" ]; then export PATH="$JAVA_HOME/bin:$PATH"; fi

if ! command -v java >/dev/null 2>&1; then
    echo "[!] Java não encontrado. Rode: sudo bash tools/scripts/setup-android-env.sh"
    exit 1
fi
echo "[+] $(java -version 2>&1 | head -1)"

if [ -z "$ANDROID_HOME" ] && [ -d "$PROJECT_DIR/.android-sdk" ]; then
    export ANDROID_HOME="$PROJECT_DIR/.android-sdk"
fi
if [ -n "$ANDROID_HOME" ]; then
    export ANDROID_SDK_ROOT="$ANDROID_HOME"
    export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/$BUILD_TOOLS_VERSION:$PATH"
    echo "$ANDROID_HOME" > "$PROJECT_DIR/local.properties.tmp"
    echo "sdk.dir=$ANDROID_HOME" > "$PROJECT_DIR/local.properties"
    rm -f "$PROJECT_DIR/local.properties.tmp"
else
    echo "[!] Android SDK não encontrado (defina ANDROID_HOME)."
    exit 1
fi

# ── Keystore de release ──
if [ ! -f "$KEYSTORE" ]; then
    echo "[+] Gerando keystore de release..."
    keytool -genkeypair -v \
        -keystore "$KEYSTORE" \
        -alias "$KEY_ALIAS" \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -storepass "$KEYSTORE_PASS" -keypass "$KEY_PASS" \
        -dname "CN=SmartED-TV, OU=SmartED, O=SmartED-TV, L=Sao Paulo, S=SP, C=BR"
fi

chmod +x "$PROJECT_DIR/gradlew"

echo "[+] Fazendo build do APK release..."
./gradlew --no-daemon assembleRelease

APK_PATH="$PROJECT_DIR/app/build/outputs/apk/release/app-release.apk"

if [ -f "$APK_PATH" ]; then
    echo ""
    echo "============================================================"
    echo "  BUILD CONCLUÍDO COM SUCESSO!"
    echo "============================================================"
    echo "APK: $APK_PATH"
    echo "Tamanho: $(du -h "$APK_PATH" | cut -f1)"
    echo ""
    echo "Instalar no dispositivo:"
    echo "  adb install -r \"$APK_PATH\""
    echo ""
else
    echo "[!] APK não encontrado em $APK_PATH"
    exit 1
fi
