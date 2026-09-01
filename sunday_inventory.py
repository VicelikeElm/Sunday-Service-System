import os
import sys
import json
import shutil
import socket
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE = Path(r"C:\Church\SermonAI")
ENV_FILE = BASE / ".env"
REPORT_FILE = BASE / "sunday_inventory.txt"

OBS_LEVELDB = Path(
    r"C:\Users\Vicel\AppData\Roaming\obs-studio"
    r"\plugin_config\obs-browser\Local Storage\leveldb"
)

LOWER_THIRDS_FOLDER = Path(
    r"C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds"
)

IMPORTANT_FOLDERS = [
    Path(r"D:\2026"),
    Path(r"D:\2026\SRT files"),
    Path(r"D:\2026\shorts\ai shorts"),
    Path(r"D:\2026\shorts\ai shorts\Raw"),
    Path(r"D:\2026\shorts\ai shorts\Transcripts"),
    Path(r"D:\2026\shorts\ai shorts\Verified"),
    Path(r"D:\2026\shorts\ai shorts\Review"),
    Path(r"D:\2026\shorts\ai shorts\Ready"),
    Path(r"D:\2026\shorts\ai shorts\Sermon Data"),
]

IMPORTANT_SCRIPTS = [
    BASE / "sermon_ai.py",
    BASE / "process_shorts.py",
    BASE / "render_shorts.py",
    BASE / "prepare_sermon.py",
    BASE / "start_sermon_ai.bat",
    BASE / "start_sermon_ai_hidden.vbs",
]

AUDIO_TARGET = "Headphones (High Definition Audio Device) [Loopback]"


def line(out, text=""):
    out.append(str(text))


def section(out, title):
    line(out)
    line(out, "=" * 78)
    line(out, title)
    line(out, "=" * 78)


def run_command(args, timeout=8):
    try:
        cp = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
        return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()
    except Exception as exc:
        return -1, "", str(exc)


def human_bytes(value):
    try:
        value = float(value)
    except Exception:
        return "unknown"

    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024


def socket_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def scan_obs(out):
    section(out, "OBS / OBS WEBSOCKET")

    load_dotenv(ENV_FILE)

    host = os.getenv("OBS_HOST", "localhost")
    try:
        port = int(os.getenv("OBS_PORT", "4455"))
    except ValueError:
        port = 4455
    password = os.getenv("OBS_PASSWORD", "")

    line(out, f"Host: {host}")
    line(out, f"Port: {port}")
    line(out, f"Password configured: {'YES' if password else 'NO'}")
    reachable = socket_open(host, port)
    line(out, f"WebSocket port reachable: {'YES' if reachable else 'NO'}")

    if not reachable:
        line(out, "OBS API details: unavailable because OBS/WebSocket is not reachable.")
        return

    try:
        import obsws_python as obs

        client = obs.ReqClient(
            host=host,
            port=port,
            password=password,
            timeout=4,
        )

        try:
            v = client.get_version()
            line(out, f"OBS version: {getattr(v, 'obs_version', 'unknown')}")
            line(out, f"obs-websocket version: {getattr(v, 'obs_web_socket_version', 'unknown')}")
            line(out, f"RPC version: {getattr(v, 'rpc_version', 'unknown')}")
        except Exception as exc:
            line(out, f"GetVersion ERROR: {exc}")

        try:
            profile = client.get_profile_list()
            line(out, f"Current OBS profile: {getattr(profile, 'current_profile_name', 'unknown')}")
            line(out, "OBS profiles:")
            for item in getattr(profile, "profiles", []):
                line(out, f"  - {item}")
        except Exception as exc:
            line(out, f"Profile list ERROR: {exc}")

        try:
            collections = client.get_scene_collection_list()
            line(out, f"Current scene collection: {getattr(collections, 'current_scene_collection_name', 'unknown')}")
            line(out, "Scene collections:")
            for item in getattr(collections, "scene_collections", []):
                line(out, f"  - {item}")
        except Exception as exc:
            line(out, f"Scene collection list ERROR: {exc}")

        try:
            scenes = client.get_scene_list()
            line(out, f"Current program scene: {getattr(scenes, 'current_program_scene_name', 'unknown')}")
            line(out, f"Current preview scene: {getattr(scenes, 'current_preview_scene_name', 'unknown')}")
            line(out, "Scenes:")
            for scene in getattr(scenes, "scenes", []):
                if isinstance(scene, dict):
                    line(out, f"  - {scene.get('sceneName', scene)}")
                else:
                    line(out, f"  - {scene}")
        except Exception as exc:
            line(out, f"Scene list ERROR: {exc}")

        try:
            inputs = client.get_input_list()
            input_rows = getattr(inputs, "inputs", [])
            line(out, f"OBS inputs ({len(input_rows)}):")

            for item in input_rows:
                if not isinstance(item, dict):
                    line(out, f"  - {item}")
                    continue

                name = item.get("inputName", "")
                kind = item.get("inputKind", "")
                muted = "?"
                volume_db = "?"

                try:
                    m = client.get_input_mute(name)
                    muted = getattr(m, "input_muted", "?")
                except Exception:
                    pass

                try:
                    vol = client.get_input_volume(name)
                    volume_db = getattr(vol, "input_volume_db", "?")
                except Exception:
                    pass

                line(
                    out,
                    f"  - {name} | kind={kind} | muted={muted} | volume_db={volume_db}"
                )
        except Exception as exc:
            line(out, f"Input list ERROR: {exc}")

        try:
            rec = client.get_record_status()
            line(out, f"Recording active: {getattr(rec, 'output_active', False)}")
            line(out, f"Recording paused: {getattr(rec, 'output_paused', False)}")
        except Exception as exc:
            line(out, f"Record status ERROR: {exc}")

        try:
            stream = client.get_stream_status()
            line(out, f"Streaming active: {getattr(stream, 'output_active', False)}")
        except Exception as exc:
            line(out, f"Stream status ERROR: {exc}")

        try:
            replay = client.get_replay_buffer_status()
            line(out, f"Replay Buffer active: {getattr(replay, 'output_active', False)}")
        except Exception as exc:
            line(out, f"Replay Buffer status ERROR: {exc}")

        try:
            try:
                rd = client.get_record_directory()
                line(out, f"OBS record directory: {getattr(rd, 'record_directory', 'unknown')}")
            except AttributeError:
                rd = client.send("GetRecordDirectory", raw=True)
                line(out, f"OBS record directory raw: {rd}")
        except Exception as exc:
            line(out, f"Record directory ERROR: {exc}")

        try:
            video = client.get_video_settings()
            attrs_fn = getattr(video, "attrs", None)
            if callable(attrs_fn):
                line(out, f"Video settings: {attrs_fn()}")
            else:
                line(out, f"Video settings object: {video}")
        except Exception as exc:
            line(out, f"Video settings ERROR: {exc}")

    except Exception as exc:
        line(out, f"OBS connection ERROR: {exc}")


def scan_audio(out):
    section(out, "WINDOWS / PYAUDIO AUDIO DEVICES")

    try:
        import pyaudiowpatch as pyaudio
        audio = pyaudio.PyAudio()

        matches = []

        for index in range(audio.get_device_count()):
            try:
                info = audio.get_device_info_by_index(index)
            except Exception:
                continue

            name = info.get("name", "")
            max_in = info.get("maxInputChannels", 0)
            rate = info.get("defaultSampleRate", 0)

            upper = name.upper()

            if (
                "LOOPBACK" in upper
                or "TASCAM" in upper
                or "US-16X08" in upper
                or "HEADPHONES" in upper
            ):
                line(
                    out,
                    f"[{index}] {name} | inputs={max_in} | rate={rate}"
                )

            if name == AUDIO_TARGET:
                matches.append(index)

        line(out)
        line(out, f"Target OBS-monitor loopback found: {'YES' if matches else 'NO'}")
        if matches:
            line(out, f"Target device index/indices: {matches}")

        audio.terminate()

    except Exception as exc:
        line(out, f"Audio scan ERROR: {exc}")


def scan_storage(out):
    section(out, "DISKS / OUTPUT FOLDERS")

    for root in [r"C:\\", r"D:\\"]:
        try:
            usage = shutil.disk_usage(root)
            line(
                out,
                f"{root} free={human_bytes(usage.free)} "
                f"used={human_bytes(usage.used)} total={human_bytes(usage.total)}"
            )
        except Exception as exc:
            line(out, f"{root} ERROR: {exc}")

    line(out)
    for folder in IMPORTANT_FOLDERS:
        exists = folder.exists()
        writable = False

        if exists:
            probe = folder / ".sermon_ai_write_test.tmp"
            try:
                probe.write_text("test", encoding="utf-8")
                probe.unlink(missing_ok=True)
                writable = True
            except Exception:
                writable = False

        line(
            out,
            f"{folder} | exists={'YES' if exists else 'NO'} "
            f"| writable={'YES' if writable else 'NO'}"
        )


def scan_tools(out):
    section(out, "TOOLS / SCRIPTS")

    for command in ["ffmpeg", "ffprobe", "nvidia-smi", "git"]:
        resolved = shutil.which(command)
        line(out, f"{command}: {resolved or 'NOT FOUND'}")

        if resolved:
            if command in ("ffmpeg", "ffprobe"):
                rc, stdout, stderr = run_command([resolved, "-version"], timeout=5)
                first = (stdout or stderr).splitlines()
                if first:
                    line(out, f"  {first[0]}")
            elif command == "nvidia-smi":
                rc, stdout, stderr = run_command(
                    [
                        resolved,
                        "--query-gpu=name,memory.total,driver_version",
                        "--format=csv,noheader",
                    ],
                    timeout=5,
                )
                if stdout:
                    line(out, f"  {stdout}")
            elif command == "git":
                rc, stdout, stderr = run_command([resolved, "--version"], timeout=5)
                if stdout:
                    line(out, f"  {stdout}")

    line(out)
    for script_path in IMPORTANT_SCRIPTS:
        if script_path.exists():
            st = script_path.stat()
            line(
                out,
                f"{script_path.name}: FOUND | size={st.st_size} "
                f"| modified={datetime.fromtimestamp(st.st_mtime)}"
            )
        else:
            line(out, f"{script_path.name}: NOT FOUND")


def scan_lower_thirds(out):
    section(out, "ANIMATED LOWER THIRDS")

    line(out, f"Lower-thirds folder: {LOWER_THIRDS_FOLDER}")
    line(out, f"Folder exists: {'YES' if LOWER_THIRDS_FOLDER.exists() else 'NO'}")

    for filename in [
        "browser-source.html",
        "control-panel.html",
        "lower-thirds_hotkeys.lua",
    ]:
        path = LOWER_THIRDS_FOLDER / filename
        line(out, f"{filename}: {'FOUND' if path.exists() else 'NOT FOUND'}")

    line(out, f"OBS Browser LocalStorage LevelDB: {OBS_LEVELDB}")
    line(out, f"LevelDB exists: {'YES' if OBS_LEVELDB.exists() else 'NO'}")

    if not OBS_LEVELDB.exists():
        return

    try:
        import tempfile
        import re
        from ccl_chromium_reader import ccl_chromium_localstorage

        temp_root = Path(tempfile.mkdtemp(prefix="sunday_inventory_lt_"))
        copied = temp_root / "leveldb"
        shutil.copytree(OBS_LEVELDB, copied, dirs_exist_ok=True)

        latest = {}

        with ccl_chromium_localstorage.LocalStoreDb(copied) as db:
            for storage_key in db.iter_storage_keys():
                try:
                    for record in db.iter_records_for_storage_key(storage_key):
                        key = record.script_key
                        value = record.value

                        if isinstance(key, bytes):
                            key = key.decode("utf-8", errors="replace")
                        if isinstance(value, bytes):
                            value = value.decode("utf-8", errors="replace")

                        key = str(key).replace("\x00", "").strip()
                        value = str(value).replace("\x00", "").strip()

                        if not re.fullmatch(
                            r"alt-[1-4]-(?:name|info)(?:-(?:[1-9]|10))?",
                            key
                        ):
                            continue

                        try:
                            seq = int(getattr(record, "leveldb_seq_number", 0) or 0)
                        except Exception:
                            seq = 0

                        if key not in latest or seq >= latest[key][0]:
                            latest[key] = (seq, value)

                except Exception:
                    continue

        line(out)
        line(out, "Current ACTIVE lower-third values:")

        for lt in range(1, 5):
            name = latest.get(f"alt-{lt}-name", (0, ""))[1]
            info = latest.get(f"alt-{lt}-info", (0, ""))[1]
            line(out, f"  LT{lt}: Name={name!r} | Info={info!r}")

        shutil.rmtree(temp_root, ignore_errors=True)

    except Exception as exc:
        line(out, f"Lower-third value scan ERROR: {exc}")


def scan_processes(out):
    section(out, "RUNNING PROGRAMS / WINDOWS TASKS")

    ps = (
        "$items = Get-CimInstance Win32_Process | "
        "Where-Object { "
        "$_.Name -match 'obs|python|tascam|presenter|worship|chrome|msedge' "
        "} | Select-Object Name, ProcessId, ExecutablePath, CommandLine; "
        "$items | ConvertTo-Json -Depth 3"
    )

    rc, stdout, stderr = run_command(
        ["powershell", "-NoProfile", "-Command", ps],
        timeout=12,
    )

    if stdout:
        try:
            data = json.loads(stdout)
            if isinstance(data, dict):
                data = [data]

            for item in data:
                name = item.get("Name", "")
                cmd = item.get("CommandLine", "") or ""

                if name.lower() in ("chrome.exe", "msedge.exe"):
                    line(out, f"{name} PID={item.get('ProcessId')} | running")
                else:
                    line(
                        out,
                        f"{name} PID={item.get('ProcessId')} "
                        f"| path={item.get('ExecutablePath')} | cmd={cmd}"
                    )
        except Exception:
            line(out, stdout)
    else:
        line(out, f"Process scan ERROR: {stderr or 'no output'}")

    line(out)
    rc, stdout, stderr = run_command(
        [
            "schtasks",
            "/Query",
            "/TN",
            "Sermon AI",
            "/V",
            "/FO",
            "LIST",
        ],
        timeout=8,
    )

    if rc == 0 and stdout:
        wanted = (
            "TaskName:",
            "Status:",
            "Scheduled Task State:",
            "Last Run Time:",
            "Last Result:",
            "Task To Run:",
            "Run As User:",
        )
        for raw in stdout.splitlines():
            if raw.strip().startswith(wanted):
                line(out, raw.strip())
    else:
        line(out, f"Sermon AI scheduled task query ERROR: {stderr or stdout}")


def scan_start_menu(out):
    section(out, "START MENU / APP CANDIDATES")

    roots = [
        Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]

    needles = (
        "obs",
        "tascam",
        "worship",
        "presenter",
    )

    found = []

    for root in roots:
        if not root.exists():
            continue

        try:
            for path in root.rglob("*.lnk"):
                low = path.name.lower()
                if any(word in low for word in needles):
                    found.append(path)
        except Exception:
            pass

    if found:
        for item in sorted(set(found)):
            line(out, f"- {item}")
    else:
        line(out, "No matching Start Menu shortcuts found.")


def main():
    out = []

    line(out, "SUNDAY AUTOMATION INVENTORY")
    line(out, "=" * 78)
    line(out, f"Generated: {datetime.now()}")
    line(out, f"Computer: {platform.node()}")
    line(out, f"Windows: {platform.platform()}")
    line(out, f"Python: {sys.version}")
    line(out, f"Python executable: {sys.executable}")
    line(out, f"Virtual environment: {os.environ.get('VIRTUAL_ENV', 'not detected')}")

    scan_obs(out)
    scan_audio(out)
    scan_storage(out)
    scan_tools(out)
    scan_lower_thirds(out)
    scan_processes(out)
    scan_start_menu(out)

    section(out, "NEXT STEP")
    line(
        out,
        "Send this sunday_inventory.txt back to ChatGPT. "
        "It contains no OBS password."
    )

    REPORT_FILE.write_text(
        "\n".join(out),
        encoding="utf-8",
    )

    print()
    print("=" * 78)
    print("SUNDAY AUTOMATION INVENTORY COMPLETE")
    print("=" * 78)
    print()
    print("Report created:")
    print(REPORT_FILE)
    print()
    print("Open it with:")
    print(f'notepad "{REPORT_FILE}"')
    print()


if __name__ == "__main__":
    main()
