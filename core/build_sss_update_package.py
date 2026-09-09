import datetime
import hashlib
import json
import zipfile
from pathlib import Path

from sss_build_info import (
    APP_ID,
    APP_VERSION,
)
from sss_updater_core import (
    MAIN_DIR_NAME,
    SETTINGS_DIR_NAME,
    UPDATER_DIR_NAME,
    UPDATE_PACKAGE_FORMAT,
)

from sss_signing import (
    load_signing_config,
    manifest_thumbprint,
    sign_manifest_cms,
    verify_authenticode_file,
    validate_signing_config,
)



SOURCE_ROOT = Path(
    __file__
).resolve().parent.parent

DIST_ROOT = (
    SOURCE_ROOT
    /
    "dist"
)

OUTPUT_ROOT = (
    SOURCE_ROOT
    /
    "update-output"
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


def _payload_files():
    files = []

    for root_name in (
        MAIN_DIR_NAME,
        SETTINGS_DIR_NAME,
        UPDATER_DIR_NAME,
    ):
        root = (
            DIST_ROOT
            /
            root_name
        )

        if not root.is_dir():
            raise RuntimeError(
                (
                    "EXE build folder is missing:\n"
                    +
                    str(
                        root
                    )
                )
            )

        for path in sorted(
            root.rglob(
                "*"
            )
        ):
            if not path.is_file():
                continue

            relative = (
                Path(
                    "payload"
                )
                /
                root_name
                /
                path.relative_to(
                    root
                )
            )

            files.append(
                (
                    path,
                    relative,
                )
            )

    return files


def build_update_package():
    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    config = load_signing_config(
        required=True
    )

    signing_status = validate_signing_config(
        config
    )

    signer_thumb = manifest_thumbprint(
        config
    )

    # The two update-delivered EXEs must already carry valid Authenticode
    # signatures from the trusted release signer before their file hashes are
    # committed into the signed manifest.
    required_exes = (
        DIST_ROOT
        /
        MAIN_DIR_NAME
        /
        "SundayServiceSystem.exe",

        DIST_ROOT
        /
        SETTINGS_DIR_NAME
        /
        "SundayServiceSystemSettings.exe",

        DIST_ROOT
        /
        UPDATER_DIR_NAME
        /
        "SundayServiceSystemUpdater.exe",
    )

    for executable in required_exes:
        verify_authenticode_file(
            executable,
            trusted_thumbprints=(
                signer_thumb,
                signing_status[
                    "code_signing"
                ][
                    "thumbprint"
                ],
            ),
            require_valid=True,
        )

    files = _payload_files()

    manifest_files = []

    for source, relative in files:
        manifest_files.append(
            {
                "path": str(
                    relative
                ).replace(
                    "\\",
                    "/"
                ),
                "size": source.stat().st_size,
                "sha256": _sha256(
                    source
                ),
            }
        )

    manifest = {
        "package_format": UPDATE_PACKAGE_FORMAT,
        "app_id": APP_ID,
        "version": APP_VERSION,
        "created_at": datetime.datetime.now().astimezone().isoformat(),
        "payload_roots": [
            MAIN_DIR_NAME,
            SETTINGS_DIR_NAME,
            UPDATER_DIR_NAME,
        ],
        "files": manifest_files,
        "updates_user_data": False,
        "updates_credentials": False,
        "updates_profiles": False,
        "updates_runtime_support": False,
        "signed": True,
        "signature_format": "CMS/PKCS#7 DETACHED",
        "signature_file": "manifest.p7s",
        "signer_thumbprint": signer_thumb,
        "signature_policy": (
            "Pinned SSS release signer + detached CMS signature + SHA-256 file "
            "manifest + Authenticode-signed Main/Settings executables"
        ),
    }

    output = (
        OUTPUT_ROOT
        /
        (
            "SundayServiceSystem-Update-v"
            +
            APP_VERSION
            +
            ".sssupdate"
        )
    )

    if output.exists():
        output.unlink()

    work = (
        OUTPUT_ROOT
        /
        (
            ".signing_"
            +
            APP_VERSION
        )
    )

    if work.exists():
        import shutil

        shutil.rmtree(
            work
        )

    work.mkdir(
        parents=True,
        exist_ok=False,
    )

    manifest_path = (
        work
        /
        "manifest.json"
    )

    signature_path = (
        work
        /
        "manifest.p7s"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
        +
        "\n",
        encoding="utf-8",
    )

    sign_manifest_cms(
        manifest_path,
        signature_path,
        config,
    )

    try:
        with zipfile.ZipFile(
            output,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.write(
                manifest_path,
                arcname="manifest.json",
            )

            archive.write(
                signature_path,
                arcname="manifest.p7s",
            )

            archive.writestr(
                "README.txt",
                (
                    "Sunday Service System signed application update package.\n"
                    "The manifest is protected by a detached CMS/PKCS#7 signature.\n"
                    "All payload files are SHA-256 hashed in that signed manifest.\n"
                    "Main, Settings, and Updater executables must also have valid Authenticode signatures.\n"
                    "This package does not contain profiles, secrets, OAuth tokens, sermon_plan.json, "
                    "ptz_camera_config.json, recordings, Event History, or Recovery snapshots.\n"
                ),
            )

            for source, relative in files:
                archive.write(
                    source,
                    arcname=str(
                        relative
                    ).replace(
                        "\\",
                        "/"
                    ),
                )

    finally:
        import shutil

        try:
            shutil.rmtree(
                work
            )
        except Exception:
            pass

    print()
    print(
        "SIGNED update package created:"
    )
    print(
        output
    )
    print()
    print(
        "Files:",
        len(
            manifest_files
        ),
    )
    print(
        "Version:",
        APP_VERSION,
    )
    print(
        "Manifest signer:",
        signer_thumb,
    )
    print(
        "Profiles/secrets/user data included: NO"
    )

    return output


if __name__ == "__main__":
    build_update_package()
