#!/usr/bin/env bash
# Valida no emulador as tres linhas da Home (conteudo real do Brazuca Play).
# Perfil sintetico + addon publico 2.1.4; nenhum dado pessoal e tocado.
set -uo pipefail
app=org.xbmc.kodi
out="${RUNNER_TEMP:?}/home-carrossel-smoke"
mkdir -p "$out"
mark=SMARTED_TEST_CARROSSEL
coleta() {
  adb exec-out screencap -p > "$out/tela-final.png" 2>/dev/null || true
  adb logcat -d -v brief > "$out/logcat.txt" 2>/dev/null || true
  adb shell "cat /sdcard/Android/data/$app/files/.kodi/temp/kodi.log" > "$out/kodi.log" 2>/dev/null || true
}
trap coleta EXIT

adb root >/dev/null 2>&1 || true
adb wait-for-device
adb logcat -G 16M || true
adb logcat -c
adb install -g "${RUNNER_TEMP:?}/home-carrossel-debug.apk" || { echo '::error::instalacao falhou'; exit 1; }
adb shell appops set "$app" MANAGE_EXTERNAL_STORAGE allow || true
adb shell am start -n "$app/.Splash" >/dev/null

pronto=0
for _ in $(seq 1 60); do
  adb logcat -d -s Kodi:V > "$out/kodi-logcat.txt" 2>/dev/null || true
  if grep -Eiq 'Loading skin file.*Home\.xml' "$out/kodi-logcat.txt"; then pronto=1; break; fi
  sleep 5
done
[ "$pronto" -eq 1 ] || { echo '::error::Home.xml nao carregou'; exit 1; }
sleep 20                       # deixa os widgets da Home resolverem a primeira vez
adb exec-out screencap -p > "$out/Home.png" 2>/dev/null || true

adb shell input keyevent 140   # F10 -> RunScript(home-carrossel-smoke.py)
resultado=0
for _ in $(seq 1 120); do
  adb logcat -d -s Kodi:V > "$out/kodi-logcat.txt" 2>/dev/null || true
  if grep -q "${mark}_OK" "$out/kodi-logcat.txt"; then resultado=1; break; fi
  if grep -q "${mark}_FAILED" "$out/kodi-logcat.txt"; then resultado=2; break; fi
  # dialogo de doacao do addon publico: responde "Nao" (botao padrao)
  if grep -q 'Loading skin file: DialogConfirm.xml' "$out/kodi-logcat.txt"; then
    sleep 3; adb shell input keyevent 66; adb logcat -c
  fi
  sleep 5
done

grep -E "$mark" "$out/kodi-logcat.txt" | sed 's/^.*Kodi: V //' | tail -40 || true
if [ "$resultado" -ne 1 ]; then
  echo "::error::carrossel da Home nao validou (codigo $resultado); ver artefatos"
  exit 1
fi
echo 'Linhas da Home abriram conteudo real do Brazuca Play no emulador.'
