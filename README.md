<<<<<<< HEAD
# sovd_raspberry_demo
SOVD prototype running on a Raspberry Pi, exposing diagnostic-style data through a RESTful HTTP server.
=======
# SOVD Raspberry Demo

Mini demo project to simulate a **SOVD-like diagnostic server** running on a Raspberry Pi.
The project exposes REST endpoints and includes a simple web interface to visualize vehicle diagnostic data.

This repository is intended as an **educational and proof-of-concept project**.

---

## 📌 Project Overview

This demo simulates the basic behavior of a Service-Oriented Vehicle Diagnostics (SOVD) server:

- A Python HTTP server running on a Raspberry Pi
- REST endpoints that expose vehicle and ECU diagnostic data
- A lightweight HTML dashboard to interact with the API via a browser

The focus of the project is to understand:
- Server / client separation
- REST-based diagnostics
- Network-accessible diagnostics services

---

## 🧩 Architecture
sovd-raspberry-demo/
├── server.py        # Python SOVD-like diagnostic server
├── index.html       # Web dashboard (HTML/CSS/JS)
├── Dockerfile       # Optional container build
└── README.md

The project follows a **simple client–server model**:
- `server.py` exposes diagnostic data as REST endpoints
- `index.html` acts as a lightweight client consuming the API

---

## 🚀 How to Run

### 1️⃣ Start the server (Raspberry Pi)

From the project root directory:

```bash
python3 server.py
>>>>>>> c7cd5aa (Initial version)
