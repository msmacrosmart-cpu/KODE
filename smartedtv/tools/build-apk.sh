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
#     SMARTEDTV_BUILD_DIR  onde compilar        (padrão: smartedtv/build)
#                        Em CI use um disco com espaço (ex.: /mnt/smartedtv-build);
#                        na raiz do runner (73 GB, ~63 GB já ocupados) o build
#                        estoura o disco e o make falha.
#     KODI_SRC           fonte já clonado      (padrão: $BUILD/kodi-21.3-Omega)
#     JOBS               paralelismo           (padrão: nproc)
#     SKIP_DEPENDS       =1 pula as dependências (recompilar só o Kodi)
#     KODI_ANDROID_STORE_FILE / _STORE_PASSWORD / _KEY_ALIAS / _KEY_PASSWORD
#                        assinatura (padrão: chave de teste do próprio repositório)
set -euo pipefail

# Em CI, transforma a falha em uma anotação com a ÚLTIMA linha do log — sem isto
# o motivo real (um erro de compilador no meio de 50 min de saída) se perde.
on_error() {
  local rc=$?
  local logf="${LOG:-}"
  echo "---- falhou (exit $rc) ----" >&2
  if [ -n "$logf" ] && [ -f "$logf" ]; then
    echo "---- últimas 25 linhas de $logf ----" >&2
    tail -25 "$logf" >&2
    if [ -n "${GITHUB_ACTIONS:-}" ]; then
      # Publica sempre as últimas linhas, sem depender de casar padrão nenhum:
      # foi assim que um erro (ERRO: espaço insuficiente) passou despercebido.
      local tailtxt
      tailtxt=$(tail -6 "$logf" | tr '\n' '|' | tr -s ' ' | cut -c1-900)
      echo "::error::build-apk falhou (exit $rc). Fim do log: $tailtxt"
    fi
  elif [ -n "${GITHUB_ACTIONS:-}" ]; then
    echo "::error::build-apk falhou (exit $rc) antes de criar o log"
  fi
  exit $rc
}
trap on_error EXIT


HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$HERE/../.." && pwd)"
SMARTED="$PROJECT/smartedtv"
BUILD="${SMARTEDTV_BUILD_DIR:-$SMARTED/build}"
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
python3 -c 'import PIL' 2>/dev/null || {
  echo "Pillow ausente. Instale: python3 -m pip install Pillow==11.3.0" >&2; exit 1; }
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
  for cand in "$BUILD/lang/resource.language.pt_br" "$SMARTED/build/lang/resource.language.pt_br"; do
    [ -d "$cand" ] && { LANG_ADDON="$cand"; break; }
  done
  [ -n "$LANG_ADDON" ] || echo "AVISO: pt-BR não encontrado; o APK sairá só com en_gb" | tee -a "$LOG"
  run python3 "$SMARTED/tools/patch-source.py" "$KODI_SRC" \
      --brand-dir "$SMARTED/out" ${LANG_ADDON:+--language-addon "$LANG_ADDON"}
fi

# ---------------------------------------------------------------------------
# Espaço em disco: sem isto o make falha no meio da compilação com um erro de
# compilador enganoso (ex.: "No space left on device" dentro de um .o).
AVAIL_KB=$(df --output=avail "$BUILD" | tail -1 | tr -d ' ')
AVAIL_GB=$((AVAIL_KB / 1024 / 1024))
echo "espaço livre em $BUILD: ${AVAIL_GB} GB"
if [ "$AVAIL_GB" -lt 12 ]; then
  echo "ERRO: apenas ${AVAIL_GB} GB livres em $BUILD; são necessários >=12 GB." >&2
  echo "      Em CI, libere espaço antes (ver passo 'Libertar espaço em disco')." >&2
  exit 1
fi

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
AVAIL_KB=$(df --output=avail "$BUILD" | tail -1 | tr -d ' ')
AVAIL_GB=$((AVAIL_KB / 1024 / 1024))
echo "espaço livre após dependências: ${AVAIL_GB} GB"
if [ "$AVAIL_GB" -lt 8 ]; then
  echo "ERRO: apenas ${AVAIL_GB} GB livres após as dependências; o build do Kodi" >&2
  echo "      precisa de ~8 GB. Libere espaço ou use um runner maior." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
step "4. Configurar e compilar o Kodi para arm64-v8a"
KODI_BUILD="$BUILD/kodi-build"
run make -C "$DEPENDS/target/cmakebuildsys" BUILD_DIR="$KODI_BUILD"
run make -C "$KODI_BUILD" -j"$JOBS"

# ---------------------------------------------------------------------------
step "5. Empacotar e assinar o APK"
# A chave de teste do projeto é usada para manter a MESMA assinatura das
# instalações de teste anteriores (versionCode maior permite atualizar).
. "$SMARTED/tools/test-signing-env.sh"

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
