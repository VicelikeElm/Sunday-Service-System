import os
import json
import socket
import subprocess
import logging
from pathlib import Path

import obsws_python as obs
from dotenv import load_dotenv

BASE = Path(r"C:\Church\SermonAI")
CONFIG_PATH = BASE / "sunday_config.json"
ENV_PATH = BASE / ".env"


# Keep expected "OBS is not open yet" connection failures out of the console.
logging.getLogger("obsws_python").setLevel(logging.CRITICAL)
logging.getLogger("websocket").setLevel(logging.CRITICAL)


def load_config():
    # utf-8-sig accepts normal UTF-8 as well as UTF-8 files written
    # with a BOM by Windows PowerShell's Set-Content -Encoding UTF8.
    with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def get_obs_endpoint(
    config=None
):
    if config is None:
        config = load_config()

    load_dotenv(
        ENV_PATH
    )

    host = os.getenv(
        "OBS_HOST",
        config.get(
            "obs_host",
            "localhost"
        )
    )

    try:
        port = int(
            os.getenv(
                "OBS_PORT",
                str(
                    config.get(
                        "obs_port",
                        4455
                    )
                )
            )
        )
    except ValueError:
        port = int(
            config.get(
                "obs_port",
                4455
            )
        )

    password = os.getenv(
        "OBS_PASSWORD",
        ""
    )

    return (
        host,
        port,
        password,
    )


def obs_port_open(
    config=None
):
    host, port, _ = (
        get_obs_endpoint(
            config
        )
    )

    try:
        with socket.create_connection(
            (
                host,
                port
            ),
            timeout=1
        ):
            return True

    except OSError:
        return False


def obs_connection(
    config=None,
    timeout=4
):
    if config is None:
        config = load_config()

    host, port, password = (
        get_obs_endpoint(
            config
        )
    )

    # Important: do not construct ReqClient until something is actually
    # listening. obsws-python otherwise prints a full traceback for the
    # perfectly normal case where Sunday Mode starts before OBS.
    if not obs_port_open(
        config
    ):
        raise ConnectionError(
            "OBS WebSocket is not listening yet."
        )

    return obs.ReqClient(
        host=host,
        port=port,
        password=password,
        timeout=timeout,
    )


def get_obs_status(client):
    recording = False
    streaming = False
    replay = False

    try:
        recording = bool(
            client.get_record_status().output_active
        )
    except Exception:
        pass

    try:
        streaming = bool(
            client.get_stream_status().output_active
        )
    except Exception:
        pass

    try:
        replay = bool(
            client.get_replay_buffer_status().output_active
        )
    except Exception:
        pass

    return {
        "recording": recording,
        "streaming": streaming,
        "replay": replay,
    }


def process_running_contains(
    needle
):
    # PowerShell's own command line contains the search text, so the
    # querying PowerShell process MUST be excluded or it can match itself.
    escaped = needle.replace(
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
                "powershell",
                "-NoProfile",
                "-Command",
                ps,
            ],
            capture_output=True,
            text=True,
            timeout=6,
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


def process_name_running(name):
    try:
        cp = subprocess.run(
            [
                "tasklist",
                "/FI",
                f"IMAGENAME eq {name}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        return (
            name.lower()
            in cp.stdout.lower()
        )
    except Exception:
        return False
