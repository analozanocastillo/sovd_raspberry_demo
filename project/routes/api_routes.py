from data.simulated_data import DATA
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
        return 200, {"ignition": "ON"}

    if path == "/ignition/off":
        DATA["vehicle"]["ignition"] = "OFF"
        DATA["vehicle"]["speed_kmh"] = 0
        return 200, {"ignition": "OFF"}

    if path == "/faults/on":
        DATA["engine"]["faults_active"] = True
        return 200, {"faults_active": True}

    if path == "/faults/off":
        DATA["engine"]["faults_active"] = False
        return 200, {"faults_active": False}

    if path == "/vehicle/speed":
        return 200, {
            "speed_kmh": DATA["vehicle"].get("speed_kmh", 0)
        }

    if path.startswith("/vehicle/speed/"):
        try:
            value = int(path.split("/")[-1])
            DATA["vehicle"]["speed_kmh"] = value
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

            # DoIP Communication =================================
            results = send_uds_sequence([uds_request], delay_s=0.2, recv_timeout_s=2.0)

            _, reply = results[-1]

            if not reply:
                return 502, {"error": "No response from DoIP ECU"}

            # DOIP RESPONSE ====================================================
            # DOIP Response Parsing =================================

            data = bytes.fromhex(reply)

            if len(data) < 12:
                return 502, {"error": "DoIP response too short"}

            _, _, _, payload_len = struct.unpack("!BBHI", data[:8])
            payload = data[8:8 + payload_len]

            if len(payload) < 4:
                return 502, {"error": "DoIP payload too short"}
            uds_resp = payload[4:]

            if len(uds_resp) < 1:
                return 502, {"error": "Empty UDS response"}

            # UDS Negative Response =================================
            # 7F 22 31 = Request Out Of Range / DID not supported

            if uds_resp[0] == 0x7F:
                nrc = uds_resp.hex().upper()

                return 404, {
                    "error": f"DID {did} not supported",
                    "uds_response": nrc}

            # UDS Positive Response =================================
            # ReadDataByIdentifier: Request: 22 F1 87 / Response: 62 F1 87 + data

            if uds_resp[0] != 0x62 or len(uds_resp) < 3:
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

            return 200, {
                "did": resp_did,
                "name": DID_NAMES.get(resp_did, "Unknown DID"),
                "value": value
            }

        except Exception as e:
            return 500, {"error": str(e)}

    return None
