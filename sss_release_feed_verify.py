import argparse
import hashlib
import json
from pathlib import Path

from sss_build_info import APP_ID
from sss_release_trust import TRUSTED_UPDATE_SIGNER_THUMBPRINTS
from sss_signing import (
    normalize_thumbprint,
    verify_manifest_cms,
)
from sss_updater_core import verify_update_package


def _sha256(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)

    return digest.hexdigest()


def verify_feed_folder(folder):
    folder = Path(folder)

    feed_path = folder / "latest.json"
    signature_path = folder / "latest.json.p7s"

    if not feed_path.is_file():
        raise RuntimeError("latest.json is missing.")

    if not signature_path.is_file():
        raise RuntimeError("latest.json.p7s is missing.")

    signature = verify_manifest_cms(
        feed_path,
        signature_path,
        trusted_thumbprints=TRUSTED_UPDATE_SIGNER_THUMBPRINTS,
        require_trusted=True,
    )

    feed = json.loads(
        feed_path.read_text(
            encoding="utf-8-sig"
        )
    )

    if feed.get("app_id") != APP_ID:
        raise RuntimeError(
            "Release feed App ID is not Sunday Service System."
        )

    if int(feed.get("feed_format", 0) or 0) != 1:
        raise RuntimeError(
            "Unsupported release-feed format."
        )

    declared = normalize_thumbprint(
        feed.get(
            "signer_thumbprint",
            ""
        )
    )

    actual = normalize_thumbprint(
        signature.get(
            "thumbprint",
            ""
        )
    )

    if declared != actual:
        raise RuntimeError(
            "Release-feed declared signer does not match CMS signer."
        )

    releases = feed.get(
        "releases",
        []
    )

    if not isinstance(releases, list) or not releases:
        raise RuntimeError(
            "Release feed has no releases."
        )

    checked = []

    for release in releases:
        version = str(
            release.get(
                "version",
                ""
            )
        )

        expected_sha = str(
            release.get(
                "package_sha256",
                ""
            )
        ).lower()

        expected_size = int(
            release.get(
                "package_size",
                0
            )
        )

        package_name = Path(
            str(
                release.get(
                    "package_url",
                    ""
                )
            ).split("?")[0]
        ).name

        package = folder / package_name

        if not package.is_file():
            raise RuntimeError(
                (
                    "Release package is missing from feed folder: "
                    +
                    package_name
                )
            )

        if package.stat().st_size != expected_size:
            raise RuntimeError(
                (
                    "Release package size mismatch: "
                    +
                    package_name
                )
            )

        if _sha256(package).lower() != expected_sha:
            raise RuntimeError(
                (
                    "Release package SHA-256 mismatch: "
                    +
                    package_name
                )
            )

        package_manifest = verify_update_package(
            package
        )

        if str(
            package_manifest.get(
                "version",
                ""
            )
        ) != version:
            raise RuntimeError(
                (
                    "Release feed/package version mismatch for "
                    +
                    package_name
                )
            )

        checked.append(
            version
        )

    return {
        "folder": str(folder),
        "signer": actual,
        "versions": checked,
        "channel": str(
            feed.get(
                "channel",
                ""
            )
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--folder",
        required=True,
    )

    args = parser.parse_args()

    result = verify_feed_folder(
        args.folder
    )

    print()
    print("[READY] SIGNED RELEASE FEED VERIFIED")
    print("Folder:", result["folder"])
    print("Channel:", result["channel"])
    print("Signer:", result["signer"])
    print("Release(s):", ", ".join(result["versions"]))
    print()


if __name__ == "__main__":
    main()
