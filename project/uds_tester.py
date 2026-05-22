
import socket
import struct
import time

DOIP_IP = "192.168.1.39"
DOIP_PORT = 13400

SOURCE_ADDR = 0x0E80
TARGET_ADDR = 0x1010

uds_messages = [
    ("Tester Present", bytes.fromhex("3E 00")),
    ("Read Data By Identifier (VIN)", bytes.fromhex("22 F1 90")),
]

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((DOIP_IP, DOIP_PORT))

for name, uds_payload in uds_messages:

    protocol_version = 0x02
    inverse_version = 0xFD
    payload_type = 0x8001

    payload_length = 4 + len(uds_payload)

    doip_header = struct.pack(
        "!BBHI",
        protocol_version,
        inverse_version,
        payload_type,
        payload_length
    )

    doip_payload = struct.pack(
        "!HH",
        SOURCE_ADDR,
        TARGET_ADDR
    ) + uds_payload

    doip_packet = doip_header + doip_payload

    sock.sendall(doip_packet)
    print(f"{name} sent")

    time.sleep(0.5)

sock.close()
