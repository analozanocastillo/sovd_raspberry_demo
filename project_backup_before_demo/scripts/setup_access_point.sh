#!/usr/bin/env bash
set -euo pipefail

SSID="${SOVD_AP_SSID:-SOVD-Demo}"
PASSWORD="${SOVD_AP_PASSWORD:-SOVDdemo2026}"
ADDRESS="${SOVD_AP_ADDRESS:-192.168.4.1/24}"
IFACE="${SOVD_AP_IFACE:-wlan0}"
CONNECTION="${SOVD_AP_CONNECTION:-sovd-demo-ap}"

if ! command -v nmcli >/dev/null 2>&1; then
    echo "nmcli was not found. This script expects Raspberry Pi OS with NetworkManager."
    exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script with sudo."
    exit 1
fi

echo "Creating Raspberry Pi access point:"
echo "  SSID: $SSID"
echo "  IP:   $ADDRESS"
echo "  Wi-Fi interface: $IFACE"
echo
echo "Warning: if you are connected to this Pi through Wi-Fi, this may disconnect your session."

if nmcli connection show "$CONNECTION" >/dev/null 2>&1; then
    nmcli connection delete "$CONNECTION"
fi

nmcli connection add \
    type wifi \
    ifname "$IFACE" \
    con-name "$CONNECTION" \
    autoconnect yes \
    ssid "$SSID"

nmcli connection modify "$CONNECTION" \
    802-11-wireless.mode ap \
    802-11-wireless.band bg \
    ipv4.method shared \
    ipv4.addresses "$ADDRESS" \
    ipv6.method disabled \
    wifi-sec.key-mgmt wpa-psk \
    wifi-sec.psk "$PASSWORD"

nmcli connection up "$CONNECTION"

echo
echo "Access point is active."
echo "Connect phones/laptops to Wi-Fi '$SSID' using password '$PASSWORD'."
echo "Open the dashboard at http://${ADDRESS%/*}:5000/"
echo
echo "If phones say this Wi-Fi has no internet, that is expected for the local demo."
echo "Stay connected to the Wi-Fi and open the dashboard QR anyway."
echo "To provide internet too, connect the Pi through Ethernet, USB tethering, or a second Wi-Fi adapter."
