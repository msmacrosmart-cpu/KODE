#!/usr/bin/env bash
# Publica um arquivo de diagnostico do runner como comentario do commit.
# Artefato de run nao baixa fora do runner; o comentario do commit sim.
set -euo pipefail
arquivo=${1:?arquivo}
if [ ! -s "$arquivo" ]; then
  echo "::notice::sem arquivo de diagnostico para publicar ($arquivo)"
  exit 0
fi
sha=${2:-${GITHUB_SHA:?sha}}
corpo=$(printf 'Diagnostico do emulador (run %s)\n\n```\n%s\n```\n' \
  "${GITHUB_RUN_ID:-local}" "$(tail -c 60000 "$arquivo")")
python3 - "$corpo" "$sha" <<'PY'
import json, os, subprocess, sys
corpo, sha = sys.argv[1], sys.argv[2]
proc = subprocess.run(['gh', 'api', '-X', 'POST',
                       'repos/%s/commits/%s/comments' % (os.environ['GITHUB_REPOSITORY'], sha),
                       '--input', '-'],
                      input=json.dumps({'body': corpo}), text=True,
                      capture_output=True)
print(proc.stdout[-300:] or proc.stderr[-300:])
PY
