import datetime
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import zipfile
from pathlib import (
    Path,
    PurePosixPath,
)

from sss_build_info import (
    APP_ID,
    APP_VERSION,
)
from sss_recovery import restore_safety_status
from sss_runtime import (
    MAIN_EXE_NAME,
    SETTINGS_EXE_NAME,
)

from sss_release_trust import (
    SIGNED_UPDATES_REQUIRED,
    TRUSTED_UPDATE_SIGNER_THUMBPRINTS,
)
from sss_signing import (
    normalize_thumbprint,
    verify_authenticode_file,
    verify_manifest_cms,
)



UPDATE_PACKAGE_FORMAT = 2

MAIN_DIR_NAME = "SundayServiceSystem"
SETTINGS_DIR_NAME = "SundayServiceSystemSettings"
UPDATER_DIR_NAME = "SundayServiceSystemUpdater"

PROGRAM_DATA = Path(
    os.environ.get(
        "PROGRAMDATA",
        r"C:\ProgramData"
    )
)

UPDATE_ROOT = (
    PROGRAM_DATA
    /
    "Sunday Service System"
    /
    "Updates"
)

ROLLBACK_ROOT = (
    UPDATE_ROOT
    /
    "Rollbacks"
)

STAGING_ROOT = (
    UPDATE_ROOT
    /
    "Staging"
)

HEALTH_ROOT = (
    UPDATE_ROOT
    /
    "Health"
)

UPDATE_STATE_FILE = (
    UPDATE_ROOT
    /
    "update_state.json"
)


def _now():
    return datetime.datetime.now().astimezone()


def _now_iso():
    return _now().isoformat()


def _stamp():
    return _now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )


def _safe_slug(value):
    text = "".join(
        char
        if (
            char.isalnum()
            or
            char in {
                "-",
                "_",
                ".",
            }
        )
        else
        "_"
        for char in str(
            value
            or
            "value"
        )
    )

    while "__" in text:
        text = text.replace(
            "__",
            "_"
        )

    return (
        text.strip(
            "_"
        )
        or
        "value"
    )


def ensure_update_dirs():
    for path in (
        UPDATE_ROOT,
        ROLLBACK_ROOT,
        STAGING_ROOT,
        HEALTH_ROOT,
    ):
        path.mkdir(
            parents=True,
            exist_ok=True,
        )


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


def load_update_state():
    try:
        payload = json.loads(
            UPDATE_STATE_FILE.read_text(
                encoding="utf-8"
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


def save_update_state(
    payload
):
    ensure_update_dirs()

    data = dict(
        payload
        or
        {}
    )

    data[
        "updated_at"
    ] = _now_iso()

    _write_json_atomic(
        UPDATE_STATE_FILE,
        data,
    )

    return data


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
            char
            for char in token
            if char.isdigit()
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


def version_is_newer(
    candidate,
    current
):
    return (
        _version_tuple(
            candidate
        )
        >
        _version_tuple(
            current
        )
    )


def _validate_archive_members(
    archive,
    *,
    manifest=None
):
    infos = archive.infolist()

    names = set()

    for info in infos:
        raw = str(
            info.filename
            or
            ""
        ).replace(
            "\\",
            "/"
        )

        if not raw:
            raise RuntimeError(
                "Update package contains a blank archive path."
            )

        path = PurePosixPath(
            raw
        )

        if (
            path.is_absolute()
            or
            ".."
            in
            path.parts
        ):
            raise RuntimeError(
                (
                    "Unsafe path in update package: "
                    +
                    raw
                )
            )

        unix_mode = (
            info.external_attr
            >>
            16
        )

        if stat.S_ISLNK(
            unix_mode
        ):
            raise RuntimeError(
                (
                    "Update package contains an unsupported symbolic link: "
                    +
                    raw
                )
            )

        names.add(
            raw.rstrip(
                "/"
            )
        )

    if manifest is None:
        return names

    expected_files = {
        str(
            entry.get(
                "path",
                ""
            )
        ).replace(
            "\\",
            "/"
        ).lstrip(
            "/"
        )
        for entry in manifest.get(
            "files",
            []
        )
    }

    allowed_files = (
        expected_files
        |
        {
            "manifest.json",
            "manifest.p7s",
            "README.txt",
        }
    )

    archive_files = {
        str(
            info.filename
        ).replace(
            "\\",
            "/"
        ).rstrip(
            "/"
        )
        for info in infos
        if not info.is_dir()
    }

    extras = sorted(
        archive_files
        -
        allowed_files
    )

    if extras:
        raise RuntimeError(
            (
                "Update package contains unmanifested file(s): "
                +
                ", ".join(
                    extras[
                        :10
                    ]
                )
            )
        )

    missing = sorted(
        expected_files
        -
        archive_files
    )

    if missing:
        raise RuntimeError(
            (
                "Update package manifest references missing file(s): "
                +
                ", ".join(
                    missing[
                        :10
                    ]
                )
            )
        )

    for relative in expected_files:
        if not (
            relative.startswith(
                "payload/"
                +
                MAIN_DIR_NAME
                +
                "/"
            )
            or
            relative.startswith(
                "payload/"
                +
                SETTINGS_DIR_NAME
                +
                "/"
            )
            or
            relative.startswith(
                "payload/"
                +
                UPDATER_DIR_NAME
                +
                "/"
            )
        ):
            raise RuntimeError(
                (
                    "Update payload targets an unsupported application area: "
                    +
                    relative
                )
            )

    return names


def read_update_manifest(
    package_path
):
    package_path = Path(
        package_path
    )

    if not package_path.exists():
        raise FileNotFoundError(
            str(
                package_path
            )
        )

    with zipfile.ZipFile(
        package_path,
        "r"
    ) as archive:
        _validate_archive_members(
            archive
        )

        try:
            raw = archive.read(
                "manifest.json"
            )
        except KeyError as exc:
            raise RuntimeError(
                "Update package has no manifest.json."
            ) from exc

    manifest = json.loads(
        raw.decode(
            "utf-8"
        )
    )

    if not isinstance(
        manifest,
        dict
    ):
        raise RuntimeError(
            "Update manifest is not a JSON object."
        )

    if int(
        manifest.get(
            "package_format",
            0
        )
        or
        0
    ) != UPDATE_PACKAGE_FORMAT:
        raise RuntimeError(
            (
                "Unsupported SSS update package format: "
                +
                str(
                    manifest.get(
                        "package_format",
                        ""
                    )
                )
            )
        )

    if str(
        manifest.get(
            "app_id",
            ""
        )
    ) != APP_ID:
        raise RuntimeError(
            "Update package is not for Sunday Service System."
        )

    version = str(
        manifest.get(
            "version",
            ""
        )
    ).strip()

    if not version:
        raise RuntimeError(
            "Update package has no version."
        )

    roots = manifest.get(
        "payload_roots",
        []
    )

    if not isinstance(
        roots,
        list
    ):
        raise RuntimeError(
            "Update payload_roots is invalid."
        )

    required = {
        MAIN_DIR_NAME,
        SETTINGS_DIR_NAME,
        UPDATER_DIR_NAME,
    }

    if not required.issubset(
        set(
            roots
        )
    ):
        raise RuntimeError(
            (
                "Update package must contain Main, Settings, and Updater "
                "application folders."
            )
        )

    files = manifest.get(
        "files",
        []
    )

    if not isinstance(
        files,
        list
    ) or not files:
        raise RuntimeError(
            "Update package file list is empty."
        )

    if SIGNED_UPDATES_REQUIRED:
        if not bool(
            manifest.get(
                "signed"
            )
        ):
            raise RuntimeError(
                (
                    "This Sunday Service System build requires a cryptographically "
                    "signed update manifest. The selected package is unsigned."
                )
            )

        if str(
            manifest.get(
                "signature_format",
                ""
            )
        ).upper() not in {
            "CMS/PKCS#7 DETACHED",
            "CMS/PKCS7 DETACHED",
        }:
            raise RuntimeError(
                "Update package uses an unsupported manifest signature format."
            )

        signer = normalize_thumbprint(
            manifest.get(
                "signer_thumbprint",
                ""
            )
        )

        if not signer:
            raise RuntimeError(
                "Signed update manifest does not declare its signer thumbprint."
            )

        trusted = {
            normalize_thumbprint(
                item
            )
            for item in TRUSTED_UPDATE_SIGNER_THUMBPRINTS
            if normalize_thumbprint(
                item
            )
        }

        if (
            not trusted
            or
            signer not in trusted
        ):
            raise RuntimeError(
                (
                    "Update package declares a signer that this installed SSS "
                    "build does not trust.\nSigner: "
                    +
                    signer
                )
            )

    return manifest


def verify_update_package(
    package_path
):
    package_path = Path(
        package_path
    )

    manifest = read_update_manifest(
        package_path
    )

    with tempfile.TemporaryDirectory(
        prefix="sss_update_verify_"
    ) as temp_dir:
        temp_root = Path(
            temp_dir
        )

        with zipfile.ZipFile(
            package_path,
            "r"
        ) as archive:
            _validate_archive_members(
                archive,
                manifest=manifest,
            )

            archive.extractall(
                temp_root
            )

        for entry in manifest.get(
            "files",
            []
        ):
            relative = str(
                entry.get(
                    "path",
                    ""
                )
            ).replace(
                "\\",
                "/"
            ).lstrip(
                "/"
            )

            if not relative:
                raise RuntimeError(
                    "Update manifest contains a blank file path."
                )

            candidate = (
                temp_root
                /
                relative
            ).resolve()

            try:
                candidate.relative_to(
                    temp_root.resolve()
                )
            except Exception as exc:
                raise RuntimeError(
                    (
                        "Unsafe path in update package: "
                        +
                        relative
                    )
                ) from exc

            if not candidate.is_file():
                raise RuntimeError(
                    (
                        "Update package is missing: "
                        +
                        relative
                    )
                )

            expected = str(
                entry.get(
                    "sha256",
                    ""
                )
            ).lower()

            actual = _sha256(
                candidate
            ).lower()

            if (
                not expected
                or
                actual
                !=
                expected
            ):
                raise RuntimeError(
                    (
                        "Update checksum failed: "
                        +
                        relative
                    )
                )

            expected_size = int(
                entry.get(
                    "size",
                    -1
                )
            )

            if (
                expected_size
                >=
                0
                and
                candidate.stat().st_size
                !=
                expected_size
            ):
                raise RuntimeError(
                    (
                        "Update size check failed: "
                        +
                        relative
                    )
                )

        signature_file = (
            temp_root
            /
            "manifest.p7s"
        )

        if SIGNED_UPDATES_REQUIRED:
            if not signature_file.is_file():
                raise RuntimeError(
                    "Signed update package is missing manifest.p7s."
                )

            signature_result = verify_manifest_cms(
                temp_root
                /
                "manifest.json",
                signature_file,
                trusted_thumbprints=TRUSTED_UPDATE_SIGNER_THUMBPRINTS,
                require_trusted=True,
            )

            declared_signer = normalize_thumbprint(
                manifest.get(
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

            if actual_signer != declared_signer:
                raise RuntimeError(
                    (
                        "Signed update manifest signer mismatch.\n"
                        "Declared: "
                        +
                        declared_signer
                        +
                        "\nActual: "
                        +
                        actual_signer
                    )
                )

            required_signed_exes = (
                temp_root
                /
                "payload"
                /
                MAIN_DIR_NAME
                /
                MAIN_EXE_NAME,

                temp_root
                /
                "payload"
                /
                SETTINGS_DIR_NAME
                /
                SETTINGS_EXE_NAME,

                temp_root
                /
                "payload"
                /
                UPDATER_DIR_NAME
                /
                "SundayServiceSystemUpdater.exe",
            )

            executable_signatures = []

            for executable in required_signed_exes:
                if not executable.is_file():
                    raise RuntimeError(
                        (
                            "Signed update package is missing required EXE: "
                            +
                            str(
                                executable
                            )
                        )
                    )

                executable_signatures.append(
                    verify_authenticode_file(
                        executable,
                        trusted_thumbprints=TRUSTED_UPDATE_SIGNER_THUMBPRINTS,
                        require_valid=True,
                    )
                )

            manifest[
                "_signature_verification"
            ] = {
                "manifest": signature_result,
                "executables": executable_signatures,
            }

    return manifest


def _wait_for_pid_exit(
    pid,
    *,
    timeout=30
):
    try:
        pid = int(
            pid
        )
    except Exception:
        return True

    if pid <= 0:
        return True

    deadline = (
        time.monotonic()
        +
        float(
            timeout
        )
    )

    while time.monotonic() < deadline:
        if os.name == "nt":
            cp = subprocess.run(
                [
                    "tasklist",
                    "/FI",
                    (
                        "PID eq "
                        +
                        str(
                            pid
                        )
                    ),
                    "/NH",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0
                ),
            )

            text = (
                cp.stdout
                or
                ""
            )

            if str(
                pid
            ) not in text:
                return True

        else:
            try:
                os.kill(
                    pid,
                    0,
                )
            except Exception:
                return True

        time.sleep(
            0.5
        )

    return False


def _processes_under_install_root(
    install_root,
    *,
    exclude_pid=None
):
    if os.name != "nt":
        return []

    install_root = str(
        Path(
            install_root
        ).resolve()
    ).replace(
        "'",
        "''"
    )

    ps = (
        "$root='"
        +
        install_root
        +
        "'; "
        "$items = Get-CimInstance Win32_Process | "
        "Where-Object { $_.ExecutablePath -and "
        "$_.ExecutablePath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase) } | "
        "Select-Object ProcessId, Name, ExecutablePath; "
        "$items | ConvertTo-Json -Compress"
    )

    try:
        cp = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                ps,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            ),
        )

        raw = (
            cp.stdout
            or
            ""
        ).strip()

        if not raw:
            return []

        payload = json.loads(
            raw
        )

        if isinstance(
            payload,
            dict
        ):
            payload = [
                payload
            ]

        if not isinstance(
            payload,
            list
        ):
            return []

        results = []

        for item in payload:
            try:
                item_pid = int(
                    item.get(
                        "ProcessId",
                        0
                    )
                    or
                    0
                )
            except Exception:
                item_pid = 0

            if (
                exclude_pid is not None
                and
                item_pid
                ==
                int(
                    exclude_pid
                )
            ):
                continue

            results.append(
                item
            )

        return results

    except Exception:
        return []


def installed_app_processes(
    install_root,
    *,
    exclude_pid=None
):
    return _processes_under_install_root(
        install_root,
        exclude_pid=exclude_pid,
    )


def _safe_remove_tree(
    path
):
    path = Path(
        path
    )

    if not path.exists():
        return

    last_error = None

    for _attempt in range(
        5
    ):
        try:
            shutil.rmtree(
                path
            )

            return

        except Exception as exc:
            last_error = exc
            time.sleep(
                0.75
            )

    raise RuntimeError(
        (
            "Could not remove application folder:\n"
            +
            str(
                path
            )
            +
            "\n\n"
            +
            str(
                last_error
            )
        )
    )


def _copy_app_tree(
    source,
    destination
):
    source = Path(
        source
    )

    destination = Path(
        destination
    )

    if destination.exists():
        _safe_remove_tree(
            destination
        )

    shutil.copytree(
        source,
        destination,
    )


def _log_event(
    message,
    *,
    level="ACTION",
    metadata=None
):
    try:
        from sss_event_history import record_event

        record_event(
            message,
            category="UPDATES",
            level=level,
            source="UPDATER",
            metadata=metadata,
        )

    except Exception:
        pass


def _stage_package(
    package_path,
    manifest
):
    ensure_update_dirs()

    stage = (
        STAGING_ROOT
        /
        (
            "update_"
            +
            _safe_slug(
                manifest.get(
                    "version",
                    "version"
                )
            )
            +
            "_"
            +
            _stamp()
        )
    )

    stage.mkdir(
        parents=True,
        exist_ok=False,
    )

    with zipfile.ZipFile(
        package_path,
        "r"
    ) as archive:
        _validate_archive_members(
            archive,
            manifest=manifest,
        )

        archive.extractall(
            stage
        )

    return stage


def _backup_file_manifest(
    backup_dir
):
    backup_dir = Path(
        backup_dir
    )

    files = []

    for folder_name in (
        MAIN_DIR_NAME,
        SETTINGS_DIR_NAME,
        UPDATER_DIR_NAME,
    ):
        root = (
            backup_dir
            /
            folder_name
        )

        for path in sorted(
            root.rglob(
                "*"
            )
        ):
            if not path.is_file():
                continue

            relative = path.relative_to(
                backup_dir
            )

            files.append(
                {
                    "path": str(
                        relative
                    ).replace(
                        "\\",
                        "/"
                    ),
                    "size": path.stat().st_size,
                    "sha256": _sha256(
                        path
                    ),
                }
            )

    return files


def _verify_backup_integrity(
    backup_dir
):
    backup_dir = Path(
        backup_dir
    )

    manifest_path = (
        backup_dir
        /
        "rollback_manifest.json"
    )

    if not manifest_path.exists():
        # v2.9 is the first version of this backup format. Refuse an unknown
        # folder instead of guessing.
        raise RuntimeError(
            (
                "Rollback backup has no rollback_manifest.json:\n"
                +
                str(
                    backup_dir
                )
            )
        )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    files = manifest.get(
        "files",
        []
    )

    if not isinstance(
        files,
        list
    ) or not files:
        raise RuntimeError(
            "Rollback backup manifest has no file integrity list."
        )

    for entry in files:
        relative = Path(
            str(
                entry.get(
                    "path",
                    ""
                )
            )
        )

        source = (
            backup_dir
            /
            relative
        ).resolve()

        try:
            source.relative_to(
                backup_dir.resolve()
            )
        except Exception as exc:
            raise RuntimeError(
                (
                    "Unsafe path in rollback backup: "
                    +
                    str(
                        relative
                    )
                )
            ) from exc

        if not source.is_file():
            raise RuntimeError(
                (
                    "Rollback backup is missing: "
                    +
                    str(
                        relative
                    )
                )
            )

        if source.stat().st_size != int(
            entry.get(
                "size",
                -1
            )
        ):
            raise RuntimeError(
                (
                    "Rollback backup size check failed: "
                    +
                    str(
                        relative
                    )
                )
            )

        if _sha256(
            source
        ).lower() != str(
            entry.get(
                "sha256",
                ""
            )
        ).lower():
            raise RuntimeError(
                (
                    "Rollback backup checksum failed: "
                    +
                    str(
                        relative
                    )
                )
            )

    return manifest


def _verify_installed_against_backup(
    *,
    install_root,
    backup_dir
):
    manifest = _verify_backup_integrity(
        backup_dir
    )

    install_root = Path(
        install_root
    )

    for entry in manifest.get(
        "files",
        []
    ):
        relative = Path(
            str(
                entry.get(
                    "path",
                    ""
                )
            )
        )

        installed = (
            install_root
            /
            relative
        )

        if not installed.is_file():
            raise RuntimeError(
                (
                    "Restored application is missing: "
                    +
                    str(
                        relative
                    )
                )
            )

        if installed.stat().st_size != int(
            entry.get(
                "size",
                -1
            )
        ):
            raise RuntimeError(
                (
                    "Restored application size check failed: "
                    +
                    str(
                        relative
                    )
                )
            )

        if _sha256(
            installed
        ).lower() != str(
            entry.get(
                "sha256",
                ""
            )
        ).lower():
            raise RuntimeError(
                (
                    "Restored application checksum failed: "
                    +
                    str(
                        relative
                    )
                )
            )

    return manifest


def _create_rollback_backup(
    install_root,
    *,
    from_version,
    to_version
):
    ensure_update_dirs()

    backup = (
        ROLLBACK_ROOT
        /
        (
            "from_"
            +
            _safe_slug(
                from_version
            )
            +
            "_before_"
            +
            _safe_slug(
                to_version
            )
            +
            "_"
            +
            _stamp()
        )
    )

    backup.mkdir(
        parents=True,
        exist_ok=False,
    )

    install_root = Path(
        install_root
    )

    for folder_name in (
        MAIN_DIR_NAME,
        SETTINGS_DIR_NAME,
        UPDATER_DIR_NAME,
    ):
        source = (
            install_root
            /
            folder_name
        )

        if not source.is_dir():
            raise RuntimeError(
                (
                    "Installed application folder is missing:\n"
                    +
                    str(
                        source
                    )
                )
            )

        shutil.copytree(
            source,
            backup
            /
            folder_name,
        )

    backup_manifest = {
        "created_at": _now_iso(),
        "from_version": from_version,
        "before_version": to_version,
        "install_root": str(
            install_root
        ),
        "folders": [
            MAIN_DIR_NAME,
            SETTINGS_DIR_NAME,
            UPDATER_DIR_NAME,
        ],
        "files": _backup_file_manifest(
            backup
        ),
    }

    _write_json_atomic(
        backup
        /
        "rollback_manifest.json",
        backup_manifest,
    )

    return backup


def _replace_installed_app(
    *,
    install_root,
    staged_root
):
    install_root = Path(
        install_root
    )

    staged_root = Path(
        staged_root
    )

    for folder_name in (
        MAIN_DIR_NAME,
        SETTINGS_DIR_NAME,
        UPDATER_DIR_NAME,
    ):
        source = (
            staged_root
            /
            "payload"
            /
            folder_name
        )

        destination = (
            install_root
            /
            folder_name
        )

        if not source.is_dir():
            raise RuntimeError(
                (
                    "Update staging folder is missing:\n"
                    +
                    str(
                        source
                    )
                )
            )

        _safe_remove_tree(
            destination
        )

        _copy_app_tree(
            source,
            destination,
        )


def _restore_backup(
    *,
    install_root,
    backup_dir
):
    install_root = Path(
        install_root
    )

    backup_dir = Path(
        backup_dir
    )

    _verify_backup_integrity(
        backup_dir
    )

    for folder_name in (
        MAIN_DIR_NAME,
        SETTINGS_DIR_NAME,
        UPDATER_DIR_NAME,
    ):
        source = (
            backup_dir
            /
            folder_name
        )

        destination = (
            install_root
            /
            folder_name
        )

        if not source.is_dir():
            raise RuntimeError(
                (
                    "Rollback backup is incomplete:\n"
                    +
                    str(
                        source
                    )
                )
            )

        _safe_remove_tree(
            destination
        )

        _copy_app_tree(
            source,
            destination,
        )

    _verify_installed_against_backup(
        install_root=install_root,
        backup_dir=backup_dir,
    )


def _verify_installed_against_update_manifest(
    *,
    install_root,
    manifest
):
    install_root = Path(
        install_root
    )

    for entry in manifest.get(
        "files",
        []
    ):
        relative_text = str(
            entry.get(
                "path",
                ""
            )
        ).replace(
            "\\",
            "/"
        )

        prefix = "payload/"

        if not relative_text.startswith(
            prefix
        ):
            raise RuntimeError(
                (
                    "Unexpected update manifest path during post-install verification: "
                    +
                    relative_text
                )
            )

        installed_relative = Path(
            relative_text[
                len(
                    prefix
                ):
            ]
        )

        installed = (
            install_root
            /
            installed_relative
        )

        if not installed.is_file():
            raise RuntimeError(
                (
                    "Installed update is missing file: "
                    +
                    str(
                        installed_relative
                    )
                )
            )

        if installed.stat().st_size != int(
            entry.get(
                "size",
                -1
            )
        ):
            raise RuntimeError(
                (
                    "Installed update size verification failed: "
                    +
                    str(
                        installed_relative
                    )
                )
            )

        if _sha256(
            installed
        ).lower() != str(
            entry.get(
                "sha256",
                ""
            )
        ).lower():
            raise RuntimeError(
                (
                    "Installed update SHA-256 verification failed: "
                    +
                    str(
                        installed_relative
                    )
                )
            )

    return True


def _run_health_check(
    *,
    install_root,
    expected_version,
    timeout=30
):
    ensure_update_dirs()

    health_file = (
        HEALTH_ROOT
        /
        (
            "health_"
            +
            _safe_slug(
                expected_version
            )
            +
            "_"
            +
            _stamp()
            +
            ".json"
        )
    )

    main_exe = (
        Path(
            install_root
        )
        /
        MAIN_DIR_NAME
        /
        MAIN_EXE_NAME
    )

    if not main_exe.exists():
        return {
            "ok": False,
            "detail": (
                "Updated main EXE is missing: "
                +
                str(
                    main_exe
                )
            ),
        }

    try:
        cp = subprocess.run(
            [
                str(
                    main_exe
                ),
                "--update-health-check",
                str(
                    health_file
                ),
                "--expected-version",
                str(
                    expected_version
                ),
            ],
            cwd=str(
                Path(
                    r"C:\Church\SermonAI"
                )
            ),
            capture_output=True,
            text=True,
            timeout=float(
                timeout
            ),
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            ),
        )

    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "detail": (
                "Updated application health check timed out."
            ),
        }

    except Exception as exc:
        return {
            "ok": False,
            "detail": (
                "Updated application could not start for health check: "
                +
                str(
                    exc
                )
            ),
        }

    if cp.returncode != 0:
        return {
            "ok": False,
            "detail": (
                "Updated application health check exited with code "
                +
                str(
                    cp.returncode
                )
                +
                ". "
                +
                (
                    cp.stderr.strip()
                    or
                    cp.stdout.strip()
                    or
                    "No additional output."
                )
            ),
        }

    if not health_file.exists():
        return {
            "ok": False,
            "detail": (
                "Updated application did not create the expected health result."
            ),
        }

    try:
        result = json.loads(
            health_file.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        return {
            "ok": False,
            "detail": (
                "Updated application health result is invalid: "
                +
                str(
                    exc
                )
            ),
        }

    if not isinstance(
        result,
        dict
    ):
        return {
            "ok": False,
            "detail": (
                "Updated application health result is not a JSON object."
            ),
        }

    if not bool(
        result.get(
            "ok"
        )
    ):
        return {
            "ok": False,
            "detail": str(
                result.get(
                    "detail",
                    "Updated application reported an unhealthy startup."
                )
            ),
        }

    reported_version = str(
        result.get(
            "version",
            ""
        )
    )

    if (
        reported_version
        !=
        str(
            expected_version
        )
    ):
        return {
            "ok": False,
            "detail": (
                "Updated application reported version "
                +
                reported_version
                +
                " but "
                +
                str(
                    expected_version
                )
                +
                " was expected."
            ),
        }

    return {
        "ok": True,
        "detail": (
            "Updated application started and passed the safe startup health check."
        ),
        "health_file": str(
            health_file
        ),
        "result": result,
    }


def _launch_settings_after_update(
    install_root
):
    settings_exe = (
        Path(
            install_root
        )
        /
        SETTINGS_DIR_NAME
        /
        SETTINGS_EXE_NAME
    )

    if not settings_exe.exists():
        return False

    try:
        subprocess.Popen(
            [
                str(
                    settings_exe
                ),
                "--updates",
            ],
            cwd=str(
                Path(
                    r"C:\Church\SermonAI"
                )
            ),
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0
            ),
        )

        return True

    except Exception:
        return False


def apply_update(
    *,
    package_path,
    install_root,
    current_version,
    parent_pid=None,
    allow_same_version=False,
    progress=None
):
    package_path = Path(
        package_path
    )

    install_root = Path(
        install_root
    )

    def report(
        message
    ):
        if callable(
            progress
        ):
            progress(
                str(
                    message
                )
            )

    report(
        "Waiting for SSS Settings to close…"
    )

    if parent_pid:
        if not _wait_for_pid_exit(
            parent_pid,
            timeout=45,
        ):
            raise RuntimeError(
                "SSS Settings did not close in time. Update was not started."
            )

    blockers = installed_app_processes(
        install_root,
        exclude_pid=os.getpid(),
    )

    if blockers:
        detail = []

        for item in blockers:
            detail.append(
                (
                    str(
                        item.get(
                            "Name",
                            "SSS process"
                        )
                    )
                    +
                    " (PID "
                    +
                    str(
                        item.get(
                            "ProcessId",
                            "?"
                        )
                    )
                    +
                    ")"
                )
            )

        raise RuntimeError(
            (
                "Close all Sunday Service System windows before updating:\n"
                +
                "\n".join(
                    detail
                )
                +
                "\n\nOBS does not need to be closed unless its live output "
                "state cannot be verified."
            )
        )

    report(
        "Checking live-service safety…"
    )

    safety = restore_safety_status()

    if not safety.get(
        "safe"
    ):
        raise RuntimeError(
            (
                "Update blocked for live-service safety.\n\n"
                +
                str(
                    safety.get(
                        "detail",
                        ""
                    )
                )
            )
        )

    report(
        "Verifying update package checksums…"
    )

    manifest = verify_update_package(
        package_path
    )

    to_version = str(
        manifest.get(
            "version"
        )
    )

    if (
        not allow_same_version
        and
        not version_is_newer(
            to_version,
            current_version
        )
    ):
        raise RuntimeError(
            (
                "Update package "
                +
                to_version
                +
                " is not newer than installed version "
                +
                str(
                    current_version
                )
                +
                "."
            )
        )

    report(
        (
            "Staging Sunday Service System "
            +
            to_version
            +
            "…"
        )
    )

    stage = _stage_package(
        package_path,
        manifest,
    )

    backup = None

    state = {
        "operation": "update",
        "status": "STARTING",
        "started_at": _now_iso(),
        "from_version": str(
            current_version
        ),
        "to_version": to_version,
        "package": str(
            package_path
        ),
        "install_root": str(
            install_root
        ),
        "rollback_dir": "",
        "automatic_rollback": False,
        "detail": "",
    }

    save_update_state(
        state
    )

    try:
        report(
            "Creating automatic pre-update application backup…"
        )

        backup = _create_rollback_backup(
            install_root,
            from_version=str(
                current_version
            ),
            to_version=to_version,
        )

        state[
            "rollback_dir"
        ] = str(
            backup
        )

        state[
            "status"
        ] = "BACKED_UP"

        save_update_state(
            state
        )

        report(
            "Installing updated application files…"
        )

        _replace_installed_app(
            install_root=install_root,
            staged_root=stage,
        )

        report(
            "Verifying installed application files against the signed manifest…"
        )

        _verify_installed_against_update_manifest(
            install_root=install_root,
            manifest=manifest,
        )

        state[
            "status"
        ] = "FILES_INSTALLED"

        save_update_state(
            state
        )

        report(
            "Running safe post-update startup verification…"
        )

        health = _run_health_check(
            install_root=install_root,
            expected_version=to_version,
        )

        if not health.get(
            "ok"
        ):
            raise RuntimeError(
                (
                    "Post-update verification failed.\n\n"
                    +
                    str(
                        health.get(
                            "detail",
                            ""
                        )
                    )
                )
            )

        state[
            "status"
        ] = "SUCCESS"

        state[
            "completed_at"
        ] = _now_iso()

        state[
            "health"
        ] = health

        state[
            "detail"
        ] = (
            "Update installed successfully and passed startup verification."
        )

        save_update_state(
            state
        )

        _log_event(
            (
                "Sunday Service System updated successfully: "
                +
                str(
                    current_version
                )
                +
                " -> "
                +
                to_version
                +
                "."
            ),
            metadata={
                "rollback_dir": str(
                    backup
                ),
            },
        )

        report(
            "Update verified successfully."
        )

        _launch_settings_after_update(
            install_root
        )

        return state

    except Exception as exc:
        failure = str(
            exc
        )

        if backup is not None:
            report(
                "Update failed — automatically restoring the previous application version…"
            )

            try:
                _restore_backup(
                    install_root=install_root,
                    backup_dir=backup,
                )

                state[
                    "status"
                ] = "ROLLED_BACK"

                state[
                    "automatic_rollback"
                ] = True

                state[
                    "completed_at"
                ] = _now_iso()

                state[
                    "detail"
                ] = (
                    "Update failed and the previous installed application was restored. "
                    +
                    failure
                )

                save_update_state(
                    state
                )

                _log_event(
                    (
                        "SSS update failed and automatic rollback restored version "
                        +
                        str(
                            current_version
                        )
                        +
                        "."
                    ),
                    level="WARNING",
                    metadata={
                        "failed_version": to_version,
                        "detail": failure,
                    },
                )

                _launch_settings_after_update(
                    install_root
                )

                return state

            except Exception as rollback_exc:
                state[
                    "status"
                ] = "ROLLBACK_FAILED"

                state[
                    "automatic_rollback"
                ] = True

                state[
                    "completed_at"
                ] = _now_iso()

                state[
                    "detail"
                ] = (
                    "Update failed, and automatic rollback also failed.\n"
                    +
                    failure
                    +
                    "\nRollback error: "
                    +
                    str(
                        rollback_exc
                    )
                )

                save_update_state(
                    state
                )

                _log_event(
                    (
                        "SSS update and automatic rollback both failed."
                    ),
                    level="WARNING",
                    metadata={
                        "detail": state[
                            "detail"
                        ],
                    },
                )

                raise RuntimeError(
                    state[
                        "detail"
                    ]
                ) from rollback_exc

        state[
            "status"
        ] = "FAILED"

        state[
            "completed_at"
        ] = _now_iso()

        state[
            "detail"
        ] = failure

        save_update_state(
            state
        )

        raise

    finally:
        try:
            _safe_remove_tree(
                stage
            )
        except Exception:
            pass


def rollback_last_update(
    *,
    install_root,
    parent_pid=None,
    progress=None
):
    install_root = Path(
        install_root
    )

    def report(
        message
    ):
        if callable(
            progress
        ):
            progress(
                str(
                    message
                )
            )

    state = load_update_state()

    backup_text = str(
        state.get(
            "rollback_dir",
            ""
        )
    ).strip()

    if not backup_text:
        raise RuntimeError(
            "No rollback backup is recorded for the last update."
        )

    backup = Path(
        backup_text
    )

    if not backup.is_dir():
        raise RuntimeError(
            (
                "The recorded rollback folder no longer exists:\n"
                +
                str(
                    backup
                )
            )
        )

    report(
        "Waiting for SSS Settings to close…"
    )

    if parent_pid:
        if not _wait_for_pid_exit(
            parent_pid,
            timeout=45,
        ):
            raise RuntimeError(
                "SSS Settings did not close in time. Rollback was not started."
            )

    blockers = installed_app_processes(
        install_root,
        exclude_pid=os.getpid(),
    )

    if blockers:
        raise RuntimeError(
            "Close all Sunday Service System windows before rollback."
        )

    report(
        "Checking live-service safety…"
    )

    safety = restore_safety_status()

    if not safety.get(
        "safe"
    ):
        raise RuntimeError(
            (
                "Rollback blocked for live-service safety.\n\n"
                +
                str(
                    safety.get(
                        "detail",
                        ""
                    )
                )
            )
        )

    current_backup = _create_rollback_backup(
        install_root,
        from_version=str(
            state.get(
                "to_version",
                APP_VERSION
            )
        ),
        to_version=(
            "manual_rollback_to_"
            +
            str(
                state.get(
                    "from_version",
                    "previous"
                )
            )
        ),
    )

    rollback_state = {
        "operation": "manual_rollback",
        "status": "STARTING",
        "started_at": _now_iso(),
        "from_version": str(
            state.get(
                "to_version",
                APP_VERSION
            )
        ),
        "to_version": str(
            state.get(
                "from_version",
                "previous"
            )
        ),
        "install_root": str(
            install_root
        ),
        "rollback_dir": str(
            current_backup
        ),
        "source_backup": str(
            backup
        ),
        "automatic_rollback": False,
        "detail": "",
    }

    save_update_state(
        rollback_state
    )

    try:
        report(
            "Restoring previous installed application version…"
        )

        _restore_backup(
            install_root=install_root,
            backup_dir=backup,
        )

        expected_version = str(
            state.get(
                "from_version",
                ""
            )
        )

        if (
            expected_version
            and
            _version_tuple(
                expected_version
            )
            >=
            _version_tuple(
                "2.9.0"
            )
        ):
            report(
                "Verifying restored application startup…"
            )

            health = _run_health_check(
                install_root=install_root,
                expected_version=expected_version,
            )

            if not health.get(
                "ok"
            ):
                raise RuntimeError(
                    (
                        "Rollback startup verification failed.\n\n"
                        +
                        str(
                            health.get(
                                "detail",
                                ""
                            )
                        )
                    )
                )

            rollback_state[
                "health"
            ] = health

        else:
            rollback_state[
                "health"
            ] = {
                "ok": True,
                "detail": (
                    "Restored application files passed rollback SHA-256 checks. "
                    "The restored version predates the v2.9 safe health-check protocol."
                ),
                "legacy_pre_health_check": True,
            }

        rollback_state[
            "status"
        ] = "SUCCESS"

        rollback_state[
            "completed_at"
        ] = _now_iso()

        rollback_state[
            "detail"
        ] = (
            "Previous application version restored successfully."
        )

        save_update_state(
            rollback_state
        )

        _log_event(
            (
                "Sunday Service System manually rolled back to version "
                +
                str(
                    rollback_state.get(
                        "to_version",
                        "previous"
                    )
                )
                +
                "."
            )
        )

        _launch_settings_after_update(
            install_root
        )

        return rollback_state

    except Exception as exc:
        report(
            "Rollback failed — restoring the application state from immediately before rollback…"
        )

        try:
            _restore_backup(
                install_root=install_root,
                backup_dir=current_backup,
            )

            rollback_state[
                "status"
            ] = "ROLLED_BACK_ROLLBACK"

            rollback_state[
                "completed_at"
            ] = _now_iso()

            rollback_state[
                "detail"
            ] = (
                "Requested rollback failed; the pre-rollback application state "
                "was restored. "
                +
                str(
                    exc
                )
            )

            save_update_state(
                rollback_state
            )

            _launch_settings_after_update(
                install_root
            )

            return rollback_state

        except Exception as recovery_exc:
            rollback_state[
                "status"
            ] = "ROLLBACK_FAILED"

            rollback_state[
                "completed_at"
            ] = _now_iso()

            rollback_state[
                "detail"
            ] = (
                "Requested rollback failed, and restoring the pre-rollback "
                "application state also failed.\n"
                +
                str(
                    exc
                )
                +
                "\nRecovery error: "
                +
                str(
                    recovery_exc
                )
            )

            save_update_state(
                rollback_state
            )

            raise RuntimeError(
                rollback_state[
                    "detail"
                ]
            ) from recovery_exc


def update_status(
    *,
    install_root=None
):
    ensure_update_dirs()

    state = load_update_state()

    rollbacks = []

    for path in sorted(
        ROLLBACK_ROOT.glob(
            "*"
        ),
        reverse=True,
    ):
        if path.is_dir():
            rollbacks.append(
                str(
                    path
                )
            )

    return {
        "current_build_version": APP_VERSION,
        "install_root": (
            str(
                install_root
            )
            if install_root is not None
            else
            ""
        ),
        "state": state,
        "rollback_available": bool(
            state.get(
                "rollback_dir"
            )
            and
            Path(
                str(
                    state.get(
                        "rollback_dir"
                    )
                )
            ).is_dir()
        ),
        "rollback_count": len(
            rollbacks
        ),
        "update_root": str(
            UPDATE_ROOT
        ),
    }
