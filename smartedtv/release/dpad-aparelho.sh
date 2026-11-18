#!/usr/bin/env bash
# Dispara a prova de d-pad/filtro DENTRO do Kodi (tests/kodi/dpad-monitor.py,
# embarcado no APK de teste) e le o resultado no kodi.log.
#
# Antes este script apertava teclas pelo adb e tentava adivinhar a janela pelo
# que aparecia na tela: falhava por tempo/foco inicial, nao por defeito do app.
# Agora quem aperta as setas e o proprio Kodi (Action(Down/Up/Right/Select)) e
# quem le o foco e o JSON-RPC interno; aqui so disparamos e conferimos.
set -uo pipefail

app="${APP_ID:-smartedtv.full}"
out="${RUNNER_TEMP:?}/dpad-aparelho"
work="${RUNNER_TEMP:?}/work"
mkdir -p "$out"

note() { printf '\n== %s\n' "$*"; }
ok()   { printf '::notice::%s\n' "$*"; }
erro() { printf '::error::%s\n' "$*"; }

KODI_LOG="/sdcard/Android/data/$app/files/.kodi/temp/kodi.log"
ler_log() { adb shell "cat $KODI_LOG" 2>/dev/null | tr -d '\r'; }
coletar() {
  adb exec-out screencap -p > "$out/tela-final.png" 2>/dev/null || true
  ler_log > "$out/kodi.log" 2>/dev/null || true
  adb logcat -d -v brief > "$out/logcat.txt" 2>/dev/null || true
}

note '0. Instalar o APK de teste e abrir pelo launcher de TV'
adb root >/dev/null 2>&1 || true
adb wait-for-device
adb logcat -c || true
# A mensagem do adb e a unica pista quando o aparelho recusa o APK: publicar.
instalacao=$(adb install -g "$work/SMARTEDTV-dpad-teste.apk" 2>&1)
rc_install=$?
printf '%s\n' "$instalacao" > "$out/instalacao.txt"
if [ "$rc_install" -ne 0 ]; then
  erro "instalacao falhou (rc=$rc_install): $(printf '%s' "$instalacao" | tr '\r\n' '  ' | cut -c1-800)"
  coletar; exit 1
fi
ok "APK de teste instalado: $(printf '%s' "$instalacao" | tr -d '\r' | tail -1)"

adb shell appops set "$app" MANAGE_EXTERNAL_STORAGE allow >/dev/null 2>&1 || true
comp=$(adb shell cmd package resolve-activity --brief --user 0 \
  -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER -p "$app" \
  | tr -d '\r' | awk -v p="$app" '$1 ~ ("^" p "\\/") {print $1}')
[ -n "$comp" ] || { erro 'APK sem atividade LEANBACK'; coletar; exit 1; }
adb shell am start -W -n "$comp" >/dev/null 2>&1 || true

# O Kodi precisa terminar de subir (a tela de entrada/ativacao vem antes).
note '1. Esperar o Kodi aceitar teclas'
# O app demora a subir (boot do Kodi + tela de entrada). Enviar o F10 antes
# disso nao faz nada e a prova "nao termina" sem nunca ter comecado - foi o que
# aconteceu nas primeiras execucoes. Aqui o log e a propria prova: espera o
# kodi.log existir e o Kodi estar desenhando, depois dispara e confirma que o
# script comecou, reenviando se preciso.
pronto=0
for _ in $(seq 1 90); do
  if adb shell "[ -f $KODI_LOG ]" 2>/dev/null && [ "$(ler_log | wc -l)" -gt 20 ]; then
    pronto=1; break
  fi
  sleep 2
done
[ "$pronto" -eq 1 ] && ok 'kodi.log presente: o app esta rodando'   || ok 'kodi.log ainda curto/ausente; tentando mesmo assim'

note '2. Disparar a prova dentro do Kodi (F10)'
iniciou=0
for tentativa in $(seq 1 8); do
  adb shell input keyevent 140 >/dev/null 2>&1 || true   # 140 = KEYCODE_F10
  for _ in $(seq 1 15); do
    sleep 2
    if ler_log | grep -q 'SMARTED_PROVA_INICIO'; then iniciou=1; break; fi
  done
  [ "$iniciou" -eq 1 ] && { ok "prova iniciada na tentativa $tentativa"; break; }
  # Antes do Kodi aceitar teclas ele pode estar na tela de entrada: um BACK
  # ajuda a chegar na Home e o F10 e reenviado.
  adb shell input keyevent 4 >/dev/null 2>&1 || true
  sleep 3
done
if [ "$iniciou" -ne 1 ]; then
  erro 'a prova nao iniciou: o Kodi nao recebeu o F10 (SMARTED_PROVA_INICIO ausente)'
  coletar; exit 1
fi

note '2b. Esperar o fim da prova'
fim=0
for _ in $(seq 1 120); do
  sleep 4
  if ler_log | grep -q 'SMARTED_PROVA_FIM'; then fim=1; break; fi
done
ler_log > "$out/kodi.log"
if [ "$fim" -ne 1 ]; then
  erro 'a prova iniciou mas nao terminou (SMARTED_PROVA_FIM ausente)'
  coletar; exit 1
fi

note '3. Resultado'
grep 'SMARTED_PROVA ' "$out/kodi.log" | sed 's/.*SMARTED_PROVA //' | tee "$out/prova.txt"
resumo=$(grep 'SMARTED_PROVA_FIM' "$out/kodi.log" | tail -1 | sed 's/.*SMARTED_PROVA_FIM //')
ok "resumo: $resumo"
falhas=$(grep -c 'SMARTED_PROVA FAIL' "$out/kodi.log" || true)
grep 'SMARTED_PROVA_ANTES\|SMARTED_PROVA_DEPOIS' "$out/kodi.log" > "$out/filtro-ordens.txt" || true
coletar
if [ "${falhas:-0}" -ne 0 ]; then
  # Uma unica anotacao: inclui a linha de contexto (ids lidos do skin e o valor
  # cru de Control.HasFocus(50)) para que a falha seja diagnosticavel sem baixar
  # o artefato.
  contexto=$(grep 'SMARTED_PROVA_IDS\|categoria_abre' "$out/kodi.log" | tail -2 | sed 's/.*SMARTED_PROVA[A-Z_]* //' | paste -sd' ; ' - | cut -c1-420)
  detalhe=$(grep 'SMARTED_PROVA FAIL' "$out/kodi.log" | sed 's/.*FAIL //' | paste -sd'; ' - | cut -c1-380)
  erro "$falhas falharam: $detalhe | contexto: $contexto"
  exit 1
fi
ok 'd-pad nas categorias, filtro A a Z, d-pad de Ajustes e subida hero->barra superior conferidos no aparelho'
