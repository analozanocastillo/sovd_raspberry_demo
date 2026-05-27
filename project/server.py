from flask import Flask, request, jsonify, Response
from collections import deque
import threading
import time

from routes.api_routes import handle_api, handle_post
from routes.ui_routes import handle_ui
from data.vehicle_state import vehicle_state
from data.diagnostic_trace import add_trace, diagnostic_events as _diagnostic_events, get_trace
from doip_client import send_uds_sequence
from data.simulated_data import DATA

try:
    import serial
except ImportError:
    serial = None

HOST = "0.0.0.0"
PORT = 5000
BAUDRATE = 9600
POSSIBLE_PORTS = [
    "/dev/ttyACM0",
    "/dev/ttyACM1",
    "/dev/ttyUSB0",
    "/dev/ttyUSB1"
]

app = Flask(__name__)
state_lock = threading.Lock()
led_event_condition = threading.Condition()
led_events = deque(maxlen=50)
led_event_seq = 0
LED_STATE_DIDS = {
    "LED_REAR": "F1A1",
    "LED_FRONT": "F1A2",
}

led_fault_states = {
    "LED_REAR": False,
    "LED_FRONT": False,
}
# Shared in-memory ring buffer: deque(maxlen=100)
diagnostic_events = _diagnostic_events

CRASH_STATE_DID = "F1A3"

BATTERY_STATE_DID = "F1A4"

def get_client_id():
    return request.headers.get("X-SOVD-Client") or request.args.get("client_id")


def get_led_state_name():
    with state_lock:
        fault_active = vehicle_state.get("rear_left_light", {}).get("fault_active", False)

    return "FAULT" if fault_active else "OK"


def publish_led_event(state):
    global led_event_seq

    with led_event_condition:
        led_event_seq += 1
        led_events.append((led_event_seq, state))
        led_event_condition.notify_all()


def send_led_state_by_uds(led_name, state):
    did = LED_STATE_DIDS.get(led_name)

    if did is None:
        print(f"[SOVD][UDS] Unknown LED name: {led_name}", flush=True)
        return

    payload_text = f"{led_name}:{state}"
    payload = payload_text.encode("ascii").hex().upper()
    uds_request = f"2E{did}{payload}"

    human_name = "Rear LED" if led_name == "LED_REAR" else "Front LED"

    add_trace(
        "LED",
        "event",
        f"{human_name} state changed to {state}",
        payload_text,
        "error" if state == "FAULT" else "success",
        global_event=True,
    )
    add_trace(
        "UDS",
        "tx",
        f"WriteDataByIdentifier DID 0x{did}",
        uds_request,
        "tx",
        global_event=True,
    )

    try:
        result = send_uds_sequence([uds_request], delay_s=0.0, recv_timeout_s=1.0)[-1]
        _, reply = result
        add_trace(
            "DoIP",
            "rx" if reply else "error",
            f"{human_name} state write {'acknowledged' if reply else 'timed out'}",
            reply,
            "rx" if reply else "error",
            global_event=True,
        )
        print(f"[SOVD][UDS] {payload_text} sent: {result}", flush=True)
    except Exception as e:
        add_trace("DoIP", "error", f"Could not send {payload_text}", str(e), "error", global_event=True)
        print(f"[SOVD][UDS] Could not send {payload_text}: {e}", flush=True)

def handle_led_serial_message(led_name, state):
    if led_name not in LED_STATE_DIDS:
        print(f"[SOVD][SERIAL] LED desconocido: {led_name}", flush=True)
        return

    if state not in ("FAULT", "OK"):
        print(f"[SOVD][SERIAL] Estado LED desconocido: {state}", flush=True)
        return

    changed = False
    all_ok_after_update = False

    with state_lock:
        previous_fault = led_fault_states.get(led_name, False)
        new_fault = state == "FAULT"

        changed = previous_fault != new_fault
        led_fault_states[led_name] = new_fault
        all_ok_after_update = not any(led_fault_states.values())

        # Mantener compatibilidad con la lógica vieja del rear LED
        if led_name == "LED_REAR":
            vehicle_state["rear_left_light"]["fault_active"] = new_fault

            if new_fault:
                vehicle_state["rear_left_light"]["fault_code"] = "B1234"
                vehicle_state["rear_left_light"]["fault_name"] = "Rear left LED failure"
                vehicle_state["rear_left_light"]["severity"] = "warning"
            else:
                vehicle_state["rear_left_light"]["fault_code"] = None
                vehicle_state["rear_left_light"]["fault_name"] = None
                vehicle_state["rear_left_light"]["severity"] = None

    print(f"[SOVD][SERIAL] {led_name} -> {state}", flush=True)

    if changed:
        if state == "FAULT":
            publish_led_event(f"{led_name}:FAULT")
        elif state == "OK" and all_ok_after_update:
            publish_led_event("SYSTEM:OK")

    send_led_state_by_uds(led_name, state)

def send_crash_event_by_uds(duration_ms):
    payload_text = f"CRASH:FAULT:{duration_ms}"
    payload = payload_text.encode("ascii").hex().upper()
    uds_request = f"2E{CRASH_STATE_DID}{payload}"

    add_trace(
        "CRASH",
        "event",
        f"Crash detected - impact duration {duration_ms} ms",
        payload_text,
        "error",
        global_event=True,
    )
    add_trace(
        "UDS",
        "tx",
        f"WriteDataByIdentifier DID 0x{CRASH_STATE_DID}",
        uds_request,
        "tx",
        global_event=True,
    )

    try:
        result = send_uds_sequence([uds_request], delay_s=0.0, recv_timeout_s=1.0)[-1]
        _, reply = result
        add_trace(
            "DoIP",
            "rx" if reply else "error",
            f"Crash event write {'acknowledged' if reply else 'timed out'}",
            reply,
            "rx" if reply else "error",
            global_event=True,
        )
        print(f"[SOVD][UDS] {payload_text} sent: {result}", flush=True)
    except Exception as e:
        add_trace(
            "DoIP",
            "error",
            f"Could not send crash event {payload_text}",
            str(e),
            "error",
            global_event=True,
        )
        print(f"[SOVD][UDS] Could not send crash event {payload_text}: {e}", flush=True)

def handle_crash_serial_message(line):
    parts = line.split(":")
    duration_ms = "unknown"

    if len(parts) >= 3:
        duration_ms = parts[2].strip()

    print(f"[SOVD][SERIAL] CRASH detected, duration={duration_ms} ms", flush=True)

    publish_led_event(f"CRASH:FAULT:{duration_ms}")
    send_crash_event_by_uds(duration_ms)

def send_battery_event_by_uds(status, voltage):
    payload_text = f"BATTERY:{status}:{voltage}"
    payload = payload_text.encode("ascii").hex().upper()
    uds_request = f"2E{BATTERY_STATE_DID}{payload}"

    level = "error" if status in ("UNDERVOLTAGE", "OVERVOLTAGE") else "success"

    if status == "UNDERVOLTAGE":
        message = f"Battery undervoltage detected - {voltage} V"
    elif status == "OVERVOLTAGE":
        message = f"Battery overvoltage detected - {voltage} V"
    else:
        message = f"Battery voltage restored - {voltage} V"

    add_trace(
        "BATTERY",
        "event",
        message,
        payload_text,
        level,
        global_event=True,
    )
    add_trace(
        "UDS",
        "tx",
        f"WriteDataByIdentifier DID 0x{BATTERY_STATE_DID}",
        uds_request,
        "tx",
        global_event=True,
    )

    try:
        result = send_uds_sequence([uds_request], delay_s=0.0, recv_timeout_s=1.0)[-1]
        _, reply = result
        add_trace(
            "DoIP",
            "rx" if reply else "error",
            f"Battery event write {'acknowledged' if reply else 'timed out'}",
            reply,
            "rx" if reply else "error",
            global_event=True,
        )
        print(f"[SOVD][UDS] {payload_text} sent: {result}", flush=True)
    except Exception as e:
        add_trace(
            "DoIP",
            "error",
            f"Could not send battery event {payload_text}",
            str(e),
            "error",
            global_event=True,
        )
        print(f"[SOVD][UDS] Could not send battery event {payload_text}: {e}", flush=True)

def handle_battery_serial_message(line):
    parts = line.split(":")

    if len(parts) < 3:
        print(f"[SOVD][SERIAL] Invalid battery message: {line}", flush=True)
        return

    event_type = parts[1].strip()
    voltage = parts[2].strip()

    try:
        voltage_value = float(voltage)

        with state_lock:
            DATA["power"]["battery_voltage"] = voltage_value

            if event_type == "UNDERVOLTAGE":
                DATA["power"]["power_mode"] = "UNDERVOLTAGE"
            elif event_type == "OVERVOLTAGE":
                DATA["power"]["power_mode"] = "OVERVOLTAGE"
            elif event_type == "OK":
                DATA["power"]["power_mode"] = "NORMAL"

    except Exception as e:
        print(f"[SOVD][BATTERY] Could not update simulated battery voltage: {e}", flush=True)

    print(f"[SOVD][SERIAL] BATTERY {event_type} {voltage} V", flush=True)

    publish_led_event(f"BATTERY:{event_type}:{voltage}")

    if event_type in ("UNDERVOLTAGE", "OVERVOLTAGE", "OK"):
        send_battery_event_by_uds(event_type, voltage)


def set_fault_active():
    changed = False

    with state_lock:
        changed = not vehicle_state["rear_left_light"]["fault_active"]
        vehicle_state["rear_left_light"]["fault_active"] = True
        vehicle_state["rear_left_light"]["fault_code"] = "B1234"
        vehicle_state["rear_left_light"]["fault_name"] = "Rear left LED failure"
        vehicle_state["rear_left_light"]["severity"] = "warning"

    print("[SOVD][SERIAL] Fallo activo:", vehicle_state["rear_left_light"], flush=True)
    if changed:
        publish_led_event("FAULT")
    send_led_state_by_uds("FAULT")


def clear_fault():
    changed = False

    with state_lock:
        changed = vehicle_state["rear_left_light"]["fault_active"]
        vehicle_state["rear_left_light"]["fault_active"] = False
        vehicle_state["rear_left_light"]["fault_code"] = None
        vehicle_state["rear_left_light"]["fault_name"] = None
        vehicle_state["rear_left_light"]["severity"] = None

    print("[SOVD][SERIAL] Fallo eliminado:", vehicle_state["rear_left_light"], flush=True)
    if changed:
        publish_led_event("OK")
    send_led_state_by_uds("OK")


def find_serial_port():
    if serial is None:
        raise RuntimeError("pyserial is not installed")

    for port in POSSIBLE_PORTS:
        try:
            ser = serial.Serial(port, BAUDRATE, timeout=1, exclusive=True)
            print(f"[SOVD][SERIAL] Conectado a {port}", flush=True)
            return ser
        except Exception:
            continue

    raise RuntimeError("No se encontró ningún puerto serial disponible")


def serial_listener():
    if serial is None:
        print("[SOVD][SERIAL] pyserial no está instalado; detector LED desactivado", flush=True)
        return

    while True:
        try:
            ser = find_serial_port()

            # Limpiar antes de que Arduino emita su estado inicial tras el reset.
            ser.reset_input_buffer()
            time.sleep(2)

            print("[SOVD][SERIAL] Escuchando en puerto serial...", flush=True)

            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip().upper()

                if not line:
                    continue

                print("[SOVD][SERIAL] RX:", repr(line), flush=True)

                if line.startswith("BATTERY:"):
                    handle_battery_serial_message(line)

                elif line.startswith("CRASH:FAULT"):
                    handle_crash_serial_message(line)

                elif ":" in line:
                    led_name, state = line.split(":", 1)
                    handle_led_serial_message(led_name.strip(), state.strip())

                elif "FAULT" in line:
                    handle_led_serial_message("LED_REAR", "FAULT")

                elif "OK" in line:
                    handle_led_serial_message("LED_REAR", "OK")

        except Exception as e:
            print("[SOVD][SERIAL] ERROR:", e, flush=True)
            print("[SOVD][SERIAL] Reintentando en 2 segundos...", flush=True)
            time.sleep(2)


# ============================
# GET ROUTES (UI + API)
# ============================
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def handle_get(path):

    full_path = "/" + path

    # ===== UI (HTML, CSS, JS) =====
    ui = handle_ui(full_path)
    if ui:
        filepath, ctype = ui
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            return Response(content, content_type=ctype)
        except FileNotFoundError:
            return jsonify({"error": "File not found"}), 404

    # ===== LED FAULT SIMULATION =====
    if full_path == "/test/fault":
        set_fault_active()
        return jsonify({
            "status": "fault_active",
            "vehicle_state": vehicle_state["rear_left_light"]
        })

    if full_path == "/test/ok":
        clear_fault()
        return jsonify({
            "status": "fault_cleared",
            "vehicle_state": vehicle_state["rear_left_light"]
        })

    # ===== DIAGNOSTIC TRACE =====
    if full_path == "/diagnostics/trace":
        client_id = get_client_id()
        try:
            limit = int(request.args.get("limit", 80))
        except ValueError:
            limit = 80

        limit = max(1, min(limit, diagnostic_events.maxlen))
        return jsonify({"items": get_trace(limit, client_id=client_id)})

    # ===== API (GET endpoints) =====
    client_id = get_client_id()
    api = handle_api(full_path, client_id=client_id)
    if api is not None:
        status, payload = api
        return jsonify(payload), status

    # ===== DEFAULT =====
    return jsonify({"error": "Not found"}), 404


# ============================
# POST ROUTES (UDS, etc.)
# ============================
@app.route("/<path:path>", methods=["POST"])
def handle_post_requests(path):

    full_path = "/" + path

    try:
        body = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    result = handle_post(full_path, body, client_id=get_client_id())

    if result is not None:
        status, payload = result
        return jsonify(payload), status

    return jsonify({"error": "Not found"}), 404


# ============================
# SSE EVENTS (REALTIME)
# ============================
@app.route("/events")
def events():

    def stream():
        with led_event_condition:
            last_event_id = led_event_seq

        # Estado inicial para que el navegador pinte el indicador al conectar.
        yield f"data: {get_led_state_name()}\n\n"

        while True:
            with led_event_condition:
                led_event_condition.wait_for(
                    lambda: led_events and led_events[-1][0] > last_event_id,
                    timeout=15,
                )
                pending_events = [
                    (event_id, state)
                    for event_id, state in led_events
                    if event_id > last_event_id
                ]

            if pending_events:
                for event_id, state in pending_events:
                    last_event_id = event_id
                    yield f"data: {state}\n\n"
            else:
                # Keep-alive para evitar timeouts en el navegador.
                yield ": keepalive\n\n"

    return Response(stream(), mimetype="text/event-stream")


# ============================
# RUN SERVER
# ============================
if __name__ == "__main__":
    threading.Thread(target=serial_listener, daemon=True).start()
    print(f"SOVD demo server running on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, threaded=True, use_reloader=False)
