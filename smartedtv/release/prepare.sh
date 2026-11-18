#!/usr/bin/env bash
# Base da linha smartedtv.full (não é a linha org.xbmc.kodi). Não segue /latest.
set -euo pipefail
cd "$(dirname "$0")/../.."
work=${RELEASE_WORK:-$PWD/build/universal}
mkdir -p "$work"
sdk=${ANDROID_HOME:?Instale o Android SDK e defina ANDROID_HOME}
bt="$sdk/build-tools/35.0.0"
if [[ ! -x $bt/zipalign ]]; then
  "$sdk/cmdline-tools/latest/bin/sdkmanager" 'build-tools;35.0.0'
fi
for tool in zipalign aapt apksigner; do test -x "$bt/$tool"; done
java -version
"$bt/apksigner" version
# O content_hash do Dropbox é SHA-256 da concatenação dos hashes dos blocos
# de 4 MiB; este JKS de 2730 bytes tem um único bloco. Não transmite a chave.
python3 - <<'PY'
from hashlib import sha256
from pathlib import Path
p = Path('dropbox/smarted-tv-test.jks').read_bytes()
if len(p) != 2730 or sha256(sha256(p).digest()).hexdigest() != 'e30aa80e3d4c1c19842bf09b76ad41d99c2b05aae97dacb81abc60f2bf40cba0':
    raise SystemExit('JKS diferente do backup de teste conferido no Dropbox')
PY
base="$work/base-v22.apk"
if [[ ! -f $base ]]; then
  gh release download v1.0.87-universal-v22 -R msmacrosmart-cpu/KODE \
    --pattern SMARTEDTV-universal.apk --output "$base"
fi
printf '%s  %s\n' 18d95307a015d4e15d5d8b2c07d6f228a7a47c487b0c5891b9e55b4c5cccaaf0 "$base" | sha256sum -c -
"$bt/apksigner" verify --print-certs "$base" > "$work/base-cert.txt"
grep -F 'certificate SHA-256 digest: 855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a' "$work/base-cert.txt"
"$bt/aapt" dump badging "$base" > "$work/base-badging.txt"
grep -E "^(package:|sdkVersion:|targetSdkVersion:|native-code:|launchable-activity:|leanback-launchable-activity:|uses-feature:)" "$work/base-badging.txt"
