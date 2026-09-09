import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

from sss_profile import (
    get_profile_sermon_source_settings,
    load_active_profile,
)

BASE = Path(r"C:\Church\SermonAI")
SERMON_PLAN_FILE = BASE / "sermon_plan.json"
GMAIL_IMPORTER = BASE / "core" / "gmail_sermon_importer.py"
GMAIL_TOKEN_FILE = BASE / "gmail_token.json"


SERMON_SOURCE_ADAPTERS = {
    "Manual": {
        "live_supported": True,
        "description": (
            "Stores a portable sermon plan in the church profile and materializes "
            "it into the normal SSS sermon_plan.json when Sunday services start."
        ),
    },
    "Pastor Email": {
        "live_supported": True,
        "description": (
            "Uses the existing date-guarded Gmail sermon importer as the provider backend."
        ),
    },
    "Imported File": {
        "live_supported": True,
        "description": (
            "Imports a validated sermon-plan JSON into the church profile so it can travel with the profile."
        ),
    },
    "Planning Software": {
        "live_supported": False,
        "description": (
            "Current Planning integration is outbound Scripture sync. Direct Planning-as-source is planned."
        ),
    },
    "Other": {
        "live_supported": False,
        "description": (
            "Reserved for future sermon-information providers."
        ),
    },
}


def adapter_info(provider):
    provider = str(provider or "Manual").strip()
    info = dict(
        SERMON_SOURCE_ADAPTERS.get(
            provider,
            {
                "live_supported": False,
                "description": "Unknown sermon source.",
            },
        )
    )
    info["provider"] = provider
    return info


def upcoming_sunday_iso(today=None):
    if today is None:
        today = datetime.date.today()

    days_until_sunday = (6 - today.weekday()) % 7
    return (
        today
        +
        datetime.timedelta(days=days_until_sunday)
    ).isoformat()


def _clean_text(value):
    return " ".join(str(value or "").split())


def _normalize_points(points):
    if not isinstance(points, list):
        points = []

    cleaned = []

    for item in points:
        if isinstance(item, dict):
            text = _clean_text(
                item.get("title")
                or
                item.get("name")
                or
                item.get("text")
                or
                item.get("point")
            )
        else:
            text = _clean_text(item)

        if text:
            cleaned.append(text)

    return cleaned


def make_plan_id(plan):
    payload = "|".join(
        [
            _clean_text(plan.get("service_date")),
            _clean_text(plan.get("title")),
            _clean_text(plan.get("scripture")),
            "||".join(_normalize_points(plan.get("points", []))),
        ]
    )

    digest = hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()[:16]

    return "profile-" + digest


def normalize_sermon_plan(plan, *, source_provider="Profile"):
    if not isinstance(plan, dict):
        raise ValueError(
            "Sermon plan must be a JSON object."
        )

    normalized = dict(plan)

    title = _clean_text(
        plan.get("title")
        or
        plan.get("sermon_title")
    )

    scripture = _clean_text(
        plan.get("scripture")
        or
        plan.get("text")
        or
        plan.get("reference")
    )

    preacher = _clean_text(
        plan.get("preacher")
        or
        plan.get("speaker")
    )

    service_date = _clean_text(
        plan.get("service_date")
        or
        plan.get("date")
    )

    points = _normalize_points(
        plan.get("points")
        or
        plan.get("outline")
        or
        []
    )

    if not title:
        raise ValueError(
            "Sermon title is required."
        )

    if not scripture:
        raise ValueError(
            "Scripture reference is required."
        )

    if not points:
        raise ValueError(
            "At least one sermon point is required."
        )

    if not service_date:
        raise ValueError(
            "Service date is required."
        )

    try:
        datetime.date.fromisoformat(
            service_date
        )
    except Exception:
        raise ValueError(
            "Service date must use YYYY-MM-DD."
        )

    normalized["title"] = title
    normalized["scripture"] = scripture
    normalized["preacher"] = preacher
    normalized["service_date"] = service_date
    normalized["points"] = points
    normalized["source_provider"] = _clean_text(
        source_provider
    )

    if not _clean_text(
        normalized.get("plan_id")
    ):
        normalized["plan_id"] = make_plan_id(
            normalized
        )

    return normalized


def build_manual_plan(
    *,
    title,
    scripture,
    service_date,
    points,
    preacher=""
):
    return normalize_sermon_plan(
        {
            "title": title,
            "scripture": scripture,
            "service_date": service_date,
            "points": list(points or []),
            "preacher": preacher,
        },
        source_provider="Manual",
    )


def load_imported_plan_file(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            str(path)
        )

    if path.suffix.lower() != ".json":
        raise ValueError(
            "Imported sermon plans must currently be JSON files."
        )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return normalize_sermon_plan(
        payload,
        source_provider="Imported File",
    )


def read_canonical_sermon_plan():
    if not SERMON_PLAN_FILE.exists():
        return {}

    try:
        payload = json.loads(
            SERMON_PLAN_FILE.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(payload, dict):
            return payload

    except Exception:
        pass

    return {}


def write_canonical_sermon_plan(plan):
    normalized = normalize_sermon_plan(
        plan,
        source_provider=(
            plan.get(
                "source_provider",
                "Profile"
            )
            if isinstance(plan, dict)
            else
            "Profile"
        ),
    )

    SERMON_PLAN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = SERMON_PLAN_FILE.with_suffix(
        SERMON_PLAN_FILE.suffix
        +
        ".tmp"
    )

    temp.write_text(
        json.dumps(
            normalized,
            indent=2,
            ensure_ascii=False,
        )
        +
        "\n",
        encoding="utf-8",
    )

    os.replace(
        temp,
        SERMON_PLAN_FILE,
    )

    return normalized


def active_sermon_source_settings():
    return get_profile_sermon_source_settings(
        load_active_profile()
    )


def profile_sermon_source_ready():
    settings = active_sermon_source_settings()

    if settings.get(
        "settings_source"
    ) != "profile":
        return (
            True,
            "LEGACY sermon source",
        )

    provider = settings.get(
        "provider",
        "Manual"
    )

    info = adapter_info(
        provider
    )

    if not info.get(
        "live_supported",
        False
    ):
        return (
            False,
            info.get(
                "description",
                ""
            ),
        )

    if provider == "Manual":
        try:
            plan = normalize_sermon_plan(
                settings.get(
                    "manual_plan",
                    {}
                ),
                source_provider="Manual",
            )

            return (
                True,
                (
                    plan.get("title", "")
                    +
                    " | "
                    +
                    plan.get("scripture", "")
                ),
            )

        except Exception as exc:
            return (
                False,
                str(exc),
            )

    if provider == "Imported File":
        try:
            plan = normalize_sermon_plan(
                settings.get(
                    "imported_plan",
                    {}
                ),
                source_provider="Imported File",
            )

            return (
                True,
                (
                    plan.get("title", "")
                    +
                    " | "
                    +
                    plan.get("scripture", "")
                ),
            )

        except Exception as exc:
            return (
                False,
                str(exc),
            )

    if provider == "Pastor Email":
        if not GMAIL_IMPORTER.exists():
            return (
                False,
                "gmail_sermon_importer.py is missing.",
            )

        if not GMAIL_TOKEN_FILE.exists():
            return (
                False,
                "Gmail authorization token is missing on this PC.",
            )

        return (
            True,
            "Pastor Email backend and local Gmail authorization are ready.",
        )

    return (
        False,
        "Sermon source adapter is not ready.",
    )


def materialize_profile_sermon_plan():
    """
    Materialize profile-contained Manual/Imported plans into the canonical
    sermon_plan.json used by the existing SSS downstream pipeline.

    Pastor Email is handled by the existing Gmail importer instead.
    """
    settings = active_sermon_source_settings()

    if settings.get(
        "settings_source"
    ) != "profile":
        return {
            "action": "legacy",
            "plan": read_canonical_sermon_plan(),
        }

    provider = settings.get(
        "provider",
        "Manual"
    )

    if provider == "Manual":
        plan = normalize_sermon_plan(
            settings.get(
                "manual_plan",
                {}
            ),
            source_provider="Manual",
        )

        return {
            "action": "materialized",
            "plan": write_canonical_sermon_plan(
                plan
            ),
        }

    if provider == "Imported File":
        plan = normalize_sermon_plan(
            settings.get(
                "imported_plan",
                {}
            ),
            source_provider="Imported File",
        )

        return {
            "action": "materialized",
            "plan": write_canonical_sermon_plan(
                plan
            ),
        }

    if provider == "Pastor Email":
        return {
            "action": "email",
            "plan": read_canonical_sermon_plan(),
        }

    raise RuntimeError(
        (
            "No live SSS sermon source adapter is implemented yet for "
            +
            str(provider)
            +
            "."
        )
    )


def refresh_pastor_email_now(
    *,
    timeout=30
):
    settings = active_sermon_source_settings()

    if (
        settings.get("settings_source") != "profile"
        or
        settings.get("provider") != "Pastor Email"
    ):
        raise RuntimeError(
            "PROFILE + Pastor Email is not active."
        )

    if not GMAIL_IMPORTER.exists():
        raise RuntimeError(
            "gmail_sermon_importer.py is missing."
        )

    python = (
        BASE
        /
        "venv"
        /
        "Scripts"
        /
        "python.exe"
    )

    if not python.exists():
        raise RuntimeError(
            "SSS Python environment is missing."
        )

    cp = subprocess.run(
        [
            str(python),
            str(GMAIL_IMPORTER),
            "--quiet",
        ],
        cwd=BASE,
        capture_output=True,
        text=True,
        timeout=int(timeout),
        creationflags=(
            subprocess.CREATE_NO_WINDOW
            if os.name == "nt"
            else 0
        ),
    )

    if cp.returncode != 0:
        detail = (
            cp.stderr.strip()
            or
            cp.stdout.strip()
            or
            "unknown Gmail importer error"
        )

        raise RuntimeError(
            detail
        )

    plan = read_canonical_sermon_plan()

    if not plan:
        raise RuntimeError(
            "Pastor Email importer completed but no sermon plan was produced."
        )

    return plan
