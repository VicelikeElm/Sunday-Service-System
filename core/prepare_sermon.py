import re
import json
import shutil
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path

from rapidfuzz import fuzz
from ccl_chromium_reader import ccl_chromium_localstorage

from sunday_common import load_config

_config = load_config()

# =========================================================
# SETTINGS
# =========================================================

SERMON_FOLDER = Path(_config.get("recording_folder", r"D:\2026"))
SRT_FOLDER = SERMON_FOLDER / "SRT files"

SHORTS_ROOT = SERMON_FOLDER / "shorts" / "ai shorts"
SERMON_DATA_FOLDER = Path(
    _config.get("sermon_data_folder", str(SHORTS_ROOT / "Sermon Data"))
)

LOWER_THIRDS_LEVELDB = Path(
    _config.get(
        "lower_thirds_leveldb",
        r"C:\Users\Vicel\AppData\Roaming\obs-studio"
        r"\plugin_config\obs-browser\Local Storage\leveldb",
    )
)

LOWER_THIRD_MATCH_THRESHOLD = 62
MAX_LOWER_THIRD_CANDIDATES = 12


# =========================================================
# GENERIC CHAPTERS / LOWER THIRD CONTENT
# =========================================================

GENERIC_CHAPTER_NAMES = [
    "start",
    "beginning prayer",
    "opening prayer",
    "prayer",
    "ending prayer",
    "closing prayer",
    "benediction",
    "announcements",
    "announcement",
    "offering",
    "scripture reading",
    "worship",
    "music",
]

GENERIC_LOWER_THIRD_TEXT = [
    "the baptist church of perry",
    "preaching",
    "pastor",
    "elder",
    "guest",
    "guest speaker",
    "welcome",
    "happy easter",
]


# =========================================================
# FILE HELPERS
# =========================================================

def ensure_folder():
    SERMON_DATA_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )


def repair_text(text):
    if not text:
        return ""

    replacements = {
        "ΓÇÖ": "’",
        "ΓÇ£": "“",
        "ΓÇ¥": "”",
        "ΓÇô": "–",
        "ΓÇö": "—",
        "ΓÇª": "…",
        "â€™": "’",
        "â€œ": "“",
        "â€\x9d": "”",
        "â€“": "–",
        "â€”": "—",
        "\x00": "",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return text.strip()


def clean_sermon_title(filename):
    title = Path(filename).stem
    title = title.rstrip(". ")
    title = title.replace("_", " ")
    return repair_text(title).strip()


def parse_filename_datetime(path):
    name = Path(path).name

    match = re.search(
        r"(\d{4}-\d{2}-\d{2})[ _]"
        r"(\d{2})-(\d{2})-(\d{2})",
        name
    )

    if not match:
        return None

    try:
        return datetime.strptime(
            (
                f"{match.group(1)} "
                f"{match.group(2)}:"
                f"{match.group(3)}:"
                f"{match.group(4)}"
            ),
            "%Y-%m-%d %H:%M:%S"
        )
    except ValueError:
        return None


def normalize_text(text):
    text = repair_text(text or "").lower()

    text = re.sub(
        r"[^a-z0-9'\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# FIND NEWEST MAIN RECORDING
# =========================================================

def find_newest_sermon_recording():
    extensions = {
        ".mp4",
        ".mkv",
        ".mov",
        ".m4v",
    }

    candidates = []

    for path in SERMON_FOLDER.iterdir():
        if not path.is_file():
            continue

        if path.suffix.lower() not in extensions:
            continue

        if "ai_clip" in path.name.lower():
            continue

        candidates.append(path)

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda p: p.stat().st_mtime
    )


# =========================================================
# FFPROBE
# =========================================================

def run_ffprobe(video_path):
    command = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_chapters",
        "-show_format",
        str(video_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(
            "FFprobe failed:\n"
            + result.stderr
        )

    return json.loads(
        result.stdout
    )


# =========================================================
# CHAPTER EXTRACTION
# =========================================================

def extract_chapters(ffprobe_data):
    chapters = []

    for chapter in ffprobe_data.get(
        "chapters",
        []
    ):
        title = repair_text(
            chapter
            .get("tags", {})
            .get("title", "")
        )

        try:
            start = float(
                chapter.get(
                    "start_time",
                    0
                )
            )
        except (ValueError, TypeError):
            start = 0.0

        try:
            end = float(
                chapter.get(
                    "end_time",
                    start
                )
            )
        except (ValueError, TypeError):
            end = start

        chapters.append({
            "title": title,
            "start": start,
            "end": end,
        })

    return chapters


def is_generic_chapter(title):
    normalized = (
        title
        .lower()
        .strip()
        .rstrip("!?.:")
    )

    return any(
        normalized == generic
        for generic in GENERIC_CHAPTER_NAMES
    )


def useful_chapters(chapters):
    return [
        chapter
        for chapter in chapters
        if (
            chapter["title"]
            and
            not is_generic_chapter(
                chapter["title"]
            )
        )
    ]


# =========================================================
# SRT PARSING
# =========================================================

def srt_time_to_seconds(value):
    """
    Accept common SRT time formats such as:
      00:01:02,345
      00:01:02.345
      0:01:02,345
      00:01:02
      00:01:02,345000
    """
    value = (value or "").strip()

    match = re.search(
        r"(\d{1,3}):(\d{1,2}):(\d{1,2})"
        r"(?:[,.](\d{1,6}))?",
        value,
    )

    if not match:
        return None

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = int(match.group(3))

    fraction = match.group(4) or ""

    if fraction:
        fraction_seconds = int(fraction) / (10 ** len(fraction))
    else:
        fraction_seconds = 0.0

    return (
        hours * 3600
        + minutes * 60
        + seconds
        + fraction_seconds
    )


def read_text_file_robust(path):
    data = Path(path).read_bytes()

    encodings = []

    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        encodings.extend([
            "utf-16",
            "utf-16-le",
            "utf-16-be",
        ])
    elif data.startswith(b"\xef\xbb\xbf"):
        encodings.append(
            "utf-8-sig"
        )

    encodings.extend([
        "utf-8-sig",
        "utf-8",
        "utf-16",
        "cp1252",
    ])

    tried = set()

    for encoding in encodings:
        if encoding in tried:
            continue

        tried.add(encoding)

        try:
            return data.decode(
                encoding
            )
        except UnicodeDecodeError:
            continue

    return data.decode(
        "utf-8",
        errors="replace"
    )


def parse_srt(path):
    """
    Parse ordinary SRT plus several slightly non-standard timestamp
    variants. If blank-line block parsing finds nothing, perform a
    second line-by-line pass so unusual SRT formatting still works.
    """
    content = read_text_file_robust(
        path
    )

    content = (
        content
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\ufeff", "")
    )

    entries = []

    def add_entry(
        timing_line,
        text_lines
    ):
        if "-->" not in timing_line:
            return

        timing = timing_line.split(
            "-->",
            1
        )

        if len(timing) != 2:
            return

        start = srt_time_to_seconds(
            timing[0]
        )

        end = srt_time_to_seconds(
            timing[1]
        )

        if start is None or end is None:
            return

        caption_text = " ".join(
            line.strip()
            for line in text_lines
            if line.strip()
        )

        caption_text = re.sub(
            r"<[^>]+>",
            "",
            caption_text,
        )

        caption_text = repair_text(
            caption_text
        )

        if not caption_text:
            return

        entries.append({
            "start": start,
            "end": end,
            "text": caption_text,
        })

    blocks = re.split(
        r"\n\s*\n",
        content.strip()
    )

    for block in blocks:
        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ]

        if not lines:
            continue

        time_index = None

        for index, line in enumerate(
            lines
        ):
            if "-->" in line:
                time_index = index
                break

        if time_index is None:
            continue

        add_entry(
            lines[time_index],
            lines[
                time_index + 1:
            ],
        )

    if entries:
        return entries

    lines = content.splitlines()
    index = 0

    while index < len(lines):
        line = lines[
            index
        ].strip()

        if "-->" not in line:
            index += 1
            continue

        timing_line = line
        index += 1
        text_lines = []

        while index < len(lines):
            current = lines[
                index
            ].strip()

            if "-->" in current:
                break

            if not current:
                index += 1
                break

            if (
                current.isdigit()
                and
                text_lines
            ):
                index += 1
                break

            text_lines.append(
                current
            )
            index += 1

        add_entry(
            timing_line,
            text_lines,
        )

    return entries


# =========================================================
# MATCH RECORDING TO SRT

# =========================================================
# MATCH RECORDING TO SRT
# =========================================================

def determine_recording_datetime(
    video_path,
    ffprobe_data
):
    creation = (
        ffprobe_data
        .get("format", {})
        .get("tags", {})
        .get("creation_time")
    )

    if creation:
        try:
            parsed = datetime.fromisoformat(
                creation.replace(
                    "Z",
                    "+00:00"
                )
            )
            return parsed.replace(
                tzinfo=None
            )
        except ValueError:
            pass

    filename_dt = (
        parse_filename_datetime(
            video_path
        )
    )

    if filename_dt:
        return filename_dt

    return datetime.fromtimestamp(
        video_path.stat().st_mtime
    )


def find_matching_srt(
    recording_dt,
    video_path=None
):
    """
    Find a usable full-sermon SRT.

    Priority:
      1. Exact recording basename match, if non-empty
      2. Same-day closest non-empty SRT
      3. Closest non-empty SRT overall

    Zero-byte SRT files are ignored because they cannot contain
    transcript captions.
    """
    if not SRT_FOLDER.exists():
        return None

    # Exact basename match first.
    if video_path is not None:
        exact = (
            SRT_FOLDER
            /
            (
                Path(video_path).stem
                + ".srt"
            )
        )

        if exact.exists():
            try:
                if exact.stat().st_size > 0:
                    return exact

                print()
                print(
                    "Ignoring empty exact-match SRT:"
                )
                print(exact)

            except OSError:
                pass

    candidates = []

    for path in SRT_FOLDER.glob(
        "*.srt"
    ):
        try:
            size = path.stat().st_size
        except OSError:
            continue

        if size <= 0:
            continue

        srt_dt = (
            parse_filename_datetime(
                path
            )
        )

        if srt_dt is None:
            srt_dt = (
                datetime
                .fromtimestamp(
                    path.stat().st_mtime
                )
            )

        same_day = (
            srt_dt.date()
            ==
            recording_dt.date()
        )

        difference = abs(
            (
                srt_dt
                -
                recording_dt
            ).total_seconds()
        )

        candidates.append(
            (
                0 if same_day else 1,
                difference,
                path,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1]
        )
    )

    return candidates[0][2]


# =========================================================
# LOWER THIRD LOCALSTORAGE
# =========================================================

def copy_lower_third_leveldb():
    temp_root = Path(
        tempfile.mkdtemp(
            prefix="sermon_ai_lowerthirds_"
        )
    )

    destination = (
        temp_root / "leveldb"
    )

    shutil.copytree(
        LOWER_THIRDS_LEVELDB,
        destination,
        dirs_exist_ok=True
    )

    return (
        temp_root,
        destination
    )


def interesting_lower_third_key(key):
    # Includes BOTH current active fields:
    #   alt-1-name / alt-1-info
    # and saved memory fields:
    #   alt-1-name-1 ... alt-4-info-10
    return re.fullmatch(
        r"alt-[1-4]-(?:name|info)(?:-(?:[1-9]|10))?",
        key
    ) is not None


def normalize_storage_value(value):
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

    return repair_text(
        str(value)
    )


def read_lower_third_slots():
    """
    Read current ACTIVE lower-third values plus all 40 memory slots.

    OBS's live LevelDB is copied to a temporary folder first. For
    duplicate LevelDB records, the record with the highest sequence
    number wins so stale values do not overwrite newer ones.
    """
    if not LOWER_THIRDS_LEVELDB.exists():
        return []

    temp_root = None

    try:
        (
            temp_root,
            copied_db,
        ) = copy_lower_third_leveldb()

        values = {}

        with (
            ccl_chromium_localstorage
            .LocalStoreDb(
                copied_db
            )
        ) as local_storage:

            for storage_key in (
                local_storage
                .iter_storage_keys()
            ):
                try:
                    records = (
                        local_storage
                        .iter_records_for_storage_key(
                            storage_key
                        )
                    )

                    for record in records:
                        key = (
                            normalize_storage_value(
                                record.script_key
                            )
                        )

                        if not (
                            interesting_lower_third_key(
                                key
                            )
                        ):
                            continue

                        value = (
                            normalize_storage_value(
                                record.value
                            )
                        )

                        try:
                            sequence = int(
                                getattr(
                                    record,
                                    "leveldb_seq_number",
                                    0
                                ) or 0
                            )
                        except (
                            TypeError,
                            ValueError
                        ):
                            sequence = 0

                        previous = (
                            values.get(
                                key
                            )
                        )

                        if (
                            previous is None
                            or
                            sequence
                            >=
                            previous[
                                "sequence"
                            ]
                        ):
                            values[key] = {
                                "sequence":
                                    sequence,
                                "value":
                                    value,
                            }

                except Exception:
                    continue

        def get_value(key):
            record = values.get(
                key,
                {
                    "sequence": 0,
                    "value": "",
                }
            )

            return (
                record["value"],
                record["sequence"],
            )

        slots = []

        for lower_third in range(
            1,
            5
        ):
            active_name, active_name_seq = (
                get_value(
                    f"alt-{lower_third}-name"
                )
            )

            active_info, active_info_seq = (
                get_value(
                    f"alt-{lower_third}-info"
                )
            )

            if (
                active_name
                or
                active_info
            ):
                slots.append({
                    "lower_third":
                        lower_third,
                    "slot":
                        0,
                    "slot_label":
                        "ACTIVE",
                    "active":
                        True,
                    "sequence":
                        max(
                            active_name_seq,
                            active_info_seq,
                        ),
                    "name":
                        active_name,
                    "info":
                        active_info,
                })

            for slot in range(
                1,
                11
            ):
                name, name_seq = (
                    get_value(
                        (
                            f"alt-{lower_third}"
                            f"-name-{slot}"
                        )
                    )
                )

                info, info_seq = (
                    get_value(
                        (
                            f"alt-{lower_third}"
                            f"-info-{slot}"
                        )
                    )
                )

                if not name and not info:
                    continue

                slots.append({
                    "lower_third":
                        lower_third,
                    "slot":
                        slot,
                    "slot_label":
                        f"Slot {slot}",
                    "active":
                        False,
                    "sequence":
                        max(
                            name_seq,
                            info_seq,
                        ),
                    "name":
                        name,
                    "info":
                        info,
                })

        return slots

    except Exception as error:
        print(
            "Lower-third fallback "
            "could not be read:"
        )
        print(error)
        return []

    finally:
        if temp_root is not None:
            shutil.rmtree(
                temp_root,
                ignore_errors=True
            )


# =========================================================
# LOWER THIRD CLASSIFICATION

# =========================================================
# LOWER THIRD CLASSIFICATION
# =========================================================

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


def looks_like_scripture(text):
    return (
        SCRIPTURE_PATTERN.search(
            text or ""
        )
        is not None
    )


def looks_like_preacher(
    text,
    allow_plain_name=False
):
    """
    Explicit titles such as Pastor/Elder are always accepted.

    Plain names such as 'Brian Zerbe' are only accepted when the
    caller allows them (normally the Info field). This avoids treating
    sermon text such as 'The Problem of Fear.' or 'Proclaim God Boldly.'
    as a person's name.
    """
    original = repair_text(
        text or ""
    ).strip()

    lower = normalize_text(
        original
    )

    if not lower:
        return False

    clergy_words = [
        "pastor ",
        "elder ",
        "reverend ",
        "rev ",
        "guest preacher",
        "guest speaker",
    ]

    if any(
        phrase in lower
        for phrase in clergy_words
    ):
        return True

    if not allow_plain_name:
        return False

    if looks_like_scripture(
        original
    ):
        return False

    if re.search(
        r"[.!?:;]$",
        original
    ):
        return False

    words = [
        word
        for word in re.split(
            r"\s+",
            original
        )
        if word
    ]

    if not (
        2 <= len(words) <= 3
    ):
        return False

    blocked_words = {
        "the",
        "of",
        "and",
        "from",
        "god",
        "lord",
        "king",
        "kingdom",
        "fear",
        "church",
        "baptist",
        "happy",
        "easter",
        "preaching",
        "title",
    }

    normalized_words = [
        re.sub(
            r"[^A-Za-z'-]",
            "",
            word
        )
        for word in words
    ]

    if any(
        not word
        for word in normalized_words
    ):
        return False

    if any(
        word.lower()
        in blocked_words
        for word in normalized_words
    ):
        return False

    if not all(
        re.fullmatch(
            r"[A-Z][A-Za-z'’-]*",
            word
        )
        for word in normalized_words
    ):
        return False

    return True


def is_generic_lower_third(text):
    normalized = normalize_text(
        text
    )

    if not normalized:
        return True

    if normalized in (
        GENERIC_LOWER_THIRD_TEXT
    ):
        return True

    if (
        "baptist church of perry"
        in normalized
    ):
        return True

    return False


def candidate_similarity_to_sermon(
    text,
    full_transcript
):
    candidate = normalize_text(
        text
    )

    sermon = normalize_text(
        full_transcript
    )

    if not candidate or not sermon:
        return 0.0

    direct = fuzz.partial_ratio(
        candidate,
        sermon
    )

    candidate_words = [
        word
        for word in candidate.split()
        if len(word) >= 4
    ]

    if not candidate_words:
        return direct

    hits = sum(
        1
        for word in candidate_words
        if word in sermon
    )

    word_coverage = (
        hits
        /
        len(candidate_words)
        *
        100
    )

    return (
        direct * 0.70
        +
        word_coverage * 0.30
    )


def classify_lower_thirds(
    slots,
    full_transcript
):
    classified = []

    for item in slots:
        name = item[
            "name"
        ].strip()

        info = item[
            "info"
        ].strip()

        name_scripture = (
            looks_like_scripture(
                name
            )
        )

        info_scripture = (
            looks_like_scripture(
                info
            )
        )

        name_preacher = (
            looks_like_preacher(
                name,
                allow_plain_name=False,
            )
        )

        info_preacher = (
            looks_like_preacher(
                info,
                allow_plain_name=True,
            )
        )

        content_candidates = []

        if (
            name
            and
            not name_scripture
            and
            not name_preacher
            and
            not is_generic_lower_third(
                name
            )
        ):
            content_candidates.append(
                name
            )

        if (
            info
            and
            not info_scripture
            and
            not info_preacher
            and
            not is_generic_lower_third(
                info
            )
        ):
            content_candidates.append(
                info
            )

        content_text = (
            content_candidates[0]
            if content_candidates
            else ""
        )

        scripture = ""

        if name_scripture:
            scripture = name
        elif info_scripture:
            scripture = info

        preacher = ""

        if name_preacher:
            preacher = name
        elif info_preacher:
            preacher = info

        content_similarity = (
            candidate_similarity_to_sermon(
                content_text,
                full_transcript
            )
            if content_text
            else 0.0
        )

        scripture_similarity = (
            candidate_similarity_to_sermon(
                scripture,
                full_transcript
            )
            if scripture
            else 0.0
        )

        preacher_similarity = (
            candidate_similarity_to_sermon(
                preacher,
                full_transcript
            )
            if preacher
            else 0.0
        )

        transcript_match = max(
            content_similarity,
            scripture_similarity,
            preacher_similarity * 0.60,
        )

        active_bonus = (
            12.0
            if item.get(
                "active"
            )
            else 0.0
        )

        selection_score = min(
            100.0,
            transcript_match
            +
            active_bonus
        )

        classified.append({
            **item,
            "content":
                content_text,
            "scripture":
                scripture,
            "preacher":
                preacher,
            "content_similarity":
                round(
                    content_similarity,
                    1
                ),
            "scripture_similarity":
                round(
                    scripture_similarity,
                    1
                ),
            "similarity":
                round(
                    transcript_match,
                    1
                ),
            "selection_score":
                round(
                    selection_score,
                    1
                ),
        })

    return classified


def normalized_scripture_key(text):
    value = repair_text(
        text or ""
    ).lower()

    value = re.sub(
        r"\s+",
        "",
        value
    )

    return value


def choose_dominant_scripture(
    candidates
):
    scores = {}
    display_values = {}

    for item in candidates:
        scripture = (
            item.get(
                "scripture"
            )
            or ""
        ).strip()

        if not scripture:
            continue

        key = normalized_scripture_key(
            scripture
        )

        if not key:
            continue

        score = float(
            item.get(
                "scripture_similarity",
                0
            )
        )

        score += (
            float(
                item.get(
                    "content_similarity",
                    0
                )
            )
            * 0.35
        )

        if item.get(
            "active"
        ):
            score += 18.0

        scores[key] = (
            scores.get(
                key,
                0.0
            )
            +
            score
        )

        display_values[
            key
        ] = scripture

    if not scores:
        return ""

    best_key = max(
        scores,
        key=scores.get
    )

    return display_values[
        best_key
    ]


def select_current_lower_thirds(
    classified,
    full_transcript=""
):
    """
    Transcript available:
      - keep only candidates that match the current sermon
      - determine the dominant Scripture reference
      - reject rows with conflicting Scripture references
      - keep preacher/title metadata only when its content exactly
        matches a row tied to the dominant Scripture

    No transcript:
      - use only one coherent ACTIVE row
    """

    if normalize_text(
        full_transcript
    ):
        matched = [
            item
            for item in classified
            if (
                item[
                    "selection_score"
                ]
                >=
                LOWER_THIRD_MATCH_THRESHOLD
            )
        ]

        if not matched:
            return []

        dominant_scripture = (
            choose_dominant_scripture(
                matched
            )
        )

        dominant_key = (
            normalized_scripture_key(
                dominant_scripture
            )
        )

        if not dominant_key:
            matched.sort(
                key=lambda item: (
                    item.get(
                        "selection_score",
                        0
                    ),
                    bool(
                        item.get(
                            "active"
                        )
                    ),
                    item.get(
                        "sequence",
                        0
                    ),
                ),
                reverse=True,
            )

            return matched[
                :MAX_LOWER_THIRD_CANDIDATES
            ]

        dominant_content_keys = set()

        for item in matched:
            scripture_key = (
                normalized_scripture_key(
                    item.get(
                        "scripture",
                        ""
                    )
                )
            )

            if (
                scripture_key
                ==
                dominant_key
                and
                item.get(
                    "content"
                )
            ):
                dominant_content_keys.add(
                    normalize_text(
                        item[
                            "content"
                        ]
                    )
                )

        selected = []

        for item in matched:
            scripture_key = (
                normalized_scripture_key(
                    item.get(
                        "scripture",
                        ""
                    )
                )
            )

            content_key = (
                normalize_text(
                    item.get(
                        "content",
                        ""
                    )
                )
            )

            # Explicit conflicting Scripture = old/unrelated sermon.
            if (
                scripture_key
                and
                scripture_key
                !=
                dominant_key
            ):
                continue

            if (
                scripture_key
                ==
                dominant_key
            ):
                selected.append(
                    item
                )
                continue

            # Allow a preacher metadata row only when the exact same
            # title/content is already tied to the dominant Scripture.
            if (
                content_key
                and
                content_key
                in
                dominant_content_keys
            ):
                selected.append(
                    item
                )

        selected.sort(
            key=lambda item: (
                item.get(
                    "selection_score",
                    0
                ),
                bool(
                    item.get(
                        "active"
                    )
                ),
                item.get(
                    "sequence",
                    0
                ),
            ),
            reverse=True,
        )

        return selected[
            :MAX_LOWER_THIRD_CANDIDATES
        ]

    # -------------------------------------------------------------
    # No transcript fallback
    # -------------------------------------------------------------

    active = [
        item
        for item in classified
        if (
            item.get(
                "active"
            )
            and
            (
                item.get(
                    "content"
                )
                or
                item.get(
                    "scripture"
                )
                or
                item.get(
                    "preacher"
                )
            )
        )
    ]

    def active_fallback_score(item):
        has_content = bool(
            item.get(
                "content"
            )
        )

        has_scripture = bool(
            item.get(
                "scripture"
            )
        )

        has_preacher = bool(
            item.get(
                "preacher"
            )
        )

        if (
            has_content
            and
            has_scripture
        ):
            quality = 100

        elif (
            has_content
            and
            has_preacher
        ):
            quality = 80

        elif has_content:
            quality = 60

        elif (
            has_scripture
            and
            has_preacher
        ):
            quality = 50

        elif has_scripture:
            quality = 40

        else:
            quality = 20

        return (
            quality,
            item.get(
                "sequence",
                0
            ),
        )

    active.sort(
        key=active_fallback_score,
        reverse=True,
    )

    return active[:1]


def filename_is_timestamp_only(
    filename_title
):
    return (
        re.fullmatch(
            r"\d{4}-\d{2}-\d{2}"
            r"(?:\s+\d{2}-\d{2}-\d{2})?",
            filename_title.strip()
        )
        is not None
    )


def build_content_groups(
    selected
):
    groups = {}

    for item in selected:
        content = (
            item.get(
                "content"
            )
            or ""
        ).strip()

        if not content:
            continue

        key = normalize_text(
            content
        )

        if not key:
            continue

        group = groups.setdefault(
            key,
            {
                "content":
                    content,
                "rows":
                    [],
                "scriptures":
                    [],
                "preachers":
                    [],
                "active":
                    False,
                "max_score":
                    0.0,
                "min_slot":
                    999,
            }
        )

        group[
            "rows"
        ].append(
            item
        )

        group[
            "active"
        ] = (
            group["active"]
            or
            bool(
                item.get(
                    "active"
                )
            )
        )

        group[
            "max_score"
        ] = max(
            group[
                "max_score"
            ],
            float(
                item.get(
                    "selection_score",
                    0
                )
            )
        )

        slot = item.get(
            "slot"
        )

        if (
            isinstance(
                slot,
                int
            )
            and
            slot > 0
        ):
            group[
                "min_slot"
            ] = min(
                group[
                    "min_slot"
                ],
                slot
            )

        scripture = (
            item.get(
                "scripture"
            )
            or ""
        ).strip()

        if (
            scripture
            and
            scripture
            not in
            group[
                "scriptures"
            ]
        ):
            group[
                "scriptures"
            ].append(
                scripture
            )

        preacher = (
            item.get(
                "preacher"
            )
            or ""
        ).strip()

        if (
            preacher
            and
            preacher
            not in
            group[
                "preachers"
            ]
        ):
            group[
                "preachers"
            ].append(
                preacher
            )

    return list(
        groups.values()
    )


def title_group_score(
    group,
    filename_title
):
    score = float(
        group[
            "max_score"
        ]
    )

    if group[
        "scriptures"
    ]:
        score += 18.0

    if group[
        "preachers"
    ]:
        score += 30.0

    # Strong signal: same text was saved once with Scripture and once
    # with preacher metadata. That is usually a sermon title preset.
    if (
        group[
            "scriptures"
        ]
        and
        group[
            "preachers"
        ]
    ):
        score += 35.0

    if group[
        "active"
    ]:
        score += 12.0

    score += min(
        len(
            group[
                "rows"
            ]
        ),
        3
    ) * 5.0

    if (
        filename_title
        and
        not filename_is_timestamp_only(
            filename_title
        )
    ):
        filename_match = fuzz.ratio(
            normalize_text(
                filename_title
            ),
            normalize_text(
                group[
                    "content"
                ]
            ),
        )

        if filename_match >= 72:
            score += 30.0

    return score


def infer_lower_third_metadata(
    selected,
    filename_title
):
    groups = build_content_groups(
        selected
    )

    if groups:
        title_group = max(
            groups,
            key=lambda group:
                title_group_score(
                    group,
                    filename_title,
                )
        )

        sermon_title = (
            title_group[
                "content"
            ]
        )

    elif (
        filename_title
        and
        not filename_is_timestamp_only(
            filename_title
        )
    ):
        title_group = None
        sermon_title = (
            filename_title
        )

    else:
        title_group = None
        sermon_title = (
            "Not automatically detected"
        )

    dominant_scripture = (
        choose_dominant_scripture(
            selected
        )
    )

    scripture = ""
    preacher = ""

    if title_group:
        if title_group[
            "scriptures"
        ]:
            scripture = (
                title_group[
                    "scriptures"
                ][0]
            )

        if title_group[
            "preachers"
        ]:
            preacher = (
                title_group[
                    "preachers"
                ][0]
            )

    if not scripture:
        scripture = (
            dominant_scripture
            or
            ""
        )

    # Do not pull a preacher from an unrelated lower third.
    if not preacher:
        title_key = normalize_text(
            sermon_title
        )

        for item in selected:
            if (
                item.get(
                    "preacher"
                )
                and
                normalize_text(
                    item.get(
                        "content",
                        ""
                    )
                )
                ==
                title_key
            ):
                preacher = (
                    item[
                        "preacher"
                    ]
                )
                break

    title_key = normalize_text(
        sermon_title
    )

    dominant_key = (
        normalized_scripture_key(
            scripture
        )
    )

    point_groups = []

    for group in groups:
        if (
            normalize_text(
                group[
                    "content"
                ]
            )
            ==
            title_key
        ):
            continue

        group_scripture_keys = {
            normalized_scripture_key(
                value
            )
            for value in group[
                "scriptures"
            ]
        }

        if (
            dominant_key
            and
            dominant_key
            not in
            group_scripture_keys
        ):
            continue

        point_groups.append(
            group
        )

    # Saved slots are useful for likely point order.
    point_groups.sort(
        key=lambda group: (
            group[
                "min_slot"
            ],
            -group[
                "max_score"
            ],
        )
    )

    point_rows = []

    for group in point_groups:
        representative = max(
            group[
                "rows"
            ],
            key=lambda item: (
                bool(
                    item.get(
                        "active"
                    )
                ),
                item.get(
                    "selection_score",
                    0
                ),
            )
        )

        point_rows.append(
            representative
        )

    content_rows = []

    for group in groups:
        representative = max(
            group[
                "rows"
            ],
            key=lambda item:
                item.get(
                    "selection_score",
                    0
                )
        )

        content_rows.append(
            representative
        )

    return {
        "sermon_title":
            sermon_title,
        "scripture":
            scripture,
        "preacher":
            preacher,
        "content_rows":
            content_rows,
        "point_rows":
            point_rows,
        "dominant_scripture":
            dominant_scripture,
    }


# =========================================================
# TRANSCRIPT HELPERS

# =========================================================
# TRANSCRIPT HELPERS

# =========================================================
# TRANSCRIPT HELPERS
# =========================================================

def get_transcript_range(
    entries,
    start,
    end
):
    pieces = []

    for entry in entries:
        if (
            entry["end"] >= start
            and
            entry["start"] <= end
        ):
            pieces.append(
                entry["text"]
            )

    return " ".join(
        pieces
    ).strip()


def find_scripture_reference(
    chapters,
    full_transcript
):
    combined = " ".join(
        chapter["title"]
        for chapter in chapters
    )

    combined += " "
    combined += full_transcript[:10000]

    match = SCRIPTURE_PATTERN.search(
        combined
    )

    if not match:
        return ""

    return repair_text(
        match.group(0)
    )


def clean_transcript(text):
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def readable_time(seconds):
    seconds = int(
        max(
            0,
            seconds
        )
    )

    hours = (
        seconds // 3600
    )

    minutes = (
        seconds % 3600
    ) // 60

    secs = (
        seconds % 60
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


def write_srt_debug_file(
    srt_path,
    video_path
):
    """
    If the SRT file exists but parses to zero captions, write a small
    diagnostic file so we can see the actual encoding/timestamp layout
    without guessing.
    """
    if not srt_path:
        return None

    try:
        data = Path(
            srt_path
        ).read_bytes()
    except Exception as error:
        print(
            "Could not read SRT for debug:"
        )
        print(error)
        return None

    recording_date = (
        parse_filename_datetime(
            video_path
        )
    )

    date_string = (
        recording_date.strftime(
            "%Y-%m-%d"
        )
        if recording_date
        else datetime.now().strftime(
            "%Y-%m-%d"
        )
    )

    debug_path = (
        SERMON_DATA_FOLDER
        /
        (
            date_string
            +
            "_SRT_Debug.txt"
        )
    )

    decoded = None
    used_encoding = None

    for encoding in [
        "utf-8-sig",
        "utf-8",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
        "cp1252",
    ]:
        try:
            decoded = data.decode(
                encoding
            )
            used_encoding = encoding
            break
        except Exception:
            continue

    if decoded is None:
        decoded = data.decode(
            "utf-8",
            errors="replace"
        )
        used_encoding = (
            "utf-8 with replacement"
        )

    lines = (
        decoded
        .replace(
            "\r\n",
            "\n"
        )
        .replace(
            "\r",
            "\n"
        )
        .splitlines()
    )

    arrow_lines = [
        line
        for line in lines
        if "-->" in line
    ]

    with open(
        debug_path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "SERMON AI - SRT PARSER DEBUG\n"
        )
        file.write(
            "=" * 78
            + "\n\n"
        )

        file.write(
            f"SRT PATH:\n{srt_path}\n\n"
        )

        file.write(
            f"BYTE SIZE:\n{len(data)}\n\n"
        )

        file.write(
            f"DECODED AS:\n{used_encoding}\n\n"
        )

        file.write(
            f"TOTAL LINES:\n{len(lines)}\n\n"
        )

        file.write(
            f"LINES CONTAINING '-->':\n"
            f"{len(arrow_lines)}\n\n"
        )

        file.write(
            "FIRST 96 BYTES (HEX)\n"
        )
        file.write(
            data[:96].hex(" ")
            + "\n\n"
        )

        file.write(
            "FIRST 80 DECODED LINES\n"
        )
        file.write(
            "-" * 78
            + "\n"
        )

        for index, line in enumerate(
            lines[:80],
            start=1,
        ):
            file.write(
                f"{index:03d}: "
                f"{repr(line)}\n"
            )

        if arrow_lines:
            file.write(
                "\nFIRST 20 TIMESTAMP-LIKE LINES\n"
            )
            file.write(
                "-" * 78
                + "\n"
            )

            for line in arrow_lines[:20]:
                file.write(
                    repr(line)
                    + "\n"
                )

    return debug_path


def find_best_point_start(
    point_text,
    srt_entries
):
    """
    Find the SRT location where a sermon point is most likely announced.

    Lower-third point wording often differs slightly from what Whisper
    heard, so compare the point text against short sliding transcript
    windows instead of requiring an exact phrase.
    """
    if not point_text or not srt_entries:
        return None

    target = normalize_text(
        point_text
    )

    if not target:
        return None

    best = None

    # 4-10 SRT entries is usually enough to contain a spoken point
    # announcement while staying local enough to avoid accidental
    # matches elsewhere in the sermon.
    for window_size in range(
        4,
        11
    ):
        for start_index in range(
            0,
            len(srt_entries)
            - window_size
            + 1
        ):
            window_entries = (
                srt_entries[
                    start_index:
                    start_index
                    + window_size
                ]
            )

            window_text = " ".join(
                entry["text"]
                for entry in window_entries
            )

            normalized_window = normalize_text(
                window_text
            )

            if not normalized_window:
                continue

            fuzzy_score = fuzz.partial_ratio(
                target,
                normalized_window
            )

            target_words = [
                word
                for word in target.split()
                if len(word) >= 4
            ]

            if target_words:
                hits = sum(
                    1
                    for word in target_words
                    if word in normalized_window
                )

                coverage = (
                    hits
                    /
                    len(target_words)
                    *
                    100
                )
            else:
                coverage = 0.0

            score = (
                fuzzy_score * 0.75
                +
                coverage * 0.25
            )

            if (
                best is None
                or
                score > best["score"]
            ):
                best = {
                    "score":
                        score,
                    "start_index":
                        start_index,
                    "end_index":
                        start_index
                        + window_size
                        - 1,
                    "start_time":
                        window_entries[0][
                            "start"
                        ],
                    "end_time":
                        window_entries[-1][
                            "end"
                        ],
                }

    if best is None:
        return None

    # Below this, the match is too weak to pretend we located the point.
    if best["score"] < 58:
        return None

    return best


def build_point_excerpt(
    srt_entries,
    point_match,
    before_seconds=20,
    after_seconds=300,
    max_chars=4500,
):
    """
    Build a compact transcript excerpt around the point announcement.

    Default:
      20 seconds before the point
      5 minutes after the point

    The character cap keeps the thumbnail-prep file useful instead of
    reproducing the entire sermon.
    """
    if not point_match:
        return ""

    start_time = max(
        0,
        point_match[
            "start_time"
        ]
        - before_seconds
    )

    end_time = (
        point_match[
            "start_time"
        ]
        + after_seconds
    )

    pieces = []

    for entry in srt_entries:
        if (
            entry["end"] >= start_time
            and
            entry["start"] <= end_time
        ):
            pieces.append(
                entry["text"]
            )

    excerpt = clean_transcript(
        " ".join(
            pieces
        )
    )

    if len(excerpt) <= max_chars:
        return excerpt

    # Prefer the beginning of each point section because that's where
    # the preacher usually states and explains the point most directly.
    trimmed = excerpt[
        :max_chars
    ]

    # Avoid ending halfway through a word where possible.
    last_space = trimmed.rfind(
        " "
    )

    if last_space > (
        max_chars
        - 250
    ):
        trimmed = trimmed[
            :last_space
        ]

    return (
        trimmed.rstrip()
        + " ..."
    )


def locate_point_sections(
    point_rows,
    srt_entries
):
    """
    Return point rows with likely SRT locations and compact transcript
    excerpts. Keeps point order supplied by the lower-third memory slots.
    """
    located = []

    for item in (
        point_rows
        or []
    ):
        point_text = (
            item.get(
                "content"
            )
            or ""
        ).strip()

        if not point_text:
            continue

        match = find_best_point_start(
            point_text,
            srt_entries,
        )

        excerpt = build_point_excerpt(
            srt_entries,
            match,
        )

        located.append({
            "item":
                item,
            "point_text":
                point_text,
            "match":
                match,
            "excerpt":
                excerpt,
        })

    return located


# =========================================================
# WRITE PREP FILE
# =========================================================

def create_prep_file(
    video_path,
    srt_path,
    chapters,
    srt_entries,
    lower_third_selected,
    lower_third_metadata,
):
    filename_title = (
        clean_sermon_title(
            video_path.name
        )
    )

    full_transcript = clean_transcript(
        " ".join(
            entry["text"]
            for entry in srt_entries
        )
    )

    point_chapters = useful_chapters(
        chapters
    )

    if point_chapters:
        structure_source = (
            "OBS embedded chapter markers"
        )
    elif lower_third_selected:
        if full_transcript:
            structure_source = (
                "Animated Lower Thirds fallback "
                "(cross-checked against full-sermon SRT)"
            )
        else:
            structure_source = (
                "Animated Lower Thirds ACTIVE-value fallback "
                "(no usable SRT transcript)"
            )
    else:
        structure_source = (
            "Full-sermon SRT fallback"
        )

    sermon_title = (
        lower_third_metadata.get(
            "sermon_title"
        )
        or filename_title
    )

    scripture = (
        lower_third_metadata.get(
            "scripture"
        )
        or find_scripture_reference(
            chapters,
            full_transcript,
        )
        or "Not automatically detected"
    )

    preacher = (
        lower_third_metadata.get(
            "preacher"
        )
        or "Not automatically detected"
    )

    recording_date = (
        parse_filename_datetime(
            video_path
        )
    )

    date_string = (
        recording_date.strftime(
            "%Y-%m-%d"
        )
        if recording_date
        else datetime.now().strftime(
            "%Y-%m-%d"
        )
    )

    output_path = (
        SERMON_DATA_FOLDER
        /
        (
            date_string
            +
            "_Thumbnail_Prep.txt"
        )
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            "YOUTUBE THUMBNAIL PREP\n"
        )
        file.write(
            "=" * 78
            + "\n\n"
        )

        file.write(
            f"STRUCTURE SOURCE\n"
            f"{structure_source}\n\n"
        )

        file.write(
            "SERMON TITLE\n"
        )
        file.write(
            sermon_title
            + "\n\n"
        )

        file.write(
            "SCRIPTURE REFERENCE\n"
        )
        file.write(
            scripture
            + "\n\n"
        )

        file.write(
            "PREACHER\n"
        )
        file.write(
            preacher
            + "\n\n"
        )

        file.write(
            "SOURCE RECORDING\n"
        )
        file.write(
            str(video_path)
            + "\n\n"
        )

        file.write(
            "SOURCE SRT\n"
        )
        file.write(
            (
                str(srt_path)
                if srt_path
                else
                "No matching SRT found"
            )
            + "\n\n"
        )

        # ---------------- Chapters ----------------

        file.write(
            "=" * 78
            + "\n"
        )
        file.write(
            "OBS CHAPTER MARKERS\n"
        )
        file.write(
            "=" * 78
            + "\n\n"
        )

        if chapters:
            for chapter in chapters:
                file.write(
                    f"{readable_time(chapter['start'])}"
                    f"  "
                    f"{chapter['title']}"
                    f"\n"
                )
        else:
            file.write(
                "No chapter markers were found.\n"
            )

        file.write("\n")

        # ---------------- Lower thirds ----------------

        file.write(
            "=" * 78
            + "\n"
        )
        file.write(
            "ANIMATED LOWER THIRD FALLBACK\n"
        )
        file.write(
            "=" * 78
            + "\n\n"
        )

        if lower_third_selected:
            if full_transcript:
                file.write(
                    "These entries survived comparison "
                    "against the current full-sermon SRT.\n\n"
                )
            else:
                file.write(
                    "No usable SRT transcript was available. "
                    "Using the single strongest current ACTIVE "
                    "lower-third row without mixing metadata "
                    "from other lower thirds.\n\n"
                )

            for item in lower_third_selected:
                file.write(
                    (
                        f"LT{item['lower_third']} "
                        f"{item.get('slot_label') or ('Slot ' + str(item['slot']))}\n"
                    )
                )
                file.write(
                    f"  Name: {item['name']}\n"
                )
                file.write(
                    f"  Info: {item['info']}\n"
                )

                if item["content"]:
                    file.write(
                        (
                            f"  Transcript match: "
                            f"{item['similarity']:.1f}%\n"
                            f"  Selection score: "
                            f"{item.get('selection_score', item['similarity']):.1f}%\n"
                        )
                    )

                if item["scripture"]:
                    file.write(
                        (
                            f"  Scripture candidate: "
                            f"{item['scripture']}\n"
                        )
                    )

                if item["preacher"]:
                    file.write(
                        (
                            f"  Preacher candidate: "
                            f"{item['preacher']}\n"
                        )
                    )

                file.write("\n")
        else:
            file.write(
                "No lower-third entries could be confidently "
                "associated with this sermon.\n\n"
            )

        # ---------------- Structure ----------------

        file.write(
            "=" * 78
            + "\n"
        )
        file.write(
            "SERMON STRUCTURE / CONTEXT\n"
        )
        file.write(
            "=" * 78
            + "\n\n"
        )

        if point_chapters:
            for index, chapter in enumerate(
                point_chapters,
                start=1,
            ):
                file.write(
                    f"POINT / SECTION {index}\n"
                )
                file.write(
                    "-" * 78
                    + "\n"
                )
                file.write(
                    chapter["title"]
                    + "\n"
                )
                file.write(
                    (
                        f"Chapter time: "
                        f"{readable_time(chapter['start'])}"
                        f" - "
                        f"{readable_time(chapter['end'])}"
                        f"\n\n"
                    )
                )

                transcript = (
                    get_transcript_range(
                        srt_entries,
                        chapter["start"],
                        chapter["end"],
                    )
                )

                transcript = (
                    clean_transcript(
                        transcript
                    )
                )

                if transcript:
                    file.write(
                        "RELEVANT SERMON TRANSCRIPT\n"
                    )
                    file.write(
                        transcript
                        + "\n\n"
                    )
                else:
                    file.write(
                        "No matching transcript text found "
                        "for this chapter range.\n\n"
                    )

        elif lower_third_metadata.get(
            "content_rows"
        ):
            file.write(
                "No useful chapter markers were available.\n"
            )

            if full_transcript:
                file.write(
                    "Animated Lower Thirds were cross-checked "
                    "against the current full-sermon SRT.\n\n"
                )
            else:
                file.write(
                    "No usable SRT transcript was available. "
                    "The current ACTIVE lower third is being "
                    "used as an unverified fallback.\n\n"
                )

            file.write(
                "RECOVERED SERMON TITLE\n"
            )
            file.write(
                "-" * 78
                + "\n"
            )
            file.write(
                (
                    lower_third_metadata.get(
                        "sermon_title"
                    )
                    or
                    "Not automatically detected"
                )
                + "\n\n"
            )

            point_rows = (
                lower_third_metadata.get(
                    "point_rows"
                )
                or
                []
            )

            located_points = (
                locate_point_sections(
                    point_rows,
                    srt_entries,
                )
                if srt_entries
                else []
            )

            file.write(
                "LIKELY SERMON POINTS / SECTIONS\n"
            )
            file.write(
                "=" * 78
                + "\n\n"
            )

            if located_points:
                for index, located in enumerate(
                    located_points,
                    start=1,
                ):
                    item = located[
                        "item"
                    ]

                    point_text = located[
                        "point_text"
                    ]

                    match = located[
                        "match"
                    ]

                    excerpt = located[
                        "excerpt"
                    ]

                    file.write(
                        f"POINT {index}\n"
                    )
                    file.write(
                        "-" * 78
                        + "\n"
                    )

                    file.write(
                        point_text
                        + "\n"
                    )

                    file.write(
                        (
                            f"Lower-third/SRT match: "
                            f"{item['similarity']:.1f}%\n"
                        )
                    )

                    if match:
                        file.write(
                            (
                                f"Likely point start: "
                                f"{readable_time(match['start_time'])}\n"
                            )
                        )

                        file.write(
                            (
                                f"Point-location confidence: "
                                f"{match['score']:.1f}%\n"
                            )
                        )

                    file.write("\n")

                    if excerpt:
                        file.write(
                            "RELEVANT TRANSCRIPT EXCERPT\n"
                        )
                        file.write(
                            "-" * 78
                            + "\n"
                        )
                        file.write(
                            excerpt
                            + "\n\n"
                        )
                    else:
                        file.write(
                            "No reliable transcript excerpt "
                            "could be located for this point.\n\n"
                        )

            elif point_rows:
                for index, item in enumerate(
                    point_rows,
                    start=1,
                ):
                    content = (
                        item.get(
                            "content"
                        )
                        or
                        ""
                    ).strip()

                    if not content:
                        continue

                    file.write(
                        (
                            f"{index}. {content} "
                            f"(match {item['similarity']:.1f}%)\n"
                        )
                    )

                file.write(
                    "\nNo usable SRT transcript was available "
                    "to create point-specific excerpts.\n\n"
                )

            else:
                file.write(
                    "No distinct sermon points were "
                    "confidently recovered.\n\n"
                )

            # Add a short overall sermon snapshot rather than the
            # entire transcript. This gives ChatGPT context outside the
            # point excerpts without making the prep file enormous.
            if full_transcript:
                file.write(
                    "OVERALL SERMON SNAPSHOT\n"
                )
                file.write(
                    "-" * 78
                    + "\n"
                )

                snapshot = (
                    full_transcript[
                        :3000
                    ]
                )

                if (
                    len(
                        full_transcript
                    )
                    >
                    len(
                        snapshot
                    )
                ):
                    last_space = (
                        snapshot.rfind(
                            " "
                        )
                    )

                    if last_space > 2700:
                        snapshot = (
                            snapshot[
                                :last_space
                            ]
                        )

                    snapshot = (
                        snapshot.rstrip()
                        + " ..."
                    )

                file.write(
                    snapshot
                    + "\n\n"
                )

        else:
            file.write(
                "No chapter markers or reliable lower-third "
                "sermon points were available.\n"
            )
            file.write(
                "Using the full sermon transcript only. "
                "Do not invent official sermon points.\n\n"
            )
            file.write(
                "FULL SERMON TRANSCRIPT\n"
            )
            file.write(
                "-" * 78
                + "\n"
            )
            file.write(
                (
                    full_transcript
                    if full_transcript
                    else
                    "No SRT transcript was available."
                )
                + "\n\n"
            )

        # ---------------- ChatGPT request ----------------

        file.write(
            "=" * 78
            + "\n"
        )
        file.write(
            "READY-TO-PASTE CHATGPT REQUEST\n"
        )
        file.write(
            "=" * 78
            + "\n\n"
        )

        file.write(
            "Create a YouTube thumbnail concept for this "
            "morning's sermon using the sermon information "
            "contained in this file.\n\n"
        )

        file.write(
            f"SERMON TITLE:\n"
            f"{sermon_title}\n\n"
        )
        file.write(
            f"SCRIPTURE:\n"
            f"{scripture}\n\n"
        )
        file.write(
            f"PREACHER:\n"
            f"{preacher}\n\n"
        )

        file.write(
            "Use the chapter markers when they are available. "
            "If chapter markers were unavailable, use the "
            "recovered lower-third title/points and the "
            "point-specific transcript excerpts as the primary "
            "context. Those lower-third entries were cross-checked "
            "against the full-sermon SRT. If neither chapters nor "
            "reliable lower-third points exist, work from the "
            "available sermon transcript without inventing official "
            "sermon points.\n\n"
        )

        file.write(
            "Determine the strongest central visual metaphor "
            "from what the sermon actually emphasizes rather "
            "than merely illustrating the title literally.\n\n"
        )

        file.write(
            "THUMBNAIL REQUIREMENTS:\n"
        )
        file.write(
            "- 16:9 YouTube thumbnail\n"
        )
        file.write(
            "- Do not depict Jesus or God\n"
        )
        file.write(
            "- Do not put the sermon points on the thumbnail\n"
        )
        file.write(
            "- Sermon points are context only\n"
        )
        file.write(
            "- Use the sermon title prominently\n"
        )
        file.write(
            "- Include the Scripture reference if it helps "
            "the composition\n"
        )
        file.write(
            "- Keep text readable at thumbnail size\n"
        )
        file.write(
            "- Use one strong central visual metaphor\n"
        )
        file.write(
            "- Avoid generic church stock-photo imagery\n"
        )
        file.write(
            "- Avoid unnecessary crowns unless strongly "
            "justified by the sermon\n"
        )
        file.write(
            "- Keep the image visually clean and high contrast\n"
        )
        file.write(
            "- Give me 2-3 strong concept options first, "
            "then recommend the strongest one\n"
        )
        file.write(
            "- After I choose a concept, create the thumbnail image\n"
        )

    return output_path


# =========================================================
# OPEN NOTEPAD
# =========================================================

def open_in_notepad(path):
    try:
        subprocess.Popen(
            [
                "notepad.exe",
                str(path),
            ]
        )
    except Exception as error:
        print(
            "Could not automatically "
            "open Notepad:"
        )
        print(error)


# =========================================================
# MAIN
# =========================================================

def main():
    ensure_folder()

    print()
    print("=" * 78)
    print(
        "SERMON AI - THUMBNAIL PREPARATION"
    )
    print("=" * 78)
    print()

    video_path = (
        find_newest_sermon_recording()
    )

    if video_path is None:
        print(
            "No sermon recording found "
            "in D:\\2026"
        )
        return

    print("Newest recording:")
    print(video_path)
    print()

    try:
        ffprobe_data = (
            run_ffprobe(
                video_path
            )
        )
    except Exception as error:
        print(
            "Could not read chapter "
            "information:"
        )
        print(error)
        return

    chapters = extract_chapters(
        ffprobe_data
    )

    useful = useful_chapters(
        chapters
    )

    print(
        f"Found {len(chapters)} total "
        f"chapter marker(s)."
    )

    print(
        f"Found {len(useful)} useful "
        f"sermon chapter(s)."
    )

    recording_dt = (
        determine_recording_datetime(
            video_path,
            ffprobe_data,
        )
    )

    srt_path = find_matching_srt(
        recording_dt,
        video_path,
    )

    if srt_path:
        print()
        print(
            "Matching full-sermon SRT:"
        )
        print(srt_path)

        try:
            srt_entries = parse_srt(
                srt_path
            )

            print(
                f"Parsed {len(srt_entries)} "
                f"SRT caption entrie(s)."
            )

            if not srt_entries:
                print(
                    "WARNING: The SRT file was found, "
                    "but no caption entries could be parsed."
                )

                debug_path = write_srt_debug_file(
                    srt_path,
                    video_path,
                )

                if debug_path:
                    print(
                        "SRT parser debug file created:"
                    )
                    print(
                        debug_path
                    )
        except Exception as error:
            print(
                "Could not parse SRT:"
            )
            print(error)
            srt_entries = []
    else:
        print()
        print(
            "No usable non-empty matching SRT found."
        )
        srt_entries = []

    full_transcript = clean_transcript(
        " ".join(
            entry["text"]
            for entry in srt_entries
        )
    )

    lower_third_selected = []
    lower_third_metadata = {
        "sermon_title":
            clean_sermon_title(
                video_path.name
            ),
        "scripture":
            "",
        "preacher":
            "",
        "content_rows":
            [],
        "point_rows":
            [],
        "dominant_scripture":
            "",
    }

    if not useful:
        print()
        print(
            "No useful sermon chapter markers."
        )
        print(
            "Checking Animated Lower Thirds fallback..."
        )

        slots = read_lower_third_slots()

        print(
            f"Read {len(slots)} populated "
            f"lower-third row(s), including ACTIVE values."
        )

        classified = (
            classify_lower_thirds(
                slots,
                full_transcript,
            )
        )

        lower_third_selected = (
            select_current_lower_thirds(
                classified,
                full_transcript,
            )
        )

        lower_third_metadata = (
            infer_lower_third_metadata(
                lower_third_selected,
                clean_sermon_title(
                    video_path.name
                ),
            )
        )

        print(
            f"Selected "
            f"{len(lower_third_selected)} "
            f"lower-third candidate(s) "
            f"for this sermon."
        )

        if lower_third_metadata.get(
            "dominant_scripture"
        ):
            print(
                "Dominant lower-third Scripture:"
            )
            print(
                lower_third_metadata[
                    "dominant_scripture"
                ]
            )

        if lower_third_metadata.get(
            "sermon_title"
        ):
            print(
                "Recovered sermon title:"
            )
            print(
                lower_third_metadata[
                    "sermon_title"
                ]
            )

        if lower_third_metadata.get(
            "preacher"
        ):
            print(
                "Recovered preacher:"
            )
            print(
                lower_third_metadata[
                    "preacher"
                ]
            )

        point_rows = (
            lower_third_metadata.get(
                "point_rows"
            )
            or
            []
        )

        if point_rows and srt_entries:
            located_points = (
                locate_point_sections(
                    point_rows,
                    srt_entries,
                )
            )

            for index, located in enumerate(
                located_points,
                start=1,
            ):
                match = located[
                    "match"
                ]

                if match:
                    print(
                        (
                            f"Point {index} likely start: "
                            f"{readable_time(match['start_time'])} "
                            f"(confidence {match['score']:.1f}%)"
                        )
                    )
                else:
                    print(
                        (
                            f"Point {index} likely start: "
                            f"not confidently located"
                        )
                    )

    else:
        lower_third_metadata[
            "scripture"
        ] = find_scripture_reference(
            chapters,
            full_transcript,
        )

    output_path = create_prep_file(
        video_path,
        srt_path,
        chapters,
        srt_entries,
        lower_third_selected,
        lower_third_metadata,
    )

    print()
    print(
        "Thumbnail preparation "
        "file created:"
    )
    print(output_path)

    print()
    print(
        "Opening in Notepad..."
    )

    open_in_notepad(
        output_path
    )


if __name__ == "__main__":
    main()
