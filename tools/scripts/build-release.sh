#!/bin/bash
# =============================================================================
# Script de build do APK release - SmartED-TV
# =============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
KEYSTORE="$PROJECT_DIR/release-keystore.jks"
KEY_ALIAS="smartedtv"
KEYSTORE_PASS="smartedtv123"
KEY_PASS="smartedtv123"

echo "============================================================"
echo "  Build APK Release - SmartED-TV"
echo "============================================================"
echo ""

# Verificar Java
if ! java -version 2>&1 | head -1 | grep -q "17\|openjdk"; then
    echo "[!] Java 17 não encontrado. Execute primeiro: ./tools/scripts/install-deps.sh"
    exit 1
fi

# Verificar Gradle Wrapper
if [ ! -f "$PROJECT_DIR/gradlew" ]; then
    echo "[!] gradlew não encontrado em $PROJECT_DIR"
    exit 1
fi

chmod +x "$PROJECT_DIR/gradlew"

# Gerar keystore de release se não existir
if [ ! -f "$KEYSTORE" ]; then
    echo "[+] Gerando keystore de release..."
    keytool -genkeypair -v \
        -keystore "$KEYSTORE" \
        -alias "$KEY_ALIAS" \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -storepass "$KEYSTORE_PASS" \
        -keypass "$KEY_PASS" \
        -dname "CN=SmartED-TV, OU=SmartED, O=SmartED-TV, L=Sao Paulo, S=SP, C=BR"
fi

# Fazer build do release
echo "[+] Fazendo build do APK release..."
cd "$PROJECT_DIR"
./gradlew assembleRelease

APK_PATH="$PROJECT_DIR/app/build/outputs/apk/release/app-release.apk"

if [ -f "$APK_PATH" ]; then
    echo ""
    echo "============================================================"
    echo "  BUILD CONCLUÍDO COM SUCESSO!"
    echo "============================================================"
    echo "APK: $APK_PATH"
    echo "Tamanho: $(du -h "$APK_PATH" | cut -f1)"
    echo ""
    echo "Para instalar no dispositivo:"
    echo "  adb install -r \"$APK_PATH\""
    echo ""
else
    echo "[!] APK não encontrado em $APK_PATH"
    exit 1
fi
