import os
import re
import json
import time
from datetime import datetime

from rapidfuzz import fuzz
from faster_whisper import WhisperModel


# =========================================================
# SETTINGS
# =========================================================

SHORTS_ROOT = r"D:\2026\shorts\ai shorts"

RAW_FOLDER = os.path.join(
    SHORTS_ROOT,
    "Raw"
)

LIVE_TRANSCRIPT_FOLDER = os.path.join(
    SHORTS_ROOT,
    "Transcripts"
)

VERIFIED_FOLDER = os.path.join(
    SHORTS_ROOT,
    "Verified"
)

REVIEW_FOLDER = os.path.join(
    SHORTS_ROOT,
    "Review"
)


# ---------------------------------------------------------
# FULL-SERMON SRT CROSS-CHECK
# ---------------------------------------------------------

FULL_SERMON_SRT_FOLDER = r"D:\2026\SRT files"

# Prefer an SRT from the same calendar date as the clip.
# If the clip filename contains a timestamp, use the closest
# same-day sermon SRT by filename timestamp.
FULL_SRT_VERIFIED_SIMILARITY = 82
FULL_SRT_MINIMUM_SIMILARITY = 65

# Number of subtitle entries kept before/after the best match
# for context reporting. These do not change the video trim
# because the whole-sermon SRT has a different time base.
FULL_SRT_CONTEXT_ENTRIES = 2


# ---------------------------------------------------------
# HIGH QUALITY WHISPER MODEL
# ---------------------------------------------------------

# Live Sermon AI uses "small".
# This second pass uses "medium" for better accuracy.

VERIFY_MODEL = "medium"

VERIFY_DEVICE = "cuda"

# This saves some VRAM compared with full float16.
# Good choice while OBS may also be using the GPU.
VERIFY_COMPUTE_TYPE = "int8_float16"


# ---------------------------------------------------------
# VERIFICATION THRESHOLDS
# ---------------------------------------------------------

# How similar the live transcription must be to the
# high-quality second transcription.

VERIFIED_SIMILARITY = 82

# Average Whisper word probability in matched passage.
VERIFIED_CONFIDENCE = 0.70


# Anything below these values needs manual review.

MINIMUM_SIMILARITY = 65
MINIMUM_CONFIDENCE = 0.55


# ---------------------------------------------------------
# TRIMMING
# ---------------------------------------------------------

# Keep a little context before and after the detected thought.

TRIM_PADDING_BEFORE = 1.5
TRIM_PADDING_AFTER = 2.0


# ---------------------------------------------------------
# WATCH MODE
# ---------------------------------------------------------

# False:
# Process everything currently in Raw and exit.
#
# True:
# Stay running and watch for new sermon clips.

WATCH_MODE = False

WATCH_INTERVAL_SECONDS = 10


# =========================================================
# BIBLICAL / THEOLOGICAL CONTEXT
# =========================================================

WHISPER_INITIAL_PROMPT = """
Christian sermon and Bible teaching.

Common biblical and theological terminology includes:

Jesus Christ,
God,
Holy Spirit,
Scripture,
Gospel,
grace,
mercy,
faith,
repentance,
righteousness,
justification,
sanctification,
salvation,
redemption,
resurrection,
disciples,
Pharisees,
apostles,
covenant,
kingdom of God,
Son of Man,
Son of God.

Bible books include:

Genesis,
Exodus,
Leviticus,
Numbers,
Deuteronomy,
Joshua,
Judges,
Ruth,
Samuel,
Kings,
Chronicles,
Ezra,
Nehemiah,
Esther,
Job,
Psalms,
Proverbs,
Ecclesiastes,
Isaiah,
Jeremiah,
Lamentations,
Ezekiel,
Daniel,
Hosea,
Joel,
Amos,
Obadiah,
Jonah,
Micah,
Nahum,
Habakkuk,
Zephaniah,
Haggai,
Zechariah,
Malachi,
Matthew,
Mark,
Luke,
John,
Acts,
Romans,
Corinthians,
Galatians,
Ephesians,
Philippians,
Colossians,
Thessalonians,
Timothy,
Titus,
Philemon,
Hebrews,
James,
Peter,
Jude,
Revelation.
"""


# =========================================================
# FILE HELPERS
# =========================================================

def ensure_folders():

    os.makedirs(
        VERIFIED_FOLDER,
        exist_ok=True
    )

    os.makedirs(
        REVIEW_FOLDER,
        exist_ok=True
    )


def get_video_files():

    if not os.path.exists(
        RAW_FOLDER
    ):
        return []

    extensions = (
        ".mp4",
        ".mkv",
        ".mov",
        ".m4v",
        ".ts",
    )

    results = []

    for name in os.listdir(
        RAW_FOLDER
    ):

        path = os.path.join(
            RAW_FOLDER,
            name
        )

        if (
            os.path.isfile(path)
            and name.lower().endswith(
                extensions
            )
        ):
            results.append(path)

    results.sort()

    return results


def get_base_name(video_path):

    return os.path.splitext(
        os.path.basename(
            video_path
        )
    )[0]


def already_processed(base_name):

    verified_json = os.path.join(
        VERIFIED_FOLDER,
        base_name + ".json"
    )

    review_json = os.path.join(
        REVIEW_FOLDER,
        base_name + ".json"
    )

    return (
        os.path.exists(
            verified_json
        )
        or
        os.path.exists(
            review_json
        )
    )


# =========================================================
# LIVE TRANSCRIPT
# =========================================================

def load_live_transcript(
    base_name
):

    path = os.path.join(
        LIVE_TRANSCRIPT_FOLDER,
        base_name + ".txt"
    )

    if not os.path.exists(path):

        return None, None

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        contents = file.read()

    marker = (
        "LIVE WHISPER TRANSCRIPT"
    )

    if marker not in contents:

        return None, path

    section = contents.split(
        marker,
        1
    )[1]

    # Remove the dashed separator
    lines = section.splitlines()

    cleaned_lines = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if set(line) == {"-"}:
            continue

        cleaned_lines.append(
            line
        )

    transcript = " ".join(
        cleaned_lines
    )

    return transcript.strip(), path


# =========================================================
# FULL-SERMON SRT HELPERS
# =========================================================

def parse_filename_datetime(path):

    name = os.path.basename(path)

    match = re.search(
        r"(\d{4}-\d{2}-\d{2})[ _](\d{2})-(\d{2})-(\d{2})",
        name,
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
            "%Y-%m-%d %H:%M:%S",
        )

    except ValueError:
        return None


def find_matching_full_sermon_srt(video_path):

    if not os.path.isdir(
        FULL_SERMON_SRT_FOLDER
    ):
        return None

    video_dt = parse_filename_datetime(
        video_path
    )

    candidates = []

    for name in os.listdir(
        FULL_SERMON_SRT_FOLDER
    ):

        if not name.lower().endswith(
            ".srt"
        ):
            continue

        path = os.path.join(
            FULL_SERMON_SRT_FOLDER,
            name,
        )

        srt_dt = parse_filename_datetime(
            path
        )

        if video_dt and srt_dt:

            if srt_dt.date() != video_dt.date():
                continue

            distance = abs(
                (
                    srt_dt - video_dt
                ).total_seconds()
            )

        elif video_dt:

            modified_dt = datetime.fromtimestamp(
                os.path.getmtime(path)
            )

            if modified_dt.date() != video_dt.date():
                continue

            distance = abs(
                (
                    modified_dt - video_dt
                ).total_seconds()
            )

        else:
            # Last-resort fallback if the clip filename
            # does not contain a recognizable timestamp.
            distance = -os.path.getmtime(
                path
            )

        candidates.append(
            (
                distance,
                path,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0]
    )

    return candidates[0][1]


def srt_time_to_seconds(value):

    match = re.match(
        (
            r"(\d+):"
            r"(\d{2}):"
            r"(\d{2})"
            r"[,.]"
            r"(\d{3})"
        ),
        value.strip(),
    )

    if not match:
        return None

    hours = int(
        match.group(1)
    )

    minutes = int(
        match.group(2)
    )

    seconds = int(
        match.group(3)
    )

    milliseconds = int(
        match.group(4)
    )

    return (
        hours * 3600
        + minutes * 60
        + seconds
        + milliseconds / 1000.0
    )


def load_full_sermon_srt(path):

    if not path:
        return []

    try:

        with open(
            path,
            "r",
            encoding="utf-8-sig",
        ) as file:

            contents = file.read()

    except Exception:
        return []

    contents = contents.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    blocks = re.split(
        r"\n\s*\n",
        contents.strip(),
    )

    entries = []

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

        timing = lines[
            time_index
        ].split(
            "-->",
            1,
        )

        if len(timing) != 2:
            continue

        start = srt_time_to_seconds(
            timing[0]
        )

        end = srt_time_to_seconds(
            timing[1].split()[0]
        )

        if (
            start is None
            or end is None
        ):
            continue

        subtitle_text = " ".join(
            lines[
                time_index + 1:
            ]
        )

        subtitle_text = re.sub(
            r"<[^>]+>",
            "",
            subtitle_text,
        )

        subtitle_text = subtitle_text.strip()

        if not subtitle_text:
            continue

        entries.append({
            "start": start,
            "end": end,
            "text": subtitle_text,
        })

    return entries


def find_best_srt_window(
    target_text,
    entries,
):

    if not target_text or not entries:
        return None

    target_normalized = normalize_text(
        target_text
    )

    target_words = (
        target_normalized.split()
    )

    if not target_words:
        return None

    target_length = len(
        target_words
    )

    # Build windows from subtitle entries rather than
    # individual words. This preserves useful surrounding
    # sermon context.
    best = None

    max_entries = min(
        len(entries),
        20,
    )

    for start_index in range(
        len(entries)
    ):

        combined_parts = []

        for end_index in range(
            start_index,
            min(
                len(entries),
                start_index
                + max_entries,
            ),
        ):

            combined_parts.append(
                entries[end_index][
                    "text"
                ]
            )

            candidate_text = " ".join(
                combined_parts
            )

            candidate_normalized = (
                normalize_text(
                    candidate_text
                )
            )

            candidate_length = len(
                candidate_normalized.split()
            )

            if candidate_length < max(
                4,
                int(
                    target_length * 0.55
                ),
            ):
                continue

            similarity = fuzz.ratio(
                target_normalized,
                candidate_normalized,
            )

            if (
                best is None
                or similarity
                > best["similarity"]
            ):

                best = {
                    "similarity":
                        similarity,

                    "start_entry":
                        start_index,

                    "end_entry":
                        end_index,

                    "start":
                        entries[
                            start_index
                        ]["start"],

                    "end":
                        entries[
                            end_index
                        ]["end"],

                    "matched_text":
                        candidate_text,
                }

            # Once the window is substantially longer than
            # the target, additional entries are unlikely
            # to improve the match.
            if candidate_length > int(
                target_length * 1.60
            ):
                break

    return best


def build_full_srt_check(
    video_path,
    target_text,
):

    srt_path = (
        find_matching_full_sermon_srt(
            video_path
        )
    )

    result = {
        "found": False,
        "path": srt_path,
        "similarity": None,
        "matched_text": None,
        "sermon_start": None,
        "sermon_end": None,
        "context_before": None,
        "context_after": None,
        "context_check": "NOT AVAILABLE",
        "beginning_check": "NOT AVAILABLE",
        "ending_check": "NOT AVAILABLE",
    }

    if not srt_path:
        return result

    entries = load_full_sermon_srt(
        srt_path
    )

    if not entries:
        result[
            "context_check"
        ] = "SRT COULD NOT BE PARSED"

        return result

    match = find_best_srt_window(
        target_text,
        entries,
    )

    if match is None:
        result[
            "context_check"
        ] = "NO MATCH"

        return result

    start_entry = match[
        "start_entry"
    ]

    end_entry = match[
        "end_entry"
    ]

    before_start = max(
        0,
        start_entry
        - FULL_SRT_CONTEXT_ENTRIES,
    )

    after_end = min(
        len(entries),
        end_entry
        + FULL_SRT_CONTEXT_ENTRIES
        + 1,
    )

    context_before = " ".join(
        entry["text"]
        for entry in entries[
            before_start:start_entry
        ]
    ).strip()

    context_after = " ".join(
        entry["text"]
        for entry in entries[
            end_entry + 1:after_end
        ]
    ).strip()

    similarity = match[
        "similarity"
    ]

    if similarity >= (
        FULL_SRT_VERIFIED_SIMILARITY
    ):
        context_check = "PASS"

    elif similarity >= (
        FULL_SRT_MINIMUM_SIMILARITY
    ):
        context_check = "REVIEW"

    else:
        context_check = "FAIL"

    # These checks are conservative. They report whether
    # surrounding sermon context exists. They do not alter
    # the clip's timebase or automatically add unrelated
    # SRT timing to the replay.
    beginning_check = (
        "CONTEXT AVAILABLE"
        if context_before
        else "START OF AVAILABLE SRT"
    )

    ending_check = (
        "CONTEXT AVAILABLE"
        if context_after
        else "END OF AVAILABLE SRT"
    )

    result.update({
        "found": True,
        "path": srt_path,
        "similarity": similarity,
        "matched_text":
            match["matched_text"],
        "sermon_start":
            match["start"],
        "sermon_end":
            match["end"],
        "context_before":
            context_before,
        "context_after":
            context_after,
        "context_check":
            context_check,
        "beginning_check":
            beginning_check,
        "ending_check":
            ending_check,
    })

    return result


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text):

    text = text.lower()

    # Normalize apostrophes
    text = (
        text
        .replace("’", "'")
        .replace("‘", "'")
    )

    # Keep letters/numbers/apostrophes
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
# TRANSCRIPTION
# =========================================================

def transcribe_video(
    model,
    video_path
):

    print()
    print(
        "Running quality transcription..."
    )

    segments_generator, info = (
        model.transcribe(
            video_path,
            language="en",
            beam_size=5,
            vad_filter=True,
            word_timestamps=True,
            initial_prompt=(
                WHISPER_INITIAL_PROMPT
            ),
            condition_on_previous_text=True,
        )
    )

    segments = []
    words = []

    for segment in segments_generator:

        segment_record = {
            "start": float(
                segment.start
            ),
            "end": float(
                segment.end
            ),
            "text": (
                segment.text.strip()
            ),
        }

        segments.append(
            segment_record
        )

        if segment.words:

            for word in segment.words:

                word_text = (
                    word.word.strip()
                )

                if not word_text:
                    continue

                probability = getattr(
                    word,
                    "probability",
                    None
                )

                words.append({
                    "word": word_text,
                    "start": float(
                        word.start
                    ),
                    "end": float(
                        word.end
                    ),
                    "probability": (
                        float(probability)
                        if probability
                        is not None
                        else None
                    ),
                    "segment_start":
                        float(
                            segment.start
                        ),
                    "segment_end":
                        float(
                            segment.end
                        ),
                })

    full_text = " ".join(
        segment["text"]
        for segment in segments
    ).strip()

    return (
        full_text,
        segments,
        words,
    )


# =========================================================
# FIND LIVE THOUGHT INSIDE FULL REPLAY
# =========================================================

def find_best_matching_window(
    live_text,
    words
):

    if not words:
        return None

    live_normalized = normalize_text(
        live_text
    )

    live_words = (
        live_normalized.split()
    )

    if not live_words:
        return None

    verified_words = []

    for index, word in enumerate(
        words
    ):

        normalized = normalize_text(
            word["word"]
        )

        if normalized:

            verified_words.append(
                (
                    index,
                    normalized
                )
            )

    if not verified_words:
        return None

    live_length = len(
        live_words
    )

    # Search different lengths because one
    # transcription may have slightly more
    # or fewer words than the other.

    length_ratios = [
        0.75,
        0.85,
        0.95,
        1.00,
        1.05,
        1.15,
        1.25,
    ]

    candidate_lengths = set()

    for ratio in length_ratios:

        length = int(
            live_length * ratio
        )

        if length >= 5:

            candidate_lengths.add(
                length
            )

    best = None

    total_words = len(
        verified_words
    )

    for window_length in (
        candidate_lengths
    ):

        if window_length > total_words:
            continue

        for start_pos in range(
            0,
            total_words
            - window_length
            + 1
        ):

            end_pos = (
                start_pos
                + window_length
            )

            candidate = (
                verified_words[
                    start_pos:end_pos
                ]
            )

            candidate_text = " ".join(
                word
                for _, word
                in candidate
            )

            similarity = fuzz.ratio(
                live_normalized,
                candidate_text
            )

            if (
                best is None
                or similarity
                > best["similarity"]
            ):

                original_start_index = (
                    candidate[0][0]
                )

                original_end_index = (
                    candidate[-1][0]
                )

                best = {
                    "similarity":
                        similarity,

                    "word_start_index":
                        original_start_index,

                    "word_end_index":
                        original_end_index,

                    "matched_text":
                        candidate_text,
                }

    return best


# =========================================================
# CONFIDENCE
# =========================================================

def calculate_confidence(
    words,
    start_index,
    end_index
):

    matched_words = words[
        start_index:
        end_index + 1
    ]

    probabilities = []

    low_confidence_words = []

    for word in matched_words:

        probability = word.get(
            "probability"
        )

        if probability is None:
            continue

        probabilities.append(
            probability
        )

        if probability < 0.60:

            low_confidence_words.append({
                "word":
                    word["word"],

                "probability":
                    round(
                        probability,
                        3
                    ),

                "start":
                    round(
                        word["start"],
                        2
                    ),
            })

    if not probabilities:

        return (
            0.0,
            low_confidence_words
        )

    average = (
        sum(probabilities)
        / len(probabilities)
    )

    return (
        average,
        low_confidence_words
    )


# =========================================================
# TRIM POINTS
# =========================================================

def determine_trim_points(
    words,
    start_index,
    end_index
):

    first_word = words[
        start_index
    ]

    last_word = words[
        end_index
    ]

    # Use Whisper's larger segment boundaries
    # rather than cutting precisely at a word.

    start = (
        first_word[
            "segment_start"
        ]
        - TRIM_PADDING_BEFORE
    )

    end = (
        last_word[
            "segment_end"
        ]
        + TRIM_PADDING_AFTER
    )

    start = max(
        0.0,
        start
    )

    if end <= start:
        end = (
            start + 10.0
        )

    return start, end


# =========================================================
# BUILD FINAL VERIFIED TEXT
# =========================================================

def build_matched_transcript(
    words,
    start_index,
    end_index
):

    matched = words[
        start_index:
        end_index + 1
    ]

    text = " ".join(
        word["word"]
        for word in matched
    )

    # Clean spacing around punctuation
    text = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        text
    )

    return text.strip()


# =========================================================
# CAPTION GROUPING
# =========================================================

def build_caption_groups(
    words,
    start_index,
    end_index,
    trim_start
):

    matched = words[
        start_index:
        end_index + 1
    ]

    captions = []

    current = []

    for word in matched:

        current.append(
            word
        )

        word_text = word[
            "word"
        ].strip()

        punctuation_end = (
            word_text.endswith(".")
            or word_text.endswith("?")
            or word_text.endswith("!")
            or word_text.endswith(",")
        )

        # Aim for short readable caption blocks
        should_finish = False

        if len(current) >= 7:
            should_finish = True

        elif (
            len(current) >= 4
            and punctuation_end
        ):
            should_finish = True

        if should_finish:

            captions.append(
                create_caption_group(
                    current,
                    trim_start
                )
            )

            current = []

    if current:

        captions.append(
            create_caption_group(
                current,
                trim_start
            )
        )

    return captions


def create_caption_group(
    words,
    trim_start
):

    start = max(
        0,
        words[0]["start"]
        - trim_start
    )

    end = max(
        start,
        words[-1]["end"]
        - trim_start
    )

    text = " ".join(
        word["word"]
        for word in words
    )

    text = re.sub(
        r"\s+([,.!?;:])",
        r"\1",
        text
    )

    return {
        "start":
            round(start, 3),

        "end":
            round(end, 3),

        "text":
            text.strip(),
    }


# =========================================================
# SRT HELPERS
# =========================================================

def format_srt_time(
    seconds
):

    milliseconds = int(
        round(seconds * 1000)
    )

    hours = (
        milliseconds
        // 3600000
    )

    milliseconds %= 3600000

    minutes = (
        milliseconds
        // 60000
    )

    milliseconds %= 60000

    secs = (
        milliseconds
        // 1000
    )

    millis = (
        milliseconds
        % 1000
    )

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{secs:02d},"
        f"{millis:03d}"
    )


def write_srt(
    path,
    captions
):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        for index, caption in enumerate(
            captions,
            start=1
        ):

            file.write(
                f"{index}\n"
            )

            file.write(
                f"{format_srt_time(caption['start'])}"
                f" --> "
                f"{format_srt_time(caption['end'])}"
                f"\n"
            )

            file.write(
                caption[
                    "text"
                ]
                + "\n\n"
            )


# =========================================================
# OUTPUT FILES
# =========================================================

def save_results(
    video_path,
    live_transcript_path,
    live_text,
    verified_full_text,
    verified_matched_text,
    words,
    match,
    confidence,
    uncertain_words,
    trim_start,
    trim_end,
    status,
    full_srt_check,
):

    base_name = get_base_name(
        video_path
    )

    if status == "VERIFIED":

        output_folder = (
            VERIFIED_FOLDER
        )

    else:

        output_folder = (
            REVIEW_FOLDER
        )

    metadata_path = os.path.join(
        output_folder,
        base_name + ".json"
    )

    transcript_path = os.path.join(
        output_folder,
        base_name
        + "_verified.txt"
    )

    srt_path = os.path.join(
        output_folder,
        base_name + ".srt"
    )

    captions = build_caption_groups(
        words,
        match[
            "word_start_index"
        ],
        match[
            "word_end_index"
        ],
        trim_start,
    )

    metadata = {

        "status":
            status,

        "processed":
            datetime.now()
            .isoformat(),

        "source_video":
            video_path,

        "live_transcript_file":
            live_transcript_path,

        "similarity":
            round(
                match[
                    "similarity"
                ],
                2
            ),

        "average_word_confidence":
            round(
                confidence,
                4
            ),

        "trim_start":
            round(
                trim_start,
                3
            ),

        "trim_end":
            round(
                trim_end,
                3
            ),

        "final_duration":
            round(
                trim_end
                - trim_start,
                3
            ),

        "live_transcript":
            live_text,

        "verified_matched_transcript":
            verified_matched_text,

        "uncertain_words":
            uncertain_words,

        "captions":
            captions,

        "full_sermon_srt":
            full_srt_check,
    }

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4,
            ensure_ascii=False
        )

    with open(
        transcript_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "SERMON AI "
            "CAPTION VERIFICATION\n"
        )

        file.write(
            "=" * 70
            + "\n\n"
        )

        file.write(
            f"STATUS: {status}\n"
        )

        file.write(
            f"Similarity: "
            f"{match['similarity']:.1f}%\n"
        )

        file.write(
            f"Average word confidence: "
            f"{confidence:.1%}\n"
        )

        file.write(
            f"Trim start: "
            f"{trim_start:.2f}s\n"
        )

        file.write(
            f"Trim end: "
            f"{trim_end:.2f}s\n"
        )

        file.write(
            f"Final duration: "
            f"{trim_end - trim_start:.2f}s\n"
        )

        file.write(
            "\nLIVE TRANSCRIPT\n"
        )

        file.write(
            "-" * 70
            + "\n"
        )

        file.write(
            live_text
            + "\n"
        )

        file.write(
            "\nHIGH-QUALITY TRANSCRIPT\n"
        )

        file.write(
            "-" * 70
            + "\n"
        )

        file.write(
            verified_matched_text
            + "\n"
        )

        file.write(
            "\nFULL-SERMON SRT CROSS-CHECK\n"
        )

        file.write(
            "-" * 70
            + "\n"
        )

        if full_srt_check.get(
            "found"
        ):

            file.write(
                f"File: "
                f"{full_srt_check.get('path')}\n"
            )

            file.write(
                f"Full SRT similarity: "
                f"{full_srt_check.get('similarity', 0):.1f}%\n"
            )

            file.write(
                f"Context check: "
                f"{full_srt_check.get('context_check')}\n"
            )

            file.write(
                f"Beginning check: "
                f"{full_srt_check.get('beginning_check')}\n"
            )

            file.write(
                f"Ending check: "
                f"{full_srt_check.get('ending_check')}\n"
            )

            file.write(
                f"Sermon SRT location: "
                f"{full_srt_check.get('sermon_start', 0):.2f}s"
                f" - "
                f"{full_srt_check.get('sermon_end', 0):.2f}s\n"
            )

            file.write(
                "\nMATCHED WHOLE-SERMON TEXT\n"
            )

            file.write(
                (
                    full_srt_check.get(
                        "matched_text"
                    )
                    or ""
                )
                + "\n"
            )

            file.write(
                "\nCONTEXT BEFORE\n"
            )

            file.write(
                (
                    full_srt_check.get(
                        "context_before"
                    )
                    or "(none)"
                )
                + "\n"
            )

            file.write(
                "\nCONTEXT AFTER\n"
            )

            file.write(
                (
                    full_srt_check.get(
                        "context_after"
                    )
                    or "(none)"
                )
                + "\n"
            )

        else:

            file.write(
                "No matching full-sermon SRT found.\n"
            )

        file.write(
            "\nUNCERTAIN WORDS\n"
        )

        file.write(
            "-" * 70
            + "\n"
        )

        if uncertain_words:

            for word in uncertain_words:

                file.write(
                    f"{word['start']:7.2f}s  "
                    f"{word['word']}  "
                    f"confidence="
                    f"{word['probability']:.1%}"
                    f"\n"
                )

        else:

            file.write(
                "None detected.\n"
            )

    write_srt(
        srt_path,
        captions
    )

    return (
        metadata_path,
        transcript_path,
        srt_path,
    )


# =========================================================
# CLASSIFICATION
# =========================================================

def determine_status(
    similarity,
    confidence,
    full_srt_check,
):

    base_verified = (
        similarity
        >= VERIFIED_SIMILARITY
        and confidence
        >= VERIFIED_CONFIDENCE
    )

    if not base_verified:
        return "REVIEW"

    # The full-sermon SRT is an extra safety layer.
    # If none exists, preserve the existing Small + Medium
    # behavior. If one exists and matches poorly, require
    # manual review rather than auto-rendering.
    if full_srt_check.get(
        "found"
    ):

        full_similarity = (
            full_srt_check.get(
                "similarity"
            )
        )

        if (
            full_similarity is None
            or full_similarity
            < FULL_SRT_VERIFIED_SIMILARITY
        ):
            return "REVIEW"

    return "VERIFIED"


# =========================================================
# PROCESS ONE VIDEO
# =========================================================

def process_video(
    model,
    video_path
):

    base_name = get_base_name(
        video_path
    )

    print()
    print("=" * 70)

    print(
        f"PROCESSING:"
    )

    print(
        os.path.basename(
            video_path
        )
    )

    print("=" * 70)

    live_text, live_path = (
        load_live_transcript(
            base_name
        )
    )

    if not live_text:

        print()
        print(
            "No matching live "
            "transcript found."
        )

        print(
            "Sending to REVIEW."
        )

        # We still transcribe it so
        # there's useful information.
        full_text, segments, words = (
            transcribe_video(
                model,
                video_path
            )
        )

        review_path = os.path.join(
            REVIEW_FOLDER,
            base_name
            + "_no_live_transcript.txt"
        )

        with open(
            review_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                full_text
            )

        # Marker so it isn't repeatedly
        # processed.
        marker = os.path.join(
            REVIEW_FOLDER,
            base_name + ".json"
        )

        with open(
            marker,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "status":
                        "REVIEW",

                    "reason":
                        "No live transcript",
                },
                file,
                indent=4
            )

        return

    print()
    print("Live candidate transcript:")
    print()
    print(live_text)

    (
        verified_full_text,
        segments,
        words,
    ) = transcribe_video(
        model,
        video_path
    )

    print()
    print(
        f"High-quality transcript "
        f"contains {len(words)} words."
    )

    match = find_best_matching_window(
        live_text,
        words
    )

    if match is None:

        print()
        print(
            "Could not align live "
            "transcript with replay."
        )

        return

    start_index = (
        match[
            "word_start_index"
        ]
    )

    end_index = (
        match[
            "word_end_index"
        ]
    )

    confidence, uncertain_words = (
        calculate_confidence(
            words,
            start_index,
            end_index,
        )
    )

    trim_start, trim_end = (
        determine_trim_points(
            words,
            start_index,
            end_index,
        )
    )

    matched_text = (
        build_matched_transcript(
            words,
            start_index,
            end_index,
        )
    )

    full_srt_check = (
        build_full_srt_check(
            video_path,
            matched_text,
        )
    )

    print()
    print("Full-sermon SRT cross-check:")

    if full_srt_check.get(
        "found"
    ):

        print(
            f"  File: "
            f"{os.path.basename(full_srt_check['path'])}"
        )

        print(
            f"  Similarity: "
            f"{full_srt_check['similarity']:.1f}%"
        )

        print(
            f"  Context: "
            f"{full_srt_check['context_check']}"
        )

        print(
            f"  Sermon time: "
            f"{full_srt_check['sermon_start']:.2f}s"
            f" - "
            f"{full_srt_check['sermon_end']:.2f}s"
        )

    else:

        print(
            "  No matching full-sermon SRT found."
        )

    status = determine_status(
        match["similarity"],
        confidence,
        full_srt_check,
    )

    print()
    print("-" * 70)

    print(
        f"Similarity: "
        f"{match['similarity']:.1f}%"
    )

    print(
        f"Average word confidence: "
        f"{confidence:.1%}"
    )

    print(
        f"Suggested trim:"
    )

    print(
        f"  START = "
        f"{trim_start:.2f}s"
    )

    print(
        f"  END   = "
        f"{trim_end:.2f}s"
    )

    print(
        f"  LENGTH = "
        f"{trim_end - trim_start:.2f}s"
    )

    print()

    print(
        "High-quality matched text:"
    )

    print()
    print(
        matched_text
    )

    print()

    print(
        f"STATUS: {status}"
    )

    (
        metadata_path,
        transcript_path,
        srt_path,
    ) = save_results(
        video_path,
        live_path,
        live_text,
        verified_full_text,
        matched_text,
        words,
        match,
        confidence,
        uncertain_words,
        trim_start,
        trim_end,
        status,
        full_srt_check,
    )

    print()
    print(
        "Verification report:"
    )

    print(
        transcript_path
    )

    print()
    print(
        "Metadata:"
    )

    print(
        metadata_path
    )

    print()
    print(
        "Caption file:"
    )

    print(
        srt_path
    )


# =========================================================
# PROCESS EVERYTHING
# =========================================================

def process_available_clips(
    model
):

    videos = get_video_files()

    new_videos = []

    for video in videos:

        base_name = get_base_name(
            video
        )

        if not already_processed(
            base_name
        ):
            new_videos.append(
                video
            )

    if not new_videos:

        print(
            "No new AI sermon clips "
            "to process."
        )

        return 0

    print(
        f"Found "
        f"{len(new_videos)} "
        f"new clip(s)."
    )

    for video in new_videos:

        try:

            process_video(
                model,
                video
            )

        except KeyboardInterrupt:
            raise

        except Exception as error:

            print()
            print(
                "ERROR processing:"
            )

            print(video)

            print(error)

            print()

    return len(new_videos)


# =========================================================
# MAIN
# =========================================================

def main():

    ensure_folders()

    print()
    print("=" * 70)
    print(
        "SERMON AI - "
        "SHORTS PROCESSOR"
    )
    print("=" * 70)

    print()
    print(
        "Loading quality-control "
        "Whisper model..."
    )

    print(
        f"Model: {VERIFY_MODEL}"
    )

    model = WhisperModel(
        VERIFY_MODEL,
        device=VERIFY_DEVICE,
        compute_type=(
            VERIFY_COMPUTE_TYPE
        ),
    )

    print(
        "Quality model loaded."
    )

    print()

    if not WATCH_MODE:

        process_available_clips(
            model
        )

        print()
        print(
            "Processing complete."
        )

        return

    print(
        "Watch mode enabled."
    )

    print(
        "Waiting for new raw clips."
    )

    print(
        "Press Ctrl+C to stop."
    )

    try:

        while True:

            process_available_clips(
                model
            )

            time.sleep(
                WATCH_INTERVAL_SECONDS
            )

    except KeyboardInterrupt:

        print()
        print(
            "Shorts processor stopped."
        )


if __name__ == "__main__":
    main()