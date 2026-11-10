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
adb install -g "$RUNNER_TEMP/novatv-debug.apk"
# API 30 requires this special app-op in addition to install -g. Without it
# Splash stays on its explanatory permission dialog and never starts Kodi.
adb shell appops set "$app" MANAGE_EXTERNAL_STORAGE allow
adb logcat -c
adb shell am start -n "$app/.Splash"
sleep 15
ready=0
for _ in $(seq 1 24); do
  adb shell "cat '$base/temp/kodi.log'" > "$out/current.log" 2>/dev/null || true
  if grep -Eiq 'Loading skin file.*Home.xml' "$out/current.log"; then ready=1; break; fi
  sleep 10
done
collect
if [ "$ready" -ne 1 ]; then
  echo '::error::Kodi did not report loading Home.xml before timeout; inspect the artifact.'
  exit 1
fi
if ! grep -iq 'skin.novatv' "$out/kodi.log"; then
  echo '::error::Kodi did not report NovaTV in the log.'
  exit 1
fi
cp "$out/screen.png" "$out/home.png"
# Install an emulator-only keymap, then restart so Kodi actually loads it.
adb root >/dev/null || true
adb wait-for-device
adb shell am force-stop "$app"
printf '%s\n' '<keymap><global><keyboard><f4>ActivateWindow(Settings)</f4><f5>ActivateWindow(InterfaceSettings)</f5></keyboard></global></keymap>' > "$out/keymap.xml"
adb shell mkdir -p "$base/userdata/keymaps"
adb push "$out/keymap.xml" "$base/userdata/keymaps/novatv-smoke.xml" >/dev/null
# adb root creates files owned by root; fix ownership to match the app directory.
adb shell "chown --reference='$base/userdata' '$base/userdata/keymaps/novatv-smoke.xml'" || true
adb shell chmod 644 "$base/userdata/keymaps/novatv-smoke.xml"
adb shell am start -n "$app/.Splash"
sleep 75
adb shell input keyevent 134
sleep 10
adb exec-out screencap -p > "$out/settings.png"
adb shell input keyevent 135
sleep 10
collect
cp "$out/screen.png" "$out/interface-settings.png"
if ! grep -Eiq 'Loading skin file.*SettingsCategory.xml' "$out/kodi.log"; then
  echo '::error::SettingsCategory.xml was not reported as loaded; inspect Kodi log and screenshots.'
  exit 1
fi
if grep -Ei 'FATAL EXCEPTION|UnsatisfiedLinkError|NoClassDefFoundError' "$out/logcat.txt" > "$out/fatal.txt"; then
  echo '::error::Potential fatal Android error; inspect the artifact.'
  exit 1
fi
printf '%s\n' 'NovaTV Home and settings files were loaded. Screenshots and logs still require review; this is not a playback or integration test.'
