from flask import Flask, request, jsonify, Response
import json
import time

from routes.api_routes import handle_api, handle_post
from routes.ui_routes import handle_ui
from data.vehicle_state import vehicle_state

HOST = "0.0.0.0"
PORT = 5000

app = Flask(__name__)


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
            current = vehicle_state.get("rear_left_light", {}).get("fault_active", False)

            # ✅ Solo envía cuando cambia
            if current != last_state:
                last_state = current

                yield f"data: {json.dumps({'fault_active': current})}\n\n"

            # ✅ Keep-alive (evita timeout navegador)
            yield ": keepalive\n\n"

            time.sleep(0.5)

    return Response(stream(), mimetype="text/event-stream")


# ============================
# RUN SERVER
# ============================
if __name__ == "__main__":
    print(f"SOVD demo server running on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, threaded=True, use_reloader=False)
