#!/usr/bin/env bash
# Compila o SMARTEDTV a partir do código-fonte do Kodi 21.3-Omega (Android arm64).
#
# Este é o único comando necessário depois de ./setup-build-env.sh:
#
#     ./smartedtv/tools/build-apk.sh
#
# Saída:
#     smartedtv/build/out/SMARTEDTV-<versão>-arm64-v8a.apk
#     smartedtv/build/out/SMARTEDTV-<versão>-arm64-v8a.apk.sha256
#     smartedtv/build/out/build-report.txt
#
# Variáveis (todas opcionais):
#     KODI_VERSION_TAG   tag do Kodi           (padrão: 21.3-Omega)
#     KODI_SRC           fonte já clonado      (padrão: smartedtv/build/kodi-21.3-Omega)
#     JOBS               paralelismo           (padrão: nproc)
#     SKIP_DEPENDS       =1 pula as dependências (recompilar só o Kodi)
#     KODI_ANDROID_STORE_FILE / _STORE_PASSWORD / _KEY_ALIAS / _KEY_PASSWORD
#                        assinatura (padrão: chave de teste do próprio repositório)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$HERE/../.." && pwd)"
SMARTED="$PROJECT/smartedtv"
BUILD="$SMARTED/build"
OUT="$BUILD/out"
KODI_VERSION_TAG="${KODI_VERSION_TAG:-21.3-Omega}"
KODI_SRC="${KODI_SRC:-$BUILD/kodi-$KODI_VERSION_TAG}"
JOBS="${JOBS:-$(nproc)}"
LOG="$BUILD/build.log"
mkdir -p "$BUILD" "$OUT"
: > "$LOG"

# O commit exato usado como referência neste projeto (tag 21.3-Omega).
EXPECTED_COMMIT="a3a448d26b8d560a65655dab2cd122994dc4e146"

step() { printf '\n=== %s ===\n' "$*" | tee -a "$LOG"; }
run()  { "$@" 2>&1 | tee -a "$LOG"; }

: "${ANDROID_SDK_ROOT:=$HOME/android-sdk}"
export ANDROID_HOME="$ANDROID_SDK_ROOT"
export ANDROID_SDK_ROOT
NDK="${ANDROID_NDK_VERSION:-21.4.7075529}"
export PATH="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$PATH"

# ---------------------------------------------------------------------------
step "0. Verificações de ambiente"
for require in java javac cmake make python3 git curl unzip; do
  command -v "$require" >/dev/null || { echo "faltando: $require (rode setup-build-env.sh)" >&2; exit 1; }
done
test -d "$ANDROID_SDK_ROOT/ndk/$NDK" || {
  echo "NDK $NDK ausente em $ANDROID_SDK_ROOT/ndk (rode setup-build-env.sh)" >&2; exit 1; }
echo "java:  $(java -version 2>&1 | head -1)"
echo "cmake: $(cmake --version | head -1)"
echo "sdk:   $ANDROID_SDK_ROOT  ndk: $NDK"
echo "jobs:  $JOBS"

# ---------------------------------------------------------------------------
step "1. Código-fonte do Kodi $KODI_VERSION_TAG"
if [ ! -d "$KODI_SRC/.git" ]; then
  mkdir -p "$BUILD"
  run git clone --depth 1 --branch "$KODI_VERSION_TAG" https://github.com/xbmc/xbmc.git "$KODI_SRC"
fi
COMMIT="$(git -C "$KODI_SRC" rev-parse HEAD)"
echo "commit: $COMMIT" | tee -a "$LOG"
if [ "$COMMIT" != "$EXPECTED_COMMIT" ]; then
  echo "AVISO: commit $COMMIT difere da referência $EXPECTED_COMMIT." | tee -a "$LOG"
  echo "       (esperado só se a tag for atualizada de propósito)" | tee -a "$LOG"
fi

# Idempotência: se a identidade já foi aplicada, não reaplica (evita erro de âncora).
if grep -q 'app_name">SMARTEDTV<' "$KODI_SRC/tools/android/packaging/xbmc/strings.xml.in"; then
  echo "identidade SMARTEDTV já aplicada — reutilizando a árvore" | tee -a "$LOG"
elif [ "${SKIP_BRAND:-0}" = "1" ]; then
  echo "SKIP_BRAND=1 — a identidade já foi aplicada por outro passo" | tee -a "$LOG"
  grep -q 'app_name">SMARTEDTV<' "$KODI_SRC/tools/android/packaging/xbmc/strings.xml.in" \
    || { echo "SKIP_BRAND=1 mas a árvore NÃO está com a identidade aplicada" >&2; exit 1; }
else
  step "2. Identidade visual SMARTEDTV (artes oficiais + textos)"
  run python3 "$SMARTED/tools/make-brand-assets.py"
  LANG_ADDON=""
  if [ -d "$BUILD/lang/resource.language.pt_br" ]; then
    LANG_ADDON="$BUILD/lang/resource.language.pt_br"
  fi
  run python3 "$SMARTED/tools/patch-source.py" "$KODI_SRC" \
      --brand-dir "$SMARTED/out" ${LANG_ADDON:+--language-addon "$LANG_ADDON"}
fi

# ---------------------------------------------------------------------------
step "3. Dependências Android (tools/depends)"
DEPENDS="$KODI_SRC/tools/depends"
PREFIX="$BUILD/xbmc-depends"
TARBALLS="$BUILD/tarballs"
mkdir -p "$PREFIX" "$TARBALLS"
if [ "${SKIP_DEPENDS:-0}" != "1" ]; then
  if [ ! -f "$DEPENDS/Makefile.include" ]; then
    run bash -c "cd '$DEPENDS' && ./bootstrap"
    run bash -c "cd '$DEPENDS' && ./configure \
        --with-tarballs='$TARBALLS' \
        --host=aarch64-linux-android \
        --with-sdk-path='$ANDROID_SDK_ROOT' \
        --with-ndk-path='$ANDROID_SDK_ROOT/ndk/$NDK' \
        --prefix='$PREFIX'"
  fi
  run make -C "$DEPENDS" -j"$JOBS"
else
  echo "SKIP_DEPENDS=1 — usando dependências já compiladas em $PREFIX" | tee -a "$LOG"
fi
test -f "$PREFIX/lib/kodi/libkodi.so" || test -d "$PREFIX/share/kodi" || {
  echo "dependências incompletas em $PREFIX" >&2; exit 1; }

# ---------------------------------------------------------------------------
step "4. Configurar e compilar o Kodi para arm64-v8a"
KODI_BUILD="$BUILD/kodi-build"
run make -C "$DEPENDS/target/cmakebuildsys" BUILD_DIR="$KODI_BUILD"
run make -C "$KODI_BUILD" -j"$JOBS"

# ---------------------------------------------------------------------------
step "5. Empacotar e assinar o APK"
# A chave de teste do projeto é usada para manter a MESMA assinatura das
# instalações de teste anteriores (versionCode maior permite atualizar).
DEFAULT_KEYSTORE="$PROJECT/dropbox/smarted-tv-test.jks"
export KODI_ANDROID_STORE_FILE="${KODI_ANDROID_STORE_FILE:-$DEFAULT_KEYSTORE}"
export KODI_ANDROID_STORE_PASSWORD="${KODI_ANDROID_STORE_PASSWORD:-android}"
export KODI_ANDROID_KEY_ALIAS="${KODI_ANDROID_KEY_ALIAS:-smarted-tv-test}"
export KODI_ANDROID_KEY_PASSWORD="${KODI_ANDROID_KEY_PASSWORD:-android}"

if [ ! -f "$KODI_ANDROID_STORE_FILE" ]; then
  echo "chave ausente: $KODI_ANDROID_STORE_FILE" >&2
  echo "gere uma com tools/kodi/init-test-key.sh ou informe KODI_ANDROID_STORE_FILE" >&2
  exit 1
fi

run make -C "$KODI_BUILD" apk

# O packaging do Kodi copia o APK final como kodiapp-<cpu>-<buildtype>.apk
APK_SOURCE="$(find "$KODI_BUILD" "$KODI_SRC" -maxdepth 2 -name '*arm64-v8a*.apk' \
              | grep -v 'unaligned\|unsigned\|intermediate' | head -1)"
[ -n "$APK_SOURCE" ] || { echo "APK não encontrado após 'make apk'" >&2; exit 1; }
echo "APK gerado: $APK_SOURCE" | tee -a "$LOG"

VERSION_NAME="$(awk '/^VERSION_MAJOR/{a=$2} /^VERSION_MINOR/{b=$2} END{print a"."b}' "$KODI_SRC/version.txt")"
FINAL="$OUT/SMARTEDTV-${VERSION_NAME}-arm64-v8a.apk"
cp "$APK_SOURCE" "$FINAL"
( cd "$OUT" && sha256sum "$(basename "$FINAL")" > "$(basename "$FINAL").sha256" )

# ---------------------------------------------------------------------------
step "6. Verificação do APK"
run python3 "$SMARTED/tools/verify-apk.py" "$FINAL" | tee -a "$LOG"

{
  echo "# Relatório de build — SMARTEDTV"
  echo
  echo "- data: $(date -u +%FT%TZ)"
  echo "- origem: xbmc/xbmc \`$KODI_VERSION_TAG\` commit \`$COMMIT\`"
  echo "- identidade: smartedtv/tools/patch-source.py (artes oficiais do Dropbox)"
  echo "- sdk: android-34 / build-tools 33.0.1 / ndk $NDK / jdk $(java -version 2>&1 | head -1 | cut -d'"' -f2)"
  echo "- apk: \`$(basename "$FINAL")\` ($(stat -c%s "$FINAL") bytes)"
  echo "- sha256: $(cut -d' ' -f1 "$FINAL.sha256")"
  echo "- assinatura: $(basename "$KODI_ANDROID_STORE_FILE") alias $KODI_ANDROID_KEY_ALIAS"
} > "$OUT/build-report.txt"
cat "$OUT/build-report.txt" | tee -a "$LOG"

step "Concluído"
echo "APK: $FINAL"
