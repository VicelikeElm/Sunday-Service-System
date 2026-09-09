from sss_profile import (
    get_profile_presentation_settings,
    load_active_profile,
)

from sss_propresenter_api import (
    connection_test as propresenter_connection_test,
    trigger_next as propresenter_next,
    trigger_previous as propresenter_previous,
)

from sss_scripture_reading import (
    presenter_back,
    presenter_next,
)


ADAPTERS = {
    "WorshipTools Presenter": {
        "live_supported": True,
        "description": "Uses the church-proven Presenter MIDI mapping.",
    },
    "ProPresenter": {
        "live_supported": True,
        "description": "Uses ProPresenter's direct local/network HTTP API.",
    },
    "Bitfocus Companion": {
        "live_supported": False,
        "description": "Adapter slot reserved for Companion-triggered actions.",
    },
    "PowerPoint / Keyboard": {
        "live_supported": False,
        "description": "Adapter slot reserved for generic presentation keyboard control.",
    },
    "None": {
        "live_supported": False,
        "description": "No presentation software configured.",
    },
    "Not configured": {
        "live_supported": False,
        "description": "Presentation software has not been configured.",
    },
}


def adapter_info(provider):
    provider = str(provider or "Not configured").strip()

    info = dict(
        ADAPTERS.get(
            provider,
            {
                "live_supported": False,
                "description": "Unknown presentation provider.",
            },
        )
    )

    info["provider"] = provider
    return info


def active_presentation_settings():
    return get_profile_presentation_settings(
        load_active_profile()
    )


def presentation_control_mode():
    settings = active_presentation_settings()
    return (
        settings.get("settings_source", "legacy"),
        settings.get("provider", "WorshipTools Presenter"),
    )


def profile_adapter_ready():
    settings = active_presentation_settings()

    if settings.get("settings_source") != "profile":
        return True, "LEGACY presentation control"

    provider = settings.get("provider", "Not configured")
    info = adapter_info(provider)

    if not info.get("live_supported", False):
        return False, info.get("description", "")

    if provider == "ProPresenter":
        try:
            result = propresenter_connection_test(
                settings.get("host", "127.0.0.1"),
                settings.get("port", 50001),
                timeout=2.0,
            )

            return (
                bool(result.get("ok")),
                "ProPresenter API connected at "
                + str(result.get("base_url", "")),
            )
        except Exception as exc:
            return False, str(exc)

    return True, info.get("description", "")


def next_slide_profile():
    settings = active_presentation_settings()

    if settings.get("settings_source") != "profile":
        raise RuntimeError(
            "Presentation profile adapter is not active."
        )

    provider = settings.get("provider", "Not configured")

    if provider == "WorshipTools Presenter":
        return presenter_next(
            port_name="Presenter",
            channel=10,
            note=60,
            velocity=126,
        )

    if provider == "ProPresenter":
        return propresenter_next(
            settings.get("host", "127.0.0.1"),
            settings.get("port", 50001),
            timeout=3.0,
        )

    raise RuntimeError(
        "No live SSS adapter is implemented yet for "
        + str(provider)
        + "."
    )


def previous_slide_profile():
    settings = active_presentation_settings()

    if settings.get("settings_source") != "profile":
        raise RuntimeError(
            "Presentation profile adapter is not active."
        )

    provider = settings.get("provider", "Not configured")

    if provider == "WorshipTools Presenter":
        return presenter_back(
            port_name="Presenter",
            channel=10,
            note=62,
            velocity=126,
        )

    if provider == "ProPresenter":
        return propresenter_previous(
            settings.get("host", "127.0.0.1"),
            settings.get("port", 50001),
            timeout=3.0,
        )

    raise RuntimeError(
        "No live SSS adapter is implemented yet for "
        + str(provider)
        + "."
    )
