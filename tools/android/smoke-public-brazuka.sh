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
donation_answered=0
for _ in $(seq 1 100); do
  adb logcat -d -s Kodi:V > "$out/kodi-logcat.txt" || true
  if grep -q SMARTED_TEST_LOCAL_KODI_PLAYER_OK "$out/kodi-logcat.txt" && grep -q SMARTED_TEST_PUBLIC_BRAZUCA_LAUNCH_WIDGET_OK "$out/kodi-logcat.txt" && grep -q SMARTED_TEST_PUBLIC_BRAZUCA_CHANNEL_SEARCH_OK "$out/kodi-logcat.txt" && grep -q SMARTED_TEST_PUBLIC_BRAZUCA_TV_OK "$out/kodi-logcat.txt" && grep -q SMARTED_TEST_PUBLIC_BRAZUCA_SEARCH_RESULT_OK "$out/kodi-logcat.txt"; then success=1; break; fi
  if grep -q SMARTED_TEST_PUBLIC_BRAZUCA_MENUS_FAILED "$out/kodi-logcat.txt"; then break; fi
  # In the clean disposable profile Brazuca asks about an optional donation.
  # Its default focused button is No (control 10); respond like a user rather
  # than changing the add-on's behavior or touching any real profile.
  if [ "$donation_answered" -eq 0 ] && grep -q SMARTED_TEST_PUBLIC_BRAZUCA_SEARCH_RESULT_OK "$out/kodi-logcat.txt" && grep -q 'Loading skin file: DialogConfirm.xml' "$out/kodi-logcat.txt"; then
    sleep 3
    adb exec-out screencap -p > "$out/donation-dialog.png" || true
    adb shell input keyevent 66
    donation_answered=1
  fi
  sleep 5
done
if [ "$success" -ne 1 ]; then echo '::error::Public Brazuca menus did not complete; inspect isolated log.'; exit 1; fi
echo 'Public 2.1.4 addon opened menus and expanded a search result in Kodi. User backup and playback were not tested.'
