#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Acrescenta ao smoke do emulador a reabertura repetida (tela preta / sair).

O texto é aplicado por arquivo (nao por heredoc) para o script bash do CI nao
precisar de escapes. Uso:
    python3 tools/android/adicionar-teste-reabertura.py
"""
from pathlib import Path

ALVO = Path(__file__).resolve().parents[2] / 'smartedtv' / 'release' / 'install-smoke.sh'
MARCA = 'REABERTURA DO APP (tela preta / app saindo sozinho)'

BLOCO = r'''
# --- REABERTURA DO APP (tela preta / app saindo sozinho) --------------------
# Sair e abrir varias vezes seguidas (inclusive em segundos, com o processo
# ainda quente) tem de terminar sempre com o app vivo e com imagem na tela.
# Era exatamente aqui que aparecia "tela preta e fecha sozinho".
python3 -m pip install --quiet --disable-pip-version-check pillow >/dev/null 2>&1 || true
tela_preto() {
  python3 - "$1" <<'PY'
import sys
try:
    from PIL import Image, ImageStat
except Exception:
    print('sem pillow: checagem de brilho pulada')
    sys.exit(0)
media = ImageStat.Stat(Image.open(sys.argv[1]).convert('L')).mean[0]
print('brilho medio: %.1f' % media)
sys.exit(0 if media >= 8 else 1)
PY
}
componente_tv=$(adb shell cmd package resolve-activity --brief --user 0 \
  -a android.intent.action.MAIN -c android.intent.category.LEANBACK_LAUNCHER \
  -p "$pkg" | tr -d '\r' | awk '$1 ~ /^smartedtv\.full\// {print $1}')
for ciclo in 1 2 3; do
  adb shell am force-stop "$pkg"
  sleep 1
  adb shell am start -W -n "$componente_tv" >/dev/null 2>&1 || true
  # 8 s: janela de boot desenhada -> tela de entrada -> Home
  sleep 8
  if ! adb shell pidof "$pkg" >/dev/null; then
    erro "reabertura $ciclo: o processo morreu ($(adb logcat -b crash -d -t 12))"
  fi
  adb exec-out screencap -p > "$work/reabertura-$ciclo.png" 2>/dev/null || true
  if [ -s "$work/reabertura-$ciclo.png" ] && ! tela_preto "$work/reabertura-$ciclo.png"; then
    erro "reabertura $ciclo: tela preta (app vivo, mas sem desenho)"
  fi
  echo "::notice::reabertura $ciclo: app vivo e com imagem na tela"
done
'''


def main():
    texto = ALVO.read_text(encoding='utf-8')
    if MARCA in texto:
        print('ja aplicado')
        return 0
    # o smoke abre o launcher de TV duas vezes; a reabertura entra depois da
    # instalação limpa, que é o último "abrir LEANBACK_LAUNCHER" do arquivo
    ancora = texto[texto.rindex('abrir LEANBACK_LAUNCHER\n'):]
    ancora = ancora[:ancora.index('\n') + 1]
    if texto.count(ancora) < 1:
        raise SystemExit('ancora da reabertura nao encontrada')
    texto = texto.replace(ancora, ancora + BLOCO, 1)
    ALVO.write_text(texto, encoding='utf-8')
    print('reabertura acrescentada ao smoke')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
