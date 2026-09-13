import os
import json
import socket
import subprocess
import logging
from pathlib import Path

import psutil
import obsws_python as obs
from dotenv import load_dotenv

BASE = Path(r"C:\Church\SermonAI")
CONFIG_PATH = BASE / "sunday_config.json"
ENV_PATH = BASE / ".env"


# Keep expected "OBS is not open yet" connection failures out of the console.
logging.getLogger("obsws_python").setLevel(logging.CRITICAL)
logging.getLogger("websocket").setLevel(logging.CRITICAL)


def load_config():
    # The first-run setup wizard (sss_first_run.py / sss_setup_wizard.py)
    # runs before sunday_config.json exists, but some of its features
    # (e.g. "Connect & Discover OBS") transitively call load_config()
    # through this module. Every caller already reads config with
    # config.get(key, default), so an empty dict here behaves exactly
    # like a config file that's simply missing that key - it does not
    # let the main app run without a real config, since sunday_mode.py's
    # startup gate checks CONFIG_PATH.exists() before this is ever
    # reached on the normal startup path.
    if not CONFIG_PATH.exists():
        return {}

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
    # Was a spawned-PowerShell + Get-CimInstance query - measured at
    # ~1.7s per call on the church PC (see the Performance page's
    # "Check: Sermon Ai" number). psutil reads process command lines
    # directly, in-process, with no interpreter-startup or WMI cost.
    needle_lower = str(
        needle
    ).lower()

    current_pid = os.getpid()

    try:
        for proc in psutil.process_iter(
            [
                "pid",
                "cmdline",
            ]
        ):
            try:
                if proc.info[
                    "pid"
                ] == current_pid:
                    continue

                command_line = " ".join(
                    proc.info.get(
                        "cmdline"
                    )
                    or
                    []
                )

                if needle_lower in command_line.lower():
                    return True

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
            ):
                continue

        return False

    except Exception:
        return False


def stop_processes_containing(needle):
    """
    Terminate any process (other than this one) whose command line
    contains `needle`. Used to clean up SSS's own hidden helper scripts
    (chapter_bridge.py, audio_sanity_monitor.py, etc.) when the main
    window closes, mirroring process_running_contains()'s matching style.

    Returns the number of processes asked to stop. Best-effort: a process
    that exits on its own between the query and the stop is not an error.

    Was a spawned-PowerShell + Get-CimInstance + Stop-Process query -
    on_app_close() calls this four times in a row (once per helper
    script), which measured at several seconds of blocking PowerShell
    overhead per call - long enough for Windows to show the main window
    as "not responding" during every close. psutil does the same
    command-line match and kill in-process, with no interpreter-startup
    or WMI cost. See sunday_common.py's process_running_contains() for
    the identical rewrite on the read-only side.
    """
    needle_lower = str(
        needle
    ).lower()

    current_pid = os.getpid()

    stopped = 0

    try:
        for proc in psutil.process_iter(
            [
                "pid",
                "cmdline",
            ]
        ):
            try:
                if proc.info[
                    "pid"
                ] == current_pid:
                    continue

                command_line = " ".join(
                    proc.info.get(
                        "cmdline"
                    )
                    or
                    []
                )

                if needle_lower in command_line.lower():
                    proc.kill()
                    stopped += 1

            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
            ):
                continue

        return stopped

    except Exception:
        return stopped


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
