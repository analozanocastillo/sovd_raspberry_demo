# SOVD Raspberry Demo

Educational proof-of-concept project that simulates a small **SOVD-like vehicle diagnostics server** on a Raspberry Pi style setup.

The project combines:

- A Flask REST API and web dashboard on port `5000`
- A simulated DoIP ECU on TCP port `13400`
- UDS `ReadDataByIdentifier` requests through DoIP
- An Arduino-based bench monitor for rear/front LEDs, crash touch input, and battery voltage
- Real-time browser notifications over Server-Sent Events (SSE), including a unified system restored event

This is not a full ASAM SOVD implementation. It is intended for learning, demos, and experimentation.

---

## Project Structure

```text
project/
├── server.py                         # Main SOVD-like REST server and dashboard backend
├── doip_ecu.py                       # DoIP ECU simulator on port 13400
├── doip_client.py                    # DoIP client helper used by the REST UDS endpoint
├── index.html                        # Main dashboard served by server.py
├── arduino_code.cpp                  # Arduino bench monitor sketch
├── data/
│   ├── diagnostic_trace.py           # In-memory diagnostics trace buffer
│   └── simulated_data.py             # Vehicle, power, ECU, sensor, and shared fault state
├── routes/
│   ├── api_routes.py                 # REST and UDS route logic
│   └── ui_routes.py                  # UI route mapping
├── Dockerfile
├── AGENTS.md                         # Project context for future Codex sessions
└── README.md
```

---

## How It Works

The main user-facing app is `server.py`.

It serves `index.html` at:

```text
http://localhost:5000/
```

The dashboard calls REST endpoints on the same origin, for example:

```text
GET  /vehicle
GET  /vehicle/power
POST /uds/readDataByIdentifier
GET  /diagnostics/trace
GET  /events
```

For UDS requests, `server.py` uses `doip_client.py` to send a DoIP diagnostic message to the simulated ECU on:

```text
127.0.0.1:13400
```

The Arduino bench monitor is integrated into `server.py`. It listens to serial messages such as:

```text
LED_REAR:FAULT
LED_REAR:OK
LED_FRONT:FAULT
LED_FRONT:OK
CRASH:FAULT:<duration_ms>
BATTERY:VOLTAGE:<voltage>
BATTERY:UNDERVOLTAGE:<voltage>
BATTERY:OVERVOLTAGE:<voltage>
BATTERY:OK:<voltage>
```

and publishes browser notifications through `/events` as raw SSE messages, for example:

```text
data: LED_REAR:FAULT
data: BATTERY:UNDERVOLTAGE:10.8
data: CRASH:FAULT:66
data: SYSTEM:OK
```

`SYSTEM:OK` is emitted only when every active bench fault has cleared: LEDs connected, crash input restored, and battery voltage back in the normal range.

---

## Run The Demo

### 1. Start The DoIP ECU Simulator

Run this if you want the dashboard's UDS DID reads to work:

```bash
python3 doip_ecu.py
```

This starts the simulated DoIP ECU on TCP port `13400`.

`doip_ecu.py` only handles DoIP/UDS traffic. The main `server.py` process owns the Arduino bench monitor to avoid two processes competing for the same serial device.

### 2. Start The Main Dashboard Server

In another terminal:

```bash
python3 server.py
```

You should see output similar to:

```text
SOVD demo server running on http://0.0.0.0:5000
```

Open:

```text
http://localhost:5000/
```

On a Raspberry Pi or another device on the same network, replace `localhost` with the Raspberry Pi IP address:

```text
http://<raspberry-pi-ip>:5000/
```

To print the correct URL for the Wi-Fi/LAN that the Pi is currently using:

```bash
./scripts/show_dashboard_url.sh
```

If an ngrok HTTP tunnel is active, the same command also prints the public `https://...ngrok...` dashboard URL.

If ngrok is already running for SSH and your account allows only one ngrok agent session, create the dashboard tunnel through the existing agent:

```bash
./scripts/ensure_ngrok_dashboard.sh
```

For example, if the Pi is connected to a normal router Wi-Fi and has address `192.168.1.57`, use:

```text
http://192.168.1.57:5000/
```

The fixed URL `http://172.20.10.2:5000/` only works on networks that actually assign or route `172.20.10.2` to the Pi. It cannot work automatically on every Wi-Fi network, because each Wi-Fi/router chooses its own IP range and client devices route traffic through that network.

### Presentation Wi-Fi Access Point

For presentations, the Raspberry Pi can create its own local Wi-Fi network. Attendees connect to that Wi-Fi first, then open the dashboard through a stable local address:

```text
http://192.168.4.1:5000/
```

Default presentation credentials:

```text
Wi-Fi name: SOVD-Demo
Password: SOVDdemo2026
```

The repository includes two QR codes:

- `sovd-wifi-qr.png`: joins the `SOVD-Demo` Wi-Fi network.
- `sovd-dashboard-qr.png`: opens `http://192.168.4.1:5000/`.

To configure the Raspberry Pi access point with NetworkManager:

```bash
sudo ./scripts/setup_access_point.sh
```

If you are connected to the Raspberry Pi through Wi-Fi, this command may disconnect your current session because the Wi-Fi interface switches from client mode to access-point mode. Use Ethernet, a local keyboard/screen, or the existing tunnel when applying this configuration.

After the access point is active:

1. Start the DoIP ECU simulator:

```bash
python3 doip_ecu.py
```

2. Start the dashboard:

```bash
python3 server.py
```

3. Ask attendees to scan `sovd-wifi-qr.png`, stay connected even if the phone says the network has no internet, then scan `sovd-dashboard-qr.png`.

The presentation Wi-Fi is a local network. If the Raspberry Pi does not have a second internet uplink, phones may show a warning such as "No Internet Connection". That is normal: the Wi-Fi still lets attendees reach the dashboard at `http://192.168.4.1:5000/`.

To make the presentation Wi-Fi provide internet too, the Pi needs another uplink while `wlan0` is being used as the access point. Good options are:

- Ethernet connected to a router.
- USB tethering from a phone.
- A second USB Wi-Fi adapter for the internet side.

Using only the built-in `wlan0` for both the access point and another Wi-Fi network is not reliable for this demo.

### Presentation Mobile Hotspot Mode

The current presentation setup uses a mobile hotspot named:

```text
SOVD-demo-Ana
```

The Raspberry Pi NetworkManager connection is configured with this fixed IPv4 address:

```text
172.20.10.2/28
Gateway: 172.20.10.1
```

With that fixed address, the dashboard QR can stay stable across Raspberry Pi reboots:

```text
http://172.20.10.2:5000/
```

This URL is specific to the `SOVD-demo-Ana` hotspot configuration. If the Pi is connected to a different Wi-Fi, run `./scripts/show_dashboard_url.sh` and use the URL it prints instead. If the phone hotspot changes its network range in the future, update the static connection settings and regenerate `sovd-dashboard-qr.png`.

---

## Arduino Bench Monitor

Upload `arduino_code.cpp` to the Arduino.

The sketch monitors:

- `A0`: rear LED connection state
- `A2`: front LED connection state
- `D2`: crash/touch input
- `A1`: battery voltage potentiometer

It writes messages over serial at `9600` baud:

```text
LED_REAR:FAULT
LED_REAR:OK
LED_FRONT:FAULT
LED_FRONT:OK
CRASH:FAULT:<duration_ms>
BATTERY:VOLTAGE:<voltage>
BATTERY:UNDERVOLTAGE:<voltage>
BATTERY:OVERVOLTAGE:<voltage>
BATTERY:OK:<voltage>
```

`server.py` scans these serial ports:

```text
/dev/ttyACM0
/dev/ttyACM1
/dev/ttyUSB0
/dev/ttyUSB1
```

When a LED is disconnected, the dashboard shows a fault popup. When battery voltage leaves the normal range, the dashboard shows an under/over voltage popup and changes `Power Mode`. A crash touch event also shows a popup.

The normal battery range is:

```text
11.0 V <= voltage <= 14.5 V
```

Below `11.0 V` is `UNDERVOLTAGE`. Above `14.5 V` is `OVERVOLTAGE`. Returning to the normal range changes `Power Mode` back to `NORMAL`; if no other bench fault is active, the dashboard shows `System Restored`.

Each bench state change also sends a UDS `WriteDataByIdentifier` request through DoIP:

```text
2E F1 A1 4C 45 44 5F 52 45 41 52 3A ...
```

The demo DIDs store the latest bench states as ASCII. For example, DID `F1A1` stores `LED_REAR:FAULT` or `LED_REAR:OK`, DID `F1A3` stores crash state, and DID `F1A4` stores battery state. The simulated ECU replies with positive WriteDataByIdentifier responses such as `6E F1 A1`.

### Test Without Arduino

You can simulate the LED state with:

```text
http://localhost:5000/test/fault
http://localhost:5000/test/ok
```

---

## API Overview

### Vehicle And Power

```http
GET /vehicle
GET /vehicle/power
```

### Components

```http
GET /components
GET /components/engine/ident
GET /components/engine/runtime
GET /components/engine/sensors
GET /components/engine/faults
```

### Simulation Controls

```http
GET /ignition/on
GET /ignition/off
GET /faults/on
GET /faults/off
GET /vehicle/speed
GET /vehicle/speed/<value>
```

### UDS ReadDataByIdentifier

```http
POST /uds/readDataByIdentifier
Content-Type: application/json

{"did": "F190"}
```

Supported DIDs:

| DID | Meaning |
| --- | --- |
| `F190` | VIN |
| `F187` | Software Version |
| `F18C` | Hardware Version |
| `F40C` | Engine RPM |
| `F40D` | Engine Load |
| `F40E` | Coolant Temperature |
| `F1A1` | Latest rear-left LED state |
| `F1A2` | Latest front LED state |
| `F1A3` | Latest crash state |
| `F1A4` | Latest battery state |

### Real-Time Events

```http
GET /events
```

This endpoint uses Server-Sent Events and emits:

```text
data: LED_REAR:FAULT
data: LED_FRONT:FAULT
data: BATTERY:UNDERVOLTAGE:10.8
data: BATTERY:OVERVOLTAGE:14.8
data: CRASH:FAULT:66
data: SYSTEM:OK
```

When a browser refreshes, `/events` immediately replays any active physical bench faults so the page does not show a restored system while a LED is disconnected or the battery voltage is still out of range.

### Diagnostics Trace

```http
GET /diagnostics/trace
```

Returns the latest entries from an in-memory `deque(maxlen=100)`.

The dashboard's `Clean Console` button clears the visible diagnostic console for the current browser by storing a local trace cursor. It does not delete the shared in-memory trace for other connected browsers.

Browser-initiated diagnostic actions are scoped per browser client, so one user's ReadDID trace is not shown to another user. Global vehicle events, such as real LED connect/disconnect, crash, and battery voltage changes, are visible to every connected browser.

Browser-controlled simulation state is also scoped per browser client. For example, if one user turns ignition OFF from a phone, another user on a computer keeps their own ignition state and diagnostic flow. Physical LED connect/disconnect events remain shared because they represent the real vehicle/bench state.

---

## Verification

Compile-check the Python files:

```bash
find . -maxdepth 3 -type f -name '*.py' -print0 | xargs -0 -n1 python3 -m py_compile
```

Quick endpoint checks:

```bash
curl http://localhost:5000/vehicle
curl http://localhost:5000/test/fault
curl http://localhost:5000/test/ok
```

Sample the SSE stream:

```bash
curl --max-time 2 http://localhost:5000/events
```

---

## Notes And Limitations

- This project stores state in Python dictionaries; there is no database.
- There is no authentication or transport security.
- The Flask apps are development/demo servers.
- Only one process should read the Arduino serial port. By convention, `server.py` owns it.
- Older experimental entrypoints were removed so the active flow is easier to follow.
