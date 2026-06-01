#!/usr/bin/env bash
set -euo pipefail

PORT="${SOVD_DASHBOARD_PORT:-5000}"
NAME="${SOVD_NGROK_TUNNEL_NAME:-sovd-dashboard}"
API="${SOVD_NGROK_API:-http://127.0.0.1:4040/api/tunnels}"

if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required."
    exit 1
fi

tunnels="$(curl --connect-timeout 1 --max-time 2 -s "$API" 2>/dev/null || true)"

if [ -z "$tunnels" ]; then
    echo "No running ngrok agent found at ${API}."
    echo "Start an ngrok tunnel with:"
    echo "  ngrok http ${PORT}"
    exit 1
fi

existing_url="$(
    printf '%s' "$tunnels" |
        grep -o '"public_url":"https://[^"]*"' |
        cut -d'"' -f4 |
        head -n 1 || true
)"

if [ -n "$existing_url" ]; then
    echo "Ngrok dashboard URL:"
    echo "  ${existing_url}/"
    exit 0
fi

created="$(
    curl -s -X POST \
        -H 'Content-Type: application/json' \
        -d "{\"name\":\"${NAME}\",\"addr\":\"http://localhost:${PORT}\",\"proto\":\"http\",\"inspect\":true}" \
        "$API"
)"

url="$(
    printf '%s' "$created" |
        grep -o '"public_url":"https://[^"]*"' |
        cut -d'"' -f4 |
        head -n 1 || true
)"

if [ -z "$url" ]; then
    echo "Could not create ngrok dashboard tunnel."
    echo "$created"
    exit 1
fi

echo "Ngrok dashboard URL:"
echo "  ${url}/"
