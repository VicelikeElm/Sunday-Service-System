import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from sss_signing import (
    load_signing_config,
    sign_authenticode_file,
    validate_signing_config,
    write_release_trust_file,
)


SOURCE_ROOT = Path(
    __file__
).resolve().parent.parent

DIST_ROOT = SOURCE_ROOT / "dist"
BUILD_ROOT = SOURCE_ROOT / "build"
PAYLOAD_ROOT = SOURCE_ROOT / "installer-payload"
RUNTIME_PAYLOAD = PAYLOAD_ROOT / "RuntimeSupport"

VERSION = "3.1.2"

SIGNING_CONFIG = None
SIGNING_STATUS = None

SAFE_RUNTIME_SUPPORT_FILES = (
    "core/audio_sanity_monitor.py",
    "core/chapter_bridge.py",
    "core/gmail_sermon_importer.py",
    "core/obs_startup_cleanup.py",
    "core/operational_cleanup.py",
    "core/planning_update_sermon.py",
    "core/post_service_supervisor.py",
    "ptz_camera_control.py",
    "core/sss_test_mode.py",
    "sunday_action.py",
    "core/sync_named_chapter_hotkeys.py",
    "core/sync_sermon_plan_to_lower_thirds.py",
    "core/weekly_snapshot.py",
    "core/youtube_studio_upload_worker.py",
    "tools/Open-YouTube-Studio-Normal-Login.bat",
)

OPTIONAL_RUNTIME_ASSETS = (
    "church_shortcut_icon.ico",
)

CRITICAL_RUNTIME_MODULES = (
    "obsws_python",
)


def _prepare_signed_release():
    global SIGNING_CONFIG
    global SIGNING_STATUS

    print()
    print("=" * 72)
    print("SSS SIGNED RELEASE PREFLIGHT")
    print("=" * 72)

    SIGNING_CONFIG = load_signing_config(
        required=True
    )

    SIGNING_STATUS = validate_signing_config(
        SIGNING_CONFIG
    )

    timestamp = str(
        SIGNING_CONFIG.get(
            "timestamp_url",
            ""
        )
        or
        ""
    ).strip()

    if not timestamp:
        raise RuntimeError(
            (
                "Signed release builds require timestamp_url in "
                "sss_signing_config.json. SSS requires RFC 3161 timestamping "
                "for Authenticode release signatures."
            )
        )

    trust_file = write_release_trust_file(
        SIGNING_CONFIG,
        destination=(
            SOURCE_ROOT
            /
            "core"
            /
            "sss_release_trust.py"
        ),
    )

    print(
        "[READY] Code signing certificate:",
        SIGNING_STATUS[
            "code_signing"
        ][
            "subject"
        ],
    )

    print(
        "[READY] Certificate thumbprint:",
        SIGNING_STATUS[
            "code_signing"
        ][
            "thumbprint"
        ],
    )

    print(
        "[READY] SignTool:",
        SIGNING_STATUS[
            "signtool"
        ],
    )

    print(
        "[READY] RFC3161 timestamp:",
        timestamp,
    )

    print(
        "[READY] Trusted update signer pins written:",
        trust_file,
    )


def _sign_release_binary(
    path,
    label
):
    if SIGNING_CONFIG is None:
        raise RuntimeError(
            "Release signing configuration was not prepared."
        )

    print()
    print(
        "Signing",
        label,
        "..."
    )

    result = sign_authenticode_file(
        path,
        SIGNING_CONFIG,
    )

    print(
        "[READY]",
        label,
        "Authenticode signer:",
        result.get(
            "thumbprint",
            ""
        ),
    )

    return result


def _check_runtime_environment():
    print()
    print("Build Python:")
    print(" ", sys.executable)

    print()
    print("Checking critical SSS runtime modules in the build Python...")

    missing = []

    for module_name in CRITICAL_RUNTIME_MODULES:
        spec = importlib.util.find_spec(
            module_name
        )

        if spec is None:
            missing.append(
                module_name
            )
            print(
                " [FIX]",
                module_name,
                "NOT FOUND",
            )
        else:
            print(
                " [READY]",
                module_name,
                "->",
                getattr(
                    spec,
                    "origin",
                    None,
                )
                or
                "package",
            )

    if missing:
        raise RuntimeError(
            (
                "The EXE build Python cannot see required SSS runtime "
                "module(s): "
                +
                ", ".join(
                    missing
                )
                +
                ". Run Build-SSS-Windows-Installer.bat v3.1.2 so the build "
                "uses C:\\Church\\SermonAI\\venv\\Scripts\\python.exe."
            )
        )


FORBIDDEN_PAYLOAD_NAMES = (
    ".env",
    "gmail_token",
    "credential",
    "credentials",
    "oauth",
    "password",
    "secret",
    "token.json",
    "sermon_plan.json",
    "sunday_config.json",
    "ptz_camera_config.json",
)


def _forbidden(path):
    name = Path(
        path
    ).name.lower()

    return any(
        part in name
        for part in FORBIDDEN_PAYLOAD_NAMES
    )


def _run(command):
    print()
    print(
        ">",
        " ".join(
            str(
                part
            )
            for part in command
        ),
    )

    subprocess.check_call(
        command,
        cwd=SOURCE_ROOT,
    )


def _running_packaged_sss_processes():
    """
    Return packaged SSS processes whose executable path is inside this project's
    dist folder. This does NOT look for or touch OBS, python.exe, or pythonw.exe.
    """
    if os.name != "nt":
        return []

    escaped_dist = str(
        DIST_ROOT.resolve()
    ).replace(
        "'",
        "''"
    )

    ps = (
        "$root='"
        +
        escaped_dist
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

        import json

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

        return payload

    except Exception:
        return []


def _remove_tree_with_retry(
    path,
    *,
    attempts=4
):
    path = Path(
        path
    )

    if not path.exists():
        return

    last_error = None

    for attempt in range(
        1,
        attempts
        +
        1
    ):
        try:
            shutil.rmtree(
                path
            )

            return

        except PermissionError as exc:
            last_error = exc

            running = _running_packaged_sss_processes()

            if running:
                details = []

                for item in running:
                    details.append(
                        (
                            str(
                                item.get(
                                    "Name",
                                    "process"
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
                            +
                            "\n    "
                            +
                            str(
                                item.get(
                                    "ExecutablePath",
                                    ""
                                )
                            )
                        )
                    )

                raise RuntimeError(
                    (
                        "The previous packaged SSS EXE is still running and is "
                        "locking the old dist folder.\n\n"
                        +
                        "\n".join(
                            details
                        )
                        +
                        "\n\nClose that EXE/error window first, or run "
                        "Close-Old-SSS-Build-EXEs.bat, then rebuild.\n"
                        "OBS is not involved and will not be stopped."
                    )
                ) from exc

            if attempt < attempts:
                time.sleep(
                    1.0
                )
                continue

        except OSError as exc:
            last_error = exc

            if attempt < attempts:
                time.sleep(
                    1.0
                )
                continue

    raise RuntimeError(
        (
            "Could not remove old build output:\n"
            +
            str(
                path
            )
            +
            "\n\nWindows is still locking one or more files.\n"
            "Close any old SundayServiceSystem.exe / "
            "SundayServiceSystemSettings.exe windows, then run the build again.\n\n"
            "Original error: "
            +
            str(
                last_error
            )
        )
    )


def _clean_build_outputs():
    running = _running_packaged_sss_processes()

    if running:
        details = []

        for item in running:
            details.append(
                (
                    str(
                        item.get(
                            "Name",
                            "process"
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
                    ")\n    "
                    +
                    str(
                        item.get(
                            "ExecutablePath",
                            ""
                        )
                    )
                )
            )

        raise RuntimeError(
            (
                "A previous packaged SSS build is still running:\n\n"
                +
                "\n".join(
                    details
                )
                +
                "\n\nClose it before rebuilding, or run "
                "Close-Old-SSS-Build-EXEs.bat.\n"
                "This build check does not stop OBS or any Python production process."
            )
        )

    for path in (
        DIST_ROOT,
        BUILD_ROOT,
        PAYLOAD_ROOT,
    ):
        _remove_tree_with_retry(
            path
        )

    DIST_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    RUNTIME_PAYLOAD.mkdir(
        parents=True,
        exist_ok=True,
    )


def _stage_safe_runtime_support():
    copied = []

    for name in SAFE_RUNTIME_SUPPORT_FILES:
        source = (
            SOURCE_ROOT
            /
            name
        )

        if not source.exists():
            continue

        if _forbidden(
            source
        ):
            raise RuntimeError(
                (
                    "Refusing to stage forbidden runtime file: "
                    +
                    source.name
                )
            )

        destination = (
            RUNTIME_PAYLOAD
            /
            source.name
        )

        shutil.copy2(
            source,
            destination,
        )

        copied.append(
            source.name
        )

    for name in OPTIONAL_RUNTIME_ASSETS:
        source = (
            SOURCE_ROOT
            /
            name
        )

        if not source.exists():
            continue

        if _forbidden(
            source
        ):
            raise RuntimeError(
                (
                    "Refusing to stage forbidden asset: "
                    +
                    source.name
                )
            )

        shutil.copy2(
            source,
            RUNTIME_PAYLOAD
            /
            source.name,
        )

        copied.append(
            source.name
        )

    print()
    print(
        "Staged",
        len(
            copied
        ),
        "safe compatibility runtime file(s).",
    )

    if copied:
        for name in copied:
            print(
                " -",
                name,
            )


def _pyinstaller_base(
    *,
    manifest_name="sss_app.manifest"
):
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--noupx",
        "--distpath",
        str(
            DIST_ROOT
        ),
        "--workpath",
        str(
            BUILD_ROOT
        ),
        "--specpath",
        str(
            BUILD_ROOT
        ),
        "--manifest",
        str(
            SOURCE_ROOT
            /
            manifest_name
        ),
        "--hidden-import",
        "obsws_python",
        "--collect-submodules",
        "obsws_python",
    ]

    # sv_ttk ships its .tcl theme scripts and sprite sheets as package data,
    # not Python modules - PyInstaller's import analysis can't see them, so
    # they must be collected explicitly or the packaged EXE falls back to
    # the plain (pre-theme) look with no error. Optional at packaging time,
    # same reasoning as the MIDI packages below.
    if importlib.util.find_spec(
        "sv_ttk"
    ) is not None:
        command.extend(
            [
                "--collect-data",
                "sv_ttk",
            ]
        )

    # MIDI packages are optional at packaging time. If the production SSS
    # environment actually has them, include them explicitly. If it does not,
    # do not ask PyInstaller for nonexistent hidden imports (which only creates
    # alarming-but-nonfatal ERROR lines).
    if importlib.util.find_spec(
        "mido"
    ) is not None:
        command.extend(
            [
                "--collect-submodules",
                "mido",
            ]
        )

        if importlib.util.find_spec(
            "mido.backends.rtmidi"
        ) is not None:
            command.extend(
                [
                    "--hidden-import",
                    "mido.backends.rtmidi",
                ]
            )

    if importlib.util.find_spec(
        "rtmidi"
    ) is not None:
        command.extend(
            [
                "--hidden-import",
                "rtmidi",
            ]
        )

    icon = (
        SOURCE_ROOT
        /
        "church_shortcut_icon.ico"
    )

    if icon.exists():
        command.extend(
            [
                "--icon",
                str(
                    icon
                ),
            ]
        )

    return command


def _build_main():
    command = _pyinstaller_base()

    command.extend(
        [
            "--name",
            "SundayServiceSystem",
            "--version-file",
            str(
                SOURCE_ROOT
                /
                "sss_version_info.txt"
            ),
            str(
                SOURCE_ROOT
                /
                "core"
                /
                "sss_main_entry.py"
            ),
        ]
    )

    _run(
        command
    )

    _sign_release_binary(
        DIST_ROOT
        /
        "SundayServiceSystem"
        /
        "SundayServiceSystem.exe",
        "SundayServiceSystem.exe",
    )


def _build_settings():
    command = _pyinstaller_base()

    command.extend(
        [
            "--name",
            "SundayServiceSystemSettings",
            "--version-file",
            str(
                SOURCE_ROOT
                /
                "sss_settings_version_info.txt"
            ),
            str(
                SOURCE_ROOT
                /
                "core"
                /
                "sss_settings.py"
            ),
        ]
    )

    _run(
        command
    )

    _sign_release_binary(
        DIST_ROOT
        /
        "SundayServiceSystemSettings"
        /
        "SundayServiceSystemSettings.exe",
        "SundayServiceSystemSettings.exe",
    )


def _build_updater():
    command = _pyinstaller_base(
        manifest_name="sss_updater.manifest"
    )

    command.extend(
        [
            "--name",
            "SundayServiceSystemUpdater",
            "--version-file",
            str(
                SOURCE_ROOT
                /
                "sss_updater_version_info.txt"
            ),
            str(
                SOURCE_ROOT
                /
                "core"
                /
                "sss_updater.py"
            ),
        ]
    )

    _run(
        command
    )

    _sign_release_binary(
        DIST_ROOT
        /
        "SundayServiceSystemUpdater"
        /
        "SundayServiceSystemUpdater.exe",
        "SundayServiceSystemUpdater.exe",
    )


def _build_update_package():
    _run(
        [
            sys.executable,
            str(
                SOURCE_ROOT
                /
                "core"
                /
                "build_sss_update_package.py"
            ),
        ]
    )


def _verify_outputs():
    required = (
        DIST_ROOT
        /
        "SundayServiceSystem"
        /
        "SundayServiceSystem.exe",
        DIST_ROOT
        /
        "SundayServiceSystemSettings"
        /
        "SundayServiceSystemSettings.exe",
        DIST_ROOT
        /
        "SundayServiceSystemUpdater"
        /
        "SundayServiceSystemUpdater.exe",
    )

    missing = [
        str(
            path
        )
        for path in required
        if not path.exists()
    ]

    if missing:
        raise RuntimeError(
            (
                "PyInstaller completed but expected EXE(s) are missing:\n"
                +
                "\n".join(
                    missing
                )
            )
        )

    print()
    print(
        "EXE build verified:"
    )

    for path in required:
        print(
            " -",
            path,
        )


def _find_inno_compiler():
    candidates = [
        Path(
            os.environ.get(
                "ProgramFiles(x86)",
                r"C:\Program Files (x86)"
            )
        )
        /
        "Inno Setup 6"
        /
        "ISCC.exe",

        Path(
            os.environ.get(
                "ProgramFiles",
                r"C:\Program Files"
            )
        )
        /
        "Inno Setup 6"
        /
        "ISCC.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def _build_installer_if_available():
    compiler = _find_inno_compiler()

    if compiler is None:
        print()
        print(
            "Inno Setup 6 was not found."
        )
        print(
            "The three EXEs and local update package were built successfully."
        )
        print(
            "Install Inno Setup 6, then run Build-SSS-Installer-Only.bat."
        )
        return False

    _run(
        [
            str(
                compiler
            ),
            str(
                SOURCE_ROOT
                /
                "installer"
                /
                "SundayServiceSystem.iss"
            ),
        ]
    )

    installer = (
        SOURCE_ROOT
        /
        "installer-output"
        /
        (
            "SundayServiceSystem-Setup-v"
            +
            VERSION
            +
            ".exe"
        )
    )

    if not installer.exists():
        raise RuntimeError(
            (
                "Inno Setup completed but the expected installer is missing:\n"
                +
                str(
                    installer
                )
            )
        )

    _sign_release_binary(
        installer,
        "SundayServiceSystem installer",
    )

    return True


def main():
    if os.name != "nt":
        raise SystemExit(
            (
                "The SSS Windows EXE/installer build must run on Windows. "
                "Copy this patch to the church PC and run "
                "Build-SSS-Windows-Installer.bat there."
            )
        )

    _prepare_signed_release()
    _check_runtime_environment()
    _clean_build_outputs()
    _stage_safe_runtime_support()
    _build_main()
    _build_settings()
    _build_updater()
    _verify_outputs()
    _build_update_package()

    installer_built = _build_installer_if_available()

    print()
    print(
        "="
        *
        72
    )
    print(
        "SSS SIGNED WINDOWS RELEASE COMPLETE"
    )
    print(
        "="
        *
        72
    )
    print(
        "Version:",
        VERSION,
    )
    print(
        "Main EXE:",
        DIST_ROOT
        /
        "SundayServiceSystem"
        /
        "SundayServiceSystem.exe",
    )
    print(
        "Settings EXE:",
        DIST_ROOT
        /
        "SundayServiceSystemSettings"
        /
        "SundayServiceSystemSettings.exe",
    )
    print(
        "Updater EXE:",
        DIST_ROOT
        /
        "SundayServiceSystemUpdater"
        /
        "SundayServiceSystemUpdater.exe",
    )
    print(
        "Local update package:",
        SOURCE_ROOT
        /
        "update-output"
        /
        (
            "SundayServiceSystem-Update-v"
            +
            VERSION
            +
            ".sssupdate"
        ),
    )

    if installer_built:
        print(
            "Installer output:",
            SOURCE_ROOT
            /
            "installer-output"
        )

    print()
    print(
        "No profile, .env, OAuth token, password, sermon_plan.json, "
        "sunday_config.json, or ptz_camera_config.json was staged into the "
        "installer payload."
    )


if __name__ == "__main__":
    main()
