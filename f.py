import os
import re
import json
import shutil
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path

from rapidfuzz import fuzz
from ccl_chromium_reader import ccl_chromium_localstorage


# =========================================================
# SETTINGS
# =========================================================

SERMON_FOLDER = Path(r"D:\2026")
SRT_FOLDER = Path(r"D:\2026\SRT files")

SHORTS_ROOT = Path(r"D:\2026\shorts\ai shorts")
SERMON_DATA_FOLDER = SHORTS_ROOT / "Sermon Data"

LOWER_THIRDS_LEVELDB = Path(
    r"C:\Users\Vicel\AppData\Roaming\obs-studio"
    r"\plugin_config\obs-browser\Local Storage\leveldb"
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
    match = re.match(
        r"(\d+):(\d{2}):(\d{2})"
        r"[,.](\d{3})",
        value.strip(),
    )

    if not match:
        return None

    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    milliseconds = int(match.group(4))

    return (
        hours * 3600
        + minutes * 60
        + seconds
        + milliseconds / 1000
    )


def parse_srt(path):
    with open(
        path,
        "r",
        encoding="utf-8-sig",
        errors="replace",
    ) as file:
        content = file.read()

    content = (
        content
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    blocks = re.split(
        r"\n\s*\n",
        content.strip()
    )

    entries = []

    for block in blocks:
        lines = [
            line.strip()
            for line
            in block.splitlines()
            if line.strip()
        ]

        if not lines:
            continue

        time_line_index = None

        for index, line in enumerate(lines):
            if "-->" in line:
                time_line_index = index
                break

        if time_line_index is None:
            continue

        timing = (
            lines[time_line_index]
            .split("-->", 1)
        )

        if len(timing) != 2:
            continue

        start = srt_time_to_seconds(
            timing[0]
        )

        end = srt_time_to_seconds(
            timing[1].split()[0]
        )

        if start is None or end is None:
            continue

        text = " ".join(
            lines[
                time_line_index + 1:
            ]
        )

        text = re.sub(
            r"<[^>]+>",
            "",
            text,
        )

        entries.append({
            "start": start,
            "end": end,
            "text": repair_text(text),
        })

    return entries


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
    recording_dt
):
    if not SRT_FOLDER.exists():
        return None

    candidates = []

    for path in SRT_FOLDER.glob(
        "*.srt"
    ):
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
    return re.fullmatch(
        r"alt-[1-4]-(?:name|info)-(?:[1-9]|10)",
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

                        if value:
                            values[key] = value

                except Exception:
                    continue

        slots = []

        for lower_third in range(
            1,
            5
        ):
            for slot in range(
                1,
                11
            ):
                name = values.get(
                    (
                        f"alt-{lower_third}"
                        f"-name-{slot}"
                    ),
                    "",
                )

                info = values.get(
                    (
                        f"alt-{lower_third}"
                        f"-info-{slot}"
                    ),
                    "",
                )

                if not name and not info:
                    continue

                slots.append({
                    "lower_third":
                        lower_third,
                    "slot":
                        slot,
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


def looks_like_preacher(text):
    lower = normalize_text(text)

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

    words = [
        word
        for word in re.split(
            r"\s+",
            repair_text(text).strip()
        )
        if word
    ]

    if (
        2 <= len(words) <= 4
        and
        not looks_like_scripture(
            text
        )
        and
        all(
            re.fullmatch(
                r"[A-Za-z.'’-]+",
                word
            )
            for word in words
        )
    ):
        return True

    return False


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
        name = item["name"].strip()
        info = item["info"].strip()

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
                name
            )
        )

        info_preacher = (
            looks_like_preacher(
                info
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

        similarity = (
            candidate_similarity_to_sermon(
                content_text,
                full_transcript
            )
            if content_text
            else 0.0
        )

        classified.append({
            **item,
            "content":
                content_text,
            "scripture":
                scripture,
            "preacher":
                preacher,
            "similarity":
                round(
                    similarity,
                    1
                ),
        })

    return classified


def select_current_lower_thirds(
    classified
):
    selected = []

    for item in classified:
        has_metadata = (
            bool(
                item["scripture"]
            )
            or
            bool(
                item["preacher"]
            )
        )

        content_matches = (
            bool(
                item["content"]
            )
            and
            item["similarity"]
            >= LOWER_THIRD_MATCH_THRESHOLD
        )

        if (
            has_metadata
            or
            content_matches
        ):
            selected.append(
                item
            )

    selected.sort(
        key=lambda item: (
            item["similarity"],
            bool(item["scripture"]),
            bool(item["preacher"]),
        ),
        reverse=True,
    )

    return selected[
        :MAX_LOWER_THIRD_CANDIDATES
    ]


def infer_lower_third_metadata(
    selected,
    filename_title
):
    scriptures = []
    preachers = []
    content_rows = []

    for item in selected:
        if item["scripture"]:
            scriptures.append(
                item["scripture"]
            )

        if item["preacher"]:
            preachers.append(
                item["preacher"]
            )

        if item["content"]:
            content_rows.append(
                item
            )

    scriptures = list(
        dict.fromkeys(
            scriptures
        )
    )

    preachers = list(
        dict.fromkeys(
            preachers
        )
    )

    sermon_title = filename_title

    filename_norm = normalize_text(
        filename_title
    )

    for item in content_rows:
        candidate = item[
            "content"
        ]

        similarity = fuzz.ratio(
            filename_norm,
            normalize_text(
                candidate
            )
        )

        if similarity >= 72:
            sermon_title = candidate
            break

    return {
        "sermon_title":
            sermon_title,
        "scripture":
            scriptures[0]
            if scriptures
            else "",
        "preacher":
            preachers[0]
            if preachers
            else "",
        "content_rows":
            content_rows,
    }


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
        structure_source = (
            "Animated Lower Thirds fallback"
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
            file.write(
                "These entries survived comparison "
                "against the current full-sermon SRT.\n\n"
            )

            for item in lower_third_selected:
                file.write(
                    (
                        f"LT{item['lower_third']} "
                        f"Slot {item['slot']}\n"
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
                            f"  Sermon-content similarity: "
                            f"{item['similarity']:.1f}%\n"
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
            file.write(
                "The following likely sermon title/point text "
                "was recovered from Animated Lower Thirds and "
                "matched against this sermon transcript.\n\n"
            )

            seen_content = set()

            for item in (
                lower_third_metadata[
                    "content_rows"
                ]
            ):
                content = (
                    item["content"].strip()
                )

                norm = normalize_text(
                    content
                )

                if (
                    not content
                    or
                    norm in seen_content
                    or
                    item["similarity"]
                    < LOWER_THIRD_MATCH_THRESHOLD
                ):
                    continue

                seen_content.add(norm)

                file.write(
                    (
                        f"- {content} "
                        f"(match {item['similarity']:.1f}%)\n"
                    )
                )

            file.write("\n")
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
            "lower-third fallback entries only as contextual "
            "clues and verify them against the sermon transcript. "
            "If neither exists, work from the sermon transcript "
            "without inventing official sermon points.\n\n"
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
        recording_dt
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
        except Exception as error:
            print(
                "Could not parse SRT:"
            )
            print(error)
            srt_entries = []
    else:
        print()
        print(
            "No matching SRT found."
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
            f"lower-third slot(s)."
        )

        classified = (
            classify_lower_thirds(
                slots,
                full_transcript,
            )
        )

        lower_third_selected = (
            select_current_lower_thirds(
                classified
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
