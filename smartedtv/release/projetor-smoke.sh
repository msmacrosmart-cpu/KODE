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
# -g: concede as permissoes declaradas na instalacao. Sem isso o motor do Kodi
# nao consegue escrever o perfil no armazenamento externo e nao inicia (foi o
# que aconteceu no primeiro run deste emulador).
adb shell settings put global hidden_api_policy 1 >/dev/null 2>&1 || true
resultado=$(adb install -r -g "$work/SMARTEDTV-universal.apk" 2>&1) || erro "instalacao: $resultado"
grep -F 'Success' <<< "$resultado" || erro "instalacao sem Success: $resultado"
# Acesso amplo ao armazenamento, como o aparelho do usuario tem depois de
# conceder a permissao na primeira abertura.
adb shell appops set "$pkg" MANAGE_EXTERNAL_STORAGE allow >/dev/null 2>&1 || true
adb shell pm grant "$pkg" android.permission.READ_EXTERNAL_STORAGE >/dev/null 2>&1 || true
adb shell pm grant "$pkg" android.permission.WRITE_EXTERNAL_STORAGE >/dev/null 2>&1 || true
# O shell nao le /sdcard/Android/data/... sem root (Android 11+). No emulador da
# CI o root e permitido e e o que permite ler o kodi.log do aparelho.
adb root >/dev/null 2>&1 || true
adb wait-for-device >/dev/null 2>&1 || true
sleep 2
etapa '1/5 APK instalado no aparelho'

# 2) abrir como a TV abre (LEANBACK_LAUNCHER), deixar o Kodi iniciar e desenhar
componente=$(adb shell cmd package resolve-activity --brief --user 0 \
  -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER \
  -p "$pkg" | tr -d '\r' | awk '$1 ~ /^smartedtv\.full\// {print $1}')
[[ -n $componente ]] || erro 'sem componente LEANBACK_LAUNCHER'
adb shell am force-stop "$pkg" >/dev/null 2>&1 || true
adb shell am start -W -n "$componente" >/dev/null 2>&1 || true
etapa "2/5 app aberto por LEANBACK_LAUNCHER ($componente); esperando o Kodi escrever o log"

# Onde o motor grava o perfil: este APK traz o Kodi com o diretorio do pacote
# antigo (org.xbmc.kodi) quando o armazenamento externo esta liberado; em
# outros aparelhos cai no pacote do proprio app. Nao adivinhar: procurar.
perfil=""
candidatos_de_perfil() {
  printf '%s\n' \
    /sdcard/Android/data/smartedtv.full/files/.kodi \
    /data/media/0/Android/data/smartedtv.full/files/.kodi \
    /sdcard/Android/data/org.xbmc.kodi/files/.kodi \
    /data/media/0/Android/data/org.xbmc.kodi/files/.kodi
}
# ``adb shell test -f`` nega leitura dentro de Android/data; o find como root
# acha o arquivo de verdade. Preferir o find.
procurar_log() {
  local achado
  achado=$(adb shell "find /sdcard/Android/data /data/media/0/Android/data -maxdepth 8 -name 'kodi.log' 2>/dev/null | head -1" 2>/dev/null | tr -d '\r' || true)
  if [[ -z $achado ]]; then
    achado=$(adb shell "find /data/data/smartedtv.full -maxdepth 8 -name 'kodi.log' 2>/dev/null | head -1" 2>/dev/null | tr -d '\r' || true)
  fi
  [[ -n $achado ]] || return 1
  perfil=${achado%/temp/kodi.log}
  printf '%s\n' "$achado"
}
log_remoto=""
for tentativa in $(seq 1 40); do
  log_remoto=$(procurar_log || true)
  [[ -n $log_remoto ]] && break
  sleep 4
done
if [[ -z $log_remoto ]]; then
  # Diagnostico: onde o motor gravou, o que o app escreveu e por que nao veio
  # o log. Vai para as anotacoes porque artefato do run nao baixa fora dele.
  adb root >/dev/null 2>&1 || true
  sleep 3
  diag="$work/diag-aparelho.txt"
  : > "$diag"
  { echo "### find kodi*.log"
    adb shell "find /sdcard/Android/data /data/data /data/media/0/Android/data -maxdepth 8 -name 'kodi*.log' 2>/dev/null"
    echo "### pacotes com dados no cartao"
    adb shell "ls -1 /sdcard/Android/data 2>/dev/null"
    for pacote in org.xbmc.kodi smartedtv.full; do
      echo "### $pacote /sdcard/Android/data/$pacote/files"
      adb shell "ls -la /sdcard/Android/data/$pacote/files 2>&1"
      echo "### $pacote /data/data/$pacote/files"
      adb shell "ls -la /data/data/$pacote/files 2>&1"
    done
  } 2>&1 | tr -d '\r' >> "$diag" || true
  adb logcat -d > "$work/logcat.txt" 2>/dev/null || true
  { echo "### logcat: SMARTED-TV / Kodi / python"
    grep -iE "SMARTED-TV|org.xbmc.kodi|Starting Kodi|kodi.log|python" "$work/logcat.txt" | tail -40
  } 2>&1 | tr -d '\r' >> "$diag" || true
  head -20 "$diag" | while IFS= read -r l; do aviso "diag: $l"; done
  echo '::notice::diagnostico completo publicado como comentario do commit (tools/kodi/publicar-diag.sh)' 
  erro 'sem kodi.log: o Kodi nao chegou a iniciar neste aparelho'
fi
aviso "kodi.log do aparelho: $log_remoto (perfil: $perfil)"

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
