from flask import Flask, request, jsonify, Response
from collections import deque
import threading
import time

from routes.api_routes import handle_api, handle_post
from routes.ui_routes import handle_ui
from data.vehicle_state import vehicle_state
from data.diagnostic_trace import add_trace, diagnostic_events as _diagnostic_events, get_trace
from doip_client import send_uds_sequence

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
LED_STATE_DID = "F1A1"
# Shared in-memory ring buffer: deque(maxlen=100)
diagnostic_events = _diagnostic_events


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


def send_led_state_by_uds(state):
    payload = f"LED_REAR:{state}".encode("ascii").hex().upper()
    uds_request = f"2E{LED_STATE_DID}{payload}"

    add_trace(
        "LED",
        "event",
        f"Rear-left LED state changed to {state}",
        f"LED_REAR:{state}",
        "error" if state == "FAULT" else "success",
        global_event=True,
    )
    add_trace(
        "UDS",
        "tx",
        f"WriteDataByIdentifier DID 0x{LED_STATE_DID}",
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
            f"LED state write {'acknowledged' if reply else 'timed out'}",
            reply,
            "rx" if reply else "error",
            global_event=True,
        )
        print(f"[SOVD][UDS] LED state sent: {result}", flush=True)
    except Exception as e:
        add_trace("DoIP", "error", f"Could not send LED state {state}", str(e), "error", global_event=True)
        print(f"[SOVD][UDS] Could not send LED state {state}: {e}", flush=True)


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

                if "FAULT" in line:
                    set_fault_active()
                elif "OK" in line:
                    clear_fault()

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
