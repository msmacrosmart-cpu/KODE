#!/bin/sh
# Gera uma chave SOMENTE para uma instalação de teste nova.
# Não substitua a chave de uma instalação que você pretende atualizar.
set -eu
CACHE="${KODE_BUILD_HOME:-$HOME/.cache/kode-build}"
KEYTOOL="$CACHE/python/jdk4py/java-runtime/bin/keytool"
KEYSTORE="$CACHE/kode-test.jks"
[ -x "$KEYTOOL" ] || { echo 'Execute tools/kodi/setup.sh primeiro.' >&2; exit 1; }
[ ! -e "$KEYSTORE" ] || { echo "A chave já existe: $KEYSTORE. Não será substituída." >&2; exit 1; }
mkdir -p "$CACHE"
umask 077
"$KEYTOOL" -genkeypair -keystore "$KEYSTORE" -storepass android -keypass android \
    -alias kode-test -dname 'CN=KODE Test, OU=Development, O=KODE, C=BR' \
    -keyalg RSA -keysize 2048 -validity 10000
echo "Chave de teste criada em $KEYSTORE. Faça backup seguro fora do repositório."
