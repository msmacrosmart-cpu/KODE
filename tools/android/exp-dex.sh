#!/usr/bin/env bash
# Experimento: isola a causa do NoClassDefFoundError visto do APK 1.0.143 em diante.
#   base = v22 original
#   A    = perfil sem terceiros + pin trocado no dex (o que vai ao ar agora)
#   B    = perfil INTACTO, so o pin trocado no dex
#   C    = perfil intacto e dex intacto (so reescreve o zip)
# Cada variante e instalada e aberta; o log diz se o app sobreviveu.
set -uo pipefail
cd "$(dirname "$0")/../.."
aviso() { printf '::notice::%s\n' "$(printf '%s' "$*" | tr '\r\n' '  ' | cut -c1-700)"; }
PROJECT=$PWD . smartedtv/tools/test-signing-env.sh
bt="${ANDROID_HOME:?}/build-tools/35.0.0"
work=build/exp
mkdir -p "$work"
cp build/universal/base-v22.apk "$work/base.apk"

python3 - <<'PY'
import importlib.util as u
spec = u.spec_from_file_location('m', 'tools/kodi/sanear-perfil-embarcado.py')
m = u.module_from_spec(spec)
spec.loader.exec_module(m)
m.executar('build/exp/base.apk', 'build/exp/A.apk', atualizar_origem=False)
terceiros = m.ADDONS_DE_TERCEIROS
m.ADDONS_DE_TERCEIROS = ()
m.executar('build/exp/base.apk', 'build/exp/B.apk', atualizar_origem=False)
m.ADDONS_DE_TERCEIROS = terceiros
print('variantes A e B geradas')
PY
cp "$work/base.apk" "$work/C.apk"

for v in A B C; do
  python3 tools/kodi/align-apk.py "$work/$v.apk" "$work/$v-al.apk" || { aviso "$v: alinhamento falhou"; continue; }
  "$bt/apksigner" sign --ks "$KODI_ANDROID_STORE_FILE" --ks-key-alias "$KODI_ANDROID_KEY_ALIAS" \
    --ks-pass env:KODI_ANDROID_STORE_PASSWORD --key-pass env:KODI_ANDROID_KEY_PASSWORD \
    --out "$work/$v-signed.apk" "$work/$v-al.apk" || { aviso "$v: assinatura falhou"; continue; }
  aviso "$v pronto: $(stat -c %s "$work/$v-signed.apk") bytes"
done

adb install "$work/base.apk" >/dev/null 2>&1 || aviso 'base nao instalou (segue)'
for v in A B C; do
  [ -f "$work/$v-signed.apk" ] || { aviso "$v: sem APK"; continue; }
  adb install -r "$work/$v-signed.apk" >/dev/null 2>&1 || aviso "$v: instalacao falhou"
  adb shell am force-stop smartedtv.full
  adb logcat -c
  adb shell am start -W -n smartedtv.full/.Splash >/dev/null 2>&1
  sleep 15
  pid=$(adb shell pidof smartedtv.full | tr -d '\r')
  if [ -z "$pid" ]; then
    aviso "$v: MORREU -> $(adb logcat -b crash -d | grep -m1 -E 'NoClassDef|FATAL' | cut -c1-200)"
  else
    aviso "$v: app vivo (pid $pid)"
    adb exec-out screencap -p > "$work/tela-$v.png" 2>/dev/null || true
  fi
done
exit 0
