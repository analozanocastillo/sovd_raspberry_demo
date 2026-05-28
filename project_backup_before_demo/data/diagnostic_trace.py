from collections import deque
from datetime import datetime
import threading

MAX_TRACE_ITEMS = 100

diagnostic_events = deque(maxlen=MAX_TRACE_ITEMS)
_trace_lock = threading.Lock()
_next_id = 1


def add_trace(source, direction, message, detail=None, level="info", client_id=None, global_event=False):
    global _next_id

    with _trace_lock:
        item = {
            "id": _next_id,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "source": source,
            "direction": direction,
            "level": level,
            "message": message,
            "detail": detail,
            "client_id": client_id,
            "scope": "global" if global_event else "client",
        }
        _next_id += 1
        diagnostic_events.append(item)
        return item


def get_trace(limit=80, client_id=None):
    with _trace_lock:
        items = [
            item for item in diagnostic_events
            if item.get("scope") == "global" or item.get("client_id") == client_id
        ]

    if limit is None:
        return items

    return items[-limit:]
