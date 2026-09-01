import datetime
import json
import os
import sys
from pathlib import Path

from sss_build_info import (
    APP_ID,
    APP_VERSION,
)


def _argument_value(
    name,
    default=""
):
    try:
        index = sys.argv.index(
            name
        )

        return sys.argv[
            index
            +
            1
        ]

    except Exception:
        return default


def _write_health_result(
    result
):
    target_text = _argument_value(
        "--update-health-check",
        ""
    )

    if not target_text:
        return

    target = Path(
        target_text
    )

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = target.with_suffix(
        target.suffix
        +
        ".tmp"
    )

    temp.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        +
        "\n",
        encoding="utf-8",
    )

    os.replace(
        temp,
        target,
    )


def run_safe_update_health_check():
    """
    Minimal wrapper around the FULL Sunday Mode import.

    Because this wrapper is the PyInstaller entry script, dependency/import
    failures inside sunday_mode can be caught here instead of becoming a
    blocking PyInstaller windowed-error dialog. That lets the external updater
    automatically roll back without waiting for a person to dismiss an error.
    """
    expected = _argument_value(
        "--expected-version",
        ""
    )

    result = {
        "ok": False,
        "version": APP_VERSION,
        "app_id": APP_ID,
        "timestamp": datetime.datetime.now().astimezone().isoformat(),
        "safe_startup_only": True,
        "detail": "",
    }

    try:
        if (
            expected
            and
            str(
                expected
            )
            !=
            str(
                APP_VERSION
            )
        ):
            raise RuntimeError(
                (
                    "Expected version "
                    +
                    str(
                        expected
                    )
                    +
                    " but this EXE reports "
                    +
                    str(
                        APP_VERSION
                    )
                    +
                    "."
                )
            )

        # Import the actual production Sunday Mode module and Settings/update
        # modules. No application objects are created and no live-service
        # actions are called.
        import sunday_mode
        import sss_settings
        import sss_updater_core

        _ = sunday_mode
        _ = sss_settings
        _ = sss_updater_core

        result[
            "ok"
        ] = True

        result[
            "detail"
        ] = (
            "Full Sunday Service System dependency/import health check passed."
        )

    except BaseException as exc:
        result[
            "detail"
        ] = (
            type(
                exc
            ).__name__
            +
            ": "
            +
            str(
                exc
            )
        )

    try:
        _write_health_result(
            result
        )
    except Exception:
        return 3

    return (
        0
        if result.get(
            "ok"
        )
        else
        2
    )


def main():
    if "--update-health-check" in sys.argv:
        raise SystemExit(
            run_safe_update_health_check()
        )

    import sunday_mode

    sunday_mode.main()


if __name__ == "__main__":
    main()
