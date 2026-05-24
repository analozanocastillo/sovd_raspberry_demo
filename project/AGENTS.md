# Project Context

This repository is an educational SOVD/DoIP vehicle diagnostics demo intended for Raspberry Pi style experiments. It combines a Flask REST dashboard, a simulated DoIP ECU, UDS ReadDataByIdentifier handling, and an Arduino-driven rear-left LED fault notification flow.

## Main Pieces

- `server.py`: Main Flask app on port `5000`. Serves the dashboard, REST API endpoints, POST UDS endpoint, Arduino rear-left LED serial monitoring, test fault endpoints, and an SSE `/events` stream.
- `routes/api_routes.py`: API routing logic for vehicle data, ignition/fault simulation, speed simulation, and `/uds/readDataByIdentifier`.
- `routes/ui_routes.py`: Maps `/` and `/ui` to `index.html`.
- `data/simulated_data.py`: In-memory vehicle, power, component, engine, sensor, and fault data.
- `data/vehicle_state.py`: Shared in-memory state for the rear-left light fault.
- `data/diagnostic_trace.py`: Bounded `deque(maxlen=100)` trace shown in the dashboard. Browser requests are scoped with `X-SOVD-Client`; LED events are global so all clients see them.
- `index.html`: Main browser dashboard for vehicle identity, power telemetry, ignition controls, UDS DID reads, terminal-style logs, and SSE popup notifications.
- `doip_client.py`: TCP DoIP client helper used by the REST UDS endpoint. Sends UDS payloads to `127.0.0.1:13400`.
- `doip_ecu.py`: DoIP ECU simulator on TCP port `13400`. It intentionally has no Flask or serial responsibilities.
- `arduino_code.cpp`: Arduino sketch that monitors `A0` and emits `LED_REAR:FAULT` or `LED_REAR:OK` over serial.

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

## Known Gotchas

- The main `server.py` `/events` endpoint emits raw SSE messages `FAULT` or `OK`, matching `index.html`.
- `server.py` starts an Arduino serial listener for the rear-left LED detector and opens the port with exclusive access.
- LED FAULT/OK transitions also create DoIP traffic on port `13400` using UDS `WriteDataByIdentifier` for DID `F1A1`.
- The dashboard stores a browser-local client ID in `localStorage` and sends it as `X-SOVD-Client`. Keep browser-triggered traces and simulation state client-scoped, but keep physical LED events global.
- `routes/api_routes.py` keeps a small in-memory client session map for browser-controlled simulation values such as ignition, speed, and demo engine faults. A phone changing ignition must not change what a laptop sees.
- `doip_ecu.py` should stay focused on DoIP so it does not compete with `server.py` for the serial port.
- Serial access expects Arduino devices at `/dev/ttyACM0`, `/dev/ttyACM1`, `/dev/ttyUSB0`, or `/dev/ttyUSB1`.

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
2. Start `server.py` for the main dashboard, vehicle API, and LED fault stream on port `5000`.
3. Open `http://localhost:5000/`.
4. Use the DID dropdown and `Execute ReadDID`.
5. Use `http://localhost:5000/test/fault` and `/test/ok` when testing notification behavior without Arduino hardware.
