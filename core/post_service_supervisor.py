import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from sunday_common import load_config
from sss_reliability import (
    BASE,
    POST_STATUS_FILE,
    atomic_json,
    now_iso,
    read_json,
    find_full_sermon_recording,
    find_service_srt,
    ffprobe_chapters,
    process_running_contains,
    internet_reachable,
    collect_known_logs,
    set_freeze,
)

PLAN_FILE = BASE / "sermon_plan.json"
PLANNING_STATUS = BASE / "planning_update_status.json"
YOUTUBE_STATUS = BASE / "youtube_upload_status.json"
YOUTUBE_HISTORY = BASE / "youtube_upload_history.json"
THUMBNAIL_SCRIPT = BASE / "core" / "thumbnail_handoff.py"
CLEANUP_SCRIPT = BASE / "core" / "operational_cleanup.py"
YOUTUBE_WORKER = BASE / "core" / "youtube_studio_upload_worker.py"


def write_state(
    plan,
    stages,
    state,
    message
):
    payload = {
        "updated": now_iso(),
        "plan_id": plan.get(
            "plan_id",
            ""
        ),
        "service_date": plan.get(
            "service_date",
            ""
        ),
        "title": plan.get(
            "title",
            ""
        ),
        "state": state,
        "message": message,
        "stages": stages,
    }

    atomic_json(
        POST_STATUS_FILE,
        payload
    )

    return payload


def stage(
    state,
    detail,
    *,
    blocking=True
):
    return {
        "state": state,
        "detail": detail,
        "blocking": bool(
            blocking
        ),
    }


def launch_hidden(
    script,
    *args
):
    pythonw = (
        BASE
        /
        "venv"
        /
        "Scripts"
        /
        "pythonw.exe"
    )

    if not pythonw.exists():
        return False

    try:
        subprocess.Popen(
            [
                str(
                    pythonw
                ),
                str(
                    script
                ),
                *args,
            ],
            cwd=BASE,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        return True

    except Exception:
        return False


def processors_running():
    names = [
        "process_shorts.py",
        "render_shorts.py",
        "prepare_sermon.py",
    ]

    active = [
        name
        for name in names
        if process_running_contains(
            name
        )
    ]

    return active


def youtube_stage(
    config,
    plan,
    recording,
    *,
    allow_launch=True
):
    history = read_json(
        YOUTUBE_HISTORY,
        {
            "uploads": []
        }
    )

    current_upload = None

    for entry in history.get(
        "uploads",
        []
    ):
        if (
            entry.get(
                "plan_id"
            )
            ==
            plan.get(
                "plan_id"
            )
        ):
            current_upload = entry
            break

    if current_upload is not None:
        detail = (
            "YouTube upload complete"
            +
            (
                f" — {current_upload.get('video_url')}"
                if current_upload.get(
                    "video_url"
                )
                else
                "."
            )
        )

        return (
            stage(
                "COMPLETE",
                detail,
            ),
            False,
        )

    payload = read_json(
        YOUTUBE_STATUS,
        {}
    )

    state_name = str(
        payload.get(
            "state",
            ""
        )
    ).upper()

    # An UPLOADED state without a matching current-plan history record
    # belongs to an older Sunday and must not satisfy this service.
    if state_name in {
        "UPLOADED",
        "ALREADY_UPLOADED",
    }:
        state_name = ""

    if state_name in {
        "UPLOADING",
        "PUBLISHING",
        "CHANNEL_VERIFIED",
        "WAITING_FOR_RECORDING",
    }:
        return (
            stage(
                "RUNNING",
                payload.get(
                    "message",
                    "YouTube upload is running."
                ),
            ),
            False,
        )

    online = internet_reachable(
        config.get(
            "internet_test_host",
            "www.youtube.com"
        ),
        config.get(
            "internet_test_port",
            443
        ),
        4
    )

    if not online:
        return (
            stage(
                "WAITING",
                (
                    "Internet is offline. Local recording is safe; "
                    "YouTube will retry automatically."
                ),
            ),
            False,
        )

    if recording is None:
        return (
            stage(
                "WAITING",
                "Waiting for a valid full sermon recording."
            ),
            False,
        )

    running = process_running_contains(
        "youtube_studio_upload_worker.py"
    )

    if not running and allow_launch:
        launch_hidden(
            YOUTUBE_WORKER,
            "--manual",
            "--quiet",
        )

        return (
            stage(
                "RUNNING",
                "Started/restarted YouTube Studio upload worker."
            ),
            True,
        )

    if not running:
        return (
            stage(
                "WAITING",
                (
                    "YouTube retry is cooling down after the last attempt. "
                    "Local recording is safe."
                ),
            ),
            False,
        )

    return (
        stage(
            "RUNNING",
            (
                payload.get(
                    "message"
                )
                or
                "YouTube Studio upload worker is running."
            ),
        ),
        False,
    )


def planning_stage(
    plan
):
    payload = read_json(
        PLANNING_STATUS,
        {}
    )

    status_service_date = str(
        payload.get(
            "service_date",
            ""
        )
    ).strip()

    if (
        status_service_date
        and
        status_service_date
        !=
        str(
            plan.get(
                "service_date",
                ""
            )
        ).strip()
    ):
        return stage(
            "WAITING",
            "Planning status belongs to a different service date.",
            blocking=False,
        )

    status_name = str(
        payload.get(
            "status",
            ""
        )
    ).upper()

    if status_name in {
        "UPDATED",
        "ALREADY_CORRECT",
    }:
        return stage(
            "COMPLETE",
            payload.get(
                "message",
                "Planning Scripture is correct."
            ),
            blocking=False,
        )

    if status_name in {
        "SKIPPED",
        "ERROR",
    }:
        return stage(
            "ATTENTION",
            payload.get(
                "message",
                "Planning needs review."
            ),
            blocking=False,
        )

    return stage(
        "WAITING",
        (
            payload.get(
                "message"
            )
            or
            "Planning status has not been confirmed."
        ),
        blocking=False,
    )


def maybe_make_thumbnail_handoff(
    plan,
    transcript_ready
):
    if not transcript_ready:
        return stage(
            "WAITING",
            "Waiting for transcript.",
            blocking=False,
        )

    if not THUMBNAIL_SCRIPT.exists():
        return stage(
            "ATTENTION",
            "Thumbnail handoff script is missing.",
            blocking=False,
        )

    marker = (
        BASE
        /
        "State"
        /
        (
            "thumbnail_handoff_"
            +
            str(
                plan.get(
                    "service_date",
                    "unknown"
                )
            )
            +
            ".json"
        )
    )

    if marker.exists():
        return stage(
            "COMPLETE",
            "Thumbnail handoff files prepared.",
            blocking=False,
        )

    python = (
        BASE
        /
        "venv"
        /
        "Scripts"
        /
        "python.exe"
    )

    try:
        cp = subprocess.run(
            [
                str(
                    python
                ),
                str(
                    THUMBNAIL_SCRIPT
                ),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            timeout=20,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        if cp.returncode == 0:
            atomic_json(
                marker,
                {
                    "done": now_iso(),
                    "path": cp.stdout.strip(),
                }
            )

            return stage(
                "COMPLETE",
                "Thumbnail handoff files prepared.",
                blocking=False,
            )

        return stage(
            "ATTENTION",
            (
                cp.stderr.strip()
                or
                cp.stdout.strip()
                or
                "Thumbnail handoff failed."
            ),
            blocking=False,
        )

    except Exception as exc:
        return stage(
            "ATTENTION",
            f"Thumbnail handoff failed: {exc}",
            blocking=False,
        )


def run():
    config = load_config()
    plan = read_json(
        PLAN_FILE,
        {}
    )

    if not plan.get(
        "service_date"
    ):
        write_state(
            plan,
            {},
            "WAITING",
            "No current sermon plan is available."
        )
        return 1

    timeout_hours = float(
        config.get(
            "post_service_supervisor_hours",
            8
        )
    )

    deadline = (
        time.time()
        +
        timeout_hours
        *
        60
        *
        60
    )

    last_upload_retry = 0.0

    while time.time() < deadline:
        stages = {}

        recording = find_full_sermon_recording(
            config,
            plan,
            require_stable=True,
            require_duration=True,
        )

        if recording is None:
            stages[
                "recording"
            ] = stage(
                "WAITING",
                (
                    "Waiting for the full sermon recording to finish "
                    "and become stable."
                ),
            )
        else:
            size_gb = (
                recording[
                    "size"
                ]
                /
                (
                    1024 ** 3
                )
            )

            minutes = (
                recording[
                    "duration"
                ]
                /
                60
            )

            stages[
                "recording"
            ] = stage(
                "COMPLETE",
                (
                    f"{recording['path'].name} — "
                    f"{size_gb:.2f} GB / {minutes:.1f} min"
                ),
            )

        transcript = find_service_srt(
            plan
        )

        transcript_ready = (
            transcript is not None
        )

        if transcript_ready:
            stages[
                "transcript"
            ] = stage(
                "COMPLETE",
                transcript.name,
            )
        else:
            stages[
                "transcript"
            ] = stage(
                "WAITING",
                "Waiting for full sermon SRT."
            )

        active_processors = processors_running()

        if active_processors:
            stages[
                "sermon_ai"
            ] = stage(
                "RUNNING",
                (
                    "Processing: "
                    +
                    ", ".join(
                        active_processors
                    )
                ),
            )

        elif (
            recording is not None
            and
            transcript_ready
            and
            time.time()
            -
            recording[
                "mtime"
            ]
            >=
            300
        ):
            stages[
                "sermon_ai"
            ] = stage(
                "COMPLETE",
                "Transcript/shorts processing is idle and complete."
            )

        else:
            stages[
                "sermon_ai"
            ] = stage(
                "WAITING",
                "Waiting for Sermon AI post-processing."
            )

        if recording is not None:
            chapters = ffprobe_chapters(
                recording[
                    "path"
                ]
            )

            if chapters:
                stages[
                    "chapters"
                ] = stage(
                    "COMPLETE",
                    f"{len(chapters)} embedded chapter marker(s) found."
                )

            else:
                stages[
                    "chapters"
                ] = stage(
                    "ATTENTION",
                    (
                        "No embedded MP4 chapters were found. "
                        "Recording is safe, but chapter markers need review."
                    ),
                )

        else:
            stages[
                "chapters"
            ] = stage(
                "WAITING",
                "Waiting for recording before chapter verification."
            )

        stages[
            "planning"
        ] = planning_stage(
            plan
        )

        retry_interval = float(
            config.get(
                "youtube_retry_interval_seconds",
                300
            )
        )

        allow_youtube_launch = (
            last_upload_retry
            ==
            0.0
            or
            time.time()
            -
            last_upload_retry
            >=
            retry_interval
        )

        youtube, launched = youtube_stage(
            config,
            plan,
            recording,
            allow_launch=allow_youtube_launch,
        )

        if launched:
            last_upload_retry = time.time()

        stages[
            "youtube"
        ] = youtube

        stages[
            "thumbnail"
        ] = maybe_make_thumbnail_handoff(
            plan,
            transcript_ready
        )

        blocking = [
            item
            for item in stages.values()
            if item.get(
                "blocking",
                True
            )
        ]

        has_attention = any(
            item[
                "state"
            ]
            ==
            "ATTENTION"
            for item in blocking
        )

        all_done = all(
            item[
                "state"
            ]
            in {
                "COMPLETE",
                "ATTENTION",
            }
            for item in blocking
        )

        youtube_done = (
            stages[
                "youtube"
            ][
                "state"
            ]
            ==
            "COMPLETE"
        )

        if (
            all_done
            and
            youtube_done
        ):
            if has_attention:
                overall = "ATTENTION"
                message = (
                    "Post-service processing finished, but one or more "
                    "items need review before declaring everything complete."
                )
            else:
                overall = "COMPLETE"
                message = (
                    "Everything finished — recording and post-service "
                    "automation are complete. Safe to shut down."
                )

            write_state(
                plan,
                stages,
                overall,
                message,
            )

            collect_known_logs(
                plan.get(
                    "service_date"
                )
            )

            set_freeze(
                False
            )

            if (
                overall
                ==
                "COMPLETE"
                and
                config.get(
                    "auto_operational_cleanup",
                    True
                )
                and
                CLEANUP_SCRIPT.exists()
            ):
                launch_hidden(
                    CLEANUP_SCRIPT
                )

            return 0

        write_state(
            plan,
            stages,
            "RUNNING",
            "Post-service jobs are still finishing.",
        )

        time.sleep(
            20
        )

    write_state(
        plan,
        stages,
        "ATTENTION",
        (
            "Post-service supervisor reached its time limit. "
            "Local files were preserved; review unfinished items."
        ),
    )

    return 2


def main():
    try:
        return run()

    except Exception as exc:
        plan = read_json(
            PLAN_FILE,
            {}
        )

        write_state(
            plan,
            {},
            "ATTENTION",
            f"Post-service supervisor error: {exc}",
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
