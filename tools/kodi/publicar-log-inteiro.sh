#!/usr/bin/env bash
# Publica um arquivo grande em pedacos como comentarios do commit.
# Usado SO no workflow de diagnostico: o artefato do run nao baixa fora do
# runner e o log do aparelho precisa ser lido de verdade.
set -euo pipefail
arquivo=${1:?arquivo}
sha=${2:-${GITHUB_SHA:?sha}}
[ -s "$arquivo" ] || { echo "::notice::arquivo vazio: $arquivo"; exit 0; }
python3 - "$arquivo" "$sha" <<'PY'
import json, os, subprocess, sys
arquivo, sha = sys.argv[1], sys.argv[2]
texto = open(arquivo, 'rb').read().decode('utf-8', 'replace')
limite = 55000
pedacos = [texto[i:i+limite] for i in range(0, len(texto), limite)] or ['']
for numero, pedaco in enumerate(pedacos, 1):
    corpo = 'kodi.log do projetor %d/%d (run %s)\n\n```\n%s\n```\n' % (
        numero, len(pedacos), os.environ.get('GITHUB_RUN_ID', 'local'), pedaco)
    proc = subprocess.run(['gh', 'api', '-X', 'POST',
                           'repos/%s/commits/%s/comments' % (os.environ['GITHUB_REPOSITORY'], sha),
                           '--input', '-'],
                          input=json.dumps({'body': corpo}), text=True,
                          capture_output=True)
    print('pedaco %d/%d: %s' % (numero, len(pedacos),
                                'ok' if proc.returncode == 0 else proc.stderr[-200:]))
PY
