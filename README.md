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
```text
sovd-raspberry-demo/
├── server.py        # Python SOVD-like diagnostic server
├── index.html       # Web dashboard (HTML/CSS/JS)
├── Dockerfile       # Optional container build
└── README.md
```


The project follows a **simple client–server model**:
- `server.py` exposes diagnostic data as REST endpoints
- `index.html` acts as a lightweight client consuming the API

---

## 🚀 How to Run

### 1️⃣ Start the server (Raspberry Pi)

From the project root directory:

```bash
python3 server.py
<<<<<<< HEAD
>>>>>>> c7cd5aa (Initial version)
=======
```
You should see:

```bash
SOVD demo server running on port 5000
```


### 2️⃣ Open the web interface
From a PC or from the Raspberry Pi browser, open: 
```bash
http://172.20.10.2:5000/
```


## 🖥️ Web Interface
The web dashboard (index.html) allows you to:

- Check system health
- Visualize available ECUs
- Read vehicle identification data
- Read ECU software information

The UI communicates with the backend **via REST API calls**.


## 🎯 Project Goals

- Simulate a SOVD-like diagnostic server
- Understand REST-based diagnostics over HTTP
- Practice embedded development using Raspberry Pi
- Separate backend logic from UI visualization

## 🚫 Limitations

- This is not a full ASAM SOVD implementation
- No authentication or security mechanisms are implemented
- Intended only for learning and demonstration purposes
