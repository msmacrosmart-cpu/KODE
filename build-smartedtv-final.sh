#!/usr/bin/env bash
# =============================================================================
# BUILD FINAL — SMARTEDTV com correção dos botões da tela VÍDEOS
# =============================================================================
# Este script compila o SMARTEDTV a partir do código-fonte do Kodi 21.3-Omega,
# incorporando as modificações da tela VÍDEOS (Assinar o VIP, Já tenho um código,
# Compartilhar o app, Enviar o link do app, Procurar atualização).
#
# PRÉ-REQUISITOS (ambiente com acesso à internet):
#   - Ubuntu 22.04+
#   - Java JDK 17 (com javac)
#   - Android SDK 34 + build-tools 33.0.1 + NDK 21.4.7075529
#   - CMake 3.22+
#   - Python 3.11 com Pillow
#   - ~20 GB de espaço em disco
#
# Saída: smartedtv/build/out/SMARTEDTV-21.4-arm64-v8a.apk
# =============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SMARTED_DIR="$PROJECT_DIR/smartedtv"
KODI_DIR="$PROJECT_DIR/kodi"
BUILD_DIR="$SMARTED_DIR/build"
OUT_DIR="$BUILD_DIR/out"
KODI_SRC="$BUILD_DIR/kodi-21.3-Omega"

export ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$HOME/android-sdk}"
export ANDROID_HOME="$ANDROID_SDK_ROOT"
export PATH="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH"
NDK_VERSION="21.4.7075529"
JOBS="${JOBS:-$(nproc)}"
LOG="$BUILD_DIR/build.log"

mkdir -p "$BUILD_DIR" "$OUT_DIR"
: > "$LOG"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# =============================================================================
# PASSO 0: Verificações de ambiente
# =============================================================================
log "PASSO 0: Verificando ambiente de build..."

for cmd in java javac cmake make python3 git curl unzip zip; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERRO: '$cmd' não encontrado. Instale antes de continuar."
    exit 1
  fi
done

if [ ! -d "$ANDROID_SDK_ROOT/ndk/$NDK_VERSION" ]; then
  echo "ERRO: NDK $NDK_VERSION não encontrado em $ANDROID_SDK_ROOT/ndk/"
  echo "  Rode: ./smartedtv/tools/setup-build-env.sh"
  exit 1
fi

python3 -c "import PIL" 2>/dev/null || {
  echo "ERRO: Pillow não encontrado. Instale: pip install Pillow==11.3.0"
  exit 1
}

log "  Java: $(java -version 2>&1 | head -1)"
log "  javac: $(javac -version 2>&1 | head -1)"
log "  cmake: $(cmake --version | head -1)"
log "  Python: $(python3 --version)"
log "  NDK: $NDK_VERSION (encontrado)"
log "  Espaço em disco: $(df -h "$BUILD_DIR" | awk 'NR==2{print $4}') livre"

# =============================================================================
# PASSO 1: Clonar Kodi 21.3-Omega
# =============================================================================
log "PASSO 1: Clonando Kodi 21.3-Omega do código-fonte..."

if [ ! -d "$KODI_SRC/.git" ]; then
  mkdir -p "$BUILD_DIR"
  git clone --depth 1 --branch 21.3-Omega https://github.com/xbmc/xbmc.git "$KODI_SRC" | tee -a "$LOG"
fi

COMMIT="$(git -C "$KODI_SRC" rev-parse HEAD)"
log "  Commit: $COMMIT"

# =============================================================================
# PASSO 2: Aplicar identidade SMARTEDTV
# =============================================================================
log "PASSO 2: Aplicando identidade visual SMARTEDTV..."

if grep -q 'app_name\">SMARTEDTV<' "$KODI_SRC/tools/android/packaging/xbmc/strings.xml.in" 2>/dev/null; then
  log "  Identidade já aplicada — reutilizando árvore"
else
  # Gerar recursos de marca
  python3 "$SMARTED_DIR/tools/make-brand-assets.py" | tee -a "$LOG"

  # Encontrar add-on de idioma pt-BR
  LANG_ADDON=""
  for cand in "$BUILD_DIR/lang/resource.language.pt_br" "$SMARTED_DIR/build/lang/resource.language.pt_br"; do
    if [ -d "$cand" ]; then LANG_ADDON="$cand"; break; fi
  done

  if [ -n "$LANG_ADDON" ]; then
    log "  Add-on pt-BR: $LANG_ADDON"
  else
    log "  AVISO: pt-BR não encontrado — APK sairá só com en_gb"
  fi

  # Aplicar patch de identidade
  LANG_ARGS=""
  [ -n "$LANG_ADDON" ] && LANG_ARGS="--language-addon $LANG_ADDON"
  python3 "$SMARTED_DIR/tools/patch-source.py" "$KODI_SRC" \
      --brand-dir "$SMARTED_DIR/out" $LANG_ARGS | tee -a "$LOG"
fi

# =============================================================================
# PASSO 3: Incorporar modificações da tela VÍDEOS na árvore do Kodi
# =============================================================================
log "PASSO 3: Incorporando modificações da tela VÍDEOS..."

# Copiar skin.novatv para o diretório de add-ons do Kodi
KODI_ADDONS_DIR="$KODI_SRC/addons"
mkdir -p "$KODI_ADDONS_DIR"

if [ -d "$KODI_DIR/skin.novatv" ]; then
  log "  Copiando skin.novatv para árvore do Kodi..."
  rm -rf "$KODI_ADDONS_DIR/skin.novatv"
  cp -r "$KODI_DIR/skin.novatv" "$KODI_ADDONS_DIR/skin.novatv"
  log "  skin.novatv incorporada ($(find "$KODI_ADDONS_DIR/skin.novatv" -type f | wc -l) arquivos)"
fi

# Copiar plugin.video.smarted para o diretório de add-ons do Kodi
if [ -d "$KODI_DIR/addons/plugin.video.smarted" ]; then
  log "  Copiando plugin.video.smarted para árvore do Kodi..."
  rm -rf "$KODI_ADDONS_DIR/plugin.video.smarted"
  cp -r "$KODI_DIR/addons/plugin.video.smarted" "$KODI_ADDONS_DIR/plugin.video.smarted"
  log "  plugin.video.smarted incorporado ($(find "$KODI_ADDONS_DIR/plugin.video.smarted" -type f | wc -l) arquivos)"
fi

log "  Modificações da tela VÍDEOS incorporadas com sucesso"

# =============================================================================
# PASSO 4: Compilar dependências Android
# =============================================================================
log "PASSO 4: Compilando dependências Android (tools/depends)..."

DEPENDS="$KODI_SRC/tools/depends"
PREFIX="$BUILD_DIR/xbmc-depends"
TARBALLS="$BUILD_DIR/tarballs"
mkdir -p "$PREFIX" "$TARBALLS"

if [ "${SKIP_DEPENDS:-0}" != "1" ] && [ ! -f "$DEPENDS/Makefile.include" ]; then
  log "  Executando bootstrap e configure..."
  (cd "$DEPENDS" && ./bootstrap) | tee -a "$LOG"
  (cd "$DEPENDS" && ./configure \
      --with-tarballs="$TARBALLS" \
      --host=aarch64-linux-android \
      --with-sdk-path="$ANDROID_SDK_ROOT" \
      --with-ndk-path="$ANDROID_SDK_ROOT/ndk/$NDK_VERSION" \
      --prefix="$PREFIX") | tee -a "$LOG"
fi

log "  Executando make -C tools/depends (pode demorar ~40 min)..."
make -C "$DEPENDS" -j"$JOBS" | tee -a "$LOG"

# =============================================================================
# PASSO 5: Compilar Kodi para arm64-v8a
# =============================================================================
log "PASSO 5: Compilando Kodi 21.3-Omega para arm64-v8a..."

KODI_BUILD="$BUILD_DIR/kodi-build"
make -C "$DEPENDS/target/cmakebuildsys" BUILD_DIR="$KODI_BUILD" | tee -a "$LOG"
make -C "$KODI_BUILD" -j"$JOBS" | tee -a "$LOG"

# =============================================================================
# PASSO 6: Empacotar e assinar o APK
# =============================================================================
log "PASSO 6: Empacotando e assinando o APK..."

DEFAULT_KEYSTORE="$PROJECT_DIR/dropbox/smarted-tv-test.jks"
export KODI_ANDROID_STORE_FILE="${KODI_ANDROID_STORE_FILE:-$DEFAULT_KEYSTORE}"
export KODI_ANDROID_STORE_PASSWORD="${KODI_ANDROID_STORE_PASSWORD:-android}"
export KODI_ANDROID_KEY_ALIAS="${KODI_ANDROID_KEY_ALIAS:-smarted-tv-test}"
export KODI_ANDROID_KEY_PASSWORD="${KODI_ANDROID_KEY_PASSWORD:-android}"

if [ ! -f "$KODI_ANDROID_STORE_FILE" ]; then
  echo "ERRO: Chave de assinatura não encontrada em $KODI_ANDROID_STORE_FILE"
  exit 1
fi

make -C "$KODI_BUILD" apk | tee -a "$LOG"

# Encontrar o APK gerado
APK_SOURCE="$(find "$KODI_BUILD" "$KODI_SRC" -maxdepth 2 -name '*arm64-v8a*.apk' \
              | grep -v 'unaligned\|unsigned\|intermediate' | head -1)"
[ -n "$APK_SOURCE" ] || { echo "ERRO: APK não encontrado após 'make apk'"; exit 1; }

log "  APK gerado: $APK_SOURCE"

VERSION_NAME="$(awk '/^VERSION_MAJOR/{a=$2} /^VERSION_MINOR/{b=$2} END{print a"."b}' "$KODI_SRC/version.txt")"
FINAL="$OUT_DIR/SMARTEDTV-${VERSION_NAME}-arm64-v8a.apk"
cp "$APK_SOURCE" "$FINAL"
( cd "$OUT_DIR" && sha256sum "$(basename "$FINAL")" > "$(basename "$FINAL").sha256" )

# =============================================================================
# PASSO 7: Verificação do APK
# =============================================================================
log "PASSO 7: Verificando APK..."

python3 "$SMARTED_DIR/tools/verify-apk.py" "$FINAL" | tee -a "$LOG"

{
  echo "# Relatório de build — SMARTEDTV"
  echo
  echo "- data: $(date -u +%FT%TZ)"
  echo "- origem: xbmc/xbmc 21.3-Omega commit $COMMIT"
  echo "- identidade: smartedtv/tools/patch-source.py"
  echo "- sdk: android-34 / build-tools 33.0.1 / ndk $NDK_VERSION"
  echo "- apk: \`$(basename "$FINAL")\` ($(stat -c%s "$FINAL") bytes)"
  echo "- sha256: $(cut -d' ' -f1 "$FINAL.sha256")"
  echo "- assinatura: $(basename "$KODI_ANDROID_STORE_FILE") alias $KODI_ANDROID_KEY_ALIAS"
  echo ""
  echo "## Modificações incorporadas:"
  echo "- kodi/skin.novatv/xml/MyVideos.xml (tela VÍDEOS com 6 itens)"
  echo "- kodi/skin.novatv/xml/Home.xml (item Vídeos na navegação)"
  echo "- kodi/addons/plugin.video.smarted/default.py (6 ações Android)"
  echo "- kodi/skin.novatv/resources/qrcode.png (QR Code sem moldura)"
  echo "- kodi/skin.novatv/language/resource.language.pt_br/strings.po (7 strings)"
} > "$OUT_DIR/build-report.txt"

cat "$OUT_DIR/build-report.txt"

log ""
log "============================================================"
log "  BUILD CONCLUÍDO COM SUCESSO"
log "============================================================"
log "APK: $FINAL"
log "SHA-256: $(cut -d' ' -f1 "$FINAL.sha256")"
log "Relatório: $OUT_DIR/build-report.txt"
log ""
log "Para instalar no dispositivo:"
log "  adb install -r $FINAL"
