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
# D: perfil sem terceiros mas dex SEM troca (pin velho) -> isola o dex
import zipfile, shutil
m.executar('build/exp/base.apk', 'build/exp/D-tmp.apk', atualizar_origem=False)
with zipfile.ZipFile('build/exp/base.apk') as original, \
        zipfile.ZipFile('build/exp/D-tmp.apk') as saneado, \
        zipfile.ZipFile('build/exp/D.apk', 'w', allowZip64=True) as saida:
    for item in saneado.infolist():
        dados = saneado.read(item)
        if item.filename.endswith('.dex'):
            dados = original.read(item.filename)
        info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
        info.compress_type = item.compress_type
        info.external_attr = item.external_attr
        saida.writestr(info, dados)
m.ADDONS_DE_TERCEIROS = terceiros
print('variantes A e B geradas')
PY
cp "$work/base.apk" "$work/C.apk"

for v in A D C; do
  python3 tools/kodi/align-apk.py "$work/$v.apk" "$work/$v-al.apk" || { aviso "$v: alinhamento falhou"; continue; }
  "$bt/apksigner" sign --ks "$KODI_ANDROID_STORE_FILE" --ks-key-alias "$KODI_ANDROID_KEY_ALIAS" \
    --ks-pass env:KODI_ANDROID_STORE_PASSWORD --key-pass env:KODI_ANDROID_KEY_PASSWORD \
    --out "$work/$v-signed.apk" "$work/$v-al.apk" || { aviso "$v: assinatura falhou"; continue; }
  aviso "$v pronto: $(stat -c %s "$work/$v-signed.apk") bytes"
done

adb install "$work/base.apk" >/dev/null 2>&1 || aviso 'base nao instalou (segue)'
for v in A D C; do
  [ -f "$work/$v-signed.apk" ] || { aviso "$v: sem APK"; continue; }
  adb install -r "$work/$v-signed.apk" >/dev/null 2>&1 || aviso "$v: instalacao falhou"
  adb shell am force-stop smartedtv.full
  adb logcat -c
  adb shell am start -W -n smartedtv.full/.Splash >/dev/null 2>&1
  sleep 15
  pid=$(adb shell pidof smartedtv.full | tr -d '\r')
  if [ -z "$pid" ]; then
    adb logcat -d > "$work/logcat-$v.txt" 2>/dev/null || true
    adb logcat -b crash -d > "$work/crash-$v.txt" 2>/dev/null || true
    printf '%s\n' "== $v: crash ==" "$(cat "$work/crash-$v.txt" 2>/dev/null | tail -60)" > "$work/resumo-$v.txt"
    grep -iE "Error|Exception|NoClassDef|Rejecting|checksum|magic|failed|DexInv|--- END" "$work/logcat-$v.txt" | grep -viE "hidden method|hidden api" | head -25 | while read -r l; do aviso "$v logcat: $l"; done
    aviso "$v: MORREU -> $(adb logcat -b crash -d | grep -m6 -E 'NoClassDef|Caused by|FATAL|at smartedtv' | tr '\n' ' ' | cut -c1-600)"
  else
    aviso "$v: app vivo (pid $pid)"
    printf '== %s: app vivo (pid %s)\n' "$v" "$pid" > "$work/resumo-$v.txt"
    adb exec-out screencap -p > "$work/tela-$v.png" 2>/dev/null || true
  fi
done
for v in A D C; do
  [ -f "$work/resumo-$v.txt" ] && cat "$work/resumo-$v.txt"
done | tail -c 60000 > "$work/resumo-exp.txt"
bash tools/kodi/publicar-diag.sh "$work/resumo-exp.txt" || true
exit 0
