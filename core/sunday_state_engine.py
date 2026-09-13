# -*- coding: utf-8 -*-
"""Derives the current Sunday-service phase from signals that already exist
elsewhere (recording state, chapter rotation, post-service status).

Deliberately dependency-light: no Tkinter, no OBS connection, no import of
sunday_mode. Callers gather what they already have and pass it in, which
keeps this module safe to unit-test with synthetic inputs.
"""

from pathlib import Path

from sss_reliability import POST_STATUS_FILE, read_json

BASE = Path(r"C:\Church\SermonAI")
SERMON_PLAN_FILE = BASE / "sermon_plan.json"

PREPARING = "PREPARING"
READY = "READY"
RECORDING = "RECORDING"
SERMON = "SERMON"
POST_SERVICE = "POST_SERVICE"
COMPLETE = "COMPLETE"

CRITICAL_PREFLIGHT_KEYS = (
    "OBS",
    "COLLECTION",
    "AUDIO",
    "INPUTS",
    "DISK",
    "FOLDERS",
    "SERMON_AI",
    "TOOLS",
)


def blocking_preflight_keys(check_results):
    """Same filter as start_recording()'s critical_failures list: a check
    counts as blocking only if it's both not-ok and not-a-warning."""
    return [
        key
        for key in CRITICAL_PREFLIGHT_KEYS
        if key in check_results
        and not check_results[key][0]
        and not check_results[key][2]
    ]


def sermon_started(rotation_sequence, rotation_state):
    """True once the rotation has fired at least one sermon-point chapter."""
    next_index = int(rotation_state.get("next_index", 0))
    fired = rotation_sequence[:next_index]
    return any(
        str(item.get("role", "")).lower().startswith("point")
        for item in fired
    )


def classify_post_service_state(post_payload, current_plan_id):
    """Returns the post-service state string for the CURRENT plan, or ""
    if there is no post-service record yet or the on-disk one belongs to a
    different (stale) plan_id — same staleness check as
    sunday_mode.check_post_service_status()."""
    if not post_payload:
        return ""

    payload_plan_id = post_payload.get("plan_id")

    if payload_plan_id and current_plan_id and payload_plan_id != current_plan_id:
        return ""

    return str(post_payload.get("state", "")).upper()


def read_post_service_state():
    return classify_post_service_state(
        read_json(POST_STATUS_FILE, {}),
        read_json(SERMON_PLAN_FILE, {}).get("plan_id"),
    )


def compute_phase(
    *,
    last_recording_state,
    service_ending,
    check_results,
    rotation_sequence,
    rotation_state,
    post_service_state=None,
):
    """Returns {"phase", "headline", "action", "blocking"}.

    post_service_state may be passed explicitly (tests do this to avoid
    touching disk); production leaves it None and it's read live.
    """
    if post_service_state is None:
        post_service_state = read_post_service_state()

    if service_ending:
        return {
            "phase": POST_SERVICE,
            "headline": "ENDING SERVICE",
            "action": "Stopping the recording — post-service jobs are starting automatically.",
            "blocking": [],
        }

    if last_recording_state is None:
        return {
            "phase": PREPARING,
            "headline": "PREPARING",
            "action": "Waiting to confirm the connection to OBS.",
            "blocking": [],
        }

    if last_recording_state:
        if sermon_started(rotation_sequence, rotation_state):
            return {
                "phase": SERMON,
                "headline": "SERMON",
                "action": (
                    "The message is underway. Keep advancing chapters as "
                    "the pastor moves through each point."
                ),
                "blocking": [],
            }

        return {
            "phase": RECORDING,
            "headline": "RECORDING — LIVE",
            "action": (
                "Advance chapters with NEXT SERMON CHAPTER (or the "
                "Scripture button) as the service proceeds."
            ),
            "blocking": [],
        }

    if post_service_state == "RUNNING":
        return {
            "phase": POST_SERVICE,
            "headline": "POST-SERVICE",
            "action": (
                "Post-service jobs (YouTube upload, transcript, cleanup) "
                "are running automatically. No action needed."
            ),
            "blocking": [],
        }

    if post_service_state == "ATTENTION":
        return {
            "phase": POST_SERVICE,
            "headline": "POST-SERVICE — NEEDS REVIEW",
            "action": "Something needs your attention — see the AFTER SERVICE section below.",
            "blocking": [],
        }

    if post_service_state == "COMPLETE":
        return {
            "phase": COMPLETE,
            "headline": "COMPLETE",
            "action": "Post-service processing finished. Safe to close Sunday Service System.",
            "blocking": [],
        }

    blocking = blocking_preflight_keys(check_results or {})

    if blocking:
        return {
            "phase": PREPARING,
            "headline": "PREPARING",
            "action": "Resolve the flagged items below, then you'll be ready to record.",
            "blocking": blocking,
        }

    return {
        "phase": READY,
        "headline": "READY",
        "action": "Everything looks good. Press START RECORDING when the service begins.",
        "blocking": [],
    }
