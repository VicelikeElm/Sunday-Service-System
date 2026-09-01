import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sunday_common import load_config
from sss_reliability import (
    BASE,
    TEST_STATUS_FILE,
    atomic_json,
    read_json,
)

from sermon_chapter_manager import (
    build_sequence,
)

from ptz_settings import (
    PTZ_CONFIG_FILE,
    load_ptz_settings,
)

PLAN_FILE = BASE / "sermon_plan.json"


def result(
    name,
    ok,
    detail
):
    return {
        "name": name,
        "ok": bool(
            ok
        ),
        "detail": detail,
    }


def writable_folder(
    path
):
    path = Path(
        path
    )

    if not path.exists():
        return False

    probe = (
        path
        /
        ".sss_test_write.tmp"
    )

    try:
        probe.write_text(
            "ok",
            encoding="utf-8"
        )

        probe.unlink(
            missing_ok=True
        )

        return True

    except Exception:
        return False


def main():
    config = load_config()
    tests = []

    tests.append(
        result(
            "Sunday configuration",
            bool(
                config
            ),
            "sunday_config.json loaded"
        )
    )

    plan = read_json(
        PLAN_FILE,
        {}
    )

    plan_ok = all(
        str(
            plan.get(
                key,
                ""
            )
        ).strip()
        for key in (
            "title",
            "scripture",
            "service_date",
            "plan_id",
        )
    )

    tests.append(
        result(
            "Sermon plan",
            plan_ok,
            (
                f"{plan.get('title', '')} | "
                f"{plan.get('scripture', '')}"
                if plan_ok
                else
                "sermon_plan.json is incomplete"
            ),
        )
    )

    try:
        sequence = build_sequence(
            {
                "plan_id": str(
                    plan.get(
                        "plan_id",
                        ""
                    )
                ),
                "service_date": str(
                    plan.get(
                        "service_date",
                        ""
                    )
                ),
                "title": str(
                    plan.get(
                        "title",
                        ""
                    )
                ),
                "scripture": str(
                    plan.get(
                        "scripture",
                        ""
                    )
                ),
                "points": [
                    str(
                        item
                    ).strip()
                    for item in plan.get(
                        "points",
                        []
                    )
                    if str(
                        item
                    ).strip()
                ][
                    :10
                ],
            },
            config,
        )

        sequence_names = [
            item.get(
                "display",
                ""
            )
            for item in sequence
        ]

        chapter_ok = (
            bool(
                sequence
            )
            and
            any(
                str(
                    item.get(
                        "role",
                        ""
                    )
                ).startswith(
                    "point"
                )
                for item in sequence
            )
        )

        tests.append(
            result(
                "Sermon chapter rotation",
                chapter_ok,
                (
                    " -> ".join(
                        sequence_names
                    )
                    if sequence_names
                    else
                    "no chapter sequence generated"
                ),
            )
        )

    except Exception as exc:
        tests.append(
            result(
                "Sermon chapter rotation",
                False,
                str(
                    exc
                ),
            )
        )

    for raw in config.get(
        "critical_folders",
        []
    ):
        folder_ok = writable_folder(
            raw
        )

        tests.append(
            result(
                f"Writable folder: {raw}",
                folder_ok,
                (
                    "writable"
                    if folder_ok
                    else
                    "missing or not writable"
                ),
            )
        )

    for tool in (
        "ffmpeg",
        "ffprobe",
        "nvidia-smi",
    ):
        found = shutil.which(
            tool
        )

        tests.append(
            result(
                tool,
                bool(
                    found
                ),
                found
                or
                "not found",
            )
        )

    host = config.get(
        "obs_host",
        "localhost"
    )

    port = int(
        config.get(
            "obs_port",
            4455
        )
    )

    try:
        with socket.create_connection(
            (
                host,
                port,
            ),
            timeout=3,
        ):
            obs_ok = True
    except Exception:
        obs_ok = False

    tests.append(
        result(
            "OBS WebSocket",
            obs_ok,
            (
                f"{host}:{port} reachable"
                if obs_ok
                else
                f"{host}:{port} not reachable"
            ),
        )
    )

    # Safe, read-only verification that the Additional Chapter Hotkeys
    # plugin has already written chapter_hotkeys into an OBS scene collection.
    appdata = os.environ.get(
        "APPDATA",
        ""
    )

    scene_folder = (
        Path(
            appdata
        )
        /
        "obs-studio"
        /
        "basic"
        /
        "scenes"
        if appdata
        else
        None
    )

    chapter_collection_found = False
    chapter_collection_detail = (
        "OBS scene collection folder unavailable"
    )

    if (
        scene_folder is not None
        and
        scene_folder.exists()
    ):
        for scene_file in scene_folder.glob(
            "*.json"
        ):
            try:
                scene_data = json.loads(
                    scene_file.read_text(
                        encoding="utf-8-sig"
                    )
                )
            except Exception:
                continue

            chapter_hotkeys = scene_data.get(
                "chapter_hotkeys"
            )

            if isinstance(
                chapter_hotkeys,
                dict
            ):
                chapter_collection_found = True

                chapter_collection_detail = (
                    f"{scene_file.name} | "
                    f"{len(chapter_hotkeys)} named chapter hotkey(s)"
                )

                break

        if not chapter_collection_found:
            chapter_collection_detail = (
                "No scene collection currently contains chapter_hotkeys. "
                "Load Additional Chapter Hotkeys in OBS once."
            )

    tests.append(
        result(
            "Additional Chapter Hotkeys scene data",
            chapter_collection_found,
            chapter_collection_detail,
        )
    )

    lower_thirds_folder = Path(
        r"C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds"
    )

    lower_thirds_lua = (
        lower_thirds_folder
        /
        "lower-thirds_hotkeys.lua"
    )

    tests.append(
        result(
            "Animated Lower Thirds hotkey script",
            lower_thirds_lua.exists(),
            str(
                lower_thirds_lua
            ),
        )
    )

    planning_profile = Path(
        config.get(
            "planning_profile_folder",
            str(
                BASE
                /
                "WorshipTools_Planning_Profile"
            )
        )
    )

    tests.append(
        result(
            "WorshipTools Planning profile",
            planning_profile.exists(),
            str(
                planning_profile
            ),
        )
    )

    ptz_settings = load_ptz_settings(
        config
    )

    ptz_ip = str(
        ptz_settings.get(
            "ptz_camera_ip",
            ""
        )
    ).strip()

    tests.append(
        result(
            "PTZ camera configuration",
            bool(
                ptz_ip
            ),
            (
                (
                    f"{ptz_ip} | "
                    f"Worship preset {ptz_settings.get('ptz_worship_preset', 1)} | "
                    f"Pastor preset {ptz_settings.get('ptz_pastor_preset', 2)} | "
                    f"persistent={'YES' if PTZ_CONFIG_FILE.exists() else 'migration pending'}"
                )
                if ptz_ip
                else
                "not configured — enter the camera address in SSS Admin"
            ),
        )
    )

    youtube_profile = Path(
        config.get(
            "youtube_studio_profile_folder",
            str(
                BASE
                /
                "YouTube_Studio_Profile"
            )
        )
    )

    tests.append(
        result(
            "YouTube Studio profile",
            youtube_profile.exists(),
            str(
                youtube_profile
            ),
        )
    )

    production_scripts = [
        "sunday_mode.py",
        "chapter_bridge.py",
        "gmail_sermon_importer.py",
        "planning_update_sermon.py",
        "youtube_studio_upload_worker.py",
        "post_service_supervisor.py",
        "audio_sanity_monitor.py",
        "sermon_chapter_manager.py",
        "sync_named_chapter_hotkeys.py",
        "ptz_settings.py",
    ]

    for name in production_scripts:
        path = (
            BASE
            /
            name
        )

        if not path.exists():
            tests.append(
                result(
                    f"Syntax: {name}",
                    False,
                    "missing"
                )
            )

            continue

        try:
            compile(
                path.read_text(
                    encoding="utf-8"
                ),
                str(
                    path
                ),
                "exec"
            )

            tests.append(
                result(
                    f"Syntax: {name}",
                    True,
                    "OK"
                )
            )

        except Exception as exc:
            tests.append(
                result(
                    f"Syntax: {name}",
                    False,
                    str(
                        exc
                    ),
                )
            )

    passed = sum(
        1
        for item in tests
        if item[
            "ok"
        ]
    )

    total = len(
        tests
    )

    payload = {
        "generated": datetime.now().isoformat(
            timespec="seconds"
        ),
        "mode": (
            "SAFE TEST — no recording, stream, chapter firing, "
            "Planning write, camera movement, or YouTube upload"
        ),
        "passed": passed,
        "total": total,
        "tests": tests,
    }

    atomic_json(
        TEST_STATUS_FILE,
        payload
    )

    report = (
        BASE
        /
        "SSS_Test_Report.txt"
    )

    lines = [
        "SUNDAY SERVICE SYSTEM v22 — SAFE TEST MODE",
        "=" * 72,
        "",
        "This test does NOT start recording, streaming, fire a chapter,",
        "move the PTZ camera, upload a video, or change WorshipTools Planning.",
        "",
        f"Passed: {passed}/{total}",
        "",
    ]

    for item in tests:
        lines.append(
            (
                "PASS"
                if item[
                    "ok"
                ]
                else
                "FAIL"
            )
            +
            " — "
            +
            item[
                "name"
            ]
            +
            " — "
            +
            str(
                item[
                    "detail"
                ]
            )
        )

    report.write_text(
        "\n".join(
            lines
        )
        +
        "\n",
        encoding="utf-8"
    )

    print(
        "\n".join(
            lines
        )
    )

    print()
    print(
        f"Report: {report}"
    )
    print()

    return (
        0
        if passed
        ==
        total
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
