import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from sunday_common import load_config
from sss_reliability import ffprobe_chapters

BASE = Path(r"C:\Church\SermonAI")
PLAN_FILE = BASE / "sermon_plan.json"
STATUS_FILE = BASE / "youtube_upload_status.json"
HISTORY_FILE = BASE / "youtube_upload_history.json"
LOG_FILE = BASE / "youtube_upload.log"

DEFAULT_CHANNEL_ID = ""
DEFAULT_CHANNEL_NAME = ""


def now():
    return datetime.now().astimezone()


def now_iso():
    return now().isoformat(timespec="seconds")


def log(message):
    try:
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(
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
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def write_status(
    state,
    message,
    *,
    ok=False,
    warning=False,
    progress=None,
    file="",
    video_id="",
    video_url="",
):
    payload = {
        "mode": "studio",
        "updated": now_iso(),
        "state": state,
        "message": message,
        "ok": bool(ok),
        "warning": bool(warning),
        "progress": progress,
        "file": file,
        "video_id": video_id,
        "video_url": video_url,
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
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", path.name)
    if not match:
        return None
    return parse_date(match.group(1))


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
            timeout=25,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        if cp.returncode != 0:
            return 0.0

        return float(cp.stdout.strip())

    except Exception:
        return 0.0


def load_plan():
    if not PLAN_FILE.exists():
        raise RuntimeError("sermon_plan.json is missing.")

    plan = read_json(PLAN_FILE, {})

    for key in ("plan_id", "title", "scripture", "service_date"):
        if not str(plan.get(key, "")).strip():
            raise RuntimeError(
                f"sermon_plan.json is missing {key}."
            )

    return plan


def eligible_recordings(config, plan, trigger_epoch, manual=False):
    folder = Path(
        config.get(
            "recording_folder",
            r"D:\2026"
        )
    )

    if not folder.exists():
        return []

    service_date = parse_date(
        plan.get("service_date")
    )

    if service_date is None:
        return []

    extensions = {
        str(item).lower()
        if str(item).startswith(".")
        else "." + str(item).lower()
        for item in config.get(
            "youtube_video_extensions",
            [".mp4"]
        )
    }

    min_bytes = int(
        float(
            config.get(
                "youtube_min_file_mb",
                500
            )
        )
        * 1024 * 1024
    )

    min_seconds = (
        float(
            config.get(
                "youtube_min_duration_minutes",
                20
            )
        )
        * 60
    )

    stable_seconds = float(
        config.get(
            "youtube_file_stable_seconds",
            300
        )
    )

    lookback_seconds = (
        float(
            config.get(
                "youtube_trigger_lookback_minutes",
                15
            )
        )
        * 60
    )

    current_time = time.time()
    found = []

    # Root of D:\2026 ONLY. Never recurse into shorts, SRT files,
    # Ready, Sermon Data, or any other generated folders.
    for path in folder.iterdir():
        if not path.is_file():
            continue

        if path.suffix.lower() not in extensions:
            continue

        if filename_date(path) != service_date:
            continue

        try:
            info = path.stat()
        except OSError:
            continue

        if info.st_size < min_bytes:
            continue

        if (
            not manual
            and
            info.st_mtime < (
                trigger_epoch
                -
                lookback_seconds
            )
        ):
            continue

        if (
            current_time
            -
            info.st_mtime
        ) < stable_seconds:
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

    # Largest eligible recording wins. This keeps a tiny accidental
    # recording or shorter rehearsal from being selected.
    found.sort(
        key=lambda item: (
            item["size"],
            item["mtime"],
        ),
        reverse=True,
    )

    return found


def wait_for_candidate(
    config,
    plan,
    trigger_epoch,
    *,
    manual=False,
    preview=False
):
    wait_minutes = float(
        config.get(
            "youtube_candidate_wait_minutes",
            360
        )
    )

    poll_seconds = float(
        config.get(
            "youtube_candidate_poll_seconds",
            30
        )
    )

    deadline = (
        time.time()
        +
        wait_minutes * 60
    )

    while True:
        candidates = eligible_recordings(
            config,
            plan,
            trigger_epoch,
            manual=manual,
        )

        if candidates:
            return candidates[0]

        if preview:
            return None

        if time.time() >= deadline:
            return None

        write_status(
            "WAITING_FOR_RECORDING",
            (
                "Waiting for the full-size, stable sermon recording "
                f"for {plan['service_date']}."
            ),
        )

        time.sleep(poll_seconds)


def upload_history():
    return read_json(
        HISTORY_FILE,
        {"uploads": []}
    )


def already_uploaded(plan, candidate):
    plan_id = str(
        plan.get("plan_id", "")
    )

    full_path = str(
        candidate["path"].resolve()
    ).lower()

    size = int(
        candidate["size"]
    )

    for entry in upload_history().get(
        "uploads",
        []
    ):
        if (
            plan_id
            and
            entry.get("plan_id") == plan_id
        ):
            return entry

        if (
            str(entry.get("file", "")).lower()
            ==
            full_path
            and
            int(entry.get("size", -1))
            ==
            size
        ):
            return entry

    return None


def add_history(
    plan,
    candidate,
    *,
    video_id="",
    video_url="",
    visibility="public"
):
    data = upload_history()

    data.setdefault(
        "uploads",
        []
    ).append(
        {
            "uploaded": now_iso(),
            "mode": "studio",
            "plan_id": plan.get("plan_id", ""),
            "service_date": plan.get("service_date", ""),
            "title": plan.get("title", ""),
            "scripture": plan.get("scripture", ""),
            "file": str(candidate["path"].resolve()),
            "size": int(candidate["size"]),
            "duration_seconds": float(candidate["duration"]),
            "video_id": video_id,
            "video_url": video_url,
            "visibility": visibility,
        }
    )

    save_json(
        HISTORY_FILE,
        data
    )


def sermon_title(plan):
    title = str(
        plan.get("title", "")
    ).strip()

    if not title:
        raise RuntimeError(
            "Pastor sermon title is empty."
        )

    # YouTube Studio title limit.
    return title[:100].rstrip()


def format_youtube_timestamp(
    seconds
):
    total = max(
        0,
        int(
            round(
                float(
                    seconds
                )
            )
        )
    )

    hours, remainder = divmod(
        total,
        3600
    )

    minutes, seconds = divmod(
        remainder,
        60
    )

    if hours:
        return (
            f"{hours}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    return (
        f"{minutes}:"
        f"{seconds:02d}"
    )


def sermon_description(
    plan,
    video_path=None
):
    lines = []

    title = str(
        plan.get("title", "")
    ).strip()

    scripture = str(
        plan.get("scripture", "")
    ).strip()

    preacher = str(
        plan.get("preacher", "")
    ).strip()

    points = plan.get(
        "points",
        []
    )

    if title:
        lines.append(title)

    if scripture:
        lines.append(scripture)

    if preacher:
        lines.extend(
            [
                "",
                f"Preacher: {preacher}",
            ]
        )

    if isinstance(points, list) and points:
        lines.extend(
            [
                "",
                "Sermon Outline:",
            ]
        )

        for index, point in enumerate(
            points,
            start=1
        ):
            point = str(point).strip()

            if point:
                lines.append(
                    f"{index}. {point}"
                )

    # Reuse the chapter markers already embedded into the full OBS MP4.
    # This lets the YouTube description receive real sermon timestamps
    # without delaying the initial upload for a separate editing pass.
    if video_path is not None:
        chapters = ffprobe_chapters(
            video_path
        )

        if chapters:
            chapter_lines = []

            sorted_chapters = sorted(
                chapters,
                key=lambda item: float(
                    item.get(
                        "start",
                        0
                    )
                )
            )

            first_stamp = format_youtube_timestamp(
                float(
                    sorted_chapters[
                        0
                    ].get(
                        "start",
                        0
                    )
                )
            )

            # YouTube requires the first manual chapter timestamp to be
            # exactly 0:00. Add a safe opening entry whenever the first
            # embedded chapter would render later than that.
            if first_stamp != "0:00":
                chapter_lines.append(
                    "0:00 Sermon"
                )

            seen = set()

            for index, item in enumerate(
                sorted_chapters,
                start=1
            ):
                start_seconds = float(
                    item.get(
                        "start",
                        0
                    )
                )

                stamp = format_youtube_timestamp(
                    start_seconds
                )

                if stamp in seen:
                    continue

                seen.add(
                    stamp
                )

                chapter_title = str(
                    item.get(
                        "title",
                        ""
                    )
                ).strip()

                if not chapter_title:
                    chapter_title = (
                        f"Chapter {index}"
                    )

                chapter_lines.append(
                    f"{stamp} {chapter_title}"
                )

            if chapter_lines:
                lines.extend(
                    [
                        "",
                        "Chapters:",
                        *chapter_lines,
                    ]
                )

    return "\n".join(
        lines
    ).strip()[:5000]

def profile_in_use(profile):
    profile_text = str(profile).replace(
        "'",
        "''"
    )

    ps = (
        "$profile = '" + profile_text + "'; "
        "$escaped = [Regex]::Escape($profile); "
        "$p = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
        "Where-Object { "
        "$_.CommandLine -and $_.CommandLine -match $escaped -and "
        "($_.Name -ieq 'chrome.exe' -or $_.Name -ieq 'msedge.exe') "
        "}; "
        "if ($p) { $p.ProcessId }"
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
            timeout=8,
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


def text_value(locator):
    try:
        return locator.inner_text(
            timeout=1000
        ).strip()
    except Exception:
        return ""


def set_editable_text(locator, value):
    locator.wait_for(
        state="visible",
        timeout=15000
    )

    try:
        locator.fill(value)
        return
    except Exception:
        pass

    locator.click()
    locator.press("Control+A")
    locator.press("Backspace")
    locator.press_sequentially(
        value,
        delay=1
    )


def first_visible(locators):
    for locator in locators:
        try:
            count = locator.count()
        except Exception:
            continue

        for index in range(
            min(count, 15)
        ):
            item = locator.nth(index)

            try:
                if item.is_visible():
                    return item
            except Exception:
                pass

    return None


def body_text(page):
    try:
        return page.locator(
            "body"
        ).inner_text(
            timeout=5000
        )
    except Exception:
        return ""


def verify_church_channel(
    page,
    expected_id,
    expected_name
):
    url = page.url

    if (
        f"/channel/{expected_id}"
        not in
        url
    ):
        raise RuntimeError(
            "YOUTUBE UPLOAD BLOCKED: Studio is not on the authorized "
            f"church channel ID {expected_id}. Current URL: {url}"
        )

    text = body_text(page)

    if expected_name.lower() not in text.lower():
        raise RuntimeError(
            "YOUTUBE UPLOAD BLOCKED: Expected church channel name "
            f"'{expected_name}' is not visible in Studio."
        )

    if (
        "you're a manager"
        not in
        text.lower()
        and
        "you’re a manager"
        not in
        text.lower()
    ):
        raise RuntimeError(
            "YOUTUBE UPLOAD BLOCKED: Studio does not show the delegated "
            "Manager role for this channel."
        )


def open_upload_dialog(page):
    dismiss_feature_announcement(page)

    # Diagnostic confirmed a dedicated Upload videos icon/button exists.
    upload_button = first_visible(
        [
            page.get_by_role(
                "button",
                name="Upload videos",
                exact=True
            ),
            page.locator(
                '[role="button"][aria-label="Upload videos"]'
            ),
        ]
    )

    if upload_button is None:
        create = first_visible(
            [
                page.get_by_role(
                    "button",
                    name="Create",
                    exact=True
                ),
                page.get_by_text(
                    "Create",
                    exact=True
                ),
            ]
        )

        if create is None:
            raise RuntimeError(
                "Could not find YouTube Studio Create/Upload videos control."
            )

        create.click()
        page.wait_for_timeout(400)

        upload_button = first_visible(
            [
                page.get_by_text(
                    "Upload videos",
                    exact=True
                ),
                page.get_by_role(
                    "menuitem",
                    name="Upload videos",
                    exact=True
                ),
            ]
        )

    if upload_button is None:
        raise RuntimeError(
            "Could not open YouTube Studio Upload videos dialog."
        )

    upload_button.click()

    select_files_button = first_visible(
        [
            page.get_by_role(
                "button",
                name=re.compile(
                    r"^\s*Select files\s*$",
                    re.IGNORECASE
                ),
            ),
            page.get_by_text(
                "Select files",
                exact=True
            ),
        ]
    )

    if select_files_button is None:
        raise RuntimeError(
            "Could not find the YouTube Studio "
            "\"Select files\" button."
        )

    return select_files_button


def select_upload_file(page, select_files_button, path):
    """
    Directly calling set_input_files() on the hidden
    input[type=file][name=Filedata] used to work, but observed
    2026-09-01: it now makes the "Select files" button flash a
    disabled state for a moment and then silently reset, with no file
    ever actually accepted -- Studio's picker no longer appears to be
    driven by that input's change event alone. Intercepting the real
    native file-chooser dialog that clicking the button opens
    (Playwright's expect_file_chooser) works regardless of which JS
    API the button uses internally underneath.
    """

    with page.expect_file_chooser(
        timeout=15000
    ) as file_chooser_info:

        select_files_button.click()

    file_chooser_info.value.set_files(
        str(path)
    )


def dismiss_feature_announcement(page):
    """
    YouTube Studio occasionally shows a one-off feature-announcement
    modal ("You're all set / You already have access to this feature")
    on top of the upload dialog. Observed 2026-09-01 sitting over the
    Upload videos dialog and permanently blocking the title field from
    ever becoming reachable, since nothing in the flow dismisses it.
    Only targets the exact known "Got it" button -- deliberately does
    NOT swallow generic OK/Close buttons, so a real warning dialog
    (e.g. a copyright claim) still surfaces to a human.
    """

    try:
        button = page.get_by_role(
            "button",
            name=re.compile(
                r"^\s*Got it\s*$",
                re.IGNORECASE
            ),
        )

        if (
            button.count()
            and
            button.first.is_visible()
        ):
            button.first.click()
            page.wait_for_timeout(300)

    except Exception:
        pass


def find_title_box(page, attempts=30, interval_ms=500):
    """
    Right after the file is attached, Studio still has to open the
    upload dialog and render the Details form -- for a large file this
    can take several seconds. A single immediate lookup reliably misses
    it, so poll instead of checking once.
    """
    locators = [
        page.locator(
            "ytcp-social-suggestions-textbox#title-textarea #textbox"
        ),
        page.locator(
            "#title-textarea #textbox"
        ),
        page.locator(
            '[aria-label*="Title" i][contenteditable="true"]'
        ),
        page.get_by_label(
            re.compile(
                r"Title",
                re.IGNORECASE
            )
        ),
    ]

    for _ in range(attempts):
        dismiss_feature_announcement(page)

        item = first_visible(locators)

        if item is not None:
            return item

        page.wait_for_timeout(interval_ms)

    try:
        page.screenshot(
            path=str(
                Path(__file__).parent
                / "youtube_title_box_debug.png"
            ),
            full_page=False,
        )

        Path(
            Path(__file__).parent
            / "youtube_title_box_debug.html"
        ).write_text(
            page.content(),
            encoding="utf-8",
        )

    except Exception:
        pass

    raise RuntimeError(
        "Could not identify the YouTube title field."
    )


def find_description_box(page):
    item = first_visible(
        [
            page.locator(
                "ytcp-social-suggestions-textbox#description-textarea #textbox"
            ),
            page.locator(
                "#description-textarea #textbox"
            ),
            page.locator(
                '[aria-label*="Description" i][contenteditable="true"]'
            ),
            page.get_by_label(
                re.compile(
                    r"Description",
                    re.IGNORECASE
                )
            ),
        ]
    )

    return item


def audience_is_selected(page):
    checked = page.locator(
        '[role="radio"][aria-checked="true"]'
    )

    for index in range(
        min(checked.count(), 30)
    ):
        item = checked.nth(index)

        try:
            context = item.evaluate(
                """
                (el) => {
                    const parent =
                        el.closest('ytcp-form-radio-button, tp-yt-paper-radio-button, div');
                    return parent ? parent.innerText : el.innerText;
                }
                """
            )
        except Exception:
            context = text_value(item)

        lower = str(context).lower()

        if (
            "made for kids"
            in
            lower
            or
            "made for children"
            in
            lower
        ):
            return True

    return False


def ensure_audience(page, config):
    if audience_is_selected(page):
        return

    setting = str(
        config.get(
            "youtube_audience",
            "channel_default"
        )
    ).strip().lower()

    if setting == "channel_default":
        raise RuntimeError(
            "YouTube Studio requires an audience choice, but no channel "
            "default was selected. Automation stopped before publishing. "
            "Set a channel upload default or set youtube_audience explicitly."
        )

    if setting == "not_made_for_kids":
        target_texts = [
            "No, it's not made for kids",
            "No, it’s not made for kids",
        ]

    elif setting == "made_for_kids":
        target_texts = [
            "Yes, it's made for kids",
            "Yes, it’s made for kids",
        ]

    else:
        raise RuntimeError(
            "youtube_audience must be channel_default, "
            "not_made_for_kids, or made_for_kids."
        )

    item = None

    for target in target_texts:
        item = first_visible(
            [
                page.get_by_text(
                    target,
                    exact=False
                ),
                page.get_by_label(
                    re.compile(
                        re.escape(
                            target.replace("’", "'")
                        ),
                        re.IGNORECASE
                    )
                ),
            ]
        )

        if item is not None:
            break

    if item is None:
        raise RuntimeError(
            "YouTube audience choice was required but the expected "
            "audience control could not be found."
        )

    item.click()
    page.wait_for_timeout(250)


def click_next(page):
    next_button = first_visible(
        [
            page.get_by_role(
                "button",
                name="Next",
                exact=True
            ),
            page.get_by_text(
                "Next",
                exact=True
            ),
        ]
    )

    if next_button is None:
        raise RuntimeError(
            "Could not find the YouTube Studio Next button."
        )

    deadline = time.time() + 120

    while time.time() < deadline:
        try:
            if next_button.is_enabled():
                next_button.click()
                page.wait_for_timeout(550)
                return
        except Exception:
            pass

        page.wait_for_timeout(750)

    raise RuntimeError(
        "YouTube Studio Next button never became enabled."
    )


def checks_have_blocker(text):
    lower = text.lower()

    blockers = [
        "copyright issue found",
        "copyright issues found",
        "ad suitability issue",
        "terms and policies issue",
        "checks found an issue",
    ]

    return any(
        item in lower
        for item in blockers
    )


def set_visibility(page, visibility):
    visibility = visibility.strip().lower()

    mapping = {
        "public": "Public",
        "unlisted": "Unlisted",
        "private": "Private",
    }

    if visibility not in mapping:
        raise RuntimeError(
            "youtube_privacy_status must be public, unlisted, or private."
        )

    label = mapping[
        visibility
    ]

    target = first_visible(
        [
            page.get_by_text(
                label,
                exact=True
            ),
            page.get_by_label(
                label,
                exact=True
            ),
        ]
    )

    if target is None:
        raise RuntimeError(
            f"Could not find YouTube visibility option: {label}"
        )

    try:
        radio = target.locator(
            "xpath=ancestor-or-self::*[@role='radio'][1]"
        )

        if radio.count():
            radio.first.click()
        else:
            target.click()
    except Exception:
        target.click()

    page.wait_for_timeout(300)


def find_publish_button(page):
    return first_visible(
        [
            page.get_by_role(
                "button",
                name="Publish",
                exact=True
            ),
            page.get_by_role(
                "button",
                name="Save",
                exact=True
            ),
            page.get_by_text(
                "Publish",
                exact=True
            ),
            page.get_by_text(
                "Save",
                exact=True
            ),
        ]
    )


def extract_video_identity(page, title):
    # First look for a direct watch/share link in the finished dialog.
    anchors = page.locator("a")

    for index in range(
        min(anchors.count(), 300)
    ):
        anchor = anchors.nth(index)

        try:
            href = (
                anchor.get_attribute("href")
                or
                ""
            )
        except Exception:
            href = ""

        match = re.search(
            r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,})",
            href
        )

        if match:
            video_id = match.group(1)
            return (
                video_id,
                f"https://www.youtube.com/watch?v={video_id}",
            )

    # Close finished dialog if present, then use Content page title link.
    close_button = first_visible(
        [
            page.get_by_role(
                "button",
                name="Close",
                exact=True
            ),
            page.locator(
                '[aria-label="Close"]'
            ),
        ]
    )

    if close_button is not None:
        try:
            close_button.click()
            page.wait_for_timeout(500)
        except Exception:
            pass

    content_link = first_visible(
        [
            page.get_by_text(
                "Content",
                exact=True
            )
        ]
    )

    if content_link is not None:
        try:
            content_link.click()
            page.wait_for_timeout(900)
        except Exception:
            pass

    title_links = page.locator("a")

    for index in range(
        min(title_links.count(), 600)
    ):
        anchor = title_links.nth(index)

        try:
            text = anchor.inner_text(
                timeout=200
            ).strip()
        except Exception:
            text = ""

        if text != title:
            continue

        try:
            href = (
                anchor.get_attribute("href")
                or
                ""
            )
        except Exception:
            href = ""

        match = re.search(
            r"/video/([A-Za-z0-9_-]{6,})/",
            href
        )

        if match:
            video_id = match.group(1)
            return (
                video_id,
                f"https://www.youtube.com/watch?v={video_id}",
            )

    return (
        "",
        "",
    )


def run_studio_upload(
    config,
    plan,
    candidate,
    *,
    show=True,
    dry_run=False
):
    expected_id = str(
        config.get(
            "youtube_expected_channel_id",
            DEFAULT_CHANNEL_ID
        )
    ).strip()

    expected_name = str(
        config.get(
            "youtube_expected_channel_name",
            DEFAULT_CHANNEL_NAME
        )
    ).strip()

    profile = Path(
        config.get(
            "youtube_studio_profile_folder",
            str(
                BASE
                /
                "YouTube_Studio_Profile"
            )
        )
    )

    if not profile.exists():
        raise RuntimeError(
            "YouTube Studio profile is missing. Run the normal Studio "
            "login helper first."
        )

    if profile_in_use(profile):
        raise RuntimeError(
            "The dedicated YouTube Studio profile is already open. "
            "Close the dedicated Studio browser before automatic upload."
        )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run the YouTube Studio setup."
        ) from exc

    title = sermon_title(plan)
    description = sermon_description(
        plan,
        candidate[
            "path"
        ]
    )

    visibility = str(
        config.get(
            "youtube_privacy_status",
            "public"
        )
    ).strip().lower()

    with sync_playwright() as p:
        context = None
        launch_errors = []

        for channel in (
            "chrome",
            "msedge"
        ):
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(profile),
                    channel=channel,
                    headless=(
                        not show
                    ),
                    viewport=(
                        None
                        if show
                        else {
                            "width": 1440,
                            "height": 1000,
                        }
                    ),
                    args=(
                        [
                            "--start-maximized"
                        ]
                        if show
                        else []
                    ),
                )
                break

            except Exception as exc:
                launch_errors.append(
                    f"{channel}: {exc}"
                )

        if context is None:
            raise RuntimeError(
                "Could not launch the saved YouTube Studio profile. "
                +
                " | ".join(launch_errors)
            )

        try:
            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )

            console_debug_path = (
                Path(__file__).parent
                / "youtube_console_debug.txt"
            )

            console_debug_path.write_text(
                "",
                encoding="utf-8"
            )

            def _log_console(message):
                try:
                    with open(
                        console_debug_path,
                        "a",
                        encoding="utf-8"
                    ) as handle:
                        handle.write(
                            f"[{message.type}] {message.text}\n"
                        )
                except Exception:
                    pass

            page.on(
                "console",
                _log_console
            )

            page.on(
                "pageerror",
                lambda exc: _log_console(
                    type(
                        "M",
                        (),
                        {
                            "type": "pageerror",
                            "text": str(exc)
                        }
                    )()
                )
            )

            target_url = (
                "https://studio.youtube.com/channel/"
                f"{expected_id}"
                f"?c={expected_id}"
            )

            page.goto(
                target_url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            page.wait_for_timeout(1200)

            verify_church_channel(
                page,
                expected_id,
                expected_name,
            )

            write_status(
                "CHANNEL_VERIFIED",
                (
                    f"Verified {expected_name} ({expected_id}). "
                    "Preparing full sermon upload."
                ),
                file=str(candidate["path"]),
            )

            select_files_button = open_upload_dialog(page)

            # Hard channel check AGAIN immediately before selecting file.
            verify_church_channel(
                page,
                expected_id,
                expected_name,
            )

            select_upload_file(
                page,
                select_files_button,
                candidate["path"]
            )

            try:
                page.wait_for_timeout(2000)

                files_len = page.evaluate(
                    "document.querySelector("
                    "'input[type=\"file\"][name=\"Filedata\"]'"
                    ").files.length"
                )

                Path(
                    Path(__file__).parent
                    / "youtube_files_debug.txt"
                ).write_text(
                    f"hidden input files.length = {files_len}\n",
                    encoding="utf-8",
                )

            except Exception as debug_error:
                Path(
                    Path(__file__).parent
                    / "youtube_files_debug.txt"
                ).write_text(
                    f"debug check failed: {debug_error}\n",
                    encoding="utf-8",
                )

            write_status(
                "UPLOADING",
                (
                    f"Studio accepted {candidate['path'].name}. "
                    f'Applying pastor title: "{title}"'
                ),
                progress=0,
                file=str(candidate["path"]),
            )

            title_box = find_title_box(page)

            set_editable_text(
                title_box,
                title
            )

            description_box = find_description_box(page)

            if description_box is not None:
                set_editable_text(
                    description_box,
                    description
                )

            ensure_audience(
                page,
                config
            )

            if dry_run:
                write_status(
                    "DRY_RUN",
                    (
                        "Channel verified and sermon file selected. "
                        "Title/description were filled, but the script "
                        "stopped before Next/Publish."
                    ),
                    ok=True,
                    warning=True,
                    file=str(candidate["path"]),
                )

                input(
                    "Dry run complete. Inspect Studio, then press Enter "
                    "to close the automation browser..."
                )

                return read_json(
                    STATUS_FILE,
                    {}
                )

            # Details -> Video elements
            click_next(page)

            # Video elements -> Checks
            click_next(page)

            # Checks page: wait briefly for a definitive blocker if one
            # appears, but do not wait hours for optional processing.
            check_deadline = time.time() + float(
                config.get(
                    "youtube_checks_wait_seconds",
                    300
                )
            )

            while time.time() < check_deadline:
                text = body_text(page)

                if checks_have_blocker(text):
                    raise RuntimeError(
                        "YouTube checks reported an issue. "
                        "Automation stopped before publishing."
                    )

                lower = text.lower()

                if (
                    "checks complete"
                    in
                    lower
                    or
                    "no issues found"
                    in
                    lower
                    or
                    "visibility"
                    in
                    lower
                ):
                    break

                page.wait_for_timeout(1500)

            # Checks -> Visibility
            click_next(page)

            set_visibility(
                page,
                visibility
            )

            publish_button = find_publish_button(page)

            if publish_button is None:
                raise RuntimeError(
                    "Could not find YouTube Studio Publish/Save button."
                )

            # Upload may still be transferring. Wait until YouTube enables
            # Publish/Save. Update visible percentages while waiting.
            publish_deadline = time.time() + (
                float(
                    config.get(
                        "youtube_studio_publish_wait_minutes",
                        360
                    )
                )
                *
                60
            )

            last_percent = None

            while time.time() < publish_deadline:
                text = body_text(page)

                percentages = [
                    int(value)
                    for value in re.findall(
                        r"\b(\d{1,3})%\b",
                        text
                    )
                    if 0 <= int(value) <= 100
                ]

                if percentages:
                    percent = max(percentages)

                    if percent != last_percent:
                        last_percent = percent

                        write_status(
                            "UPLOADING",
                            (
                                f"{candidate['path'].name} — "
                                f"{percent}%"
                            ),
                            progress=percent,
                            file=str(candidate["path"]),
                        )

                if checks_have_blocker(text):
                    raise RuntimeError(
                        "YouTube reported an issue before publish. "
                        "Automation stopped."
                    )

                try:
                    if publish_button.is_enabled():
                        break
                except Exception:
                    publish_button = find_publish_button(page)

                page.wait_for_timeout(2000)

            else:
                raise RuntimeError(
                    "YouTube Publish/Save did not become enabled before "
                    "the configured timeout."
                )

            publish_button.click()

            write_status(
                "PUBLISHING",
                (
                    f'Publishing "{title}" as {visibility}.'
                ),
                progress=100,
                file=str(candidate["path"]),
            )

            # Wait for a finished/published state.
            finish_deadline = time.time() + 180

            while time.time() < finish_deadline:
                text = body_text(page).lower()

                if (
                    "video published"
                    in
                    text
                    or
                    "video uploaded"
                    in
                    text
                    or
                    "processing will begin shortly"
                    in
                    text
                    or
                    "checks complete"
                    in
                    text
                ):
                    page.wait_for_timeout(600)
                    break

                page.wait_for_timeout(1000)

            video_id, video_url = extract_video_identity(
                page,
                title
            )

            add_history(
                plan,
                candidate,
                video_id=video_id,
                video_url=video_url,
                visibility=visibility,
            )

            return write_status(
                "UPLOADED",
                (
                    f'Uploaded "{title}" to {expected_name}'
                    +
                    (
                        f" — {video_url}"
                        if video_url
                        else
                        "."
                    )
                ),
                ok=True,
                progress=100,
                file=str(candidate["path"]),
                video_id=video_id,
                video_url=video_url,
            )

        finally:
            try:
                context.close()
            except Exception:
                pass


def run(
    *,
    manual=False,
    preview=False,
    dry_run=False,
    show=True
):
    config = load_config()
    plan = load_plan()

    service_date = parse_date(
        plan["service_date"]
    )

    today = now().date()

    grace_days = int(
        config.get(
            "youtube_service_date_grace_days",
            3
        )
    )

    if (
        service_date is None
        or
        (
            today
            -
            service_date
        ).days
        <
        0
        or
        (
            today
            -
            service_date
        ).days
        >
        grace_days
    ):
        return write_status(
            "SKIPPED_DATE",
            (
                f"Sermon plan is for {service_date}; today is {today}. "
                f"Automatic recovery only allows {grace_days} day(s) "
                "after the service. Nothing was uploaded."
            ),
            warning=True,
        )

    trigger_epoch = time.time()

    candidate = wait_for_candidate(
        config,
        plan,
        trigger_epoch,
        manual=manual,
        preview=preview,
    )

    if preview:
        if candidate is None:
            return write_status(
                "PREVIEW_NONE",
                (
                    "No recording currently passes the "
                    "date/size/duration/stability checks."
                ),
                warning=True,
            )

        size_gb = (
            candidate["size"]
            /
            (
                1024 ** 3
            )
        )

        minutes = (
            candidate["duration"]
            /
            60
        )

        return write_status(
            "PREVIEW_READY",
            (
                f"{candidate['path']} | "
                f"{size_gb:.2f} GB | "
                f"{minutes:.1f} minutes"
            ),
            ok=True,
            file=str(candidate["path"]),
        )

    if candidate is None:
        return write_status(
            "NO_RECORDING",
            (
                "No full sermon recording became eligible before "
                "the wait period expired."
            ),
            warning=True,
        )

    duplicate = already_uploaded(
        plan,
        candidate
    )

    if duplicate:
        return write_status(
            "ALREADY_UPLOADED",
            (
                "This sermon plan/recording is already in the "
                "YouTube upload history."
            ),
            ok=True,
            file=str(candidate["path"]),
            video_id=duplicate.get(
                "video_id",
                ""
            ),
            video_url=duplicate.get(
                "video_url",
                ""
            ),
        )

    return run_studio_upload(
        config,
        plan,
        candidate,
        show=show,
        dry_run=dry_run,
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--manual",
        action="store_true"
    )

    parser.add_argument(
        "--preview",
        action="store_true"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true"
    )

    parser.add_argument(
        "--headless",
        action="store_true"
    )

    parser.add_argument(
        "--quiet",
        action="store_true"
    )

    args = parser.parse_args()

    try:
        result = run(
            manual=args.manual,
            preview=args.preview,
            dry_run=args.dry_run,
            show=(
                not args.headless
            ),
        )

        if not args.quiet:
            print()
            print(
                "YOUTUBE STUDIO SERMON UPLOAD"
            )
            print(
                "=" * 72
            )
            print(
                result.get(
                    "state",
                    ""
                )
            )
            print(
                result.get(
                    "message",
                    ""
                )
            )

            if result.get(
                "video_url"
            ):
                print(
                    result[
                        "video_url"
                    ]
                )

            print()

        return 0

    except Exception as exc:
        result = write_status(
            "ERROR",
            str(exc),
            warning=True,
        )

        if not args.quiet:
            print()
            print(
                "YouTube Studio upload error:"
            )
            print(
                result[
                    "message"
                ]
            )
            print()

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
