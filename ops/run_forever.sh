#!/usr/bin/env bash
set -u

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESTART_DELAY_SECONDS="${RESTART_DELAY_SECONDS:-3}"

cd "${APP_DIR}"
export PYTHONDONTWRITEBYTECODE=1

echo "[SOVD][WATCHDOG] Starting SOVD dashboard watchdog in ${APP_DIR}"

while true; do
    started_at="$(date -Is)"
    echo "[SOVD][WATCHDOG] ${started_at} launching server.py"

    python3 -u server.py
    exit_code="$?"

    stopped_at="$(date -Is)"
    echo "[SOVD][WATCHDOG] ${stopped_at} server.py exited with code ${exit_code}; restarting in ${RESTART_DELAY_SECONDS}s"
    sleep "${RESTART_DELAY_SECONDS}"
done
