import os
from os import path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # apunta a /project

def handle_ui(path):
    # UI en / o /ui
    if path == "/" or path == "/ui":
        return os.path.join(BASE_DIR, "index.html"), "text/html; charset=utf-8"


    return None  # no es UI
