import sys
from pathlib import Path

# This file is a permanent, fixed-path entry point invoked directly by
# StreamDeck buttons (see StreamDeck_*.bat) - it stays at the project root
# forever so those buttons never need reconfiguring. Everything it depends
# on lives in core/, which is why it's added to sys.path explicitly rather
# than relying on the usual same-directory import resolution.
sys.path.insert(0, str(Path(__file__).resolve().parent / "core"))

from sunday_common import (
    obs_connection,
    get_obs_status,
)


def safe_client():
    try:
        return obs_connection()
    except Exception as exc:
        print(
            f"Could not connect to OBS: {exc}"
        )
        return None


def start_recording():
    client = safe_client()

    if client is None:
        return 2

    status = get_obs_status(
        client
    )

    if status["recording"]:
        print(
            "Recording is already running."
        )
        return 0

    client.start_record()

    print(
        "Recording start requested."
    )

    return 0


def stop_recording():
    client = safe_client()

    if client is None:
        return 2

    status = get_obs_status(
        client
    )

    if not status["recording"]:
        print(
            "Recording is already stopped."
        )
        return 0

    client.stop_record()

    print(
        "Recording stop requested."
    )

    return 0


def start_stream():
    client = safe_client()

    if client is None:
        return 2

    status = get_obs_status(
        client
    )

    if status["streaming"]:
        print(
            "Stream is already running."
        )
        return 0

    client.start_stream()

    print(
        "Stream start requested."
    )

    return 0


def stop_stream():
    client = safe_client()

    if client is None:
        return 2

    status = get_obs_status(
        client
    )

    if not status["streaming"]:
        print(
            "Stream is already stopped."
        )
        return 0

    client.stop_stream()

    print(
        "Stream stop requested."
    )

    return 0


def emergency_mute():
    from sunday_common import load_config

    config = load_config()
    client = safe_client()

    if client is None:
        return 2

    names = config.get(
        "emergency_mute_inputs",
        [
            "main",
            "room mics"
        ]
    )

    current = []

    for name in names:
        try:
            state = (
                client.get_input_mute(
                    name
                ).input_muted
            )

            current.append(
                bool(state)
            )
        except Exception:
            pass

    new_state = not (
        current
        and
        all(current)
    )

    for name in names:
        try:
            client.set_input_mute(
                name,
                new_state
            )
        except Exception as exc:
            print(
                f"Could not set mute for "
                f"{name}: {exc}"
            )

    print(
        "Emergency audio "
        +
        (
            "MUTED"
            if new_state
            else
            "UNMUTED"
        )
    )

    return 0


def chapter_now():
    client = safe_client()

    if client is None:
        return 2

    status = get_obs_status(
        client
    )

    if not status[
        "recording"
    ]:
        print(
            "Cannot add chapter: "
            "OBS is not recording."
        )
        return 3

    name = (
        "Manual Chapter"
    )

    if len(
        sys.argv
    ) >= 3:
        name = " ".join(
            sys.argv[
                2:
            ]
        ).strip()

    client.send(
        "CreateRecordChapter",
        {
            "chapterName":
                str(name)
        },
        raw=True,
    )

    print(
        f"Chapter created: {name}"
    )

    return 0


def main():
    if len(
        sys.argv
    ) < 2:
        print(
            "Usage: sunday_action.py "
            "record-start|record-stop|"
            "stream-start|stream-stop|"
            "mute|chapter [name]"
        )
        return 1

    action = (
        sys.argv[
            1
        ].lower()
    )

    if action == "record-start":
        return start_recording()

    if action == "record-stop":
        return stop_recording()

    if action == "stream-start":
        return start_stream()

    if action == "stream-stop":
        return stop_stream()

    if action == "mute":
        return emergency_mute()

    if action == "chapter":
        return chapter_now()

    print(
        f"Unknown action: {action}"
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
