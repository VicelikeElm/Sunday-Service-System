import json
import socket
import urllib.error
import urllib.request

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 50001


def clean_host(host):
    host = str(host or DEFAULT_HOST).strip()

    if host.startswith("http://"):
        host = host[len("http://"):]
    elif host.startswith("https://"):
        host = host[len("https://"):]

    host = host.rstrip("/")

    return host or DEFAULT_HOST


def base_url(host, port):
    return "http://" + clean_host(host) + ":" + str(int(port or DEFAULT_PORT))


def request_json(host, port, path, timeout=3.0):
    url = base_url(host, port) + str(path)

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "SundayServiceSystem/1.7",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=float(timeout)) as response:
            raw = response.read()
            status = int(getattr(response, "status", 200))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            "ProPresenter API returned HTTP "
            + str(exc.code)
            + " for "
            + str(path)
            + "."
        ) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(
            "Could not reach ProPresenter at "
            + base_url(host, port)
            + ". "
            + str(reason)
        ) from exc
    except socket.timeout as exc:
        raise RuntimeError(
            "ProPresenter API timed out at "
            + base_url(host, port)
            + "."
        ) from exc

    if not (200 <= status < 300):
        raise RuntimeError(
            "ProPresenter API returned HTTP "
            + str(status)
            + "."
        )

    if not raw:
        return {}

    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        return {"raw": raw.decode("utf-8", errors="replace")}


def get_version(host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=3.0):
    return request_json(host, port, "/version", timeout=timeout)


def get_active_presentation(host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=3.0):
    return request_json(
        host,
        port,
        "/v1/presentation/active",
        timeout=timeout,
    )


def connection_test(host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=3.0):
    version = get_version(host, port, timeout=timeout)

    return {
        "ok": True,
        "base_url": base_url(host, port),
        "version": version,
    }


def trigger_next(host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=3.0):
    return request_json(
        host,
        port,
        "/v1/presentation/active/next/trigger",
        timeout=timeout,
    )


def trigger_previous(host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=3.0):
    return request_json(
        host,
        port,
        "/v1/presentation/active/previous/trigger",
        timeout=timeout,
    )
