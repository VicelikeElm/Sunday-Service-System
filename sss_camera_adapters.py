import socket
import urllib.error
import urllib.request

from sss_profile import (
    get_profile_camera_settings,
    load_active_profile,
)


CAMERA_ADAPTERS = {
    "PTZOptics / HTTP-CGI": {
        "live_supported": True,
        "has_presets": True,
        "description": (
            "Uses PTZOptics HTTP-CGI preset recall."
        ),
    },
    "VISCA over IP": {
        "live_supported": False,
        "has_presets": True,
        "description": (
            "Portable VISCA over IP adapter is planned."
        ),
    },
    "Fixed camera": {
        "live_supported": True,
        "has_presets": False,
        "description": (
            "Fixed camera requires no SSS movement controls."
        ),
    },
    "None": {
        "live_supported": True,
        "has_presets": False,
        "description": (
            "No camera control is used by this profile."
        ),
    },
    "Not configured": {
        "live_supported": False,
        "has_presets": False,
        "description": (
            "Camera has not been configured."
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
        CAMERA_ADAPTERS.get(
            provider,
            {
                "live_supported": False,
                "has_presets": False,
                "description": (
                    "Unknown camera provider."
                ),
            },
        )
    )

    info[
        "provider"
    ] = provider

    return info


def _clean_host(
    host
):
    host = str(
        host
        or
        ""
    ).strip()

    if host.startswith(
        "http://"
    ):
        host = host[
            len(
                "http://"
            ):
        ]

    elif host.startswith(
        "https://"
    ):
        host = host[
            len(
                "https://"
            ):
        ]

    host = host.rstrip(
        "/"
    )

    return host


def _camera_base_url(
    host,
    port
):
    host = _clean_host(
        host
    )

    if not host:
        raise ValueError(
            "Camera host / IP is blank."
        )

    port = int(
        port
        or
        80
    )

    if port == 80:
        return (
            "http://"
            +
            host
        )

    return (
        "http://"
        +
        host
        +
        ":"
        +
        str(
            port
        )
    )


def check_tcp_connection(
    host,
    port=80,
    *,
    timeout=2.0
):
    host = _clean_host(
        host
    )

    if not host:
        raise ValueError(
            "Camera host / IP is blank."
        )

    port = int(
        port
        or
        80
    )

    try:
        with socket.create_connection(
            (
                host,
                port,
            ),
            timeout=float(
                timeout
            ),
        ):
            pass

    except Exception as exc:
        raise RuntimeError(
            (
                "Could not reach camera at "
                +
                host
                +
                ":"
                +
                str(
                    port
                )
                +
                ". "
                +
                str(
                    exc
                )
            )
        ) from exc

    return {
        "ok": True,
        "host": host,
        "port": port,
    }


def recall_ptzoptics_preset(
    host,
    preset,
    *,
    port=80,
    timeout=4.0
):
    """
    Recall a PTZOptics preset through the known HTTP-CGI command:

      /cgi-bin/ptzctrl.cgi?ptzcmd&poscall&<preset>
    """
    host = _clean_host(
        host
    )

    if not host:
        raise ValueError(
            "Camera host / IP is blank."
        )

    try:
        preset = int(
            preset
        )
    except Exception:
        raise ValueError(
            "Camera preset must be a whole number."
        )

    url = (
        _camera_base_url(
            host,
            port
        )
        +
        "/cgi-bin/ptzctrl.cgi?ptzcmd&poscall&"
        +
        str(
            preset
        )
    )

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "SundayServiceSystem/2.0",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=float(
                timeout
            ),
        ) as response:
            status = int(
                getattr(
                    response,
                    "status",
                    200
                )
            )

            body = response.read(
                512
            ).decode(
                "utf-8",
                errors="replace",
            )

    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            (
                "Camera returned HTTP "
                +
                str(
                    exc.code
                )
                +
                " while recalling preset "
                +
                str(
                    preset
                )
                +
                "."
            )
        ) from exc

    except urllib.error.URLError as exc:
        reason = getattr(
            exc,
            "reason",
            exc,
        )

        raise RuntimeError(
            (
                "Could not reach PTZ camera at "
                +
                _camera_base_url(
                    host,
                    port
                )
                +
                ". "
                +
                str(
                    reason
                )
            )
        ) from exc

    except socket.timeout as exc:
        raise RuntimeError(
            "PTZ camera command timed out."
        ) from exc

    if not (
        200
        <=
        status
        <
        300
    ):
        raise RuntimeError(
            (
                "Camera returned HTTP "
                +
                str(
                    status
                )
                +
                "."
            )
        )

    return {
        "ok": True,
        "host": host,
        "port": int(
            port
        ),
        "preset": preset,
        "status": status,
        "response": body,
    }


def active_camera_settings():
    return get_profile_camera_settings(
        load_active_profile()
    )


def profile_camera_ready():
    settings = active_camera_settings()

    if settings.get(
        "settings_source"
    ) != "profile":
        return (
            True,
            "LEGACY camera control",
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

    if provider in {
        "Fixed camera",
        "None",
    }:
        return (
            True,
            info.get(
                "description",
                ""
            ),
        )

    if provider == "PTZOptics / HTTP-CGI":
        try:
            result = check_tcp_connection(
                settings.get(
                    "host",
                    ""
                ),
                settings.get(
                    "port",
                    80
                ),
                timeout=1.5,
            )

            return (
                bool(
                    result.get(
                        "ok"
                    )
                ),
                (
                    "PTZOptics reachable at "
                    +
                    str(
                        result.get(
                            "host",
                            ""
                        )
                    )
                    +
                    ":"
                    +
                    str(
                        result.get(
                            "port",
                            80
                        )
                    )
                ),
            )

        except Exception as exc:
            return (
                False,
                str(
                    exc
                ),
            )

    return (
        False,
        "Camera adapter is not ready."
    )


def recall_profile_camera_preset(
    preset
):
    settings = active_camera_settings()

    if settings.get(
        "settings_source"
    ) != "profile":
        raise RuntimeError(
            "Camera profile adapter is not active."
        )

    provider = settings.get(
        "provider",
        "Not configured"
    )

    if provider == "PTZOptics / HTTP-CGI":
        return recall_ptzoptics_preset(
            settings.get(
                "host",
                ""
            ),
            preset,
            port=settings.get(
                "port",
                80
            ),
            timeout=4.0,
        )

    if provider in {
        "Fixed camera",
        "None",
    }:
        raise RuntimeError(
            (
                provider
                +
                " does not have movable camera presets."
            )
        )

    raise RuntimeError(
        (
            "No live SSS camera adapter is implemented yet for "
            +
            str(
                provider
            )
            +
            "."
        )
    )


def test_profile_camera_preset(
    preset
):
    """
    Intentional movement test used only from Camera Setup.
    """
    return recall_profile_camera_preset(
        preset
    )
