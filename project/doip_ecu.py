import socket
import struct

HOST = "0.0.0.0"
PORT = 13400

DIDS = {
    "F190": "WVWZZZ12345678901",
    "F187": "SW_VER_1.0.0",
    "F18C": "HW_VER_A1",
    "F40C": "3500",
    "F40D": "45%",
    "F40E": "92C",
    "F1A1": "LED_REAR:OK",
    "F1A2": "LED_FRONT:OK",
    "F1A3": "CRASH:OK",
}

def build_doip_response(source_addr, target_addr, uds_response):
    response_payload = struct.pack("!HH", target_addr, source_addr) + uds_response
    header = struct.pack("!BBHI", 0x02, 0xFD, 0x8001, len(response_payload))
    return header + response_payload


def handle_uds_request(uds):
    if not uds:
        return b"\x7F\x00\x13"

    if uds.startswith(b"\x3E"):
        return b"\x7E\x00"

    if uds.startswith(b"\x22"):
        if len(uds) < 3:
            return b"\x7F\x22\x13"

        did_hex = uds[1:3].hex().upper()
        print("DID REQUESTED:", did_hex, flush=True)

        if did_hex not in DIDS:
            print("DID NOT SUPPORTED:", did_hex, flush=True)
            return b"\x7F\x22\x31"

        value = DIDS[did_hex].encode("ascii")
        print("POSITIVE RESPONSE FOR:", did_hex, flush=True)
        return b"\x62" + bytes.fromhex(did_hex) + value

    if uds.startswith(b"\x2E"):
        if len(uds) < 4:
            return b"\x7F\x2E\x13"

        did_hex = uds[1:3].hex().upper()
        value = uds[3:].decode("ascii", errors="ignore")

        print("WRITE DID REQUESTED:", did_hex, value, flush=True)

        if did_hex not in ("F1A1", "F1A2", "F1A3"):
            print("WRITE DID NOT SUPPORTED:", did_hex, flush=True)
            return b"\x7F\x2E\x31"

        DIDS[did_hex] = value
        return b"\x6E" + bytes.fromhex(did_hex)

    return b"\x7F" + uds[:1] + b"\x11"


def handle_connection(conn):
    while True:
        try:
            data = conn.recv(4096)
        except ConnectionResetError:
            print("Client connection closed unexpectedly", flush=True)
            break

        if not data:
            print("Client disconnected", flush=True)
            break

        if len(data) < 12:
            print("Invalid DoIP packet: too short", flush=True)
            continue

        try:
            _, _, _, payload_length = struct.unpack("!BBHI", data[:8])
            payload = data[8:8 + payload_length]

            if len(payload) < 4:
                print("Invalid DoIP payload: too short", flush=True)
                continue

            source_addr, target_addr = struct.unpack("!HH", payload[:4])
            uds = payload[4:]

            print("UDS:", uds.hex(), flush=True)

            uds_response = handle_uds_request(uds)
            doip_response = build_doip_response(source_addr, target_addr, uds_response)

            conn.sendall(doip_response)
            print("RESPONSE SENT:", doip_response.hex(), flush=True)

        except Exception as e:
            print("ERROR:", e, flush=True)


def run_doip_ecu():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))
    sock.listen(5)

    print(f"DoIP ECU listening on port {PORT}", flush=True)

    while True:
        conn, addr = sock.accept()
        print(f"Connection from {addr}", flush=True)

        try:
            handle_connection(conn)
        finally:
            conn.close()


if __name__ == "__main__":
    run_doip_ecu()
