#!/usr/bin/env zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"
mkdir -p logs data build
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

"$PYTHON_BIN" -m aigithub_radar.cli init-db
"$PYTHON_BIN" -m aigithub_radar.cli compile-specs
exec "$PYTHON_BIN" -m aigithub_radar.cli ops-loop --interval-hours 12 --theme-limit 3 --repos-per-theme 20 --deep-limit 2 --validate-limit 1
