#!/bin/sh
# Ambiente de REEMPACOTAMENTO Linux x86_64 (não compila o Kodi do código-fonte).
set -eu
CACHE="${KODE_BUILD_HOME:-$HOME/.cache/kode-build}"
mkdir -p "$CACHE/python" "$CACHE/tools"
python3 -m pip install --disable-pip-version-check --target "$CACHE/python" --upgrade 'jdk4py==17.0.9.2' 'Pillow==11.3.0'
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
npm pack '@postar/apktool-node@0.3.4' --pack-destination "$TMP" >/dev/null
tar -xzf "$TMP/postar-apktool-node-0.3.4.tgz" -C "$TMP" package/lib/apksigner.jar
cp "$TMP/package/lib/apksigner.jar" "$CACHE/tools/apksigner.jar"
"$CACHE/python/jdk4py/java-runtime/bin/java" -jar "$CACHE/tools/apksigner.jar" version
printf 'Ferramentas instaladas em %s\n' "$CACHE"
