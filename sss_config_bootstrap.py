"""
Builds a fresh sunday_config.json for a brand-new church install.

Pure dict-in/file-out: no Tkinter, no dependency on sss_profile.py or
sunday_common.py, so it can be imported by the first-run wizard without
either of those modules needing to know this exists.
"""

import json
import os
from pathlib import Path

BASE = Path(r"C:\Church\SermonAI")
CONFIG_PATH = BASE / "sunday_config.json"


def default_sunday_config():
    """
    Safe, church-agnostic defaults for every key the setup wizard doesn't
    ask about. These are policy/timing defaults, not facts about any
    particular church, so the same values are correct for every install.
    """
    return {
        "minimum_free_gb": 100,
        "critical_free_gb": 25,
        "internet_test_host": "www.youtube.com",
        "internet_test_port": 443,
        "start_streaming_with_service": False,
        "start_recording_with_service": False,
        "auto_fix_scene_collection": True,
        "auto_start_sermon_ai": True,
        "auto_start_chapter_bridge": True,
        "chapter_bridge_poll_seconds": 1.5,
        "chapter_duplicate_cooldown_seconds": 12,
        "chapter_mark_start": False,
        "dashboard_refresh_seconds": 5.0,
        "volunteer_default_action": "recording_only",
        "gmail_sermon_lookback_days": 14,
        "auto_update_planning_scripture": True,
        "planning_update_timeout_seconds": 60,
        "auto_start_presenter": True,
        "youtube_video_extensions": [".mp4"],
        "youtube_min_file_mb": 500,
        "youtube_min_duration_minutes": 20,
        "youtube_file_stable_seconds": 300,
        "youtube_trigger_lookback_minutes": 15,
        "youtube_candidate_wait_minutes": 360,
        "youtube_candidate_poll_seconds": 30,
        "youtube_upload_retries": 10,
        "youtube_upload_mode": "studio",
        "youtube_studio_publish_wait_minutes": 360,
        "youtube_checks_wait_seconds": 300,
        "youtube_retry_interval_seconds": 300,
        "youtube_service_date_grace_days": 3,
        "sss_version": "22",
        "weekly_backup_retention_weeks": 12,
        "log_retention_days": 90,
        "recording_growth_alarm_seconds": 60,
        "recording_growth_min_bytes": 1048576,
        "recording_file_find_alarm_seconds": 30,
        "audio_sanity_silence_db": -55,
        "audio_sanity_silence_seconds": 120,
        "audio_sanity_clip_db": -0.5,
        "audio_sanity_clip_seconds": 3,
        "audio_sanity_start_grace_seconds": 90,
        "post_service_supervisor_hours": 8,
        "post_service_auto_resume": True,
        "auto_weekly_snapshot": True,
        "auto_operational_cleanup": True,
        "ptz_camera_timeout_seconds": 4,
        "ptz_auto_recall_on_sss_start": True,
        "chapter_rotation_enabled": True,
        "chapter_include_prayer": True,
        "chapter_prayer_name": "Prayer",
        "chapter_include_reference": True,
        "chapter_reference_name": "Reference",
        "chapter_reference_use_scripture": False,
        "chapter_include_benediction": True,
        "chapter_benediction_name": "Benediction",
        "chapter_sync_named_hotkeys_from_gmail": True,
        "chapter_hotkey_sync_while_obs_running": False,
        "chapter_bridge_auto_from_lower_thirds": False,
        "chapter_include_ending_prayer": True,
        "chapter_ending_prayer_name": "Ending Prayer",
        "obs_host": "localhost",
        "obs_port": 4455,
    }


def _machine_paths(base):
    """Paths derived from the install location / this Windows profile - never hardcoded to a specific church's machine."""
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    start_menu = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    appdata = Path(os.environ.get("APPDATA", ""))
    userprofile = Path(os.environ.get("USERPROFILE", ""))

    obs_exe = program_files / "obs-studio" / "bin" / "64bit" / "obs64.exe"
    obs_shortcut = start_menu / "OBS Studio.lnk"
    presenter_shortcut = start_menu / "Presenter.lnk"

    return {
        "obs_exe": str(obs_exe) if obs_exe.exists() else "",
        "obs_shortcut": str(obs_shortcut) if obs_shortcut.exists() else "",
        "presenter_shortcut": str(presenter_shortcut) if presenter_shortcut.exists() else "",
        "sermon_ai_launcher": str(base / "start_sermon_ai_hidden.vbs"),
        "lower_thirds_leveldb": str(
            appdata / "obs-studio" / "plugin_config" / "obs-browser" / "Local Storage" / "leveldb"
        ),
        "lower_thirds_folder": str(
            userprofile / "Documents" / "Animated-Lower-Thirds" / "lower thirds"
        ),
        "gmail_credentials_file": str(base / "gmail_credentials.json"),
        "gmail_token_file": str(base / "gmail_token.json"),
        "youtube_credentials_file": str(base / "gmail_credentials.json"),
        "youtube_token_file": str(base / "youtube_token.json"),
        "sermon_plan_file": str(base / "sermon_plan.json"),
        "planning_profile_folder": str(base / "WorshipTools_Planning_Profile"),
        "youtube_studio_profile_folder": str(base / "YouTube_Studio_Profile"),
    }


def build_sunday_config(profile, answers, base=BASE):
    """
    Combine the wizard's collected answers with safe defaults and
    machine-derived paths into a complete sunday_config.json payload.

    `answers` is a flat dict keyed by the same names as sunday_config.json,
    built by the setup wizard's _collect_answers(). Any key the wizard
    didn't ask about (integration was skipped, or it's a safe default)
    is simply absent from `answers` and falls back to the defaults below.
    """
    config = default_sunday_config()
    config.update(_machine_paths(base))

    recording_folder = str(
        answers.get("recording_folder")
        or
        (base.drive + "\\2026" if base.drive else r"D:\2026")
    )

    config["recording_folder"] = recording_folder
    config["critical_folders"] = [
        recording_folder,
        str(Path(recording_folder) / "SRT files"),
        str(Path(recording_folder) / "shorts" / "ai shorts" / "Ready"),
        str(Path(recording_folder) / "shorts" / "ai shorts" / "Sermon Data"),
    ]
    config["sermon_data_folder"] = str(
        Path(recording_folder) / "shorts" / "ai shorts" / "Sermon Data"
    )

    church_specific_keys = (
        "scene_collection",
        "default_preacher",
        "help_contact_text",
        "gmail_sermon_sender",
        "gmail_sermon_senders",
        "planning_account_id",
        "planning_translation",
        "planning_service_time",
        "youtube_expected_channel_id",
        "youtube_expected_channel_name",
        "youtube_expected_handle",
        "youtube_privacy_status",
        "youtube_category_id",
        "youtube_notify_subscribers",
        "youtube_audience",
        "ptz_camera_provider",
        "ptz_camera_ip",
        "ptz_camera_scheme",
        "ptz_camera_http_port",
        "ptz_camera_username",
        "ptz_camera_password",
        "ptz_startup_preset",
        "ptz_worship_preset",
        "ptz_pastor_preset",
        "audio_loopback_name",
        "audio_loopback_label",
        "critical_inputs",
        "recommended_inputs",
        "emergency_mute_inputs",
        "audio_sanity_inputs",
        "ptz_camera_enabled",
        "auto_upload_youtube",
        "auto_import_sermon_email",
        "audio_sanity_enabled",
    )

    for key in church_specific_keys:
        if key in answers:
            config[key] = answers[key]

    config.setdefault("scene_collection", "Church recording")
    config.setdefault("critical_inputs", [])
    config.setdefault("recommended_inputs", [])
    config.setdefault("emergency_mute_inputs", [])
    config.setdefault("audio_sanity_inputs", [])
    config.setdefault("ptz_camera_enabled", False)
    config.setdefault("auto_upload_youtube", False)
    config.setdefault("auto_import_sermon_email", False)
    config.setdefault("audio_sanity_enabled", False)

    # Keys left blank when the matching integration/page was skipped, kept
    # present (rather than absent) so the file's shape stays predictable
    # for anyone editing it later in Settings.
    config.setdefault("default_preacher", "")
    config.setdefault("help_contact_text", "")
    config.setdefault("gmail_sermon_sender", "")
    config.setdefault("gmail_sermon_senders", [])
    config.setdefault("planning_account_id", "")
    config.setdefault("planning_translation", "ESV")
    config.setdefault("planning_service_time", "")
    config.setdefault("audio_loopback_name", "")
    config.setdefault("audio_loopback_label", "Audio Interface")
    config.setdefault("ptz_camera_provider", "PTZOptics / HTTP-CGI")
    config.setdefault("ptz_camera_ip", "")
    config.setdefault("ptz_camera_scheme", "http")
    config.setdefault("ptz_camera_http_port", "")
    config.setdefault("ptz_camera_username", "")
    config.setdefault("ptz_camera_password", "")
    config.setdefault("ptz_startup_preset", 2)
    config.setdefault("ptz_worship_preset", 1)
    config.setdefault("ptz_pastor_preset", 2)
    config.setdefault("youtube_expected_channel_id", "")
    config.setdefault("youtube_expected_channel_name", "")
    config.setdefault("youtube_expected_handle", "")
    config.setdefault("youtube_privacy_status", "public")
    config.setdefault("youtube_category_id", "29")
    config.setdefault("youtube_notify_subscribers", True)
    config.setdefault("youtube_audience", "channel_default")

    return config


def write_sunday_config(config, path=CONFIG_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def provision_filesystem(config):
    """Create the recording folder and its critical subfolders so a new install doesn't start with a 'missing folder' warning."""
    for folder in config.get("critical_folders", []):
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
