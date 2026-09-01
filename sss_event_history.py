import datetime
import json
import os
from pathlib import Path


BASE = Path(r"C:\Church\SermonAI")
EVENT_ROOT = BASE / "Event History"
SESSION_STATE_FILE = EVENT_ROOT / "session_state.json"
LAST_CRASH_FILE = EVENT_ROOT / "last_unexpected_shutdown.json"

EVENT_SCHEMA_VERSION = 1


def _now():
    return datetime.datetime.now().astimezone()


def _now_iso():
    return _now().isoformat()


def prune_event_history(
    retention_days=90
):
    ensure_event_root()

    cutoff = (
        _now().date()
        -
        datetime.timedelta(
            days=max(
                1,
                int(
                    retention_days
                )
            )
        )
    )

    removed = 0

    for path in EVENT_ROOT.glob(
        "*.jsonl"
    ):
        try:
            day = datetime.date.fromisoformat(
                path.stem
            )
        except Exception:
            continue

        if day < cutoff:
            try:
                path.unlink()
                removed += 1
            except Exception:
                pass

    return removed


def _today_file():
    return (
        EVENT_ROOT
        /
        (
            _now().date().isoformat()
            +
            ".jsonl"
        )
    )


def ensure_event_root():
    EVENT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    return EVENT_ROOT


def _write_json_atomic(
    path,
    payload
):
    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_suffix(
        path.suffix
        +
        ".tmp"
    )

    temp.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        +
        "\n",
        encoding="utf-8",
    )

    os.replace(
        temp,
        path,
    )


def _read_json(
    path,
    default=None
):
    if default is None:
        default = {}

    try:
        payload = json.loads(
            Path(
                path
            ).read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            payload,
            dict
        ):
            return payload

    except Exception:
        pass

    return default


def _pid_running(
    pid
):
    try:
        pid = int(
            pid
        )
    except Exception:
        return False

    if pid <= 0:
        return False

    if pid == os.getpid():
        return True

    if os.name == "nt":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION,
                False,
                pid,
            )

            if not handle:
                return False

            ctypes.windll.kernel32.CloseHandle(
                handle
            )

            return True

        except Exception:
            return False

    try:
        os.kill(
            pid,
            0,
        )

        return True

    except Exception:
        return False


def _classify_message(
    message
):
    text = str(
        message
        or
        ""
    )

    lower = text.lower()

    if (
        "credential"
        in lower
        or
        "vault"
        in lower
        or
        "secret"
        in lower
    ):
        category = "SECURITY"
    elif "record" in lower:
        category = "RECORDING"
    elif "stream" in lower:
        category = "STREAMING"
    elif (
        "audio"
        in lower
        or
        "mute"
        in lower
    ):
        category = "AUDIO"
    elif (
        "camera"
        in lower
        or
        "ptz"
        in lower
        or
        "worship view"
        in lower
        or
        "pastor view"
        in lower
    ):
        category = "CAMERA"
    elif "scripture" in lower:
        category = "SCRIPTURE"
    elif (
        "chapter"
        in lower
        or
        "lower third"
        in lower
        or
        "sermon"
        in lower
    ):
        category = "SERMON"
    elif (
        "presenter"
        in lower
        or
        "propresenter"
        in lower
        or
        "presentation"
        in lower
    ):
        category = "PRESENTATION"
    elif "planning" in lower:
        category = "PLANNING"
    elif "youtube" in lower:
        category = "YOUTUBE"
    elif "obs" in lower:
        category = "OBS"
    elif (
        "recovery"
        in lower
        or
        "snapshot"
        in lower
        or
        "diagnostic"
        in lower
    ):
        category = "SYSTEM"
    else:
        category = "SYSTEM"

    if any(
        word
        in lower
        for word in (
            "failed",
            "failure",
            "error",
            "missing",
            "warning",
            "could not",
            "not reachable",
            "problem",
        )
    ):
        level = "WARNING"

    elif any(
        word
        in lower
        for word in (
            "start",
            "stop",
            "requested",
            "moved",
            "selected",
            "loaded",
            "saved",
            "synced",
            "applied",
            "reset",
            "unmuted",
            "muted",
        )
    ):
        level = "ACTION"

    else:
        level = "INFO"

    return (
        category,
        level,
    )


def record_event(
    message,
    *,
    category=None,
    level=None,
    source="SSS",
    metadata=None
):
    ensure_event_root()

    message = " ".join(
        str(
            message
            or
            ""
        ).split()
    )

    if not message:
        return None

    inferred_category, inferred_level = _classify_message(
        message
    )

    event = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "timestamp": _now_iso(),
        "category": str(
            category
            or
            inferred_category
        ).upper(),
        "level": str(
            level
            or
            inferred_level
        ).upper(),
        "source": str(
            source
            or
            "SSS"
        ),
        "message": message,
        "pid": os.getpid(),
    }

    if isinstance(
        metadata,
        dict
    ) and metadata:
        event[
            "metadata"
        ] = metadata

    target = _today_file()

    with target.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                event,
                ensure_ascii=False,
            )
            +
            "\n"
        )

    return event


def current_session_state():
    return _read_json(
        SESSION_STATE_FILE,
        {}
    )


def get_last_unexpected_shutdown():
    return _read_json(
        LAST_CRASH_FILE,
        {}
    )


def start_session(
    *,
    profile_name=""
):
    """
    Start a new main-SSS session and return the previous unexpected-session
    record if one exists.

    If the old PID is still alive, it is treated as another active SSS process
    rather than a crash.
    """
    ensure_event_root()

    try:
        prune_event_history(
            retention_days=90
        )
    except Exception:
        pass

    previous = current_session_state()
    unexpected = None

    if (
        previous.get(
            "state"
        )
        ==
        "RUNNING"
    ):
        old_pid = previous.get(
            "pid"
        )

        if not _pid_running(
            old_pid
        ):
            unexpected = dict(
                previous
            )

            unexpected[
                "detected_at"
            ] = _now_iso()

            unexpected[
                "reason"
            ] = (
                "The previous SSS session did not record a normal shutdown."
            )

            _write_json_atomic(
                LAST_CRASH_FILE,
                unexpected,
            )

            record_event(
                (
                    "Previous SSS session ended unexpectedly. "
                    "Startup recovery review is available."
                ),
                category="RECOVERY",
                level="WARNING",
                source="SESSION",
                metadata={
                    "previous_pid": old_pid,
                    "previous_started_at": previous.get(
                        "started_at",
                        ""
                    ),
                    "previous_heartbeat_at": previous.get(
                        "heartbeat_at",
                        ""
                    ),
                },
            )

    state = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "state": "RUNNING",
        "pid": os.getpid(),
        "started_at": _now_iso(),
        "heartbeat_at": _now_iso(),
        "profile_name": str(
            profile_name
            or
            ""
        ),
        "last_event": "",
        "last_event_at": "",
        "recording": None,
        "streaming": None,
        "clean_shutdown_at": "",
    }

    _write_json_atomic(
        SESSION_STATE_FILE,
        state,
    )

    record_event(
        "Sunday Service System session started.",
        category="SYSTEM",
        level="INFO",
        source="SESSION",
        metadata={
            "profile_name": str(
                profile_name
                or
                ""
            ),
        },
    )

    return unexpected


def update_session_heartbeat(
    *,
    recording=None,
    streaming=None,
    last_event=None,
    profile_name=None
):
    state = current_session_state()

    if (
        state.get(
            "state"
        )
        !=
        "RUNNING"
        or
        int(
            state.get(
                "pid",
                -1
            )
            or
            -1
        )
        !=
        os.getpid()
    ):
        return False

    state[
        "heartbeat_at"
    ] = _now_iso()

    if recording is not None:
        state[
            "recording"
        ] = bool(
            recording
        )

    if streaming is not None:
        state[
            "streaming"
        ] = bool(
            streaming
        )

    if profile_name is not None:
        state[
            "profile_name"
        ] = str(
            profile_name
            or
            ""
        )

    if last_event:
        state[
            "last_event"
        ] = " ".join(
            str(
                last_event
            ).split()
        )

        state[
            "last_event_at"
        ] = _now_iso()

    _write_json_atomic(
        SESSION_STATE_FILE,
        state,
    )

    return True


def mark_clean_shutdown(
    *,
    detail="Sunday Service System closed normally."
):
    state = current_session_state()

    if int(
        state.get(
            "pid",
            -1
        )
        or
        -1
    ) != os.getpid():
        return False

    state[
        "state"
    ] = "CLOSED"

    state[
        "heartbeat_at"
    ] = _now_iso()

    state[
        "clean_shutdown_at"
    ] = _now_iso()

    _write_json_atomic(
        SESSION_STATE_FILE,
        state,
    )

    record_event(
        detail,
        category="SYSTEM",
        level="INFO",
        source="SESSION",
    )

    return True


def read_recent_events(
    *,
    limit=250,
    days=14
):
    ensure_event_root()

    limit = max(
        1,
        int(
            limit
        )
    )

    days = max(
        1,
        int(
            days
        )
    )

    today = _now().date()
    files = []

    for offset in range(
        days
    ):
        day = (
            today
            -
            datetime.timedelta(
                days=offset
            )
        )

        path = (
            EVENT_ROOT
            /
            (
                day.isoformat()
                +
                ".jsonl"
            )
        )

        if path.exists():
            files.append(
                path
            )

    events = []

    for path in files:
        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()

        except Exception:
            continue

        for line in reversed(
            lines
        ):
            try:
                event = json.loads(
                    line
                )

                if isinstance(
                    event,
                    dict
                ):
                    events.append(
                        event
                    )

                    if len(
                        events
                    ) >= limit:
                        return events

            except Exception:
                continue

    return events


def format_event_time(
    timestamp
):
    text = str(
        timestamp
        or
        ""
    )

    try:
        value = datetime.datetime.fromisoformat(
            text
        )

        return value.strftime(
            "%Y-%m-%d %I:%M:%S %p"
        )

    except Exception:
        return text


def export_event_history_text(
    *,
    limit=1000,
    days=30
):
    ensure_event_root()

    events = read_recent_events(
        limit=limit,
        days=days,
    )

    stamp = _now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    target = (
        EVENT_ROOT
        /
        (
            "SSS-Event-History_"
            +
            stamp
            +
            ".txt"
        )
    )

    lines = [
        "SUNDAY SERVICE SYSTEM — EVENT HISTORY",
        "="
        *
        38,
        "",
    ]

    for event in reversed(
        events
    ):
        lines.append(
            (
                "["
                +
                format_event_time(
                    event.get(
                        "timestamp",
                        ""
                    )
                )
                +
                "] ["
                +
                str(
                    event.get(
                        "category",
                        "SYSTEM"
                    )
                )
                +
                "] ["
                +
                str(
                    event.get(
                        "level",
                        "INFO"
                    )
                )
                +
                "] "
                +
                str(
                    event.get(
                        "message",
                        ""
                    )
                )
            )
        )

    target.write_text(
        "\n".join(
            lines
        )
        +
        "\n",
        encoding="utf-8",
    )

    return target
