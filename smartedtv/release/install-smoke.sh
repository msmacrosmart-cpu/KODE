#!/usr/bin/env bash
# Executar SOMENTE no AVD descartável da CI, sem mudar proteções do aparelho.
set -euo pipefail
cd "$(dirname "$0")/../.."
. kodi/addons/service.smarted.bootstrap/smarted_release.py
work=${RELEASE_WORK:-$PWD/build/universal}
pkg=smartedtv.full
abi=$(adb shell getprop ro.product.cpu.abilist | tr -d '\r')
echo "AVD API $(adb shell getprop ro.build.version.sdk), ABIs: $abi"
[[ $abi == *arm* ]] || { echo '::error::imagem sem tradução ARM; não é um teste válido'; exit 1; }
install() {
  local result
  result=$(adb install "$@" 2>&1) || { echo "::error::Instalação: $result"; return 1; }
  grep -F 'Success' <<< "$result"
}
install "$work/base-v22.apk"
install -r "$work/SMARTEDTV-universal.apk"
adb shell dumpsys package "$pkg" > "$work/pacote-instalado.txt"
grep -E "versionCode=$VERSION_CODE([[:space:]]|$)|primaryCpuAbi=" "$work/pacote-instalado.txt"
grep -Fq "versionCode=$VERSION_CODE " "$work/pacote-instalado.txt"
for cat in LAUNCHER LEANBACK_LAUNCHER; do
  adb shell am force-stop "$pkg"
  result=$(adb shell am start -W -a android.intent.action.MAIN -c "android.intent.category.$cat" -p "$pkg")
  echo "$result"
  grep -Fq 'Status: ok' <<< "$result" || { echo "::error::Launcher $cat falhou: $result"; exit 1; }
  sleep 4
  adb shell pidof "$pkg" || { echo "::error::O processo encerrou depois de $cat"; exit 1; }
done
if adb logcat -b crash -d | grep -E 'Process: smartedtv\.full,|>>> smartedtv\.full <<<' ; then
  echo '::error::Crash do SMARTEDTV no primeiro arranque'; exit 1
fi
echo "::notice::AVD API $(adb shell getprop ro.build.version.sdk | tr -d '\r'): v22 instalada e atualizada via adb install -r; versão $VERSION_CODE. Os dois launchers abriram. ABIs do AVD: $abi"
