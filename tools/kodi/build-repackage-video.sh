#!/usr/bin/env bash
# Reempacotamento RAPIDO do SMARTEDTV com tela VIDEOS.
# Nao compila o Kodi do zero. Reempacota o APK base existente.
set -uo pipefail

BASE_TAG="v1.0.83-tela-inicial-v9"
BASE_APK="SMARTEDTV-atual-com-tela-inicial-v9.apk"
NOVA_VERSAO="21.4.1"
TAG_SAIDA="smartedtv-videos-21.4.1-arm64"

log() { echo "[$(date +%H:%M:%S)] $*"; }

log "=== 1. Download APK base ==="
mkdir -p "$RUNNER_TEMP/base"
if ! gh release download "$BASE_TAG" -R "$GITHUB_REPOSITORY" \
  --pattern "$BASE_APK" --dir "$RUNNER_TEMP/base" 2>&1; then
  log "ERRO: falha ao baixar APK base da release $BASE_TAG"
  exit 1
fi
APK_FILE=$(find "$RUNNER_TEMP/base" -name '*.apk' | head -1)
if [ -z "$APK_FILE" ]; then
  log "ERRO: nenhum APK encontrado apos download"
  ls -la "$RUNNER_TEMP/base/"
  exit 1
fi
log "APK base: $APK_FILE"

log "=== 2. Instalar ferramentas ==="
sudo apt-get update -qq 2>/dev/null || true
sudo apt-get install -y -qq --no-install-recommends python3 python3-pip unzip zip curl openjdk-17-jdk-headless 2>/dev/null || true
python3 -m pip install --quiet --break-system-packages Pillow==11.3.0 pyaxmlparser==0.3.31 2>/dev/null || true
log "Ferramentas instaladas"

log "=== 3. Baixar apksigner.jar ==="
CACHE="$HOME/.cache/kode-build"
mkdir -p "$CACHE/tools"
SIGNER="$CACHE/tools/apksigner.jar"
if [ ! -f "$SIGNER" ]; then
  log "Baixando apksigner.jar do Maven Central..."
  if ! curl -fsSL -o "$SIGNER" \
    "https://repo1.maven.org/maven2/com/google/android/apksigner/33.0.1/apksigner-33.0.1.jar" 2>&1; then
    log "ERRO: falha ao baixar apksigner.jar"
    exit 1
  fi
fi
if [ ! -f "$SIGNER" ]; then
  log "ERRO: apksigner.jar nao existe apos download"
  exit 1
fi
log "apksigner.jar: $SIGNER ($(stat -c%s "$SIGNER") bytes)"

log "=== 4. Injetar modificacoes da tela VIDEOS ==="
if ! python3 tools/kodi/injetar-videos.py \
  --apk "$APK_FILE" \
  --saida "$RUNNER_TEMP/bruto.apk" 2>&1; then
  log "ERRO: falha na injetacao de modificacoes"
  exit 1
fi
ls -lh "$RUNNER_TEMP/bruto.apk"

log "=== 5. Alinhar APK ==="
if ! python3 tools/kodi/align-apk.py "$RUNNER_TEMP/bruto.apk" "$RUNNER_TEMP/alinhado.apk" 2>&1; then
  log "ERRO: falha no alinhamento do APK"
  exit 1
fi
ls -lh "$RUNNER_TEMP/alinhado.apk"

log "=== 6. Assinar APK ==="
JAVA=$(find /usr -name java -type f 2>/dev/null | head -1)
if [ -z "$JAVA" ]; then
  JAVA=/usr/bin/java
fi
log "Usando Java: $JAVA"
if ! "$JAVA" -jar "$SIGNER" sign \
  --ks dropbox/smarted-tv-test.jks \
  --ks-pass pass:android \
  --key-pass pass:android \
  --ks-key-alias smarted-tv-test \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --v4-signing-enabled false \
  --out "$RUNNER_TEMP/assinado.apk" "$RUNNER_TEMP/alinhado.apk" 2>&1; then
  log "ERRO: falha na assinatura do APK"
  exit 1
fi
ls -lh "$RUNNER_TEMP/assinado.apk"

log "=== 7. Verificar assinatura ==="
"$JAVA" -jar "$SIGNER" verify --verbose --print-certs "$RUNNER_TEMP/assinado.apk" \
  | tee "$RUNNER_TEMP/verify.txt" 2>&1 || true
grep -qi "smarted-tv-test\|855de171" "$RUNNER_TEMP/verify.txt" && log "Assinatura OK" || log "AVISO: verifique o certificado"

log "=== 8. Copiar para final ==="
cp "$RUNNER_TEMP/assinado.apk" "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk"
sha256sum "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk" > "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk.sha256"
cat "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk.sha256"
ls -lh "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk"

log "=== 9. Publicar release ==="
if gh release view "$TAG_SAIDA" -R "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  gh release upload "$TAG_SAIDA" "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk" "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk.sha256" -R "$GITHUB_REPOSITORY" --clobber
else
  gh release create "$TAG_SAIDA" \
    "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk" \
    "SMARTEDTV-${NOVA_VERSAO}-arm64-v8a.apk.sha256" \
    -R "$GITHUB_REPOSITORY" --target "$GITHUB_SHA" \
    --title "SMARTEDTV ${NOVA_VERSAO} (arm64-v8a) - Tela VIDEOS" \
    --notes "SMARTEDTV ${NOVA_VERSAO} - tela VIDEOS com 6 acoes externas do Android.

Base: SMARTEDTV 1.0.83 (release ${BASE_TAG}), reempacotado sem recompilar o Kodi.
Apenas injecao de addons: skin.novatv, plugin.video.smarted, service.smarted.bootstrap.

- Tela VIDEOS personalizada (MyVideos.xml)
- 6 acoes: open_url (Cakto VIP), enter_code, show_qr (QR Code), share_link (ACTION_SEND), check_update, download_apk
- Application ID: org.xbmc.kodi (preservado)
- Assinatura: smarted-tv-test (atualiza o 1.0.83; nao atualiza Kodi oficial)
- SHA-256 no arquivo .sha256"
fi
log "Release: https://github.com/$GITHUB_REPOSITORY/releases/tag/$TAG_SAIDA"

log "=== CONCLUIDO ==="
