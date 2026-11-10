#!/usr/bin/env bash
# Only run on an isolated emulator. Logs contain personal data: never upload or
# print them; report only a small whitelist of aggregate observations.
set -euo pipefail
app=org.xbmc.kodi
adb install -g "$RUNNER_TEMP/private.apk" >/dev/null
adb shell appops set "$app" MANAGE_EXTERNAL_STORAGE allow
adb logcat -c
adb shell am start -n "$app/.Splash" >/dev/null
ok=0
for _ in $(seq 1 120); do
  adb logcat -d -v brief > "$RUNNER_TEMP/private-logcat.txt" 2>/dev/null || true
  if grep -Eiq 'Loading skin file.*Home.xml' "$RUNNER_TEMP/private-logcat.txt"; then ok=1; break; fi
  sleep 5
done
python3 - "$RUNNER_TEMP/private-logcat.txt" <<'PY'
from pathlib import Path
import re,sys
text=Path(sys.argv[1]).read_text(errors='replace')
for name,pattern in [('home',r'Loading skin file.*Home.xml'),('seed_ok',r'Perfil inicial preparado'),('profile_preserved',r'Perfil existente preservado'),('seed_error',r'Falha ao preparar perfil inicial'),('fatal_java',r'FATAL EXCEPTION'),('native_crash',r'Fatal signal \d+'),('out_of_memory',r'OutOfMemoryError'),('missing_class',r'NoClassDefFoundError'),('link_error',r'UnsatisfiedLinkError')]:
 print(name+'='+str(bool(re.search(pattern,text,re.I))).lower())
PY
if [ "$ok" -ne 1 ]; then echo '::error::Home não foi detectada em emulador isolado; logs privados não foram publicados.'; exit 1; fi
# Update over the existing private profile, with the same signing key.
adb shell am force-stop "$app"
if [ -f "$RUNNER_TEMP/private-upgrade.apk" ]; then adb install -r -g "$RUNNER_TEMP/private-upgrade.apk" >/dev/null; fi
adb logcat -c
adb shell am start -n "$app/.Splash" >/dev/null
ok=0
for _ in $(seq 1 120); do
  adb logcat -d -v brief > "$RUNNER_TEMP/private-restart-logcat.txt" 2>/dev/null || true
  if grep -Eiq 'Loading skin file.*Home.xml' "$RUNNER_TEMP/private-restart-logcat.txt"; then ok=1; break; fi
  sleep 5
done
if [ "$ok" -ne 1 ]; then echo '::error::Home não foi detectada ao reiniciar; logs privados não foram publicados.'; exit 1; fi
echo 'Home carregou em perfil isolado novo e após atualização no perfil existente; nenhuma informação do perfil foi publicada.'
