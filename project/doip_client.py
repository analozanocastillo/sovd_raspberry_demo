import socket
import struct
import time

DOIP_IP = "127.0.0.1"   # dentro de la Raspberry
DOIP_PORT = 13400

SOURCE_ADDR = 0x0E80  # tester
TARGET_ADDR = 0x1010  # ECU

def _build_doip_diag(uds_payload: bytes) -> bytes:
    protocol_version = 0x02
    inverse_version = 0xFD
    payload_type = 0x8001  # Diagnostic Message

    payload_length = 4 + len(uds_payload)  # src(2)+tgt(2)+uds

    header = struct.pack("!BBHI", protocol_version, inverse_version, payload_type, payload_length)
    payload = struct.pack("!HH", SOURCE_ADDR, TARGET_ADDR) + uds_payload
    return header + payload

def send_uds_sequence(uds_hex_list, delay_s=0.2, recv_timeout_s=1.0):
    """
    Envía varios UDS (hex string tipo '3E00', '22F190') en UNA sola conexión TCP DoIP.
    Devuelve lista con (req_hex, reply_hex_o_None)
    """
    results = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(recv_timeout_s)
    sock.connect((DOIP_IP, DOIP_PORT))

    for uds_hex in uds_hex_list:
        uds_payload = bytes.fromhex(uds_hex)
        pkt = _build_doip_diag(uds_payload)
        sock.sendall(pkt)

        # We try to read a response (If doip_ecu.py responds)
        reply = None
        try:
            data = sock.recv(4096)
            if data:
                reply = data.hex()
        except socket.timeout:
            reply = None

        results.append((uds_hex, reply))
        time.sleep(delay_s)

    sock.close()
    return results
    return results
