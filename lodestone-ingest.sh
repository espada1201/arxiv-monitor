#!/bin/bash
# Sole coupling point between monitor and lodestone's CLI path.
# If lodestone moves, only this file needs updating.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load credentials from .env if present (needed when run from cron)
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/.env"
    set +a
fi

uv run --project ~/.lodestone python -m _system.scripts.ingest "$@"
