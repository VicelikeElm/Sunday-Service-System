import re
from pathlib import Path

from sunday_common import load_config
from sss_reliability import (
    read_json,
    find_service_srt,
)

BASE = Path(r"C:\Church\SermonAI")
PLAN_FILE = BASE / "sermon_plan.json"


def transcript_excerpt(
    path,
    max_chars=4000
):
    if path is None:
        return ""

    try:
        raw = path.read_text(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        return ""

    lines = []

    for line in raw.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.isdigit():
            continue

        if "-->" in line:
            continue

        lines.append(
            line
        )

    text = " ".join(
        lines
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text[
        :max_chars
    ]


def main():
    config = load_config()
    plan = read_json(
        PLAN_FILE,
        {}
    )

    service_date = str(
        plan.get(
            "service_date",
            ""
        )
    ).strip()

    if not service_date:
        print(
            "No sermon service_date."
        )
        return 1

    root = Path(
        config.get(
            "sermon_data_folder",
            r"D:\2026\shorts\ai shorts\Sermon Data"
        )
    )

    root.mkdir(
        parents=True,
        exist_ok=True
    )

    destination = (
        root
        /
        (
            service_date
            +
            "_Thumbnail_Handoff"
        )
    )

    destination.mkdir(
        parents=True,
        exist_ok=True
    )

    title = str(
        plan.get(
            "title",
            ""
        )
    ).strip()

    scripture = str(
        plan.get(
            "scripture",
            ""
        )
    ).strip()

    points = plan.get(
        "points",
        []
    )

    preacher = str(
        plan.get(
            "preacher",
            ""
        )
    ).strip()

    srt = find_service_srt(
        plan
    )

    excerpt = transcript_excerpt(
        srt
    )

    (
        destination
        /
        "sermon_title.txt"
    ).write_text(
        title
        +
        "\n",
        encoding="utf-8"
    )

    (
        destination
        /
        "scripture.txt"
    ).write_text(
        scripture
        +
        "\n",
        encoding="utf-8"
    )

    (
        destination
        /
        "outline.txt"
    ).write_text(
        "\n".join(
            f"{index}. {point}"
            for index, point in enumerate(
                points,
                start=1
            )
        )
        +
        "\n",
        encoding="utf-8"
    )

    (
        destination
        /
        "transcript_excerpt.txt"
    ).write_text(
        excerpt
        +
        "\n",
        encoding="utf-8"
    )

    prompt = (
        "YouTube sermon thumbnail handoff\n\n"
        f"Title: {title}\n"
        f"Scripture: {scripture}\n"
        f"Preacher: {preacher}\n\n"
        "Outline:\n"
        +
        "\n".join(
            f"- {point}"
            for point in points
        )
        +
        "\n\n"
        "Design direction: create a strong 16:9 YouTube sermon thumbnail "
        "based on the sermon theme. Keep text minimal and highly readable. "
        "Do not depict Jesus or God directly. Use the sermon title and "
        "Scripture as the primary reference.\n"
    )

    (
        destination
        /
        "thumbnail_prompt.txt"
    ).write_text(
        prompt,
        encoding="utf-8"
    )

    print(
        destination
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
