#!/usr/bin/env bash
# One command to run the demo locally.
#   ./demo.sh live      live API (real model calls, key from .env) + web app; opens chat and console
#   ./demo.sh replay    the public replay build, offline, on :3018; opens chat and console
#   ./demo.sh live --fresh   same as live, with an empty event log (old one moved to runs_<timestamp>)
# Ctrl-C stops everything and restores config/control.yaml.
set -euo pipefail
cd "$(dirname "$0")"
mode="${1:-}"

busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }
need_free() { if busy "$1"; then echo "Port $1 is in use. Stop that process first (lsof -nP -i :$1)."; exit 1; fi; }
open_tabs() { sleep "$2"; open "$1/"; open "$1/console/"; }

case "$mode" in
  live)
    [ -f .env ] || { echo "No .env file: add GEMINI_API_KEY to .env first."; exit 1; }
    need_free 8018; need_free 5173
    if [ "${2:-}" = "--fresh" ] && [ -d runs ]; then mv runs "runs_$(date +%Y%m%d_%H%M%S)"; fi
    set -a; . ./.env; set +a
    RUN_MODE=live uv run uvicorn trusted_service_agent.api:app --host 127.0.0.1 --port 8018 --log-level warning &
    api=$!
    stop() { kill "$api" "${web:-}" 2>/dev/null; wait 2>/dev/null; git checkout -q config/control.yaml; echo; echo "Stopped. control.yaml restored."; }
    trap 'stop; exit 0' INT TERM
    open_tabs http://localhost:5173 4 &
    echo "Live demo: chat http://localhost:5173  ·  console http://localhost:5173/console/  ·  Ctrl-C to stop"
    (cd web && exec npx vite --clearScreen false) &
    web=$!
    wait "$web"
    ;;
  replay)
    need_free 3018
    [ -d web/dist ] || make build-static
    open_tabs http://localhost:3018 1 &
    echo "Replay demo (offline): chat http://localhost:3018  ·  console http://localhost:3018/console/  ·  Ctrl-C to stop"
    python3 -m http.server 3018 -d web/dist
    ;;
  *)
    echo "Usage: ./demo.sh live [--fresh] | ./demo.sh replay"; exit 1 ;;
esac
