import json
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE = Path(r"C:\Church\SermonAI")

PLAN = BASE / "sermon_plan.json"

LOWER_THIRDS = Path(
    r"C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds"
)

CONTROL_PANEL = LOWER_THIRDS / "control-panel.html"
TEMPLATE = BASE / "control-panel-v15-template.html"
BACKUP_DIR = BASE / "LowerThird_Backups"

START_MARKER = "// SERMON_AI_PLAN_START"
END_MARKER = "// SERMON_AI_PLAN_END"


def clean(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("*", "")
        .strip()
    )


def load_plan():
    if not PLAN.exists():
        raise FileNotFoundError(
            f"Sermon plan not found: {PLAN}"
        )

    data = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    result = {
        "plan_id": clean(
            data.get(
                "plan_id",
                ""
            )
        ),
        "updated": clean(
            data.get(
                "updated",
                ""
            )
        ),
        "source": clean(
            data.get(
                "source",
                ""
            )
        ),
        "title": clean(
            data.get(
                "title",
                ""
            )
        ),
        "scripture": clean(
            data.get(
                "scripture",
                ""
            )
        ),
        "preacher": clean(
            data.get(
                "preacher",
                ""
            )
        ),
        "points": [
            clean(point)
            for point in data.get(
                "points",
                []
            )
            if clean(point)
        ],
    }

    if (
        not result["title"]
        or
        not result["scripture"]
        or
        not result["points"]
    ):
        raise ValueError(
            "sermon_plan.json is incomplete."
        )

    return result


def ensure_template_installed():
    if not TEMPLATE.exists():
        raise FileNotFoundError(
            f"Missing v15 template: {TEMPLATE}"
        )

    if not CONTROL_PANEL.exists():
        raise FileNotFoundError(
            f"Lower-third control panel not found: {CONTROL_PANEL}"
        )

    current = CONTROL_PANEL.read_text(
        encoding="utf-8",
        errors="replace"
    )

    # If the current panel is not v12 yet, install the template.
    if (
        START_MARKER not in current
        or
        END_MARKER not in current
    ):
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
            f"control-panel_before_v15_sync_{stamp}.html"
        )

        shutil.copy2(
            CONTROL_PANEL,
            backup
        )

        shutil.copy2(
            TEMPLATE,
            CONTROL_PANEL
        )


def embed_plan(plan):
    ensure_template_installed()

    panel = CONTROL_PANEL.read_text(
        encoding="utf-8",
        errors="replace"
    )

    assignment = (
        START_MARKER
        +
        "\n"
        +
        "			window.SERMON_AI_PLAN_EMBEDDED = "
        +
        json.dumps(
            plan,
            ensure_ascii=False,
            separators=(
                ",",
                ":"
            )
        )
        +
        ";\n"
        +
        "			"
        +
        END_MARKER
    )

    pattern = re.compile(
        re.escape(
            START_MARKER
        )
        +
        r".*?"
        +
        re.escape(
            END_MARKER
        ),
        re.DOTALL
    )

    updated, count = pattern.subn(
        assignment,
        panel,
        count=1
    )

    if count != 1:
        raise RuntimeError(
            "Could not locate the v12 sermon-plan markers."
        )

    temp = CONTROL_PANEL.with_suffix(
        ".html.tmp"
    )

    temp.write_text(
        updated,
        encoding="utf-8"
    )

    temp.replace(
        CONTROL_PANEL
    )


def sync_plan():
    plan = load_plan()
    embed_plan(
        plan
    )
    return plan


def main():
    plan = sync_plan()

    print(
        "Lower-third sermon plan embedded."
    )

    print()

    print(
        f"Title: {plan['title']}"
    )

    print(
        f"Scripture: {plan['scripture']}"
    )

    print(
        f"Points: {len(plan['points'])}"
    )

    print()

    print(
        "Written directly into:"
    )

    print(
        CONTROL_PANEL
    )

    print()

    print(
        "The next OBS lower-thirds page load will use this sermon."
    )


if __name__ == "__main__":
    main()
