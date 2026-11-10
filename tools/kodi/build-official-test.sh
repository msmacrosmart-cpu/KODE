#!/bin/sh
# Reempacota APK oficial Kodi 21.3; reutiliza a chave de teste existente.
set -eu
[ "$#" -eq 1 ] || { echo "Uso: $0 /caminho/kodi-21.3.apk" >&2; exit 2; }
ROOT=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
CACHE="${KODE_BUILD_HOME:-$HOME/.cache/kode-build}"
JAVA="$CACHE/python/jdk4py/java-runtime/bin/java"
SIGNER="$CACHE/tools/apksigner.jar"
KEYSTORE="$CACHE/kode-test.jks"
[ -x "$JAVA" ] && [ -f "$SIGNER" ] || { echo 'Execute tools/kodi/setup.sh primeiro.' >&2; exit 1; }
[ -f "$KEYSTORE" ] || { echo 'Chave de teste ausente. Recupere a chave anterior antes de continuar.' >&2; exit 1; }
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# A assinatura é verificada antes de reempacotar; restringe a fonte ao certificado
# presente no pacote Kodi 21.3 inspecionado, e exige exatamente um signatário.
"$JAVA" -jar "$SIGNER" verify --verbose --print-certs "$1" >"$TMP/source-verify.txt"
grep -q '^Number of signers: 1$' "$TMP/source-verify.txt" || { echo 'Número de signatários inesperado.' >&2; exit 1; }
grep -qi '^Signer #1 certificate SHA-256 digest: f517b44b5db5e62a6c1ec55ba47526db7de0d61f6ba26a7987520e293499b8d5$' "$TMP/source-verify.txt" || { echo 'Certificado de origem diferente do Kodi inspecionado.' >&2; exit 1; }
PYTHONPATH="$CACHE/python${PYTHONPATH:+:$PYTHONPATH}" python3 "$ROOT/tools/kodi/repack-apk.py" "$1" "$TMP/unsigned.apk"
mkdir -p "$ROOT/artifacts"
"$JAVA" -jar "$SIGNER" sign --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
    --ks-key-alias kode-test --v1-signing-enabled true --v2-signing-enabled true \
    --v3-signing-enabled true --v4-signing-enabled false \
    --out "$ROOT/artifacts/kodi-estuary-pb-oficial-teste.apk" "$TMP/unsigned.apk"
"$JAVA" -jar "$SIGNER" verify --verbose --print-certs "$ROOT/artifacts/kodi-estuary-pb-oficial-teste.apk"
python3 "$ROOT/tools/kodi/verify-content.py" --apk "$1" "$ROOT/artifacts/kodi-estuary-pb-oficial-teste.apk"
echo "APK de teste: $ROOT/artifacts/kodi-estuary-pb-oficial-teste.apk"
