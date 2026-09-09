import json
from pathlib import Path

PLAN = Path(r"C:\Church\SermonAI\sermon_plan.json")


def clean(value):
    if isinstance(value, str):
        return value.replace("*", "").strip()
    return value


def main():
    if not PLAN.exists():
        print("No sermon_plan.json found.")
        return

    data = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )

    data["title"] = clean(
        data.get(
            "title",
            ""
        )
    )

    data["scripture"] = clean(
        data.get(
            "scripture",
            ""
        )
    )

    data["preacher"] = clean(
        data.get(
            "preacher",
            ""
        )
    )

    data["points"] = [
        clean(point)
        for point in data.get(
            "points",
            []
        )
    ]

    temp = PLAN.with_suffix(
        ".json.tmp"
    )

    temp.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    temp.replace(
        PLAN
    )

    print("Cleaned sermon_plan.json:")
    print()
    print(f"Title: {data.get('title', '')}")
    print(f"Scripture: {data.get('scripture', '')}")
    print("Points:")

    for i, point in enumerate(
        data.get(
            "points",
            []
        ),
        start=1
    ):
        print(
            f"  {i}. {point}"
        )


if __name__ == "__main__":
    main()
