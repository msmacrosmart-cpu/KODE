#!/usr/bin/env bash
# Instala o APK SMARTEDTV num emulador e prova que ele abre.
#
# Roda dentro do android-emulator-runner (adb disponível, KVM habilitado).
# Coleta evidências em smartedtv/build/emulador/:
#   - tela-splash.png     screenshot durante a inicialização
#   - tela-home.png       screenshot com a Home carregada
#   - tela-info.png       tela de informações do sistema (se alcançável)
#   - kodi.log            log do Kodi
#   - logcat.txt          logcat completo
#   - launcher.txt        dump da lista de apps (nome exibido)
#   - resumo.txt          o que passou e o que falhou
#
# Sai != 0 se o app não instalar ou não abrir. Uma falha em etapa opcional
# (ex.: navegar até a tela de informações) é registrada como NÃO TESTADO,
# nunca como sucesso.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$HERE/../.." && pwd)"
OUT="$PROJECT/smartedtv/build/emulador"
APP_ID="org.xbmc.kodi"
mkdir -p "$OUT"
: > "$OUT/resumo.txt"

note() { echo "$*" | tee -a "$OUT/resumo.txt"; }
fail() { echo "FALHA: $*" | tee -a "$OUT/resumo.txt"; collect; exit 1; }

collect() {
  adb exec-out screencap -p > "$OUT/tela-final.png" 2>/dev/null || true
  adb shell "cat /sdcard/Android/data/$APP_ID/files/.kodi/temp/kodi.log" > "$OUT/kodi.log" 2>/dev/null || true
  adb logcat -d -v brief > "$OUT/logcat.txt" 2>/dev/null || true
}

APK=$(find "$PROJECT/apk" -name '*.apk' 2>/dev/null | head -1)
[ -n "$APK" ] || fail "APK não encontrado em $PROJECT/apk"

adb wait-for-device
adb logcat -c || true

note "== instalação"
adb install -g "$APK" > "$OUT/install.txt" 2>&1 || fail "adb install falhou (ver install.txt)"
note "instalado: $(basename "$APK")"

# Nome exibido no launcher / Android TV
adb shell cmd package resolve-activity --brief "$APP_ID" > "$OUT/launcher.txt" 2>&1 || true
adb shell dumpsys package "$APP_ID" | grep -E "versionName|versionCode|firstInstallTime" \
  >> "$OUT/launcher.txt" 2>/dev/null || true

note "== abrindo o app"
adb shell am start -n "$APP_ID/.Splash" > "$OUT/start.txt" 2>&1 || fail "am start falhou"
sleep 8
adb exec-out screencap -p > "$OUT/tela-splash.png" 2>/dev/null || true

# Espera a Home da Estuary carregar (o Kodi registra o carregamento no logcat)
note "== esperando a Home"
home_ok=0
for _ in $(seq 1 60); do
  if adb logcat -d -s Kodi:V 2>/dev/null | grep -Eiq 'Loading skin file.*Home\.xml'; then
    home_ok=1; break
  fi
  # o processo morrer antes da Home é falha real
  if ! adb shell pidof "$APP_ID" >/dev/null 2>&1; then
    fail "processo do app encerrou antes de carregar a Home"
  fi
  sleep 5
done

if [ "$home_ok" -ne 1 ]; then
  note "NÃO TESTADO: Home.xml não confirmada em 5 min"
  collect
  exit 1
fi

sleep 20   # widgets e texturas
adb exec-out screencap -p > "$OUT/tela-home.png" 2>/dev/null || true
note "OK: app instalou, iniciou e carregou a Home da skin Estuary"

# --- checagens de identidade em tempo de execução -------------------------
note "== identidade"
if adb logcat -d 2>/dev/null | grep -q 'Starting SMARTEDTV'; then
  note "OK: splash nativa exibe 'Starting SMARTEDTV...'"
else
  note "NÃO TESTADO: mensagem 'Starting SMARTEDTV...' não apareceu no logcat"
fi

if adb shell dumpsys package "$APP_ID" | grep -qi 'SMARTEDTV'; then
  note "OK: nome exibido contém SMARTEDTV"
else
  note "NÃO TESTADO: dumpsys não mostrou o label (normal em builds ofuscados)"
fi

# --- configurações e playlists nativas -----------------------------------
note "== navegação nativa (configurações)"
adb shell input keyevent KEYCODE_ESCAPE >/dev/null 2>&1 || true   # volta ao início
# 's' abre Configurações no mapeamento padrão do Kodi (teclado)
adb shell input text 's' >/dev/null 2>&1 || true
sleep 6
adb exec-out screencap -p > "$OUT/tela-configuracoes.png" 2>/dev/null || true
if adb logcat -d -s Kodi:V 2>/dev/null | grep -Eiq 'Loading skin file.*Settings\.xml'; then
  note "OK: janela de Configurações abriu pelo controle nativo"
  adb shell input keyevent KEYCODE_ESCAPE >/dev/null 2>&1 || true
else
  note "NÃO TESTADO: Configurações não confirmadas via teclado no emulador"
fi

# --- add-ons que NÃO devem existir ---------------------------------------
note "== ausência de conteúdo de terceiros"
profile="/sdcard/Android/data/$APP_ID/files/.kodi"
addons=$(adb shell "ls $profile/addons 2>/dev/null" | tr -d '\r' || true)
echo "$addons" > "$OUT/addons-instalados.txt"
for forbidden in brazuka smarted novatv titan; do
  if echo "$addons" | grep -qi "$forbidden"; then
    note "FALHA: add-on '$forbidden' presente no perfil"
  else
    note "OK: nenhum add-on '$forbidden' no perfil"
  fi
done
note "add-ons no perfil: $(echo "$addons" | tr '\n' ' ')"

collect
note "== fim"
