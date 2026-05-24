from flask import Flask, request, jsonify, Response
import threading
import time

from routes.api_routes import handle_api, handle_post
from routes.ui_routes import handle_ui
from data.vehicle_state import vehicle_state
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
LED_STATE_DID = "F1A1"


def send_led_state_by_uds(state):
    payload = f"LED_REAR:{state}".encode("ascii").hex().upper()
    uds_request = f"2E{LED_STATE_DID}{payload}"

    try:
        result = send_uds_sequence([uds_request], delay_s=0.0, recv_timeout_s=1.0)[-1]
        print(f"[SOVD][UDS] LED state sent: {result}", flush=True)
    except Exception as e:
        print(f"[SOVD][UDS] Could not send LED state {state}: {e}", flush=True)


def set_fault_active():
    with state_lock:
        vehicle_state["rear_left_light"]["fault_active"] = True
        vehicle_state["rear_left_light"]["fault_code"] = "B1234"
        vehicle_state["rear_left_light"]["fault_name"] = "Rear left LED failure"
        vehicle_state["rear_left_light"]["severity"] = "warning"

    print("[SOVD][SERIAL] Fallo activo:", vehicle_state["rear_left_light"], flush=True)
    send_led_state_by_uds("FAULT")


def clear_fault():
    with state_lock:
        vehicle_state["rear_left_light"]["fault_active"] = False
        vehicle_state["rear_left_light"]["fault_code"] = None
        vehicle_state["rear_left_light"]["fault_name"] = None
        vehicle_state["rear_left_light"]["severity"] = None

    print("[SOVD][SERIAL] Fallo eliminado:", vehicle_state["rear_left_light"], flush=True)
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

    # ===== API (GET endpoints) =====
    api = handle_api(full_path)
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

    result = handle_post(full_path, body)

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
        last_state = None

        while True:
            with state_lock:
                current = vehicle_state.get("rear_left_light", {}).get("fault_active", False)

            # Solo envía cuando cambia, usando el formato que espera index.html.
            if current != last_state:
                last_state = current

                if current:
                    yield "data: FAULT\n\n"
                else:
                    yield "data: OK\n\n"

            # Keep-alive para evitar timeouts en el navegador.
            yield ": keepalive\n\n"

            time.sleep(0.2)

    return Response(stream(), mimetype="text/event-stream")


# ============================
# RUN SERVER
# ============================
if __name__ == "__main__":
    threading.Thread(target=serial_listener, daemon=True).start()
    print(f"SOVD demo server running on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, threaded=True, use_reloader=False)
