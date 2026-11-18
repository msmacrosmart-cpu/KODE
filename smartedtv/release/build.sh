#!/usr/bin/env bash
# Reempacota somente overlays + manifesto. O motor já compilado não muda.
set -euo pipefail
cd "$(dirname "$0")/../.."
PROJECT=$PWD
work=${RELEASE_WORK:-$PWD/build/universal}
bt="${ANDROID_HOME:?}/build-tools/35.0.0"
. kodi/addons/service.smarted.bootstrap/smarted_release.py
[[ $VERSION_NAME =~ ^[0-9]+\.[0-9]+\.[0-9]+$ && $VERSION_CODE =~ ^[0-9]+$ ]]
((VERSION_CODE > 2103077 && VERSION_CODE <= 2100000000)) || { echo 'versionCode precisa superar todas as versões até v22' >&2; exit 1; }
# Reutilizar as convenções de assinatura da linha de teste; nunca gerar chave.
. smartedtv/tools/test-signing-env.sh
base="$work/base-v22.apk"
final="$work/SMARTEDTV-universal.apk"
scratch=$(mktemp -d "$work/montagem.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
python3 tools/kodi/atualizar-apk-v17.py --apk "$base" --saida "$scratch/overlay.apk"
python3 tools/kodi/ajustar-versao-apk.py "$scratch/overlay.apk" "$scratch/raw.apk" \
  --de 1.0.87 --de-codigo 2103073 --para "$VERSION_NAME" --para-codigo "$VERSION_CODE" --min-sdk 26
"$bt/zipalign" -P 16 -f 4 "$scratch/raw.apk" "$scratch/aligned.apk"
"$bt/apksigner" sign --ks "$KODI_ANDROID_STORE_FILE" --ks-key-alias "$KODI_ANDROID_KEY_ALIAS" \
  --ks-pass env:KODI_ANDROID_STORE_PASSWORD --key-pass env:KODI_ANDROID_KEY_PASSWORD \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true --v4-signing-enabled false \
  --out "$scratch/signed.apk" "$scratch/aligned.apk"
"$bt/zipalign" -c -P 16 4 "$scratch/signed.apk"
"$bt/apksigner" verify "$scratch/signed.apk"
# A partir de API 26 o verificador normalmente pula o v1: testar também a faixa v1.
"$bt/apksigner" verify --min-sdk-version 21 --verbose --print-certs "$scratch/signed.apk" > "$work/signature.txt"
for scheme in 1 2 3; do grep -E "^Verified using v$scheme scheme .*: true$" "$work/signature.txt"; done
grep -Fx 'Number of signers: 1' "$work/signature.txt"
grep -F 'certificate SHA-256 digest: 855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a' "$work/signature.txt"
"$ANDROID_HOME/cmdline-tools/latest/bin/apkanalyzer" manifest print "$scratch/signed.apk" > "$work/manifest.xml"
python3 smartedtv/release/verify.py "$base" "$scratch/signed.apk" "$work/manifest.xml" "$VERSION_NAME" "$VERSION_CODE"
python3 tools/kodi/simular-boot-tela-entrada.py --apk "$scratch/signed.apk"
mv "$scratch/signed.apk" "$final"
sha256sum "$final"
