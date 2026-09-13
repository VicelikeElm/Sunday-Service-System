import re
import json
import time
import shutil
import tempfile
import logging
from pathlib import Path
from datetime import datetime

from ccl_chromium_reader import (
    ccl_chromium_localstorage
)

from sunday_common import (
    load_config,
    obs_connection,
    get_obs_status,
)

BASE = Path(
    r"C:\Church\SermonAI"
)

LOG_PATH = (
    BASE
    /
    "chapter_bridge.log"
)

STATUS_PATH = (
    BASE
    /
    "chapter_bridge_status.json"
)

PLAN_PATH = (
    BASE
    /
    "sermon_plan.json"
)

SCRIPTURE_PATTERN = re.compile(
    r"\b("
    r"(?:[1-3]\s*)?"
    r"(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|"
    r"Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|"
    r"Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|"
    r"Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|"
    r"Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|"
    r"Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|"
    r"Luke|John|Acts|Romans|Corinthians|Galatians|"
    r"Ephesians|Philippians|Colossians|Thessalonians|"
    r"Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|"
    r"Revelation)"
    r")\s+\d{1,3}"
    r"(?:\s*:\s*\d{1,3}"
    r"(?:\s*-\s*\d{1,3})?)?",
    flags=re.IGNORECASE,
)

GENERIC_NAMES = {
    "",
    "the baptist church of perry",
    "happy easter",
    "welcome",
    "preaching",
    "title",
}


logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)


def log(message):
    logging.info(
        message
    )


def write_status(
    state,
    last_chapter="",
    detail=""
):
    payload = {
        "state":
            state,
        "last_chapter":
            last_chapter,
        "detail":
            detail,
        "updated":
            datetime.now().isoformat(
                timespec="seconds"
            ),
    }

    try:
        STATUS_PATH.write_text(
            json.dumps(
                payload,
                indent=2
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def repair_text(value):
    if value is None:
        return ""

    if isinstance(
        value,
        bytes
    ):
        value = value.decode(
            "utf-8",
            errors="replace"
        )

    value = str(
        value
    )

    replacements = {
        "\x00": "",
        "ΓÇÖ": "’",
        "â€™": "’",
        "ΓÇô": "–",
        "â€“": "–",
        "ΓÇö": "—",
        "â€”": "—",
    }

    for bad, good in (
        replacements.items()
    ):
        value = value.replace(
            bad,
            good
        )

    return value.strip()


def norm(value):
    value = repair_text(
        value
    ).lower()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def scripture_key(value):
    match = (
        SCRIPTURE_PATTERN.search(
            repair_text(
                value
            )
        )
    )

    if not match:
        return ""

    return re.sub(
        r"\s+",
        "",
        match.group(0).lower()
    )


def storage_fingerprint(
    folder
):
    try:
        rows = []

        for path in folder.iterdir():
            if (
                path.is_file()
                and
                (
                    path.suffix.lower()
                    in {
                        ".log",
                        ".ldb"
                    }
                    or
                    path.name
                    in {
                        "CURRENT",
                        "MANIFEST-000001"
                    }
                    or
                    path.name.startswith(
                        "MANIFEST-"
                    )
                )
            ):
                st = path.stat()

                rows.append(
                    (
                        path.name,
                        st.st_mtime_ns,
                        st.st_size,
                    )
                )

        return tuple(
            sorted(
                rows
            )
        )

    except Exception:
        return ()


def read_lower_thirds(
    folder
):
    temp_root = Path(
        tempfile.mkdtemp(
            prefix=(
                "sermon_ai_chapter_"
            )
        )
    )

    copied = (
        temp_root
        /
        "leveldb"
    )

    try:
        shutil.copytree(
            folder,
            copied,
            dirs_exist_ok=True
        )

        latest = {}

        with (
            ccl_chromium_localstorage
            .LocalStoreDb(
                copied
            )
        ) as db:
            for storage_key in (
                db.iter_storage_keys()
            ):
                try:
                    records = (
                        db.iter_records_for_storage_key(
                            storage_key
                        )
                    )

                    for record in records:
                        key = repair_text(
                            record.script_key
                        )

                        if not re.fullmatch(
                            r"alt-[1-4]-(?:name|info)"
                            r"(?:-(?:[1-9]|10))?",
                            key
                        ):
                            continue

                        value = repair_text(
                            record.value
                        )

                        try:
                            seq = int(
                                getattr(
                                    record,
                                    "leveldb_seq_number",
                                    0
                                )
                                or
                                0
                            )
                        except Exception:
                            seq = 0

                        previous = (
                            latest.get(
                                key
                            )
                        )

                        if (
                            previous is None
                            or
                            seq
                            >=
                            previous[
                                "seq"
                            ]
                        ):
                            latest[
                                key
                            ] = {
                                "seq":
                                    seq,
                                "value":
                                    value,
                            }

                except Exception:
                    continue

        return latest

    finally:
        shutil.rmtree(
            temp_root,
            ignore_errors=True
        )


def current_active_rows(
    values
):
    rows = []

    for lt in range(
        1,
        5
    ):
        name_rec = values.get(
            f"alt-{lt}-name",
            {
                "value": "",
                "seq": 0,
            },
        )

        info_rec = values.get(
            f"alt-{lt}-info",
            {
                "value": "",
                "seq": 0,
            },
        )

        name = (
            name_rec[
                "value"
            ].strip()
        )

        info = (
            info_rec[
                "value"
            ].strip()
        )

        if not name and not info:
            continue

        rows.append({
            "lt":
                lt,
            "name":
                name,
            "info":
                info,
            "seq":
                max(
                    name_rec[
                        "seq"
                    ],
                    info_rec[
                        "seq"
                    ],
                ),
        })

    return rows


def choose_current_scripture(
    active_rows
):
    scripture_rows = []

    for row in active_rows:
        key = scripture_key(
            row[
                "name"
            ]
        )

        if not key:
            key = scripture_key(
                row[
                    "info"
                ]
            )

        if key:
            scripture_rows.append(
                (
                    row[
                        "seq"
                    ],
                    key,
                )
            )

    if not scripture_rows:
        return ""

    scripture_rows.sort(
        reverse=True
    )

    return scripture_rows[
        0
    ][1]


def load_official_plan():
    if not PLAN_PATH.exists():
        return None

    try:
        payload = json.loads(
            PLAN_PATH.read_text(
                encoding="utf-8"
            )
        )

        title = repair_text(
            payload.get(
                "title",
                ""
            )
        )

        scripture = repair_text(
            payload.get(
                "scripture",
                ""
            )
        )

        points = [
            repair_text(
                item
            )
            for item in payload.get(
                "points",
                []
            )
            if repair_text(
                item
            )
        ]

        if (
            title
            and
            scripture
            and
            points
        ):
            return {
                "title": title,
                "scripture": scripture,
                "points": points,
            }

    except Exception:
        return None

    return None


def build_candidate_names(
    values,
    active_rows
):
    official = load_official_plan()

    if official:
        return set(
            official[
                "points"
            ]
        )

    current_scripture = (
        choose_current_scripture(
            active_rows
        )
    )

    candidates = set()

    # Current active rows first.
    for row in active_rows:
        name = (
            row[
                "name"
            ].strip()
        )

        if (
            name
            and
            norm(
                name
            )
            not in
            GENERIC_NAMES
        ):
            row_scripture = (
                scripture_key(
                    row[
                        "name"
                    ]
                )
                or
                scripture_key(
                    row[
                        "info"
                    ]
                )
            )

            if (
                current_scripture
                and
                row_scripture
                ==
                current_scripture
            ):
                candidates.add(
                    name
                )

    # Memory slots associated with the same Scripture.
    if current_scripture:
        for lt in range(
            1,
            5
        ):
            for slot in range(
                1,
                11
            ):
                name = values.get(
                    (
                        f"alt-{lt}"
                        f"-name-{slot}"
                    ),
                    {
                        "value": ""
                    },
                )[
                    "value"
                ].strip()

                info = values.get(
                    (
                        f"alt-{lt}"
                        f"-info-{slot}"
                    ),
                    {
                        "value": ""
                    },
                )[
                    "value"
                ].strip()

                row_scripture = (
                    scripture_key(
                        name
                    )
                    or
                    scripture_key(
                        info
                    )
                )

                if (
                    name
                    and
                    row_scripture
                    ==
                    current_scripture
                    and
                    norm(
                        name
                    )
                    not in
                    GENERIC_NAMES
                ):
                    candidates.add(
                        name
                    )

    # Guest sermon fallback when no Scripture has been entered.
    if not candidates:
        for row in active_rows:
            name = (
                row[
                    "name"
                ].strip()
            )

            if (
                name
                and
                norm(
                    name
                )
                not in
                GENERIC_NAMES
            ):
                candidates.add(
                    name
                )

    return candidates


def create_chapter(
    client,
    name
):
    client.send(
        "CreateRecordChapter",
        {
            "chapterName":
                str(name)
        },
        raw=True,
    )


def connect_obs():
    try:
        return obs_connection(
            timeout=4
        )
    except Exception:
        return None


def main():
    config = load_config()

    folder = Path(
        config[
            "lower_thirds_leveldb"
        ]
    )

    poll_seconds = float(
        config.get(
            "chapter_bridge_poll_seconds",
            1.5
        )
    )

    duplicate_cooldown = float(
        config.get(
            "chapter_duplicate_cooldown_seconds",
            12
        )
    )

    auto_from_lower_thirds = bool(
        config.get(
            "chapter_bridge_auto_from_lower_thirds",
            True
        )
    )

    if not folder.exists():
        write_status(
            "ERROR",
            detail=(
                "Lower-third LevelDB "
                "folder not found."
            ),
        )

        log(
            "Lower-third LevelDB "
            "folder not found."
        )

        return 2

    log(
        "Chapter Bridge starting."
    )

    write_status(
        "STARTING"
    )

    client = None
    previous_active = {}
    previous_recording = False
    last_fingerprint = None
    last_chapter = ""
    last_chapter_time = 0.0
    cached_values = {}

    while True:
        try:
            if client is None:
                client = connect_obs()

            if client is None:
                write_status(
                    "WAITING_FOR_OBS",
                    last_chapter=(
                        last_chapter
                    ),
                )

                time.sleep(
                    3
                )

                continue

            try:
                obs_status = (
                    get_obs_status(
                        client
                    )
                )
            except Exception:
                client = None
                continue

            recording = bool(
                obs_status[
                    "recording"
                ]
            )

            # Automatic Start marker at the beginning
            # of every normal OBS recording.
            if (
                recording
                and
                not previous_recording
                and
                config.get(
                    "chapter_mark_start",
                    True
                )
            ):
                try:
                    time.sleep(
                        0.75
                    )

                    create_chapter(
                        client,
                        "Start"
                    )

                    last_chapter = (
                        "Start"
                    )

                    last_chapter_time = (
                        time.time()
                    )

                    log(
                        "Created chapter: Start"
                    )

                except Exception as exc:
                    log(
                        "Could not create Start "
                        f"chapter: {exc}"
                    )

            previous_recording = (
                recording
            )

            fingerprint = (
                storage_fingerprint(
                    folder
                )
            )

            if (
                fingerprint
                and
                fingerprint
                !=
                last_fingerprint
            ):
                try:
                    cached_values = (
                        read_lower_thirds(
                            folder
                        )
                    )

                    last_fingerprint = (
                        fingerprint
                    )

                except Exception as exc:
                    log(
                        "Lower-third read "
                        f"failed: {exc}"
                    )

            active_rows = (
                current_active_rows(
                    cached_values
                )
            )

            candidates = (
                build_candidate_names(
                    cached_values,
                    active_rows,
                )
            )

            now = time.time()

            current_map = {
                row[
                    "lt"
                ]:
                row[
                    "name"
                ]
                for row in active_rows
            }

            if (
                previous_active
                and
                auto_from_lower_thirds
            ):
                for lt, name in (
                    current_map.items()
                ):
                    old_name = (
                        previous_active.get(
                            lt,
                            ""
                        )
                    )

                    if (
                        name
                        and
                        name
                        !=
                        old_name
                        and
                        name
                        in
                        candidates
                        and
                        recording
                    ):
                        duplicate = (
                            name
                            ==
                            last_chapter
                            and
                            (
                                now
                                -
                                last_chapter_time
                            )
                            <
                            duplicate_cooldown
                        )

                        if duplicate:
                            continue

                        try:
                            create_chapter(
                                client,
                                name
                            )

                            last_chapter = (
                                name
                            )

                            last_chapter_time = (
                                now
                            )

                            log(
                                "Created chapter "
                                f"from LT{lt}: "
                                f"{name}"
                            )

                        except Exception as exc:
                            log(
                                "CreateRecordChapter "
                                f"failed: {exc}"
                            )

            previous_active = (
                current_map
            )

            write_status(
                (
                    "RECORDING"
                    if recording
                    else
                    "READY"
                ),
                last_chapter=(
                    last_chapter
                ),
                detail=(
                    (
                        f"{len(candidates)} current sermon "
                        "lower-third candidate(s)"
                    )
                    +
                    (
                        " | automatic LT chapter creation ON"
                        if auto_from_lower_thirds
                        else
                        " | SSS rotating chapter button owns markers"
                    )
                ),
            )

            time.sleep(
                poll_seconds
            )

        except KeyboardInterrupt:
            log(
                "Chapter Bridge stopped."
            )

            write_status(
                "STOPPED",
                last_chapter=(
                    last_chapter
                ),
            )

            return 0

        except Exception as exc:
            log(
                "Bridge loop error: "
                f"{exc}"
            )

            write_status(
                "ERROR",
                last_chapter=(
                    last_chapter
                ),
                detail=str(
                    exc
                ),
            )

            client = None

            time.sleep(
                3
            )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
