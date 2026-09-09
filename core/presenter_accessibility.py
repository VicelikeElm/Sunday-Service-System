import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path


DEFAULT_CONTROL_HOST = "127.0.0.1"
DEFAULT_CONTROL_PORT = 9223


def _powershell_shortcut_info(shortcut_path):
    if not shortcut_path:
        return {}

    shortcut_path = Path(shortcut_path)

    if not shortcut_path.exists():
        return {}

    command = (
        "$s=(New-Object -ComObject WScript.Shell)"
        ".CreateShortcut($args[0]); "
        "[pscustomobject]@{"
        "TargetPath=$s.TargetPath;"
        "Arguments=$s.Arguments;"
        "WorkingDirectory=$s.WorkingDirectory"
        "} | ConvertTo-Json -Compress"
    )

    creationflags = (
        subprocess.CREATE_NO_WINDOW
        if os.name == "nt"
        else 0
    )

    try:
        cp = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                command,
                str(shortcut_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            creationflags=creationflags,
        )
    except Exception:
        return {}

    if cp.returncode != 0:
        return {}

    try:
        data = json.loads((cp.stdout or "").strip())
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def _presenter_candidates(shortcut_path=None):
    candidates = []

    def add(value):
        if not value:
            return

        try:
            value = Path(value)
        except Exception:
            return

        if (
            value.exists()
            and value.is_file()
            and value.name.lower() == "presenter.exe"
            and value not in candidates
        ):
            candidates.append(value)

    # Confirmed by the user's Presenter diagnostic.
    add(Path(r"C:\Program Files\Presenter\Presenter.exe"))
    add(Path(r"C:\Program Files (x86)\Presenter\Presenter.exe"))

    info = _powershell_shortcut_info(shortcut_path)
    target_raw = str(info.get("TargetPath", "") or "")
    target = Path(target_raw) if target_raw else None
    add(target)

    if target is not None and target.exists():
        try:
            for candidate in target.parent.glob("app-*/Presenter.exe"):
                add(candidate)
        except Exception:
            pass

    local = Path(os.environ.get("LOCALAPPDATA", ""))

    for candidate in (
        local / "Programs" / "Presenter" / "Presenter.exe",
        local / "Programs" / "WorshipTools Presenter" / "Presenter.exe",
        local / "Presenter" / "Presenter.exe",
    ):
        add(candidate)

    return candidates


def resolve_presenter_exe(shortcut_path=None):
    candidates = _presenter_candidates(shortcut_path)
    return candidates[0] if candidates else None


def presenter_control_ready(
    *,
    host=DEFAULT_CONTROL_HOST,
    port=DEFAULT_CONTROL_PORT,
    timeout=0.7
):
    url = f"http://{host}:{int(port)}/json/version"

    try:
        with urllib.request.urlopen(url, timeout=float(timeout)) as response:
            payload = json.loads(
                response.read().decode("utf-8", errors="replace")
            )

        browser = str(payload.get("Browser", "") or "")

        return (
            True,
            browser or "Presenter control channel ready",
        )

    except Exception as exc:
        return (
            False,
            str(exc),
        )


def launch_presenter_accessible(
    shortcut_path=None,
    *,
    control_port=DEFAULT_CONTROL_PORT,
    wait_seconds=12
):
    exe = resolve_presenter_exe(shortcut_path)

    if exe is None:
        return {
            "success": False,
            "control_ready": False,
            "reason": "Could not find Presenter.exe.",
            "exe": "",
        }

    creationflags = 0

    if os.name == "nt":
        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            |
            subprocess.DETACHED_PROCESS
        )

    args = [
        str(exe),
        "--force-renderer-accessibility",
        f"--remote-debugging-port={int(control_port)}",
        "--remote-debugging-address=127.0.0.1",
        "--remote-allow-origins=*",
    ]

    try:
        subprocess.Popen(
            args,
            cwd=str(exe.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

    except Exception as exc:
        return {
            "success": False,
            "control_ready": False,
            "reason": str(exc),
            "exe": str(exe),
        }

    deadline = time.time() + float(wait_seconds)
    last_detail = ""

    while time.time() < deadline:
        ready, detail = presenter_control_ready(
            port=control_port,
            timeout=0.5,
        )

        last_detail = detail

        if ready:
            return {
                "success": True,
                "control_ready": True,
                "reason": "Presenter started in SSS control mode.",
                "exe": str(exe),
                "control_port": int(control_port),
            }

        time.sleep(0.35)

    return {
        "success": True,
        "control_ready": False,
        "reason": (
            "Presenter opened, but the SSS control channel did not start. "
            + (last_detail or "No response from localhost control port.")
        ),
        "exe": str(exe),
        "control_port": int(control_port),
    }
