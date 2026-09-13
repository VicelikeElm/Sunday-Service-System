import json
import urllib.request


DEFAULT_CONTROL_HOST = "127.0.0.1"
DEFAULT_CONTROL_PORT = 9223


def _read_json_url(url, *, timeout=1.5):
    with urllib.request.urlopen(
        url,
        timeout=float(timeout),
    ) as response:
        return json.loads(
            response.read().decode(
                "utf-8",
                errors="replace",
            )
        )


def _cdp_targets(
    *,
    host=DEFAULT_CONTROL_HOST,
    port=DEFAULT_CONTROL_PORT
):
    last_error = None

    for url in (
        f"http://{host}:{int(port)}/json/list",
        f"http://{host}:{int(port)}/json",
    ):
        try:
            payload = _read_json_url(url)

            if isinstance(payload, list):
                return payload

        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    return []
