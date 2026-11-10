#!/usr/bin/env bash
# Fresh emulator, synthetic profile and disposable signature only.
set -euo pipefail
app=org.xbmc.kodi
out="${RUNNER_TEMP:?}/seed-smoke"
mkdir -p "$out"
collect() { adb logcat -d -v brief > "$out/logcat.txt" 2>/dev/null || true; }
trap collect EXIT
adb root >/dev/null || true
adb wait-for-device
adb install -g "$RUNNER_TEMP/seed-debug.apk"
adb shell appops set "$app" MANAGE_EXTERNAL_STORAGE allow
adb logcat -c
adb shell am start -n "$app/.Splash"
first=0
for _ in $(seq 1 48); do
  adb logcat -d -s SMARTED-TV:I '*:S' > "$out/seed-log.txt" || true
  if grep -q 'Perfil inicial preparado' "$out/seed-log.txt"; then first=1; break; fi
  if grep -q 'Falha ao preparar perfil inicial' "$out/seed-log.txt"; then break; fi
  sleep 5
done
if [ "$first" -ne 1 ]; then echo '::error::Synthetic profile was not installed.'; exit 1; fi
base="/sdcard/Android/data/$app/files/.kodi"
# Verify a synthetic file was copied into Kodi's real data directory.
adb shell "cat '$base/userdata/smarted-seed-test.txt'" | tr -d '\r' | grep -Fx 'synthetic-seed-only'
# Wait for Kodi to initialize before a controlled restart.
ready=0
for _ in $(seq 1 48); do
  adb logcat -d -s Kodi:V > "$out/kodi-logcat.txt" || true
  if grep -Eiq 'Loading skin file.*Home.xml' "$out/kodi-logcat.txt"; then ready=1; break; fi
  sleep 5
done
if [ "$ready" -ne 1 ]; then echo '::error::Kodi did not reach Home after synthetic seeding.'; exit 1; fi
adb shell am force-stop "$app"
adb shell "echo preserved-profile > '$base/userdata/smarted-seed-test.txt'"
adb logcat -c
adb shell am start -n "$app/.Splash"
preserved=0
for _ in $(seq 1 36); do
  adb logcat -d -s SMARTED-TV:I '*:S' > "$out/restart-log.txt" || true
  if grep -q 'Perfil existente preservado' "$out/restart-log.txt"; then preserved=1; break; fi
  sleep 5
done
if [ "$preserved" -ne 1 ]; then echo '::error::Existing profile path not confirmed on restart.'; exit 1; fi
adb shell "cat '$base/userdata/smarted-seed-test.txt'" | tr -d '\r' | grep -Fx 'preserved-profile'
collect
if grep -Ei 'FATAL EXCEPTION|UnsatisfiedLinkError|NoClassDefFoundError' "$out/logcat.txt"; then
  echo '::error::Potential fatal error on restart.'; exit 1
fi
printf '%s\n' 'Synthetic fresh profile installed; existing profile preserved on restart. Not an update test or release APK.'
