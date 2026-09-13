import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from sunday_common import (
    load_config,
    process_name_running,
)
from sermon_chapter_manager import (
    BASE,
    MAPPING_FILE,
    load_plan,
    build_sequence,
    clean,
)

STATUS_FILE = BASE / "chapter_hotkey_sync_status.json"
BACKUP_ROOT = BASE / "Chapter_Hotkey_Backups"


def read_json(path, default=None):
    if default is None:
        default = {}

    try:
        return json.loads(
            Path(path).read_text(
                encoding="utf-8-sig"
            )
        )
    except Exception:
        return default


def atomic_json(path, payload):
    path = Path(path)
    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    temp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    temp.replace(path)


def normalize(value):
    value = clean(
        value
    ).lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return " ".join(
        value.split()
    )


def scene_collection_folder():
    appdata = os.environ.get(
        "APPDATA",
        ""
    )

    if not appdata:
        raise RuntimeError(
            "APPDATA is not available."
        )

    return (
        Path(
            appdata
        )
        /
        "obs-studio"
        /
        "basic"
        /
        "scenes"
    )


def find_scene_collection(
    configured_name
):
    folder = scene_collection_folder()

    if not folder.exists():
        raise RuntimeError(
            f"OBS scene collection folder not found: {folder}"
        )

    target = normalize(
        configured_name
    )

    candidates = []

    for path in folder.glob(
        "*.json"
    ):
        data = read_json(
            path,
            None
        )

        if not isinstance(
            data,
            dict
        ):
            continue

        collection_name = clean(
            data.get(
                "name",
                ""
            )
        )

        score = 0

        if normalize(
            collection_name
        ) == target:
            score += 100

        if normalize(
            path.stem
        ) == target:
            score += 80

        if target and target in normalize(
            collection_name
        ):
            score += 40

        if "chapter_hotkeys" in data:
            score += 15

        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0

        candidates.append(
            (
                score,
                mtime,
                path,
                data,
            )
        )

    if not candidates:
        raise RuntimeError(
            "No OBS scene collection JSON files were found."
        )

    candidates.sort(
        key=lambda item: (
            item[
                0
            ],
            item[
                1
            ],
        ),
        reverse=True,
    )

    best = candidates[
        0
    ]

    if (
        target
        and
        best[
            0
        ]
        <
        40
    ):
        raise RuntimeError(
            (
                "Could not confidently locate the configured OBS "
                f"scene collection: {configured_name}"
            )
        )

    return (
        best[
            2
        ],
        best[
            3
        ],
    )


def semantic_role_match(
    role,
    name,
    current_point_names
):
    normalized = normalize(
        name
    )

    if not normalized:
        return False

    if role == "prayer":
        return (
            normalized
            in {
                "prayer",
                "opening prayer",
                "beginning prayer",
                "sermon prayer",
            }
            or
            normalized.startswith(
                "prayer "
            )
        )

    if role == "reference":
        if (
            normalized
            in {
                "reference",
                "scripture",
                "scripture reference",
                "sermon reference",
                "bible reference",
                "bible reading",
            }
        ):
            return True

        # Once SSS renames this hotkey to the actual passage, recognize
        # Scripture-looking names such as "Matthew 12:43-50" later too,
        # so the same hotkey ID / Stream Deck binding can be reused.
        return bool(
            re.search(
                r"\\b(?:[1-3]\\s*)?[a-z]+(?:\\s+[a-z]+)*\\s+\\d+\\s*:\\s*\\d+",
                normalized,
                flags=re.IGNORECASE,
            )
        )

    if role == "ending_prayer":
        return (
            normalized
            in {
                "ending prayer",
                "closing prayer",
                "final prayer",
                "sermon ending prayer",
            }
            or
            normalized.startswith(
                "ending prayer "
            )
        )

    if role == "benediction":
        return (
            "benediction"
            in
            normalized
        )

    match = re.fullmatch(
        r"(?:sermon )?point ?#? ?(\d+)",
        normalized,
    )

    if match:
        return (
            role
            ==
            f"point{int(match.group(1))}"
        )

    if role.startswith(
        "point"
    ):
        try:
            index = int(
                role[
                    5:
                ]
            )

            desired = normalize(
                current_point_names[
                    index
                    -
                    1
                ]
            )

            return (
                desired
                and
                normalized
                ==
                desired
            )

        except Exception:
            return False

    return False


def desired_managed_roles(
    plan,
    config
):
    sequence = build_sequence(
        plan,
        config,
    )

    return {
        item[
            "role"
        ]:
            item[
                "chapter_name"
            ]
        for item in sequence
    }


def choose_existing_id(
    role,
    chapter_hotkeys,
    used_ids,
    current_point_names
):
    # First choice: an exact semantic match. This covers Prayer,
    # Reference, Ending Prayer, Benediction, generic "Point N" labels, and a point that
    # already has this week's Gmail text.
    for hotkey_id, item in chapter_hotkeys.items():
        if hotkey_id in used_ids:
            continue

        name = clean(
            (
                item
                if isinstance(
                    item,
                    dict
                )
                else
                {}
            ).get(
                "name",
                ""
            )
        )

        if semantic_role_match(
            role,
            name,
            current_point_names,
        ):
            return hotkey_id

    # First-run bootstrap: the user's existing Point hotkeys may still
    # contain LAST Sunday's sermon wording. There is no textual way to
    # match that old wording to this week's Gmail points, so reuse the
    # remaining non-fixed chapter entries in their saved scene-collection
    # order. This preserves the existing keyboard/Stream Deck bindings.
    if role.startswith(
        "point"
    ):
        blocked_generic = {
            "",
            "start",
            "sermon",
            "intro",
            "introduction",
            "ending",
            "end",
        }

        for hotkey_id, item in chapter_hotkeys.items():
            if hotkey_id in used_ids:
                continue

            name = clean(
                (
                    item
                    if isinstance(
                        item,
                        dict
                    )
                    else
                    {}
                ).get(
                    "name",
                    ""
                )
            )

            normalized = normalize(
                name
            )

            if normalized in blocked_generic:
                continue

            # Do not steal one of the fixed service-section hotkeys.
            if any(
                semantic_role_match(
                    fixed_role,
                    name,
                    current_point_names,
                )
                for fixed_role in (
                    "prayer",
                    "reference",
                    "ending_prayer",
                    "benediction",
                )
            ):
                continue

            # Old "Unused Sermon Point N" slots are ideal reusable slots.
            # Old sermon-point wording is also accepted here by design.
            return hotkey_id

    return ""


def stable_id_for_role(
    role
):
    return (
        "chapter_hotkey_sss_"
        +
        role
    )


def sync(
    *,
    force=False,
    preview=False
):
    config = load_config()
    plan = load_plan()

    if not plan.get(
        "plan_id"
    ):
        raise RuntimeError(
            "sermon_plan.json has no plan_id."
        )

    configured_collection = clean(
        config.get(
            "scene_collection",
            "Church recording"
        )
    )

    path, data = find_scene_collection(
        configured_collection
    )

    obs_running = process_name_running(
        "obs64.exe"
    )

    if (
        obs_running
        and
        not force
    ):
        payload = {
            "state": "DEFERRED_OBS_RUNNING",
            "message": (
                "OBS is already running, so the scene-collection "
                "chapter-hotkey names were not edited live. "
                "SSS can still fire correct named chapters directly, "
                "but restart OBS before Sunday to load the new plugin labels."
            ),
            "scene_collection": str(
                path
            ),
            "plan_id": plan.get(
                "plan_id",
                ""
            ),
            "updated": datetime.now().isoformat(
                timespec="seconds"
            ),
        }

        atomic_json(
            STATUS_FILE,
            payload
        )

        return payload

    chapter_hotkeys = data.get(
        "chapter_hotkeys"
    )

    if not isinstance(
        chapter_hotkeys,
        dict
    ):
        chapter_hotkeys = {}

    mapping = read_json(
        MAPPING_FILE,
        {}
    )

    roles = mapping.get(
        "roles"
    )

    if not isinstance(
        roles,
        dict
    ):
        roles = {}

    desired = desired_managed_roles(
        plan,
        config,
    )

    current_point_names = plan.get(
        "points",
        []
    )

    used_ids = set()
    changes = []
    created = []

    # Preserve existing IDs and key bindings wherever possible.
    for role, desired_name in desired.items():
        hotkey_id = clean(
            roles.get(
                role,
                ""
            )
        )

        if (
            not hotkey_id
            or
            hotkey_id
            not in chapter_hotkeys
            or
            hotkey_id in used_ids
        ):
            hotkey_id = choose_existing_id(
                role,
                chapter_hotkeys,
                used_ids,
                current_point_names,
            )

        if not hotkey_id:
            hotkey_id = stable_id_for_role(
                role
            )

            suffix = 1
            base_id = hotkey_id

            while (
                hotkey_id
                in chapter_hotkeys
                and
                hotkey_id
                in used_ids
            ):
                suffix += 1
                hotkey_id = (
                    f"{base_id}_{suffix}"
                )

            if hotkey_id not in chapter_hotkeys:
                chapter_hotkeys[
                    hotkey_id
                ] = {
                    "name": desired_name,
                    "bindings": [],
                }

                created.append(
                    role
                )

        item = chapter_hotkeys.get(
            hotkey_id
        )

        if not isinstance(
            item,
            dict
        ):
            item = {
                "name": "",
                "bindings": [],
            }

            chapter_hotkeys[
                hotkey_id
            ] = item

        old_name = clean(
            item.get(
                "name",
                ""
            )
        )

        if old_name != desired_name:
            item[
                "name"
            ] = desired_name

            changes.append(
                {
                    "role": role,
                    "hotkey_id": hotkey_id,
                    "old_name": old_name,
                    "new_name": desired_name,
                }
            )

        if not isinstance(
            item.get(
                "bindings"
            ),
            list,
        ):
            item[
                "bindings"
            ] = []

        roles[
            role
        ] = hotkey_id

        used_ids.add(
            hotkey_id
        )

    # Keep extra point slots and their bindings so a future sermon with
    # more points can reuse the same Stream Deck/keyboard mapping.
    for index in range(
        1,
        11
    ):
        role = f"point{index}"

        if role in desired:
            continue

        hotkey_id = clean(
            roles.get(
                role,
                ""
            )
        )

        if (
            hotkey_id
            and
            hotkey_id
            in chapter_hotkeys
        ):
            item = chapter_hotkeys[
                hotkey_id
            ]

            if isinstance(
                item,
                dict
            ):
                inactive_name = (
                    f"Unused Sermon Point {index}"
                )

                if clean(
                    item.get(
                        "name",
                        ""
                    )
                ) != inactive_name:
                    item[
                        "name"
                    ] = inactive_name

                    changes.append(
                        {
                            "role": role,
                            "hotkey_id": hotkey_id,
                            "old_name": "",
                            "new_name": inactive_name,
                        }
                    )

    data[
        "chapter_hotkeys"
    ] = chapter_hotkeys

    mapping_payload = {
        "scene_collection": configured_collection,
        "scene_collection_file": str(
            path
        ),
        "plan_id": plan.get(
            "plan_id",
            ""
        ),
        "service_date": plan.get(
            "service_date",
            ""
        ),
        "roles": roles,
        "updated": datetime.now().isoformat(
            timespec="seconds"
        ),
    }

    if preview:
        return {
            "state": "PREVIEW",
            "scene_collection": str(
                path
            ),
            "desired": desired,
            "roles": roles,
            "changes": changes,
            "created": created,
        }

    BACKUP_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    stamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    backup_path = (
        BACKUP_ROOT
        /
        (
            stamp
            +
            "_"
            +
            path.name
        )
    )

    shutil.copy2(
        path,
        backup_path,
    )

    temp = path.with_suffix(
        ".json.sss.tmp"
    )

    temp.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    temp.replace(
        path
    )

    atomic_json(
        MAPPING_FILE,
        mapping_payload
    )

    payload = {
        "state": "SYNCED",
        "message": (
            f"Synced {len(desired)} sermon chapter hotkey(s) "
            f"for {plan.get('service_date', '')}. "
            f"Preserved existing bindings where found."
        ),
        "scene_collection": str(
            path
        ),
        "backup": str(
            backup_path
        ),
        "plan_id": plan.get(
            "plan_id",
            ""
        ),
        "service_date": plan.get(
            "service_date",
            ""
        ),
        "desired": desired,
        "roles": roles,
        "changes": changes,
        "created": created,
        "updated": datetime.now().isoformat(
            timespec="seconds"
        ),
    }

    atomic_json(
        STATUS_FILE,
        payload
    )

    return payload


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--preview",
        action="store_true"
    )

    parser.add_argument(
        "--force",
        action="store_true"
    )

    args = parser.parse_args()

    try:
        result = sync(
            force=args.force,
            preview=args.preview,
        )

        print()
        print(
            "SERMON CHAPTER HOTKEY SYNC"
        )
        print(
            "=" * 72
        )
        print(
            result.get(
                "state",
                ""
            )
        )
        print(
            result.get(
                "message",
                ""
            )
        )

        desired = result.get(
            "desired",
            {}
        )

        if desired:
            print()

            for role, name in desired.items():
                print(
                    f"{role:12} -> {name}"
                )

        print()

        return (
            0
            if result.get(
                "state"
            )
            in {
                "SYNCED",
                "PREVIEW",
                "DEFERRED_OBS_RUNNING",
            }
            else
            1
        )

    except Exception as exc:
        payload = {
            "state": "ERROR",
            "message": str(
                exc
            ),
            "updated": datetime.now().isoformat(
                timespec="seconds"
            ),
        }

        atomic_json(
            STATUS_FILE,
            payload
        )

        print(
            f"Chapter hotkey sync failed: {exc}"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
