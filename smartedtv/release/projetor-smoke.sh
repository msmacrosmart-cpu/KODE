#!/usr/bin/env bash
# Executa NO EMULADOR DE PROJETOR da CI (AVD leanback, sem toque).
#
# O que este script faz e diferente do install-smoke.sh: aqui o objetivo e ver
# o Kodi do projetor COMECAR, abrir a Home e escrever o kodi.log - e depois ler
# esse log. Foi assim que o cliente viu, no projetor Magicubic, notificacao de
# addon com erro antes da Home e Home sem dados. Sem o log do Kodi nao ha prova
# nenhuma; so opiniao.
set -euo pipefail
cd "$(dirname "$0")/../.."
work=${RELEASE_WORK:-$PWD/build/universal}
pkg=smartedtv.full
avd_tipo=$(adb shell getprop ro.build.characteristics | tr -d '\r')
echo "::notice::aparelho do teste: characteristics=$avd_tipo api=$(adb shell getprop ro.build.version.sdk | tr -d '\r')"

erro() { printf '::error::%s\n' "$(printf '%s' "$*" | tr '\r\n' '  ' | cut -c1-900)"; exit 1; }
aviso() { printf '::notice::%s\n' "$(printf '%s' "$*" | tr '\r\n' '  ' | cut -c1-900)"; }

# 1) instalar o APK desta rodada
resultado=$(adb install -r "$work/SMARTEDTV-universal.apk" 2>&1) || erro "instalacao: $resultado"
grep -F 'Success' <<< "$resultado" || erro "instalacao sem Success: $resultado"
aviso 'APK instalado no emulador de projetor'

# 2) abrir como a TV abre (LEANBACK_LAUNCHER), deixar o Kodi iniciar e desenhar
componente=$(adb shell cmd package resolve-activity --brief --user 0 \
  -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER \
  -p "$pkg" | tr -d '\r' | awk '$1 ~ /^smartedtv\.full\// {print $1}')
[[ -n $componente ]] || erro 'sem componente LEANBACK_LAUNCHER'
adb shell am force-stop "$pkg"
adb shell am start -W -n "$componente" >/dev/null 2>&1 || true

# O projetor e lento: espera o kodi.log aparecer no perfil do app, dentro do
# armazenamento externo do proprio pacote (mesma pasta que o Kodi usa).
log_remoto=$(adb shell 'ls -1 /sdcard/Android/data/smartedtv.full/files/.kodi/temp/kodi.log 2>/dev/null' | tr -d '\r' | head -1)
if [[ -z $log_remoto ]]; then
  log_remoto=$(adb shell 'ls -1 /sdcard/Android/data/smartedtv.full/files/.kodi/userdata/kodi.log 2>/dev/null' | tr -d '\r' | head -1)
fi
for _ in $(seq 1 30); do
  [[ -n $log_remoto ]] && break
  sleep 4
  log_remoto=$(adb shell 'ls -1 /sdcard/Android/data/smartedtv.full/files/.kodi/temp/kodi.log 2>/dev/null' | tr -d '\r' | head -1)
done
if [[ -z $log_remoto ]]; then
  aviso 'kodi.log nao apareceu pelo adb; procurando pela pasta do perfil'
  adb shell 'find /sdcard/Android/data/smartedtv.full /data/data/smartedtv.full -name kodi.log 2>/dev/null' | tr -d '\r' | head -5 || true
  adb shell 'ls -la /sdcard/Android/data/smartedtv.full/files 2>/dev/null' | tr -d '\r' | head -20 || true
  erro 'sem kodi.log: o Kodi nao chegou a iniciar neste aparelho'
fi
aviso "kodi.log do aparelho: $log_remoto"

# 3) esperar a Home: o app escreve "pronto" ou liberou a Home; 90 s e teto de AVD
for _ in $(seq 1 18); do
  sleep 5
  if adb shell "grep -qE 'pronto apos|liberando a Home|Perfil existente preservado|Perfil inicial preparado' '$log_remoto'" 2>/dev/null; then
    break
  fi
done
sleep 10
adb shell pidof "$pkg" >/dev/null || erro "o app nao esta rodando depois do boot: $(adb logcat -b crash -d -t 20 | tr -d '\r')"
adb exec-out screencap -p > "$work/projetor-home.png" 2>/dev/null || true

# 4) trazer o log do aparelho e analisar DE VERDADE
adb pull "$log_remoto" "$work/kodi.log" >/dev/null 2>&1 || erro 'nao foi possivel copiar o kodi.log do aparelho'
wc -l "$work/kodi.log" | sed 's/^/linhas gravadas pelo Kodi: /'
# O Kodi reescreve o log quando reinicia; guarda tambem o rotativo anterior.
adb pull "${log_remoto%.log}.old.log" "$work/kodi-anterior.log" >/dev/null 2>&1 || true
grep -nE 'Add-on com erro|Failed to load addon|Unable to load addon|Perfil existente|Perfil inicial|liberando a Home|pronto apos|\[SmartAds\]|skin=' \
  "$work/kodi.log" | tail -40 | while IFS= read -r linha; do aviso "${linha}"; done

# 5) o perfil do aparelho TEM os addons que o Kodi viu? (o defeito do projetor)
adb shell "ls -1 /sdcard/Android/data/smartedtv.full/files/.kodi/addons 2>/dev/null" \
  | tr -d '\r' | sort > "$work/addons-no-aparelho.txt" || true
aviso "addons no perfil do aparelho: $(wc -l < "$work/addons-no-aparelho.txt")"
# Pasta de addon sem addon.xml = exatamente o que vira "Add-on com erro".
while IFS= read -r addon; do
  [[ -n $addon ]] || continue
  if ! adb shell "test -f /sdcard/Android/data/smartedtv.full/files/.kodi/addons/$addon/addon.xml" 2>/dev/null; then
    aviso "addon sem addon.xml no aparelho: $addon"
  fi
done < "$work/addons-no-aparelho.txt"

if ! python3 tools/kodi/analisar-kodi-log.py "$work/kodi.log"; then
  aviso 'analise do kodi.log falhou ao rodar (log ilegivel?)'
fi
aviso 'projetor: app iniciou, Home abriu e o kodi.log foi lido'
