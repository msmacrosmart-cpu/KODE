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
erro() { printf '::error::%s\n' "$(printf '%s' "$*" | tr '\r\n' '  ' | cut -c1-900)"; exit 1; }
abrir() {
  local cat=$1 resolved component result
  # O launcher consulta MAIN + categoria e inicia o componente explícito.
  # am start apenas com -p é um intent implícito: exige CATEGORY_DEFAULT,
  # que os filtros LAUNCHER/LEANBACK_LAUNCHER não precisam declarar.
  resolved=$(adb shell cmd package resolve-activity --brief --user 0 \
    -a android.intent.action.MAIN -c "android.intent.category.$cat" -p "$pkg" | tr -d '\r')
  component=$(awk '$1 ~ /^smartedtv\.full\// {print $1}' <<< "$resolved")
  [[ -n $component ]] || erro "Sem componente para $cat: $resolved"
  adb shell am force-stop "$pkg"
  result=$(adb shell am start -W -n "$component" -a android.intent.action.MAIN -c "android.intent.category.$cat" 2>&1) || erro "$result"
  grep -Fq 'Status: ok' <<< "$result" || erro "Launcher $cat: $result"
  sleep 5
  if ! adb shell pidof "$pkg"; then
    erro "Processo encerrou depois de $cat: $(adb logcat -b crash -d -t 16)"
  fi
  echo "::notice::Aberto pelo $cat: $component. $(echo "$result" | tr '\r\n' '  ')"
}
primary=$(awk -F= '/primaryCpuAbi=/{gsub(/[[:space:]]/, "", $2);print $2;exit}' "$work/pacote-instalado.txt")
echo "::notice::v22 instalada e atualizada com adb install -r; versionCode=$VERSION_CODE; ABI selecionada: $primary"
abrir LAUNCHER
abrir LEANBACK_LAUNCHER
# Testar também instalação limpa. Se o tradutor oferecer ambas as ABIs,
# usar a outra, sem inventar suporte a uma ABI não anunciada pelo Android.
other=armeabi-v7a
[[ $primary != armeabi-v7a ]] || other=arm64-v8a
adb uninstall "$pkg"
if [[ ,$abi, == *,$other,* ]]; then
  install --abi "$other" "$work/SMARTEDTV-universal.apk"
else
  install "$work/SMARTEDTV-universal.apk"
fi
abrir LEANBACK_LAUNCHER
if adb logcat -b crash -d | grep -E 'Process: smartedtv\.full,|>>> smartedtv\.full <<<' ; then
  erro 'Crash do SMARTEDTV no primeiro arranque'
fi
primary_clean=$(adb shell dumpsys package "$pkg" | sed -n 's/.*primaryCpuAbi=//p' | tr -d '\r')
echo "::notice::AVD API $(adb shell getprop ro.build.version.sdk | tr -d '\r'): atualização ($primary), instalação limpa ($primary_clean) e os dois launchers aprovados. ABIs do AVD: $abi"
