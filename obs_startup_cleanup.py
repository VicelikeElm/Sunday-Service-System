import os
import time
import ctypes
import subprocess
from ctypes import wintypes
from pathlib import Path
from datetime import datetime

BASE = Path(r"C:\Church\SermonAI")
LOG_PATH = BASE / "obs_startup_cleanup.log"

TARGET_TITLES = {
    "plugin load error",
    "script log",
}

WATCH_SECONDS = 60
POLL_SECONDS = 0.35

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WM_CLOSE = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

EnumWindowsProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HWND,
    wintypes.LPARAM,
)

user32.EnumWindows.argtypes = [
    EnumWindowsProc,
    wintypes.LPARAM,
]
user32.EnumWindows.restype = wintypes.BOOL

user32.GetWindowTextLengthW.argtypes = [
    wintypes.HWND,
]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [
    wintypes.HWND,
    wintypes.LPWSTR,
    ctypes.c_int,
]
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

user32.IsWindowVisible.argtypes = [
    wintypes.HWND,
]
user32.IsWindowVisible.restype = wintypes.BOOL

user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostMessageW.restype = wintypes.BOOL

kernel32.OpenProcess.argtypes = [
    wintypes.DWORD,
    wintypes.BOOL,
    wintypes.DWORD,
]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [
    wintypes.HANDLE,
]
kernel32.CloseHandle.restype = wintypes.BOOL


def log(message):
    try:
        with LOG_PATH.open(
            "a",
            encoding="utf-8",
        ) as f:
            f.write(
                f"{datetime.now().isoformat(timespec='seconds')} | "
                f"{message}\n"
            )
    except Exception:
        pass


def process_image_name(pid):
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION,
        False,
        pid,
    )

    if not handle:
        return ""

    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(
            size.value
        )

        ok = kernel32.QueryFullProcessImageNameW(
            handle,
            0,
            buffer,
            ctypes.byref(size),
        )

        if not ok:
            return ""

        return buffer.value.lower()

    finally:
        kernel32.CloseHandle(
            handle
        )


def obs_is_running():
    try:
        cp = subprocess.run(
            [
                "tasklist",
                "/FI",
                "IMAGENAME eq obs64.exe",
            ],
            capture_output=True,
            text=True,
            timeout=4,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        return (
            "obs64.exe"
            in cp.stdout.lower()
        )

    except Exception:
        return False


def close_target_windows():
    closed = []

    @EnumWindowsProc
    def callback(hwnd, lparam):
        if not user32.IsWindowVisible(
            hwnd
        ):
            return True

        length = user32.GetWindowTextLengthW(
            hwnd
        )

        if length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(
            length + 1
        )

        user32.GetWindowTextW(
            hwnd,
            buffer,
            length + 1,
        )

        title = (
            buffer.value
            .strip()
        )

        if (
            title.lower()
            not in TARGET_TITLES
        ):
            return True

        pid = wintypes.DWORD()

        user32.GetWindowThreadProcessId(
            hwnd,
            ctypes.byref(
                pid
            ),
        )

        image = process_image_name(
            pid.value
        )

        # Only touch windows owned by OBS itself.
        if not image.endswith(
            r"\obs64.exe"
        ):
            return True

        if user32.PostMessageW(
            hwnd,
            WM_CLOSE,
            0,
            0,
        ):
            closed.append(
                title
            )

        return True

    user32.EnumWindows(
        callback,
        0,
    )

    return closed


def main():
    log(
        "OBS startup cleanup helper started."
    )

    deadline = (
        time.time()
        +
        WATCH_SECONDS
    )

    saw_obs = False

    while time.time() < deadline:
        if obs_is_running():
            saw_obs = True

            for title in (
                close_target_windows()
            ):
                log(
                    f"Closed OBS window: {title}"
                )

        elif saw_obs:
            # OBS was seen and then disappeared;
            # no reason to keep watching.
            break

        time.sleep(
            POLL_SECONDS
        )

    log(
        "OBS startup cleanup helper finished."
    )


if __name__ == "__main__":
    main()
