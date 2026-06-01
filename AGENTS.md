# Project Context

This repository is an educational SOVD/DoIP vehicle diagnostics demo intended for Raspberry Pi style experiments. It combines a Flask REST dashboard, a simulated DoIP ECU, UDS ReadDataByIdentifier handling, and an Arduino-driven bench notification flow for rear/front LEDs, crash touch input, and battery voltage.

## Main Pieces

- `server.py`: Main Flask app on port `5000`. Serves the dashboard, REST API endpoints, POST UDS endpoint, Arduino bench serial monitoring, test LED fault endpoints, and an SSE `/events` stream.
- `routes/api_routes.py`: API routing logic for vehicle data, ignition/fault simulation, speed simulation, and `/uds/readDataByIdentifier`.
- `routes/ui_routes.py`: Maps `/` and `/ui` to `index.html`.
- `data/simulated_data.py`: In-memory vehicle, power, component, engine, sensor, and shared fault state data.
- `data/diagnostic_trace.py`: Bounded `deque(maxlen=100)` trace shown in the dashboard. Browser requests are scoped with `X-SOVD-Client`; physical bench events are global so all clients see them.
- `index.html`: Main browser dashboard for vehicle identity, power telemetry, ignition controls, UDS DID reads, terminal-style logs, a client-local `Clean Console` button, and SSE popup notifications.
- `doip_client.py`: TCP DoIP client helper used by the REST UDS endpoint. Sends UDS payloads to `127.0.0.1:13400`.
- `doip_ecu.py`: DoIP ECU simulator on TCP port `13400`. It intentionally has no Flask or serial responsibilities.
- `arduino_code.cpp`: Arduino sketch that monitors rear LED on `A0`, front LED on `A2`, crash/touch on `D2`, and battery potentiometer on `A1`. Emits `LED_*`, `CRASH:*`, and `BATTERY:*` serial messages.

## How To Run

Main SOVD REST/dashboard server:

```bash
python3 server.py
```

Open:

```text
http://localhost:5000/
```

DoIP ECU simulator:

```bash
python3 doip_ecu.py
```

The main `server.py` app exposes LED simulation endpoints on port `5000`:

```text
http://localhost:5000/test/fault
http://localhost:5000/test/ok
```

## Presentation Access Point

- For presentations, the Raspberry Pi can run its own Wi-Fi access point named `SOVD-Demo` with password `SOVDdemo2026`.
- `scripts/setup_access_point.sh` configures this through NetworkManager and gives the Pi the stable AP address `192.168.4.1`.
- `sovd-wifi-qr.png` joins the Wi-Fi network.
- `sovd-dashboard-qr.png` opens `http://192.168.4.1:5000/`.
- Warn before running the AP setup over Wi-Fi because switching `wlan0` into AP mode can disconnect the active session.
- Current mobile-hotspot presentation mode uses SSID `SOVD-demo-Ana`.
- The Raspberry Pi NetworkManager connection `SOVD-demo-Ana` has been set to manual IPv4 `172.20.10.2/28`, gateway `172.20.10.1`, DNS `172.20.10.1 8.8.8.8`.
- In mobile-hotspot mode, `sovd-dashboard-qr.png` should point to `http://172.20.10.2:5000/`.

## API Shape

Common GET endpoints:

- `/vehicle`
- `/vehicle/power`
- `/diagnostics/trace`
- `/components`
- `/components/engine/ident`
- `/components/engine/runtime`
- `/components/engine/sensors`
- `/components/engine/faults`
- `/ignition/on`
- `/ignition/off`
- `/faults/on`
- `/faults/off`
- `/vehicle/speed`
- `/vehicle/speed/<value>`

UDS ReadDataByIdentifier:

```http
POST /uds/readDataByIdentifier
Content-Type: application/json

{"did": "F190"}
```

Supported DIDs in the DoIP ECU:

- `F190`: VIN
- `F187`: Software Version
- `F18C`: Hardware Version
- `F40C`: Engine RPM
- `F40D`: Engine Load
- `F40E`: Coolant Temperature
- `F1A1`: Latest rear-left LED state. LED changes are sent from `server.py` to `doip_ecu.py` with UDS `WriteDataByIdentifier` (`2E F1 A1 ...`) and the ECU replies with `6E F1 A1`.
- `F1A2`: Latest front LED state.
- `F1A3`: Latest crash state.
- `F1A4`: Latest battery state.

## Known Gotchas

- The main `server.py` `/events` endpoint emits raw SSE messages such as `LED_REAR:FAULT`, `LED_FRONT:FAULT`, `BATTERY:UNDERVOLTAGE:10.8`, `BATTERY:OVERVOLTAGE:14.8`, `CRASH:FAULT:66`, and `SYSTEM:OK`, matching `index.html`.
- On browser reconnect or page refresh, `/events` immediately replays active physical bench faults so the dashboard does not show restored while a LED is disconnected or battery voltage is out of range.
- `SYSTEM:OK` should be emitted only when every active physical bench fault is clear: LEDs connected, crash restored, and battery voltage normal.
- Battery state is voltage-driven. Normal is `11.0 V <= voltage <= 14.5 V`; below `11.0 V` is `UNDERVOLTAGE`, above `14.5 V` is `OVERVOLTAGE`. Keep `arduino_code.cpp`, `server.py`, and `index.html` thresholds aligned.
- `server.py` starts an Arduino serial listener for the bench monitor and opens the port with exclusive access.
- Bench FAULT/OK transitions create DoIP traffic on port `13400` using UDS `WriteDataByIdentifier` for DIDs `F1A1` through `F1A4`.
- The dashboard stores a browser-local client ID in `localStorage` and sends it as `X-SOVD-Client`. Keep browser-triggered traces and simulation state client-scoped, but keep physical bench events global.
- The dashboard's `Clean Console` button is client-local: it stores a trace cursor in `localStorage` and hides older visible trace rows for that browser. It does not delete shared trace entries.
- `routes/api_routes.py` keeps a small in-memory client session map for browser-controlled simulation values such as ignition, speed, and demo engine faults. A phone changing ignition must not change what a laptop sees.
- `doip_ecu.py` should stay focused on DoIP so it does not compete with `server.py` for the serial port.
- Serial access expects Arduino devices at `/dev/ttyACM0`, `/dev/ttyACM1`, `/dev/ttyUSB0`, or `/dev/ttyUSB1`.
- The visible red fault background in `index.html` is driven by frontend active-fault tracking for battery, LEDs, and crash. Do not leave visual state dependent only on a single `SYSTEM:OK` message; missed SSE messages should not strand the page in a red fault state when current data is normal.

## Development Notes

- This project stores state in Python module-level dictionaries; there is no database.
- The Flask apps are development/demo servers, not production services.
- Existing files include Spanish comments and UI text. Preserve that style where appropriate.
- Be careful with `doip_ecu.py` and `index.html`: they may already contain user edits.
- Before changing behavior, check whether the user is running `server.py`, `doip_ecu.py`, or both.

## Verification

Syntax check:

```bash
find . -maxdepth 3 -type f -name '*.py' -print0 | xargs -0 -n1 python3 -m py_compile
```

Basic manual flow:

1. Start `doip_ecu.py` so DoIP port `13400` is available if UDS DID reads need a live DoIP ECU.
2. Start `server.py` for the main dashboard, vehicle API, and bench event stream on port `5000`.
3. Open `http://localhost:5000/`.
4. Use the DID dropdown and `Execute ReadDID`.
5. Use `http://localhost:5000/test/fault` and `/test/ok` when testing rear LED notification behavior without Arduino hardware.
6. Test battery restore by moving voltage outside the normal range, then back into `11.0 V` to `14.5 V`; the dashboard should return to `NORMAL` and show `System Restored` when no other bench fault is active.
