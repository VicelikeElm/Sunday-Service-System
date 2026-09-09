import os
import sys
import gc
import re
import time
import wave
import shutil
import tempfile
import subprocess
import logging
import threading
import queue
from datetime import datetime

import pyaudiowpatch as pyaudio
import obsws_python as obs

from dotenv import load_dotenv
from faster_whisper import WhisperModel

import socket


# =========================================================
# QUIET LIBRARY LOGGING
# =========================================================

# Prevent OBS connection attempts from filling the log with
# harmless tracebacks while OBS is not running.
logging.getLogger("obsws_python").setLevel(logging.CRITICAL)
logging.getLogger("websocket").setLevel(logging.CRITICAL)


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

OBS_HOST = os.getenv("OBS_HOST", "localhost")
OBS_PORT = int(os.getenv("OBS_PORT", "4455"))
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")


# =========================================================
# PATHS
# =========================================================

BASE_FOLDER = r"C:\Church\SermonAI"

SHORTS_ROOT = r"D:\2026\shorts\ai shorts"

RAW_FOLDER = os.path.join(
    SHORTS_ROOT,
    "Raw"
)

TRANSCRIPT_FOLDER = os.path.join(
    SHORTS_ROOT,
    "Transcripts"
)

PREPARE_SERMON_SCRIPT = os.path.join(
    BASE_FOLDER,
    "prepare_sermon.py"
)

# This must match the folder OBS itself initially writes
# Replay Buffer recordings into.
OBS_REPLAY_FOLDER = r"D:\2026"

PROCESS_SHORTS_SCRIPT = os.path.join(
    BASE_FOLDER,
    "process_shorts.py"
)

RENDER_SHORTS_SCRIPT = os.path.join(
    BASE_FOLDER,
    "render_shorts.py"
)


# =========================================================
# AUDIO
# =========================================================

# Instead of assuming device 44 forever, search for this
# loopback device every time Sermon AI starts.
AUDIO_DEVICE_NAME = (
    "Headphones (High Definition Audio Device) [Loopback]"
)

# If device-name matching ever fails, this is only a fallback.
AUDIO_DEVICE_FALLBACK = 44


# =========================================================
# LIVE WHISPER
# =========================================================

WHISPER_MODEL = "small"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"

CHUNK_SECONDS = 6


# =========================================================
# THOUGHT DETECTION
# =========================================================

MIN_THOUGHT_SECONDS = 24
TARGET_THOUGHT_SECONDS = 35
MAX_THOUGHT_SECONDS = 65

SILENCE_CHUNKS_TO_FINISH = 1


# =========================================================
# CLIP SCORING
# =========================================================

POSSIBLE_THRESHOLD = 55
SAVE_THRESHOLD = 70

MIN_SECONDS_BETWEEN_SAVES = 75

SAVE_DELAY_SECONDS = 5


# =========================================================
# CONTROLLER TIMING
# =========================================================

OBS_SEARCH_INTERVAL = 5

# After all OBS output activity ends, wait this long before
# loading Medium Whisper and processing Shorts.
POST_SERVICE_DELAY = 90

# How frequently to check whether OBS becomes active again.
IDLE_CHECK_INTERVAL = 2

# How long to wait for OBS to finish creating a replay file.
REPLAY_FILE_WAIT_SECONDS = 20


# =========================================================
# SERMON LANGUAGE
# =========================================================

STRONG_PHRASES = [
    "the point is",
    "here's the point",
    "here is the point",
    "listen to this",
    "listen carefully",
    "understand this",
    "don't miss this",
    "do not miss this",
    "remember this",
    "we need to understand",
    "what this means",
    "this means",
    "the truth is",
    "the reality is",
    "the gospel",
    "god's grace",
    "god's mercy",
    "god's word",
    "the word of god",
    "scripture tells us",
    "the bible tells us",
    "christian life",
    "as christians",
    "we are called",
    "you are called",
    "we must",
    "you must",
    "we cannot",
    "you cannot",
    "the question is",
    "ask yourself",
    "think about this",
    "what will you do",
    "what are you going to do",
]

APPLICATION_PHRASES = [
    "in your life",
    "in our lives",
    "for us today",
    "for you today",
    "this week",
    "when you leave here",
    "when we leave here",
    "how do we",
    "how should we",
    "what should we",
    "we ought to",
    "we should",
    "you should",
    "we need to",
    "you need to",
    "apply this",
    "application",
]

SCRIPTURE_PHRASES = [
    "the text says",
    "the passage says",
    "scripture says",
    "the bible says",
    "verse",
    "chapter",
    "matthew",
    "mark",
    "luke",
    "john",
    "acts",
    "romans",
    "corinthians",
    "galatians",
    "ephesians",
    "philippians",
    "colossians",
    "thessalonians",
    "timothy",
    "titus",
    "hebrews",
    "james",
    "peter",
    "jude",
    "revelation",
    "psalm",
    "proverbs",
    "genesis",
    "exodus",
    "isaiah",
    "jeremiah",
]

ADMIN_PHRASES = [
    "good morning",
    "welcome",
    "announcement",
    "announcements",
    "bulletin",
    "offering",
    "silence your phone",
    "turn your phone",
    "let's stand",
    "let us stand",
]

PRAYER_START_PHRASES = [
    "let us pray",
    "let's pray",
    "lets pray",
    "bow your heads",
    "bow our heads",
    "go to prayer",
    "go to the lord in prayer",
]


# =========================================================
# SIMPLE OUTPUT
# =========================================================

def log(message=""):
    print(message, flush=True)


# =========================================================
# FOLDERS
# =========================================================

def ensure_folders():

    os.makedirs(
        RAW_FOLDER,
        exist_ok=True
    )

    os.makedirs(
        TRANSCRIPT_FOLDER,
        exist_ok=True
    )


# =========================================================
# AUDIO DEVICE DISCOVERY
# =========================================================

def find_loopback_device(audio):

    exact_matches = []
    partial_matches = []

    for index in range(
        audio.get_device_count()
    ):

        info = (
            audio.get_device_info_by_index(
                index
            )
        )

        name = info.get(
            "name",
            ""
        )

        if name == AUDIO_DEVICE_NAME:
            exact_matches.append(index)

        elif (
            "Headphones"
            in name
            and
            "High Definition Audio Device"
            in name
            and
            "Loopback"
            in name
        ):
            partial_matches.append(index)

    if exact_matches:

        return exact_matches[0]

    if partial_matches:

        return partial_matches[0]

    # Last resort
    try:

        info = (
            audio.get_device_info_by_index(
                AUDIO_DEVICE_FALLBACK
            )
        )

        if (
            info.get(
                "maxInputChannels",
                0
            )
            > 0
        ):

            return AUDIO_DEVICE_FALLBACK

    except Exception:
        pass

    raise RuntimeError(
        "Could not find the OBS monitor "
        "Headphones loopback device."
    )


def open_loopback_stream():
    """
    Creates a fresh PyAudio instance + loopback stream. Used both at
    startup and to recover after the audio stream stalls out.
    """

    audio = pyaudio.PyAudio()

    device_index = find_loopback_device(audio)

    device_info = audio.get_device_info_by_index(
        device_index
    )

    rate = int(
        device_info["defaultSampleRate"]
    )

    channels = int(
        device_info["maxInputChannels"]
    )

    stream = audio.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=1024,
    )

    return audio, stream, device_index, rate, channels


def read_stream_chunk(
    stream,
    frame_count,
    timeout_seconds=15.0
):
    """
    stream.read() is a blocking native (WASAPI) call. If the underlying
    Windows Audio session dies mid-service -- observed 2026-08-30, when
    a crash in Elgato's audio routing server (ElgatoAudioControlServer
    .exe / WindowsAudioRouterApi.dll) took down the whole Windows Audio
    service -- the call never returns and never raises. It just hangs
    forever, silently ending live clip detection for the rest of the
    service. Run the read on a background thread and time it out
    instead of blocking the live loop indefinitely.
    """

    result = queue.Queue(
        maxsize=1
    )

    def _read():

        try:
            result.put(
                (
                    "ok",
                    stream.read(
                        frame_count,
                        exception_on_overflow=False,
                    ),
                )
            )

        except Exception as error:
            result.put(
                (
                    "error",
                    error
                )
            )

    threading.Thread(
        target=_read,
        daemon=True
    ).start()

    try:
        status, payload = result.get(
            timeout=timeout_seconds
        )

    except queue.Empty:
        raise TimeoutError(
            "Audio stream stalled (no data for "
            f"{timeout_seconds:.0f}s) -- Windows Audio may "
            "have restarted underneath the capture stream."
        )

    if status == "error":
        raise payload

    return payload


# =========================================================
# OBS CONNECTION
# =========================================================

def obs_port_is_open():

    try:

        with socket.create_connection(
            (OBS_HOST, OBS_PORT),
            timeout=1
        ):
            return True

    except OSError:
        return False


def try_connect_obs():

    # Don't even invoke obsws-python until
    # something is actually listening on 4455.
    if not obs_port_is_open():
        return None

    try:

        # OBS can open the WebSocket port while
        # the rest of OBS is still initializing.
        client = obs.ReqClient(
            host=OBS_HOST,
            port=OBS_PORT,
            password=OBS_PASSWORD,
            timeout=3,
        )

        client.get_version()

        return client

    except Exception:

        # OBS exists but isn't quite ready yet.
        return None


def wait_for_obs():

    log("Waiting for OBS...")

    while True:

        client = try_connect_obs()

        if client is not None:

            log("OBS is ready.")
            log("OBS WebSocket connected.")

            return client

        time.sleep(
            OBS_SEARCH_INTERVAL
        )


# =========================================================
# OBS OUTPUT STATUS
# =========================================================

def read_obs_status(client):

    try:

        stream_status = (
            client.get_stream_status()
        )

        record_status = (
            client.get_record_status()
        )

        replay_status = (
            client.get_replay_buffer_status()
        )

        streaming = bool(
            getattr(
                stream_status,
                "output_active",
                False
            )
        )

        recording = bool(
            getattr(
                record_status,
                "output_active",
                False
            )
        )

        replay = bool(
            getattr(
                replay_status,
                "output_active",
                False
            )
        )

        return {
            "connected": True,
            "streaming": streaming,
            "recording": recording,
            "replay": replay,
        }

    except Exception:

        return {
            "connected": False,
            "streaming": False,
            "recording": False,
            "replay": False,
        }


def obs_has_activity(status):

    return (
        status["streaming"]
        or status["recording"]
        or status["replay"]
    )


def main_service_running(status):

    return (
        status["streaming"]
        or status["recording"]
    )


# =========================================================
# WAIT FOR SERVICE ACTIVITY
# =========================================================

def wait_for_service_activity():

    client = None

    while True:

        if client is None:

            client = wait_for_obs()

            log()
            log(
                "Waiting for OBS recording, "
                "streaming, or Replay Buffer..."
            )

        status = read_obs_status(
            client
        )

        if not status["connected"]:

            log("OBS closed.")
            client = None

            time.sleep(
                OBS_SEARCH_INTERVAL
            )

            continue

        if obs_has_activity(status):

            log()
            log("OBS activity detected.")

            if status["streaming"]:
                log("  Streaming: ON")

            if status["recording"]:
                log("  Recording: ON")

            if status["replay"]:
                log("  Replay Buffer: ON")

            return client, status

        time.sleep(2)


# =========================================================
# REPLAY BUFFER CONTROL
# =========================================================

def ensure_replay_buffer(
    client,
    status
):

    # Replay already running.
    if status["replay"]:

        return False

    # If recording/streaming begins, automatically
    # enable Replay Buffer for AI clipping.
    if main_service_running(status):

        try:

            log(
                "Starting Replay Buffer "
                "for Sermon AI..."
            )

            client.start_replay_buffer()

            time.sleep(2)

            return True

        except Exception as error:

            log(
                "WARNING: Could not start "
                "Replay Buffer."
            )

            log(str(error))

    return False


def stop_auto_replay(
    client,
    auto_started
):

    if not auto_started:
        return

    try:

        status = read_obs_status(
            client
        )

        if (
            status["connected"]
            and status["replay"]
        ):

            log(
                "Stopping Sermon AI's "
                "Replay Buffer..."
            )

            client.stop_replay_buffer()

            time.sleep(1)

    except Exception:
        pass


# =========================================================
# REPLAY FILE HELPERS
# =========================================================

def get_media_files(folder):

    if not os.path.exists(folder):

        return []

    extensions = (
        ".mp4",
        ".mkv",
        ".mov",
        ".ts",
        ".m4v",
    )

    results = []

    for name in os.listdir(folder):

        path = os.path.join(
            folder,
            name
        )

        if (
            os.path.isfile(path)
            and
            name.lower().endswith(
                extensions
            )
        ):

            results.append(path)

    return results


def snapshot_replay_files():

    return set(
        get_media_files(
            OBS_REPLAY_FOLDER
        )
    )


def wait_for_new_replay(
    before_files
):

    deadline = (
        time.time()
        +
        REPLAY_FILE_WAIT_SECONDS
    )

    while time.time() < deadline:

        time.sleep(0.5)

        after_files = set(
            get_media_files(
                OBS_REPLAY_FOLDER
            )
        )

        new_files = list(
            after_files
            -
            before_files
        )

        if not new_files:
            continue

        newest = max(
            new_files,
            key=os.path.getmtime
        )

        previous_size = -1
        stable_checks = 0

        for _ in range(40):

            try:

                size = os.path.getsize(
                    newest
                )

            except OSError:

                time.sleep(0.5)
                continue

            if (
                size == previous_size
                and
                size > 0
            ):

                stable_checks += 1

            else:

                stable_checks = 0

            if stable_checks >= 2:

                return newest

            previous_size = size

            time.sleep(0.5)

        return newest

    return None


# =========================================================
# CLIP FILES
# =========================================================

def move_replay(
    source_path,
    clip_number,
    score
):

    extension = os.path.splitext(
        source_path
    )[1]

    stamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    filename = (
        f"{stamp}_AI_Clip_"
        f"{clip_number:02d}"
        f"_Score_{score}"
        f"{extension}"
    )

    destination = os.path.join(
        RAW_FOLDER,
        filename
    )

    shutil.move(
        source_path,
        destination
    )

    return destination


def save_candidate_transcript(
    clip_path,
    score,
    text,
    reasons,
    duration
):

    base_name = os.path.splitext(
        os.path.basename(
            clip_path
        )
    )[0]

    destination = os.path.join(
        TRANSCRIPT_FOLDER,
        base_name + ".txt"
    )

    with open(
        destination,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "SERMON AI CANDIDATE\n"
        )

        file.write(
            "=" * 70 + "\n\n"
        )

        file.write(
            f"Created: "
            f"{datetime.now()}\n"
        )

        file.write(
            f"Score: {score}\n"
        )

        file.write(
            f"Thought duration: "
            f"{duration:.1f} seconds\n"
        )

        file.write(
            f"Raw replay: "
            f"{clip_path}\n"
        )

        file.write(
            "\nReasons:\n"
        )

        for reason in reasons:

            file.write(
                f"- {reason}\n"
            )

        file.write(
            "\nLIVE WHISPER TRANSCRIPT\n"
        )

        file.write(
            "-" * 70 + "\n"
        )

        file.write(text.strip())

        file.write("\n")

    return destination


# =========================================================
# TEXT HELPERS
# =========================================================

def contains_any(
    text,
    phrases
):

    lower = text.lower()

    return any(
        phrase in lower
        for phrase in phrases
    )


def count_phrase_hits(
    text,
    phrases
):

    lower = text.lower()

    return sum(
        1
        for phrase in phrases
        if phrase in lower
    )


# =========================================================
# PRAYER DETECTION
# =========================================================

def update_prayer_state(
    text,
    in_prayer
):

    lower = text.lower()

    if not in_prayer:

        if contains_any(
            lower,
            PRAYER_START_PHRASES
        ):

            log()
            log(
                "*** PRAYER DETECTED "
                "- clipping paused ***"
            )

            return True

        return False

    # Once we're in prayer, a final Amen is a reasonable
    # signal to resume clipping.
    if re.search(
        r"\bamen\b",
        lower
    ):

        log()
        log(
            "*** PRAYER ENDED "
            "- clipping resumed ***"
        )

        return False

    return True


# =========================================================
# THOUGHT DETECTION
# =========================================================

def ends_like_sentence(text):

    text = text.strip()

    if not text:
        return False

    return text.endswith(
        (".", "!", "?")
    )


def should_finish_thought(
    duration,
    latest_text,
    silence_chunks
):

    if (
        duration
        >= MIN_THOUGHT_SECONDS
        and
        silence_chunks
        >= SILENCE_CHUNKS_TO_FINISH
    ):

        return True

    if (
        duration
        >= TARGET_THOUGHT_SECONDS
        and
        ends_like_sentence(
            latest_text
        )
    ):

        return True

    if duration >= MAX_THOUGHT_SECONDS:

        return True

    return False


# =========================================================
# SERMON SCORING
# =========================================================

def score_sermon_moment(
    text,
    duration
):

    clean = text.strip()

    if not clean:

        return 0, []

    lower = clean.lower()

    word_count = len(
        clean.split()
    )

    score = 0
    reasons = []

    # Duration
    if 30 <= duration <= 55:

        score += 20

        reasons.append(
            "excellent clip duration"
        )

    elif 24 <= duration <= 65:

        score += 14

        reasons.append(
            "usable clip duration"
        )

    # Speech amount
    if 65 <= word_count <= 160:

        score += 15

        reasons.append(
            "good amount of speech"
        )

    elif 40 <= word_count < 65:

        score += 8

    # Complete ending
    if clean.endswith(
        (".", "!", "?")
    ):

        score += 8

        reasons.append(
            "complete ending"
        )

    # Strong sermon language
    hits = count_phrase_hits(
        clean,
        STRONG_PHRASES
    )

    if hits:

        score += min(
            hits * 7,
            21
        )

        reasons.append(
            f"{hits} strong sermon phrase(s)"
        )

    # Application
    hits = count_phrase_hits(
        clean,
        APPLICATION_PHRASES
    )

    if hits:

        score += min(
            hits * 7,
            18
        )

        reasons.append(
            f"{hits} application phrase(s)"
        )

    # Scripture
    hits = count_phrase_hits(
        clean,
        SCRIPTURE_PHRASES
    )

    if hits:

        score += min(
            hits * 4,
            12
        )

        reasons.append(
            "Scripture connection"
        )

    # Structure
    if "?" in clean:

        score += 5

        reasons.append(
            "rhetorical question"
        )

    if "!" in clean:

        score += 3

    if "therefore" in lower:

        score += 6

        reasons.append(
            "conclusion"
        )

    if "because" in lower:

        score += 4

    if (
        "but" in lower
        and
        "because" in lower
    ):

        score += 4

    if "so that" in lower:

        score += 4

    contrast_words = [
        "but",
        "yet",
        "instead",
        "however",
        "rather",
    ]

    contrast_hits = sum(
        1
        for word in contrast_words
        if
        f" {word} "
        in
        f" {lower} "
    )

    if contrast_hits >= 2:

        score += 5

        reasons.append(
            "strong contrast"
        )

    # Administrative material
    admin_hits = count_phrase_hits(
        clean,
        ADMIN_PHRASES
    )

    if admin_hits:

        penalty = min(
            admin_hits * 25,
            60
        )

        score -= penalty

        reasons.append(
            f"-{penalty} admin"
        )

    if word_count < 35:

        score -= 20

        reasons.append(
            "too little context"
        )

    score = max(
        0,
        min(
            score,
            100
        )
    )

    return score, reasons


# =========================================================
# SAVE REPLAY
# =========================================================

def save_obs_replay(
    client
):

    status = read_obs_status(
        client
    )

    if (
        not status["connected"]
        or
        not status["replay"]
    ):

        log(
            "Replay Buffer is not running. "
            "Cannot save this candidate."
        )

        return client, None

    before_files = (
        snapshot_replay_files()
    )

    try:

        client.save_replay_buffer()

    except Exception:

        log(
            "OBS connection was lost "
            "while saving."
        )

        return None, None

    replay_path = (
        wait_for_new_replay(
            before_files
        )
    )

    return client, replay_path


# =========================================================
# LIVE SERMON SESSION
# =========================================================

def run_live_sermon(
    client,
    initial_status
):

    log()
    log("=" * 70)
    log("LIVE SERMON AI STARTING")
    log("=" * 70)

    auto_started_replay = (
        ensure_replay_buffer(
            client,
            initial_status
        )
    )

    # -----------------------------------------------------
    # LOAD SMALL MODEL
    # -----------------------------------------------------

    log()
    log(
        "Loading live Whisper "
        "model: small"
    )

    model = WhisperModel(
        WHISPER_MODEL,
        device=WHISPER_DEVICE,
        compute_type=(
            WHISPER_COMPUTE_TYPE
        ),
    )

    log(
        "Live Whisper loaded."
    )

    # -----------------------------------------------------
    # AUDIO
    # -----------------------------------------------------

    audio, stream, device_index, rate, channels = (
        open_loopback_stream()
    )

    log()
    log(
        f"Listening to device "
        f"{device_index}: "
        f"{audio.get_device_info_by_index(device_index)['name']}"
    )

    # -----------------------------------------------------
    # SESSION STATE
    # -----------------------------------------------------

    thought_parts = []
    thought_start_time = None
    silence_chunks = 0

    last_save_time = 0
    clip_number = 0

    in_prayer = False

    session_running = True

    try:

        while session_running:

            # ---------------------------------------------
            # CHECK OBS FIRST
            # ---------------------------------------------

            status = read_obs_status(
                client
            )

            if not status["connected"]:

                log()
                log(
                    "OBS disconnected."
                )

                session_running = False
                break

            # If we started Replay Buffer automatically,
            # stop it once stream + recording have ended.
            if (
                auto_started_replay
                and
                not main_service_running(
                    status
                )
            ):

                stop_auto_replay(
                    client,
                    True
                )

                auto_started_replay = False

                status = read_obs_status(
                    client
                )

            # If nothing OBS-related is active anymore,
            # the live session is finished.
            if not obs_has_activity(
                status
            ):

                log()
                log(
                    "All OBS output activity "
                    "has stopped."
                )

                session_running = False
                break

            # If recording/streaming starts but replay
            # somehow stopped, restart it.
            if (
                main_service_running(status)
                and
                not status["replay"]
            ):

                auto_started_replay = (
                    ensure_replay_buffer(
                        client,
                        status
                    )
                    or
                    auto_started_replay
                )

            # ---------------------------------------------
            # CAPTURE 6 SEC
            # ---------------------------------------------

            frames = []

            chunks_to_read = int(
                rate
                /
                1024
                *
                CHUNK_SECONDS
            )

            try:

                for _ in range(
                    chunks_to_read
                ):

                    data = read_stream_chunk(
                        stream,
                        1024
                    )

                    frames.append(data)

            except Exception as error:

                log()
                log(
                    "WARNING: Audio capture stalled "
                    f"({error}). Reopening the loopback "
                    "device..."
                )

                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass

                try:
                    audio.terminate()
                except Exception:
                    pass

                reopened = False

                for attempt in range(6):

                    try:
                        (
                            audio,
                            stream,
                            device_index,
                            rate,
                            channels,
                        ) = open_loopback_stream()

                        reopened = True
                        break

                    except Exception as reopen_error:

                        log(
                            f"Retry {attempt + 1}/6: still "
                            f"cannot reopen audio device "
                            f"({reopen_error})."
                        )

                        time.sleep(5)

                if reopened:
                    log(
                        "Audio device reopened. Resuming "
                        "live listening."
                    )
                else:
                    log(
                        "Could not recover the audio "
                        "device. Ending live listening for "
                        "this service."
                    )

                    session_running = False
                    break

                continue

            # ---------------------------------------------
            # TEMP AUDIO
            # ---------------------------------------------

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            ) as temp_file:

                temp_path = (
                    temp_file.name
                )

            with wave.open(
                temp_path,
                "wb"
            ) as wf:

                wf.setnchannels(
                    channels
                )

                wf.setsampwidth(
                    audio.get_sample_size(
                        pyaudio.paInt16
                    )
                )

                wf.setframerate(
                    rate
                )

                wf.writeframes(
                    b"".join(frames)
                )

            # ---------------------------------------------
            # TRANSCRIBE
            # ---------------------------------------------

            chunk_text = ""

            try:

                segments, _ = (
                    model.transcribe(
                        temp_path,
                        language="en",
                        vad_filter=True,
                        beam_size=5,
                    )
                )

                pieces = []

                for segment in segments:

                    text = (
                        segment.text
                        .strip()
                    )

                    if text:

                        pieces.append(
                            text
                        )

                chunk_text = " ".join(
                    pieces
                )

            finally:

                try:

                    os.remove(
                        temp_path
                    )

                except OSError:

                    pass

            now = time.time()

            process_thought = False

            # ---------------------------------------------
            # SILENCE
            # ---------------------------------------------

            if not chunk_text:

                if thought_parts:

                    silence_chunks += 1

                    duration = (
                        now
                        -
                        thought_start_time
                    )

                    process_thought = (
                        should_finish_thought(
                            duration,
                            "",
                            silence_chunks,
                        )
                    )

                if not process_thought:

                    continue

            else:

                silence_chunks = 0

                clock = (
                    datetime.now()
                    .strftime(
                        "%H:%M:%S"
                    )
                )

                log(
                    f"[{clock}] "
                    f"{chunk_text}"
                )

                # -----------------------------------------
                # PRAYER MODE
                # -----------------------------------------

                previous_prayer = (
                    in_prayer
                )

                in_prayer = (
                    update_prayer_state(
                        chunk_text,
                        in_prayer
                    )
                )

                # Still inside prayer
                if in_prayer:

                    thought_parts = []
                    thought_start_time = None

                    continue

                # Prayer just ended. Don't use the Amen
                # chunk as a new candidate.
                if (
                    previous_prayer
                    and
                    not in_prayer
                ):

                    thought_parts = []
                    thought_start_time = None

                    continue

                # -----------------------------------------
                # THOUGHT
                # -----------------------------------------

                if thought_start_time is None:

                    thought_start_time = now

                thought_parts.append(
                    chunk_text
                )

                duration = (
                    now
                    -
                    thought_start_time
                    +
                    CHUNK_SECONDS
                )

                process_thought = (
                    should_finish_thought(
                        duration,
                        chunk_text,
                        silence_chunks,
                    )
                )

                if not process_thought:

                    continue

            # ---------------------------------------------
            # COMPLETE THOUGHT
            # ---------------------------------------------

            if not thought_parts:

                continue

            thought_text = " ".join(
                thought_parts
            ).strip()

            thought_duration = (
                now
                -
                thought_start_time
                +
                CHUNK_SECONDS
            )

            # Start fresh immediately
            thought_parts = []
            thought_start_time = None
            silence_chunks = 0

            if (
                thought_duration
                <
                MIN_THOUGHT_SECONDS
            ):

                continue

            score, reasons = (
                score_sermon_moment(
                    thought_text,
                    thought_duration,
                )
            )

            log()
            log("-" * 70)
            log("COMPLETED THOUGHT")

            log(
                f"Duration: "
                f"{thought_duration:.1f}s"
            )

            log(
                f"Score: {score}"
            )

            log()
            log(thought_text)
            log()

            if reasons:

                log(
                    "Reasons: "
                    +
                    ", ".join(
                        reasons
                    )
                )

            # ---------------------------------------------
            # SCORE
            # ---------------------------------------------

            if (
                score
                <
                POSSIBLE_THRESHOLD
            ):

                log(
                    "Status: ignore"
                )

                continue

            if (
                score
                <
                SAVE_THRESHOLD
            ):

                log(
                    "Status: POSSIBLE CLIP"
                )

                continue

            log(
                "Status: STRONG CLIP"
            )

            # ---------------------------------------------
            # COOLDOWN
            # ---------------------------------------------

            elapsed = (
                now
                -
                last_save_time
            )

            if (
                elapsed
                <
                MIN_SECONDS_BETWEEN_SAVES
            ):

                remaining = int(
                    MIN_SECONDS_BETWEEN_SAVES
                    -
                    elapsed
                )

                log(
                    "Cooldown active: "
                    f"{remaining}s remaining."
                )

                continue

            # ---------------------------------------------
            # SAVE
            # ---------------------------------------------

            log(
                f"Waiting "
                f"{SAVE_DELAY_SECONDS}s "
                f"before saving..."
            )

            time.sleep(
                SAVE_DELAY_SECONDS
            )

            log(
                "Saving OBS Replay Buffer..."
            )

            client, replay_path = (
                save_obs_replay(
                    client
                )
            )

            if client is None:

                log(
                    "OBS connection lost."
                )

                session_running = False
                break

            if replay_path is None:

                log(
                    "WARNING: Replay was "
                    "not located."
                )

                continue

            clip_number += 1

            clip_path = move_replay(
                replay_path,
                clip_number,
                score,
            )

            transcript_path = (
                save_candidate_transcript(
                    clip_path,
                    score,
                    thought_text,
                    reasons,
                    thought_duration,
                )
            )

            last_save_time = (
                time.time()
            )

            log()
            log("CLIP SAVED:")
            log(clip_path)

            log()
            log(
                "TRANSCRIPT SAVED:"
            )

            log(
                transcript_path
            )

    finally:

        # If the service ended while our replay buffer
        # was still active, shut it down.
        try:

            stop_auto_replay(
                client,
                auto_started_replay
            )

        except Exception:

            pass

        try:

            stream.stop_stream()
            stream.close()

        except Exception:

            pass

        try:

            audio.terminate()

        except Exception:

            pass

        # Explicitly unload the Small model before
        # Medium is ever launched.
        try:

            del model

        except Exception:

            pass

        gc.collect()

        log()
        log(
            "Live Whisper unloaded."
        )

    return client


# =========================================================
# POST-SERVICE IDLE WAIT
# =========================================================

def wait_post_service_delay():

    log()
    log(
        f"Waiting {POST_SERVICE_DELAY} "
        f"seconds before quality processing..."
    )

    start = time.time()

    client = None

    while True:

        elapsed = (
            time.time()
            -
            start
        )

        remaining = int(
            POST_SERVICE_DELAY
            -
            elapsed
        )

        if remaining <= 0:

            log(
                "Post-service delay complete."
            )

            return True

        # OBS may be closed completely, which is fine.
        if client is None:

            client = try_connect_obs()

        if client is not None:

            status = read_obs_status(
                client
            )

            if not status["connected"]:

                client = None

            elif obs_has_activity(
                status
            ):

                log()
                log(
                    "OBS became active again. "
                    "Cancelling post-service "
                    "processing."
                )

                return False

        time.sleep(
            IDLE_CHECK_INTERVAL
        )


# =========================================================
# MEDIUM MODEL PROCESSOR
# =========================================================

def obs_became_active():

    client = try_connect_obs()

    if client is None:
        return False

    status = read_obs_status(
        client
    )

    if not status["connected"]:
        return False

    return obs_has_activity(
        status
    )


def run_post_service_program(
    script_path,
    description
):

    if not os.path.exists(
        script_path
    ):

        log(
            f"ERROR: {os.path.basename(script_path)} "
            f"was not found."
        )

        return False

    log()
    log("=" * 70)
    log(description)
    log("=" * 70)

    process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            script_path,
        ],
        cwd=BASE_FOLDER,
    )

    while True:

        return_code = (
            process.poll()
        )

        if return_code is not None:

            if return_code == 0:

                log()
                log(
                    f"{description} finished "
                    f"successfully."
                )

                return True

            else:

                log()
                log(
                    f"{description} exited "
                    f"with code {return_code}."
                )

                return False

        # If OBS suddenly starts again,
        # immediately give the GPU back
        # to the live service.
        if obs_became_active():

            log()
            log(
                "OBS became active again."
            )

            log(
                f"Stopping {description}..."
            )

            try:

                process.terminate()

                process.wait(
                    timeout=10
                )

            except Exception:

                try:
                    process.kill()

                except Exception:
                    pass

            return False

        time.sleep(2)


def run_quality_processor():

    log()
    log("=" * 70)
    log(
        "POST-SERVICE PROCESSING STARTING"
    )
    log("=" * 70)

    # =====================================================
    # STAGE 1
    # MEDIUM WHISPER VERIFICATION
    # =====================================================

    verified = run_post_service_program(
        PROCESS_SHORTS_SCRIPT,
        "MEDIUM WHISPER VERIFICATION"
    )

    if not verified:

        log()
        log(
            "Verification did not complete."
        )

        return False

    # Make sure OBS has not started again.
    if obs_became_active():

        log()
        log(
            "OBS activity detected before rendering."
        )

        return False

    # =====================================================
    # STAGE 2
    # VERTICAL SHORT RENDERING
    # =====================================================

    rendered = run_post_service_program(
        RENDER_SHORTS_SCRIPT,
        "VERTICAL SHORT RENDERING"
    )

    if not rendered:

        log()
        log(
            "Renderer did not complete."
        )

        return False

    # Make sure OBS is still idle before
    # preparing the sermon information.
    if obs_became_active():

        log()
        log(
            "OBS became active before "
            "thumbnail preparation."
        )

        return False

    # =====================================================
    # STAGE 3
    # SERMON / THUMBNAIL PREPARATION
    # =====================================================

    prepared = run_post_service_program(
        PREPARE_SERMON_SCRIPT,
        "SERMON THUMBNAIL PREPARATION"
    )

    if not prepared:

        log()
        log(
            "Thumbnail preparation "
            "did not complete."
        )

        return False

    # =====================================================
    # COMPLETE
    # =====================================================

    log()
    log("=" * 70)
    log(
        "POST-SERVICE PROCESSING COMPLETE"
    )
    log("=" * 70)

    return True
# =========================================================
# CONTROLLER
# =========================================================

def main():

    ensure_folders()

    if not OBS_PASSWORD:

        log(
            "ERROR: OBS_PASSWORD is "
            "missing from .env"
        )

        return

    log()
    log("=" * 70)
    log("SERMON AI CONTROLLER")
    log("=" * 70)

    log(
        f"Started: {datetime.now()}"
    )

    log()
    log(
        "The controller will stay idle "
        "until OBS activity begins."
    )

    while True:

        try:

            # ---------------------------------------------
            # WAIT FOR CHURCH VIDEO ACTIVITY
            # ---------------------------------------------

            (
                client,
                status,
            ) = wait_for_service_activity()

            # ---------------------------------------------
            # SMALL WHISPER / LIVE CLIPPING
            # ---------------------------------------------

            client = run_live_sermon(
                client,
                status
            )

            # ---------------------------------------------
            # WAIT BEFORE MEDIUM
            # ---------------------------------------------

            safe_to_process = (
                wait_post_service_delay()
            )

            if not safe_to_process:

                log()
                log(
                    "Returning to live "
                    "activity detection."
                )

                continue

            # ---------------------------------------------
            # MEDIUM VERIFICATION
            # ---------------------------------------------

            completed = (
                run_quality_processor()
            )

            if not completed:

                log()
                log(
                    "Quality processing was "
                    "interrupted by new OBS "
                    "activity."
                )

            # ---------------------------------------------
            # RETURN TO IDLE
            # ---------------------------------------------

            log()
            log("=" * 70)
            log(
                "SERMON AI RETURNING TO IDLE"
            )
            log("=" * 70)
            log()

        except KeyboardInterrupt:

            log()
            log(
                "Sermon AI controller stopped."
            )

            break

        except Exception as error:

            log()
            log(
                "Controller encountered "
                "an error:"
            )

            log(
                str(error)
            )

            log(
                "Restarting controller "
                "in 10 seconds..."
            )

            time.sleep(10)


if __name__ == "__main__":
    main()