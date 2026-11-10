#!/bin/sh
# Reconstrói recursos Android + mantém motor e add-ons da entrada assinada.
set -eu
[ "$#" -eq 1 ] || { echo "Uso: $0 /caminho/kodi-21.3-Omega-arm64-v8a.apk" >&2; exit 2; }
ROOT=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
CACHE="${KODE_BUILD_HOME:-$HOME/.cache/kode-build}"
JAVA="$CACHE/python/jdk4py/java-runtime/bin/java"
SIGNER="$CACHE/tools/apksigner.jar"
APKTOOL="$CACHE/tools/apktool.jar"
KEYSTORE="$CACHE/smarted-tv-test.jks"
[ -x "$JAVA" ] && [ -f "$SIGNER" ] && [ -f "$APKTOOL" ] || { echo 'Execute tools/kodi/setup.sh primeiro.' >&2; exit 1; }
[ -f "$KEYSTORE" ] || { echo "Chave SMARTED-TV de teste ausente em $KEYSTORE. Restaure a chave anterior; não gere outra para uma instalação existente." >&2; exit 1; }
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
"$JAVA" -jar "$SIGNER" verify --verbose --print-certs "$1" > "$TMP/source-verify.txt"
grep -q '^Number of signers: 1$' "$TMP/source-verify.txt" || { echo 'Número de signatários inesperado.' >&2; exit 1; }
grep -qi '^Signer #1 certificate SHA-256 digest: f517b44b5db5e62a6c1ec55ba47526db7de0d61f6ba26a7987520e293499b8d5$' "$TMP/source-verify.txt" || { echo 'Certificado de origem diferente do Kodi inspecionado.' >&2; exit 1; }
export PYTHONPATH="$CACHE/python${PYTHONPATH:+:$PYTHONPATH}"
# Rejeita outras versões ou identidades antes da decodificação.
python3 - "$1" <<'PY'
import sys
from pyaxmlparser import APK
p=APK(sys.argv[1]); app=p.get_android_manifest_xml().find('application')
if (p.package,p.version_name,str(p.version_code)) != ('org.xbmc.kodi','21.3','2103000') or app is None or app.get('{http://schemas.android.com/apk/res/android}extractNativeLibs') != 'true':
    raise SystemExit('Entrada incompatível: esperado Kodi 21.3, extractNativeLibs=true')
PY
"$JAVA" -jar "$APKTOOL" d -s -f "$1" -o "$TMP/decoded"
python3 "$ROOT/tools/kodi/brand.py" "$TMP/decoded"
"$JAVA" -jar "$APKTOOL" b "$TMP/decoded" -o "$TMP/unaligned.apk"
python3 "$ROOT/tools/kodi/align-apk.py" "$TMP/unaligned.apk" "$TMP/aligned.apk"
"$JAVA" -jar "$SIGNER" sign --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
    --ks-key-alias smarted-tv-test --v1-signing-enabled true --v2-signing-enabled true \
    --v3-signing-enabled true --v4-signing-enabled false --out "$TMP/signed.apk" "$TMP/aligned.apk"
"$JAVA" -jar "$SIGNER" verify --verbose --print-certs "$TMP/signed.apk" > "$TMP/signed-verify.txt"
cat "$TMP/signed-verify.txt"
grep -qi "^Signer #1 certificate SHA-256 digest: 855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a$" "$TMP/signed-verify.txt" || { echo "Chave de assinatura não é a chave SMARTED-TV de teste esperada." >&2; exit 1; }
python3 "$ROOT/tools/kodi/verify-branded.py" "$1" "$TMP/signed.apk"
mkdir -p "$ROOT/artifacts"
cp "$TMP/signed.apk" "$ROOT/artifacts/SMARTED-TV-v1.0.15-arm64-teste.apk"
echo "APK de teste: $ROOT/artifacts/SMARTED-TV-v1.0.15-arm64-teste.apk"
