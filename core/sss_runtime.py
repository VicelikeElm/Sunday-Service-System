import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path

from sss_build_info import (
    APP_NAME,
    APP_VERSION,
)


LEGACY_RUNTIME_ROOT = Path(
    r"C:\Church\SermonAI"
)

MAIN_EXE_NAME = "SundayServiceSystem.exe"
SETTINGS_EXE_NAME = "SundayServiceSystemSettings.exe"
UPDATER_EXE_NAME = "SundayServiceSystemUpdater.exe"

PROGRAM_DATA = Path(
    os.environ.get(
        "PROGRAMDATA",
        r"C:\ProgramData"
    )
)

UPDATER_RUNTIME_ROOT = (
    PROGRAM_DATA
    /
    "Sunday Service System"
    /
    "Updates"
    /
    "UpdaterRuntime"
)


def is_frozen():
    return bool(
        getattr(
            sys,
            "frozen",
            False
        )
    )


def executable_path():
    return Path(
        sys.executable
    ).resolve()


def executable_dir():
    return executable_path().parent


def application_install_root():
    """
    For PyInstaller onedir builds, the main and Settings executables live
    in separate sibling application folders under the same install root.

    Return <install> when that layout is detected; otherwise the executable dir.
    """
    current = executable_dir()

    if current.name in {
        "SundayServiceSystem",
        "SundayServiceSystemSettings",
        "SundayServiceSystemUpdater",
    }:
        return current.parent

    return current


def settings_executable_candidates():
    current = executable_dir()
    install_root = application_install_root()

    return [
        current
        /
        SETTINGS_EXE_NAME,

        install_root
        /
        "SundayServiceSystemSettings"
        /
        SETTINGS_EXE_NAME,

        install_root
        /
        SETTINGS_EXE_NAME,
    ]


def updater_executable_candidates():
    current = executable_dir()
    install_root = application_install_root()

    return [
        current
        /
        UPDATER_EXE_NAME,

        install_root
        /
        "SundayServiceSystemUpdater"
        /
        UPDATER_EXE_NAME,

        install_root
        /
        UPDATER_EXE_NAME,
    ]


def _prune_old_updater_runtime_copies():
    try:
        UPDATER_RUNTIME_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        cutoff = (
            datetime.datetime.now().timestamp()
            -
            (
                7
                *
                24
                *
                60
                *
                60
            )
        )

        for path in UPDATER_RUNTIME_ROOT.glob(
            "launch_*"
        ):
            try:
                if (
                    path.is_dir()
                    and
                    path.stat().st_mtime
                    <
                    cutoff
                ):
                    shutil.rmtree(
                        path
                    )
            except Exception:
                pass

    except Exception:
        pass


def _stage_external_updater_runtime(
    updater_exe
):
    """
    Copy the entire PyInstaller onedir Updater beside ProgramData, then launch
    that copy. This lets the updater replace its own installed Program Files
    folder safely because the running process is no longer inside that folder.
    """
    updater_exe = Path(
        updater_exe
    ).resolve()

    source_dir = updater_exe.parent

    _prune_old_updater_runtime_copies()

    UPDATER_RUNTIME_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = datetime.datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    destination = (
        UPDATER_RUNTIME_ROOT
        /
        (
            "launch_"
            +
            stamp
            +
            "_"
            +
            str(
                os.getpid()
            )
        )
    )

    shutil.copytree(
        source_dir,
        destination,
    )

    staged_exe = (
        destination
        /
        UPDATER_EXE_NAME
    )

    if not staged_exe.exists():
        raise RuntimeError(
            (
                "External updater staging failed; copied updater EXE is missing:\\n"
                +
                str(
                    staged_exe
                )
            )
        )

    return staged_exe


def launch_updater(
    *args
):
    arguments = [
        str(
            arg
        )
        for arg in args
        if str(
            arg
        )
    ]

    if not is_frozen():
        updater_script = (
            LEGACY_RUNTIME_ROOT
            /
            "core"
            /
            "sss_updater.py"
        )

        if not updater_script.exists():
            raise FileNotFoundError(
                str(
                    updater_script
                )
            )

        return subprocess.Popen(
            [
                str(
                    _pythonw()
                ),
                str(
                    updater_script
                ),
                *arguments,
            ],
            cwd=str(
                LEGACY_RUNTIME_ROOT
            ),
            creationflags=_creationflags(),
        )

    for candidate in updater_executable_candidates():
        if candidate.exists():
            staged_exe = _stage_external_updater_runtime(
                candidate
            )

            return subprocess.Popen(
                [
                    str(
                        staged_exe
                    ),
                    *arguments,
                ],
                cwd=str(
                    LEGACY_RUNTIME_ROOT
                ),
                creationflags=_creationflags(),
            )

    raise FileNotFoundError(
        (
            "SundayServiceSystemUpdater.exe was not found beside the "
            "installed Sunday Service System."
        )
    )


def _creationflags():
    if os.name != "nt":
        return 0

    return getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0
    )


def _pythonw():
    executable = executable_path()

    pythonw = (
        executable.parent
        /
        "pythonw.exe"
    )

    if pythonw.exists():
        return pythonw

    return executable


def launch_settings(
    *args
):
    """
    Launch Settings correctly in both development/Python mode and installed EXE
    mode.

    This avoids trying to execute "sss_settings.py" through a frozen EXE.
    """
    arguments = [
        str(
            arg
        )
        for arg in args
        if str(
            arg
        )
    ]

    if is_frozen():
        for candidate in settings_executable_candidates():
            if candidate.exists():
                return subprocess.Popen(
                    [
                        str(
                            candidate
                        ),
                        *arguments,
                    ],
                    cwd=str(
                        LEGACY_RUNTIME_ROOT
                    ),
                    creationflags=_creationflags(),
                )

        raise FileNotFoundError(
            (
                "SundayServiceSystemSettings.exe was not found beside the "
                "installed Sunday Service System."
            )
        )

    settings_script = (
        LEGACY_RUNTIME_ROOT
        /
        "core"
        /
        "sss_settings.py"
    )

    manager_script = (
        LEGACY_RUNTIME_ROOT
        /
        "core"
        /
        "sss_profile_manager.py"
    )

    launch_script = (
        settings_script
        if settings_script.exists()
        else
        manager_script
    )

    if not launch_script.exists():
        raise FileNotFoundError(
            (
                "SSS Settings / Profile Manager script was not found: "
                +
                str(
                    launch_script
                )
            )
        )

    return subprocess.Popen(
        [
            str(
                _pythonw()
            ),
            str(
                launch_script
            ),
            *arguments,
        ],
        cwd=str(
            LEGACY_RUNTIME_ROOT
        ),
        creationflags=_creationflags(),
    )


def runtime_info():
    install_root = application_install_root()

    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "frozen": is_frozen(),
        "mode": (
            "Installed Windows EXE"
            if is_frozen()
            else
            "Python compatibility mode"
        ),
        "executable": str(
            executable_path()
        ),
        "install_root": str(
            install_root
        ),
        "legacy_runtime_root": str(
            LEGACY_RUNTIME_ROOT
        ),
    }


def open_install_folder():
    folder = application_install_root()

    if os.name == "nt":
        os.startfile(
            str(
                folder
            )
        )

        return

    subprocess.Popen(
        [
            "xdg-open",
            str(
                folder
            ),
        ]
    )
