from collections import deque
from datetime import datetime
import threading

MAX_TRACE_ITEMS = 100

diagnostic_events = deque(maxlen=MAX_TRACE_ITEMS)
_trace_lock = threading.Lock()
_next_id = 1


def add_trace(source, direction, message, detail=None, level="info"):
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
        }
        _next_id += 1
        diagnostic_events.append(item)
        return item


def get_trace(limit=80):
    with _trace_lock:
        items = list(diagnostic_events)

    if limit is None:
        return items

    return items[-limit:]
