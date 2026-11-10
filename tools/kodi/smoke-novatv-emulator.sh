#!/usr/bin/env bash
# Isolated, fresh emulator only: no customer profile or signed release APK.
set -euo pipefail
out="${RUNNER_TEMP:?}/novatv-smoke"
mkdir -p "$out"
app=org.xbmc.kodi
base="/sdcard/Android/data/$app/files/.kodi"
collect() {
  adb exec-out screencap -p > "$out/screen.png" 2>/dev/null || true
  adb logcat -d -v brief > "$out/logcat.txt" 2>/dev/null || true
  adb shell "cat '$base/temp/kodi.log'" > "$out/kodi.log" 2>/dev/null || true
}
trap collect EXIT
adb root >/dev/null || true
adb wait-for-device
adb logcat -G 16M || true
adb install -g "$RUNNER_TEMP/novatv-debug.apk"
# API 30 requires this special app-op in addition to install -g. Without it
# Splash stays on its explanatory permission dialog and never starts Kodi.
adb shell appops set "$app" MANAGE_EXTERNAL_STORAGE allow
adb logcat -c
adb shell am start -n "$app/.Splash"
sleep 15
adb exec-out screencap -p > "$out/initial-splash.png" || true
ready=0
: > "$out/current.log"
for _ in $(seq 1 36); do
  # Some Android images place the profile under internal app data instead of
  # external files. Search both and fall back to the Kodi logcat tag.
  logpath=$(adb shell "find /sdcard/Android/data/$app/files /data/user/0/$app -name kodi.log 2>/dev/null | head -1" | tr -d '\r' || true)
  if [ -n "$logpath" ]; then
    base=${logpath%/temp/kodi.log}
    adb shell "cat '$logpath'" > "$out/current.log" 2>/dev/null || true
  fi
  adb logcat -d -s Kodi:V > "$out/kodi-logcat.txt" || true
  if grep -Eiq 'Loading skin file.*Home.xml' "$out/current.log" "$out/kodi-logcat.txt"; then ready=1; break; fi
  sleep 10
done
collect
if [ "$ready" -ne 1 ]; then
  echo '::error::Kodi did not report loading Home.xml before timeout; inspect the artifact.'
  exit 1
fi
if ! grep -iq 'skin.novatv' "$out/current.log" "$out/kodi-logcat.txt"; then
  echo '::error::Kodi did not report NovaTV in the log.'
  exit 1
fi
cp "$out/screen.png" "$out/home.png"
# F4/F5 are provided only by the emulator build's system keymap; this avoids
# adb-pushed profile files with the wrong SELinux label on Android 11.
adb shell input keyevent 134
sleep 10
adb exec-out screencap -p > "$out/settings.png"
adb shell input keyevent 135
sleep 10
collect
adb logcat -d -s Kodi:V > "$out/kodi-logcat.txt" || true
cp "$out/screen.png" "$out/interface-settings.png"
if ! grep -Eiq 'Loading skin file.*SettingsCategory.xml' "$out/kodi.log" "$out/kodi-logcat.txt"; then
  echo '::error::SettingsCategory.xml was not reported as loaded; inspect Kodi log and screenshots.'
  exit 1
fi
if grep -Ei 'FATAL EXCEPTION|UnsatisfiedLinkError|NoClassDefFoundError' "$out/logcat.txt" > "$out/fatal.txt"; then
  echo '::error::Potential fatal Android error; inspect the artifact.'
  exit 1
fi
# Return from InterfaceSettings through Settings to Home, then exercise the
# eight-click/two-visits unlock. The temporary app has no personal profile.
adb shell input keyevent 4
sleep 3
adb shell input keyevent 4
sleep 4
adb shell input keyevent 136  # F6: focus logo
sleep 2
for _ in $(seq 1 8); do adb shell input keyevent 66; sleep 0.5; done
check_unlock() {
  expected="$1"
  sleep 3
  adb shell "cat '$base/userdata/addon_data/skin.novatv/settings.xml'" > "$out/skin-state-$expected.xml"
  python3 - "$out/skin-state-$expected.xml" "$expected" <<'PY'
import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
settings = {x.get('id', '').lower(): (x.text or '').lower() for x in root.findall('.//setting')}
expected = sys.argv[2]
if expected == 'full':
    assert settings.get('smartedfullmode') == 'true', settings
else:
    assert settings.get('smartedunlock') == expected, settings
    assert settings.get('smartedfullmode', 'false') != 'true', settings
print('Unlock stage confirmed:', expected)
PY
}
check_unlock 8
adb shell input keyevent 134
sleep 3
adb shell input keyevent 4
check_unlock 9
adb shell input keyevent 134
sleep 3
adb shell input keyevent 4
check_unlock full
adb exec-out screencap -p > "$out/unlocked-home.png"
printf '%s\n' 'NovaTV Home, settings and unlock sequence loaded. Playback, real data and backup integration remain untested.'
