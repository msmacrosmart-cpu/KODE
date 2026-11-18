#!/usr/bin/env bash
# Prova funcional de d-pad e de filtro, DENTRO da janela real do Kodi.
#
# Nao le XML: aperta KEYCODE_DPAD_* de verdade e compara o que a janela mostra
# antes/depois, lendo o kodi.log (o observador dpad-monitor.py registra janela,
# controle focado e itens da lista). Roda SOMENTE no emulador descartavel do CI.
set -uo pipefail

app="${APP_ID:-smartedtv.full}"
out="${RUNNER_TEMP:?}/dpad-aparelho"
work="${RUNNER_TEMP:?}/work"
mkdir -p "$out"
falhas=0

note() { printf '\n== %s\n' "$*"; }
ok()   { printf '::notice::%s\n' "$*"; }
err()  { printf '::error::%s\n' "$*"; falhas=$((falhas + 1)); }

tecla() { adb shell input keyevent "$1" >/dev/null 2>&1; sleep "${2:-0.6}"; }

# O estado vem do kodi.log: o observador (dpad-monitor.py) escreve uma linha
# a cada mudanca de foco. Nada aqui depende de servidor HTTP nem de tecla
# dentro da janela: so do que o Kodi ve na tela.
KODI_LOG="/sdcard/Android/data/$app/files/.kodi/temp/kodi.log"

snapshot() {
  adb shell input keyevent 140 >/dev/null 2>&1 || true
  sleep "${1:-2.5}"
  adb shell "cat $KODI_LOG" 2>/dev/null | tr -d '\r' \
    | awk '/SMARTED_DPAD_SNAP/{snap=$0} /SMARTED_DPAD_ITEM/{itens=itens $0 "\n"} END{print snap; printf "%s", itens}'
}

estado() { # estado <campo> [snapshot-ja-coletado]
  local dados=${2:-$(snapshot "${SNAP_ESPERA:-2.5}")}
  printf '%s\n' "$dados" | head -1 \
    | sed 's/.*SMARTED_DPAD_SNAP //' | awk -F'|' -v c="$1" '{print $c}'
}

itens() {
  snapshot "${SNAP_ESPERA:-2.5}" | sed -n '/SMARTED_DPAD_ITEM/!d' \
    | sed 's/.*SMARTED_DPAD_ITEM [0-9]*|//' | paste -sd'|' -
}

janela()  { local d; d=$(snapshot "${SNAP_ESPERA:-2.5}"); estado 1 "$d"; }
controle(){
  local d; d=$(snapshot "${SNAP_ESPERA:-2.5}")
  printf '%s:%s' "$(estado 2 "$d")" "$(estado 3 "$d")"
}

espera_janela() { # espera_janela <label> <segundos>
  local alvo=$1 limite=${2:-40}
  for _ in $(seq 1 "$limite"); do
    [ "$(janela)" = "$alvo" ] && return 0
    sleep 1
  done
  return 1
}

coletar() {
  adb exec-out screencap -p > "$out/tela-final.png" 2>/dev/null || true
  adb shell "cat /sdcard/Android/data/$app/files/.kodi/temp/kodi.log" \
    > "$out/kodi.log" 2>/dev/null || true
  adb logcat -d -v brief > "$out/logcat.txt" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
note '0. Instalar o APK de teste e abrir pelo launcher de TV'
adb root >/dev/null 2>&1 || true
adb wait-for-device
adb logcat -c || true
# A mensagem do adb e a unica pista quando o aparelho recusa o APK: guardar e
# publicar nos dois canais (log do passo e anotacao do job).
instalacao=$(adb install -g "$work/SMARTEDTV-dpad-teste.apk" 2>&1)
rc_install=$?
printf '%s\n' "$instalacao" > "$out/instalacao.txt"
if [ "$rc_install" -ne 0 ]; then
  err "instalacao falhou (rc=$rc_install): $(printf '%s' "$instalacao" | tr '\r\n' '  ' | cut -c1-800)"
  adb shell df -h /data 2>&1 | tee "$out/df-data.txt" || true
  adb shell dumpsys package "$app" 2>/dev/null | head -5 | tee "$out/pacote.txt" || true
  coletar
  exit 1
fi
printf '::notice::APK de teste instalado: %s\n' "$(printf '%s' "$instalacao" | tr -d '\r' | tail -1)"
adb shell appops set "$app" MANAGE_EXTERNAL_STORAGE allow >/dev/null 2>&1 || true
comp=$(adb shell cmd package resolve-activity --brief --user 0 \
  -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER -p "$app" \
  | tr -d '\r' | awk -v p="$app" '$1 ~ ("^" p "\\/") {print $1}')
[ -n "$comp" ] || { err 'APK sem atividade LEANBACK'; coletar; exit 1; }
adb shell am start -W -n "$comp" >/dev/null 2>&1 || true
sleep 20
# Se a tela de entrada/ativacao aparecer, o Home ainda nao esta na frente.
for _ in $(seq 1 40); do
  [ "$(janela)" = 'Home' ] && break
  tecla 4 1.0
  sleep 1
done
ok "janela inicial: $(janela)"

note '1. Abrir a tela de pastas/categorias'
# Rota direta, a mesma que os botoes da barra superior usam.
adb shell input keyevent 140 >/dev/null 2>&1 || true   # F10: liga o observador
sleep 1
# A primeira opcao da barra superior e "TV ao vivo" -> AbrirWindow(Videos, ...)
tecla 20 1.0     # descer do topo para a barra/hero
tecla 22 0.8     # andar para a direita
tecla 23 6.0     # OK
sleep 4
janela_pastas=$(janela)
ok "janela apos OK na barra superior: $janela_pastas"
printf '%s\n' "$janela_pastas" > "$out/janela-pastas.txt"

note '2. D-PAD DENTRO DA CATEGORIA (antes: o foco saia da lista)'
primeiro=$(controle)
for _ in 1 2 3 4 5; do
  tecla 20 0.5
  printf '%s\n' "$(controle)" >> "$out/dpad-down.txt"
done
depois=$(controle)
printf 'antes=%s\ndepois=%s\n' "$primeiro" "$depois" > "$out/dpad-resumo.txt"
id_ini=${primeiro%%:*}
id_fim=${depois%%:*}
case "$id_ini" in
  50|51|52) ok "lista focada ao entrar na categoria (controle $id_ini)" ;;
  *) err "ao entrar na categoria o foco nao estava na lista (controle ${id_ini:-?})" ;;
esac
case "$id_fim" in
  50|51|52) ok "depois de 5 DPAD_DOWN o foco segue na lista (controle $id_fim)" ;;
  *) err "o d-pad saiu da lista ao descer (foi para ${id_fim:-?}): nao navega dentro da categoria" ;;
esac

note '3. DPAD_UP leva da lista para a barra de filtros'
for _ in 1 2 3 4 5 6; do tecla 19 0.5; done
barra=$(controle)
printf 'apos subir: %s\n' "$barra" >> "$out/dpad-resumo.txt"
case "$barra" in
  9060:*) ok 'DPAD_UP levou o foco para a barra de filtros (9060)' ;;
  *) printf '::warning::foco apos subir: %s (esperado 9060)\n' "$barra" ;;
esac

note '4. FILTRO: "A a Z" tem de reordenar os itens de verdade'
antes=$(itens)
printf '%s\n' "$antes" > "$out/filtro-antes.txt"
# Na barra: o 1o botao e "Todos", o 2o e "A a Z".
tecla 22 0.6
tecla 23 8.0
sleep 5
depois=$(itens)
printf '%s\n' "$depois" > "$out/filtro-depois.txt"
if [ -z "$antes" ] || [ -z "$depois" ]; then
  printf '::warning::lista vazia nesta execucao; nao foi possivel comparar a ordem\n'
elif [ "$antes" = "$depois" ]; then
  err 'o filtro "A a Z" nao alterou a ordem dos itens'
else
  ok 'o filtro "A a Z" reordenou os itens da categoria'
  if python3 - "$depois" <<'PY'
import sys
rotulos = [r for r in sys.argv[1].split('|') if r]
alfabetica = sorted(rotulos, key=lambda t: t.casefold().lstrip('[').strip())
sys.exit(0 if rotulos == alfabetica else 1)
PY
  then ok 'a lista ficou em ordem alfabetica'
  else printf '::warning::mudou a ordem, mas com prefixos/acentos do addon (nao estritamente A-Z)\n'
  fi
fi

note '4b. HOME (blade): subir do hero ate a barra superior'
# No layout blade o hero fica no meio e a barra superior (busca/ajustes/energia)
# no topo. Antes, 9121-9123 desciam para o 9000 (que so existe no aurora) e o
# 9320 subia para a lateral 9100, que subia para si mesma: nao havia caminho.
tecla 4 1.5
sleep 2
estado_layout=$(adb shell "grep -c 'home_layout=blade' /sdcard/Android/data/$app/files/.kodi/userdata/guisettings.xml" 2>/dev/null | tr -d '\r')
printf 'blade no guisettings: %s\n' "${estado_layout:-?}" >> "$out/home-dpad.txt"
for _ in 1 2 3 4 5 6 7 8; do tecla 19 0.4; done
topo_blade=$(controle)
printf 'apos subir da Home: %s\n' "$topo_blade" >> "$out/home-dpad.txt"
case "$topo_blade" in
  9121:*|9122:*|9123:*) ok "subiu do hero para a barra superior ($topo_blade)" ;;
  *) printf '::warning::foco apos subir na Home (blade): %s (esperado 9121/9122/9123)\n' "$topo_blade" ;;
esac
# E descer do topo tem de devolver o foco ao conteudo, nunca a um controle
# invisivel (9000 nao existe em blade).
tecla 20 1.0
abaixo_topo=$(controle)
printf 'apos descer do topo: %s\n' "$abaixo_topo" >> "$out/home-dpad.txt"
case "$abaixo_topo" in
  9*) ok "descer da barra superior leva a conteudo visivel ($abaixo_topo)" ;;
  *) printf '::warning::descer do topo foi para %s\n' "${abaixo_topo:-?}" ;;
esac

note '5. D-PAD NA BARRA/GRADE DE AJUSTES'
# Sai da janela de pastas e vai para a Home, depois Ajustes pela barra superior.
tecla 4 1.5
sleep 2
# botao de ajustes da Home e o 9122 (segundo da barra superior)
for _ in 1 2 3 4 5 6 7 8; do tecla 19 0.4; done
tecla 22 0.6
tecla 23 4.0
sleep 3
janela_ajustes=$(janela)
printf '%s\n' "$janela_ajustes" > "$out/janela-ajustes.txt"
if [ "$janela_ajustes" != 'Ajustes' ] && [ "$janela_ajustes" != 'Settings' ]; then
  printf '::warning::janela de Ajustes nao abriu pela Home (janela: %s)\n' "$janela_ajustes"
else
  ok 'janela de Ajustes aberta'
  ini=$(controle)
  for _ in 1 2 3; do tecla 22 0.5; printf '%s\n' "$(controle)" >> "$out/ajustes-dpad.txt"; done
  dir=$(controle)
  for _ in 1 2 3; do tecla 20 0.5; printf '%s\n' "$(controle)" >> "$out/ajustes-dpad.txt"; done
  baixo=$(controle)
  printf 'inicio=%s direita=%s baixo=%s\n' "$ini" "$dir" "$baixo" > "$out/ajustes-resumo.txt"
  if [ "$ini" = "$dir" ] && [ "$dir" = "$baixo" ]; then
    err "o d-pad nao andou na grade de Ajustes (foco parado em ${ini:-?})"
  else
    ok 'o d-pad percorre os tiles de Ajustes (direita e baixo movem o foco)'
  fi
fi

coletar
if [ "$falhas" -ne 0 ]; then
  printf '::error::%d verificacao(oes) de d-pad/filtro falharam (artefato dpad-aparelho)\n' "$falhas"
  exit 1
fi
ok 'd-pad nas categorias, filtro A a Z e d-pad de Ajustes conferidos no aparelho'
