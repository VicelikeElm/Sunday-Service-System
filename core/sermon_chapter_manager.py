import argparse
import ctypes
import hashlib
import json
import sys
import time
from pathlib import Path

from sunday_common import (
    load_config,
    obs_connection,
    get_obs_status,
)

BASE = Path(r"C:\Church\SermonAI")
PLAN_FILE = BASE / "sermon_plan.json"
MAPPING_FILE = BASE / "chapter_hotkey_mapping.json"
ROTATION_FILE = BASE / "chapter_rotation_state.json"
ACTION_FILE = BASE / "chapter_action_state.json"


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


def clean(value):
    return " ".join(
        str(
            value
            or
            ""
        ).split()
    ).strip()


def load_plan():
    plan = read_json(
        PLAN_FILE,
        {}
    )

    points = [
        clean(
            item
        )
        for item in plan.get(
            "points",
            []
        )
        if clean(
            item
        )
    ]

    return {
        "plan_id": clean(
            plan.get(
                "plan_id",
                ""
            )
        ),
        "service_date": clean(
            plan.get(
                "service_date",
                ""
            )
        ),
        "title": clean(
            plan.get(
                "title",
                ""
            )
        ),
        "scripture": clean(
            plan.get(
                "scripture",
                ""
            )
        ),
        "points": points[
            :10
        ],
    }


def build_sequence(
    plan=None,
    config=None
):
    if plan is None:
        plan = load_plan()

    if config is None:
        config = load_config()

    sequence = []

    if config.get(
        "chapter_include_prayer",
        True
    ):
        prayer_name = clean(
            config.get(
                "chapter_prayer_name",
                "Prayer"
            )
        ) or "Prayer"

        sequence.append(
            {
                "role": "prayer",
                "display": prayer_name,
                "chapter_name": prayer_name,
                "lt_hotkey": "",
            }
        )

    if config.get(
        "chapter_include_reference",
        True
    ):
        scripture = clean(
            plan.get(
                "scripture",
                ""
            )
        )

        reference_fallback = clean(
            config.get(
                "chapter_reference_name",
                "Reference"
            )
        ) or "Reference"

        # Use the actual weekly Scripture passage as the chapter name.
        # Example: "Matthew 12:43-50" instead of the generic "Reference".
        # Fall back to "Reference" only if the sermon plan has no Scripture.
        chapter_name = (
            scripture
            or
            reference_fallback
        )

        display = chapter_name

        sequence.append(
            {
                "role": "reference",
                "display": display,
                "chapter_name": chapter_name,
                # LT2 slot 1 is the weekly sermon title + Scripture.
                "lt_hotkey": "LT2_SLT01",
            }
        )

    for index, point in enumerate(
        plan.get(
            "points",
            []
        ),
        start=1,
    ):
        point = clean(
            point
        )

        if not point:
            continue

        sequence.append(
            {
                "role": f"point{index}",
                "display": (
                    f"Point {index} — {point}"
                ),
                # The actual OBS chapter is the pastor's official point,
                # not a generic "Point 1" label.
                "chapter_name": point,
                "lt_hotkey": (
                    f"LT1_SLT{index:02d}"
                ),
            }
        )

    if config.get(
        "chapter_include_ending_prayer",
        True
    ):
        ending_prayer_name = clean(
            config.get(
                "chapter_ending_prayer_name",
                "Ending Prayer"
            )
        ) or "Ending Prayer"

        sequence.append(
            {
                "role": "ending_prayer",
                "display": ending_prayer_name,
                "chapter_name": ending_prayer_name,
                "lt_hotkey": "",
            }
        )

    if config.get(
        "chapter_include_benediction",
        True
    ):
        benediction_name = clean(
            config.get(
                "chapter_benediction_name",
                "Benediction"
            )
        ) or "Benediction"

        sequence.append(
            {
                "role": "benediction",
                "display": benediction_name,
                "chapter_name": benediction_name,
                "lt_hotkey": "",
            }
        )

    return sequence


def sequence_hash(
    plan,
    sequence
):
    payload = {
        "plan_id": plan.get(
            "plan_id",
            ""
        ),
        "sequence": [
            (
                item[
                    "role"
                ],
                item[
                    "chapter_name"
                ],
                item[
                    "lt_hotkey"
                ],
            )
            for item in sequence
        ],
    }

    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def load_rotation():
    plan = load_plan()
    config = load_config()
    sequence = build_sequence(
        plan,
        config,
    )

    fingerprint = sequence_hash(
        plan,
        sequence,
    )

    state = read_json(
        ROTATION_FILE,
        {}
    )

    if (
        state.get(
            "plan_id"
        )
        !=
        plan.get(
            "plan_id"
        )
        or
        state.get(
            "sequence_hash"
        )
        !=
        fingerprint
    ):
        state = {
            "plan_id": plan.get(
                "plan_id",
                ""
            ),
            "service_date": plan.get(
                "service_date",
                ""
            ),
            "sequence_hash": fingerprint,
            "next_index": 0,
            "last_chapter": "",
            "updated": time.time(),
        }

        atomic_json(
            ROTATION_FILE,
            state
        )

    return (
        plan,
        sequence,
        state,
    )


def reset_rotation():
    plan = load_plan()
    config = load_config()
    sequence = build_sequence(
        plan,
        config,
    )

    state = {
        "plan_id": plan.get(
            "plan_id",
            ""
        ),
        "service_date": plan.get(
            "service_date",
            ""
        ),
        "sequence_hash": sequence_hash(
            plan,
            sequence,
        ),
        "next_index": 0,
        "last_chapter": "",
        "updated": time.time(),
    }

    atomic_json(
        ROTATION_FILE,
        state
    )

    return (
        plan,
        sequence,
        state,
    )


def next_button_text(
    max_length=54
):
    plan, sequence, state = load_rotation()

    index = int(
        state.get(
            "next_index",
            0
        )
    )

    if not sequence:
        return "NO SERMON CHAPTERS"

    if index >= len(
        sequence
    ):
        return "CHAPTERS COMPLETE"

    item = sequence[
        index
    ]

    # Keep the SSS control compact: show only the information the
    # operator actually needs at this moment. For sermon points this is
    # the exact official Gmail point text.
    text = clean(
        item.get(
            "chapter_name",
            ""
        )
        or
        item.get(
            "display",
            ""
        )
    )

    if len(
        text
    ) > max_length:
        text = (
            text[
                :max_length
                -
                1
            ].rstrip()
            +
            "…"
        )

    return text

def trigger_hotkey(
    client,
    hotkey_name
):
    client.send(
        "TriggerHotkeyByName",
        {
            "hotkeyName":
                str(
                    hotkey_name
                )
        },
        raw=True,
    )


def send_windows_alt_shift_f16():
    """
    Fallback for the church-PC LT1 toggle binding.

    The Animated Lower Thirds LT1 switch is bound in OBS to:
        Alt + Shift + F16

    Normally SSS triggers the plugin's OBS hotkey name A_SWITCH_1
    directly. This Windows key injection is only a fallback.
    """
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32

    VK_MENU = 0x12
    VK_SHIFT = 0x10
    VK_F16 = 0x7F
    KEYEVENTF_KEYUP = 0x0002

    try:
        user32.keybd_event(
            VK_MENU,
            0,
            0,
            0
        )
        user32.keybd_event(
            VK_SHIFT,
            0,
            0,
            0
        )
        user32.keybd_event(
            VK_F16,
            0,
            0,
            0
        )

        time.sleep(
            0.05
        )

        user32.keybd_event(
            VK_F16,
            0,
            KEYEVENTF_KEYUP,
            0
        )
        user32.keybd_event(
            VK_SHIFT,
            0,
            KEYEVENTF_KEYUP,
            0
        )
        user32.keybd_event(
            VK_MENU,
            0,
            KEYEVENTF_KEYUP,
            0
        )

        return True

    except Exception:
        return False


def trigger_lt1_switch(
    client,
    config
):
    """
    Toggle Lower Third 1.

    A_SWITCH_1 is the Animated Lower Thirds OBS hotkey corresponding
    to the church Stream Deck's Alt+Shift+F16 LT1-launch action.
    """
    hotkey_name = clean(
        config.get(
            "lt1_switch_hotkey_name",
            "A_SWITCH_1"
        )
    ) or "A_SWITCH_1"

    try:
        trigger_hotkey(
            client,
            hotkey_name,
        )

        return (
            True,
            f"OBS:{hotkey_name}",
        )

    except Exception:
        if send_windows_alt_shift_f16():
            return (
                True,
                "Windows:Alt+Shift+F16",
            )

    return (
        False,
        "",
    )


def create_direct_chapter(
    client,
    chapter_name
):
    client.send(
        "CreateRecordChapter",
        {
            "chapterName":
                str(
                    chapter_name
                )
        },
        raw=True,
    )


def fire_item(
    item,
    *,
    client=None,
    test_mode=False
):
    if client is None:
        client = obs_connection(
            timeout=5
        )

    status = get_obs_status(
        client
    )

    if (
        not test_mode
        and
        not status[
            "recording"
        ]
    ):
        raise RuntimeError(
            "OBS is not recording. "
            "The chapter sequence was not advanced."
        )

    # Admin Chapter/LT Test Mode deliberately does NOT create a real
    # recording chapter marker. It exercises the same sequence and
    # lower-third actions without touching the real sermon position or
    # requiring a recording.
    chapter_method = (
        "test-simulated"
        if test_mode
        else
        "direct"
    )

    if not test_mode:
        mapping = read_json(
            MAPPING_FILE,
            {}
        )

        current_plan = load_plan()

        mapping_is_current = (
            bool(
                current_plan.get(
                    "plan_id"
                )
            )
            and
            mapping.get(
                "plan_id"
            )
            ==
            current_plan.get(
                "plan_id"
            )
        )

        hotkey_id = ""

        if mapping_is_current:
            hotkey_id = clean(
                mapping.get(
                    "roles",
                    {}
                ).get(
                    item[
                        "role"
                    ],
                    ""
                )
            )

        # Never fire an old Sunday's mapped plugin hotkey. If the current
        # Gmail plan could not be synced into the scene collection because
        # OBS was already open, create the CORRECT chapter directly instead.
        # Prefer the Additional Chapter Hotkeys plugin only when the mapping
        # explicitly belongs to this sermon plan. If the scene collection
        # has not reloaded yet, fall back to OBS's native
        # CreateRecordChapter so the correct chapter is never lost.
        if hotkey_id:
            try:
                trigger_hotkey(
                    client,
                    hotkey_id,
                )

                chapter_method = (
                    "named-hotkey-plugin"
                )

            except Exception:
                create_direct_chapter(
                    client,
                    item[
                        "chapter_name"
                    ],
                )

        else:
            create_direct_chapter(
                client,
                item[
                    "chapter_name"
                ],
            )

    lt_hotkey = clean(
        item.get(
            "lt_hotkey",
            ""
        )
    )

    lt_triggered = False
    lt_switch_triggered = False
    lt_switch_method = ""
    lt_display_seconds = 0.0

    if lt_hotkey:
        try:
            # First load the correct memory slot.
            trigger_hotkey(
                client,
                lt_hotkey,
            )

            lt_triggered = True

        except Exception:
            # The chapter marker must still be preserved even if the
            # lower-third slot hotkey is unavailable.
            lt_triggered = False

        # Sermon POINTS use LT1. Loading LT1_SLT01/02/etc only changes
        # the stored text; it does not turn the LT1 switch on. Recreate
        # the Stream Deck macro here:
        #
        #   LT1 slot N
        #   short load delay
        #   LT1 ON   (A_SWITCH_1 / Alt+Shift+F16)
        #   11 seconds
        #   LT1 OFF  (same toggle)
        #
        # Keep this synchronous so the SSS chapter button stays disabled
        # for the entire display window and cannot be double-clicked.
        if (
            lt_triggered
            and
            lt_hotkey.upper().startswith(
                "LT1_SLT"
            )
        ):
            config = load_config()

            slot_delay = float(
                config.get(
                    "lt1_slot_load_delay_seconds",
                    0.35
                )
            )

            lt_display_seconds = float(
                config.get(
                    "lt1_chapter_display_seconds",
                    11
                )
            )

            time.sleep(
                max(
                    0.0,
                    slot_delay
                )
            )

            (
                lt_switch_triggered,
                lt_switch_method,
            ) = trigger_lt1_switch(
                client,
                config,
            )

            if lt_switch_triggered:
                time.sleep(
                    max(
                        0.0,
                        lt_display_seconds
                    )
                )

                # Toggle the same LT1 switch back OFF.
                off_ok, off_method = (
                    trigger_lt1_switch(
                        client,
                        config,
                    )
                )

                if not off_ok:
                    lt_switch_triggered = False

                elif not lt_switch_method:
                    lt_switch_method = off_method

    atomic_json(
        ACTION_FILE,
        {
            "time": time.time(),
            "role": item[
                "role"
            ],
            "chapter_name": item[
                "chapter_name"
            ],
            "chapter_method": chapter_method,
            "lt_hotkey": lt_hotkey,
            "lt_triggered": lt_triggered,
            "lt_switch_triggered": lt_switch_triggered,
            "lt_switch_method": lt_switch_method,
            "lt_display_seconds": lt_display_seconds,
            "test_mode": bool(
                test_mode
            ),
        }
    )

    return {
        "chapter_method": chapter_method,
        "lt_triggered": lt_triggered,
        "lt_switch_triggered": lt_switch_triggered,
        "lt_switch_method": lt_switch_method,
        "lt_display_seconds": lt_display_seconds,
        "test_mode": bool(
            test_mode
        ),
    }


def fire_next():
    plan, sequence, state = load_rotation()

    index = int(
        state.get(
            "next_index",
            0
        )
    )

    if index >= len(
        sequence
    ):
        raise RuntimeError(
            "All sermon chapters have already been fired."
        )

    item = sequence[
        index
    ]

    result = fire_item(
        item
    )

    state[
        "next_index"
    ] = (
        index
        +
        1
    )

    state[
        "last_chapter"
    ] = item[
        "chapter_name"
    ]

    state[
        "updated"
    ] = time.time()

    atomic_json(
        ROTATION_FILE,
        state
    )

    return {
        "item": item,
        "result": result,
        "next_button_text":
            next_button_text(),
    }


def print_sequence():
    plan, sequence, state = load_rotation()

    print()
    print(
        "SERMON CHAPTER ROTATION"
    )
    print(
        "=" * 72
    )
    print(
        f"Title: {plan.get('title', '')}"
    )
    print(
        f"Scripture: {plan.get('scripture', '')}"
    )
    print()

    for index, item in enumerate(
        sequence,
        start=1,
    ):
        print(
            f"{index}. "
            f"{item['display']}"
            +
            (
                f" | LT hotkey {item['lt_hotkey']}"
                if item[
                    "lt_hotkey"
                ]
                else
                ""
            )
        )

    print()
    print(
        next_button_text()
    )
    print()


def main():
    parser = argparse.ArgumentParser()

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "show"
    )

    sub.add_parser(
        "reset"
    )

    sub.add_parser(
        "next"
    )

    args = parser.parse_args()

    if args.command == "show":
        print_sequence()
        return 0

    if args.command == "reset":
        reset_rotation()
        print(
            next_button_text()
        )
        return 0

    if args.command == "next":
        try:
            result = fire_next()

            item = result[
                "item"
            ]

            print(
                (
                    "Chapter fired: "
                    f"{item['chapter_name']}"
                )
            )

            if item.get(
                "lt_hotkey"
            ):
                print(
                    (
                        "Lower third: "
                        +
                        (
                            "triggered"
                            if result[
                                "result"
                            ][
                                "lt_triggered"
                            ]
                            else
                            "NOT triggered"
                        )
                    )
                )

            print(
                result[
                    "next_button_text"
                ]
            )

            return 0

        except Exception as exc:
            print(
                f"Chapter not fired: {exc}"
            )
            return 2

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
