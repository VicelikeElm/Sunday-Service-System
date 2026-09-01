import ctypes
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from sss_profile_migrations import (
    CURRENT_PROFILE_SCHEMA_VERSION,
    migrate_profile_dict,
    profile_schema_version,
)


APP_NAME = "Sunday Service System"
APP_ID = "SundayServiceSystem.Desktop"
PROFILE_SCHEMA_VERSION = CURRENT_PROFILE_SCHEMA_VERSION

LEGACY_BASE = Path(
    r"C:\Church\SermonAI"
)


def _safe_slug(value):
    value = " ".join(
        str(
            value
            or
            "Church Profile"
        ).split()
    )

    slug = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        value,
    ).strip(
        "._-"
    )

    return (
        slug
        or
        "Church_Profile"
    )


def _write_json_atomic(
    path,
    payload
):
    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix
        +
        ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        +
        "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        path,
    )


def _profile_root_candidates():
    candidates = []

    program_data = os.environ.get(
        "PROGRAMDATA"
    )

    if program_data:
        candidates.append(
            Path(
                program_data
            )
            /
            APP_NAME
        )

    local_app_data = os.environ.get(
        "LOCALAPPDATA"
    )

    if local_app_data:
        candidates.append(
            Path(
                local_app_data
            )
            /
            APP_NAME
        )

    candidates.append(
        LEGACY_BASE
        /
        "Profiles"
    )

    return candidates


def profile_root():
    """
    Prefer ProgramData for the future installed-app layout.

    Until we have an installer that creates ProgramData permissions,
    transparently fall back to LocalAppData or the existing SermonAI
    folder. This prevents the new profile layer from breaking today's
    working church PC.
    """
    for candidate in _profile_root_candidates():
        try:
            candidate.mkdir(
                parents=True,
                exist_ok=True,
            )

            probe = (
                candidate
                /
                ".sss_write_test"
            )

            probe.write_text(
                "ok",
                encoding="utf-8",
            )

            probe.unlink(
                missing_ok=True
            )

            return candidate

        except Exception:
            continue

    raise RuntimeError(
        "Sunday Service System could not create its profile folder."
    )


def profiles_dir():
    path = (
        profile_root()
        /
        "Profiles"
    )

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path


def active_profile_pointer():
    return (
        profile_root()
        /
        "active_profile.json"
    )


def migration_backups_dir():
    path = (
        profile_root()
        /
        "Migration Backups"
    )

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path


def _backup_profile_before_migration(
    path,
    *,
    from_version,
    to_version
):
    path = Path(
        path
    )

    stamp = datetime.now().astimezone().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    backup = (
        migration_backups_dir()
        /
        (
            _safe_slug(
                path.stem
            )
            +
            "_schema"
            +
            str(
                from_version
            )
            +
            "_to"
            +
            str(
                to_version
            )
            +
            "_"
            +
            stamp
            +
            ".json"
        )
    )

    shutil.copy2(
        path,
        backup,
    )

    return backup


def _validate_current_profile(
    profile
):
    if not isinstance(
        profile,
        dict
    ):
        raise ValueError(
            "Profile file is not a JSON object."
        )

    version = profile_schema_version(
        profile
    )

    if version != PROFILE_SCHEMA_VERSION:
        raise ValueError(
            (
                "Profile migration did not produce the current schema. "
                "Expected "
                +
                str(
                    PROFILE_SCHEMA_VERSION
                )
                +
                ", got "
                +
                str(
                    version
                )
                +
                "."
            )
        )

    name = " ".join(
        str(
            profile.get(
                "profile_name",
                ""
            )
        ).split()
    )

    if not name:
        raise ValueError(
            "Profile is missing profile_name."
        )

    compatibility = profile.get(
        "compatibility",
        {}
    )

    if not isinstance(
        compatibility,
        dict
    ):
        raise ValueError(
            "Profile compatibility block is invalid."
        )

    integrations = profile.get(
        "integrations",
        {}
    )

    if not isinstance(
        integrations,
        dict
    ):
        raise ValueError(
            "Profile integrations block is invalid."
        )

    for required in (
        "obs",
        "presentation",
        "camera",
        "audio",
        "sermon_source",
    ):
        if not isinstance(
            integrations.get(
                required,
                {}
            ),
            dict
        ):
            raise ValueError(
                (
                    "Profile integration block is invalid: "
                    +
                    required
                )
            )

    setup = profile.get(
        "setup",
        {}
    )

    if not isinstance(
        setup,
        dict
    ):
        raise ValueError(
            "Profile setup block is invalid."
        )

    capabilities = profile.get(
        "capabilities",
        {}
    )

    if not isinstance(
        capabilities,
        dict
    ):
        raise ValueError(
            "Profile capabilities block is invalid."
        )

    security = profile.get(
        "security",
        {}
    )

    if not isinstance(
        security,
        dict
    ):
        raise ValueError(
            "Profile security block is invalid."
        )

    return profile


def _prepare_profile_data(
    profile
):
    migrated, report = migrate_profile_dict(
        profile
    )

    migrated = _validate_current_profile(
        migrated
    )

    return (
        migrated,
        report,
    )


def migrate_profile_file(
    path
):
    """
    Upgrade one installed profile safely.

    - Future schemas are rejected without modification.
    - Old profiles are backed up before rewrite.
    - Migration never changes LEGACY to PROFILE.
    - Atomic write occurs only after the full migration validates.
    """
    path = Path(
        path
    )

    raw = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    original_version = profile_schema_version(
        raw
    )

    migrated, report = _prepare_profile_data(
        raw
    )

    backup = None

    if report.get(
        "changed"
    ):
        backup = _backup_profile_before_migration(
            path,
            from_version=report[
                "from_version"
            ],
            to_version=report[
                "to_version"
            ],
        )

        migrated = dict(
            migrated
        )

        migrated[
            "updated_at"
        ] = datetime.now().astimezone().isoformat()

        _write_json_atomic(
            path,
            migrated,
        )

        try:
            from sss_event_history import record_event

            record_event(
                (
                    "Profile migrated: "
                    +
                    str(
                        migrated.get(
                            "profile_name",
                            path.stem
                        )
                    )
                    +
                    " — schema "
                    +
                    str(
                        original_version
                    )
                    +
                    " -> "
                    +
                    str(
                        PROFILE_SCHEMA_VERSION
                    )
                    +
                    "."
                ),
                category="SYSTEM",
                level="ACTION",
                source="PROFILE MIGRATION",
                metadata={
                    "backup": (
                        str(
                            backup
                        )
                        if backup is not None
                        else
                        ""
                    ),
                },
            )
        except Exception:
            pass

    return {
        "profile": migrated,
        "report": report,
        "backup": backup,
        "path": path,
    }


def profile_migration_status(
    path
):
    path = Path(
        path
    )

    raw = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    version = profile_schema_version(
        raw
    )

    if version > PROFILE_SCHEMA_VERSION:
        return {
            "path": path,
            "profile_name": str(
                raw.get(
                    "profile_name",
                    path.stem
                )
            ),
            "schema_version": version,
            "current_schema_version": PROFILE_SCHEMA_VERSION,
            "status": "NEWER",
            "needs_migration": False,
            "detail": (
                "Profile is newer than this SSS build."
            ),
        }

    if version < PROFILE_SCHEMA_VERSION:
        return {
            "path": path,
            "profile_name": str(
                raw.get(
                    "profile_name",
                    path.stem
                )
            ),
            "schema_version": version,
            "current_schema_version": PROFILE_SCHEMA_VERSION,
            "status": "UPGRADE",
            "needs_migration": True,
            "detail": (
                "Safe migration available."
            ),
        }

    _validate_current_profile(
        raw
    )

    return {
        "path": path,
        "profile_name": str(
            raw.get(
                "profile_name",
                path.stem
            )
        ),
        "schema_version": version,
        "current_schema_version": PROFILE_SCHEMA_VERSION,
        "status": "CURRENT",
        "needs_migration": False,
        "detail": "Current profile schema.",
    }


def list_profile_migration_status():
    results = []

    for path in sorted(
        profiles_dir().glob(
            "*.json"
        ),
        key=lambda item:
            item.name.lower(),
    ):
        try:
            results.append(
                profile_migration_status(
                    path
                )
            )
        except Exception as exc:
            results.append(
                {
                    "path": path,
                    "profile_name": path.stem,
                    "schema_version": None,
                    "current_schema_version": PROFILE_SCHEMA_VERSION,
                    "status": "ERROR",
                    "needs_migration": False,
                    "detail": str(
                        exc
                    ),
                }
            )

    return results


def migrate_all_installed_profiles():
    results = []

    for item in list_profile_migration_status():
        path = item.get(
            "path"
        )

        if item.get(
            "status"
        ) == "NEWER":
            results.append(
                item
            )
            continue

        if item.get(
            "status"
        ) == "ERROR":
            results.append(
                item
            )
            continue

        if not item.get(
            "needs_migration"
        ):
            results.append(
                item
            )
            continue

        try:
            migrated = migrate_profile_file(
                path
            )

            report = migrated[
                "report"
            ]

            results.append(
                {
                    "path": path,
                    "profile_name": migrated[
                        "profile"
                    ].get(
                        "profile_name",
                        path.stem
                    ),
                    "schema_version": report[
                        "to_version"
                    ],
                    "current_schema_version": PROFILE_SCHEMA_VERSION,
                    "status": "MIGRATED",
                    "needs_migration": False,
                    "detail": (
                        "Migrated schema "
                        +
                        str(
                            report[
                                "from_version"
                            ]
                        )
                        +
                        " -> "
                        +
                        str(
                            report[
                                "to_version"
                            ]
                        )
                    ),
                    "backup": migrated.get(
                        "backup"
                    ),
                }
            )

        except Exception as exc:
            results.append(
                {
                    "path": path,
                    "profile_name": item.get(
                        "profile_name",
                        path.stem
                    ),
                    "schema_version": item.get(
                        "schema_version"
                    ),
                    "current_schema_version": PROFILE_SCHEMA_VERSION,
                    "status": "ERROR",
                    "needs_migration": True,
                    "detail": str(
                        exc
                    ),
                }
            )

    return results


def _default_perry_profile():
    """
    Compatibility profile for the existing church system.

    Version 1 deliberately does NOT replace the existing sunday_config,
    PTZ persistent settings, .env, Gmail credentials, or other working
    configuration. It describes the current installation and gives us a
    stable portable profile container to migrate settings into gradually.
    """
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "profile_id": "baptist_church_of_perry",
        "profile_name": "Baptist Church of Perry",
        "church": {
            "name": "Baptist Church of Perry",
        },
        "compatibility": {
            "mode": "legacy_existing_configuration",
            "behavior_changes_enabled": False,
            "notes": (
                "Versioned compatibility profile. Existing SermonAI/SSS settings "
                "remain authoritative so Sunday behavior does not change."
            ),
        },
        "integrations": {
            "obs": {
                "enabled": True,
                "provider": "OBS Studio",
                "settings_source": "existing_configuration",
            },
            "presentation": {
                "enabled": True,
                "provider": "WorshipTools Presenter",
                "settings_source": "existing_configuration",
                "connection": {
                    "host": "127.0.0.1",
                    "port": 50001,
                },
            },
            "camera": {
                "enabled": True,
                "provider": "PTZOptics / HTTP-CGI",
                "settings_source": "existing_configuration",
                "connection": {
                    "host": "",
                    "port": 80,
                },
                "presets": {
                    "worship": 1,
                    "pastor": 2,
                    "startup": 2,
                },
                "auto_recall_on_start": True,
            },
            "audio": {
                "enabled": True,
                "provider": "OBS Audio Inputs",
                "settings_source": "existing_configuration",
                "mute_inputs": [],
                "monitor": {
                    "endpoint": "",
                    "label": "Audio Interface",
                },
            },
            "sermon_source": {
                "enabled": True,
                "provider": "Pastor Email",
                "settings_source": "existing_configuration",
                "manual_plan": {},
                "imported_plan": {},
                "email": {
                    "sender": "",
                    "auto_refresh_on_start": True,
                },
                "last_import_name": "",
            },
            "planning": {
                "enabled": True,
                "settings_source": "existing_configuration",
            },
            "youtube": {
                "enabled": True,
                "settings_source": "existing_configuration",
            },
            "sermon_ai": {
                "enabled": True,
                "settings_source": "existing_configuration",
            },
        },
        "portable_settings": {},
        "capabilities": {
            "settings_source": "legacy",
            "recording": True,
            "streaming": True,
            "audio_mute": True,
            "scripture": True,
            "sermon_controls": True,
            "camera_controls": True,
        },
        "setup": {
            "wizard_completed": False,
            "completed_steps": [],
            "last_completed_at": "",
        },
        "migration": {
            "history": [],
            "last_migrated_at": "",
            "last_migrated_from": None,
            "last_migrated_to": None,
        },
        "security": {
            "credential_provider": "Windows Credential Manager",
            "secrets_portable": False,
            "obs_websocket_password": {
                "storage": "local_vault_preferred",
                "portable": False,
            },
            "oauth": {
                "gmail": "legacy_local_file",
                "youtube": "legacy_local_file",
            },
        },
        "secrets": {
            "included": False,
            "notes": (
                "Passwords, OAuth tokens, API credentials, .env values, "
                "and other secrets are never written into exported profiles."
            ),
        },
        "created_at": datetime.now().astimezone().isoformat(),
        "updated_at": datetime.now().astimezone().isoformat(),
    }


def _validate_profile(
    profile
):
    """
    Backward-compatible in-memory validation.

    Disk migration/backups are handled by migrate_profile_file(). This helper
    lets imported/listed old profiles be inspected safely without forcing a
    write.
    """
    migrated, _report = _prepare_profile_data(
        profile
    )

    return migrated


def _profile_path_from_id(
    profile_id
):
    return (
        profiles_dir()
        /
        (
            _safe_slug(
                profile_id
            )
            +
            ".json"
        )
    )


def _set_active_profile_path(
    path
):
    path = Path(
        path
    )

    payload = {
        "schema_version": 1,
        "active_profile_file": path.name,
        "updated_at": datetime.now().astimezone().isoformat(),
    }

    _write_json_atomic(
        active_profile_pointer(),
        payload,
    )


def ensure_active_profile():
    """
    Create the Perry compatibility profile only when no valid active-profile
    pointer/profile exists yet.

    If an existing active profile cannot be migrated/validated, propagate the
    error instead of silently switching churches.
    """
    pointer = active_profile_pointer()

    if pointer.exists():
        data = None

        try:
            data = json.loads(
                pointer.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            data = None

        if isinstance(
            data,
            dict
        ):
            filename = str(
                data.get(
                    "active_profile_file",
                    ""
                )
                or
                ""
            ).strip()

            if filename:
                candidate = (
                    profiles_dir()
                    /
                    Path(
                        filename
                    ).name
                )

                if candidate.exists():
                    migrated = migrate_profile_file(
                        candidate
                    )

                    return migrated[
                        "profile"
                    ]

    profile = _default_perry_profile()

    path = _profile_path_from_id(
        profile[
            "profile_id"
        ]
    )

    if not path.exists():
        _write_json_atomic(
            path,
            profile,
        )

    else:
        profile = migrate_profile_file(
            path
        )[
            "profile"
        ]

    _set_active_profile_path(
        path
    )

    return profile


def load_active_profile():
    return ensure_active_profile()


def active_profile_path():
    ensure_active_profile()

    data = json.loads(
        active_profile_pointer().read_text(
            encoding="utf-8"
        )
    )

    filename = Path(
        str(
            data[
                "active_profile_file"
            ]
        )
    ).name

    return (
        profiles_dir()
        /
        filename
    )


def create_profile(
    profile_name,
    *,
    church_name=None,
    make_active=True
):
    """Create a new compatibility-mode SSS church profile."""
    profile_name = " ".join(
        str(
            profile_name
            or
            ""
        ).split()
    )

    if not profile_name:
        raise ValueError(
            "Profile name is required."
        )

    if church_name is None:
        church_name = profile_name

    church_name = " ".join(
        str(
            church_name
            or
            profile_name
        ).split()
    )

    base_id = _safe_slug(
        profile_name
    ).lower()

    existing_ids = {
        str(
            item.get(
                "profile_id",
                ""
            )
        )
        for item in list_profiles()
    }

    profile_id = base_id
    suffix = 2

    while profile_id in existing_ids:
        profile_id = (
            base_id
            +
            "_"
            +
            str(
                suffix
            )
        )

        suffix += 1

    now = datetime.now().astimezone().isoformat()

    profile = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "profile_id": profile_id,
        "profile_name": profile_name,
        "church": {
            "name": church_name,
        },
        "compatibility": {
            "mode": "legacy_existing_configuration",
            "behavior_changes_enabled": False,
            "notes": (
                "Current SSS compatibility profile. Existing live "
                "SSS settings remain authoritative until a later migration "
                "step explicitly enables profile-backed configuration."
            ),
        },
        "integrations": {
            "obs": {
                "enabled": False,
                "provider": "",
                "settings_source": "not_configured",
            },
            "presentation": {
                "enabled": False,
                "provider": "",
                "settings_source": "not_configured",
                "connection": {
                    "host": "127.0.0.1",
                    "port": 50001,
                },
            },
            "camera": {
                "enabled": False,
                "provider": "",
                "settings_source": "not_configured",
                "connection": {
                    "host": "",
                    "port": 80,
                },
                "presets": {
                    "worship": 1,
                    "pastor": 2,
                    "startup": 2,
                },
                "auto_recall_on_start": True,
            },
            "audio": {
                "enabled": False,
                "provider": "OBS Audio Inputs",
                "settings_source": "not_configured",
                "mute_inputs": [],
                "monitor": {
                    "endpoint": "",
                    "label": "Audio Interface",
                },
            },
            "sermon_source": {
                "enabled": False,
                "provider": "Manual",
                "settings_source": "not_configured",
                "manual_plan": {},
                "imported_plan": {},
                "email": {
                    "sender": "",
                    "auto_refresh_on_start": True,
                },
                "last_import_name": "",
            },
            "planning": {
                "enabled": False,
                "settings_source": "not_configured",
            },
            "youtube": {
                "enabled": False,
                "settings_source": "not_configured",
            },
            "sermon_ai": {
                "enabled": False,
                "settings_source": "not_configured",
            },
        },
        "portable_settings": {},
        "capabilities": {
            "settings_source": "profile",
            "recording": True,
            "streaming": True,
            "audio_mute": True,
            "scripture": True,
            "sermon_controls": True,
            "camera_controls": True,
        },
        "setup": {
            "wizard_completed": False,
            "completed_steps": [],
            "last_completed_at": "",
        },
        "migration": {
            "history": [],
            "last_migrated_at": "",
            "last_migrated_from": None,
            "last_migrated_to": None,
        },
        "security": {
            "credential_provider": "Windows Credential Manager",
            "secrets_portable": False,
            "obs_websocket_password": {
                "storage": "local_vault_preferred",
                "portable": False,
            },
            "oauth": {
                "gmail": "legacy_local_file",
                "youtube": "legacy_local_file",
            },
        },
        "secrets": {
            "included": False,
            "notes": (
                "Passwords, OAuth tokens, API credentials, .env values, "
                "and other secrets are never stored in portable profiles."
            ),
        },
        "created_at": now,
        "updated_at": now,
    }

    path = _profile_path_from_id(
        profile_id
    )

    _write_json_atomic(
        path,
        profile,
    )

    if make_active:
        _set_active_profile_path(
            path
        )

    return profile


def list_profiles():
    """
    Return installed SSS profiles without changing the active profile.

    Invalid/corrupt profile files are skipped so one bad import cannot break
    the Sunday dashboard.
    """
    profiles = []

    active_path = None

    try:
        active_path = active_profile_path().resolve()
    except Exception:
        active_path = None

    for path in sorted(
        profiles_dir().glob(
            "*.json"
        ),
        key=lambda item: item.name.lower(),
    ):
        try:
            raw_profile = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            original_schema = profile_schema_version(
                raw_profile
            )

            profile = _validate_profile(
                raw_profile
            )

            resolved = path.resolve()

            profiles.append(
                {
                    "schema_version": original_schema,
                    "current_schema_version": PROFILE_SCHEMA_VERSION,
                    "migration_needed": (
                        original_schema
                        <
                        PROFILE_SCHEMA_VERSION
                    ),
                    "profile_id": str(
                        profile.get(
                            "profile_id",
                            path.stem
                        )
                    ),
                    "profile_name": " ".join(
                        str(
                            profile.get(
                                "profile_name",
                                path.stem
                            )
                        ).split()
                    ),
                    "path": str(
                        path
                    ),
                    "active": (
                        active_path is not None
                        and
                        resolved == active_path
                    ),
                }
            )

        except Exception:
            continue

    return profiles


def set_active_profile(
    profile_id
):
    """
    Switch the active profile pointer.

    Profile Layer v1 remains compatibility-only, so this changes only the
    selected church profile identity. Existing live SSS configuration remains
    authoritative until later migration stages explicitly enable profile-backed
    settings.
    """
    requested = str(
        profile_id
        or
        ""
    ).strip()

    if not requested:
        raise ValueError(
            "No profile was selected."
        )

    for item in list_profiles():
        if item[
            "profile_id"
        ] == requested:
            path = Path(
                item[
                    "path"
                ]
            )

            profile = migrate_profile_file(
                path
            )[
                "profile"
            ]

            _set_active_profile_path(
                path
            )

            return profile

    raise FileNotFoundError(
        (
            "SSS profile was not found: "
            +
            requested
        )
    )


def save_active_profile(
    profile
):
    """Validate and atomically save the currently active profile."""
    profile, _migration_report = _prepare_profile_data(
        profile
    )

    profile = dict(
        profile
    )

    profile[
        "updated_at"
    ] = datetime.now().astimezone().isoformat()

    path = active_profile_path()

    _write_json_atomic(
        path,
        profile,
    )

    return profile


def get_profile_obs_settings(
    profile=None
):
    """
    Return a normalized OBS profile block.

    Older v1 profiles are upgraded in memory only. Merely reading settings
    never rewrites a user's profile file.
    """
    if profile is None:
        profile = load_active_profile()

    integrations = profile.get(
        "integrations",
        {}
    )

    if not isinstance(
        integrations,
        dict
    ):
        integrations = {}

    raw = integrations.get(
        "obs",
        {}
    )

    if not isinstance(
        raw,
        dict
    ):
        raw = {}

    raw_source = str(
        raw.get(
            "settings_source",
            "legacy"
        )
        or
        "legacy"
    ).strip().lower()

    if raw_source in {
        "existing_configuration",
        "legacy_existing_configuration",
        "current",
    }:
        source = "legacy"
    elif raw_source == "profile":
        source = "profile"
    else:
        source = "legacy"

    scenes = raw.get(
        "scenes",
        {}
    )

    if not isinstance(
        scenes,
        dict
    ):
        scenes = {}

    return {
        "enabled": bool(
            raw.get(
                "enabled",
                True
            )
        ),
        "provider": str(
            raw.get(
                "provider",
                "OBS Studio"
            )
            or
            "OBS Studio"
        ),
        "settings_source": source,
        "scene_collection": " ".join(
            str(
                raw.get(
                    "scene_collection",
                    ""
                )
                or
                ""
            ).split()
        ),
        "normal_scene": " ".join(
            str(
                scenes.get(
                    "normal",
                    raw.get(
                        "normal_scene",
                        ""
                    )
                )
                or
                ""
            ).split()
        ),
        "scripture_scene": " ".join(
            str(
                scenes.get(
                    "scripture",
                    raw.get(
                        "scripture_scene",
                        ""
                    )
                )
                or
                ""
            ).split()
        ),
        "sermon_scene": " ".join(
            str(
                scenes.get(
                    "sermon",
                    raw.get(
                        "sermon_scene",
                        ""
                    )
                )
                or
                ""
            ).split()
        ),
        "discovered_at": str(
            raw.get(
                "discovered_at",
                ""
            )
            or
            ""
        ),
    }


def save_active_obs_settings(
    *,
    settings_source,
    scene_collection="",
    normal_scene="",
    scripture_scene="",
    sermon_scene="",
    discovered_at=""
):
    """Save portable OBS scene mappings into the active profile."""
    source = str(
        settings_source
        or
        "legacy"
    ).strip().lower()

    if source not in {
        "legacy",
        "profile",
    }:
        raise ValueError(
            "OBS configuration source must be LEGACY or PROFILE."
        )

    if source == "profile":
        missing = []

        if not str(
            scene_collection
            or
            ""
        ).strip():
            missing.append(
                "scene collection"
            )

        if not str(
            normal_scene
            or
            ""
        ).strip():
            missing.append(
                "normal / webcam scene"
            )

        if not str(
            scripture_scene
            or
            ""
        ).strip():
            missing.append(
                "scripture / presentation scene"
            )

        if missing:
            raise ValueError(
                (
                    "PROFILE mode needs: "
                    +
                    ", ".join(
                        missing
                    )
                    +
                    "."
                )
            )

    profile = dict(
        load_active_profile()
    )

    integrations = dict(
        profile.get(
            "integrations",
            {}
        )
        or
        {}
    )

    obs_settings = dict(
        integrations.get(
            "obs",
            {}
        )
        or
        {}
    )

    obs_settings.update(
        {
            "enabled": True,
            "provider": "OBS Studio",
            "settings_source": source,
            "scene_collection": " ".join(
                str(
                    scene_collection
                    or
                    ""
                ).split()
            ),
            "scenes": {
                "normal": " ".join(
                    str(
                        normal_scene
                        or
                        ""
                    ).split()
                ),
                "scripture": " ".join(
                    str(
                        scripture_scene
                        or
                        ""
                    ).split()
                ),
                "sermon": " ".join(
                    str(
                        sermon_scene
                        or
                        ""
                    ).split()
                ),
            },
            "discovered_at": str(
                discovered_at
                or
                ""
            ),
        }
    )

    integrations[
        "obs"
    ] = obs_settings

    profile[
        "integrations"
    ] = integrations

    return save_active_profile(
        profile
    )


SETUP_STEPS = (
    "church",
    "obs",
    "presentation",
    "camera",
    "sermon_source",
)


def get_profile_setup_status(profile=None):
    if profile is None:
        profile = load_active_profile()

    completed = set()

    church = profile.get("church", {})
    if isinstance(church, dict) and str(church.get("name", "")).strip():
        completed.add("church")

    integrations = profile.get("integrations", {})
    if not isinstance(integrations, dict):
        integrations = {}

    obs = integrations.get("obs", {})
    if isinstance(obs, dict):
        source = str(obs.get("settings_source", "") or "").strip().lower()
        if source in {
            "legacy",
            "existing_configuration",
            "legacy_existing_configuration",
            "profile",
        }:
            completed.add("obs")

    presentation = integrations.get("presentation", {})
    if (
        isinstance(presentation, dict)
        and
        str(presentation.get("provider", "")).strip()
    ):
        completed.add("presentation")

    camera = integrations.get("camera", {})
    if isinstance(camera, dict):
        provider = str(camera.get("provider", "")).strip()
        if provider or camera.get("enabled") is False:
            completed.add("camera")

    sermon = integrations.get("sermon_source", {})
    if (
        isinstance(sermon, dict)
        and
        str(sermon.get("provider", "")).strip()
    ):
        completed.add("sermon_source")

    setup = profile.get("setup", {})
    if isinstance(setup, dict):
        for step in setup.get("completed_steps", []) or []:
            if step in SETUP_STEPS:
                completed.add(step)

    ordered = [step for step in SETUP_STEPS if step in completed]

    return {
        "completed": len(ordered),
        "total": len(SETUP_STEPS),
        "ready": len(ordered) == len(SETUP_STEPS),
        "wizard_completed": bool(
            isinstance(setup, dict)
            and
            setup.get("wizard_completed", False)
        ),
        "completed_steps": ordered,
        "missing_steps": [
            step
            for step in SETUP_STEPS
            if step not in completed
        ],
    }


def save_active_setup_choices(
    *,
    church_name,
    presentation_provider,
    camera_provider,
    sermon_source_provider,
    wizard_completed=True
):
    profile = dict(load_active_profile())

    profile["church"] = {
        "name": " ".join(
            str(
                church_name
                or
                profile.get("profile_name", "Church Profile")
            ).split()
        )
    }

    integrations = dict(profile.get("integrations", {}) or {})

    presentation_name = " ".join(
        str(presentation_provider or "Not configured").split()
    )
    presentation = dict(integrations.get("presentation", {}) or {})

    previous_provider = " ".join(
        str(
            presentation.get(
                "provider",
                ""
            )
            or
            ""
        ).split()
    )

    previous_source = str(
        presentation.get(
            "settings_source",
            ""
        )
        or
        ""
    ).strip().lower()

    if (
        previous_provider
        and
        previous_provider != presentation_name
        and
        previous_source == "profile"
    ):
        # Changing provider in the general wizard should never silently
        # activate a different live adapter. Return it to safe LEGACY mode;
        # Presentation Setup can explicitly enable PROFILE after testing.
        presentation_source = "legacy"
    elif previous_source in {
        "legacy",
        "profile",
    }:
        presentation_source = previous_source
    else:
        presentation_source = "profile_metadata"

    presentation.update(
        {
            "enabled": presentation_name.lower()
            not in {"", "none", "not configured"},
            "provider": presentation_name,
            "settings_source": presentation_source,
        }
    )
    integrations["presentation"] = presentation

    camera_name = " ".join(
        str(camera_provider or "Not configured").split()
    )
    camera = dict(integrations.get("camera", {}) or {})

    previous_camera_provider = " ".join(
        str(
            camera.get(
                "provider",
                ""
            )
            or
            ""
        ).split()
    )

    previous_camera_source = str(
        camera.get(
            "settings_source",
            ""
        )
        or
        ""
    ).strip().lower()

    if (
        previous_camera_provider
        and
        previous_camera_provider != camera_name
        and
        previous_camera_source == "profile"
    ):
        camera_source = "legacy"
    elif previous_camera_source in {
        "legacy",
        "profile",
    }:
        camera_source = previous_camera_source
    else:
        camera_source = "profile_metadata"

    camera.update(
        {
            "enabled": camera_name.lower()
            not in {"", "none", "fixed camera", "not configured"},
            "provider": camera_name,
            "settings_source": camera_source,
        }
    )
    integrations["camera"] = camera

    sermon_name = " ".join(
        str(sermon_source_provider or "Manual").split()
    )
    sermon = dict(integrations.get("sermon_source", {}) or {})

    previous_sermon_provider = " ".join(
        str(
            sermon.get(
                "provider",
                ""
            )
            or
            ""
        ).split()
    )

    previous_sermon_source = str(
        sermon.get(
            "settings_source",
            ""
        )
        or
        ""
    ).strip().lower()

    if (
        previous_sermon_provider
        and
        previous_sermon_provider != sermon_name
        and
        previous_sermon_source == "profile"
    ):
        sermon_settings_source = "legacy"
    elif previous_sermon_source in {
        "legacy",
        "profile",
    }:
        sermon_settings_source = previous_sermon_source
    else:
        sermon_settings_source = "profile_metadata"

    sermon.update(
        {
            "enabled": True,
            "provider": sermon_name,
            "settings_source": sermon_settings_source,
        }
    )
    integrations["sermon_source"] = sermon

    profile["integrations"] = integrations

    status = get_profile_setup_status(profile)
    completed = set(status["completed_steps"])
    completed.update(
        {
            "church",
            "presentation",
            "camera",
            "sermon_source",
        }
    )

    profile["setup"] = {
        "wizard_completed": bool(wizard_completed),
        "completed_steps": [
            step for step in SETUP_STEPS if step in completed
        ],
        "last_completed_at": (
            datetime.now().astimezone().isoformat()
            if wizard_completed
            else
            ""
        ),
    }

    return save_active_profile(profile)


def get_profile_presentation_settings(
    profile=None
):
    """
    Normalize the presentation integration block.

    v1.6 supports a true PROFILE-backed adapter for WorshipTools Presenter.
    Other providers can be selected as metadata now, but remain on LEGACY
    until their adapter is implemented.
    """
    if profile is None:
        profile = load_active_profile()

    integrations = profile.get(
        "integrations",
        {}
    )

    if not isinstance(
        integrations,
        dict
    ):
        integrations = {}

    raw = integrations.get(
        "presentation",
        {}
    )

    if not isinstance(
        raw,
        dict
    ):
        raw = {}

    raw_source = str(
        raw.get(
            "settings_source",
            "legacy"
        )
        or
        "legacy"
    ).strip().lower()

    if raw_source in {
        "profile",
        "profile_adapter",
    }:
        source = "profile"
    else:
        source = "legacy"

    provider = " ".join(
        str(
            raw.get(
                "provider",
                "WorshipTools Presenter"
            )
            or
            "WorshipTools Presenter"
        ).split()
    )

    connection = raw.get(
        "connection",
        {}
    )

    if not isinstance(
        connection,
        dict
    ):
        connection = {}

    return {
        "enabled": bool(
            raw.get(
                "enabled",
                True
            )
        ),
        "provider": provider,
        "settings_source": source,
        "host": " ".join(
            str(
                connection.get(
                    "host",
                    raw.get(
                        "host",
                        "127.0.0.1"
                    )
                )
                or
                "127.0.0.1"
            ).split()
        ),
        "port": int(
            connection.get(
                "port",
                raw.get(
                    "port",
                    50001
                )
            )
            or
            50001
        ),
    }


def save_active_presentation_settings(
    *,
    settings_source,
    provider,
    host="127.0.0.1",
    port=50001
):
    """
    Save the active profile's presentation adapter choice.

    PROFILE mode is intentionally enabled only for the first proven adapter:
    WorshipTools Presenter. Other providers remain selectable metadata but
    cannot be activated live until their adapter exists.
    """
    source = str(
        settings_source
        or
        "legacy"
    ).strip().lower()

    if source not in {
        "legacy",
        "profile",
    }:
        raise ValueError(
            "Presentation configuration source must be LEGACY or PROFILE."
        )

    provider_clean = " ".join(
        str(
            provider
            or
            "Not configured"
        ).split()
    )

    if source == "profile":
        if provider_clean not in {
            "WorshipTools Presenter",
            "ProPresenter",
        }:
            raise ValueError(
                (
                    "PROFILE presentation control is currently available for "
                    "WorshipTools Presenter and ProPresenter. Keep this provider "
                    "on LEGACY until its adapter is implemented."
                )
            )

    host_clean = " ".join(
        str(
            host
            or
            "127.0.0.1"
        ).split()
    )

    try:
        port_clean = int(
            port
        )
    except Exception:
        raise ValueError(
            "ProPresenter API port must be a number."
        )

    if not (
        1
        <=
        port_clean
        <=
        65535
    ):
        raise ValueError(
            "ProPresenter API port must be between 1 and 65535."
        )

    profile = dict(
        load_active_profile()
    )

    integrations = dict(
        profile.get(
            "integrations",
            {}
        )
        or
        {}
    )

    presentation = dict(
        integrations.get(
            "presentation",
            {}
        )
        or
        {}
    )

    presentation.update(
        {
            "enabled": (
                provider_clean.lower()
                not in {
                    "",
                    "none",
                    "not configured",
                }
            ),
            "provider": provider_clean,
            "settings_source": source,
            "connection": {
                "host": host_clean,
                "port": port_clean,
            },
        }
    )

    integrations[
        "presentation"
    ] = presentation

    profile[
        "integrations"
    ] = integrations

    return save_active_profile(
        profile
    )


def get_profile_capabilities(
    profile=None
):
    """
    Volunteer-control visibility for the active church profile.

    Profiles created before v1.8 default to LEGACY/full UI. This guarantees
    installing v1.8 cannot remove controls from an existing working church.
    """
    if profile is None:
        profile = load_active_profile()

    raw = profile.get(
        "capabilities",
        {}
    )

    if not isinstance(
        raw,
        dict
    ):
        raw = {}

    source = str(
        raw.get(
            "settings_source",
            "legacy"
        )
        or
        "legacy"
    ).strip().lower()

    if source not in {
        "legacy",
        "profile",
    }:
        source = "legacy"

    defaults = {
        "recording": True,
        "streaming": True,
        "audio_mute": True,
        "scripture": True,
        "sermon_controls": True,
        "camera_controls": True,
    }

    result = {
        "settings_source": source,
    }

    for key, default in defaults.items():
        result[
            key
        ] = bool(
            raw.get(
                key,
                default
            )
        )

    if source == "legacy":
        for key in defaults:
            result[
                key
            ] = True

    return result


def save_active_capabilities(
    *,
    settings_source,
    recording=True,
    streaming=True,
    audio_mute=True,
    scripture=True,
    sermon_controls=True,
    camera_controls=True
):
    source = str(
        settings_source
        or
        "legacy"
    ).strip().lower()

    if source not in {
        "legacy",
        "profile",
    }:
        raise ValueError(
            "Volunteer Controls source must be LEGACY or PROFILE."
        )

    profile = dict(
        load_active_profile()
    )

    profile[
        "capabilities"
    ] = {
        "settings_source": source,
        "recording": bool(
            recording
        ),
        "streaming": bool(
            streaming
        ),
        "audio_mute": bool(
            audio_mute
        ),
        "scripture": bool(
            scripture
        ),
        "sermon_controls": bool(
            sermon_controls
        ),
        "camera_controls": bool(
            camera_controls
        ),
    }

    return save_active_profile(
        profile
    )


def get_profile_camera_settings(
    profile=None
):
    """
    Normalize the active profile's camera integration.

    Older profiles remain LEGACY until Camera Setup explicitly saves PROFILE.
    """
    if profile is None:
        profile = load_active_profile()

    integrations = profile.get(
        "integrations",
        {}
    )

    if not isinstance(
        integrations,
        dict
    ):
        integrations = {}

    raw = integrations.get(
        "camera",
        {}
    )

    if not isinstance(
        raw,
        dict
    ):
        raw = {}

    raw_source = str(
        raw.get(
            "settings_source",
            "legacy"
        )
        or
        "legacy"
    ).strip().lower()

    source = (
        "profile"
        if raw_source == "profile"
        else
        "legacy"
    )

    provider = " ".join(
        str(
            raw.get(
                "provider",
                "PTZOptics / HTTP-CGI"
            )
            or
            "PTZOptics / HTTP-CGI"
        ).split()
    )

    connection = raw.get(
        "connection",
        {}
    )

    if not isinstance(
        connection,
        dict
    ):
        connection = {}

    presets = raw.get(
        "presets",
        {}
    )

    if not isinstance(
        presets,
        dict
    ):
        presets = {}

    def _safe_int(
        value,
        default
    ):
        try:
            return int(
                value
            )
        except Exception:
            return int(
                default
            )

    return {
        "enabled": bool(
            raw.get(
                "enabled",
                provider.lower()
                not in {
                    "none",
                    "fixed camera",
                    "not configured",
                }
            )
        ),
        "provider": provider,
        "settings_source": source,
        "host": " ".join(
            str(
                connection.get(
                    "host",
                    raw.get(
                        "host",
                        ""
                    )
                )
                or
                ""
            ).split()
        ),
        "port": _safe_int(
            connection.get(
                "port",
                raw.get(
                    "port",
                    80
                )
            ),
            80,
        ),
        "worship_preset": _safe_int(
            presets.get(
                "worship",
                raw.get(
                    "worship_preset",
                    1
                )
            ),
            1,
        ),
        "pastor_preset": _safe_int(
            presets.get(
                "pastor",
                raw.get(
                    "pastor_preset",
                    2
                )
            ),
            2,
        ),
        "startup_preset": _safe_int(
            presets.get(
                "startup",
                raw.get(
                    "startup_preset",
                    presets.get(
                        "pastor",
                        2
                    )
                )
            ),
            2,
        ),
        "auto_recall_on_start": bool(
            raw.get(
                "auto_recall_on_start",
                True
            )
        ),
    }


def save_active_camera_settings(
    *,
    settings_source,
    provider,
    host="",
    port=80,
    worship_preset=1,
    pastor_preset=2,
    startup_preset=None,
    auto_recall_on_start=True
):
    source = str(
        settings_source
        or
        "legacy"
    ).strip().lower()

    if source not in {
        "legacy",
        "profile",
    }:
        raise ValueError(
            "Camera configuration source must be LEGACY or PROFILE."
        )

    provider_clean = " ".join(
        str(
            provider
            or
            "Not configured"
        ).split()
    )

    supported_profile_providers = {
        "PTZOptics / HTTP-CGI",
        "Fixed camera",
        "None",
    }

    if (
        source == "profile"
        and
        provider_clean not in supported_profile_providers
    ):
        raise ValueError(
            (
                "PROFILE camera control is currently available for "
                "PTZOptics / HTTP-CGI, Fixed camera, and None. "
                "Keep this provider on LEGACY until its adapter is implemented."
            )
        )

    host_clean = " ".join(
        str(
            host
            or
            ""
        ).split()
    )

    try:
        port_clean = int(
            port
        )
    except Exception:
        raise ValueError(
            "Camera port must be a number."
        )

    if not (
        1
        <=
        port_clean
        <=
        65535
    ):
        raise ValueError(
            "Camera port must be between 1 and 65535."
        )

    try:
        worship_clean = int(
            worship_preset
        )
        pastor_clean = int(
            pastor_preset
        )

        if startup_preset is None:
            startup_clean = pastor_clean
        else:
            startup_clean = int(
                startup_preset
            )

    except Exception:
        raise ValueError(
            "Camera presets must be whole numbers."
        )

    if source == "profile" and provider_clean == "PTZOptics / HTTP-CGI":
        if not host_clean:
            raise ValueError(
                "PTZOptics PROFILE mode needs a camera IP / host."
            )

    enabled = provider_clean.lower() not in {
        "",
        "none",
        "fixed camera",
        "not configured",
    }

    profile = dict(
        load_active_profile()
    )

    integrations = dict(
        profile.get(
            "integrations",
            {}
        )
        or
        {}
    )

    camera = dict(
        integrations.get(
            "camera",
            {}
        )
        or
        {}
    )

    camera.update(
        {
            "enabled": enabled,
            "provider": provider_clean,
            "settings_source": source,
            "connection": {
                "host": host_clean,
                "port": port_clean,
            },
            "presets": {
                "worship": worship_clean,
                "pastor": pastor_clean,
                "startup": startup_clean,
            },
            "auto_recall_on_start": bool(
                auto_recall_on_start
            ),
        }
    )

    integrations[
        "camera"
    ] = camera

    profile[
        "integrations"
    ] = integrations

    return save_active_profile(
        profile
    )


def get_profile_audio_settings(
    profile=None
):
    """
    Normalize the active profile's audio-control integration.

    v2.1 controls the volunteer MUTE/UNMUTE action through selected OBS inputs.
    The existing live level-meter/audio-sanity process remains on its proven
    legacy path for now.
    """
    if profile is None:
        profile = load_active_profile()

    integrations = profile.get(
        "integrations",
        {}
    )

    if not isinstance(
        integrations,
        dict
    ):
        integrations = {}

    raw = integrations.get(
        "audio",
        {}
    )

    if not isinstance(
        raw,
        dict
    ):
        raw = {}

    raw_source = str(
        raw.get(
            "settings_source",
            "legacy"
        )
        or
        "legacy"
    ).strip().lower()

    source = (
        "profile"
        if raw_source == "profile"
        else
        "legacy"
    )

    provider = " ".join(
        str(
            raw.get(
                "provider",
                "OBS Audio Inputs"
            )
            or
            "OBS Audio Inputs"
        ).split()
    )

    mute_inputs = raw.get(
        "mute_inputs",
        []
    )

    if not isinstance(
        mute_inputs,
        list
    ):
        mute_inputs = []

    cleaned_inputs = []

    for item in mute_inputs:
        name = " ".join(
            str(
                item
                or
                ""
            ).split()
        )

        if (
            name
            and
            name not in cleaned_inputs
        ):
            cleaned_inputs.append(
                name
            )

    monitor = raw.get(
        "monitor",
        {}
    )

    if not isinstance(
        monitor,
        dict
    ):
        monitor = {}

    return {
        "enabled": bool(
            raw.get(
                "enabled",
                provider.lower()
                not in {
                    "none",
                    "not configured",
                }
            )
        ),
        "provider": provider,
        "settings_source": source,
        "mute_inputs": cleaned_inputs,
        "monitor_endpoint": " ".join(
            str(
                monitor.get(
                    "endpoint",
                    ""
                )
                or
                ""
            ).split()
        ),
        "monitor_label": " ".join(
            str(
                monitor.get(
                    "label",
                    "Audio Interface"
                )
                or
                "Audio Interface"
            ).split()
        ),
    }


def save_active_audio_settings(
    *,
    settings_source,
    provider,
    mute_inputs=None,
    monitor_endpoint="",
    monitor_label="Audio Interface"
):
    source = str(
        settings_source
        or
        "legacy"
    ).strip().lower()

    if source not in {
        "legacy",
        "profile",
    }:
        raise ValueError(
            "Audio configuration source must be LEGACY or PROFILE."
        )

    provider_clean = " ".join(
        str(
            provider
            or
            "Not configured"
        ).split()
    )

    if (
        source == "profile"
        and
        provider_clean not in {
            "OBS Audio Inputs",
            "None",
        }
    ):
        raise ValueError(
            (
                "PROFILE audio control is currently available for "
                "OBS Audio Inputs and None. Keep this provider on LEGACY "
                "until its adapter is implemented."
            )
        )

    if mute_inputs is None:
        mute_inputs = []

    if not isinstance(
        mute_inputs,
        (
            list,
            tuple,
            set,
        )
    ):
        raise ValueError(
            "Audio mute inputs must be a list of OBS input names."
        )

    cleaned_inputs = []

    for item in mute_inputs:
        name = " ".join(
            str(
                item
                or
                ""
            ).split()
        )

        if (
            name
            and
            name not in cleaned_inputs
        ):
            cleaned_inputs.append(
                name
            )

    if (
        source == "profile"
        and
        provider_clean == "OBS Audio Inputs"
        and
        not cleaned_inputs
    ):
        raise ValueError(
            "PROFILE + OBS Audio Inputs needs at least one mute input."
        )

    endpoint_clean = " ".join(
        str(
            monitor_endpoint
            or
            ""
        ).split()
    )

    label_clean = " ".join(
        str(
            monitor_label
            or
            "Audio Interface"
        ).split()
    )

    profile = dict(
        load_active_profile()
    )

    integrations = dict(
        profile.get(
            "integrations",
            {}
        )
        or
        {}
    )

    audio = dict(
        integrations.get(
            "audio",
            {}
        )
        or
        {}
    )

    audio.update(
        {
            "enabled": (
                provider_clean.lower()
                not in {
                    "",
                    "none",
                    "not configured",
                }
            ),
            "provider": provider_clean,
            "settings_source": source,
            "mute_inputs": cleaned_inputs,
            "monitor": {
                "endpoint": endpoint_clean,
                "label": label_clean,
            },
        }
    )

    integrations[
        "audio"
    ] = audio

    profile[
        "integrations"
    ] = integrations

    return save_active_profile(
        profile
    )


def get_profile_sermon_source_settings(
    profile=None
):
    """
    Normalize the active profile's sermon-information source.

    Older profiles remain LEGACY until Sermon Setup explicitly enables PROFILE.
    """
    if profile is None:
        profile = load_active_profile()

    integrations = profile.get(
        "integrations",
        {}
    )

    if not isinstance(
        integrations,
        dict
    ):
        integrations = {}

    raw = integrations.get(
        "sermon_source",
        {}
    )

    if not isinstance(
        raw,
        dict
    ):
        raw = {}

    raw_source = str(
        raw.get(
            "settings_source",
            "legacy"
        )
        or
        "legacy"
    ).strip().lower()

    source = (
        "profile"
        if raw_source == "profile"
        else
        "legacy"
    )

    provider = " ".join(
        str(
            raw.get(
                "provider",
                "Manual"
            )
            or
            "Manual"
        ).split()
    )

    manual_plan = raw.get(
        "manual_plan",
        {}
    )

    if not isinstance(
        manual_plan,
        dict
    ):
        manual_plan = {}

    imported_plan = raw.get(
        "imported_plan",
        {}
    )

    if not isinstance(
        imported_plan,
        dict
    ):
        imported_plan = {}

    email = raw.get(
        "email",
        {}
    )

    if not isinstance(
        email,
        dict
    ):
        email = {}

    return {
        "enabled": bool(
            raw.get(
                "enabled",
                True
            )
        ),
        "provider": provider,
        "settings_source": source,
        "manual_plan": manual_plan,
        "imported_plan": imported_plan,
        "email_sender": " ".join(
            str(
                email.get(
                    "sender",
                    ""
                )
                or
                ""
            ).split()
        ),
        "email_auto_refresh": bool(
            email.get(
                "auto_refresh_on_start",
                True
            )
        ),
        "last_import_name": " ".join(
            str(
                raw.get(
                    "last_import_name",
                    ""
                )
                or
                ""
            ).split()
        ),
    }


def save_active_sermon_source_settings(
    *,
    settings_source,
    provider,
    manual_plan=None,
    imported_plan=None,
    email_sender="",
    email_auto_refresh=True,
    last_import_name=""
):
    source = str(
        settings_source
        or
        "legacy"
    ).strip().lower()

    if source not in {
        "legacy",
        "profile",
    }:
        raise ValueError(
            "Sermon source must be LEGACY or PROFILE."
        )

    provider_clean = " ".join(
        str(
            provider
            or
            "Manual"
        ).split()
    )

    supported_profile_providers = {
        "Manual",
        "Pastor Email",
        "Imported File",
    }

    if (
        source == "profile"
        and
        provider_clean not in supported_profile_providers
    ):
        raise ValueError(
            (
                "PROFILE sermon source is currently available for Manual, "
                "Pastor Email, and Imported File. Planning Software and Other "
                "remain on LEGACY until their source adapters are implemented."
            )
        )

    if manual_plan is None:
        manual_plan = {}

    if imported_plan is None:
        imported_plan = {}

    if not isinstance(
        manual_plan,
        dict
    ):
        raise ValueError(
            "Manual sermon plan must be a dictionary/object."
        )

    if not isinstance(
        imported_plan,
        dict
    ):
        raise ValueError(
            "Imported sermon plan must be a dictionary/object."
        )

    profile = dict(
        load_active_profile()
    )

    integrations = dict(
        profile.get(
            "integrations",
            {}
        )
        or
        {}
    )

    sermon = dict(
        integrations.get(
            "sermon_source",
            {}
        )
        or
        {}
    )

    sermon.update(
        {
            "enabled": True,
            "provider": provider_clean,
            "settings_source": source,
            "manual_plan": dict(
                manual_plan
            ),
            "imported_plan": dict(
                imported_plan
            ),
            "email": {
                "sender": " ".join(
                    str(
                        email_sender
                        or
                        ""
                    ).split()
                ),
                "auto_refresh_on_start": bool(
                    email_auto_refresh
                ),
            },
            "last_import_name": " ".join(
                str(
                    last_import_name
                    or
                    ""
                ).split()
            ),
        }
    )

    integrations[
        "sermon_source"
    ] = sermon

    profile[
        "integrations"
    ] = integrations

    return save_active_profile(
        profile
    )


def profile_display_name():
    try:
        profile = load_active_profile()

        return " ".join(
            str(
                profile.get(
                    "profile_name",
                    "Church Profile"
                )
            ).split()
        )

    except Exception:
        return "Church Profile"


def export_active_profile(
    destination
):
    """
    Export the active portable profile.

    The profile format itself contains no credentials. We nevertheless
    create a fresh export object instead of copying arbitrary runtime
    files, ensuring .env, Gmail tokens, OBS passwords, etc. cannot be
    swept into the export accidentally.
    """
    profile = dict(
        load_active_profile()
    )

    profile[
        "exported_at"
    ] = datetime.now().astimezone().isoformat()

    profile[
        "secrets"
    ] = {
        "included": False,
        "notes": (
            "No passwords, OAuth tokens, API credentials, or .env values "
            "are contained in this .sssprofile file."
        ),
    }

    destination = Path(
        destination
    )

    if destination.suffix.lower() != ".sssprofile":
        destination = destination.with_suffix(
            ".sssprofile"
        )

    _write_json_atomic(
        destination,
        profile,
    )

    return destination


def import_profile(
    source
):
    source = Path(
        source
    )

    profile = json.loads(
        source.read_text(
            encoding="utf-8"
        )
    )

    original_schema = profile_schema_version(
        profile
    )

    profile, migration_report = _prepare_profile_data(
        profile
    )

    profile = dict(
        profile
    )

    profile.pop(
        "exported_at",
        None,
    )

    profile[
        "updated_at"
    ] = datetime.now().astimezone().isoformat()

    profile_id = (
        profile.get(
            "profile_id"
        )
        or
        _safe_slug(
            profile[
                "profile_name"
            ]
        ).lower()
    )

    profile[
        "profile_id"
    ] = profile_id

    destination = _profile_path_from_id(
        profile_id
    )

    _write_json_atomic(
        destination,
        profile,
    )

    _set_active_profile_path(
        destination
    )

    if migration_report.get(
        "changed"
    ):
        try:
            from sss_event_history import record_event

            record_event(
                (
                    "Imported profile upgraded during import: "
                    +
                    str(
                        profile.get(
                            "profile_name",
                            profile_id
                        )
                    )
                    +
                    " — schema "
                    +
                    str(
                        original_schema
                    )
                    +
                    " -> "
                    +
                    str(
                        PROFILE_SCHEMA_VERSION
                    )
                    +
                    "."
                ),
                category="SYSTEM",
                level="ACTION",
                source="PROFILE MIGRATION",
            )
        except Exception:
            pass

    return profile


def set_windows_app_user_model_id():
    """
    Give the current Python build a real SSS Windows application identity.

    This is preparation for the future SundayServiceSystem.exe. It helps
    Windows group SSS windows consistently now, while leaving the current
    launch method untouched.
    """
    if sys.platform != "win32":
        return False

    try:
        shell32 = ctypes.windll.shell32

        result = shell32.SetCurrentProcessExplicitAppUserModelID(
            ctypes.c_wchar_p(
                APP_ID
            )
        )

        return result == 0

    except Exception:
        return False
