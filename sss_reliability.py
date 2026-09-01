import json
import os
import shutil
import socket
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(r"C:\Church\SermonAI")
STATE_DIR = BASE / "State"
LOG_ROOT = BASE / "Logs"
BACKUP_ROOT = BASE / "Weekly_Backups"

FREEZE_FILE = STATE_DIR / "Sunday_Freeze.json"
POST_STATUS_FILE = STATE_DIR / "post_service_status.json"
AUDIO_STATUS_FILE = STATE_DIR / "audio_sanity_status.json"
TEST_STATUS_FILE = STATE_DIR / "sss_test_status.json"

KNOWN_LOGS = [
    "sermon_ai.log",
    "youtube_upload.log",
    "planning_update.log",
    "chapter_bridge.log",
]


def now_local():
    return datetime.now().astimezone()


def now_iso():
    return now_local().isoformat(
        timespec="seconds"
    )


def ensure_dirs():
    for folder in (
        STATE_DIR,
        LOG_ROOT,
        BACKUP_ROOT,
    ):
        folder.mkdir(
            parents=True,
            exist_ok=True
        )


def read_json(path, default=None):
    if default is None:
        default = {}

    try:
        return json.loads(
            Path(path).read_text(
                encoding="utf-8-sig"
            )
        )
    except Exception:
        return default


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp = path.with_suffix(
        path.suffix
        +
        ".tmp"
    )

    temp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    temp.replace(
        path
    )


def service_log_folder(service_date=None):
    ensure_dirs()

    if service_date is None:
        service_date = now_local().date().isoformat()

    folder = (
        LOG_ROOT
        /
        str(
            service_date
        )
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    return folder


def append_system_log(
    message,
    *,
    service_date=None,
    filename="Sunday_Service_System.log"
):
    folder = service_log_folder(
        service_date
    )

    line = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"{message}\n"
    )

    try:
        with (
            folder
            /
            filename
        ).open(
            "a",
            encoding="utf-8"
        ) as handle:
            handle.write(
                line
            )
    except Exception:
        pass


def collect_known_logs(
    service_date=None
):
    folder = service_log_folder(
        service_date
    )

    copied = []

    for name in KNOWN_LOGS:
        source = (
            BASE
            /
            name
        )

        if not source.exists():
            continue

        try:
            shutil.copy2(
                source,
                folder
                /
                name
            )

            copied.append(
                name
            )

        except Exception:
            pass

    return copied


def set_freeze(
    active,
    reason="Sunday service active"
):
    ensure_dirs()

    if active:
        atomic_json(
            FREEZE_FILE,
            {
                "active": True,
                "started": now_iso(),
                "reason": reason,
            }
        )

    else:
        try:
            FREEZE_FILE.unlink(
                missing_ok=True
            )
        except Exception:
            pass


def is_frozen():
    payload = read_json(
        FREEZE_FILE,
        {}
    )

    return bool(
        payload.get(
            "active",
            False
        )
    )


def internet_reachable(
    host="www.youtube.com",
    port=443,
    timeout=4
):
    try:
        with socket.create_connection(
            (
                host,
                int(
                    port
                ),
            ),
            timeout=float(
                timeout
            ),
        ):
            return True

    except OSError:
        return False


def process_running_contains(
    needle
):
    escaped = str(
        needle
    ).replace(
        "'",
        "''"
    )

    ps = (
        "$selfPid = $PID; "
        "Get-CimInstance Win32_Process | "
        "Where-Object { "
        "$_.ProcessId -ne $selfPid -and "
        "$_.CommandLine -and "
        f"$_.CommandLine -like '*{escaped}*' "
        "} | "
        "Select-Object -First 1 "
        "-ExpandProperty ProcessId"
    )

    try:
        cp = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                ps,
            ],
            capture_output=True,
            text=True,
            timeout=7,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        return bool(
            cp.stdout.strip()
        )

    except Exception:
        return False


def ffprobe_duration(
    path
):
    try:
        cp = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(
                    path
                ),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        if cp.returncode != 0:
            return 0.0

        return float(
            cp.stdout.strip()
        )

    except Exception:
        return 0.0


def ffprobe_chapters(
    path
):
    try:
        cp = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_chapters",
                str(
                    path
                ),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        if cp.returncode != 0:
            return []

        data = json.loads(
            cp.stdout
            or
            "{}"
        )

        result = []

        for item in data.get(
            "chapters",
            []
        ):
            tags = item.get(
                "tags",
                {}
            )

            title = str(
                tags.get(
                    "title",
                    ""
                )
            ).strip()

            try:
                start = float(
                    item.get(
                        "start_time",
                        0
                    )
                )
            except Exception:
                start = 0.0

            result.append(
                {
                    "start": start,
                    "title": title,
                }
            )

        return result

    except Exception:
        return []


def filename_date(
    path
):
    import re

    match = re.match(
        r"^(\d{4}-\d{2}-\d{2})",
        Path(
            path
        ).name
    )

    if not match:
        return None

    try:
        return datetime.strptime(
            match.group(
                1
            ),
            "%Y-%m-%d"
        ).date()

    except Exception:
        return None


def find_full_sermon_recording(
    config,
    plan,
    *,
    require_stable=True,
    require_duration=True
):
    folder = Path(
        config.get(
            "recording_folder",
            r"D:\2026"
        )
    )

    try:
        service_date = datetime.strptime(
            str(
                plan.get(
                    "service_date",
                    ""
                )
            ),
            "%Y-%m-%d"
        ).date()

    except Exception:
        return None

    if not folder.exists():
        return None

    min_bytes = int(
        float(
            config.get(
                "youtube_min_file_mb",
                500
            )
        )
        *
        1024
        *
        1024
    )

    min_seconds = (
        float(
            config.get(
                "youtube_min_duration_minutes",
                20
            )
        )
        *
        60
    )

    stable_seconds = float(
        config.get(
            "youtube_file_stable_seconds",
            300
        )
    )

    now_epoch = time.time()

    candidates = []

    for path in folder.iterdir():
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".mp4",
            ".mkv",
            ".mov",
        }:
            continue

        if filename_date(
            path
        ) != service_date:
            continue

        try:
            stat = path.stat()
        except OSError:
            continue

        if stat.st_size < min_bytes:
            continue

        if (
            require_stable
            and
            now_epoch
            -
            stat.st_mtime
            <
            stable_seconds
        ):
            continue

        duration = 0.0

        if require_duration:
            duration = ffprobe_duration(
                path
            )

            if duration < min_seconds:
                continue

        candidates.append(
            {
                "path": path,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "duration": duration,
            }
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[
                "size"
            ],
            item[
                "mtime"
            ],
        ),
        reverse=True,
    )

    return candidates[
        0
    ]


def find_service_srt(
    plan,
    srt_folder=r"D:\2026\SRT files"
):
    folder = Path(
        srt_folder
    )

    if not folder.exists():
        return None

    service_date = str(
        plan.get(
            "service_date",
            ""
        )
    ).strip()

    candidates = []

    for path in folder.glob(
        "*.srt"
    ):
        try:
            stat = path.stat()
        except OSError:
            continue

        filename_match = path.name.startswith(
            service_date
        )

        mtime_date = datetime.fromtimestamp(
            stat.st_mtime
        ).date().isoformat()

        if (
            filename_match
            or
            mtime_date
            ==
            service_date
        ):
            candidates.append(
                (
                    stat.st_size,
                    stat.st_mtime,
                    path,
                )
            )

    if not candidates:
        return None

    candidates.sort(
        reverse=True
    )

    return candidates[
        0
    ][
        2
    ]


def weekly_snapshot(
    *,
    service_date=None,
    retention_weeks=12,
    phase="current"
):
    ensure_dirs()

    if service_date is None:
        today = now_local().date()
        days = (
            6
            -
            today.weekday()
        ) % 7

        service_date = (
            today
            +
            timedelta(
                days=days
            )
        ).isoformat()

    destination = (
        BACKUP_ROOT
        /
        str(
            service_date
        )
        /
        str(
            phase
        )
    )

    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    names = [
        "sermon_plan.json",
        "sunday_config.json",
        "ptz_camera_config.json",
        "planning_update_status.json",
        "youtube_upload_status.json",
        "chapter_bridge_status.json",
        "control-panel-v15-template.html",
        "gmail_sermon_importer.py",
        "planning_update_sermon.py",
        "youtube_studio_upload_worker.py",
        "sunday_mode.py",
    ]

    copied = []

    for name in names:
        source = (
            BASE
            /
            name
        )

        if not source.exists():
            continue

        try:
            shutil.copy2(
                source,
                destination
                /
                name
            )

            copied.append(
                name
            )

        except Exception:
            pass

    snapshot_meta = {
        "created": now_iso(),
        "service_date": str(
            service_date
        ),
        "files": copied,
    }

    atomic_json(
        destination
        /
        "snapshot.json",
        snapshot_meta
    )

    cutoff = (
        now_local().date()
        -
        timedelta(
            weeks=int(
                retention_weeks
            )
        )
    )

    for folder in BACKUP_ROOT.iterdir():
        if not folder.is_dir():
            continue

        try:
            folder_date = datetime.strptime(
                folder.name,
                "%Y-%m-%d"
            ).date()
        except Exception:
            continue

        if folder_date < cutoff:
            try:
                shutil.rmtree(
                    folder
                )
            except Exception:
                pass

    return destination


def purge_old_log_folders(
    retention_days=90
):
    ensure_dirs()

    cutoff = (
        now_local().date()
        -
        timedelta(
            days=int(
                retention_days
            )
        )
    )

    removed = []

    for folder in LOG_ROOT.iterdir():
        if not folder.is_dir():
            continue

        try:
            folder_date = datetime.strptime(
                folder.name,
                "%Y-%m-%d"
            ).date()
        except Exception:
            continue

        if folder_date < cutoff:
            try:
                shutil.rmtree(
                    folder
                )

                removed.append(
                    folder.name
                )

            except Exception:
                pass

    return removed
