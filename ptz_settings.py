import json
import re
from pathlib import Path

BASE = Path(r"C:\Church\SermonAI")
PTZ_CONFIG_FILE = BASE / "ptz_camera_config.json"

DEFAULTS = {
    "ptz_camera_enabled": True,
    "ptz_camera_ip": "",
    "ptz_camera_scheme": "http",
    "ptz_camera_http_port": "",
    "ptz_camera_username": "",
    "ptz_camera_password": "",
    "ptz_camera_timeout_seconds": 4,
    "ptz_auto_recall_on_sss_start": True,
    "ptz_startup_preset": 2,
    "ptz_worship_preset": 1,
    "ptz_pastor_preset": 2,
}


def read_json(path, default=None):
    if default is None:
        default = {}

    try:
        return json.loads(
            Path(path).read_text(
                encoding="utf-8-sig"
            )
        )
    except Exception:
        return default


def atomic_json(path, payload):
    path = Path(path)
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    temp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temp.replace(path)


def normalize_host(value):
    value = str(
        value
        or
        ""
    ).strip()

    value = re.sub(
        r"^https?://",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = value.strip(
        "/"
    )

    if "/" in value:
        value = value.split(
            "/",
            1
        )[0]

    return value.strip()


def valid_preset(value):
    try:
        number = int(
            value
        )
    except Exception:
        return False

    return (
        0 <= number <= 89
        or
        100 <= number <= 254
    )


def _ptz_keys_from_config(config):
    result = {}

    if not isinstance(
        config,
        dict,
    ):
        return result

    for key in DEFAULTS:
        if key in config:
            result[
                key
            ] = config[
                key
            ]

    return result


def load_ptz_settings(
    base_config=None,
    *,
    migrate=True
):
    settings = dict(
        DEFAULTS
    )

    legacy = _ptz_keys_from_config(
        base_config
    )

    settings.update(
        legacy
    )

    persistent = read_json(
        PTZ_CONFIG_FILE,
        {}
    )

    if persistent:
        settings.update(
            _ptz_keys_from_config(
                persistent
            )
        )

    settings[
        "ptz_camera_ip"
    ] = normalize_host(
        settings.get(
            "ptz_camera_ip",
            ""
        )
    )

    # One-time migration from sunday_config.json. Once migrated, future
    # SSS ZIP updates can safely replace sunday_config.json without losing
    # the camera address/presets.
    if (
        migrate
        and
        not PTZ_CONFIG_FILE.exists()
        and
        settings[
            "ptz_camera_ip"
        ]
    ):
        atomic_json(
            PTZ_CONFIG_FILE,
            settings
        )

    return settings


def save_ptz_settings(
    updates,
    base_config=None
):
    settings = load_ptz_settings(
        base_config,
        migrate=False,
    )

    updates = dict(
        updates
        or
        {}
    )

    if (
        "ptz_camera_ip"
        in
        updates
    ):
        updates[
            "ptz_camera_ip"
        ] = normalize_host(
            updates[
                "ptz_camera_ip"
            ]
        )

    for preset_key in (
        "ptz_worship_preset",
        "ptz_pastor_preset",
        "ptz_startup_preset",
    ):
        if preset_key in updates:
            if not valid_preset(
                updates[
                    preset_key
                ]
            ):
                raise ValueError(
                    f"Invalid PTZ preset: {updates[preset_key]}"
                )

            updates[
                preset_key
            ] = int(
                updates[
                    preset_key
                ]
            )

    settings.update(
        {
            key: value
            for key, value in updates.items()
            if key in DEFAULTS
        }
    )

    if not settings[
        "ptz_camera_ip"
    ]:
        raise ValueError(
            "PTZ camera IP/address cannot be blank."
        )

    # Pastor is the startup shot unless explicitly overridden.
    if (
        "ptz_pastor_preset"
        in
        updates
        and
        "ptz_startup_preset"
        not in
        updates
    ):
        settings[
            "ptz_startup_preset"
        ] = settings[
            "ptz_pastor_preset"
        ]

    atomic_json(
        PTZ_CONFIG_FILE,
        settings
    )

    return settings
