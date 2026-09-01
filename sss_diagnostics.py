import datetime
import json
import os
import shutil
import socket
import subprocess
import zipfile
from pathlib import Path

from sunday_common import load_config

from sss_event_history import record_event


from sss_audio_adapters import (
    discover_obs_audio_inputs,
    profile_audio_ready,
)
from sss_camera_adapters import (
    check_tcp_connection,
    profile_camera_ready,
)
from sss_obs_profile import (
    connect_local_obs,
    discover_obs,
)
from sss_presentation_adapters import (
    profile_adapter_ready,
)
from sss_profile import (
    active_profile_path,
    PROFILE_SCHEMA_VERSION,
    get_profile_audio_settings,
    get_profile_camera_settings,
    get_profile_obs_settings,
    get_profile_presentation_settings,
    get_profile_sermon_source_settings,
    get_profile_setup_status,
    load_active_profile,
)
from sss_sermon_sources import (
    normalize_sermon_plan,
    profile_sermon_source_ready,
    read_canonical_sermon_plan,
    upcoming_sunday_iso,
)

from sss_secrets_vault import (
    security_overview,
)

from sss_runtime import (
    runtime_info,
    updater_executable_candidates,
)

from sss_updater_core import (
    update_status,
)

from sss_release_trust import (
    SIGNED_UPDATES_REQUIRED,
    TRUSTED_UPDATE_SIGNER_THUMBPRINTS,
)
from sss_signing import (
    verify_authenticode_file,
)

from sss_update_feed import (
    load_feed_config,
    validate_https_url,
)







BASE = Path(r"C:\Church\SermonAI")
CHAPTER_SYNC_STATUS = BASE / "chapter_hotkey_sync_status.json"
CHAPTER_ROTATION_STATE = BASE / "chapter_rotation_state.json"
PTZ_LEGACY_CONFIG = BASE / "ptz_camera_config.json"
SERMON_PLAN_FILE = BASE / "sermon_plan.json"

LEVEL_ORDER = {
    "READY": 0,
    "INFO": 0,
    "CHECK": 1,
    "FIX": 2,
}


def _now_iso():
    return datetime.datetime.now().astimezone().isoformat()


def _result(name, level, detail, category="SYSTEM"):
    level = str(level or "CHECK").upper()

    if level not in LEVEL_ORDER:
        level = "CHECK"

    return {
        "name": str(name),
        "category": str(category),
        "level": level,
        "detail": " ".join(
            str(detail or "").split()
        ),
    }


def _safe_json(path, default=None):
    if default is None:
        default = {}

    try:
        payload = json.loads(
            Path(path).read_text(
                encoding="utf-8"
            )
        )

        return payload

    except Exception:
        return default


def _clean_name(value):
    return " ".join(
        str(value or "").split()
    )


def _extract_obs_inputs(client):
    response = client.get_input_list()
    raw_inputs = getattr(
        response,
        "inputs",
        []
    ) or []

    names = []

    for item in raw_inputs:
        name = ""

        if isinstance(item, dict):
            name = (
                item.get("inputName")
                or
                item.get("input_name")
                or
                item.get("name")
                or
                ""
            )
        else:
            for key in (
                "input_name",
                "inputName",
                "name",
            ):
                try:
                    value = getattr(
                        item,
                        key
                    )

                    if value:
                        name = value
                        break

                except Exception:
                    pass

        name = _clean_name(name)

        if name and name not in names:
            names.append(name)

    return names


def _obs_output_status(client):
    try:
        response = client.get_output_list()

        # Not every obsws-python build exposes recording/streaming from this
        # call in a consistent shape. Prefer the dedicated calls below.
        _ = response
    except Exception:
        pass

    recording = False
    streaming = False

    try:
        response = client.get_record_status()
        recording = bool(
            getattr(
                response,
                "output_active",
                getattr(
                    response,
                    "outputActive",
                    False
                )
            )
        )
    except Exception:
        pass

    try:
        response = client.get_stream_status()
        streaming = bool(
            getattr(
                response,
                "output_active",
                getattr(
                    response,
                    "outputActive",
                    False
                )
            )
        )
    except Exception:
        pass

    return {
        "recording": recording,
        "streaming": streaming,
    }


def check_application_runtime():
    try:
        info = runtime_info()

        return _result(
            "Application Runtime",
            (
                "READY"
                if info.get(
                    "frozen"
                )
                else
                "INFO"
            ),
            (
                "SSS "
                +
                str(
                    info.get(
                        "version",
                        ""
                    )
                )
                +
                " — "
                +
                str(
                    info.get(
                        "mode",
                        ""
                    )
                )
            ),
            "SYSTEM",
        )

    except Exception as exc:
        return _result(
            "Application Runtime",
            "CHECK",
            str(
                exc
            ),
            "SYSTEM",
        )


def check_updater():
    try:
        info = runtime_info()

        if not info.get(
            "frozen"
        ):
            return _result(
                "Application Updater",
                "INFO",
                "Python compatibility mode — built-in install/rollback applies after the Windows EXE is installed",
                "SYSTEM",
            )

        candidates = updater_executable_candidates()

        updater = next(
            (
                path
                for path in candidates
                if path.exists()
            ),
            None,
        )

        if updater is None:
            return _result(
                "Application Updater",
                "FIX",
                "SundayServiceSystemUpdater.exe is missing from the installed application",
                "SYSTEM",
            )

        status = update_status(
            install_root=info.get(
                "install_root",
                ""
            )
        )

        state = status.get(
            "state",
            {}
        )

        last = str(
            state.get(
                "status",
                "NONE"
            )
            or
            "NONE"
        ).upper()

        if last == "ROLLBACK_FAILED":
            return _result(
                "Application Updater",
                "FIX",
                (
                    "Updater installed, but the last recorded update/rollback needs manual recovery: "
                    +
                    str(
                        state.get(
                            "detail",
                            ""
                        )
                    )
                ),
                "SYSTEM",
            )

        if last in {
            "ROLLED_BACK",
            "ROLLED_BACK_ROLLBACK",
            "FAILED",
        }:
            return _result(
                "Application Updater",
                "CHECK",
                (
                    "Updater ready; last operation: "
                    +
                    last
                    +
                    (
                        " — "
                        +
                        str(
                            state.get(
                                "detail",
                                ""
                            )
                        )
                        if state.get(
                            "detail"
                        )
                        else
                        ""
                    )
                ),
                "SYSTEM",
            )

        return _result(
            "Application Updater",
            "READY",
            (
                "Updater installed"
                +
                (
                    " — last update: "
                    +
                    last
                    if last != "NONE"
                    else
                    ""
                )
                +
                (
                    " — rollback backup available"
                    if status.get(
                        "rollback_available"
                    )
                    else
                    ""
                )
            ),
            "SYSTEM",
        )

    except Exception as exc:
        return _result(
            "Application Updater",
            "CHECK",
            str(
                exc
            ),
            "SYSTEM",
        )


def check_release_signatures():
    try:
        info = runtime_info()

        if not info.get(
            "frozen"
        ):
            return _result(
                "Release Signatures",
                "INFO",
                (
                    "Python compatibility mode — Authenticode applies to the "
                    "installed Windows EXE release."
                ),
                "SECURITY",
            )

        trusted = tuple(
            str(
                value
            )
            for value in TRUSTED_UPDATE_SIGNER_THUMBPRINTS
            if str(
                value
            )
        )

        if (
            SIGNED_UPDATES_REQUIRED
            and
            not trusted
        ):
            return _result(
                "Release Signatures",
                "FIX",
                (
                    "Signed updates are required, but this installed build has "
                    "no trusted release signer thumbprint compiled in."
                ),
                "SECURITY",
            )

        install_root = Path(
            str(
                info.get(
                    "install_root",
                    ""
                )
            )
        )

        executables = (
            install_root
            /
            "SundayServiceSystem"
            /
            "SundayServiceSystem.exe",

            install_root
            /
            "SundayServiceSystemSettings"
            /
            "SundayServiceSystemSettings.exe",

            install_root
            /
            "SundayServiceSystemUpdater"
            /
            "SundayServiceSystemUpdater.exe",
        )

        signers = []

        for executable in executables:
            if not executable.exists():
                return _result(
                    "Release Signatures",
                    "FIX",
                    (
                        "Installed application EXE is missing: "
                        +
                        str(
                            executable
                        )
                    ),
                    "SECURITY",
                )

            result = verify_authenticode_file(
                executable,
                trusted_thumbprints=trusted,
                require_valid=True,
            )

            signers.append(
                result.get(
                    "thumbprint",
                    ""
                )
            )

        return _result(
            "Release Signatures",
            "READY",
            (
                "Main, Settings, and Updater have valid Authenticode signatures "
                "from trusted SSS release signer(s): "
                +
                ", ".join(
                    sorted(
                        set(
                            signers
                        )
                    )
                )
            ),
            "SECURITY",
        )

    except Exception as exc:
        return _result(
            "Release Signatures",
            "FIX",
            str(
                exc
            ),
            "SECURITY",
        )


def check_online_update_feed():
    try:
        config = load_feed_config()

        if not config.get(
            "enabled"
        ):
            return _result(
                "Online Update Feed",
                "INFO",
                (
                    "Not configured — local signed .sssupdate packages remain "
                    "available from Settings -> Updates"
                ),
                "SECURITY",
            )

        feed_url = validate_https_url(
            config.get(
                "feed_url",
                ""
            ),
            label="Release feed URL",
        )

        trusted = [
            str(
                value
            )
            for value in TRUSTED_UPDATE_SIGNER_THUMBPRINTS
            if str(
                value
            )
        ]

        if not trusted:
            return _result(
                "Online Update Feed",
                "FIX",
                (
                    "HTTPS feed is configured, but no trusted release signer "
                    "thumbprint is compiled into this SSS build"
                ),
                "SECURITY",
            )

        return _result(
            "Online Update Feed",
            "READY",
            (
                "Configured "
                +
                str(
                    config.get(
                        "channel",
                        "stable"
                    )
                ).upper()
                +
                " HTTPS feed — "
                +
                feed_url
                +
                " — network download is NOT performed by Full System Diagnostics"
            ),
            "SECURITY",
        )

    except Exception as exc:
        return _result(
            "Online Update Feed",
            "CHECK",
            str(
                exc
            ),
            "SECURITY",
        )


def check_profile():
    try:
        profile = load_active_profile()
        status = get_profile_setup_status(
            profile
        )

        name = _clean_name(
            profile.get(
                "profile_name",
                "Church Profile"
            )
        )

        if status.get("ready"):
            return _result(
                "Church Profile",
                "READY",
                (
                    name
                    +
                    " — schema "
                    +
                    str(
                        profile.get(
                            "schema_version",
                            "?"
                        )
                    )
                    +
                    "/"
                    +
                    str(
                        PROFILE_SCHEMA_VERSION
                    )
                    +
                    " — "
                    +
                    str(status.get("completed", 0))
                    +
                    "/"
                    +
                    str(status.get("total", 0))
                    +
                    " setup areas complete"
                ),
                "PROFILE",
            )

        missing = status.get(
            "missing_steps",
            []
        )

        return _result(
            "Church Profile",
            "CHECK",
            (
                name
                +
                " — "
                +
                str(status.get("completed", 0))
                +
                "/"
                +
                str(status.get("total", 0))
                +
                " complete"
                +
                (
                    " — missing: "
                    +
                    ", ".join(missing)
                    if missing
                    else
                    ""
                )
            ),
            "PROFILE",
        )

    except Exception as exc:
        return _result(
            "Church Profile",
            "FIX",
            str(exc),
            "PROFILE",
        )


def check_obs():
    try:
        data = discover_obs()
        profile = load_active_profile()
        settings = get_profile_obs_settings(
            profile
        )

        current_collection = _clean_name(
            data.get(
                "current_collection",
                ""
            )
        )

        scenes = set(
            data.get(
                "scenes",
                []
            )
            or
            []
        )

        collections = set(
            data.get(
                "collections",
                []
            )
            or
            []
        )

        if settings.get("settings_source") == "profile":
            expected_collection = _clean_name(
                settings.get(
                    "scene_collection",
                    ""
                )
            )

            missing = []

            if (
                expected_collection
                and
                expected_collection not in collections
            ):
                missing.append(
                    "collection "
                    +
                    expected_collection
                )

            for label, key in (
                (
                    "normal",
                    "normal_scene",
                ),
                (
                    "Scripture",
                    "scripture_scene",
                ),
            ):
                scene = _clean_name(
                    settings.get(
                        key,
                        ""
                    )
                )

                if not scene:
                    missing.append(
                        label
                        +
                        " scene mapping"
                    )
                elif (
                    expected_collection
                    ==
                    current_collection
                    and
                    scene not in scenes
                ):
                    missing.append(
                        label
                        +
                        " scene "
                        +
                        scene
                    )

            if missing:
                return _result(
                    "OBS",
                    "FIX",
                    (
                        "Connected, but profile mapping needs attention: "
                        +
                        "; ".join(missing)
                    ),
                    "OBS",
                )

            if (
                expected_collection
                and
                current_collection
                and
                expected_collection
                !=
                current_collection
            ):
                return _result(
                    "OBS",
                    "CHECK",
                    (
                        "Connected — saved collection "
                        +
                        expected_collection
                        +
                        ", current collection "
                        +
                        current_collection
                        +
                        ". Scene membership was not changed by this test."
                    ),
                    "OBS",
                )

            return _result(
                "OBS",
                "READY",
                (
                    "Connected — PROFILE collection "
                    +
                    (
                        expected_collection
                        or
                        current_collection
                        or
                        "(unnamed)"
                    )
                ),
                "OBS",
            )

        return _result(
            "OBS",
            "READY",
            (
                "Connected — LEGACY mode — current collection "
                +
                (
                    current_collection
                    or
                    "(unknown)"
                )
            ),
            "OBS",
        )

    except Exception as exc:
        return _result(
            "OBS",
            "FIX",
            str(exc),
            "OBS",
        )


def check_outputs():
    try:
        client, _config, _host, _port = connect_local_obs(
            timeout=3
        )

        state = _obs_output_status(
            client
        )

        if state["recording"] or state["streaming"]:
            active = []

            if state["recording"]:
                active.append(
                    "Recording"
                )

            if state["streaming"]:
                active.append(
                    "Streaming"
                )

            return _result(
                "OBS Outputs",
                "INFO",
                (
                    ", ".join(active)
                    +
                    " currently active — diagnostics are read-only and did not change them"
                ),
                "OBS",
            )

        return _result(
            "OBS Outputs",
            "READY",
            "Recording and Streaming are currently stopped",
            "OBS",
        )

    except Exception as exc:
        return _result(
            "OBS Outputs",
            "CHECK",
            str(exc),
            "OBS",
        )


def _legacy_midi_ready(port_name):
    try:
        import mido

        outputs = list(
            mido.get_output_names()
        )

        exact = [
            name
            for name in outputs
            if _clean_name(name)
            ==
            _clean_name(port_name)
        ]

        if exact:
            return (
                True,
                port_name
                +
                " MIDI output ready"
            )

        contains = [
            name
            for name in outputs
            if _clean_name(port_name).lower()
            in
            _clean_name(name).lower()
        ]

        if contains:
            return (
                True,
                contains[0]
                +
                " MIDI output ready"
            )

        return (
            False,
            (
                "MIDI output "
                +
                port_name
                +
                " not found"
            ),
        )

    except Exception as exc:
        return (
            False,
            (
                "Could not inspect MIDI outputs: "
                +
                str(exc)
            ),
        )


def check_presentation():
    try:
        settings = get_profile_presentation_settings(
            load_active_profile()
        )

        provider = settings.get(
            "provider",
            "WorshipTools Presenter"
        )

        if settings.get("settings_source") == "profile":
            ready, detail = profile_adapter_ready()

            return _result(
                "Presentation",
                (
                    "READY"
                    if ready
                    else
                    "FIX"
                ),
                (
                    provider
                    +
                    " — "
                    +
                    str(detail)
                ),
                "PRESENTATION",
            )

        if provider == "WorshipTools Presenter":
            ready, detail = _legacy_midi_ready(
                "Presenter"
            )

            return _result(
                "Presentation",
                (
                    "READY"
                    if ready
                    else
                    "FIX"
                ),
                (
                    "LEGACY WorshipTools Presenter — "
                    +
                    detail
                ),
                "PRESENTATION",
            )

        return _result(
            "Presentation",
            "CHECK",
            (
                "LEGACY "
                +
                provider
                +
                " — deep provider test is not available in the standalone diagnostic"
            ),
            "PRESENTATION",
        )

    except Exception as exc:
        return _result(
            "Presentation",
            "FIX",
            str(exc),
            "PRESENTATION",
        )


def check_camera():
    try:
        settings = get_profile_camera_settings(
            load_active_profile()
        )

        provider = settings.get(
            "provider",
            "PTZOptics / HTTP-CGI"
        )

        if settings.get("settings_source") == "profile":
            ready, detail = profile_camera_ready()

            return _result(
                "Camera",
                (
                    "READY"
                    if ready
                    else
                    "FIX"
                ),
                (
                    provider
                    +
                    " — "
                    +
                    str(detail)
                    +
                    " — no movement command sent"
                ),
                "CAMERA",
            )

        legacy = _safe_json(
            PTZ_LEGACY_CONFIG,
            {}
        )

        enabled = bool(
            legacy.get(
                "ptz_camera_enabled",
                legacy.get(
                    "enabled",
                    True
                )
            )
        )

        if not enabled:
            return _result(
                "Camera",
                "READY",
                "LEGACY camera control disabled",
                "CAMERA",
            )

        host = _clean_name(
            legacy.get(
                "ptz_camera_ip",
                legacy.get(
                    "camera_ip",
                    legacy.get(
                        "ip",
                        legacy.get(
                            "host",
                            ""
                        )
                    )
                )
            )
        )

        if not host:
            return _result(
                "Camera",
                "CHECK",
                "LEGACY camera selected, but camera IP is not available in the local PTZ settings",
                "CAMERA",
            )

        port = int(
            legacy.get(
                "ptz_camera_port",
                legacy.get(
                    "port",
                    80
                )
            )
            or
            80
        )

        try:
            check_tcp_connection(
                host,
                port,
                timeout=1.5,
            )

            return _result(
                "Camera",
                "READY",
                (
                    "LEGACY PTZ camera reachable at "
                    +
                    host
                    +
                    ":"
                    +
                    str(port)
                    +
                    " — no movement command sent"
                ),
                "CAMERA",
            )

        except Exception as exc:
            return _result(
                "Camera",
                "FIX",
                str(exc),
                "CAMERA",
            )

    except Exception as exc:
        return _result(
            "Camera",
            "FIX",
            str(exc),
            "CAMERA",
        )


def _windows_audio_endpoint_ready(config):
    target = _clean_name(
        config.get(
            "audio_loopback_name",
            ""
        )
    )

    if target.lower().endswith(
        "[loopback]"
    ):
        target = target[
            :-len(
                "[Loopback]"
            )
        ].strip()

    label = _clean_name(
        config.get(
            "audio_loopback_label",
            "Audio Interface"
        )
    )

    if not target:
        return (
            False,
            label
            +
            " endpoint not configured"
        )

    if os.name != "nt":
        return (
            True,
            label
            +
            " endpoint check skipped on non-Windows system"
        )

    ps = (
        "$ErrorActionPreference='SilentlyContinue'; "
        "$names=@(); "
        "try { $names += Get-PnpDevice -Class AudioEndpoint | "
        "Where-Object { $_.Status -eq 'OK' } | "
        "ForEach-Object { $_.FriendlyName } } catch {}; "
        "try { $names += Get-CimInstance Win32_SoundDevice | "
        "Where-Object { $_.Status -eq 'OK' } | "
        "ForEach-Object { $_.Name } } catch {}; "
        "$names | Sort-Object -Unique"
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

        names = [
            line.strip()
            for line in (
                cp.stdout
                or
                ""
            ).splitlines()
            if line.strip()
        ]

        target_lower = target.lower()

        found = any(
            (
                name.lower()
                ==
                target_lower
            )
            or
            (
                target_lower
                in
                name.lower()
            )
            or
            (
                name.lower()
                in
                target_lower
            )
            for name in names
        )

        if found:
            return (
                True,
                label
                +
                " endpoint ready"
            )

        return (
            False,
            label
            +
            " endpoint missing"
        )

    except Exception as exc:
        return (
            False,
            label
            +
            " endpoint check failed: "
            +
            str(exc)
        )


def check_audio():
    try:
        profile = load_active_profile()
        settings = get_profile_audio_settings(
            profile
        )
        config = load_config()

        if settings.get("settings_source") == "profile":
            ready, detail = profile_audio_ready()

            if not ready:
                return _result(
                    "Audio",
                    "FIX",
                    str(detail),
                    "AUDIO",
                )

            endpoint_ok, endpoint_detail = _windows_audio_endpoint_ready(
                config
            )

            return _result(
                "Audio",
                (
                    "READY"
                    if endpoint_ok
                    else
                    "CHECK"
                ),
                (
                    str(detail)
                    +
                    " | "
                    +
                    endpoint_detail
                ),
                "AUDIO",
            )

        client, _config, _host, _port = connect_local_obs(
            timeout=3
        )

        available = set(
            _extract_obs_inputs(
                client
            )
        )

        expected = [
            _clean_name(name)
            for name in config.get(
                "emergency_mute_inputs",
                [
                    "main",
                    "room mics",
                ]
            )
            if _clean_name(name)
        ]

        missing = [
            name
            for name in expected
            if name not in available
        ]

        endpoint_ok, endpoint_detail = _windows_audio_endpoint_ready(
            config
        )

        if missing:
            return _result(
                "Audio",
                "FIX",
                (
                    "LEGACY OBS mute input(s) missing: "
                    +
                    ", ".join(missing)
                    +
                    " | "
                    +
                    endpoint_detail
                ),
                "AUDIO",
            )

        return _result(
            "Audio",
            (
                "READY"
                if endpoint_ok
                else
                "CHECK"
            ),
            (
                "LEGACY mute targets ready: "
                +
                ", ".join(expected)
                +
                " | "
                +
                endpoint_detail
            ),
            "AUDIO",
        )

    except Exception as exc:
        return _result(
            "Audio",
            "FIX",
            str(exc),
            "AUDIO",
        )


def check_sermon():
    try:
        settings = get_profile_sermon_source_settings(
            load_active_profile()
        )

        if settings.get("settings_source") == "profile":
            ready, detail = profile_sermon_source_ready()

            if not ready:
                return _result(
                    "Sermon Source",
                    "FIX",
                    str(detail),
                    "SERMON",
                )

        plan = read_canonical_sermon_plan()

        if not plan:
            return _result(
                "Sermon Source",
                "FIX",
                "No sermon_plan.json is loaded",
                "SERMON",
            )

        normalized = normalize_sermon_plan(
            plan,
            source_provider=plan.get(
                "source_provider",
                "Runtime"
            ),
        )

        expected_date = upcoming_sunday_iso()
        service_date = _clean_name(
            normalized.get(
                "service_date",
                ""
            )
        )

        provider = (
            settings.get(
                "provider",
                "Legacy"
            )
            if settings.get(
                "settings_source"
            )
            ==
            "profile"
            else
            "LEGACY"
        )

        if service_date != expected_date:
            return _result(
                "Sermon Source",
                "FIX",
                (
                    provider
                    +
                    " — loaded sermon date "
                    +
                    service_date
                    +
                    ", upcoming Sunday "
                    +
                    expected_date
                ),
                "SERMON",
            )

        return _result(
            "Sermon Source",
            "READY",
            (
                provider
                +
                " — "
                +
                normalized.get(
                    "title",
                    ""
                )
                +
                " | "
                +
                normalized.get(
                    "scripture",
                    ""
                )
                +
                " | "
                +
                str(
                    len(
                        normalized.get(
                            "points",
                            []
                        )
                    )
                )
                +
                " point(s)"
            ),
            "SERMON",
        )

    except Exception as exc:
        return _result(
            "Sermon Source",
            "FIX",
            str(exc),
            "SERMON",
        )


def check_chapters():
    try:
        plan = read_canonical_sermon_plan()

        if not plan:
            return _result(
                "Sermon Chapters",
                "FIX",
                "No active sermon plan",
                "SERMON",
            )

        sync = _safe_json(
            CHAPTER_SYNC_STATUS,
            {}
        )

        state = _clean_name(
            sync.get(
                "state",
                ""
            )
        ).upper()

        plan_id = _clean_name(
            plan.get(
                "plan_id",
                ""
            )
        )

        sync_plan_id = _clean_name(
            sync.get(
                "plan_id",
                ""
            )
        )

        if (
            plan_id
            and
            sync_plan_id
            and
            plan_id
            !=
            sync_plan_id
        ):
            return _result(
                "Sermon Chapters",
                "CHECK",
                "Named chapter hotkey status belongs to a different sermon plan",
                "SERMON",
            )

        if state == "ERROR":
            return _result(
                "Sermon Chapters",
                "FIX",
                (
                    sync.get(
                        "message",
                        "Named chapter hotkey sync error"
                    )
                ),
                "SERMON",
            )

        if state == "DEFERRED_OBS_RUNNING":
            return _result(
                "Sermon Chapters",
                "CHECK",
                "Chapter labels are waiting for an OBS restart",
                "SERMON",
            )

        if state == "SYNCED":
            return _result(
                "Sermon Chapters",
                "READY",
                "Named chapter hotkeys synced for the active sermon",
                "SERMON",
            )

        if CHAPTER_ROTATION_STATE.exists():
            return _result(
                "Sermon Chapters",
                "CHECK",
                "Chapter rotation state exists, but named-hotkey sync status is not confirmed",
                "SERMON",
            )

        return _result(
            "Sermon Chapters",
            "CHECK",
            "Chapter state has not been prepared yet",
            "SERMON",
        )

    except Exception as exc:
        return _result(
            "Sermon Chapters",
            "CHECK",
            str(exc),
            "SERMON",
        )


def check_security():
    try:
        overview = security_overview()

        if not overview.get(
            "vault_available"
        ):
            return _result(
                "Secrets Vault",
                "CHECK",
                "Windows Credential Manager is unavailable; legacy local credential storage remains in use",
                "SECURITY",
            )

        vaulted = bool(
            overview.get(
                "obs_vault_stored"
            )
        )

        loose = bool(
            overview.get(
                "legacy_obs_password_present"
            )
        )

        if vaulted and not loose:
            return _result(
                "Secrets Vault",
                "READY",
                "OBS WebSocket password is protected in Windows Credential Manager; no known loose OBS password entry detected",
                "SECURITY",
            )

        if vaulted and loose:
            return _result(
                "Secrets Vault",
                "CHECK",
                "Protected OBS credential is ready, but a legacy loose OBS_PASSWORD entry still exists",
                "SECURITY",
            )

        if loose:
            return _result(
                "Secrets Vault",
                "CHECK",
                "OBS WebSocket password still uses legacy loose configuration; migrate it from Settings -> Security",
                "SECURITY",
            )

        return _result(
            "Secrets Vault",
            "READY",
            "No OBS password is stored in the SSS vault or known loose config; OBS authentication may be disabled",
            "SECURITY",
        )

    except Exception as exc:
        return _result(
            "Secrets Vault",
            "CHECK",
            str(
                exc
            ),
            "SECURITY",
        )


def check_storage():
    try:
        config = load_config()
        folder = Path(
            config.get(
                "recording_folder",
                r"D:\2026"
            )
        )

        if not folder.exists():
            return _result(
                "Recording Storage",
                "FIX",
                (
                    "Recording folder missing: "
                    +
                    str(folder)
                ),
                "STORAGE",
            )

        usage = shutil.disk_usage(
            folder
        )

        free_gb = (
            usage.free
            /
            (
                1024
                **
                3
            )
        )

        minimum = float(
            config.get(
                "minimum_free_gb",
                100
            )
        )

        critical = float(
            config.get(
                "critical_free_gb",
                25
            )
        )

        if free_gb < critical:
            level = "FIX"
        elif free_gb < minimum:
            level = "CHECK"
        else:
            level = "READY"

        return _result(
            "Recording Storage",
            level,
            (
                str(folder)
                +
                " — "
                +
                f"{free_gb:.0f} GB free"
            ),
            "STORAGE",
        )

    except Exception as exc:
        return _result(
            "Recording Storage",
            "FIX",
            str(exc),
            "STORAGE",
        )


def check_folders():
    try:
        config = load_config()

        raw_folders = list(
            config.get(
                "critical_folders",
                []
            )
            or
            []
        )

        if not raw_folders:
            return _result(
                "Critical Folders",
                "CHECK",
                "No critical folders configured",
                "STORAGE",
            )

        missing = []
        not_writable = []

        for raw in raw_folders:
            path = Path(raw)

            if not path.exists():
                missing.append(
                    str(path)
                )
                continue

            if not os.access(
                path,
                os.W_OK
            ):
                not_writable.append(
                    str(path)
                )

        if missing or not_writable:
            details = []

            if missing:
                details.append(
                    "missing: "
                    +
                    ", ".join(missing)
                )

            if not_writable:
                details.append(
                    "not writable: "
                    +
                    ", ".join(not_writable)
                )

            return _result(
                "Critical Folders",
                "FIX",
                " | ".join(details),
                "STORAGE",
            )

        return _result(
            "Critical Folders",
            "READY",
            (
                str(len(raw_folders))
                +
                " configured folder(s) present"
            ),
            "STORAGE",
        )

    except Exception as exc:
        return _result(
            "Critical Folders",
            "FIX",
            str(exc),
            "STORAGE",
        )


def check_tools():
    names = [
        "ffmpeg",
        "ffprobe",
        "nvidia-smi",
    ]

    missing = [
        name
        for name in names
        if not shutil.which(name)
    ]

    if missing:
        return _result(
            "Media / GPU Tools",
            "FIX",
            (
                "Missing: "
                +
                ", ".join(missing)
            ),
            "TOOLS",
        )

    return _result(
        "Media / GPU Tools",
        "READY",
        "FFmpeg, FFprobe, and NVIDIA tools found",
        "TOOLS",
    )


def check_internet():
    try:
        config = load_config()

        host = _clean_name(
            config.get(
                "internet_test_host",
                "8.8.8.8"
            )
        )

        port = int(
            config.get(
                "internet_test_port",
                53
            )
            or
            53
        )

        timeout = float(
            config.get(
                "internet_test_timeout",
                2.0
            )
            or
            2.0
        )

        with socket.create_connection(
            (
                host,
                port,
            ),
            timeout=timeout,
        ):
            pass

        return _result(
            "Network",
            "READY",
            (
                "Reachable: "
                +
                host
                +
                ":"
                +
                str(port)
            ),
            "NETWORK",
        )

    except Exception as exc:
        return _result(
            "Network",
            "CHECK",
            (
                "Internet/network check failed: "
                +
                str(exc)
                +
                " — local recording/control can still work"
            ),
            "NETWORK",
        )


def check_lower_thirds():
    candidates = [
        BASE
        /
        "sync_sermon_plan_to_lower_thirds.py",
        Path(
            os.environ.get(
                "USERPROFILE",
                ""
            )
        )
        /
        "Documents"
        /
        "Animated-Lower-Thirds"
        /
        "lower thirds"
        /
        "control-panel.html",
    ]

    missing = [
        str(path)
        for path in candidates
        if not path.exists()
    ]

    if missing:
        return _result(
            "Lower Thirds",
            "CHECK",
            (
                "Missing expected component(s): "
                +
                ", ".join(missing)
            ),
            "TOOLS",
        )

    return _result(
        "Lower Thirds",
        "READY",
        "Lower-third sync script and control panel found",
        "TOOLS",
    )


def _sanitize(value):
    sensitive_words = (
        "password",
        "passwd",
        "secret",
        "token",
        "oauth",
        "authorization",
        "credential",
        "api_key",
        "apikey",
    )

    if isinstance(value, dict):
        cleaned = {}

        for key, item in value.items():
            key_text = str(key)

            if any(
                word
                in
                key_text.lower()
                for word in sensitive_words
            ):
                cleaned[key_text] = "<redacted>"
            else:
                cleaned[key_text] = _sanitize(
                    item
                )

        return cleaned

    if isinstance(value, list):
        return [
            _sanitize(item)
            for item in value
        ]

    return value


def summarize_results(results):
    worst = 0

    for item in results:
        worst = max(
            worst,
            LEVEL_ORDER.get(
                item.get(
                    "level",
                    "CHECK"
                ),
                1,
            ),
        )

    if worst >= 2:
        overall = "FIX"
    elif worst == 1:
        overall = "CHECK"
    else:
        overall = "READY"

    counts = {
        "READY": 0,
        "CHECK": 0,
        "FIX": 0,
        "INFO": 0,
    }

    for item in results:
        level = item.get(
            "level",
            "CHECK"
        )

        counts[
            level
        ] = counts.get(
            level,
            0
        ) + 1

    return {
        "overall": overall,
        "counts": counts,
    }


def run_full_system_test():
    checks = [
        check_application_runtime,
        check_updater,
        check_release_signatures,
        check_online_update_feed,
        check_profile,
        check_obs,
        check_outputs,
        check_presentation,
        check_camera,
        check_audio,
        check_sermon,
        check_chapters,
        check_security,
        check_storage,
        check_folders,
        check_tools,
        check_lower_thirds,
        check_internet,
    ]

    results = []

    for check in checks:
        try:
            results.append(
                check()
            )
        except Exception as exc:
            results.append(
                _result(
                    getattr(
                        check,
                        "__name__",
                        "Diagnostic"
                    ),
                    "FIX",
                    str(exc),
                )
            )

    summary = summarize_results(
        results
    )

    profile = {}

    try:
        profile = load_active_profile()
    except Exception:
        pass

    report = {
        "generated_at": _now_iso(),
        "overall": summary["overall"],
        "counts": summary["counts"],
        "profile_name": _clean_name(
            profile.get(
                "profile_name",
                ""
            )
        ),
        "active_profile_path": str(
            active_profile_path()
        ),
        "read_only": True,
        "results": results,
    }

    try:
        record_event(
            (
                "Full System Diagnostics completed: "
                +
                str(
                    report.get(
                        "overall",
                        "CHECK"
                    )
                )
                +
                " — "
                +
                str(
                    report.get(
                        "counts",
                        {}
                    ).get(
                        "READY",
                        0
                    )
                )
                +
                " READY / "
                +
                str(
                    report.get(
                        "counts",
                        {}
                    ).get(
                        "CHECK",
                        0
                    )
                )
                +
                " CHECK / "
                +
                str(
                    report.get(
                        "counts",
                        {}
                    ).get(
                        "FIX",
                        0
                    )
                )
                +
                " FIX."
            ),
            category="SYSTEM",
            level=(
                "INFO"
                if report.get(
                    "overall"
                )
                ==
                "READY"
                else
                "WARNING"
            ),
            source="DIAGNOSTICS",
        )
    except Exception:
        pass

    return report


def report_text(report):
    lines = []

    lines.append(
        "SUNDAY SERVICE SYSTEM — FULL SYSTEM TEST"
    )
    lines.append(
        "="
        *
        44
    )
    lines.append(
        "Generated: "
        +
        str(
            report.get(
                "generated_at",
                ""
            )
        )
    )
    lines.append(
        "Profile: "
        +
        str(
            report.get(
                "profile_name",
                ""
            )
        )
    )
    lines.append(
        "Overall: "
        +
        str(
            report.get(
                "overall",
                "CHECK"
            )
        )
    )
    lines.append(
        "Mode: READ-ONLY — no recording, streaming, camera movement, "
        "presentation movement, or audio mute changes"
    )
    lines.append(
        ""
    )

    for item in report.get(
        "results",
        []
    ):
        lines.append(
            "["
            +
            str(
                item.get(
                    "level",
                    "CHECK"
                )
            )
            +
            "] "
            +
            str(
                item.get(
                    "name",
                    "Diagnostic"
                )
            )
        )
        lines.append(
            "    "
            +
            str(
                item.get(
                    "detail",
                    ""
                )
            )
        )

    lines.append(
        ""
    )

    return "\n".join(
        lines
    )


def export_diagnostic_bundle(
    report=None,
    destination_dir=None
):
    if report is None:
        report = run_full_system_test()

    if destination_dir is None:
        destination_dir = (
            BASE
            /
            "Diagnostics"
        )

    destination_dir = Path(
        destination_dir
    )

    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = datetime.datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    bundle = (
        destination_dir
        /
        (
            "SSS-Diagnostic_"
            +
            stamp
            +
            ".zip"
        )
    )

    config = {}

    try:
        config = load_config()
    except Exception:
        pass

    profile = {}

    try:
        profile = load_active_profile()
    except Exception:
        pass

    report_json = json.dumps(
        _sanitize(
            report
        ),
        indent=2,
        ensure_ascii=False,
    )

    profile_json = json.dumps(
        _sanitize(
            profile
        ),
        indent=2,
        ensure_ascii=False,
    )

    config_json = json.dumps(
        _sanitize(
            config
        ),
        indent=2,
        ensure_ascii=False,
    )

    with zipfile.ZipFile(
        bundle,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "diagnostic_report.txt",
            report_text(
                report
            ),
        )

        archive.writestr(
            "diagnostic_report.json",
            report_json,
        )

        archive.writestr(
            "active_profile_sanitized.json",
            profile_json,
        )

        archive.writestr(
            "sunday_config_sanitized.json",
            config_json,
        )

        archive.writestr(
            "README.txt",
            (
                "This SSS diagnostic bundle was generated automatically.\n"
                "Password/token/secret-like keys were redacted.\n"
                "The full system test is read-only and does not start/stop "
                "recording or streaming, move cameras/slides, or change audio mute state.\n"
            ),
        )

    return bundle
