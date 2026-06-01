#!/usr/bin/env bash
set -euo pipefail

PORT="${SOVD_DASHBOARD_PORT:-5000}"

if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required."
    exit 1
fi

ngrok_urls="$(
    curl --connect-timeout 1 --max-time 2 -s http://127.0.0.1:4040/api/tunnels 2>/dev/null |
        grep -o '"public_url":"https://[^"]*"' |
        cut -d'"' -f4 || true
)"

if [ -z "$ngrok_urls" ]; then
    echo "No ngrok dashboard URL found."
    echo "Create one with:"
    echo "  ./scripts/ensure_ngrok_dashboard.sh"
    echo
    echo "Expected local target: http://localhost:${PORT}/"
    exit 1
fi

echo "Ngrok dashboard URLs:"
for url in $ngrok_urls; do
    echo "  ${url}/"
done
