from data.simulated_data import DATA

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
        return 200, {"ignition": "OFF"}

    if path == "/faults/on":
        DATA["engine"]["faults_active"] = True
        return 200, {"faults_active": True}

    if path == "/faults/off":
        DATA["engine"]["faults_active"] = False
        return 200, {"faults_active": False}

    return None