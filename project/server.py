from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from urllib.parse import urlparse

from routes.api_routes import handle_api
from routes.ui_routes import handle_ui

HOST = "0.0.0.0"
PORT = 5000

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

        # 1) UI
        ui = handle_ui(path)
        if ui:
            filepath, ctype = ui
            return self._send_file(filepath, ctype)

        # 2) API
        api = handle_api(path)
        if api:
            status, payload = api
            return self._send_json(status, payload)

        # 3) Default
        return self._send_json(404, {"error": "Not found"})

print("SOVD demo server running on port 5000")
HTTPServer((HOST, PORT), Handler).serve_forever()
