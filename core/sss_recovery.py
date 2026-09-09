import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from sss_obs_profile import connect_local_obs

from sss_event_history import record_event

from sss_profile import (
    load_active_profile,
    profile_root,
)


BASE = Path(r"C:\Church\SermonAI")
RECOVERY_ROOT = BASE / "Recovery"
SNAPSHOT_DIR = RECOVERY_ROOT / "Snapshots"
LAST_KNOWN_GOOD_POINTER = RECOVERY_ROOT / "last_known_good.json"

SNAPSHOT_SCHEMA_VERSION = 1

SECRET_NAME_PARTS = (
    ".env",
    "credential",
    "credentials",
    "gmail_token",
    "oauth",
    "password",
    "passwd",
    "secret",
    "token.json",
)

SAFE_CONFIG_JSON_NAMES = {
    "sunday_config.json",
    "ptz_camera_config.json",
}

TRANSIENT_EXACT_NAMES = {
    "sermon_plan.json",
    "chapter_rotation_state.json",
    "chapter_hotkey_sync_status.json",
    "ptz_camera_status.json",
    "audio_sanity_status.json",
    "youtube_upload_status.json",
    "youtube_upload_state.json",
}

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    "CUDA",
    "Diagnostics",
    "Recovery",
    "logs",
    "venv",
}


def _now():
    return datetime.datetime.now().astimezone()


def _now_iso():
    return _now().isoformat()


def _safe_slug(value):
    text = "".join(
        char
        if (
            char.isalnum()
            or
            char in {
                "-",
                "_",
            }
        )
        else
        "_"
        for char in str(
            value
            or
            "snapshot"
        )
    )

    while "__" in text:
        text = text.replace(
            "__",
            "_"
        )

    return (
        text.strip(
            "_"
        )
        or
        "snapshot"
    )


def _sha256(path):
    digest = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as handle:
        while True:
            block = handle.read(
                1024
                *
                1024
            )

            if not block:
                break

            digest.update(
                block
            )

    return digest.hexdigest()


def _is_secret_name(path):
    name = Path(
        path
    ).name.lower()

    return any(
        part in name
        for part in SECRET_NAME_PARTS
    )


def _is_transient_name(path):
    return (
        Path(
            path
        ).name.lower()
        in {
            item.lower()
            for item in TRANSIENT_EXACT_NAMES
        }
    )


def _include_app_file(path):
    path = Path(
        path
    )

    if not path.is_file():
        return False

    if _is_secret_name(
        path
    ):
        return False

    if _is_transient_name(
        path
    ):
        return False

    suffix = path.suffix.lower()
    name = path.name.lower()

    if suffix == ".py":
        return True

    if suffix in {
        ".bat",
        ".cmd",
        ".vbs",
    }:
        return True

    if suffix == ".json":
        return (
            name
            in
            SAFE_CONFIG_JSON_NAMES
        )

    if name in {
        "requirements.txt",
        "requirements-lock.txt",
    }:
        return True

    return False


def _walk_app_files():
    if not BASE.exists():
        return []

    files = []

    for item in BASE.iterdir():
        if item.is_file():
            if _include_app_file(
                item
            ):
                files.append(
                    item
                )

            continue

        if (
            item.is_dir()
            and
            item.name
            in EXCLUDED_DIR_NAMES
        ):
            continue

        # Recovery deliberately does not recursively copy arbitrary application
        # folders. The top-level SSS scripts/configuration and profile store are
        # the stable rollback boundary. This avoids copying venvs, media, models,
        # logs, caches, and large generated content.

    return sorted(
        files,
        key=lambda path:
            path.name.lower(),
    )


def _walk_profile_files():
    root = profile_root()

    if not root.exists():
        return []

    files = []

    for path in root.rglob(
        "*"
    ):
        if not path.is_file():
            continue

        try:
            relative_parts = path.relative_to(
                root
            ).parts
        except Exception:
            relative_parts = path.parts

        if "Migration Backups" in relative_parts:
            continue

        if _is_secret_name(
            path
        ):
            continue

        files.append(
            path
        )

    return sorted(
        files,
        key=lambda path:
            str(
                path
            ).lower(),
    )


def ensure_recovery_dirs():
    SNAPSHOT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    return SNAPSHOT_DIR


def _obs_output_state():
    """
    Return recording/streaming state without changing OBS.
    """
    client, _config, _host, _port = connect_local_obs(
        timeout=2
    )

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


def _obs_process_running():
    if os.name != "nt":
        return False

    try:
        cp = subprocess.run(
            [
                "tasklist",
                "/FI",
                "IMAGENAME eq obs64.exe",
                "/NH",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            ),
        )

        text = (
            cp.stdout
            or
            ""
        ).lower()

        return (
            "obs64.exe"
            in text
        )

    except Exception:
        return False


def restore_safety_status():
    """
    Restoration is blocked while OBS is actively recording/streaming.

    If OBS is running but WebSocket status cannot be verified, restoration is
    also blocked. This is deliberately conservative for a live-service PC.
    """
    try:
        state = _obs_output_state()

        if (
            state.get(
                "recording"
            )
            or
            state.get(
                "streaming"
            )
        ):
            active = []

            if state.get(
                "recording"
            ):
                active.append(
                    "Recording"
                )

            if state.get(
                "streaming"
            ):
                active.append(
                    "Streaming"
                )

            return {
                "safe": False,
                "detail": (
                    "Restore blocked while "
                    +
                    " and ".join(
                        active
                    )
                    +
                    " is active."
                ),
            }

        return {
            "safe": True,
            "detail": (
                "OBS is reachable and Recording/Streaming are stopped."
            ),
        }

    except Exception as exc:
        if _obs_process_running():
            return {
                "safe": False,
                "detail": (
                    "OBS appears to be running, but SSS could not verify "
                    "Recording/Streaming state. Close OBS before restoring. "
                    +
                    str(
                        exc
                    )
                ),
            }

        return {
            "safe": True,
            "detail": (
                "OBS is not reachable and no obs64.exe process was detected."
            ),
        }


SENSITIVE_JSON_KEY_PARTS = (
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


def _is_sensitive_json_key(
    key
):
    key = str(
        key
    ).lower()

    return any(
        part in key
        for part in SENSITIVE_JSON_KEY_PARTS
    )


def _sanitize_json_object(
    value
):
    if isinstance(
        value,
        dict
    ):
        cleaned = {}

        for key, item in value.items():
            if _is_sensitive_json_key(
                key
            ):
                continue

            cleaned[
                key
            ] = _sanitize_json_object(
                item
            )

        return cleaned

    if isinstance(
        value,
        list
    ):
        return [
            _sanitize_json_object(
                item
            )
            for item in value
        ]

    return value


def _merge_preserving_sensitive(
    current,
    restored
):
    """
    Restore non-secret configuration while preserving any secret-like values
    already present on this PC.
    """
    if not isinstance(
        restored,
        dict
    ):
        return restored

    if not isinstance(
        current,
        dict
    ):
        current = {}

    merged = dict(
        current
    )

    for key, value in restored.items():
        if _is_sensitive_json_key(
            key
        ):
            continue

        if isinstance(
            value,
            dict
        ):
            merged[
                key
            ] = _merge_preserving_sensitive(
                current.get(
                    key,
                    {}
                ),
                value,
            )
        else:
            merged[
                key
            ] = value

    return merged


def _manifest_entry_bytes(
    *,
    archive_path,
    data,
    destination_group,
    destination_relative,
    restore_mode="replace"
):
    return {
        "archive_path": archive_path,
        "destination_group": destination_group,
        "destination_relative": str(
            destination_relative
        ).replace(
            "\\",
            "/"
        ),
        "size": len(
            data
        ),
        "sha256": hashlib.sha256(
            data
        ).hexdigest(),
        "restore_mode": restore_mode,
    }


def _manifest_entry(
    *,
    archive_path,
    source_path,
    destination_group,
    destination_relative
):
    source_path = Path(
        source_path
    )

    return {
        "archive_path": archive_path,
        "destination_group": destination_group,
        "destination_relative": str(
            destination_relative
        ).replace(
            "\\",
            "/"
        ),
        "size": source_path.stat().st_size,
        "sha256": _sha256(
            source_path
        ),
        "restore_mode": "replace",
    }


def create_recovery_snapshot(
    *,
    kind="manual",
    label="",
    diagnostic_report=None,
    require_ready=False
):
    ensure_recovery_dirs()

    kind_clean = _safe_slug(
        kind
    ).lower()

    if require_ready:
        if not isinstance(
            diagnostic_report,
            dict
        ):
            raise RuntimeError(
                (
                    "Run Full System Diagnostics first. "
                    "Last Known Good can only be saved from a READY diagnostic."
                )
            )

        if str(
            diagnostic_report.get(
                "overall",
                ""
            )
        ).upper() != "READY":
            raise RuntimeError(
                (
                    "Last Known Good requires an overall READY diagnostic result. "
                    "Current result: "
                    +
                    str(
                        diagnostic_report.get(
                            "overall",
                            "NOT RUN"
                        )
                    )
                )
            )

    profile = {}

    try:
        profile = load_active_profile()
    except Exception:
        pass

    profile_name = str(
        profile.get(
            "profile_name",
            "Church Profile"
        )
    )

    stamp = _now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    label_clean = _safe_slug(
        label
    ) if label else ""

    filename = (
        "SSS-Recovery_"
        +
        stamp
        +
        "_"
        +
        kind_clean
    )

    if label_clean:
        filename += (
            "_"
            +
            label_clean
        )

    snapshot_path = (
        SNAPSHOT_DIR
        /
        (
            filename
            +
            ".zip"
        )
    )

    app_files = _walk_app_files()
    profile_files = _walk_profile_files()
    entries = []

    temp_snapshot = snapshot_path.with_suffix(
        ".zip.tmp"
    )

    if temp_snapshot.exists():
        temp_snapshot.unlink()

    with zipfile.ZipFile(
        temp_snapshot,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        for source in app_files:
            archive_path = (
                "app/"
                +
                source.name
            )

            if source.name.lower() == "sunday_config.json":
                try:
                    payload = json.loads(
                        source.read_text(
                            encoding="utf-8"
                        )
                    )

                    sanitized = _sanitize_json_object(
                        payload
                    )

                    data = (
                        json.dumps(
                            sanitized,
                            indent=2,
                            ensure_ascii=False,
                        )
                        +
                        "\n"
                    ).encode(
                        "utf-8"
                    )

                    archive.writestr(
                        archive_path,
                        data,
                    )

                    entries.append(
                        _manifest_entry_bytes(
                            archive_path=archive_path,
                            data=data,
                            destination_group="app",
                            destination_relative=source.name,
                            restore_mode="merge_preserve_sensitive_json",
                        )
                    )

                except Exception:
                    # If the config cannot be parsed safely, skip it rather than
                    # writing a raw potentially-secret configuration into an
                    # unencrypted recovery ZIP.
                    continue

            else:
                archive.write(
                    source,
                    arcname=archive_path,
                )

                entries.append(
                    _manifest_entry(
                        archive_path=archive_path,
                        source_path=source,
                        destination_group="app",
                        destination_relative=source.name,
                    )
                )

        profile_root_path = profile_root()

        for source in profile_files:
            relative = source.relative_to(
                profile_root_path
            )

            archive_path = (
                "profile_store/"
                +
                str(
                    relative
                ).replace(
                    "\\",
                    "/"
                )
            )

            archive.write(
                source,
                arcname=archive_path,
            )

            entries.append(
                _manifest_entry(
                    archive_path=archive_path,
                    source_path=source,
                    destination_group="profile_store",
                    destination_relative=relative,
                )
            )

        manifest = {
            "schema_version": SNAPSHOT_SCHEMA_VERSION,
            "created_at": _now_iso(),
            "kind": kind_clean,
            "label": str(
                label
                or
                ""
            ),
            "profile_name": profile_name,
            "profile_id": str(
                profile.get(
                    "profile_id",
                    ""
                )
            ),
            "source_base": str(
                BASE
            ),
            "source_profile_root": str(
                profile_root_path
            ),
            "diagnostic_overall": (
                str(
                    diagnostic_report.get(
                        "overall",
                        ""
                    )
                ).upper()
                if isinstance(
                    diagnostic_report,
                    dict
                )
                else
                ""
            ),
            "diagnostic_generated_at": (
                str(
                    diagnostic_report.get(
                        "generated_at",
                        ""
                    )
                )
                if isinstance(
                    diagnostic_report,
                    dict
                )
                else
                ""
            ),
            "secrets_included": False,
            "sunday_config_secret_keys_included": False,
            "runtime_sermon_plan_included": False,
            "file_count": len(
                entries
            ),
            "files": entries,
        }

        archive.writestr(
            "manifest.json",
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            )
            +
            "\n",
        )

        if isinstance(
            diagnostic_report,
            dict
        ):
            archive.writestr(
                "diagnostic_reference.json",
                json.dumps(
                    diagnostic_report,
                    indent=2,
                    ensure_ascii=False,
                )
                +
                "\n",
            )

        archive.writestr(
            "README.txt",
            (
                "Sunday Service System recovery snapshot.\n"
                "Secrets/OAuth/password/token files are excluded.\n"
                "Secret-like keys are removed from sunday_config.json and preserved from the current PC during restore.\n"
                "Transient weekly sermon/runtime status files are excluded.\n"
                "Restore is explicit and blocked while live OBS outputs are active.\n"
            ),
        )

    os.replace(
        temp_snapshot,
        snapshot_path,
    )

    if kind_clean == "last_known_good":
        pointer = {
            "snapshot": snapshot_path.name,
            "created_at": _now_iso(),
            "diagnostic_overall": "READY",
            "profile_name": profile_name,
        }

        RECOVERY_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_pointer = LAST_KNOWN_GOOD_POINTER.with_suffix(
            ".json.tmp"
        )

        temp_pointer.write_text(
            json.dumps(
                pointer,
                indent=2,
            )
            +
            "\n",
            encoding="utf-8",
        )

        os.replace(
            temp_pointer,
            LAST_KNOWN_GOOD_POINTER,
        )

    try:
        record_event(
            (
                "Recovery snapshot created: "
                +
                snapshot_path.name
                +
                " ("
                +
                kind_clean.replace(
                    "_",
                    " "
                )
                +
                ")."
            ),
            category="RECOVERY",
            level="ACTION",
            source="RECOVERY",
            metadata={
                "kind": kind_clean,
                "diagnostic_overall": (
                    str(
                        diagnostic_report.get(
                            "overall",
                            ""
                        )
                    )
                    if isinstance(
                        diagnostic_report,
                        dict
                    )
                    else
                    ""
                ),
            },
        )
    except Exception:
        pass

    return snapshot_path


def read_snapshot_manifest(
    snapshot_path
):
    snapshot_path = Path(
        snapshot_path
    )

    with zipfile.ZipFile(
        snapshot_path,
        "r"
    ) as archive:
        try:
            raw = archive.read(
                "manifest.json"
            )
        except KeyError as exc:
            raise RuntimeError(
                "Recovery ZIP has no manifest.json."
            ) from exc

    manifest = json.loads(
        raw.decode(
            "utf-8"
        )
    )

    if int(
        manifest.get(
            "schema_version",
            0
        )
    ) != SNAPSHOT_SCHEMA_VERSION:
        raise RuntimeError(
            (
                "Unsupported recovery snapshot schema: "
                +
                str(
                    manifest.get(
                        "schema_version",
                        ""
                    )
                )
            )
        )

    return manifest


def list_recovery_snapshots():
    ensure_recovery_dirs()

    items = []

    for path in SNAPSHOT_DIR.glob(
        "*.zip"
    ):
        try:
            manifest = read_snapshot_manifest(
                path
            )

            items.append(
                {
                    "path": path,
                    "filename": path.name,
                    "created_at": manifest.get(
                        "created_at",
                        ""
                    ),
                    "kind": manifest.get(
                        "kind",
                        "manual"
                    ),
                    "label": manifest.get(
                        "label",
                        ""
                    ),
                    "profile_name": manifest.get(
                        "profile_name",
                        ""
                    ),
                    "diagnostic_overall": manifest.get(
                        "diagnostic_overall",
                        ""
                    ),
                    "file_count": manifest.get(
                        "file_count",
                        0
                    ),
                }
            )

        except Exception as exc:
            items.append(
                {
                    "path": path,
                    "filename": path.name,
                    "created_at": "",
                    "kind": "invalid",
                    "label": "",
                    "profile_name": "",
                    "diagnostic_overall": "",
                    "file_count": 0,
                    "error": str(
                        exc
                    ),
                }
            )

    items.sort(
        key=lambda item:
            item.get(
                "created_at",
                ""
            ),
        reverse=True,
    )

    return items


def last_known_good_snapshot():
    if not LAST_KNOWN_GOOD_POINTER.exists():
        return None

    try:
        payload = json.loads(
            LAST_KNOWN_GOOD_POINTER.read_text(
                encoding="utf-8"
            )
        )

        filename = Path(
            str(
                payload.get(
                    "snapshot",
                    ""
                )
            )
        ).name

        if not filename:
            return None

        path = (
            SNAPSHOT_DIR
            /
            filename
        )

        if not path.exists():
            return None

        return path

    except Exception:
        return None


def _safe_archive_member_path(
    root,
    archive_name
):
    root = Path(
        root
    ).resolve()

    candidate = (
        root
        /
        archive_name
    ).resolve()

    try:
        candidate.relative_to(
            root
        )
    except Exception as exc:
        raise RuntimeError(
            (
                "Unsafe path in recovery snapshot: "
                +
                archive_name
            )
        ) from exc

    return candidate


def verify_recovery_snapshot(
    snapshot_path
):
    snapshot_path = Path(
        snapshot_path
    )

    manifest = read_snapshot_manifest(
        snapshot_path
    )

    with tempfile.TemporaryDirectory(
        prefix="sss_recovery_verify_"
    ) as temp_dir:
        temp_root = Path(
            temp_dir
        )

        with zipfile.ZipFile(
            snapshot_path,
            "r"
        ) as archive:
            archive.extractall(
                temp_root
            )

        for entry in manifest.get(
            "files",
            []
        ):
            archive_name = str(
                entry.get(
                    "archive_path",
                    ""
                )
            )

            source = _safe_archive_member_path(
                temp_root,
                archive_name
            )

            if not source.exists():
                raise RuntimeError(
                    (
                        "Recovery snapshot is missing: "
                        +
                        archive_name
                    )
                )

            expected = str(
                entry.get(
                    "sha256",
                    ""
                )
            ).lower()

            actual = _sha256(
                source
            ).lower()

            if (
                expected
                and
                actual
                !=
                expected
            ):
                raise RuntimeError(
                    (
                        "Recovery snapshot checksum failed: "
                        +
                        archive_name
                    )
                )

    return manifest


def restore_recovery_snapshot(
    snapshot_path,
    *,
    create_pre_restore=True
):
    snapshot_path = Path(
        snapshot_path
    )

    safety = restore_safety_status()

    if not safety.get(
        "safe"
    ):
        raise RuntimeError(
            safety.get(
                "detail",
                "Restore is not safe right now."
            )
        )

    manifest = verify_recovery_snapshot(
        snapshot_path
    )

    pre_restore_snapshot = None

    if create_pre_restore:
        pre_restore_snapshot = create_recovery_snapshot(
            kind="pre_restore",
            label="automatic",
        )

    with tempfile.TemporaryDirectory(
        prefix="sss_recovery_restore_"
    ) as temp_dir:
        temp_root = Path(
            temp_dir
        )

        with zipfile.ZipFile(
            snapshot_path,
            "r"
        ) as archive:
            archive.extractall(
                temp_root
            )

        for entry in manifest.get(
            "files",
            []
        ):
            archive_name = str(
                entry.get(
                    "archive_path",
                    ""
                )
            )

            source = _safe_archive_member_path(
                temp_root,
                archive_name
            )

            group = str(
                entry.get(
                    "destination_group",
                    ""
                )
            )

            relative = Path(
                str(
                    entry.get(
                        "destination_relative",
                        ""
                    )
                )
            )

            if (
                not str(
                    relative
                )
                or
                str(
                    relative
                )
                ==
                "."
            ):
                raise RuntimeError(
                    (
                        "Invalid restore destination for "
                        +
                        archive_name
                    )
                )

            if group == "app":
                destination = (
                    BASE
                    /
                    relative
                )

            elif group == "profile_store":
                destination = (
                    profile_root()
                    /
                    relative
                )

            else:
                raise RuntimeError(
                    (
                        "Unknown recovery destination group: "
                        +
                        group
                    )
                )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            restore_mode = str(
                entry.get(
                    "restore_mode",
                    "replace"
                )
            )

            temp_destination = destination.with_suffix(
                destination.suffix
                +
                ".sss_restore_tmp"
            )

            if restore_mode == "merge_preserve_sensitive_json":
                restored_payload = json.loads(
                    source.read_text(
                        encoding="utf-8"
                    )
                )

                current_payload = {}

                if destination.exists():
                    try:
                        current_payload = json.loads(
                            destination.read_text(
                                encoding="utf-8"
                            )
                        )
                    except Exception:
                        current_payload = {}

                merged_payload = _merge_preserving_sensitive(
                    current_payload,
                    restored_payload,
                )

                temp_destination.write_text(
                    json.dumps(
                        merged_payload,
                        indent=2,
                        ensure_ascii=False,
                    )
                    +
                    "\n",
                    encoding="utf-8",
                )

            else:
                shutil.copy2(
                    source,
                    temp_destination,
                )

            os.replace(
                temp_destination,
                destination,
            )

    result = {
        "restored_snapshot": snapshot_path,
        "manifest": manifest,
        "pre_restore_snapshot": pre_restore_snapshot,
        "restart_required": True,
        "secrets_touched": False,
        "sermon_plan_touched": False,
    }

    try:
        record_event(
            (
                "SSS recovery snapshot restored: "
                +
                snapshot_path.name
                +
                ". Restart required."
            ),
            category="RECOVERY",
            level="ACTION",
            source="RECOVERY",
            metadata={
                "pre_restore_snapshot": (
                    str(
                        pre_restore_snapshot
                    )
                    if pre_restore_snapshot
                    else
                    ""
                ),
            },
        )
    except Exception:
        pass

    return result
