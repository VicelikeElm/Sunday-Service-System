import shutil
import time
from pathlib import Path

from sunday_common import load_config
from sss_reliability import (
    BASE,
    STATE_DIR,
    is_frozen,
    purge_old_log_folders,
)

SAFE_TEMP_NAMES = {
    "__pycache__",
}


def main():
    if is_frozen():
        print(
            "Sunday Freeze is active. "
            "Operational cleanup was skipped."
        )
        return 2

    config = load_config()

    retention_days = int(
        config.get(
            "log_retention_days",
            90
        )
    )

    purge_old_log_folders(
        retention_days
    )

    # Deliberately conservative: only local cache/temp files.
    for child in BASE.iterdir():
        if (
            child.is_dir()
            and
            child.name
            in
            SAFE_TEMP_NAMES
        ):
            try:
                shutil.rmtree(
                    child
                )
            except Exception:
                pass

        elif (
            child.is_file()
            and
            child.suffix.lower()
            in
            {
                ".tmp",
                ".temp",
            }
        ):
            try:
                child.unlink()
            except Exception:
                pass

    # Clear stale temporary state files only.
    cutoff = time.time() - (
        30
        *
        24
        *
        60
        *
        60
    )

    if STATE_DIR.exists():
        for child in STATE_DIR.iterdir():
            if not child.is_file():
                continue

            if child.name in {
                "post_service_status.json",
                "audio_sanity_status.json",
                "Sunday_Freeze.json",
            }:
                continue

            try:
                if child.stat().st_mtime < cutoff:
                    child.unlink()
            except Exception:
                pass

    print(
        "Operational cleanup complete. "
        "Recordings, SRTs, shorts, sermon data, and upload history "
        "were not touched."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
