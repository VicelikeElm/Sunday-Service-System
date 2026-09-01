import argparse
import json
import mimetypes
import os
import random
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from sunday_common import load_config

BASE = Path(r"C:\Church\SermonAI")
PLAN_FILE = BASE / "sermon_plan.json"
STATUS_FILE = BASE / "youtube_upload_status.json"
HISTORY_FILE = BASE / "youtube_upload_history.json"
CHANNEL_FILE = BASE / "youtube_channel.json"
LOG_FILE = BASE / "youtube_upload.log"

UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
VALID_PRIVACY = {"private", "unlisted", "public"}
RETRIABLE = {500, 502, 503, 504}


def now():
    return datetime.now().astimezone()


def now_iso():
    return now().isoformat(timespec="seconds")


def log(message):
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"{message}\n"
            )
    except Exception:
        pass


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    tmp.replace(path)


def status(
    state,
    message,
    *,
    ok=False,
    warning=False,
    progress=None,
    file="",
    video_id="",
    video_url="",
    requested_privacy="",
    actual_privacy="",
):
    payload = {
        "updated": now_iso(),
        "state": state,
        "message": message,
        "ok": bool(ok),
        "warning": bool(warning),
        "progress": progress,
        "file": file,
        "video_id": video_id,
        "video_url": video_url,
        "requested_privacy": requested_privacy,
        "actual_privacy": actual_privacy,
    }
    save_json(STATUS_FILE, payload)
    log(f"{state}: {message}")
    return payload


def parse_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def filename_date(path):
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", path.name)
    return parse_date(m.group(1)) if m else None


def load_plan():
    if not PLAN_FILE.exists():
        raise RuntimeError("sermon_plan.json is missing.")

    plan = read_json(PLAN_FILE, {})
    for key in ("plan_id", "title", "scripture", "service_date"):
        if not str(plan.get(key, "")).strip():
            raise RuntimeError(f"sermon_plan.json is missing {key}.")

    return plan


def get_credentials(config, interactive=False):
    credentials_file = Path(
        config.get(
            "youtube_credentials_file",
            config.get(
                "gmail_credentials_file",
                str(BASE / "gmail_credentials.json")
            )
        )
    )
    token_file = Path(
        config.get(
            "youtube_token_file",
            str(BASE / "youtube_token.json")
        )
    )

    if not credentials_file.exists():
        raise RuntimeError(
            f"YouTube OAuth credentials file is missing: {credentials_file}"
        )

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise RuntimeError(
            "Google API libraries are not installed. "
            "Run Setup-YouTube-Upload.bat."
        ) from exc

    creds = None

    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(token_file),
                [UPLOAD_SCOPE]
            )
        except Exception:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if not interactive:
            raise RuntimeError(
                "YouTube authorization is required. "
                "Run Setup-YouTube-Upload.bat."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_file),
            [UPLOAD_SCOPE]
        )
        creds = flow.run_local_server(
            port=0,
            open_browser=True,
            prompt="consent"
        )
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return creds


def youtube_service(config, interactive=False):
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "google-api-python-client is not installed."
        ) from exc

    return build(
        "youtube",
        "v3",
        credentials=get_credentials(config, interactive=interactive),
        cache_discovery=False
    )


def authorize(config):
    youtube = youtube_service(config, interactive=True)

    response = youtube.channels().list(
        part="snippet",
        mine=True,
        maxResults=5
    ).execute()

    items = response.get("items", [])
    if not items:
        raise RuntimeError(
            "The authorized Google account has no YouTube channel."
        )

    # Usually one channel is returned for an OAuth identity.  Refuse to
    # guess if the API ever returns several.
    if len(items) != 1:
        raise RuntimeError(
            "More than one YouTube channel was returned. "
            "Authorize the intended church channel/account."
        )

    item = items[0]
    channel = {
        "channel_id": item.get("id", ""),
        "channel_title": item.get("snippet", {}).get("title", ""),
        "authorized": now_iso(),
    }
    save_json(CHANNEL_FILE, channel)

    status(
        "AUTHORIZED",
        f"Authorized YouTube channel: {channel['channel_title']}",
        ok=True
    )

    return channel


def verify_channel(youtube):
    expected = read_json(CHANNEL_FILE, {})
    expected_id = str(expected.get("channel_id", "")).strip()

    if not expected_id:
        raise RuntimeError(
            "YouTube channel identity is not recorded. "
            "Run Setup-YouTube-Upload.bat."
        )

    response = youtube.channels().list(
        part="snippet",
        mine=True,
        maxResults=5
    ).execute()

    actual_ids = {
        str(item.get("id", ""))
        for item in response.get("items", [])
    }

    if expected_id not in actual_ids:
        raise RuntimeError(
            "The current YouTube token does not match the channel "
            "authorized during setup. Nothing was uploaded."
        )

    return expected


def duration_seconds(path):
    try:
        cp = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
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
        return float(cp.stdout.strip()) if cp.returncode == 0 else 0.0
    except Exception:
        return 0.0


def eligible_files(config, plan, trigger_epoch, manual=False):
    folder = Path(config.get("recording_folder", r"D:\2026"))
    if not folder.exists():
        return []

    service_date = parse_date(plan.get("service_date"))
    if service_date is None:
        return []

    extensions = {
        str(x).lower() if str(x).startswith(".") else "." + str(x).lower()
        for x in config.get("youtube_video_extensions", [".mp4"])
    }

    min_bytes = int(
        float(config.get("youtube_min_file_mb", 500))
        * 1024 * 1024
    )
    min_seconds = (
        float(config.get("youtube_min_duration_minutes", 20))
        * 60
    )
    stable_seconds = float(
        config.get("youtube_file_stable_seconds", 300)
    )
    lookback_seconds = (
        float(config.get("youtube_trigger_lookback_minutes", 15))
        * 60
    )

    current_time = time.time()
    found = []

    # IMPORTANT: root files only. Never recurse into shorts/SRT/Ready.
    for path in folder.iterdir():
        if not path.is_file():
            continue

        if path.suffix.lower() not in extensions:
            continue

        # Strong date guard using the church OBS filename format.
        if filename_date(path) != service_date:
            continue

        try:
            info = path.stat()
        except OSError:
            continue

        # A 2-second misclick cannot pass this threshold.
        if info.st_size < min_bytes:
            continue

        # Automatic worker was awakened by a recording STOP event.
        # Ignore older same-day files, such as a rehearsal.
        if (
            not manual
            and
            info.st_mtime < (trigger_epoch - lookback_seconds)
        ):
            continue

        # Recording must be finished/stable.
        if (current_time - info.st_mtime) < stable_seconds:
            continue

        duration = duration_seconds(path)
        if duration < min_seconds:
            continue

        found.append(
            {
                "path": path,
                "size": info.st_size,
                "mtime": info.st_mtime,
                "duration": duration,
            }
        )

    # User asked for size to help identify the real sermon.
    # Largest eligible same-date recording wins.
    found.sort(
        key=lambda x: (x["size"], x["mtime"]),
        reverse=True
    )
    return found


def history():
    return read_json(HISTORY_FILE, {"uploads": []})


def duplicate_entry(plan, candidate):
    plan_id = str(plan.get("plan_id", ""))
    file_name = str(candidate["path"].resolve()).lower()
    size = int(candidate["size"])

    for entry in history().get("uploads", []):
        if plan_id and entry.get("plan_id") == plan_id:
            return entry

        if (
            str(entry.get("file", "")).lower() == file_name
            and
            int(entry.get("size", -1)) == size
        ):
            return entry

    return None


def record_history(plan, candidate, video_id, video_url,
                   requested_privacy, actual_privacy):
    data = history()
    data.setdefault("uploads", []).append(
        {
            "uploaded": now_iso(),
            "plan_id": plan.get("plan_id", ""),
            "service_date": plan.get("service_date", ""),
            "title": plan.get("title", ""),
            "scripture": plan.get("scripture", ""),
            "file": str(candidate["path"].resolve()),
            "size": int(candidate["size"]),
            "duration_seconds": float(candidate["duration"]),
            "video_id": video_id,
            "video_url": video_url,
            "requested_privacy": requested_privacy,
            "actual_privacy": actual_privacy,
        }
    )
    save_json(HISTORY_FILE, data)


def make_title(plan):
    # Exact pastor-message title. Do not derive title from filename.
    title = str(plan.get("title", "")).strip()
    if not title:
        raise RuntimeError("Pastor sermon title is empty.")
    return title[:100].rstrip()


def make_description(plan):
    lines = [
        str(plan.get("title", "")).strip(),
        str(plan.get("scripture", "")).strip(),
    ]

    preacher = str(plan.get("preacher", "")).strip()
    if preacher:
        lines += ["", f"Preacher: {preacher}"]

    points = plan.get("points", [])
    if isinstance(points, list) and points:
        lines += ["", "Sermon Outline:"]
        for index, point in enumerate(points, start=1):
            point = str(point).strip()
            if point:
                lines.append(f"{index}. {point}")

    return "\n".join(x for x in lines if x is not None).strip()[:5000]


def upload(youtube, config, plan, candidate):
    try:
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
    except ImportError as exc:
        raise RuntimeError(
            "Google API client libraries are not installed."
        ) from exc

    privacy = str(
        config.get("youtube_privacy_status", "public")
    ).lower().strip()

    if privacy not in VALID_PRIVACY:
        raise RuntimeError(
            "youtube_privacy_status must be private, unlisted, or public."
        )

    path = candidate["path"]
    title = make_title(plan)
    description = make_description(plan)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": str(
                config.get("youtube_category_id", "29")
            ),
        },
        "status": {
            "privacyStatus": privacy,
        },
    }

    if "youtube_made_for_kids" in config:
        body["status"]["selfDeclaredMadeForKids"] = bool(
            config["youtube_made_for_kids"]
        )

    media = MediaFileUpload(
        str(path),
        mimetype=(
            mimetypes.guess_type(str(path))[0]
            or
            "video/*"
        ),
        chunksize=8 * 1024 * 1024,
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
        notifySubscribers=bool(
            config.get("youtube_notify_subscribers", True)
        ),
    )

    status(
        "UPLOADING",
        f'Uploading {path.name} as "{title}"',
        progress=0,
        file=str(path),
        requested_privacy=privacy,
    )

    response = None
    retry_count = 0
    max_retries = int(config.get("youtube_upload_retries", 10))

    while response is None:
        try:
            progress, response = request.next_chunk()

            if progress is not None:
                pct = int(round(progress.progress() * 100))
                status(
                    "UPLOADING",
                    f"{path.name} — {pct}%",
                    progress=pct,
                    file=str(path),
                    requested_privacy=privacy,
                )

        except HttpError as exc:
            code = getattr(exc.resp, "status", None)

            if code not in RETRIABLE or retry_count >= max_retries:
                raise

            retry_count += 1
            status(
                "RETRYING",
                f"YouTube temporary error {code}; "
                f"retry {retry_count}/{max_retries}.",
                file=str(path),
                requested_privacy=privacy,
            )
            time.sleep(
                min((2 ** retry_count) * random.random(), 60)
            )

        except (OSError, TimeoutError) as exc:
            if retry_count >= max_retries:
                raise

            retry_count += 1
            status(
                "RETRYING",
                f"Network/upload error; retry "
                f"{retry_count}/{max_retries}: {exc}",
                file=str(path),
                requested_privacy=privacy,
            )
            time.sleep(min(2 ** retry_count, 60))

    video_id = str(response.get("id", "")).strip()
    if not video_id:
        raise RuntimeError("YouTube returned no video ID.")

    actual_privacy = ""
    try:
        r = youtube.videos().list(
            part="status",
            id=video_id
        ).execute()

        items = r.get("items", [])
        if items:
            actual_privacy = str(
                items[0].get("status", {}).get("privacyStatus", "")
            ).strip()
    except Exception:
        pass

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    record_history(
        plan,
        candidate,
        video_id,
        video_url,
        privacy,
        actual_privacy,
    )

    if privacy == "public" and actual_privacy == "private":
        return status(
            "UPLOADED_PRIVATE",
            "Upload succeeded, but YouTube kept the video PRIVATE. "
            "The API project may require YouTube compliance verification.",
            ok=True,
            warning=True,
            progress=100,
            file=str(path),
            video_id=video_id,
            video_url=video_url,
            requested_privacy=privacy,
            actual_privacy=actual_privacy,
        )

    return status(
        "UPLOADED",
        f'Uploaded "{title}" successfully.',
        ok=True,
        progress=100,
        file=str(path),
        video_id=video_id,
        video_url=video_url,
        requested_privacy=privacy,
        actual_privacy=actual_privacy,
    )


def find_candidate(config, plan, trigger_epoch, manual=False, preview=False):
    wait_minutes = float(
        config.get("youtube_candidate_wait_minutes", 360)
    )
    poll_seconds = float(
        config.get("youtube_candidate_poll_seconds", 30)
    )
    deadline = time.time() + wait_minutes * 60

    while True:
        candidates = eligible_files(
            config,
            plan,
            trigger_epoch,
            manual=manual
        )

        if candidates:
            return candidates[0]

        if preview:
            return None

        if time.time() >= deadline:
            return None

        status(
            "WAITING_FOR_RECORDING",
            "Waiting for the full-size, stable sermon recording "
            f"for {plan['service_date']}."
        )
        time.sleep(poll_seconds)


def run(authorize_only=False, interactive=False,
        manual=False, preview=False):
    config = load_config()

    if authorize_only:
        return {
            "state": "AUTHORIZED",
            "channel": authorize(config)
        }

    plan = load_plan()
    service_date = parse_date(plan["service_date"])
    today = now().date()

    if service_date != today:
        return status(
            "SKIPPED_DATE",
            f"Sermon plan is for {service_date}; today is {today}. "
            "Nothing was uploaded.",
            warning=True
        )

    trigger_epoch = time.time()

    candidate = find_candidate(
        config,
        plan,
        trigger_epoch,
        manual=manual,
        preview=preview
    )

    if preview:
        if candidate is None:
            return status(
                "PREVIEW_NONE",
                "No recording currently passes the "
                "date/size/duration/stability checks.",
                warning=True
            )

        size_gb = candidate["size"] / (1024 ** 3)
        mins = candidate["duration"] / 60

        return status(
            "PREVIEW_READY",
            f"{candidate['path']} | {size_gb:.2f} GB | {mins:.1f} minutes",
            ok=True,
            file=str(candidate["path"])
        )

    if candidate is None:
        return status(
            "NO_RECORDING",
            "No full sermon recording became eligible before "
            "the upload wait period expired.",
            warning=True
        )

    duplicate = duplicate_entry(plan, candidate)
    if duplicate:
        return status(
            "ALREADY_UPLOADED",
            "This sermon/recording was already uploaded.",
            ok=True,
            file=str(candidate["path"]),
            video_id=duplicate.get("video_id", ""),
            video_url=duplicate.get("video_url", ""),
            requested_privacy=duplicate.get("requested_privacy", ""),
            actual_privacy=duplicate.get("actual_privacy", ""),
        )

    youtube = youtube_service(config, interactive=interactive)
    verify_channel(youtube)

    return upload(youtube, config, plan, candidate)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--authorize-only", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Search the whole service date instead of only a stop-event window."
    )
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    try:
        result = run(
            authorize_only=args.authorize_only,
            interactive=args.interactive,
            manual=args.manual,
            preview=args.preview,
        )

        if not args.quiet:
            print()
            print("YOUTUBE SERMON UPLOAD")
            print("=" * 68)

            if args.authorize_only:
                channel = result["channel"]
                print("Authorized channel:")
                print(f"  {channel.get('channel_title', '')}")
                print(f"  {channel.get('channel_id', '')}")
            else:
                print(result.get("state", ""))
                print(result.get("message", ""))
                if result.get("video_url"):
                    print(result["video_url"])
            print()

        return 0

    except Exception as exc:
        result = status(
            "ERROR",
            str(exc),
            warning=True
        )

        if not args.quiet:
            print()
            print("YouTube upload error:")
            print(result["message"])
            print()

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
