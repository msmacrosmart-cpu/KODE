#!/usr/bin/env bash
# Reempacota o APK base SMARTEDTV injetando as modificacoes da tela VIDEOS
# e assinando com a chave do projeto.
#
# Uso: ./tools/kodi/build-repackage-video.sh
set -euo pipefail

BASE_TAG="v1.0.83-tela-inicial-v9"
BASE_APK="SMARTEDTV-atual-com-tela-inicial-v9.apk"
NOVA_VERSAO="21.4.1"
TAG_SAIDA="smartedtv-videos-21.4.1-arm64"

echo "=== 1. Download APK base ==="
mkdir -p "$RUNNER_TEMP/base"
gh release download "$BASE_TAG" -R "$GITHUB_REPOSITORY" \
  --pattern "$BASE_APK" --dir "$RUNNER_TEMP/base"
APK_FILE=$(find "$RUNNER_TEMP/base" -name '*.apk' | head -1)
echo "APK base: $APK_FILE"

echo "=== 2. Injetar modificacoes da tela VIDEOS ==="
python3 tools/kodi/injetar-videos.py \
  --apk "$APK_FILE" \
  --saida "$RUNNER_TEMP/bruto.apk"
ls -lh "$RUNNER_TEMP/bruto.apk"

echo "=== 3. Copiar para alinhado (pular align) ==="
cp "$RUNNER_TEMP/bruto.apk" "$RUNNER_TEMP/alinhado.apk"
ls -lh "$RUNNER_TEMP/alinhado.apk"

echo "=== 4. Instalar apksigner Python ==="
python3 -m pip install --quiet --break-system-packages apksigner 2>/dev/null || true

echo "=== 5. Assinar APK ==="
python3 -c "
from apksigner import ApkSigner
signer = ApkSigner(
    keystore='dropbox/smarted-tv-test.jks',
    keystore_pass='android',
    key_pass='android',
    key_alias='smarted-tv-test',
)
signer.sign('$RUNNER_TEMP/alinhado.apk', '$RUNNER_TEMP/assinado.apk')
print('APK assinado com sucesso')
"
ls -lh "$RUNNER_TEMP/assinado.apk"

echo "=== 6. Copiar para final ==="
cp "$RUNNER_TEMP/assinado.apk" "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk"
sha256sum "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk" > "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk.sha256"
cat "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk.sha256"
ls -lh "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk"

echo "=== 7. Publicar release ==="
if gh release view "$TAG_SAIDA" -R "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  gh release upload "$TAG_SAIDA" "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk" "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk.sha256" -R "$GITHUB_REPOSITORY" --clobber
else
  gh release create "$TAG_SAIDA" \
    "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk" \
    "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk.sha256" \
    -R "$GITHUB_REPOSITORY" --target "$GITHUB_SHA" \
    --title "SMARTEDTV ${NOVA_VERSAO} (arm64-v8a) - Video Screen"
fi
echo "Release publicada: https://github.com/$GITHUB_REPOSITORY/releases/tag/$TAG_SAIDA"

echo "=== CONCLUIDO ==="
