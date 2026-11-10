#!/usr/bin/env bash
# Public addon and synthetic profile only; APK is signed with a throwaway key.
set -euo pipefail
app=org.xbmc.kodi
out="${RUNNER_TEMP:?}/public-brazuka-smoke"
mkdir -p "$out"
collect() { adb logcat -d -v brief > "$out/logcat.txt" 2>/dev/null || true; adb exec-out screencap -p > "$out/screen.png" 2>/dev/null || true; }
trap collect EXIT
adb root >/dev/null || true
adb wait-for-device
adb install -g "$RUNNER_TEMP/public-debug.apk"
adb shell appops set "$app" MANAGE_EXTERNAL_STORAGE allow
adb logcat -c
adb shell am start -n "$app/.Splash"
ready=0
for _ in $(seq 1 48); do
  adb logcat -d -s Kodi:V > "$out/kodi-logcat.txt" || true
  if grep -Eiq 'Loading skin file.*Home.xml' "$out/kodi-logcat.txt"; then ready=1; break; fi
  sleep 5
done
if [ "$ready" -ne 1 ]; then echo '::error::Kodi Home did not load.'; exit 1; fi
adb shell input keyevent 140  # F10 invokes the isolated JSON-RPC test script
success=0
for _ in $(seq 1 60); do
  adb logcat -d -s Kodi:V > "$out/kodi-logcat.txt" || true
  if grep -q SMARTED_TEST_PUBLIC_BRAZUCA_TV_OK "$out/kodi-logcat.txt" && grep -q SMARTED_TEST_PUBLIC_BRAZUCA_SEARCH_RESULT_OK "$out/kodi-logcat.txt"; then success=1; break; fi
  if grep -q SMARTED_TEST_PUBLIC_BRAZUCA_MENUS_FAILED "$out/kodi-logcat.txt"; then break; fi
  sleep 5
done
if [ "$success" -ne 1 ]; then echo '::error::Public Brazuca menus did not complete; inspect isolated log.'; exit 1; fi
echo 'Public 2.1.4 addon opened menus and expanded a search result in Kodi. User backup and playback were not tested.'
