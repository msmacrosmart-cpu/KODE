#!/usr/bin/env bash
# Fresh emulator, synthetic profile and disposable signature only.
set -euo pipefail
app=org.xbmc.kodi
out="${RUNNER_TEMP:?}/seed-smoke"
mkdir -p "$out"
collect() { adb logcat -d -v brief > "$out/logcat.txt" 2>/dev/null || true; adb exec-out screencap -p > "$out/screen.png" 2>/dev/null || true; }
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
# Exercise the actual bridge and video window; the Brazuka stub contains no real
# catalogue and exists only inside this discarded emulator candidate.
adb shell input keyevent 137  # F7 opens the bridge's series directory
opened=0
for _ in $(seq 1 24); do
  adb logcat -d -s Kodi:V > "$out/bridge-logcat.txt" || true
  if grep -Eiq 'Loading skin file.*MyVideoNav.xml' "$out/bridge-logcat.txt"; then opened=1; break; fi
  sleep 5
done
if [ "$opened" -ne 1 ]; then echo '::error::Video directory did not open.'; exit 1; fi
adb shell input keyevent 138  # F8 runs the JSON-RPC routing test fixture
bridge=0
for _ in $(seq 1 24); do
  adb logcat -d -s Kodi:V > "$out/bridge-logcat.txt" || true
  if grep -q 'SMARTED_TEST_BRIDGE_JSONRPC_OK' "$out/bridge-logcat.txt"; then bridge=1; break; fi
  if grep -q 'SMARTED_TEST_BRIDGE_JSONRPC_FAILED' "$out/bridge-logcat.txt"; then break; fi
  sleep 5
done
if [ "$bridge" -ne 1 ] || ! grep -q 'SMARTED_TEST_BRAZUCA_SERIES_OK' "$out/bridge-logcat.txt"; then
  echo '::error::Bridge routing fixture failed; inspect the synthetic log.'; exit 1
fi
# Real public indexes are queried, while the target add-on is still a stub.
adb logcat -c
adb shell input keyevent 139  # F9: start unified search
keyboard=0
for _ in $(seq 1 24); do
  adb logcat -d -s Kodi:V > "$out/keyboard-logcat.txt" || true
  if grep -q 'XBMCNativeKeyboard.show' "$out/keyboard-logcat.txt"; then keyboard=1; break; fi
  sleep 5
done
if [ "$keyboard" -ne 1 ]; then echo '::error::Native search keyboard was not shown.'; exit 1; fi
sleep 3
adb exec-out screencap -p > "$out/search-keyboard.png" || true
adb shell uiautomator dump /sdcard/smarted-window.xml >/dev/null
adb exec-out cat /sdcard/smarted-window.xml > "$out/search-window.xml"
# Click the actual native edit field and confirmation button instead of sending
# KEYCODE_ENTER (which does not trigger the IME_ACTION_DONE callback on all IMEs).
coords() {
  python3 - "$out/search-window.xml" "$1" <<'PY2'
import re, sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
for n in root.iter('node'):
    match = (sys.argv[2] == 'edit' and n.get('class') == 'android.widget.EditText') or (sys.argv[2] == 'ok' and n.get('resource-id') == 'android:id/button1')
    if match:
        nums = [int(x) for x in re.findall(r'\d+', n.get('bounds', ''))]
        if len(nums) == 4:
            print((nums[0] + nums[2]) // 2, (nums[1] + nums[3]) // 2)
            break
else:
    raise SystemExit('Native keyboard control missing')
PY2
}
adb shell input tap $(coords edit)
adb shell input text 'amor'
# The IME can cover the dialog's OK button. Hide the IME, then re-measure
# controls instead of tapping stale coordinates through the keyboard.
adb shell input keyevent 4
sleep 2
adb shell uiautomator dump /sdcard/smarted-window.xml >/dev/null
adb exec-out cat /sdcard/smarted-window.xml > "$out/search-window-after-input.xml"
cp "$out/search-window-after-input.xml" "$out/search-window.xml"
adb shell input tap $(coords ok)
search_ok=0
for _ in $(seq 1 36); do
  adb logcat -d -s Kodi:V > "$out/search-logcat.txt" || true
  if grep -q 'SMARTED_TEST_SEARCH_COMPLETED' "$out/search-logcat.txt"; then
    if grep -Eq 'SMARTED_TEST_SEARCH_COMPLETED results=[1-9][0-9]* failed=0' "$out/search-logcat.txt"; then search_ok=1; fi
    break
  fi
  sleep 5
done
if [ "$search_ok" -ne 1 ]; then echo '::error::Real-index search did not return complete results.'; exit 1; fi
adb exec-out screencap -p > "$out/search-results.png" || true
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
printf '%s\n' 'Synthetic profile, bridge, public-index search and existing-profile preservation passed. Playback and the actual Brazuka add-on remain untested.'
