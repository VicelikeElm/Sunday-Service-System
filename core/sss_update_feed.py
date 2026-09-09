import datetime
import hashlib
import json
import os
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from sss_build_info import (
    APP_ID,
    APP_VERSION,
)
from sss_release_trust import (
    TRUSTED_UPDATE_SIGNER_THUMBPRINTS,
)
from sss_signing import (
    normalize_thumbprint,
    verify_manifest_cms,
)
from sss_updater_core import (
    UPDATE_ROOT,
    verify_update_package,
    version_is_newer,
)


FEED_FORMAT = 1

FEED_CONFIG_FILE = (
    UPDATE_ROOT
    /
    "feed_config.json"
)

FEED_STATE_FILE = (
    UPDATE_ROOT
    /
    "feed_state.json"
)

DOWNLOAD_ROOT = (
    UPDATE_ROOT
    /
    "Downloads"
)

DEFAULT_CHANNEL = "stable"

MAX_FEED_BYTES = (
    2
    *
    1024
    *
    1024
)

MAX_SIGNATURE_BYTES = (
    2
    *
    1024
    *
    1024
)

MAX_UPDATE_BYTES = (
    3
    *
    1024
    *
    1024
    *
    1024
)

USER_AGENT = (
    "SundayServiceSystem/"
    +
    APP_VERSION
    +
    " UpdateClient"
)


def _now_iso():
    return datetime.datetime.now().astimezone().isoformat()


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

    temp = path.with_suffix(
        path.suffix
        +
        ".tmp"
    )

    temp.write_text(
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
        temp,
        path,
    )


def load_feed_config():
    default = {
        "enabled": False,
        "feed_url": "",
        "signature_url": "",
        "channel": DEFAULT_CHANNEL,
        "timeout_seconds": 20,
    }

    try:
        payload = json.loads(
            FEED_CONFIG_FILE.read_text(
                encoding="utf-8-sig"
            )
        )

        if isinstance(
            payload,
            dict
        ):
            default.update(
                payload
            )

    except Exception:
        pass

    default[
        "feed_url"
    ] = str(
        default.get(
            "feed_url",
            ""
        )
        or
        ""
    ).strip()

    default[
        "signature_url"
    ] = str(
        default.get(
            "signature_url",
            ""
        )
        or
        ""
    ).strip()

    channel = str(
        default.get(
            "channel",
            DEFAULT_CHANNEL
        )
        or
        DEFAULT_CHANNEL
    ).strip().lower()

    if channel not in {
        "stable",
        "beta",
    }:
        channel = DEFAULT_CHANNEL

    default[
        "channel"
    ] = channel

    try:
        timeout = int(
            default.get(
                "timeout_seconds",
                20
            )
        )
    except Exception:
        timeout = 20

    default[
        "timeout_seconds"
    ] = min(
        120,
        max(
            5,
            timeout
        )
    )

    default[
        "enabled"
    ] = bool(
        default.get(
            "enabled"
        )
        and
        default[
            "feed_url"
        ]
    )

    return default


def save_feed_config(
    *,
    feed_url,
    channel=DEFAULT_CHANNEL,
    signature_url="",
    enabled=True,
    timeout_seconds=20
):
    feed_url = str(
        feed_url
        or
        ""
    ).strip()

    signature_url = str(
        signature_url
        or
        ""
    ).strip()

    channel = str(
        channel
        or
        DEFAULT_CHANNEL
    ).strip().lower()

    if channel not in {
        "stable",
        "beta",
    }:
        raise ValueError(
            "Update channel must be stable or beta."
        )

    if feed_url:
        validate_https_url(
            feed_url,
            label="Release feed URL",
        )

    if signature_url:
        validate_https_url(
            signature_url,
            label="Release feed signature URL",
        )

    payload = {
        "enabled": bool(
            enabled
            and
            feed_url
        ),
        "feed_url": feed_url,
        "signature_url": signature_url,
        "channel": channel,
        "timeout_seconds": min(
            120,
            max(
                5,
                int(
                    timeout_seconds
                )
            )
        ),
        "saved_at": _now_iso(),
    }

    _write_json_atomic(
        FEED_CONFIG_FILE,
        payload,
    )

    return payload


def load_feed_state():
    try:
        payload = json.loads(
            FEED_STATE_FILE.read_text(
                encoding="utf-8-sig"
            )
        )

        if isinstance(
            payload,
            dict
        ):
            return payload

    except Exception:
        pass

    return {}


def save_feed_state(
    payload
):
    data = dict(
        payload
        or
        {}
    )

    data[
        "updated_at"
    ] = _now_iso()

    _write_json_atomic(
        FEED_STATE_FILE,
        data,
    )

    return data


def validate_https_url(
    url,
    *,
    label="URL"
):
    text = str(
        url
        or
        ""
    ).strip()

    if not text:
        raise ValueError(
            label
            +
            " is blank."
        )

    parsed = urllib.parse.urlparse(
        text
    )

    if parsed.scheme.lower() != "https":
        raise ValueError(
            (
                label
                +
                " must use HTTPS."
            )
        )

    if not parsed.netloc:
        raise ValueError(
            (
                label
                +
                " has no host."
            )
        )

    if parsed.username or parsed.password:
        raise ValueError(
            (
                label
                +
                " must not contain embedded username/password credentials."
            )
        )

    return text


class _HTTPSOnlyRedirectHandler(
    urllib.request.HTTPRedirectHandler
):
    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl
    ):
        validate_https_url(
            newurl,
            label="Redirect URL",
        )

        return super().redirect_request(
            req,
            fp,
            code,
            msg,
            headers,
            newurl,
        )


def _https_opener():
    context = ssl.create_default_context()

    return urllib.request.build_opener(
        urllib.request.HTTPSHandler(
            context=context
        ),
        _HTTPSOnlyRedirectHandler(),
    )


def _download_bytes(
    url,
    *,
    max_bytes,
    timeout,
    label
):
    validate_https_url(
        url,
        label=label,
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/octet-stream, application/json;q=0.9, */*;q=0.1"
            ),
            "Cache-Control": "no-cache",
            "Accept-Encoding": "identity",
        },
        method="GET",
    )

    opener = _https_opener()

    try:
        with opener.open(
            request,
            timeout=float(
                timeout
            ),
        ) as response:
            final_url = str(
                response.geturl()
            )

            validate_https_url(
                final_url,
                label="Final download URL",
            )

            length = response.headers.get(
                "Content-Length"
            )

            if length:
                try:
                    declared = int(
                        length
                    )
                except Exception:
                    declared = 0

                if (
                    declared
                    >
                    int(
                        max_bytes
                    )
                ):
                    raise RuntimeError(
                        (
                            label
                            +
                            " is larger than the configured safety limit."
                        )
                    )

            chunks = []
            total = 0

            while True:
                block = response.read(
                    1024
                    *
                    256
                )

                if not block:
                    break

                total += len(
                    block
                )

                if total > int(
                    max_bytes
                ):
                    raise RuntimeError(
                        (
                            label
                            +
                            " exceeded the configured safety limit."
                        )
                    )

                chunks.append(
                    block
                )

            return (
                b"".join(
                    chunks
                ),
                final_url,
            )

    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            (
                label
                +
                " returned HTTP "
                +
                str(
                    exc.code
                )
                +
                "."
            )
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            (
                label
                +
                " could not be downloaded: "
                +
                str(
                    exc.reason
                )
            )
        ) from exc


def _signature_url(
    config
):
    explicit = str(
        config.get(
            "signature_url",
            ""
        )
        or
        ""
    ).strip()

    if explicit:
        return validate_https_url(
            explicit,
            label="Release feed signature URL",
        )

    feed_url = validate_https_url(
        config.get(
            "feed_url",
            ""
        ),
        label="Release feed URL",
    )

    return (
        feed_url
        +
        ".p7s"
    )


def _version_tuple(
    version
):
    parts = []

    for token in str(
        version
        or
        "0"
    ).split(
        "."
    ):
        digits = "".join(
            character
            for character in token
            if character.isdigit()
        )

        parts.append(
            int(
                digits
                or
                0
            )
        )

    while len(
        parts
    ) < 4:
        parts.append(
            0
        )

    return tuple(
        parts[
            :4
        ]
    )


def _validate_release(
    release
):
    if not isinstance(
        release,
        dict
    ):
        raise RuntimeError(
            "Release feed contains an invalid release entry."
        )

    version = str(
        release.get(
            "version",
            ""
        )
    ).strip()

    if not version:
        raise RuntimeError(
            "Release feed entry has no version."
        )

    package_url = validate_https_url(
        release.get(
            "package_url",
            ""
        ),
        label=(
            "Package URL for "
            +
            version
        ),
    )

    package_sha256 = "".join(
        character
        for character in str(
            release.get(
                "package_sha256",
                ""
            )
        ).lower()
        if character in "0123456789abcdef"
    )

    if len(
        package_sha256
    ) != 64:
        raise RuntimeError(
            (
                "Release "
                +
                version
                +
                " has an invalid package SHA-256."
            )
        )

    try:
        package_size = int(
            release.get(
                "package_size",
                0
            )
        )
    except Exception as exc:
        raise RuntimeError(
            (
                "Release "
                +
                version
                +
                " has an invalid package size."
            )
        ) from exc

    if (
        package_size
        <=
        0
        or
        package_size
        >
        MAX_UPDATE_BYTES
    ):
        raise RuntimeError(
            (
                "Release "
                +
                version
                +
                " has an unsafe package size."
            )
        )

    channel = str(
        release.get(
            "channel",
            DEFAULT_CHANNEL
        )
        or
        DEFAULT_CHANNEL
    ).strip().lower()

    if channel not in {
        "stable",
        "beta",
    }:
        raise RuntimeError(
            (
                "Release "
                +
                version
                +
                " has an unsupported channel."
            )
        )

    result = dict(
        release
    )

    result[
        "version"
    ] = version

    result[
        "package_url"
    ] = package_url

    result[
        "package_sha256"
    ] = package_sha256

    result[
        "package_size"
    ] = package_size

    result[
        "channel"
    ] = channel

    result[
        "withdrawn"
    ] = bool(
        release.get(
            "withdrawn",
            False
        )
    )

    result[
        "minimum_update_client_version"
    ] = str(
        release.get(
            "minimum_update_client_version",
            "3.1.0"
        )
        or
        "3.1.0"
    ).strip()

    return result


def _record_update_event(
    message,
    *,
    level="INFO",
    metadata=None
):
    try:
        from sss_event_history import record_event

        record_event(
            str(
                message
            ),
            category="UPDATES",
            level=level,
            source="ONLINE UPDATE FEED",
            metadata=(
                metadata
                if isinstance(
                    metadata,
                    dict
                )
                else
                {}
            ),
        )
    except Exception:
        pass


def check_release_feed(
    *,
    current_version=None,
    config=None
):
    config = dict(
        config
        or
        load_feed_config()
    )

    if not config.get(
        "enabled"
    ):
        raise RuntimeError(
            (
                "Online update feed is not configured. "
                "Set an HTTPS feed URL in Settings -> Updates."
            )
        )

    feed_url = validate_https_url(
        config.get(
            "feed_url",
            ""
        ),
        label="Release feed URL",
    )

    signature_url = _signature_url(
        config
    )

    timeout = int(
        config.get(
            "timeout_seconds",
            20
        )
    )

    feed_bytes, final_feed_url = _download_bytes(
        feed_url,
        max_bytes=MAX_FEED_BYTES,
        timeout=timeout,
        label="Signed release feed",
    )

    signature_bytes, final_signature_url = _download_bytes(
        signature_url,
        max_bytes=MAX_SIGNATURE_BYTES,
        timeout=timeout,
        label="Release feed signature",
    )

    with tempfile.TemporaryDirectory(
        prefix="sss_feed_verify_"
    ) as temp_dir:
        temp_root = Path(
            temp_dir
        )

        feed_file = (
            temp_root
            /
            "latest.json"
        )

        signature_file = (
            temp_root
            /
            "latest.json.p7s"
        )

        feed_file.write_bytes(
            feed_bytes
        )

        signature_file.write_bytes(
            signature_bytes
        )

        signature_result = verify_manifest_cms(
            feed_file,
            signature_file,
            trusted_thumbprints=TRUSTED_UPDATE_SIGNER_THUMBPRINTS,
            require_trusted=True,
        )

    try:
        feed = json.loads(
            feed_bytes.decode(
                "utf-8-sig"
            )
        )
    except Exception as exc:
        raise RuntimeError(
            (
                "Signed release feed JSON is invalid: "
                +
                str(
                    exc
                )
            )
        ) from exc

    if not isinstance(
        feed,
        dict
    ):
        raise RuntimeError(
            "Signed release feed is not a JSON object."
        )

    if int(
        feed.get(
            "feed_format",
            0
        )
        or
        0
    ) != FEED_FORMAT:
        raise RuntimeError(
            (
                "Unsupported SSS release feed format: "
                +
                str(
                    feed.get(
                        "feed_format",
                        ""
                    )
                )
            )
        )

    if str(
        feed.get(
            "app_id",
            ""
        )
    ) != APP_ID:
        raise RuntimeError(
            "Signed release feed is not for Sunday Service System."
        )

    declared_signer = normalize_thumbprint(
        feed.get(
            "signer_thumbprint",
            ""
        )
    )

    actual_signer = normalize_thumbprint(
        signature_result.get(
            "thumbprint",
            ""
        )
    )

    if (
        not declared_signer
        or
        declared_signer
        !=
        actual_signer
    ):
        raise RuntimeError(
            (
                "Release feed signer mismatch.\n"
                "Declared: "
                +
                declared_signer
                +
                "\nActual: "
                +
                actual_signer
            )
        )

    configured_channel = str(
        config.get(
            "channel",
            DEFAULT_CHANNEL
        )
    ).lower()

    releases_raw = feed.get(
        "releases",
        []
    )

    if not isinstance(
        releases_raw,
        list
    ):
        raise RuntimeError(
            "Signed release feed releases list is invalid."
        )

    releases = []

    for item in releases_raw:
        release = _validate_release(
            item
        )

        if release.get(
            "withdrawn"
        ):
            continue

        if release.get(
            "channel"
        ) != configured_channel:
            continue

        releases.append(
            release
        )

    releases.sort(
        key=lambda item:
            _version_tuple(
                item.get(
                    "version"
                )
            ),
        reverse=True,
    )

    latest = (
        releases[
            0
        ]
        if releases
        else
        None
    )

    current_version = str(
        current_version
        or
        APP_VERSION
    )

    client_too_old = bool(
        latest
        and
        _version_tuple(
            current_version
        )
        <
        _version_tuple(
            latest.get(
                "minimum_update_client_version",
                "3.1.0"
            )
        )
    )

    available = bool(
        latest
        and
        not client_too_old
        and
        version_is_newer(
            latest.get(
                "version"
            ),
            current_version,
        )
    )

    state = {
        "last_checked_at": _now_iso(),
        "feed_url": final_feed_url,
        "signature_url": final_signature_url,
        "channel": configured_channel,
        "feed_signer_thumbprint": actual_signer,
        "current_version": current_version,
        "update_available": available,
        "client_too_old": client_too_old,
        "minimum_update_client_version": (
            str(
                latest.get(
                    "minimum_update_client_version",
                    ""
                )
            )
            if latest
            else
            ""
        ),
        "latest_version": (
            str(
                latest.get(
                    "version"
                )
            )
            if latest
            else
            ""
        ),
        "latest_release": latest,
    }

    save_feed_state(
        state
    )

    _record_update_event(
        (
            "Signed online release feed checked: "
            +
            configured_channel.upper()
            +
            " — latest "
            +
            (
                str(
                    latest.get(
                        "version",
                        ""
                    )
                )
                if latest
                else
                "(none)"
            )
            +
            (
                " — update available"
                if available
                else
                " — no installable newer update"
            )
            +
            "."
        ),
        metadata={
            "feed_url": final_feed_url,
            "signer_thumbprint": actual_signer,
        },
    )

    return {
        "feed": feed,
        "latest_release": latest,
        "update_available": available,
        "client_too_old": client_too_old,
        "signature": signature_result,
        "state": state,
    }


def _sha256_file(
    path
):
    digest = hashlib.sha256()

    with Path(
        path
    ).open(
        "rb"
    ) as handle:
        while True:
            block = handle.read(
                1024
                *
                1024
            )

            if not block:
                break

            digest.update(
                block
            )

    return digest.hexdigest()


def _safe_download_name(
    release
):
    version = "".join(
        character
        for character in str(
            release.get(
                "version",
                "update"
            )
        )
        if (
            character.isalnum()
            or
            character in {
                ".",
                "-",
                "_",
            }
        )
    )

    return (
        "SundayServiceSystem-Update-v"
        +
        (
            version
            or
            "update"
        )
        +
        ".sssupdate"
    )


def download_release_package(
    release,
    *,
    config=None,
    progress=None
):
    release = _validate_release(
        release
    )

    config = dict(
        config
        or
        load_feed_config()
    )

    timeout = int(
        config.get(
            "timeout_seconds",
            20
        )
    )

    DOWNLOAD_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        DOWNLOAD_ROOT
        /
        _safe_download_name(
            release
        )
    )

    temp = destination.with_suffix(
        destination.suffix
        +
        ".download"
    )

    try:
        temp.unlink()
    except Exception:
        pass

    url = validate_https_url(
        release.get(
            "package_url"
        ),
        label="Release package URL",
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream",
            "Cache-Control": "no-cache",
            "Accept-Encoding": "identity",
        },
        method="GET",
    )

    opener = _https_opener()

    digest = hashlib.sha256()
    total = 0

    expected_size = int(
        release.get(
            "package_size"
        )
    )

    try:
        with opener.open(
            request,
            timeout=float(
                timeout
            ),
        ) as response:
            final_url = str(
                response.geturl()
            )

            validate_https_url(
                final_url,
                label="Final update package URL",
            )

            length = response.headers.get(
                "Content-Length"
            )

            if length:
                try:
                    declared = int(
                        length
                    )
                except Exception:
                    declared = 0

                if (
                    declared
                    >
                    MAX_UPDATE_BYTES
                    or
                    (
                        declared
                        >
                        0
                        and
                        declared
                        !=
                        expected_size
                    )
                ):
                    raise RuntimeError(
                        "Downloaded update Content-Length does not match the signed feed."
                    )

            with temp.open(
                "wb"
            ) as handle:
                while True:
                    block = response.read(
                        1024
                        *
                        1024
                    )

                    if not block:
                        break

                    total += len(
                        block
                    )

                    if total > MAX_UPDATE_BYTES:
                        raise RuntimeError(
                            "Downloaded update exceeded the maximum allowed size."
                        )

                    if total > expected_size:
                        raise RuntimeError(
                            "Downloaded update exceeded the size declared in the signed feed."
                        )

                    handle.write(
                        block
                    )

                    digest.update(
                        block
                    )

                    if callable(
                        progress
                    ):
                        progress(
                            total,
                            expected_size,
                        )

    except Exception:
        try:
            temp.unlink()
        except Exception:
            pass

        raise

    if total != expected_size:
        try:
            temp.unlink()
        except Exception:
            pass

        raise RuntimeError(
            (
                "Downloaded update size mismatch. Expected "
                +
                str(
                    expected_size
                )
                +
                " bytes, received "
                +
                str(
                    total
                )
                +
                "."
            )
        )

    actual_sha = digest.hexdigest().lower()

    expected_sha = str(
        release.get(
            "package_sha256"
        )
    ).lower()

    if actual_sha != expected_sha:
        try:
            temp.unlink()
        except Exception:
            pass

        raise RuntimeError(
            (
                "Downloaded update SHA-256 does not match the signed release feed."
            )
        )

    os.replace(
        temp,
        destination,
    )

    manifest = verify_update_package(
        destination
    )

    if str(
        manifest.get(
            "version",
            ""
        )
    ) != str(
        release.get(
            "version",
            ""
        )
    ):
        try:
            destination.unlink()
        except Exception:
            pass

        raise RuntimeError(
            (
                "Downloaded signed package version does not match the signed release feed."
            )
        )

    state = load_feed_state()

    state.update(
        {
            "downloaded_at": _now_iso(),
            "downloaded_version": str(
                release.get(
                    "version",
                    ""
                )
            ),
            "downloaded_path": str(
                destination
            ),
            "downloaded_sha256": actual_sha,
            "download_verified": True,
        }
    )

    save_feed_state(
        state
    )

    _record_update_event(
        (
            "Online update downloaded and fully verified: SSS "
            +
            str(
                release.get(
                    "version",
                    ""
                )
            )
            +
            "."
        ),
        metadata={
            "path": str(
                destination
            ),
            "sha256": actual_sha,
        },
    )

    return {
        "path": destination,
        "manifest": manifest,
        "release": release,
        "sha256": actual_sha,
        "size": total,
    }


def online_update_status():
    return {
        "config": load_feed_config(),
        "state": load_feed_state(),
        "download_root": str(
            DOWNLOAD_ROOT
        ),
    }
