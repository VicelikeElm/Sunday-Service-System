# -*- coding: utf-8 -*-
"""Pure helpers for shaping performance-timing data.

No Tkinter, no OBS, no file I/O - callers gather the actual timings and
call these to shape the dict that gets written to PERFORMANCE_FILE. Kept
separate so this can be unit-tested with synthetic inputs, same reasoning
as sunday_state_engine.py.
"""


def mark_startup(data, name, elapsed_ms):
    data.setdefault("startup", {})[name] = round(elapsed_ms, 1)
    return data


def record_operation(data, name, duration_ms, at):
    data.setdefault("operations", {})[name] = {
        "duration_ms": round(duration_ms, 1),
        "at": at,
    }
    return data
