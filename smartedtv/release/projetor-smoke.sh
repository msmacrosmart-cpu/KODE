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
avd_tipo=$(adb shell getprop ro.build.characteristics 2>/dev/null | tr -d '\r' || true)
etapa() { printf '::notice::etapa: %s\n' "$*"; }
echo "::notice::aparelho do teste: characteristics=$avd_tipo api=$(adb shell getprop ro.build.version.sdk | tr -d '\r')"

erro() { printf '::error::%s\n' "$(printf '%s' "$*" | tr '\r\n' '  ' | cut -c1-900)"; exit 1; }
aviso() { printf '::notice::%s\n' "$(printf '%s' "$*" | tr '\r\n' '  ' | cut -c1-900)"; }

# 1) instalar o APK desta rodada
resultado=$(adb install -r "$work/SMARTEDTV-universal.apk" 2>&1) || erro "instalacao: $resultado"
grep -F 'Success' <<< "$resultado" || erro "instalacao sem Success: $resultado"
etapa '1/5 APK instalado no aparelho'

# 2) abrir como a TV abre (LEANBACK_LAUNCHER), deixar o Kodi iniciar e desenhar
componente=$(adb shell cmd package resolve-activity --brief --user 0 \
  -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER \
  -p "$pkg" | tr -d '\r' | awk '$1 ~ /^smartedtv\.full\// {print $1}')
[[ -n $componente ]] || erro 'sem componente LEANBACK_LAUNCHER'
adb shell am force-stop "$pkg" >/dev/null 2>&1 || true
adb shell am start -W -n "$componente" >/dev/null 2>&1 || true
etapa "2/5 app aberto por LEANBACK_LAUNCHER ($componente); esperando o Kodi escrever o log"

# O projetor e lento: espera o kodi.log aparecer no perfil do app, dentro do
# armazenamento externo do proprio pacote (mesma pasta que o Kodi usa).
perfil=/sdcard/Android/data/smartedtv.full/files/.kodi
procurar_log() {
  for candidato in "$perfil/temp/kodi.log" \
                   "$perfil/userdata/kodi.log" \
                   "$perfil/temp/kodi.old.log"; do
    if adb shell "test -f '$candidato'" >/dev/null 2>&1; then
      printf '%s\n' "$candidato"
      return 0
    fi
  done
  return 1
}
log_remoto=""
for tentativa in $(seq 1 30); do
  log_remoto=$(procurar_log || true)
  [[ -n $log_remoto ]] && break
  sleep 4
done
if [[ -z $log_remoto ]]; then
  aviso 'kodi.log nao apareceu; o que existe no perfil do app:'
  adb shell "ls -la /sdcard/Android/data/smartedtv.full/files 2>/dev/null" 2>/dev/null | tr -d '\r' | head -20 || true
  adb shell "find /sdcard/Android/data/smartedtv.full -name 'kodi*.log' 2>/dev/null" 2>/dev/null | tr -d '\r' | head -5 || true
  aviso "processo do app: $(adb shell pidof $pkg 2>/dev/null | tr -d '\r' || echo nenhum)"
  aviso "ultimas linhas do logcat do app:"
  adb logcat -d -t 40 2>/dev/null | grep -iE "smartedtv|kodi|Python" | tail -20 | tr -d '\r' || true
  erro 'sem kodi.log: o Kodi nao chegou a iniciar neste aparelho'
fi
aviso "kodi.log do aparelho: $log_remoto"

# 3) esperar a Home: o app escreve "pronto" ou liberou a Home; 90 s e teto de AVD
for _ in $(seq 1 18); do
  sleep 5
  if adb shell "grep -qE 'pronto apos|liberando a Home|Perfil existente preservado|Perfil inicial preparado' '$log_remoto'" >/dev/null 2>&1; then
    break
  fi
done
etapa '3/5 Home liberada (ou tempo esgotado); lendo o log do aparelho' 
sleep 10
adb shell pidof "$pkg" >/dev/null || erro "o app nao esta rodando depois do boot: $(adb logcat -b crash -d -t 20 | tr -d '\r')"
adb exec-out screencap -p > "$work/projetor-home.png" 2>/dev/null || true

# 4) trazer o log do aparelho e analisar DE VERDADE
mkdir -p "$work"
adb pull "$log_remoto" "$work/kodi.log" >/dev/null 2>&1 || true
[[ -s "$work/kodi.log" ]] || erro 'nao foi possivel copiar o kodi.log do aparelho'
etapa '4/5 kodi.log copiado do aparelho'
wc -l "$work/kodi.log" | sed 's/^/linhas gravadas pelo Kodi: /'
# O Kodi reescreve o log quando reinicia; guarda tambem o rotativo anterior.
adb pull "${log_remoto%.log}.old.log" "$work/kodi-anterior.log" >/dev/null 2>&1 || true
grep -nE 'Add-on com erro|Failed to load addon|Unable to load addon|Perfil existente|Perfil inicial|liberando a Home|pronto apos|\[SmartAds\]|skin=' \
  "$work/kodi.log" | tail -40 | while IFS= read -r linha; do aviso "${linha}"; done

# 5) o perfil do aparelho TEM os addons que o Kodi viu? (o defeito do projetor)
{ adb shell "ls -1 $perfil/addons 2>/dev/null" 2>/dev/null | tr -d '\r' | sort > "$work/addons-no-aparelho.txt"; } || true
aviso "addons no perfil do aparelho: $(wc -l < "$work/addons-no-aparelho.txt")"
# Pasta de addon sem addon.xml = exatamente o que vira "Add-on com erro".
while IFS= read -r addon; do
  [[ -n $addon ]] || continue
  if ! adb shell "test -f $perfil/addons/$addon/addon.xml" >/dev/null 2>&1; then
    aviso "addon sem addon.xml no aparelho: $addon"
  fi
done < "$work/addons-no-aparelho.txt"

python3 tools/kodi/analisar-kodi-log.py "$work/kodi.log" || true
etapa '5/5 projetor: app iniciou, Home abriu e o kodi.log foi lido'
aviso "resumo: addons no perfil=$(wc -l < "$work/addons-no-aparelho.txt") linhas no log=$(wc -l < "$work/kodi.log")"
