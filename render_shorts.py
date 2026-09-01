import os
import json
import subprocess
from pathlib import Path


# =========================================================
# SETTINGS
# =========================================================

SHORTS_ROOT = Path(
    r"D:\2026\shorts\ai shorts"
)

RAW_FOLDER = SHORTS_ROOT / "Raw"
VERIFIED_FOLDER = SHORTS_ROOT / "Verified"
READY_FOLDER = SHORTS_ROOT / "Ready"

# Final YouTube Short resolution
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920

# Encoding
VIDEO_CODEC = "h264_nvenc"

# RTX 2070 NVENC quality setting
NVENC_PRESET = "p5"

# CQ: lower = better quality / larger file
CQ = "20"

AUDIO_BITRATE = "192k"


# =========================================================
# CAPTION STYLE
# =========================================================

# ASS subtitle styling used by FFmpeg.
#
# FontSize is deliberately large because we're producing
# a 1080x1920 vertical video.
#
# MarginV keeps captions above the very bottom of the Short
# so YouTube's UI doesn't cover them.

CAPTION_STYLE = (
    "FontName=Arial,"
    "FontSize=24,"
    "Bold=1,"
    "PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,"
    "BackColour=&H80000000,"
    "BorderStyle=1,"
    "Outline=3,"
    "Shadow=1,"
    "Alignment=2,"
    "MarginL=90,"
    "MarginR=90,"
    "MarginV=300"
)


# =========================================================
# HELPERS
# =========================================================

def ensure_folders():

    READY_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )


def find_raw_video(base_name):

    extensions = [
        ".mp4",
        ".mkv",
        ".mov",
        ".m4v",
        ".ts",
    ]

    for extension in extensions:

        path = RAW_FOLDER / (
            base_name + extension
        )

        if path.exists():
            return path

    return None


def already_rendered(base_name):

    output = READY_FOLDER / (
        base_name + "_SHORT.mp4"
    )

    return output.exists()


def escape_subtitle_path(path):

    # FFmpeg's subtitles filter needs Windows paths
    # escaped carefully.

    text = str(
        path.resolve()
    )

    text = text.replace(
        "\\",
        "/"
    )

    text = text.replace(
        ":",
        "\\:"
    )

    text = text.replace(
        "'",
        "\\'"
    )

    return text


# =========================================================
# LOAD VERIFIED CLIPS
# =========================================================

def get_verified_jobs():

    jobs = []

    if not VERIFIED_FOLDER.exists():

        return jobs

    for json_path in sorted(
        VERIFIED_FOLDER.glob("*.json")
    ):

        try:

            with open(
                json_path,
                "r",
                encoding="utf-8"
            ) as file:

                metadata = json.load(
                    file
                )

        except Exception as error:

            print(
                f"Could not read "
                f"{json_path.name}: "
                f"{error}"
            )

            continue

        if (
            metadata.get("status")
            !=
            "VERIFIED"
        ):

            continue

        base_name = (
            json_path.stem
        )

        if already_rendered(
            base_name
        ):

            continue

        raw_video = find_raw_video(
            base_name
        )

        if raw_video is None:

            print()
            print(
                "Raw video not found:"
            )

            print(
                base_name
            )

            continue

        srt_path = (
            VERIFIED_FOLDER
            /
            (base_name + ".srt")
        )

        if not srt_path.exists():

            print()
            print(
                "SRT not found:"
            )

            print(
                srt_path
            )

            continue

        trim_start = metadata.get(
            "trim_start"
        )

        trim_end = metadata.get(
            "trim_end"
        )

        if (
            trim_start is None
            or
            trim_end is None
        ):

            print()
            print(
                "Trim information missing:"
            )

            print(
                json_path
            )

            continue

        try:

            trim_start = float(
                trim_start
            )

            trim_end = float(
                trim_end
            )

        except (TypeError, ValueError):

            print(
                "Invalid trim values:"
            )

            print(
                json_path
            )

            continue

        if trim_end <= trim_start:

            print(
                "Invalid trim range:"
            )

            print(
                json_path
            )

            continue

        jobs.append({
            "base_name":
                base_name,

            "raw_video":
                raw_video,

            "srt":
                srt_path,

            "json":
                json_path,

            "trim_start":
                trim_start,

            "trim_end":
                trim_end,
        })

    return jobs


# =========================================================
# BUILD VERTICAL VIDEO
# =========================================================

def render_job(job):

    base_name = job[
        "base_name"
    ]

    raw_video = job[
        "raw_video"
    ]

    srt_path = job[
        "srt"
    ]

    trim_start = job[
        "trim_start"
    ]

    trim_end = job[
        "trim_end"
    ]

    duration = (
        trim_end
        -
        trim_start
    )

    output_path = (
        READY_FOLDER
        /
        (
            base_name
            +
            "_SHORT.mp4"
        )
    )

    escaped_srt = (
        escape_subtitle_path(
            srt_path
        )
    )

    print()
    print("=" * 70)
    print("RENDERING SHORT")
    print("=" * 70)

    print()
    print(
        f"Source: "
        f"{raw_video.name}"
    )

    print(
        f"Start: "
        f"{trim_start:.2f}s"
    )

    print(
        f"End: "
        f"{trim_end:.2f}s"
    )

    print(
        f"Duration: "
        f"{duration:.2f}s"
    )

    print()

    # -----------------------------------------------------
    # FILTER DESIGN
    # -----------------------------------------------------
    #
    # Input video
    #       ↓
    # split
    #   ↙       ↘
    # blurred    normal
    # vertical   scaled
    # background foreground
    #   ↘       ↙
    #    overlay
    #       ↓
    # subtitles
    #
    # This keeps the COMPLETE original sermon frame visible.
    # Nothing important is automatically cropped away.

    filter_complex = (
        "[0:v]"
        "split=2"
        "[bg][fg];"

        # -----------------------------------------------
        # BACKGROUND
        # -----------------------------------------------

        "[bg]"
        f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        f"crop={OUTPUT_WIDTH}:{OUTPUT_HEIGHT},"
        "gblur=sigma=35"
        "[background];"

        # -----------------------------------------------
        # FOREGROUND
        # -----------------------------------------------

        "[fg]"
        f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
        "force_original_aspect_ratio=decrease"
        "[foreground];"

        # -----------------------------------------------
        # CENTER ORIGINAL VIDEO
        # -----------------------------------------------

        "[background][foreground]"
        "overlay="
        "(W-w)/2:"
        "(H-h)/2"
        "[vertical];"

        # -----------------------------------------------
        # CAPTIONS
        # -----------------------------------------------

        "[vertical]"
        f"subtitles='{escaped_srt}':"
        f"force_style='{CAPTION_STYLE}'"
        "[final]"
    )

    command = [
        "ffmpeg",

        "-y",

        # Seek before decoding.
        "-ss",
        f"{trim_start:.3f}",

        "-i",
        str(raw_video),

        "-t",
        f"{duration:.3f}",

        "-filter_complex",
        filter_complex,

        "-map",
        "[final]",

        "-map",
        "0:a?",

        # -----------------------------------------------
        # RTX 2070 NVENC
        # -----------------------------------------------

        "-c:v",
        VIDEO_CODEC,

        "-preset",
        NVENC_PRESET,

        "-rc",
        "vbr",

        "-cq",
        CQ,

        "-b:v",
        "0",

        # YouTube-friendly pixel format
        "-pix_fmt",
        "yuv420p",

        # -----------------------------------------------
        # AUDIO
        # -----------------------------------------------

        "-c:a",
        "aac",

        "-b:a",
        AUDIO_BITRATE,

        "-ar",
        "48000",

        # -----------------------------------------------
        # MP4
        # -----------------------------------------------

        "-movflags",
        "+faststart",

        str(
            output_path
        ),
    ]

    print(
        "Starting FFmpeg..."
    )

    print()

    result = subprocess.run(
        command
    )

    if result.returncode != 0:

        print()
        print(
            "ERROR: FFmpeg failed."
        )

        return False

    if not output_path.exists():

        print()
        print(
            "ERROR: Output video "
            "was not created."
        )

        return False

    size_mb = (
        output_path.stat().st_size
        /
        1024
        /
        1024
    )

    print()
    print(
        "SHORT COMPLETE"
    )

    print(
        output_path
    )

    print(
        f"File size: "
        f"{size_mb:.1f} MB"
    )

    return True


# =========================================================
# MAIN
# =========================================================

def main():

    ensure_folders()

    print()
    print("=" * 70)
    print(
        "SERMON AI - "
        "SHORT RENDERER"
    )
    print("=" * 70)

    jobs = get_verified_jobs()

    if not jobs:

        print()
        print(
            "No new VERIFIED clips "
            "need rendering."
        )

        return

    print()
    print(
        f"Found "
        f"{len(jobs)} "
        f"Short(s) to render."
    )

    completed = 0
    failed = 0

    for job in jobs:

        try:

            success = render_job(
                job
            )

            if success:
                completed += 1

            else:
                failed += 1

        except KeyboardInterrupt:

            print()
            print(
                "Rendering stopped."
            )

            return

        except Exception as error:

            failed += 1

            print()
            print(
                "ERROR rendering:"
            )

            print(
                job["base_name"]
            )

            print(
                error
            )

    print()
    print("=" * 70)

    print(
        f"Finished: "
        f"{completed} rendered, "
        f"{failed} failed."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()