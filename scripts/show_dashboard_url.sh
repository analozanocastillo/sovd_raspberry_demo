#!/usr/bin/env bash
set -euo pipefail

PORT="${SOVD_DASHBOARD_PORT:-5000}"

if command -v hostname >/dev/null 2>&1; then
    ips="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | grep -v '^127\.' | grep -v '^172\.17\.' || true)"
else
    ips=""
fi

if [ -z "$ips" ] && command -v ip >/dev/null 2>&1; then
    ips="$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | grep -v '^172\.17\.' || true)"
fi

if [ -z "$ips" ]; then
    echo "No Wi-Fi/LAN IPv4 address found."
    echo "Local dashboard: http://localhost:${PORT}/"
    exit 1
fi

echo "Dashboard URLs for this network:"
for ip in $ips; do
    echo "  http://${ip}:${PORT}/"
done

host="$(hostname 2>/dev/null || true)"
if [ -n "$host" ]; then
    echo
    echo "Hostname URL if mDNS is available on the client:"
    echo "  http://${host}.local:${PORT}/"
fi

if command -v curl >/dev/null 2>&1; then
    ngrok_urls="$(
        curl --connect-timeout 1 --max-time 2 -s http://127.0.0.1:4040/api/tunnels 2>/dev/null |
            grep -o '"public_url":"https://[^"]*"' |
            cut -d'"' -f4 || true
    )"

    if [ -n "$ngrok_urls" ]; then
        echo
        echo "Ngrok dashboard URLs:"
        for url in $ngrok_urls; do
            echo "  ${url}/"
        done
    fi
fi
