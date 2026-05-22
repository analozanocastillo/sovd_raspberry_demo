from flask import Flask, Response, render_template, request, jsonify
import time
import threading
import serial

app = Flask(__name__)

BAUDRATE = 9600

POSSIBLE_PORTS = [
    "/dev/ttyACM0",
    "/dev/ttyACM1",
    "/dev/ttyUSB0",
    "/dev/ttyUSB1"
]

fault_active = True
USE_SERIAL = True


# ------------------------
# AUTODETECCIÓN DE PUERTO
# ------------------------

def find_serial_port():
    for port in POSSIBLE_PORTS:
        try:
            ser = serial.Serial(port, BAUDRATE, timeout=1)
            print(f"✅ Conectado a {port}")
            return ser
        except:
            continue

    raise Exception("❌ No se encontró ningún puerto serial disponible")


# ------------------------
# LECTURA DEL ARDUINO
# ------------------------

def serial_reader():
    global fault_active

    while True:
        try:
            ser = find_serial_port()

            time.sleep(2)
            ser.reset_input_buffer()

            print("Escuchando en puerto serial...")

            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip().upper()

                if not line:
                    continue

                print("RX:", repr(line))

                if "FAULT" in line:
                    print(">>> DETECTADO FAULT")
                    set_fault_state(True)

                elif "OK" in line:
                    print(">>> DETECTADO OK")
                    set_fault_state(False)

                else:
                    print("Mensaje desconocido:", line)

        except Exception as e:
            print("Error serial:", e)
            print("Reintentando en 2 segundos...")
            time.sleep(2)


def set_fault_state(state: bool):
    global fault_active
    fault_active = state


# ------------------------
# SSE
# ------------------------

def event_stream():
    last_sent = None

    while True:
        if fault_active != last_sent:
            last_sent = fault_active

            if fault_active:
                yield "data: FAULT\n\n"
            else:
                yield "data: OK\n\n"

        time.sleep(0.2)


@app.route("/")
def index():
    return render_template("notification_client.html")


@app.route("/events")
def events():
    if request.headers.get("accept") == "text/event-stream":
        return Response(event_stream(), mimetype="text/event-stream")

    state = request.args.get("state")

    if state == "fault":
        set_fault_state(True)
        return jsonify({"result": "FAULT set"})

    elif state == "ok":
        set_fault_state(False)
        return jsonify({"result": "OK set"})

    else:
        return jsonify({"error": "Missing or invalid state"}), 400


# ------------------------
# MAIN
# ------------------------

if __name__ == "__main__":
    if USE_SERIAL:
        threading.Thread(target=serial_reader, daemon=True).start()

    app.run(host="0.0.0.0", port=5001)