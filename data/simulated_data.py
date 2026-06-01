DATA = {

    "vehicle": {
        "id": "vehicle-001",
        "brand": "DemoMotors",
        "model": "SOVD-Edu",
        "ignition": "ON",
        "uptime_s": 1234,
        "ambient_temp_c": 18.5,

        # --- SPEED SIMULATION ---
        "speed_kmh": 0,
        "speed_profile": [
            0,
            15,
            30,
            50,
            80,
            100,
            120,
            90,
            60,
            30,
            0
        ]
    },

    "power": {
        "battery_voltage": 12.4,
        "battery_current": 1.8,
        "power_mode": "NORMAL"
    },

    "components": [
        {"id": "engine", "name": "Engine Control Unit"},
        {"id": "door", "name": "Door Control Unit"}
    ],

    "engine": {
        "ident": {
            "vin": "WVWZZZ12345678901",
            "hw_version": "HW-A03",
            "sw_version": "1.0.0"
        },
        "runtime": {
            "rpm": 850,
            "engine_load": 21.3,
            "coolant_temp_c": 88.0
        },
        "sensors": {
            "throttle_pos": 14.2,
            "air_temp_c": 32.1,
            "oil_pressure_bar": 3.1
        },
        "faults_active": False,
        "faults": [
            {"code": "P0120", "description": "Throttle position sensor fault"},
            {"code": "P0300", "description": "Random misfire detected"}
        ],

    },

    "vehicle_state": {
        "rear_left_light": {
            "fault_active": False,
            "fault_code": None,
            "fault_name": None,
            "severity": None
        }
    }
}

vehicle_state = DATA["vehicle_state"]
