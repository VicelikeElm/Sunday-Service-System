import shutil
from datetime import datetime
from pathlib import Path

BASE = Path(r"C:\Church\SermonAI")
LOWER_THIRDS = Path(
    r"C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds"
)

CONTROL_PANEL = LOWER_THIRDS / "control-panel.html"
SOURCE_JS = BASE / "sermon_plan_loader.js"
TARGET_JS = LOWER_THIRDS / "sermon_plan_loader.js"

BACKUP_DIR = BASE / "LowerThird_Backups"
MARKER = '<script src="sermon-plan-loader.js"></script>'


def main():
    if not CONTROL_PANEL.exists():
        raise SystemExit(
            f"Could not find {CONTROL_PANEL}"
        )

    if not SOURCE_JS.exists():
        raise SystemExit(
            f"Could not find {SOURCE_JS}"
        )

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    stamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    backup = (
        BACKUP_DIR
        /
        f"control-panel_{stamp}.html"
    )

    shutil.copy2(
        CONTROL_PANEL,
        backup
    )

    shutil.copy2(
        SOURCE_JS,
        TARGET_JS
    )

    html = CONTROL_PANEL.read_text(
        encoding="utf-8",
        errors="replace"
    )

    if MARKER not in html:
        lower = html.lower()
        body_pos = lower.rfind(
            "</body>"
        )

        if body_pos >= 0:
            html = (
                html[:body_pos]
                +
                "\n  "
                +
                MARKER
                +
                "\n"
                +
                html[body_pos:]
            )
        else:
            html += (
                "\n"
                +
                MARKER
                +
                "\n"
            )

        CONTROL_PANEL.write_text(
            html,
            encoding="utf-8"
        )

        print(
            "Installed Sermon AI lower-third loader."
        )
    else:
        print(
            "Sermon AI lower-third loader was already installed."
        )

    print()
    print("Backup:")
    print(backup)
    print()
    print("Loader:")
    print(TARGET_JS)
    print()
    print(
        "Restart OBS after this installer completes."
    )


if __name__ == "__main__":
    main()
