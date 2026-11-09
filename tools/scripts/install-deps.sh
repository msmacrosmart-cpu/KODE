#!/usr/bin/env bash
# =============================================================================
#  install-deps.sh — atalho compatível para instalar o ambiente de build
#  (mantido por compatibilidade; a implementação real está em setup-android-env.sh)
# =============================================================================
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/setup-android-env.sh" "$@"
