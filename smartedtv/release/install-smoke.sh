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
# Um unico APK (rodada de finalizacao): nao ha mais arquivo de TV para testar.
# A versao de TV e o MESMO arquivo, decidindo o anuncio no aparelho por
# ``variante.py`` (e_tv()); o emulador API 30 e celular, entao aqui se prova o
# caminho AdMob. O caminho VAST tem cobertura automatizada em
# tests/test_ads_vast_tv.py.
adb shell dumpsys package "$pkg" > "$work/pacote-instalado.txt"
# Guardar o que o APARELHO leu do APK instalado: identidade/ABI em uso, para
# comparar com o badging do arquivo. É evidência, não suposição.
adb shell dumpsys package "$pkg" | grep -E "versionName|versionCode|primaryCpuAbi|codePath|targetSdk" \
  | head -8 | sed 's/^ *//' | tee "$work/instalado-resumo.txt"
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

# --- REABERTURA DO APP (tela preta / app saindo sozinho) --------------------
# Sair e abrir varias vezes seguidas (inclusive em segundos, com o processo
# ainda quente) tem de terminar sempre com o app vivo e com imagem na tela.
# Era exatamente aqui que aparecia "tela preta e fecha sozinho".
python3 -m pip install --quiet --disable-pip-version-check pillow >/dev/null 2>&1 || true
tela_preto() {
  python3 - "$1" <<'PY'
import sys
try:
    from PIL import Image, ImageStat
except Exception:
    print('sem pillow: checagem de brilho pulada')
    sys.exit(0)
media = ImageStat.Stat(Image.open(sys.argv[1]).convert('L')).mean[0]
print('brilho medio: %.1f' % media)
sys.exit(0 if media >= 8 else 1)
PY
}
componente_tv=$(adb shell cmd package resolve-activity --brief --user 0 \
  -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER \
  -p "$pkg" | tr -d '\r' | awk '$1 ~ /^smartedtv\.full\// {print $1}')
for ciclo in 1 2 3; do
  adb shell am force-stop "$pkg"
  sleep 1
  adb shell am start -W -n "$componente_tv" >/dev/null 2>&1 || true
  # 8 s: janela de boot desenhada -> tela de entrada -> Home
  sleep 8
  if ! adb shell pidof "$pkg" >/dev/null; then
    erro "reabertura $ciclo: o processo morreu ($(adb logcat -b crash -d -t 12))"
  fi
  adb exec-out screencap -p > "$work/reabertura-$ciclo.png" 2>/dev/null || true
  if [ -s "$work/reabertura-$ciclo.png" ] && ! tela_preto "$work/reabertura-$ciclo.png"; then
    erro "reabertura $ciclo: tela preta (app vivo, mas sem desenho)"
  fi
  echo "::notice::reabertura $ciclo: app vivo e com imagem na tela"
done
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
# --- INSTALADOR PELO CAMINHO DO APP ----------------------------------------
# "Aplicativo nao instalado" sem abrir a barra de progresso acontece antes da
# tela do instalador: quem abre o file:// nao conseguiu ler o arquivo, ou nao
# ha atividade que atenda a intent. Aqui provamos o que da para provar no AVD.
# A permissao do arquivo baixado pelo app (chmod 644) e coberta pelos testes
# unitarios, porque run-as exige app debuggable e este APK e debuggable=false.
adtmp=/data/local/tmp/SMARTEDTV.apk
if adb push build/universal/SMARTEDTV-universal.apk "$adtmp" >/dev/null 2>&1; then
  echo "::notice::APK enviado ao aparelho: $adtmp"
else
  erro 'adb push do APK falhou'
fi
# O instalador le o arquivo pelo mesmo caminho de quem usa o botao Atualizar.
instalou=$(adb shell pm install -r -d "$adtmp" 2>&1 | tr -d '\r' ) || true
echo "$instalou" | tee "$work/install-do-app.txt"
grep -q 'Success' <<< "$instalou" || erro "instalador recusou o APK: $instalou"
echo '::notice::instalador (pm install -r -d) aceitou o APK do app'
# Ha atividade para abrir um .apk por file://? No AVD sem a UI do instalador
# isso pode nao existir; registra como aviso para nao mascarar o resto.
resolvido=$(adb shell cmd package resolve-activity --brief -a android.intent.action.VIEW \
  -d "file://$adtmp" -t application/vnd.android.package-archive 2>&1 | tr -d '\r') || true
if grep -q '/' <<< "$resolvido"; then
  echo "::notice::intent do instalador resolvida: $resolvido"
else
  echo "::warning::nenhuma atividade atende file:// no AVD (esperado sem a UI do instalador): $resolvido"
fi
adb shell rm -f "$adtmp" >/dev/null 2>&1 || true
if adb logcat -b crash -d | grep -E 'Process: smartedtv\.full,|>>> smartedtv\.full <<<' ; then
  erro 'Crash do SMARTEDTV no primeiro arranque'
fi
primary_clean=$(adb shell dumpsys package "$pkg" | sed -n 's/.*primaryCpuAbi=//p' | tr -d '\r')
echo "::notice::AVD API $(adb shell getprop ro.build.version.sdk | tr -d '\r'): atualização ($primary), instalação limpa ($primary_clean) e os dois launchers aprovados. ABIs do AVD: $abi"
