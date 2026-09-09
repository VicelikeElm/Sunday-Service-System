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
        "live_supported": True,
        "has_presets": True,
        "description": (
            "Uses the Sony VISCA-over-IP standard (UDP) preset recall - "
            "supported by many non-PTZOptics PTZ cameras."
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


VISCA_DEFAULT_PORT = 52381


def _visca_packet(
    payload_bytes,
    *,
    payload_type=b"\x01\x00",
    sequence=1
):
    """
    Wrap raw VISCA command bytes in the standard 8-byte VISCA-over-IP
    header (Sony's UDP encapsulation, used by the large majority of
    non-PTZOptics network PTZ cameras): 2-byte payload type, 2-byte
    payload length, 4-byte sequence number, then the payload itself.
    """
    length = len(
        payload_bytes
    ).to_bytes(
        2,
        "big",
    )

    seq = int(
        sequence
    ).to_bytes(
        4,
        "big",
    )

    return (
        payload_type
        +
        length
        +
        seq
        +
        payload_bytes
    )


def _visca_send(
    host,
    packet,
    *,
    port=VISCA_DEFAULT_PORT,
    timeout=2.0
):
    """
    Fire-and-forget UDP send, returning whatever reply bytes (if any)
    come back within the timeout. VISCA cameras normally ACK a command
    almost immediately, so any reply at all is treated as "reachable
    and responding" - this does not attempt to parse/validate the
    ACK/Completion sequence, matching the same fire-and-forget level of
    support the existing PTZOptics HTTP-CGI adapter provides.
    """
    host = _clean_host(
        host
    )

    if not host:
        raise ValueError(
            "Camera host / IP is blank."
        )

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
    )

    try:
        sock.settimeout(
            float(
                timeout
            )
        )

        sock.sendto(
            packet,
            (
                host,
                int(
                    port
                ),
            ),
        )

        try:
            reply, _ = sock.recvfrom(
                256
            )
            return reply

        except socket.timeout:
            return None

    finally:
        sock.close()


def check_visca_connection(
    host,
    *,
    port=VISCA_DEFAULT_PORT,
    camera_address=1,
    timeout=2.0
):
    """
    Sends IF_Clear (the standard VISCA interface-reset command, chosen
    because it never moves the camera) as a broadcast and waits for any
    reply to confirm something VISCA-speaking is listening.
    """
    packet = _visca_packet(
        bytes(
            [
                0x88,
                0x01,
                0x00,
                0x01,
                0xFF,
            ]
        )
    )

    reply = _visca_send(
        host,
        packet,
        port=port,
        timeout=timeout,
    )

    if reply is None:
        raise RuntimeError(
            "No VISCA reply from "
            +
            _clean_host(
                host
            )
            +
            ":"
            +
            str(
                port
            )
            +
            " - check the IP/port, or that the camera is powered on."
        )

    return {
        "ok": True,
        "host": _clean_host(
            host
        ),
        "port": int(
            port
        ),
    }


def recall_visca_preset(
    host,
    preset,
    *,
    port=VISCA_DEFAULT_PORT,
    camera_address=1,
    timeout=2.0
):
    """
    Standard VISCA CAM_Memory (Recall) command: 8x 01 04 3F 02 pp FF,
    where x is the camera address (1 unless daisy-chained) and pp is
    the preset number. Universal across VISCA-compatible cameras.
    """
    try:
        preset = int(
            preset
        )
    except Exception:
        raise ValueError(
            "Camera preset must be a whole number."
        )

    if not (
        0 <= preset <= 255
    ):
        raise ValueError(
            "Camera preset must be between 0 and 255."
        )

    address_byte = 0x80 | (
        int(
            camera_address
        )
        &
        0x0F
    )

    packet = _visca_packet(
        bytes(
            [
                address_byte,
                0x01,
                0x04,
                0x3F,
                0x02,
                preset,
                0xFF,
            ]
        )
    )

    reply = _visca_send(
        host,
        packet,
        port=port,
        timeout=timeout,
    )

    if reply is None:
        raise RuntimeError(
            "No VISCA reply from "
            +
            _clean_host(
                host
            )
            +
            ":"
            +
            str(
                port
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

    return {
        "ok": True,
        "host": _clean_host(
            host
        ),
        "port": int(
            port
        ),
        "preset": preset,
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

    if provider == "VISCA over IP":
        try:
            result = check_visca_connection(
                settings.get(
                    "host",
                    ""
                ),
                port=settings.get(
                    "port",
                    VISCA_DEFAULT_PORT
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
                    "VISCA camera reachable at "
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
                            VISCA_DEFAULT_PORT
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

    if provider == "VISCA over IP":
        return recall_visca_preset(
            settings.get(
                "host",
                ""
            ),
            preset,
            port=settings.get(
                "port",
                VISCA_DEFAULT_PORT
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
