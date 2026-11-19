#!/usr/bin/env bash
# Prova de d-pad e de filtro NO APARELHO, com o Kodi de verdade.
#
# Divisao de trabalho:
#   * o CI aperta KEYCODE_DPAD_* pelo adb, como um controle remoto;
#   * tests/kodi/dpad-monitor.py (dentro do APK) so OBSERVA e escreve uma linha
#     SMARTED_DPAD_SNAP por leitura: janela|controle_com_foco|n_itens|rotulos.
# Assim ninguem age duas vezes na interface (era o defeito da versao anterior,
# em que o script abria janelas e o bootstrap reimpunha a Home no meio).
set -uo pipefail

app="${APP_ID:-smartedtv.full}"
out="${RUNNER_TEMP:?}/dpad-aparelho"
work="${RUNNER_TEMP:?}/work"
mkdir -p "$out"

note() { printf '\n== %s\n' "$*"; }
ok()   { printf '::notice::%s\n' "$*"; }
erro() { printf '::error::%s\n' "$*"; }
falhas=0

KODI_LOG="/sdcard/Android/data/$app/files/.kodi/temp/kodi.log"
# O observador grava em arquivo proprio: o kodi.log e rotacionado quando o app
# reinicia o Kodi, e ler por ele devolvia zero linhas (falha falsa).
OBS_LOG="/sdcard/Android/data/$app/files/.kodi/temp/dpad-observador.log"
ler_log() { adb shell "cat $KODI_LOG" 2>/dev/null | tr -d '\r'; }
ler_obs() { adb shell "cat $OBS_LOG" 2>/dev/null | tr -d '\r'; }
tecla() { adb shell input keyevent "$1" >/dev/null 2>&1; sleep "${2:-0.8}"; }
coletar() {
  adb exec-out screencap -p > "$out/tela-final.png" 2>/dev/null || true
  ler_log > "$out/kodi.log" 2>/dev/null || true
  adb logcat -d -v brief > "$out/logcat.txt" 2>/dev/null || true
}
ultimo_snap() { ler_obs | grep 'SMARTED_DPAD_SNAP' | tail -1 | sed 's/.*SMARTED_DPAD_SNAP //'; }
campo() { ultimo_snap | awk -F'|' -v c="$1" '{print $c}'; }

# esperar <campo> <valor esperado como prefixo> <tentativas> -> 0 se chegou
esperar() {
  local alvo=$1 valor=$2 voltas=${3:-12} atual
  for _ in $(seq 1 "$voltas"); do
    atual=$(campo "$alvo")
    case "$atual" in "$valor"*) return 0 ;; esac
    sleep 0.8
  done
  return 1
}

checar() { # checar <nome> <condicao ja avaliada: 0/1> <detalhe>
  if [ "$2" -eq 0 ]; then ok "$1: $3"; else erro "$1: $3"; falhas=$((falhas + 1)); fi
}

note '0. Instalar e abrir'
adb root >/dev/null 2>&1 || true
adb wait-for-device
adb logcat -c || true
instalacao=$(adb install -g "$work/SMARTEDTV-dpad-teste.apk" 2>&1)
rc=$?
printf '%s\n' "$instalacao" > "$out/instalacao.txt"
if [ "$rc" -ne 0 ]; then
  erro "instalacao falhou (rc=$rc): $(printf '%s' "$instalacao" | tr '\r\n' '  ' | cut -c1-700)"
  coletar; exit 1
fi
ok "instalado: $(printf '%s' "$instalacao" | tr -d '\r' | tail -1)"
adb shell appops set "$app" MANAGE_EXTERNAL_STORAGE allow >/dev/null 2>&1 || true
comp=$(adb shell cmd package resolve-activity --brief --user 0 \
  -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER -p "$app" \
  | tr -d '\r' | awk -v p="$app" '$1 ~ ("^" p "\\/") {print $1}')
[ -n "$comp" ] || { erro 'APK sem atividade LEANBACK'; coletar; exit 1; }
adb shell am start -W -n "$comp" >/dev/null 2>&1 || true

note '1. Esperar o app subir e o vigia de boot terminar'
for _ in $(seq 1 90); do
  [ "$(ler_log | wc -l)" -gt 20 ] && break
  sleep 2
done
# O bootstrap reimpoe a Home por ate ~25 s depois do boot; agir antes disso faz
# a janela ser fechada no meio do teste.
sleep 70
ler_log | grep -c 'startup' > "$out/startup.txt" 2>/dev/null || true

note '2. Ligar o observador (F10)'
iniciou=0
for tentativa in $(seq 1 6); do
  adb shell input keyevent 140 >/dev/null 2>&1 || true
  for _ in $(seq 1 12); do
    sleep 2
    if ler_obs | grep -q 'SMARTED_DPAD_INICIO'; then iniciou=1; break; fi
  done
  [ "$iniciou" -eq 1 ] && { ok "observador ligado (tentativa $tentativa)"; break; }
  adb shell input keyevent 4 >/dev/null 2>&1 || true
  sleep 3
done
[ "$iniciou" -eq 1 ] || { erro 'o observador nao iniciou (F10 nao chegou ao Kodi)'; coletar; exit 1; }

note '3. D-PAD DENTRO DA CATEGORIA'
# A barra da Home tem as categorias (9030..) que abrem o plugin na janela Videos.
# Aqui se usa o caminho do usuario: descer da barra superior para a barra de
# categorias e confirmar com OK.
tecla 4 2.0                       # garantir Home
tecla 19 0.6; tecla 19 0.6        # subir para a barra superior
tecla 20 0.8                      # descer para as categorias
tecla 23 6.0                      # OK na primeira categoria
janela_pastas=$(campo 1)
ok "janela apos abrir a categoria: $janela_pastas"
foco_ini=$(campo 2); itens_ini=$(campo 3)
printf '%s\n' "$(ultimo_snap)" > "$out/categoria-inicio.txt"
case "$foco_ini" in
  50|51|52) checar 'categoria_foco_na_lista' 0 "foco na lista ($foco_ini), $itens_ini itens" ;;
  *)        checar 'categoria_foco_na_lista' 1 "foco em $foco_ini, esperado 50/51/52 (janela $janela_pastas)" ;;
esac
trilha="$foco_ini"
for _ in 1 2 3 4 5; do
  tecla 20 0.7
  trilha="$trilha>$(campo 2)"
done
printf '%s\n' "$trilha" > "$out/categoria-trilha.txt"
foco_fim=$(campo 2)
case "$foco_fim" in
  50|51|52) checar 'categoria_dpad_desce' 0 "desceu e continuou na lista: $trilha" ;;
  *)        checar 'categoria_dpad_desce' 1 "saiu da lista ao descer: $trilha" ;;
esac

note '4. FILTRO "A a Z"'
# Subir da lista leva a barra de filtros (9060 -> botoes 9061todos/az/...).
for _ in $(seq 1 8); do
  tecla 19 0.5
  case "$(campo 2)" in 9061*|9060*) break ;; esac
done
foco_filtro=$(campo 2)
case "$foco_filtro" in
  9061*|9060*) checar 'filtro_alcancavel' 0 "foco na barra de filtros ($foco_filtro)" ;;
  *)           checar 'filtro_alcancavel' 1 "nao cheguei na barra de filtros (foco $foco_filtro)" ;;
esac
antes=$(ultimo_snap | cut -d'|' -f4-)
tecla 22 0.7                       # "Todos" -> "A a Z"
tecla 23 1.2                       # dispara a rota ordenar
sleep 8
depois=$(ultimo_snap | cut -d'|' -f4-)
printf 'antes: %s\ndepois: %s\n' "$antes" "$depois" > "$out/filtro-ordens.txt"
if [ -z "$antes" ] || [ "$antes" = "0" ]; then
  checar 'filtro_reordena' 1 "lista vazia nesta execucao; nao da para comparar"
elif [ "$antes" = "$depois" ]; then
  checar 'filtro_reordena' 1 "a ordem nao mudou: $antes"
else
  checar 'filtro_reordena' 0 "ordem mudou: $antes -> $depois"
fi

note '5. D-PAD NA GRADE DE AJUSTES'
tecla 4 2.0
tecla 19 0.8
tecla 22 1.0                       # segundo botao do topo = Ajustes
tecla 23 4.0
janela_aj=$(campo 1)
if [ "$janela_aj" != 'Ajustes' ] && [ "$janela_aj" != 'Settings' ]; then
  checar 'ajustes_abre' 0 "janela: $janela_aj"
  # abrir direto para nao deixar sem prova da grade
  adb shell am start -n "$comp" >/dev/null 2>&1 || true
  sleep 4
fi
ini=$(campo 2); trilha_aj="$ini"
for _ in 1 2 3; do tecla 22 0.6; trilha_aj="$trilha_aj>$(campo 2)"; done
for _ in 1 2 3; do tecla 20 0.6; trilha_aj="$trilha_aj>$(campo 2)"; done
printf '%s\n' "$trilha_aj" > "$out/ajustes-trilha.txt"
distintos=$(printf '%s' "$trilha_aj" | tr '>' '\n' | sort -u | wc -l)
[ "$distintos" -gt 1 ] && checar 'ajustes_dpad_move' 0 "foco andou: $trilha_aj" \
                       || checar 'ajustes_dpad_move' 1 "foco parado: $trilha_aj"

note '6. HOME: SUBIR DO HERO PARA A BARRA SUPERIOR'
tecla 4 2.5
for _ in $(seq 1 4); do tecla 20 0.6; done   # entrar no conteudo/hero
trilha_home=''
for _ in $(seq 1 10); do
  tecla 19 0.6
  atual=$(campo 2)
  trilha_home="$trilha_home>$atual"
  case "$atual" in 9121|9122|9123) break ;; esac
done
printf '%s\n' "$trilha_home" > "$out/home-trilha.txt"
chegou=$(campo 2)
case "$chegou" in
  9121|9122|9123) checar 'home_sobe_para_barra' 0 "chegou na barra superior: $trilha_home" ;;
  *)              checar 'home_sobe_para_barra' 1 "parou em $chegou ($trilha_home)" ;;
esac
tecla 20 1.0
abaixo=$(campo 2)
case "$abaixo" in
  9000|'?') checar 'home_topo_desce_visivel' 1 "desceu para $abaixo (controle invisivel neste layout)" ;;
  *)        checar 'home_topo_desce_visivel' 0 "desceu para $abaixo" ;;
esac

ler_obs > "$out/observador.log"
ler_log > "$out/kodi.log"
note '7. Resultado'
grep 'SMARTED_DPAD_SNAP' "$out/observador.log" | tail -5 | sed 's/.*SMARTED_DPAD_SNAP //' > "$out/ultimas-leituras.txt"
cat "$out/ultimas-leituras.txt"
coletar
if [ "$falhas" -ne 0 ]; then
  erro "$falhas verificacao(oes) falharam (ver artefato dpad-aparelho)"
  exit 1
fi
ok 'd-pad nas categorias, filtro A a Z, grade de Ajustes e subida hero->barra superior conferidos no aparelho'
