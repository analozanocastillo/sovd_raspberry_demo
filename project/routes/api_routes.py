from data.simulated_data import DATA
from data.diagnostic_trace import add_trace
from doip_client import send_uds_sequence
import struct


def handle_api(path):
    # ========= VEHICLE =========
    if path == "/vehicle":
        return 200, DATA["vehicle"]

    if path == "/vehicle/power":
        return 200, DATA["power"]

    # ========= COMPONENTS =========
    if path == "/components":
        if DATA["vehicle"]["ignition"] == "OFF":
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
        if not DATA["engine"]["faults_active"]:
            return 200, {"faults": []}
        return 200, {"faults": DATA["engine"]["faults"]}

    # ========= STATE CONTROL (SIMULATION) =========
    if path == "/ignition/on":
        DATA["vehicle"]["ignition"] = "ON"
        add_trace("Vehicle", "action", "Ignition switched ON", "GET /ignition/on", "event")
        return 200, {"ignition": "ON"}

    if path == "/ignition/off":
        DATA["vehicle"]["ignition"] = "OFF"
        DATA["vehicle"]["speed_kmh"] = 0
        add_trace("Vehicle", "action", "Ignition switched OFF", "GET /ignition/off", "event")
        return 200, {"ignition": "OFF"}

    if path == "/faults/on":
        DATA["engine"]["faults_active"] = True
        add_trace("Vehicle", "action", "Engine demo faults enabled", "GET /faults/on", "event")
        return 200, {"faults_active": True}

    if path == "/faults/off":
        DATA["engine"]["faults_active"] = False
        add_trace("Vehicle", "action", "Engine demo faults cleared", "GET /faults/off", "event")
        return 200, {"faults_active": False}

    if path == "/vehicle/speed":
        return 200, {
            "speed_kmh": DATA["vehicle"].get("speed_kmh", 0)
        }

    if path.startswith("/vehicle/speed/"):
        try:
            value = int(path.split("/")[-1])
            DATA["vehicle"]["speed_kmh"] = value
            add_trace("Vehicle", "action", "Vehicle speed updated", f"{value} km/h", "event")
            return 200, {"speed_kmh": value}
        except ValueError:
            return 400, {"error": "Invalid speed"}

    return None


def handle_post(path, body):
    if path == "/uds/readDataByIdentifier":
        # Did validation =================================
        did = (body or {}).get("did")

        if not did:
            return 400, {"error": "Missing DID"}

        did = did.strip().upper()

        # Ignition check =================================
        if DATA["vehicle"]["ignition"] == "OFF":
            return 403, {"error": "Ignition OFF"}

        # UDS Construction =================================
        try:
            uds_request = f"22{did}"
            add_trace("HTTP", "rx", "POST /uds/readDataByIdentifier", f"DID 0x{did}", "info")
            add_trace("UDS", "tx", f"ReadDataByIdentifier DID 0x{did}", uds_request, "tx")

            # DoIP Communication =================================
            results = send_uds_sequence([uds_request], delay_s=0.2, recv_timeout_s=2.0)

            _, reply = results[-1]

            if not reply:
                add_trace("DoIP", "error", "No response from ECU", uds_request, "error")
                return 502, {"error": "No response from DoIP ECU"}

            add_trace("DoIP", "rx", "Diagnostic response received", reply, "rx")

            # DOIP RESPONSE ====================================================
            # DOIP Response Parsing =================================

            data = bytes.fromhex(reply)

            if len(data) < 12:
                add_trace("DoIP", "error", "DoIP response too short", reply, "error")
                return 502, {"error": "DoIP response too short"}

            _, _, _, payload_len = struct.unpack("!BBHI", data[:8])
            payload = data[8:8 + payload_len]

            if len(payload) < 4:
                add_trace("DoIP", "error", "DoIP payload too short", payload.hex().upper(), "error")
                return 502, {"error": "DoIP payload too short"}
            uds_resp = payload[4:]

            if len(uds_resp) < 1:
                add_trace("UDS", "error", "Empty UDS response", reply, "error")
                return 502, {"error": "Empty UDS response"}

            # UDS Negative Response =================================
            # 7F 22 31 = Request Out Of Range / DID not supported

            if uds_resp[0] == 0x7F:
                nrc = uds_resp.hex().upper()
                add_trace("UDS", "error", f"Negative response for DID 0x{did}", nrc, "error")

                return 404, {
                    "error": f"DID {did} not supported",
                    "uds_response": nrc}

            # UDS Positive Response =================================
            # ReadDataByIdentifier: Request: 22 F1 87 / Response: 62 F1 87 + data

            if uds_resp[0] != 0x62 or len(uds_resp) < 3:
                add_trace("UDS", "error", "Unexpected UDS response", uds_resp.hex().upper(), "error")
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
            )

            return 200, {
                "did": resp_did,
                "name": DID_NAMES.get(resp_did, "Unknown DID"),
                "value": value
            }

        except Exception as e:
            add_trace("DoIP", "error", "DoIP request failed", str(e), "error")
            return 500, {"error": str(e)}

    return None
