import copy
import datetime


CURRENT_PROFILE_SCHEMA_VERSION = 7
MIN_SUPPORTED_PROFILE_SCHEMA_VERSION = 1


def _now_iso():
    return datetime.datetime.now().astimezone().isoformat()


def profile_schema_version(profile):
    if not isinstance(profile, dict):
        raise ValueError(
            "Profile file is not a JSON object."
        )

    raw = profile.get(
        "schema_version",
        1,
    )

    try:
        version = int(
            raw
            or
            1
        )
    except Exception as exc:
        raise ValueError(
            "Profile schema_version is not a number."
        ) from exc

    return version


def _ensure_dict(parent, key):
    value = parent.get(
        key
    )

    if not isinstance(
        value,
        dict
    ):
        value = {}
        parent[
            key
        ] = value

    return value


def _ensure_list(parent, key):
    value = parent.get(
        key
    )

    if not isinstance(
        value,
        list
    ):
        value = []
        parent[
            key
        ] = value

    return value


def _source_or_legacy(value):
    source = str(
        value
        or
        "legacy"
    ).strip().lower()

    if source in {
        "profile",
    }:
        return "profile"

    if source in {
        "existing_configuration",
        "legacy_existing_configuration",
        "current",
        "legacy",
    }:
        return "legacy"

    # Old profiles sometimes used metadata/not-configured values. Keep them
    # non-live rather than silently activating PROFILE behavior.
    return source or "legacy"


def _migrate_1_to_2(profile):
    """
    v2 introduced first-run setup state and capability-based volunteer UI.

    Existing v1 profiles MUST retain the complete volunteer screen. Therefore
    their capability source defaults to LEGACY, even though newly-created
    current-schema profiles may choose PROFILE later.
    """
    setup = _ensure_dict(
        profile,
        "setup",
    )

    setup.setdefault(
        "wizard_completed",
        False,
    )
    _ensure_list(
        setup,
        "completed_steps",
    )
    setup.setdefault(
        "last_completed_at",
        "",
    )

    capabilities = _ensure_dict(
        profile,
        "capabilities",
    )

    capabilities.setdefault(
        "settings_source",
        "legacy",
    )

    for key in (
        "recording",
        "streaming",
        "audio_mute",
        "scripture",
        "sermon_controls",
        "camera_controls",
    ):
        capabilities.setdefault(
            key,
            True,
        )

    profile[
        "schema_version"
    ] = 2

    return profile


def _migrate_2_to_3(profile):
    """
    v3 formalized Presentation adapter connection settings.
    """
    integrations = _ensure_dict(
        profile,
        "integrations",
    )

    presentation = _ensure_dict(
        integrations,
        "presentation",
    )

    presentation.setdefault(
        "enabled",
        True,
    )
    presentation.setdefault(
        "provider",
        "WorshipTools Presenter",
    )

    presentation[
        "settings_source"
    ] = _source_or_legacy(
        presentation.get(
            "settings_source",
            "legacy",
        )
    )

    connection = _ensure_dict(
        presentation,
        "connection",
    )

    connection.setdefault(
        "host",
        "127.0.0.1",
    )
    connection.setdefault(
        "port",
        50001,
    )

    profile[
        "schema_version"
    ] = 3

    return profile


def _migrate_3_to_4(profile):
    """
    v4 formalized Camera adapter connection/preset fields.

    Legacy PTZ machine configuration remains authoritative unless the profile
    was already explicitly using PROFILE.
    """
    integrations = _ensure_dict(
        profile,
        "integrations",
    )

    camera = _ensure_dict(
        integrations,
        "camera",
    )

    camera.setdefault(
        "enabled",
        True,
    )
    camera.setdefault(
        "provider",
        "PTZOptics / HTTP-CGI",
    )

    camera[
        "settings_source"
    ] = _source_or_legacy(
        camera.get(
            "settings_source",
            "legacy",
        )
    )

    connection = _ensure_dict(
        camera,
        "connection",
    )

    connection.setdefault(
        "host",
        "",
    )
    connection.setdefault(
        "port",
        80,
    )

    presets = _ensure_dict(
        camera,
        "presets",
    )

    presets.setdefault(
        "worship",
        1,
    )
    presets.setdefault(
        "pastor",
        2,
    )
    presets.setdefault(
        "startup",
        presets.get(
            "pastor",
            2,
        ),
    )

    camera.setdefault(
        "auto_recall_on_start",
        True,
    )

    profile[
        "schema_version"
    ] = 4

    return profile


def _migrate_4_to_5(profile):
    """
    v5 formalized Audio adapter settings.
    """
    integrations = _ensure_dict(
        profile,
        "integrations",
    )

    audio = _ensure_dict(
        integrations,
        "audio",
    )

    audio.setdefault(
        "enabled",
        True,
    )
    audio.setdefault(
        "provider",
        "OBS Audio Inputs",
    )

    audio[
        "settings_source"
    ] = _source_or_legacy(
        audio.get(
            "settings_source",
            "legacy",
        )
    )

    _ensure_list(
        audio,
        "mute_inputs",
    )

    monitor = _ensure_dict(
        audio,
        "monitor",
    )

    monitor.setdefault(
        "endpoint",
        "",
    )
    monitor.setdefault(
        "label",
        "Audio Interface",
    )

    profile[
        "schema_version"
    ] = 5

    return profile


def _migrate_5_to_6(profile):
    """
    v6 formalized Sermon Source adapter data and migration metadata.
    """
    integrations = _ensure_dict(
        profile,
        "integrations",
    )

    sermon = _ensure_dict(
        integrations,
        "sermon_source",
    )

    sermon.setdefault(
        "enabled",
        True,
    )
    sermon.setdefault(
        "provider",
        "Manual",
    )

    sermon[
        "settings_source"
    ] = _source_or_legacy(
        sermon.get(
            "settings_source",
            "legacy",
        )
    )

    _ensure_dict(
        sermon,
        "manual_plan",
    )
    _ensure_dict(
        sermon,
        "imported_plan",
    )

    email = _ensure_dict(
        sermon,
        "email",
    )

    email.setdefault(
        "sender",
        "",
    )
    email.setdefault(
        "auto_refresh_on_start",
        True,
    )

    sermon.setdefault(
        "last_import_name",
        "",
    )

    migration = _ensure_dict(
        profile,
        "migration",
    )

    migration.setdefault(
        "history",
        [],
    )
    migration.setdefault(
        "last_migrated_at",
        "",
    )
    migration.setdefault(
        "last_migrated_from",
        None,
    )
    migration.setdefault(
        "last_migrated_to",
        None,
    )

    profile[
        "schema_version"
    ] = 6

    return profile


def _migrate_6_to_7(profile):
    """
    v7 formalized local protected-secret metadata.

    No secret values are ever inserted into the portable profile. This block
    only records which local credential provider SSS prefers.
    """
    security = _ensure_dict(
        profile,
        "security",
    )

    security.setdefault(
        "credential_provider",
        "Windows Credential Manager",
    )
    security.setdefault(
        "secrets_portable",
        False,
    )

    obs_secret = _ensure_dict(
        security,
        "obs_websocket_password",
    )

    obs_secret.setdefault(
        "storage",
        "local_vault_preferred",
    )
    obs_secret.setdefault(
        "portable",
        False,
    )

    oauth = _ensure_dict(
        security,
        "oauth",
    )

    oauth.setdefault(
        "gmail",
        "legacy_local_file",
    )
    oauth.setdefault(
        "youtube",
        "legacy_local_file",
    )

    profile[
        "schema_version"
    ] = 7

    return profile


MIGRATIONS = {
    1: _migrate_1_to_2,
    2: _migrate_2_to_3,
    3: _migrate_3_to_4,
    4: _migrate_4_to_5,
    5: _migrate_5_to_6,
    6: _migrate_6_to_7,
}


def migrate_profile_dict(profile):
    """
    Return:
      migrated_profile, migration_report

    This function is pure with respect to disk. Unknown fields are preserved.
    It never changes LEGACY to PROFILE.
    """
    original = copy.deepcopy(
        profile
    )

    version = profile_schema_version(
        original
    )

    if version > CURRENT_PROFILE_SCHEMA_VERSION:
        raise ValueError(
            (
                "This profile was created by a newer Sunday Service System "
                "profile format (schema "
                +
                str(
                    version
                )
                +
                "). This SSS build supports up to schema "
                +
                str(
                    CURRENT_PROFILE_SCHEMA_VERSION
                )
                +
                "."
            )
        )

    if version < MIN_SUPPORTED_PROFILE_SCHEMA_VERSION:
        raise ValueError(
            (
                "Unsupported old SSS profile schema "
                +
                str(
                    version
                )
                +
                "."
            )
        )

    migrated = copy.deepcopy(
        original
    )

    from_version = version
    applied = []

    while version < CURRENT_PROFILE_SCHEMA_VERSION:
        migration = MIGRATIONS.get(
            version
        )

        if migration is None:
            raise RuntimeError(
                (
                    "No profile migration exists from schema "
                    +
                    str(
                        version
                    )
                    +
                    "."
                )
            )

        next_version = (
            version
            +
            1
        )

        migrated = migration(
            migrated
        )

        actual = profile_schema_version(
            migrated
        )

        if actual != next_version:
            raise RuntimeError(
                (
                    "Profile migration "
                    +
                    str(
                        version
                    )
                    +
                    " -> "
                    +
                    str(
                        next_version
                    )
                    +
                    " produced schema "
                    +
                    str(
                        actual
                    )
                    +
                    "."
                )
            )

        applied.append(
            {
                "from": version,
                "to": next_version,
            }
        )

        version = next_version

    report = {
        "changed": bool(
            applied
        ),
        "from_version": from_version,
        "to_version": version,
        "applied": applied,
    }

    if applied:
        migration = _ensure_dict(
            migrated,
            "migration",
        )

        history = migration.get(
            "history",
            []
        )

        if not isinstance(
            history,
            list
        ):
            history = []

        migrated_at = _now_iso()

        history.append(
            {
                "migrated_at": migrated_at,
                "from_version": from_version,
                "to_version": version,
                "steps": applied,
            }
        )

        # Keep migration history bounded so profiles do not grow forever.
        migration[
            "history"
        ] = history[
            -25:
        ]

        migration[
            "last_migrated_at"
        ] = migrated_at
        migration[
            "last_migrated_from"
        ] = from_version
        migration[
            "last_migrated_to"
        ] = version

    return (
        migrated,
        report,
    )
