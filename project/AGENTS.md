# Project Context

This repository is an educational SOVD/DoIP vehicle diagnostics demo intended for Raspberry Pi style experiments. It combines a Flask REST dashboard, a simulated DoIP ECU, UDS ReadDataByIdentifier handling, and an Arduino-driven rear-left LED fault notification flow.

## Main Pieces

- `server.py`: Main Flask app on port `5000`. Serves the dashboard, REST API endpoints, POST UDS endpoint, Arduino rear-left LED serial monitoring, test fault endpoints, and an SSE `/events` stream.
- `routes/api_routes.py`: API routing logic for vehicle data, ignition/fault simulation, speed simulation, and `/uds/readDataByIdentifier`.
- `routes/ui_routes.py`: Maps `/` and `/ui` to `index.html`.
- `data/simulated_data.py`: In-memory vehicle, power, component, engine, sensor, and fault data.
- `data/vehicle_state.py`: Shared in-memory state for the rear-left light fault.
- `index.html`: Main browser dashboard for vehicle identity, power telemetry, ignition controls, UDS DID reads, terminal-style logs, and SSE popup notifications.
- `doip_client.py`: TCP DoIP client helper used by the REST UDS endpoint. Sends UDS payloads to `127.0.0.1:13400`.
- `doip_ecu.py`: Current combined DoIP ECU simulator plus web notification server. It listens on DoIP port `13400`, starts a Flask notification UI on port `5001`, and exposes test endpoints. Its serial listener is disabled by default with `USE_SERIAL = False` so `server.py` can own the Arduino detector.
- `ecu.py`: Older/similar ECU simulator implementation with DoIP, serial, and notification server behavior.
- `event_server.py`: Separate Arduino/SSE notification server on port `5001`.
- `templates/notification_client.html`: Standalone notification UI that listens to `/events`.
- `arduino_code.cpp`: Arduino sketch that monitors `A0` and emits `LED_REAR:FAULT` or `LED_REAR:OK` over serial.
- `uds_tester.py`: Simple standalone DoIP tester using a hardcoded remote IP.

## How To Run

Main SOVD REST/dashboard server:

```bash
python3 server.py
```

Open:

```text
http://localhost:5000/
```

Combined DoIP ECU and notification server:

```bash
python3 doip_ecu.py
```

Notification UI:

```text
http://localhost:5001/notification
```

Useful test endpoints in `doip_ecu.py`:

```text
http://localhost:5001/test/fault
http://localhost:5001/test/ok
```

The main `server.py` app also exposes the same LED simulation endpoints on port `5000`:

```text
http://localhost:5000/test/fault
http://localhost:5000/test/ok
```

## API Shape

Common GET endpoints:

- `/vehicle`
- `/vehicle/power`
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

## Known Gotchas

- The main `server.py` `/events` endpoint emits raw SSE messages `FAULT` or `OK`, matching `index.html`.
- `server.py` starts an Arduino serial listener for the rear-left LED detector and opens the port with exclusive access. Keep `doip_ecu.py` serial disabled unless intentionally testing the old port `5001` flow.
- `routes/api_routes.py` contains an `init_routes(app)` function with another `/events` endpoint, but `server.py` does not call it.
- There is overlap between `event_server.py`, `ecu.py`, and `doip_ecu.py`. Treat `doip_ecu.py` as the likely current active combined ECU implementation unless the user says otherwise.
- `doip_client.py` has a duplicate `return results` at the end.
- `uds_tester.py` targets `192.168.1.39`, while the main REST DoIP client targets `127.0.0.1`.
- Serial access expects Arduino devices at `/dev/ttyACM0`, `/dev/ttyACM1`, `/dev/ttyUSB0`, or `/dev/ttyUSB1`.

## Development Notes

- This project stores state in Python module-level dictionaries; there is no database.
- The Flask apps are development/demo servers, not production services.
- Existing files include Spanish comments and UI text. Preserve that style where appropriate.
- Be careful with `doip_ecu.py` and `index.html`: they may already contain user edits.
- Before changing behavior, check which server the user is actually running: `server.py`, `doip_ecu.py`, `ecu.py`, or `event_server.py`.

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
