from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from urllib.parse import urlparse

HOST = "0.0.0.0"
PORT = 5000

DATA = {
    "components": [
        {"id": "engine", "name": "Engine Control Unit"},
        {"id": "door", "name": "Door Control Unit"},
    ],
    "engine": {
        "vin": "WVWZZZ12345678901",
        "swversion": "1.0.0"
    }
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(BaseHTTPRequestHandler):

    def _send_json(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def _send_file(self, filepath, content_type="text/html; charset=utf-8"):
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._send_json(404, {"error": "File not found"})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1) UI: servir index.html en /
        if path == "/" or path == "/ui":
            return self._send_file(os.path.join(BASE_DIR, "index.html"))

        # 2) (Opcional) servir ficheros estáticos simples si los añades:
        #    /static/style.css  -> carpeta static/
        if path.startswith("/static/"):
            safe_path = path.replace("/", os.sep).lstrip(os.sep)
            file_path = os.path.join(BASE_DIR, safe_path)

            # content-type mínimo
            if file_path.endswith(".css"):
                return self._send_file(file_path, "text/css; charset=utf-8")
            if file_path.endswith(".js"):
                return self._send_file(file_path, "application/javascript; charset=utf-8")
            if file_path.endswith(".png"):
                return self._send_file(file_path, "image/png")
            return self._send_file(file_path, "application/octet-stream")

        # 3) API endpoints (los tuyos)
        if path == "/health":
            return self._send_json(200, {"status": "ok"})

        if path == "/components":
            return self._send_json(200, {"items": DATA["components"]})

        if path == "/components/engine/data/vin":
            return self._send_json(200, {"vin": DATA["engine"]["vin"]})

        if path == "/components/engine/data/swversion":
            return self._send_json(200, {"swversion": DATA["engine"]["swversion"]})

        # Default
        return self._send_json(404, {"error": "Not found"})

print("SOVD demo server running on port 5000")
HTTPServer((HOST, PORT), Handler).serve_forever()
