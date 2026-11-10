#!/bin/sh
# APK somente para testes: não usa a chave original do Kodi.
set -eu
[ "$#" -eq 1 ] || { echo "Uso: $0 /caminho/Kodi.for.Android.21.3.zip" >&2; exit 2; }
ROOT=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
CACHE="${KODE_BUILD_HOME:-$HOME/.cache/kode-build}"
JAVA="$CACHE/python/jdk4py/java-runtime/bin/java"
SIGNER="$CACHE/tools/apksigner.jar"
KEYSTORE="$CACHE/kode-test.jks"
[ -x "$JAVA" ] && [ -f "$SIGNER" ] || { echo 'Execute tools/kodi/setup.sh primeiro.' >&2; exit 1; }
mkdir -p "$CACHE" "$ROOT/artifacts"
[ -f "$KEYSTORE" ] || { echo "Chave de teste ausente: $KEYSTORE. Recupere a chave anterior; para um novo teste independente, execute tools/kodi/init-test-key.sh." >&2; exit 1; }
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PYTHONPATH="$CACHE/python${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT/tools/kodi/repack.py" "$1" "$TMP/unsigned.apk"
"$JAVA" -jar "$SIGNER" sign --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
    --ks-key-alias kode-test --v1-signing-enabled true --v2-signing-enabled true \
    --v3-signing-enabled true --v4-signing-enabled false \
    --out "$ROOT/artifacts/kodi-estuary-pb-teste.apk" "$TMP/unsigned.apk"
"$JAVA" -jar "$SIGNER" verify --verbose "$ROOT/artifacts/kodi-estuary-pb-teste.apk"
python3 "$ROOT/tools/kodi/verify-content.py" "$1" "$ROOT/artifacts/kodi-estuary-pb-teste.apk"
echo "APK de teste: $ROOT/artifacts/kodi-estuary-pb-teste.apk"
