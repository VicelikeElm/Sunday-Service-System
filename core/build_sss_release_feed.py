import argparse
import datetime
import hashlib
import json
import shutil
from pathlib import Path

from sss_build_info import (
    APP_ID,
    APP_VERSION,
)
from sss_signing import (
    load_signing_config,
    manifest_thumbprint,
    sign_manifest_cms,
    validate_signing_config,
)
from sss_updater_core import (
    verify_update_package,
)


SOURCE_ROOT = Path(
    __file__
).resolve().parent.parent

UPDATE_OUTPUT = (
    SOURCE_ROOT
    /
    "update-output"
)

FEED_OUTPUT = (
    SOURCE_ROOT
    /
    "release-feed-output"
)


def _sha256(
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


def _https_base_url(
    value
):
    from urllib.parse import urlparse

    text = str(
        value
        or
        ""
    ).strip().rstrip(
        "/"
    )

    parsed = urlparse(
        text
    )

    if (
        parsed.scheme.lower()
        !=
        "https"
        or
        not parsed.netloc
    ):
        raise ValueError(
            "Release base URL must be HTTPS, for example https://updates.example.com/stable"
        )

    if parsed.username or parsed.password:
        raise ValueError(
            "Release base URL must not contain embedded credentials."
        )

    if parsed.query or parsed.fragment:
        raise ValueError(
            "Release base URL must not contain a query string or fragment."
        )

    return text


def build_release_feed(
    *,
    base_url,
    channel="stable",
    summary="",
    release_notes_url="",
    package_path=None,
    output_root=None
):
    base_url = _https_base_url(
        base_url
    )

    channel = str(
        channel
        or
        "stable"
    ).strip().lower()

    if channel not in {
        "stable",
        "beta",
    }:
        raise ValueError(
            "Channel must be stable or beta."
        )

    package = Path(
        package_path
        or
        (
            UPDATE_OUTPUT
            /
            (
                "SundayServiceSystem-Update-v"
                +
                APP_VERSION
                +
                ".sssupdate"
            )
        )
    )

    if not package.exists():
        raise FileNotFoundError(
            (
                "Signed update package is missing:\n"
                +
                str(
                    package
                )
                +
                "\nBuild the signed Windows release first."
            )
        )

    # This verifies the package's signed manifest, pinned signer, payload hashes,
    # and Authenticode-signed Main/Settings/Updater EXEs before the feed points
    # at it.
    package_manifest = verify_update_package(
        package
    )

    if str(
        package_manifest.get(
            "version",
            ""
        )
    ) != APP_VERSION:
        raise RuntimeError(
            (
                "Update package version "
                +
                str(
                    package_manifest.get(
                        "version",
                        ""
                    )
                )
                +
                " does not match release build "
                +
                APP_VERSION
                +
                "."
            )
        )

    config = load_signing_config(
        required=True
    )

    validate_signing_config(
        config
    )

    signer = manifest_thumbprint(
        config
    )

    output_root = Path(
        output_root
        or
        FEED_OUTPUT
    )

    channel_dir = (
        output_root
        /
        channel
    )

    if channel_dir.exists():
        shutil.rmtree(
            channel_dir
        )

    channel_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    package_name = package.name

    package_url = (
        base_url
        +
        "/"
        +
        package_name
    )

    notes_url = str(
        release_notes_url
        or
        ""
    ).strip()

    if notes_url:
        notes_url = _https_base_url(
            notes_url
        )

    release = {
        "version": APP_VERSION,
        "channel": channel,
        "published_at": datetime.datetime.now().astimezone().isoformat(),
        "package_url": package_url,
        "package_sha256": _sha256(
            package
        ),
        "package_size": package.stat().st_size,
        "summary": str(
            summary
            or
            ""
        ).strip(),
        "release_notes_url": notes_url,
        "minimum_update_client_version": "3.1.0",
        "withdrawn": False,
    }

    feed = {
        "feed_format": 1,
        "app_id": APP_ID,
        "channel": channel,
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "signer_thumbprint": signer,
        "releases": [
            release
        ],
    }

    feed_path = (
        channel_dir
        /
        "latest.json"
    )

    signature_path = (
        channel_dir
        /
        "latest.json.p7s"
    )

    feed_path.write_text(
        json.dumps(
            feed,
            indent=2,
            ensure_ascii=False,
        )
        +
        "\n",
        encoding="utf-8",
    )

    sign_manifest_cms(
        feed_path,
        signature_path,
        config,
    )

    shutil.copy2(
        package,
        channel_dir
        /
        package_name,
    )

    (channel_dir/"README_UPLOAD.txt").write_text(
        (
            "Sunday Service System signed "
            +
            channel
            +
            " release feed.\n\n"
            "Upload ALL THREE files to the HTTPS base URL:\n\n"
            "  latest.json\n"
            "  latest.json.p7s\n"
            "  "
            +
            package_name
            +
            "\n\n"
            "Expected URLs:\n"
            "  Feed:      "
            +
            base_url
            +
            "/latest.json\n"
            "  Signature: "
            +
            base_url
            +
            "/latest.json.p7s\n"
            "  Package:   "
            +
            package_url
            +
            "\n\n"
            "Do not edit latest.json after signing it. Any edit invalidates latest.json.p7s.\n"
        ),
        encoding="utf-8",
    )

    print()
    print(
        "SIGNED RELEASE FEED CREATED"
    )
    print(
        "Channel:",
        channel,
    )
    print(
        "Version:",
        APP_VERSION,
    )
    print(
        "Signer:",
        signer,
    )
    print(
        "Upload folder:",
        channel_dir,
    )
    print()
    print(
        "Feed URL after upload:",
        base_url
        +
        "/latest.json",
    )
    print(
        "Package URL after upload:",
        package_url,
    )

    return channel_dir


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build a signed Sunday Service System HTTPS release feed."
        )
    )

    parser.add_argument(
        "--base-url",
        required=True,
        help=(
            "HTTPS folder URL where latest.json, latest.json.p7s, and the "
            ".sssupdate package will be hosted."
        ),
    )

    parser.add_argument(
        "--channel",
        choices=(
            "stable",
            "beta",
        ),
        default="stable",
    )

    parser.add_argument(
        "--summary",
        default="",
    )

    parser.add_argument(
        "--release-notes-url",
        default="",
    )

    parser.add_argument(
        "--package",
        default="",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    build_release_feed(
        base_url=args.base_url,
        channel=args.channel,
        summary=args.summary,
        release_notes_url=args.release_notes_url,
        package_path=(
            args.package
            or
            None
        ),
    )
