import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from sunday_common import load_config
from ptz_settings import load_ptz_settings

BASE = Path(r"C:\Church\SermonAI")
STATUS_FILE = BASE / "ptz_camera_status.json"


def write_status(state, message, preset=None):
    payload = {
        "state": state,
        "message": message,
        "preset": preset,
    }

    try:
        STATUS_FILE.write_text(
            json.dumps(
                payload,
                indent=2
            ),
            encoding="utf-8"
        )
    except Exception:
        pass

    return payload


def valid_preset(value):
    try:
        value = int(value)
    except Exception:
        return False

    return (
        0 <= value <= 89
        or
        100 <= value <= 254
    )


def build_url(config, preset):
    host = str(
        config.get(
            "ptz_camera_ip",
            ""
        )
    ).strip()

    if not host:
        raise RuntimeError(
            "PTZ camera IP is not configured. "
            "Run Setup-PTZ-Camera.bat."
        )

    scheme = str(
        config.get(
            "ptz_camera_scheme",
            "http"
        )
    ).strip().lower()

    port = str(
        config.get(
            "ptz_camera_http_port",
            ""
        )
    ).strip()

    if scheme not in {
        "http",
        "https",
    }:
        scheme = "http"

    host = re.sub(
        r"^https?://",
        "",
        host,
        flags=re.IGNORECASE,
    ).strip("/")

    if "/" in host:
        host = host.split(
            "/",
            1
        )[0]

    if port:
        authority = (
            f"{host}:{port}"
        )
    else:
        authority = host

    return (
        f"{scheme}://{authority}"
        f"/cgi-bin/ptzctrl.cgi"
        f"?ptzcmd&poscall&{int(preset)}"
    )


def recall_preset(preset):
    base_config = load_config()
    config = load_ptz_settings(
        base_config
    )

    if not valid_preset(
        preset
    ):
        raise RuntimeError(
            f"Invalid PTZ preset: {preset}"
        )

    url = build_url(
        config,
        int(
            preset
        )
    )

    request = urllib.request.Request(
        url,
        method="GET",
    )

    username = str(
        config.get(
            "ptz_camera_username",
            ""
        )
    ).strip()

    password = str(
        config.get(
            "ptz_camera_password",
            ""
        )
    )

    if username:
        token = base64.b64encode(
            f"{username}:{password}".encode(
                "utf-8"
            )
        ).decode(
            "ascii"
        )

        request.add_header(
            "Authorization",
            f"Basic {token}"
        )

    timeout = float(
        config.get(
            "ptz_camera_timeout_seconds",
            4
        )
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout
        ) as response:
            code = getattr(
                response,
                "status",
                200
            )

        if int(code) >= 400:
            raise RuntimeError(
                f"Camera returned HTTP {code}."
            )

        return write_status(
            "OK",
            f"PTZ preset {preset} recalled.",
            int(
                preset
            )
        )

    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"PTZ camera HTTP error {exc.code}."
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach PTZ camera: {exc.reason}"
        ) from exc


def resolve_named_preset(config, name):
    name = str(
        name
    ).strip().lower()

    if name == "worship":
        return int(
            config.get(
                "ptz_worship_preset",
                1
            )
        )

    if name == "pastor":
        return int(
            config.get(
                "ptz_pastor_preset",
                2
            )
        )

    return int(
        name
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "preset",
        help=(
            "Preset number or one of: worship, pastor"
        )
    )

    args = parser.parse_args()

    base_config = load_config()
    config = load_ptz_settings(
        base_config
    )

    try:
        preset = resolve_named_preset(
            config,
            args.preset,
        )

        result = recall_preset(
            preset
        )

        print(
            result[
                "message"
            ]
        )

        return 0

    except Exception as exc:
        write_status(
            "ERROR",
            str(
                exc
            )
        )

        print(
            f"PTZ camera error: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
