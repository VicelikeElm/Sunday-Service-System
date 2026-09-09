from sss_obs_profile import connect_local_obs
from sss_profile import (
    get_profile_audio_settings,
    load_active_profile,
)


AUDIO_ADAPTERS = {
    "OBS Audio Inputs": {
        "live_supported": True,
        "description": (
            "Uses OBS WebSocket input mute state for the selected program-audio inputs."
        ),
    },
    "TASCAM Interface": {
        "live_supported": False,
        "description": (
            "Direct TASCAM control adapter is planned. Existing Windows/OBS audio remains available through LEGACY."
        ),
    },
    "Windows Audio Endpoint": {
        "live_supported": False,
        "description": (
            "Windows endpoint monitoring is recognized, but direct mute control is not enabled yet."
        ),
    },
    "None": {
        "live_supported": True,
        "description": (
            "This profile does not expose a volunteer program-audio mute control."
        ),
    },
    "Not configured": {
        "live_supported": False,
        "description": (
            "Audio control has not been configured."
        ),
    },
}


def adapter_info(
    provider
):
    provider = str(
        provider
        or
        "Not configured"
    ).strip()

    info = dict(
        AUDIO_ADAPTERS.get(
            provider,
            {
                "live_supported": False,
                "description": "Unknown audio provider.",
            },
        )
    )

    info["provider"] = provider
    return info


def _input_name(
    item
):
    if isinstance(
        item,
        dict
    ):
        for key in (
            "inputName",
            "input_name",
            "name",
        ):
            value = item.get(
                key
            )

            if value:
                return " ".join(
                    str(
                        value
                    ).split()
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
                    return " ".join(
                        str(
                            value
                        ).split()
                    )
            except Exception:
                pass

    return ""


def discover_obs_audio_inputs():
    client, _config, host, port = connect_local_obs(
        timeout=5
    )

    response = client.get_input_list()

    raw_inputs = getattr(
        response,
        "inputs",
        []
    ) or []

    names = []

    for item in raw_inputs:
        name = _input_name(
            item
        )

        if (
            name
            and
            name not in names
        ):
            names.append(
                name
            )

    return {
        "host": str(
            host
        ),
        "port": int(
            port
        ),
        "inputs": names,
    }


def active_audio_settings():
    return get_profile_audio_settings(
        load_active_profile()
    )


def validate_obs_audio_inputs(
    names
):
    cleaned = []

    for item in names or []:
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
            name not in cleaned
        ):
            cleaned.append(
                name
            )

    if not cleaned:
        return (
            False,
            "No OBS audio inputs selected.",
        )

    try:
        data = discover_obs_audio_inputs()

    except Exception as exc:
        return (
            False,
            str(
                exc
            ),
        )

    available = set(
        data.get(
            "inputs",
            []
        )
    )

    missing = [
        name
        for name in cleaned
        if name not in available
    ]

    if missing:
        return (
            False,
            (
                "OBS audio input(s) missing: "
                +
                ", ".join(
                    missing
                )
            ),
        )

    return (
        True,
        (
            "OBS audio ready — "
            +
            ", ".join(
                cleaned
            )
        ),
    )


def profile_audio_ready():
    settings = active_audio_settings()

    if settings.get(
        "settings_source"
    ) != "profile":
        return (
            True,
            "LEGACY audio control",
        )

    provider = settings.get(
        "provider",
        "Not configured"
    )

    info = adapter_info(
        provider
    )

    if not info.get(
        "live_supported",
        False
    ):
        return (
            False,
            info.get(
                "description",
                ""
            ),
        )

    if provider == "None":
        return (
            True,
            "No volunteer audio control configured",
        )

    if provider != "OBS Audio Inputs":
        return (
            False,
            "Audio adapter is not ready.",
        )

    return validate_obs_audio_inputs(
        settings.get(
            "mute_inputs",
            []
        )
    )


def get_profile_mute_states():
    settings = active_audio_settings()

    if (
        settings.get(
            "settings_source"
        )
        !=
        "profile"
        or
        settings.get(
            "provider"
        )
        !=
        "OBS Audio Inputs"
    ):
        raise RuntimeError(
            "OBS Audio Inputs profile adapter is not active."
        )

    names = list(
        settings.get(
            "mute_inputs",
            []
        )
        or
        []
    )

    if not names:
        raise RuntimeError(
            "No OBS audio inputs are selected."
        )

    client, _config, _host, _port = connect_local_obs(
        timeout=4
    )

    states = {}

    for name in names:
        response = client.get_input_mute(
            name
        )

        states[
            name
        ] = bool(
            getattr(
                response,
                "input_muted",
                getattr(
                    response,
                    "inputMuted",
                    False
                )
            )
        )

    return states


def set_profile_muted(
    muted
):
    settings = active_audio_settings()

    if (
        settings.get(
            "settings_source"
        )
        !=
        "profile"
        or
        settings.get(
            "provider"
        )
        !=
        "OBS Audio Inputs"
    ):
        raise RuntimeError(
            "OBS Audio Inputs profile adapter is not active."
        )

    names = list(
        settings.get(
            "mute_inputs",
            []
        )
        or
        []
    )

    if not names:
        raise RuntimeError(
            "No OBS audio inputs are selected."
        )

    client, _config, _host, _port = connect_local_obs(
        timeout=4
    )

    failures = []

    for name in names:
        try:
            client.set_input_mute(
                name,
                bool(
                    muted
                )
            )
        except Exception as exc:
            failures.append(
                (
                    name,
                    str(
                        exc
                    ),
                )
            )

    if failures:
        raise RuntimeError(
            (
                "Mute failed for: "
                +
                "; ".join(
                    (
                        name
                        +
                        " ("
                        +
                        detail
                        +
                        ")"
                    )
                    for name, detail in failures
                )
            )
        )

    return {
        "ok": True,
        "muted": bool(
            muted
        ),
        "inputs": names,
    }


def toggle_profile_mute():
    states = get_profile_mute_states()

    all_muted = bool(
        states
    ) and all(
        states.values()
    )

    new_state = not all_muted

    result = set_profile_muted(
        new_state
    )

    result[
        "previous_states"
    ] = states

    return result
