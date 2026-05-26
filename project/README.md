# SOVD Raspberry Demo

Educational proof-of-concept project that simulates a small **SOVD-like vehicle diagnostics server** on a Raspberry Pi style setup.

The project combines:

- A Flask REST API and web dashboard on port `5000`
- A simulated DoIP ECU on TCP port `13400`
- UDS `ReadDataByIdentifier` requests through DoIP
- An Arduino-based rear-left LED connect/disconnect detector
- Real-time browser notifications over Server-Sent Events (SSE)

This is not a full ASAM SOVD implementation. It is intended for learning, demos, and experimentation.

---

## Project Structure

```text
project/
├── server.py                         # Main SOVD-like REST server and dashboard backend
├── doip_ecu.py                       # DoIP ECU simulator on port 13400
├── doip_client.py                    # DoIP client helper used by the REST UDS endpoint
├── index.html                        # Main dashboard served by server.py
├── arduino_code.cpp                  # Arduino LED detector sketch
├── data/
│   ├── diagnostic_trace.py           # In-memory diagnostics trace buffer
│   ├── simulated_data.py             # Vehicle, power, ECU, sensor, and fault demo data
│   └── vehicle_state.py              # Shared rear-left light fault state
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

The LED detector is also integrated into `server.py`. It listens to Arduino serial messages such as:

```text
LED_REAR:FAULT
LED_REAR:OK
```

and publishes browser notifications through `/events` as:

```text
data: FAULT
data: OK
```

---

## Run The Demo

### 1. Start The DoIP ECU Simulator

Run this if you want the dashboard's UDS DID reads to work:

```bash
python3 doip_ecu.py
```

This starts the simulated DoIP ECU on TCP port `13400`.

`doip_ecu.py` only handles DoIP/UDS traffic. The main `server.py` process owns the LED detector to avoid two processes competing for the same serial device.

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

If the phone hotspot changes its network range in the future, update the static connection settings and regenerate `sovd-dashboard-qr.png`.

---

## Arduino LED Detector

Upload `arduino_code.cpp` to the Arduino.

The sketch monitors analog pin `A0` and writes one of these messages over serial at `9600` baud:

```text
LED_REAR:FAULT
LED_REAR:OK
```

`server.py` scans these serial ports:

```text
/dev/ttyACM0
/dev/ttyACM1
/dev/ttyUSB0
/dev/ttyUSB1
```

When the LED is disconnected, the dashboard should show a fault popup. When the LED is restored, it should show a recovery popup.

Each LED state change also sends a UDS `WriteDataByIdentifier` request through DoIP:

```text
2E F1 A1 4C 45 44 5F 52 45 41 52 3A ...
```

The demo DID `F1A1` stores the latest LED state as ASCII, for example `LED_REAR:FAULT` or `LED_REAR:OK`. The simulated ECU replies with `6E F1 A1`.

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

### Real-Time Events

```http
GET /events
```

This endpoint uses Server-Sent Events and emits:

```text
data: FAULT
data: OK
```

### Diagnostics Trace

```http
GET /diagnostics/trace
```

Returns the latest entries from an in-memory `deque(maxlen=100)`.

Browser-initiated diagnostic actions are scoped per browser client, so one user's ReadDID trace is not shown to another user. Global vehicle events, such as real LED connect/disconnect changes, are visible to every connected browser.

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
