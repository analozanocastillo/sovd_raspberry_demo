from data.simulated_data import DATA
from data.diagnostic_trace import add_trace
from doip_client import send_uds_sequence
import struct
import threading


_client_state_lock = threading.Lock()
_client_states = {}


def _session_key(client_id):
    return client_id or "anonymous"


def _default_client_state():
    return {
        "vehicle": {
            "ignition": DATA["vehicle"].get("ignition", "ON"),
            "speed_kmh": DATA["vehicle"].get("speed_kmh", 0),
        },
        "engine": {
            "faults_active": DATA["engine"].get("faults_active", False),
        },
    }


def _vehicle_for_client(client_id):
    key = _session_key(client_id)
    with _client_state_lock:
        client_state = _client_states.setdefault(key, _default_client_state())
        vehicle = dict(DATA["vehicle"])
        vehicle.update(client_state["vehicle"])
        return vehicle


def _engine_faults_active_for_client(client_id):
    key = _session_key(client_id)
    with _client_state_lock:
        client_state = _client_states.setdefault(key, _default_client_state())
        return client_state["engine"]["faults_active"]


def _update_client_vehicle(client_id, **values):
    key = _session_key(client_id)
    with _client_state_lock:
        client_state = _client_states.setdefault(key, _default_client_state())
        client_state["vehicle"].update(values)


def _update_client_engine(client_id, **values):
    key = _session_key(client_id)
    with _client_state_lock:
        client_state = _client_states.setdefault(key, _default_client_state())
        client_state["engine"].update(values)


def handle_api(path, client_id=None):
    # ========= VEHICLE =========
    if path == "/vehicle":
        return 200, _vehicle_for_client(client_id)

    if path == "/vehicle/power":
        return 200, DATA["power"]

    # ========= COMPONENTS =========
    if path == "/components":
        if _vehicle_for_client(client_id)["ignition"] == "OFF":
            return 403, {"error": "Ignition OFF"}
        return 200, {"items": DATA["components"]}

    # ========= ENGINE ECU =========
    if path == "/components/engine/ident":
        return 200, DATA["engine"]["ident"]

    if path == "/components/engine/runtime":
        return 200, DATA["engine"]["runtime"]

    if path == "/components/engine/sensors":
        return 200, DATA["engine"]["sensors"]

    if path == "/components/engine/faults":
        if not _engine_faults_active_for_client(client_id):
            return 200, {"faults": []}
        return 200, {"faults": DATA["engine"]["faults"]}

    # ========= STATE CONTROL (SIMULATION) =========
    if path == "/ignition/on":
        _update_client_vehicle(client_id, ignition="ON")
        add_trace("Vehicle", "action", "Ignition switched ON", "GET /ignition/on", "event", client_id=client_id)
        return 200, {"ignition": "ON"}

    if path == "/ignition/off":
        _update_client_vehicle(client_id, ignition="OFF", speed_kmh=0)
        add_trace("Vehicle", "action", "Ignition switched OFF", "GET /ignition/off", "event", client_id=client_id)
        return 200, {"ignition": "OFF"}

    if path == "/faults/on":
        _update_client_engine(client_id, faults_active=True)
        add_trace("Vehicle", "action", "Engine demo faults enabled", "GET /faults/on", "event", client_id=client_id)
        return 200, {"faults_active": True}

    if path == "/faults/off":
        _update_client_engine(client_id, faults_active=False)
        add_trace("Vehicle", "action", "Engine demo faults cleared", "GET /faults/off", "event", client_id=client_id)
        return 200, {"faults_active": False}

    if path == "/vehicle/speed":
        return 200, {
            "speed_kmh": _vehicle_for_client(client_id).get("speed_kmh", 0)
        }

    if path.startswith("/vehicle/speed/"):
        try:
            value = int(path.split("/")[-1])
            _update_client_vehicle(client_id, speed_kmh=value)
            add_trace("Vehicle", "action", "Vehicle speed updated", f"{value} km/h", "event", client_id=client_id)
            return 200, {"speed_kmh": value}
        except ValueError:
            return 400, {"error": "Invalid speed"}

    return None


def handle_post(path, body, client_id=None):
    if path == "/uds/readDataByIdentifier":
        # Did validation =================================
        did = (body or {}).get("did")

        if not did:
            return 400, {"error": "Missing DID"}

        did = did.strip().upper()

        # Ignition check =================================
        if _vehicle_for_client(client_id)["ignition"] == "OFF":
            return 403, {"error": "Ignition OFF"}

        # UDS Construction =================================
        try:
            uds_request = f"22{did}"
            add_trace("HTTP", "rx", "POST /uds/readDataByIdentifier", f"DID 0x{did}", "info", client_id=client_id)
            add_trace("UDS", "tx", f"ReadDataByIdentifier DID 0x{did}", uds_request, "tx", client_id=client_id)

            # DoIP Communication =================================
            results = send_uds_sequence([uds_request], delay_s=0.2, recv_timeout_s=2.0)

            _, reply = results[-1]

            if not reply:
                add_trace("DoIP", "error", "No response from ECU", uds_request, "error", client_id=client_id)
                return 502, {"error": "No response from DoIP ECU"}

            add_trace("DoIP", "rx", "Diagnostic response received", reply, "rx", client_id=client_id)

            # DOIP RESPONSE ====================================================
            # DOIP Response Parsing =================================

            data = bytes.fromhex(reply)

            if len(data) < 12:
                add_trace("DoIP", "error", "DoIP response too short", reply, "error", client_id=client_id)
                return 502, {"error": "DoIP response too short"}

            _, _, _, payload_len = struct.unpack("!BBHI", data[:8])
            payload = data[8:8 + payload_len]

            if len(payload) < 4:
                add_trace("DoIP", "error", "DoIP payload too short", payload.hex().upper(), "error", client_id=client_id)
                return 502, {"error": "DoIP payload too short"}
            uds_resp = payload[4:]

            if len(uds_resp) < 1:
                add_trace("UDS", "error", "Empty UDS response", reply, "error", client_id=client_id)
                return 502, {"error": "Empty UDS response"}

            # UDS Negative Response =================================
            # 7F 22 31 = Request Out Of Range / DID not supported

            if uds_resp[0] == 0x7F:
                nrc = uds_resp.hex().upper()
                add_trace("UDS", "error", f"Negative response for DID 0x{did}", nrc, "error", client_id=client_id)

                return 404, {
                    "error": f"DID {did} not supported",
                    "uds_response": nrc}

            # UDS Positive Response =================================
            # ReadDataByIdentifier: Request: 22 F1 87 / Response: 62 F1 87 + data

            if uds_resp[0] != 0x62 or len(uds_resp) < 3:
                add_trace("UDS", "error", "Unexpected UDS response", uds_resp.hex().upper(), "error", client_id=client_id)
                return 502, {
                    "error": "Unexpected UDS response",
                    "uds_response": uds_resp.hex().upper()}

            resp_did = uds_resp[1:3].hex().upper()
            value_bytes = uds_resp[3:]

            value = value_bytes.decode(
                "ascii",
                errors="ignore"
            ).strip("\x00").strip()

            DID_NAMES = {
                "F190": "VIN",
                "F187": "Software Version",
                "F18C": "Hardware Version",
                "F40C": "Engine RPM",
                "F40D": "Engine Load",
                "F40E": "Coolant Temperature"
            }
            add_trace(
                "UDS",
                "rx",
                f"Positive response DID 0x{resp_did}",
                value,
                "rx",
                client_id=client_id,
            )

            return 200, {
                "did": resp_did,
                "name": DID_NAMES.get(resp_did, "Unknown DID"),
                "value": value
            }

        except Exception as e:
            add_trace("DoIP", "error", "DoIP request failed", str(e), "error", client_id=client_id)
            return 500, {"error": str(e)}

    return None
