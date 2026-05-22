import socket
import struct
import threading
import time
import serial

from flask import Flask, Response, render_template
from data.vehicle_state import vehicle_state

HOST = "0.0.0.0"
PORT = 13400

WEB_HOST = "0.0.0.0"
WEB_PORT = 5001

BAUDRATE = 9600
POSSIBLE_PORTS = [
    "/dev/ttyACM0",
    "/dev/ttyACM1",
    "/dev/ttyUSB0",
    "/dev/ttyUSB1"
]

DIDS = {
    "F190": "WVWZZZ12345678901",
    "F187": "SW_VER_1.0.0",
    "F18C": "HW_VER_A1",
    "F40C": "3500",
    "F40D": "45%",
    "F40E": "92C"
}

# =====================================================
# ESTADO INTERNO VEHÍCULO
# =====================================================

if "rear_left_light" not in vehicle_state:
    vehicle_state["rear_left_light"] = {
        "fault_active": False,
        "fault_code": None,
        "fault_name": None,
        "severity": None
    }

state_lock = threading.Lock()

def set_fault_active():
    with state_lock:
        vehicle_state["rear_left_light"]["fault_active"] = True
        vehicle_state["rear_left_light"]["fault_code"] = "B1234"
        vehicle_state["rear_left_light"]["fault_name"] = "Rear left LED failure"
        vehicle_state["rear_left_light"]["severity"] = "warning"

    print("[ECU] Fallo activo:", vehicle_state["rear_left_light"], flush=True)

def clear_fault():
    with state_lock:
        vehicle_state["rear_left_light"]["fault_active"] = False
        vehicle_state["rear_left_light"]["fault_code"] = None
        vehicle_state["rear_left_light"]["fault_name"] = None
        vehicle_state["rear_left_light"]["severity"] = None

    print("[ECU] Fallo eliminado:", vehicle_state["rear_left_light"], flush=True)


# =====================================================
# LECTURA SERIAL DESDE ARDUINO
# =====================================================

def find_serial_port():
    for port in POSSIBLE_PORTS:
        try:
            ser = serial.Serial(port, BAUDRATE, timeout=1)
            print(f"[ECU] ✅ Conectado a {port}", flush=True)
            return ser
        except Exception:
            continue

    raise Exception("[ECU] ❌ No se encontró ningún puerto serial disponible")

def serial_listener():
    while True:
        try:
            ser = find_serial_port()

            # Esperar a que Arduino reinicie al abrir el puerto serie
            time.sleep(2)

            # Limpiar basura inicial
            ser.reset_input_buffer()

            print("[ECU] Escuchando en puerto serial...", flush=True)

            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()

                if not line:
                    continue

                print("[ECU][SERIAL] RX:", line, flush=True)

                if line == "LED_REAR:FAULT":
                    set_fault_active()

                elif line == "LED_REAR:OK":
                    clear_fault()

                else:
                    # ignorar ruido o mensajes no válidos
                    pass

        except Exception as e:
            print("[ECU][SERIAL] ERROR:", e, flush=True)
            print("[ECU][SERIAL] Reintentando en 2 segundos...", flush=True)
            time.sleep(2)


# =====================================================
# SERVIDOR WEB + SSE PARA NOTIFICACIONES ACTIVAS
# =====================================================

app = Flask(__name__)

def event_stream():
    last_sent = None

    while True:
        with state_lock:
            current_state = vehicle_state["rear_left_light"]["fault_active"]

        if current_state != last_sent:
            last_sent = current_state

            if current_state:
                yield "data: FAULT\n\n"
            else:
                yield "data: OK\n\n"

        time.sleep(0.2)

@app.route("/")
def index():
    return render_template("notification_client.html")

@app.route("/events")
def events():
    return Response(event_stream(), mimetype="text/event-stream")

def run_web_server():
    print(f"[ECU] Web notification server on port {WEB_PORT}", flush=True)
    app.run(host=WEB_HOST, port=WEB_PORT, threaded=True, use_reloader=False)


# =====================================================
# DOIP ECU SERVER SIMULATION
# =====================================================

def run_doip_ecu():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind((HOST, PORT))
    sock.listen(5)

    print("DoIP ECU listening on port 13400", flush=True)

    while True:
        conn, addr = sock.accept()
        print(f"Connection from {addr}", flush=True)

        while True:
            try:
                data = conn.recv(4096)

            except ConnectionResetError:
                print("Client connection closed unexpectedly", flush=True)
                break

            if not data:
                print("Client disconnected", flush=True)
                break

            try:
                if len(data) < 12:
                    print("Invalid DoIP packet: too short", flush=True)
                    continue

                # ========= PARSE DOIP HEADER =========
                version, inverse, payload_type, payload_length = struct.unpack("!BBHI", data[:8])

                payload = data[8:8 + payload_length]

                if len(payload) < 4:
                    print("Invalid DoIP payload: too short", flush=True)
                    continue

                # ========= EXTRAER DIRECCIONES =========
                source_addr, target_addr = struct.unpack("!HH", payload[:4])

                # ========= EXTRAER UDS =========
                uds = payload[4:]
                print("UDS:", uds.hex(), flush=True)

                # ========= LA ECU LEE SU ESTADO INTERNO =========
                with state_lock:
                    rear_left_fault = vehicle_state["rear_left_light"]["fault_active"]

                if rear_left_fault:
                    print("[ECU INTERNAL STATE] Rear left light fault ACTIVE", flush=True)
                else:
                    print("[ECU INTERNAL STATE] Rear left light OK", flush=True)

                # ========= RESPUESTAS UDS =========
                if len(uds) == 0:
                    uds_response = b"\x7F\x00\x13"

                # ========= TESTER PRESENT =========
                elif uds.startswith(b"\x3E"):
                    uds_response = b"\x7E\x00"

                # ========= READ DATA BY IDENTIFIER =========
                elif uds.startswith(b"\x22"):
                    if len(uds) < 3:
                        uds_response = b"\x7F\x22\x13"

                    else:
                        did_hex = uds[1:3].hex().upper()
                        print("DID REQUESTED:", did_hex, flush=True)

                        if did_hex in DIDS:
                            value = DIDS[did_hex].encode("ascii")
                            uds_response = (
                                b"\x62"
                                + bytes.fromhex(did_hex)
                                + value
                            )
                            print("POSITIVE RESPONSE FOR:", did_hex, flush=True)

                        else:
                            print("DID NOT SUPPORTED:", did_hex, flush=True)
                            uds_response = b"\x7F\x22\x31"

                # ========= SERVICE NOT SUPPORTED =========
                else:
                    service_id = uds[:1]
                    uds_response = (b"\x7F" + service_id + b"\x11")

                # ========= BUILD DOIP RESPONSE =========
                response_payload_length = 4 + len(uds_response)

                doip_response = (
                    struct.pack(
                        "!BBHI",
                        0x02,
                        0xFD,
                        0x8001,
                        response_payload_length
                    )
                    + struct.pack(
                        "!HH",
                        target_addr,
                        source_addr
                    )
                    + uds_response
                )

                conn.sendall(doip_response)
                print("RESPONSE SENT:", doip_response.hex(), flush=True)

            except Exception as e:
                print("ERROR:", e, flush=True)

        conn.close()


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    # Hilo que escucha el Arduino
    threading.Thread(target=serial_listener, daemon=True).start()

    # Hilo del servidor web para la notificación activa
    threading.Thread(target=run_web_server, daemon=True).start()

    # La ECU DoIP corre en el hilo principal
    run_doip_ecu()