import os
import sys
import json
import re
import datetime
import time
import socket
import shutil
import subprocess
import threading
import queue
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import (
    ttk,
    messagebox,
)

try:
    import winsound
except Exception:
    winsound = None


from sunday_common import (
    CONFIG_PATH,
    load_config,
    obs_port_open,
    get_obs_status,
    process_running_contains,
    process_name_running,
)

from sss_event_history import (
    mark_clean_shutdown,
    record_event,
    start_session,
    update_session_heartbeat,
)

from sss_reliability import (
    FREEZE_FILE,
    POST_STATUS_FILE,
    AUDIO_STATUS_FILE,
    LOG_ROOT,
    atomic_json,
    read_json,
    set_freeze,
    is_frozen,
    append_system_log,
    weekly_snapshot,
    find_full_sermon_recording,
    now_local,
)

from sermon_chapter_manager import (
    next_button_text,
    reset_rotation,
    fire_next,
    fire_item,
    load_rotation,
)

from ptz_settings import (
    PTZ_CONFIG_FILE,
    load_ptz_settings,
    save_ptz_settings,
)

from sss_profile import (
    ensure_active_profile,
    get_profile_audio_settings,
    get_profile_camera_settings,
    get_profile_capabilities,
    get_profile_obs_settings,
    get_profile_presentation_settings,
    get_profile_sermon_source_settings,
    load_active_profile,
    profile_display_name,
    set_windows_app_user_model_id,
)

from sss_audio_adapters import (
    get_profile_mute_states,
    profile_audio_ready,
    toggle_profile_mute,
)

from sss_camera_adapters import (
    profile_camera_ready,
    recall_profile_camera_preset,
)

from sss_obs_profile import (
    load_scene_to_preview,
)

from sss_presentation_adapters import (
    next_slide_profile,
    previous_slide_profile,
    profile_adapter_ready,
)

from sss_sermon_sources import (
    materialize_profile_sermon_plan,
    profile_sermon_source_ready,
)

from sss_secrets_vault import (
    connect_obs_with_vault,
)

from sss_runtime import (
    launch_settings,
)

from sss_build_info import (
    APP_ID,
    APP_VERSION,
)

from sss_update_feed import (
    check_release_feed,
    load_feed_state,
    save_feed_state,
)




from sss_scripture_reading import (
    parse_scripture_reference,
    midi_port_available,
    presenter_next,
    presenter_back,
    send_webcam_tp_to_preview,
    send_webcam_only,
    send_studio_transition,
)


BASE = Path(
    r"C:\Church\SermonAI"
)

CHURCH_WINDOW_ICON = (
    BASE
    /
    "church_shortcut_icon.ico"
)

BRIDGE_STATUS = (
    BASE
    /
    "chapter_bridge_status.json"
)

BRIDGE_SCRIPT = (
    BASE
    /
    "core"
    /
    "chapter_bridge.py"
)

ACTION_SCRIPT = (
    BASE
    /
    "sunday_action.py"
)

OBS_CLEANUP_SCRIPT = (
    BASE
    /
    "core"
    /
    "obs_startup_cleanup.py"
)


GMAIL_IMPORTER = (
    BASE
    /
    "core"
    /
    "gmail_sermon_importer.py"
)

SERMON_PLAN_FILE = (
    BASE
    /
    "sermon_plan.json"
)

SERMON_PLAN_SYNC = (
    BASE
    /
    "core"
    /
    "sync_sermon_plan_to_lower_thirds.py"
)

PLANNING_UPDATE_SCRIPT = (
    BASE
    /
    "core"
    /
    "planning_update_sermon.py"
)

PLANNING_STATUS_FILE = (
    BASE
    /
    "planning_update_status.json"
)

YOUTUBE_UPLOAD_SCRIPT = (
    BASE
    /
    "core"
    /
    "youtube_studio_upload_worker.py"
)

YOUTUBE_STATUS_FILE = (
    BASE
    /
    "youtube_upload_status.json"
)

YOUTUBE_HISTORY_FILE = (
    BASE
    /
    "youtube_upload_history.json"
)

POST_SERVICE_SCRIPT = (
    BASE
    /
    "core"
    /
    "post_service_supervisor.py"
)

AUDIO_SANITY_SCRIPT = (
    BASE
    /
    "core"
    /
    "audio_sanity_monitor.py"
)

WEEKLY_SNAPSHOT_SCRIPT = (
    BASE
    /
    "core"
    /
    "weekly_snapshot.py"
)

TEST_MODE_SCRIPT = (
    BASE
    /
    "core"
    /
    "sss_test_mode.py"
)

OPERATIONAL_CLEANUP_SCRIPT = (
    BASE
    /
    "core"
    /
    "operational_cleanup.py"
)

YOUTUBE_STUDIO_LOGIN = (
    BASE
    /
    "tools"
    /
    "Open-YouTube-Studio-Normal-Login.bat"
)

PTZ_CAMERA_SCRIPT = (
    BASE
    /
    "ptz_camera_control.py"
)

PTZ_CAMERA_STATUS = (
    BASE
    /
    "ptz_camera_status.json"
)

CHAPTER_HOTKEY_SYNC_SCRIPT = (
    BASE
    /
    "core"
    /
    "sync_named_chapter_hotkeys.py"
)

CHAPTER_HOTKEY_SYNC_STATUS = (
    BASE
    /
    "chapter_hotkey_sync_status.json"
)

CHAPTER_ROTATION_STATE = (
    BASE
    /
    "chapter_rotation_state.json"
)


def get_startup_work_area(
    root
):
    """
    Return left, top, width, height for the usable monitor where the mouse
    cursor currently is.

    On Windows this uses that monitor's WORK AREA, so the taskbar is excluded.
    On other platforms it falls back to Tk's screen dimensions.
    """
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class POINT(
                ctypes.Structure
            ):
                _fields_ = [
                    (
                        "x",
                        wintypes.LONG
                    ),
                    (
                        "y",
                        wintypes.LONG
                    ),
                ]

            class RECT(
                ctypes.Structure
            ):
                _fields_ = [
                    (
                        "left",
                        wintypes.LONG
                    ),
                    (
                        "top",
                        wintypes.LONG
                    ),
                    (
                        "right",
                        wintypes.LONG
                    ),
                    (
                        "bottom",
                        wintypes.LONG
                    ),
                ]

            class MONITORINFO(
                ctypes.Structure
            ):
                _fields_ = [
                    (
                        "cbSize",
                        wintypes.DWORD
                    ),
                    (
                        "rcMonitor",
                        RECT
                    ),
                    (
                        "rcWork",
                        RECT
                    ),
                    (
                        "dwFlags",
                        wintypes.DWORD
                    ),
                ]

            user32 = ctypes.windll.user32

            point = POINT()

            if not user32.GetCursorPos(
                ctypes.byref(
                    point
                )
            ):
                raise RuntimeError(
                    "GetCursorPos failed."
                )

            MONITOR_DEFAULTTONEAREST = 2

            monitor = user32.MonitorFromPoint(
                point,
                MONITOR_DEFAULTTONEAREST,
            )

            if not monitor:
                raise RuntimeError(
                    "MonitorFromPoint failed."
                )

            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(
                MONITORINFO
            )

            if not user32.GetMonitorInfoW(
                monitor,
                ctypes.byref(
                    info
                ),
            ):
                raise RuntimeError(
                    "GetMonitorInfoW failed."
                )

            work = info.rcWork

            width = max(
                1,
                int(
                    work.right
                    -
                    work.left
                )
            )

            height = max(
                1,
                int(
                    work.bottom
                    -
                    work.top
                )
            )

            return (
                int(
                    work.left
                ),
                int(
                    work.top
                ),
                width,
                height,
            )

        except Exception:
            pass

    return (
        0,
        0,
        int(
            root.winfo_screenwidth()
        ),
        int(
            root.winfo_screenheight()
        ),
    )


class HoverTooltip:
    """Small volunteer-friendly hover tooltip for Tk/ttk widgets."""

    def __init__(
        self,
        widget,
        text,
        *,
        delay=450,
        wraplength=360,
        on_show=None
    ):
        self.widget = widget
        self.text = str(text or "")
        self.delay = int(delay)
        self.wraplength = int(wraplength)
        self.on_show = on_show
        self.after_id = None
        self.tip_window = None

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, event=None):
        self._cancel()

        if callable(self.on_show):
            try:
                self.on_show(self.text)
            except Exception:
                pass

        try:
            self.after_id = self.widget.after(
                self.delay,
                self._show,
            )
        except Exception:
            self.after_id = None

    def _cancel(self):
        if self.after_id is not None:
            try:
                self.widget.after_cancel(self.after_id)
            except Exception:
                pass

            self.after_id = None

    def _show(self):
        self.after_id = None

        if not self.text or self.tip_window is not None:
            return

        try:
            # Keep the popup fixed relative to the control rather than
            # following the mouse pointer.
            x = self.widget.winfo_rootx() + 8
            y = (
                self.widget.winfo_rooty()
                +
                self.widget.winfo_height()
                +
                4
            )

            tip = tk.Toplevel(self.widget)
            self.tip_window = tip
            tip.wm_overrideredirect(True)

            try:
                tip.attributes("-topmost", True)
            except Exception:
                pass

            tip.geometry(f"+{x}+{y}")

            frame = tk.Frame(
                tip,
                background="#FFF7D6",
                borderwidth=1,
                relief="solid",
            )
            frame.pack()

            tk.Label(
                frame,
                text=self.text,
                justify="left",
                anchor="w",
                wraplength=self.wraplength,
                padx=8,
                pady=6,
                background="#FFF7D6",
                foreground="#202020",
                font=("Segoe UI", 9),
            ).pack()

        except Exception:
            self.tip_window = None

    def _hide(self, event=None):
        self._cancel()

        if self.tip_window is not None:
            try:
                self.tip_window.destroy()
            except Exception:
                pass

            self.tip_window = None


class SundayModeApp:
    def __init__(
        self,
        root
    ):
        self.root = root
        self.root.title(
            "Sunday Service System"
        )

        # Replace Tk's default feather icon with the church icon.
        # Using "default=" also applies it to child/Toplevel windows.
        if CHURCH_WINDOW_ICON.exists():
            try:
                self.root.iconbitmap(
                    default=str(
                        CHURCH_WINDOW_ICON
                    )
                )
            except Exception:
                pass

        (
            work_left,
            work_top,
            work_width,
            work_height,
        ) = get_startup_work_area(
            self.root
        )

        # Smart initial sizing:
        #
        # - use the monitor where the mouse is
        # - exclude that monitor's taskbar
        # - leave some desktop breathing room
        # - let the existing responsive UI shrink/grow the controls to fit
        #
        # This avoids the oversized / oddly positioned first launch that can
        # happen on mixed-size or mixed-DPI multi-monitor church PCs.
        window_width = min(
            1280,
            max(
                1020,
                int(
                    work_width
                    *
                    0.75
                )
            )
        )

        window_height = min(
            860,
            max(
                740,
                int(
                    work_height
                    *
                    0.84
                )
            )
        )

        # Never exceed the usable monitor work area.
        window_width = min(
            window_width,
            max(
                860,
                work_width
                -
                48
            ),
        )

        window_height = min(
            window_height,
            max(
                720,
                work_height
                -
                48
            ),
        )

        x_position = (
            work_left
            +
            max(
                0,
                int(
                    (
                        work_width
                        -
                        window_width
                    )
                    /
                    2
                )
            )
        )

        y_position = (
            work_top
            +
            max(
                0,
                int(
                    (
                        work_height
                        -
                        window_height
                    )
                    /
                    2
                )
            )
        )

        self.root.geometry(
            (
                f"{window_width}x{window_height}"
                f"+{x_position}+{y_position}"
            )
        )

        self.root.minsize(
            860,
            720
        )

        # 1200x840 is the "designed at 100%" SSS layout size.
        #
        # Do NOT use the initial window dimensions as the responsive baseline.
        # If the available monitor is a little shorter, doing that would keep
        # 100% fonts/padding and merely clip the bottom. Using a stable design
        # baseline lets the responsive layer immediately shrink everything to
        # fit on first launch, then grow it again when maximized.
        self._responsive_base_width = 1200
        self._responsive_base_height = 840
        self._responsive_scale = 1.0
        self._responsive_after_id = None
        self._responsive_fonts = []
        self._responsive_pixel_options = []
        self._responsive_geometry = []

        self.config = (
            load_config()
        )

        # Profile Layer v1 is compatibility-only. It creates/loads a portable
        # church profile container but deliberately does NOT override any
        # existing Sunday configuration yet.
        try:
            self.active_profile = ensure_active_profile()
            self.active_profile_name = profile_display_name()
        except Exception:
            self.active_profile = {}
            self.active_profile_name = "Legacy Configuration"

        try:
            self.previous_unexpected_session = start_session(
                profile_name=self.active_profile_name
            )
        except Exception:
            self.previous_unexpected_session = None

        self.profile_display_var = tk.StringVar(
            value=(
                "Profile: "
                +
                self.active_profile_name
            )
        )
        self.profile_display_label = None
        self.volunteer_button_frame = None
        self.workflow_label_widgets = {}
        self.end_service_hint = None

        self.service_commanded = False
        self.service_ending = False
        self.mute_state = False
        self.last_alarm_time = 0.0
        self.last_preflight_message = None
        self.planning_update_running = False
        self.preflight_running = False
        self.watchdog_running = False
        self.last_recording_state = None

        # Reliability / recovery state.
        self.recording_started_at = 0.0
        self.active_recording_path = ""
        self.last_recording_size = 0
        self.last_recording_growth_time = 0.0
        self.last_completion_plan_id = None
        self.admin_window = None
        self.admin_ptz_ip_var = None
        self.admin_ptz_worship_var = None
        self.admin_ptz_pastor_var = None

        # Admin-only Chapter / Lower-Third test mode. This uses a separate
        # in-memory chapter index so the real sermon chapter position is
        # never changed by testing.
        self.chapter_test_mode = False
        self.chapter_test_index = 0
        self.chapter_action_running = False
        self.admin_chapter_test_var = None
        self.admin_chapter_test_status_var = None

        # Scripture-reading control state. This runs Presenter from SSS and
        # uses the existing sermon plan Scripture reference.
        self.scripture_reading_active = False
        self.scripture_reading_busy = False
        self.scripture_reference = ""
        self.scripture_verses = []
        self.scripture_verses_exact = False
        self.scripture_verse_index = -1

        # Collapsible preflight dashboard state.
        self.preflight_expanded = True
        self.preflight_header_button = None
        self.preflight_content = None

        # Collapsible Sunday Log state.
        self.sunday_log_expanded = False
        self.sunday_log_header_button = None
        self.sunday_log_content = None

        # Background workers never call Tk directly.  They post work
        # into this queue and the main Tk thread drains it.
        self.ui_queue = queue.Queue()

        self.status_vars = {}
        self.status_labels = {}
        self.status_detail_text = {}
        self.status_detail_var = None

        # Live program-audio meter. The separate audio_sanity_monitor.py
        # sends instantaneous levels over localhost UDP; the existing
        # status JSON remains a 1-second fallback.
        self.audio_meter_canvas = None
        self.audio_meter_db_var = None
        self.audio_meter_db_label = None
        self.audio_meter_issue_var = None
        self.audio_meter_issue_label = None
        self.audio_meter_latest = {}
        self.audio_meter_last_packet = 0.0
        self.audio_meter_listener_started = False

        # Meter animation state. The raw OBS peak can jump violently from
        # packet to packet, so the dashboard uses a fast attack and slower
        # release for a calmer, easier-to-read meter.
        self.audio_meter_target_db = -60.0
        self.audio_meter_display_db = -60.0

        self.build_ui()

        try:
            self.root.protocol(
                "WM_DELETE_WINDOW",
                self.on_app_close,
            )
        except Exception:
            pass

        # Capture the finished 100% layout once, then scale it whenever the
        # main SSS window changes size. This works with the normal Windows
        # maximize/restore buttons and with manual resizing.
        self.root.update_idletasks()
        self._capture_responsive_layout()
        self.root.bind(
            "<Configure>",
            self._on_responsive_configure,
            add="+",
        )
        self._schedule_responsive_scale(
            immediate=True
        )

        # Windows can report the final client size a fraction of a second
        # after creating the window (especially across mixed-DPI monitors).
        # Re-apply once after launch so first-open sizing matches what you get
        # after manually maximize/restore.
        self.root.after(
            250,
            self._apply_responsive_scale,
        )

        self.root.bind(
            "<FocusIn>",
            self.refresh_active_profile_label,
            add="+",
        )

        self.root.after(
            5000,
            self.check_for_update_notification,
        )

        self.start_live_audio_meter_listener()

        self.root.after(
            100,
            self.refresh_live_audio_meter
        )

        self.root.after(
            100,
            self.drain_ui_queue
        )

        self.root.after(
            1800,
            self.session_heartbeat
        )

        if self.previous_unexpected_session:
            self.root.after(
                3600,
                self.show_startup_recovery_notice
            )

        self.append_log(
            "Sunday Service System ready."
        )

        # Create a weekly rollback snapshot before the Sunday workflow
        # begins changing plan/status files.
        if self.config.get(
            "auto_weekly_snapshot",
            True
        ):
            try:
                destination = weekly_snapshot(
                    retention_weeks=int(
                        self.config.get(
                            "weekly_backup_retention_weeks",
                            12
                        )
                    ),
                    phase="pre_start",
                )

                self.append_log(
                    "Pre-start rollback snapshot ready: "
                    f"{destination.parent.name}"
                )

            except Exception as exc:
                self.append_log(
                    "Pre-start snapshot warning: "
                    f"{exc}"
                )

        self.start_sermon_plan_services()
        self.refresh_chapter_rotation_button(
            reset_if_plan_changed=True
        )

        if self.config.get(
            "auto_weekly_snapshot",
            True
        ):
            self.start_weekly_snapshot_async(
                "current"
            )
        self.launch_background_helpers()
        self.start_obs_cleanup_helper()
        self.start_audio_sanity_monitor()
        self.ensure_obs_running()

        if self.config.get(
            "auto_start_presenter",
            True
        ):
            self.ensure_presenter_running()

        # Put the PTZ camera on the pastor shot when SSS opens.
        # PTZ settings are stored separately from sunday_config.json so
        # normal SSS updates cannot erase the camera address/presets.
        ptz_settings = self.get_ptz_settings()

        if (
            ptz_settings.get(
                "ptz_camera_enabled",
                True
            )
            and
            ptz_settings.get(
                "ptz_auto_recall_on_sss_start",
                True
            )
            and
            str(
                ptz_settings.get(
                    "ptz_camera_ip",
                    ""
                )
            ).strip()
        ):
            self.root.after(
                1800,
                self.ptz_startup_position
            )

        # Planning updates do not need to delay OBS startup. Run the
        # date-guarded Scripture sync in the background.
        if self.config.get(
            "auto_update_planning_scripture",
            True
        ):
            self.root.after(
                600,
                self.update_planning_async
            )

        self.root.after(
            1200,
            self.run_preflight_async
        )

        # If Windows/SSS restarted after a service, recover unfinished
        # post-service work instead of relying on someone to remember it.
        if self.config.get(
            "post_service_auto_resume",
            True
        ):
            self.root.after(
                5000,
                self.resume_pending_post_service
            )

        refresh_ms = int(
            float(
                self.config.get(
                    "dashboard_refresh_seconds",
                    5
                )
            )
            *
            1000
        )

        self.root.after(
            refresh_ms,
            self.periodic_refresh
        )

    def post_ui(
        self,
        callback,
        *args,
        **kwargs
    ):
        """
        Queue a UI operation for the Tk main thread.

        This avoids calling Tkinter from background worker threads,
        which can cause native pythonw/_tkinter crashes on Windows.
        """
        self.ui_queue.put(
            (
                callback,
                args,
                kwargs,
            )
        )

    def drain_ui_queue(
        self
    ):
        try:
            while True:
                callback, args, kwargs = (
                    self.ui_queue.get_nowait()
                )

                try:
                    callback(
                        *args,
                        **kwargs
                    )
                except Exception as exc:
                    # Keep the UI alive even if one queued update fails.
                    try:
                        self.append_log(
                            f"UI update warning: {exc}"
                        )
                    except Exception:
                        pass

        except queue.Empty:
            pass

        try:
            self.root.after(
                100,
                self.drain_ui_queue
            )
        except Exception:
            pass

    def _walk_main_widgets(
        self,
        parent=None
    ):
        if parent is None:
            parent = self.root

        widgets = []

        try:
            children = parent.winfo_children()
        except Exception:
            children = []

        for child in children:
            # Do not capture transient top-level windows such as Admin.
            try:
                if isinstance(
                    child,
                    tk.Toplevel
                ):
                    continue
            except Exception:
                pass

            widgets.append(
                child
            )
            widgets.extend(
                self._walk_main_widgets(
                    child
                )
            )

        return widgets

    def _scale_tcl_values(
        self,
        value,
        scale,
        *,
        minimum=0
    ):
        """
        Scale Tk/Ttk pixel values such as:
          14
          "0 8 0 0"
          (4, 8)
        """
        try:
            parts = self.root.tk.splitlist(
                value
            )
        except Exception:
            parts = (
                value,
            )

        scaled = []

        for part in parts:
            try:
                number = float(
                    part
                )
            except Exception:
                return value

            sign = (
                -1
                if number < 0
                else
                1
            )

            amount = max(
                minimum,
                int(
                    round(
                        abs(
                            number
                        )
                        *
                        scale
                    )
                ),
            )

            scaled.append(
                sign
                *
                amount
            )

        if len(
            scaled
        ) == 1:
            return scaled[
                0
            ]

        return tuple(
            scaled
        )

    def _capture_responsive_layout(
        self
    ):
        """
        Capture the current UI as the 100% layout.

        We make private Font objects for widgets that use explicit fonts,
        allowing their point sizes to grow/shrink without rebuilding SSS.
        Pixel-only UI pieces (wrap lengths, canvas heights, frame padding,
        and grid/pack spacing) are also captured.
        """
        self._responsive_fonts = []
        self._responsive_pixel_options = []
        self._responsive_geometry = []

        widgets = self._walk_main_widgets()

        for widget in widgets:
            # -------------------------------------------------------------
            # Explicit widget fonts
            # -------------------------------------------------------------
            try:
                keys = widget.keys()
            except Exception:
                keys = []

            if "font" in keys:
                try:
                    font_spec = widget.cget(
                        "font"
                    )
                except Exception:
                    font_spec = ""

                if font_spec:
                    try:
                        source_font = tkfont.Font(
                            root=self.root,
                            font=font_spec,
                        )

                        actual = source_font.actual()
                        base_size = int(
                            actual.get(
                                "size",
                                9
                            )
                        )

                        # Negative Tk font sizes are pixel sizes. Preserve the
                        # sign while scaling the magnitude.
                        font_obj = tkfont.Font(
                            root=self.root,
                            family=actual.get(
                                "family",
                                "Segoe UI"
                            ),
                            size=base_size,
                            weight=actual.get(
                                "weight",
                                "normal"
                            ),
                            slant=actual.get(
                                "slant",
                                "roman"
                            ),
                            underline=actual.get(
                                "underline",
                                0
                            ),
                            overstrike=actual.get(
                                "overstrike",
                                0
                            ),
                        )

                        widget.configure(
                            font=font_obj
                        )

                        self._responsive_fonts.append(
                            (
                                font_obj,
                                base_size,
                            )
                        )

                    except Exception:
                        pass

            # -------------------------------------------------------------
            # Pixel-sized widget options
            # -------------------------------------------------------------
            for option in (
                "wraplength",
                "padding",
            ):
                if option not in keys:
                    continue

                try:
                    original = widget.cget(
                        option
                    )
                except Exception:
                    continue

                try:
                    parts = self.root.tk.splitlist(
                        original
                    )
                except Exception:
                    parts = (
                        original,
                    )

                numeric = True

                for part in parts:
                    try:
                        float(
                            part
                        )
                    except Exception:
                        numeric = False
                        break

                if not numeric:
                    continue

                # A zero wraplength means "disabled"; leave it alone.
                if (
                    option == "wraplength"
                    and
                    len(parts) == 1
                    and
                    float(
                        parts[0]
                    ) <= 0
                ):
                    continue

                self._responsive_pixel_options.append(
                    (
                        widget,
                        option,
                        original,
                    )
                )

            # tk.Frame / tk.Canvas explicit heights are pixels and should
            # follow the UI scale. Do not touch text-unit button/label widths.
            try:
                widget_class = widget.winfo_class()
            except Exception:
                widget_class = ""

            if widget_class in (
                "Frame",
                "Canvas",
            ):
                for option in (
                    "height",
                ):
                    if option not in keys:
                        continue

                    try:
                        original = int(
                            float(
                                widget.cget(
                                    option
                                )
                            )
                        )
                    except Exception:
                        continue

                    if original > 1:
                        self._responsive_pixel_options.append(
                            (
                                widget,
                                option,
                                original,
                            )
                        )

            # -------------------------------------------------------------
            # Geometry-manager spacing
            # -------------------------------------------------------------
            manager = ""

            try:
                manager = widget.winfo_manager()
            except Exception:
                pass

            if manager == "pack":
                try:
                    info = widget.pack_info()
                except Exception:
                    info = {}

                captured = {}

                for option in (
                    "padx",
                    "pady",
                    "ipadx",
                    "ipady",
                ):
                    if option in info:
                        captured[
                            option
                        ] = info[
                            option
                        ]

                if captured:
                    self._responsive_geometry.append(
                        (
                            widget,
                            "pack",
                            captured,
                        )
                    )

            elif manager == "grid":
                try:
                    info = widget.grid_info()
                except Exception:
                    info = {}

                captured = {}

                for option in (
                    "padx",
                    "pady",
                    "ipadx",
                    "ipady",
                ):
                    if option in info:
                        captured[
                            option
                        ] = info[
                            option
                        ]

                if captured:
                    self._responsive_geometry.append(
                        (
                            widget,
                            "grid",
                            captured,
                        )
                    )

    def _responsive_target_scale(
        self
    ):
        try:
            width = max(
                1,
                int(
                    self.root.winfo_width()
                )
            )

            height = max(
                1,
                int(
                    self.root.winfo_height()
                )
            )
        except Exception:
            return 1.0

        width_scale = (
            width
            /
            max(
                1,
                self._responsive_base_width
            )
        )

        height_scale = (
            height
            /
            max(
                1,
                self._responsive_base_height
            )
        )

        # Fit to BOTH dimensions, so maximized/fullscreen SSS gets larger
        # without growing so much that the bottom controls fall off-screen.
        scale = min(
            width_scale,
            height_scale,
        )

        return max(
            0.78,
            min(
                1.50,
                scale,
            )
        )

    def _apply_responsive_scale(
        self
    ):
        self._responsive_after_id = None

        scale = self._responsive_target_scale()

        if abs(
            scale
            -
            self._responsive_scale
        ) < 0.015:
            return

        self._responsive_scale = scale

        # Font sizes
        for font_obj, base_size in self._responsive_fonts:
            try:
                sign = (
                    -1
                    if base_size < 0
                    else
                    1
                )

                magnitude = max(
                    7,
                    int(
                        round(
                            abs(
                                base_size
                            )
                            *
                            scale
                        )
                    ),
                )

                font_obj.configure(
                    size=sign
                    *
                    magnitude
                )
            except Exception:
                pass

        # Widget pixel options
        for (
            widget,
            option,
            original,
        ) in self._responsive_pixel_options:
            try:
                scaled = self._scale_tcl_values(
                    original,
                    scale,
                    minimum=0,
                )

                widget.configure(
                    **{
                        option: scaled
                    }
                )
            except Exception:
                pass

        # Grid / pack spacing
        for (
            widget,
            manager,
            captured,
        ) in self._responsive_geometry:
            options = {}

            for option, original in captured.items():
                try:
                    options[
                        option
                    ] = self._scale_tcl_values(
                        original,
                        scale,
                        minimum=0,
                    )
                except Exception:
                    pass

            if not options:
                continue

            try:
                if manager == "pack":
                    widget.pack_configure(
                        **options
                    )
                elif manager == "grid":
                    widget.grid_configure(
                        **options
                    )
            except Exception:
                pass

        # Redraw the audio meter immediately so its visual proportions match
        # the newly scaled canvas.
        try:
            self.draw_live_audio_meter(
                self.audio_meter_display_db
            )
        except Exception:
            pass

    def _schedule_responsive_scale(
        self,
        *,
        immediate=False
    ):
        try:
            if self._responsive_after_id is not None:
                self.root.after_cancel(
                    self._responsive_after_id
                )
        except Exception:
            pass

        delay = (
            0
            if immediate
            else
            90
        )

        try:
            self._responsive_after_id = self.root.after(
                delay,
                self._apply_responsive_scale,
            )
        except Exception:
            self._responsive_after_id = None

    def _on_responsive_configure(
        self,
        event=None
    ):
        # <Configure> also fires for child widgets. Only react to changes to
        # the main root window itself.
        if (
            event is not None
            and
            getattr(
                event,
                "widget",
                None
            )
            is not
            self.root
        ):
            return

        self._schedule_responsive_scale()

    def refresh_active_profile_label(
        self,
        event=None
    ):
        try:
            self.active_profile = ensure_active_profile()
            self.active_profile_name = profile_display_name()

            if self.profile_display_var is not None:
                self.profile_display_var.set(
                    "Profile: "
                    +
                    self.active_profile_name
                )

            try:
                self.apply_profile_capabilities()
            except Exception:
                pass

        except Exception as exc:
            self.append_log(
                (
                    "Profile label refresh warning: "
                    +
                    str(exc)
                )
            )

    def open_profile_manager(
        self
    ):
        try:
            launch_settings()

        except Exception as exc:
            messagebox.showwarning(
                'SSS Setup & Settings',
                (
                    'Could not open SSS Setup & Settings.'
                    +
                    "\n\n"
                    +
                    str(
                        exc
                    )
                ),
            )

    def check_for_update_notification(
        self
    ):
        def worker():
            try:
                skipped_version = str(
                    load_feed_state().get(
                        "skipped_version",
                        ""
                    )
                )

                result = check_release_feed(
                    current_version=APP_VERSION,
                )

                release = result.get(
                    "latest_release"
                )

                if (
                    not release
                    or
                    not result.get(
                        "update_available"
                    )
                    or
                    result.get(
                        "client_too_old"
                    )
                ):
                    return

                if str(
                    release.get(
                        "version",
                        ""
                    )
                ) == skipped_version:
                    return

                self.post_ui(
                    self.show_update_notification,
                    release,
                )

            except Exception:
                # Background courtesy check only - a misconfigured or
                # unreachable feed should never interrupt a live service.
                # Settings -> Updates still works for a manual check.
                pass

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def show_update_notification(
        self,
        release
    ):
        if getattr(
            self,
            "_update_notification_open",
            False
        ):
            return

        self._update_notification_open = True

        version = str(
            release.get(
                "version",
                ""
            )
        )

        summary = str(
            release.get(
                "summary",
                ""
            )
            or
            ""
        ).strip()

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "SSS Update Available"
        )

        window.transient(
            self.root
        )

        window.resizable(
            False,
            False
        )

        def on_close():
            self._update_notification_open = False

            try:
                window.destroy()
            except Exception:
                pass

        window.protocol(
            "WM_DELETE_WINDOW",
            on_close,
        )

        outer = ttk.Frame(
            window,
            padding=16,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            outer,
            text=(
                "Sunday Service System "
                +
                version
                +
                " is available."
            ),
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            outer,
            text=(
                "You're currently running "
                +
                str(
                    APP_VERSION
                )
                +
                "."
            ),
            font=(
                "Segoe UI",
                9,
            ),
        ).pack(
            anchor="w",
            pady=(
                2,
                10,
            ),
        )

        if summary:
            display_summary = summary

            if len(
                display_summary
            ) > 400:
                display_summary = (
                    display_summary[
                        :400
                    ].rstrip()
                    +
                    "…"
                )

            ttk.Label(
                outer,
                text=display_summary,
                font=(
                    "Segoe UI",
                    9,
                ),
                wraplength=380,
                justify="left",
            ).pack(
                anchor="w",
                pady=(
                    0,
                    12,
                ),
            )

        button_row = ttk.Frame(
            outer
        )

        button_row.pack(
            fill="x",
        )

        def do_update():
            on_close()

            try:
                launch_settings(
                    "--updates"
                )
            except Exception as exc:
                messagebox.showwarning(
                    "SSS Update",
                    (
                        "Could not open SSS Setup & Settings.\n\n"
                        +
                        str(
                            exc
                        )
                    ),
                )

        def do_skip():
            try:
                state = load_feed_state()
                state["skipped_version"] = version
                save_feed_state(
                    state
                )
            except Exception:
                pass

            on_close()

        ttk.Button(
            button_row,
            text="UPDATE NOW",
            command=do_update,
        ).pack(
            side="left",
            expand=True,
            fill="x",
            padx=(
                0,
                4,
            ),
        )

        ttk.Button(
            button_row,
            text="SKIP THIS VERSION",
            command=do_skip,
        ).pack(
            side="left",
            expand=True,
            fill="x",
            padx=4,
        )

        ttk.Button(
            button_row,
            text="REMIND ME LATER",
            command=on_close,
        ).pack(
            side="left",
            expand=True,
            fill="x",
            padx=(
                4,
                0,
            ),
        )

        window.update_idletasks()

        try:
            window.lift()
            window.focus_force()
        except Exception:
            pass

    def open_full_system_diagnostics(
        self
    ):
        try:
            launch_settings(
                '--diagnostics'
            )

        except Exception as exc:
            messagebox.showwarning(
                'SSS Diagnostics',
                (
                    'Could not open Full System Diagnostics.'
                    +
                    "\n\n"
                    +
                    str(
                        exc
                    )
                ),
            )

    def open_recovery_center(
        self
    ):
        # Folded in here so a standalone "Run Weekly Snapshot" admin
        # button is not needed: opening Recovery always makes sure a
        # fresh weekly rollback snapshot exists too.
        self.start_weekly_snapshot_async()

        try:
            launch_settings(
                '--recovery'
            )

        except Exception as exc:
            messagebox.showwarning(
                'SSS Recovery',
                (
                    'Could not open Backup / Recovery.'
                    +
                    "\n\n"
                    +
                    str(
                        exc
                    )
                ),
            )

    def open_event_history(
        self
    ):
        try:
            launch_settings(
                '--history'
            )

        except Exception as exc:
            messagebox.showwarning(
                'SSS Event History',
                (
                    'Could not open Event History.'
                    +
                    "\n\n"
                    +
                    str(
                        exc
                    )
                ),
            )

    def session_heartbeat(
        self
    ):
        """
        Keep a tiny session marker current so a future SSS launch can tell the
        difference between a normal close and an unexpected shutdown.

        This reads OBS status only. It never starts/stops an output.
        """
        recording = None
        streaming = None

        try:
            client = self.connect_obs()

            if client is not None:
                status = get_obs_status(
                    client
                )

                recording = bool(
                    status.get(
                        "recording",
                        False
                    )
                )

                streaming = bool(
                    status.get(
                        "streaming",
                        False
                    )
                )

        except Exception:
            pass

        try:
            update_session_heartbeat(
                recording=recording,
                streaming=streaming,
                profile_name=self.active_profile_name,
            )
        except Exception:
            pass

        try:
            self.root.after(
                15000,
                self.session_heartbeat,
            )
        except Exception:
            pass

    def on_app_close(
        self
    ):
        """
        Record a normal shutdown and leave all live OBS outputs untouched.
        """
        try:
            client = self.connect_obs()

            if client is not None:
                status = get_obs_status(
                    client
                )

                update_session_heartbeat(
                    recording=bool(
                        status.get(
                            "recording",
                            False
                        )
                    ),
                    streaming=bool(
                        status.get(
                            "streaming",
                            False
                        )
                    ),
                    last_event=(
                        "SSS window closed normally; OBS outputs were left unchanged."
                    ),
                    profile_name=self.active_profile_name,
                )

        except Exception:
            pass

        try:
            mark_clean_shutdown(
                detail=(
                    "Sunday Service System closed normally. "
                    "OBS outputs were left unchanged."
                )
            )
        except Exception:
            pass

        try:
            self.root.destroy()
        except Exception:
            pass

    def show_startup_recovery_notice(
        self
    ):
        previous = self.previous_unexpected_session

        if not isinstance(
            previous,
            dict
        ) or not previous:
            return

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "Sunday Service System — Startup Recovery"
        )

        window.geometry(
            "720x560"
        )

        window.minsize(
            650,
            500,
        )

        try:
            window.transient(
                self.root
            )
            window.grab_set()
        except Exception:
            pass

        outer = ttk.Frame(
            window,
            padding=18,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            outer,
            text="STARTUP RECOVERY",
            font=(
                "Segoe UI",
                18,
                "bold"
            ),
        ).pack(
            anchor="w",
            pady=(
                0,
                6
            ),
        )

        ttk.Label(
            outer,
            text=(
                "The previous SSS session did not record a normal shutdown. "
                "This can happen after a crash, forced restart, power loss, or "
                "ending pythonw from Task Manager."
            ),
            wraplength=670,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                0,
                12
            ),
        )

        detail_frame = ttk.LabelFrame(
            outer,
            text="Previous Session",
            padding=10,
        )

        detail_frame.pack(
            fill="x",
            pady=(
                0,
                12
            ),
        )

        recording = previous.get(
            "recording"
        )

        streaming = previous.get(
            "streaming"
        )

        def state_text(
            value
        ):
            if value is True:
                return "ACTIVE"
            if value is False:
                return "stopped"
            return "unknown"

        previous_text = (
            "Started: "
            +
            str(
                previous.get(
                    "started_at",
                    "unknown"
                )
            )
            +
            "\nLast heartbeat: "
            +
            str(
                previous.get(
                    "heartbeat_at",
                    "unknown"
                )
            )
            +
            "\nLast event: "
            +
            str(
                previous.get(
                    "last_event",
                    "(none recorded)"
                )
            )
            +
            "\nRecording at last heartbeat: "
            +
            state_text(
                recording
            )
            +
            "\nStreaming at last heartbeat: "
            +
            state_text(
                streaming
            )
        )

        ttk.Label(
            detail_frame,
            text=previous_text,
            wraplength=640,
            justify="left",
        ).pack(
            anchor="w"
        )

        if (
            recording is True
            or
            streaming is True
        ):
            ttk.Label(
                outer,
                text=(
                    "IMPORTANT: the previous session reported a live OBS output. "
                    "SSS will NOT stop it automatically. Verify OBS before taking "
                    "any recovery action."
                ),
                wraplength=670,
                justify="left",
                font=(
                    "Segoe UI",
                    10,
                    "bold"
                ),
            ).pack(
                anchor="w",
                pady=(
                    0,
                    12
                ),
            )

        ttk.Label(
            outer,
            text=(
                "Nothing below changes the live service automatically. You can "
                "continue normally, inspect Diagnostics, open Backup / Recovery, "
                "or review the event timeline."
            ),
            wraplength=670,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                0,
                12
            ),
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x",
            side="bottom",
        )

        for column in range(
            2
        ):
            buttons.columnconfigure(
                column,
                weight=1
            )

        def close_and(
            callback=None
        ):
            try:
                window.grab_release()
            except Exception:
                pass

            try:
                window.destroy()
            except Exception:
                pass

            if callable(
                callback
            ):
                callback()

        ttk.Button(
            buttons,
            text="CONTINUE SUNDAY MODE",
            command=lambda:
                close_and(),
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
            pady=4,
        )

        ttk.Button(
            buttons,
            text="RUN FULL SYSTEM DIAGNOSTICS",
            command=lambda:
                close_and(
                    self.open_full_system_diagnostics
                ),
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
            pady=4,
        )

        ttk.Button(
            buttons,
            text="OPEN BACKUP / RECOVERY",
            command=lambda:
                close_and(
                    self.open_recovery_center
                ),
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
            pady=4,
        )

        ttk.Button(
            buttons,
            text="VIEW EVENT HISTORY",
            command=lambda:
                close_and(
                    self.open_event_history
                ),
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
            pady=4,
        )

        try:
            window.protocol(
                "WM_DELETE_WINDOW",
                lambda:
                    close_and(),
            )
        except Exception:
            pass

    def open_security_center(
        self
    ):
        try:
            launch_settings(
                '--security'
            )

        except Exception as exc:
            messagebox.showwarning(
                'SSS Security',
                (
                    'Could not open Security / Secrets Vault.'
                    +
                    "\n\n"
                    +
                    str(
                        exc
                    )
                ),
            )

    def open_updates_center(
        self
    ):
        try:
            launch_settings(
                "--updates"
            )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Updates",
                (
                    "Could not open Application Updates."
                    +
                    "\n\n"
                    +
                    str(
                        exc
                    )
                ),
            )

    def _set_workflow_row_visible(
        self,
        row,
        visible
    ):
        frame = self.volunteer_button_frame

        if frame is None:
            return

        try:
            widgets = frame.grid_slaves(
                row=row
            )
        except Exception:
            widgets = []

        for widget in widgets:
            try:
                if visible:
                    widget.grid()
                else:
                    widget.grid_remove()
            except Exception:
                pass

    def apply_profile_capabilities(
        self
    ):
        """
        Capability-based volunteer UI.

        LEGACY = preserve the complete existing six-step workflow.
        PROFILE = hide controls this church does not use.

        Visibility only: this function never starts/stops OBS, recording,
        streaming, presentation, cameras, or any other integration.
        """
        if self.volunteer_button_frame is None:
            return

        try:
            capabilities = get_profile_capabilities(
                load_active_profile()
            )
        except Exception:
            capabilities = {
                "settings_source": "legacy",
                "recording": True,
                "streaming": True,
                "audio_mute": True,
                "scripture": True,
                "sermon_controls": True,
                "camera_controls": True,
            }

        recording = bool(
            capabilities.get(
                "recording",
                True
            )
        )
        streaming = bool(
            capabilities.get(
                "streaming",
                True
            )
        )
        audio_mute = bool(
            capabilities.get(
                "audio_mute",
                True
            )
        )
        scripture = bool(
            capabilities.get(
                "scripture",
                True
            )
        )
        sermon = bool(
            capabilities.get(
                "sermon_controls",
                True
            )
        )
        camera = bool(
            capabilities.get(
                "camera_controls",
                True
            )
        )

        try:
            audio_settings = get_profile_audio_settings(
                load_active_profile()
            )

            if (
                audio_settings.get(
                    "settings_source"
                )
                ==
                "profile"
                and
                audio_settings.get(
                    "provider"
                )
                ==
                "None"
            ):
                audio_mute = False

        except Exception:
            pass

        try:
            camera_settings = get_profile_camera_settings(
                load_active_profile()
            )

            if (
                camera_settings.get(
                    "settings_source"
                )
                ==
                "profile"
                and
                camera_settings.get(
                    "provider"
                )
                in {
                    "Fixed camera",
                    "None",
                }
            ):
                camera = False

        except Exception:
            pass

        visible_rows = {
            0: True,
            1: (
                recording
                or
                streaming
                or
                audio_mute
            ),
            2: scripture,
            3: sermon,
            4: camera,
            5: (
                recording
                or
                streaming
            ),
        }

        for row, visible in visible_rows.items():
            self._set_workflow_row_visible(
                row,
                visible
            )

        # When only one of recording/streaming is enabled for this church,
        # its buttons take over column 1 (the prominent slot) instead of
        # leaving an empty gap where the disabled one used to sit.
        stream_start_column = (
            1
            if (
                streaming
                and
                not recording
            )
            else 2
        )

        record_stop_column = (
            1
            if (
                recording
                and
                not streaming
            )
            else 2
        )

        for widget, visible, row, column in (
            (
                getattr(
                    self,
                    "record_start_button",
                    None
                ),
                recording,
                1,
                1,
            ),
            (
                getattr(
                    self,
                    "stream_start_button",
                    None
                ),
                streaming,
                1,
                stream_start_column,
            ),
            (
                getattr(
                    self,
                    "mute_button",
                    None
                ),
                audio_mute,
                1,
                3,
            ),
            (
                getattr(
                    self,
                    "stream_stop_button",
                    None
                ),
                streaming,
                5,
                1,
            ),
            (
                getattr(
                    self,
                    "record_stop_button",
                    None
                ),
                recording,
                5,
                record_stop_column,
            ),
        ):
            if widget is None:
                continue

            try:
                if visible:
                    widget.grid(
                        row=row,
                        column=column,
                        padx=4,
                        pady=4,
                        sticky="ew",
                    )
                else:
                    widget.grid_remove()
            except Exception:
                pass

        if self.end_service_hint is not None:
            try:
                if recording and streaming:
                    self.end_service_hint.configure(
                        text="Stream first, then Recording"
                    )
                    self.end_service_hint.grid()
                elif recording:
                    self.end_service_hint.configure(
                        text="Finish by stopping Recording"
                    )
                    self.end_service_hint.grid()
                elif streaming:
                    self.end_service_hint.configure(
                        text="Finish by stopping Stream"
                    )
                    self.end_service_hint.grid()
                else:
                    self.end_service_hint.grid_remove()
            except Exception:
                pass

        titles = {
            0: "SERVICE PREP",
            1: "LIVE A/V",
            2: "SCRIPTURE",
            3: "SERMON",
            4: "CAMERA VIEW",
            5: "END SERVICE",
        }

        next_number = 1

        for row in range(
            6
        ):
            label = self.workflow_label_widgets.get(
                row
            )

            if label is None:
                continue

            if visible_rows.get(
                row,
                False
            ):
                try:
                    label.configure(
                        text=(
                            str(
                                next_number
                            )
                            +
                            " — "
                            +
                            titles[
                                row
                            ]
                        )
                    )
                except Exception:
                    pass

                next_number += 1

        try:
            self.volunteer_button_frame.configure(
                text=(
                    "Volunteer Controls — Follow 1 → "
                    +
                    str(
                        max(
                            1,
                            next_number
                            -
                            1
                        )
                    )
                )
            )
        except Exception:
            pass

    def build_ui(
        self
    ):
        outer = ttk.Frame(
            self.root,
            padding=14
        )

        outer.pack(
            fill="both",
            expand=True
        )

        title = ttk.Label(
            outer,
            text=(
                "SUNDAY SERVICE SYSTEM"
            ),
            font=(
                "Segoe UI",
                22,
                "bold"
            ),
        )

        title.pack(
            pady=(
                0,
                6
            )
        )

        self.bind_tooltip(
            title,
            (
                "The Sunday Service System is the volunteer dashboard for "
                "starting the church service tools, checking readiness, "
                "controlling recording/streaming, sermon lower thirds, "
                "chapter markers, and camera views."
            ),
        )

        help_contact_text = str(
            self.config.get(
                "help_contact_text",
                ""
            )
        ).strip()

        if help_contact_text:
            help_contact = ttk.Label(
                outer,
                text=help_contact_text,
                font=(
                    "Segoe UI",
                    11,
                    "bold"
                ),
            )

            help_contact.pack(
                pady=(
                    0,
                    8
                )
            )

        self.bind_tooltip(
            help_contact,
            (
                "If something does not look right and the volunteer is "
                "unsure what to do, use the listed help contacts."
            ),
        )

        subtitle = ttk.Label(
            outer,
            text=(
                "No color = normal. YELLOW = CHECK. RED = FIX."
            ),
            font=(
                "Segoe UI",
                11
            ),
        )

        subtitle.pack(
            pady=(
                0,
                14
            )
        )

        self.bind_tooltip(
            subtitle,
            (
                "Normal items are intentionally neutral. Yellow means the "
                "item should be checked. Red means the volunteer should fix "
                "or get help with that item before continuing."
            ),
        )

        self.profile_display_label = ttk.Button(
            outer,
            textvariable=self.profile_display_var,
            command=self.open_profile_manager,
        )

        self.profile_display_label.pack(
            pady=(
                0,
                10
            )
        )

        self.bind_tooltip(
            self.profile_display_label,
            (
                "Shows the active Sunday Service System church profile. "
                "Click this label to open SSS Setup & Settings."
            ),
        )

        preflight_wrapper = ttk.Frame(
            outer
        )

        preflight_wrapper.pack(
            fill="x"
        )

        self.preflight_header_button = ttk.Button(
            preflight_wrapper,
            text="▼ SYSTEM STATUS",
            command=self.toggle_preflight,
        )

        self.preflight_header_button.pack(
            fill="x"
        )

        self.bind_tooltip(
            self.preflight_header_button,
            (
                "Click to expand or collapse System Status. These checks keep "
                "running even when this section is collapsed."
            ),
        )

        self.preflight_content = ttk.Frame(
            preflight_wrapper,
            padding=(
                0,
                8,
                0,
                0
            ),
        )

        self.preflight_content.pack(
            fill="x"
        )

        status_frame = self.preflight_content

        important_frame = ttk.LabelFrame(
            status_frame,
            text="SERVICE",
            padding=8,
        )

        important_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(
                0,
                6
            ),
        )

        secondary_frame = ttk.LabelFrame(
            status_frame,
            text="AFTER SERVICE",
            padding=8,
        )

        secondary_frame.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(
                6,
                0
            ),
        )

        status_frame.columnconfigure(
            0,
            weight=1
        )

        status_frame.columnconfigure(
            1,
            weight=1
        )

        important_items = [
            ("SERMON", "Sermon"),
            ("SERMON_CHAPTERS", "Chapters"),
            ("PTZ", "Camera"),
            ("OBS", "OBS"),
            ("PRESENTER", "Presenter"),
            ("COLLECTION", "OBS scene"),
            ("AUDIO", "Audio monitor"),
            ("AUDIO_HEALTH", "Program audio"),
            ("RECORDING_HEALTH", "Recording"),
            ("INPUTS", "Sources"),
            ("DISK", "Storage"),
            ("INTERNET", "Internet"),
        ]

        secondary_items = [
            ("PLANNING", "Planning"),
            ("YOUTUBE", "YouTube"),
            ("POST", "Post-service"),
            ("FOLDERS", "Folders"),
            ("SERMON_AI", "Sermon AI"),
            ("CHAPTERS", "Chapter system"),
            ("TOOLS", "Tools / GPU"),
        ]

        def add_status_items(
            parent,
            items
        ):
            for row, (
                key,
                label
            ) in enumerate(
                items
            ):
                var = tk.StringVar(
                    value="Checking..."
                )

                self.status_vars[
                    key
                ] = var

                name_label = ttk.Label(
                    parent,
                    text=label,
                    width=16,
                    cursor="hand2",
                )

                name_label.grid(
                    row=row,
                    column=0,
                    sticky="w",
                    padx=4,
                    pady=2,
                )

                name_label.bind(
                    "<Button-1>",
                    lambda event, status_key=key:
                        self.show_status_detail(
                            status_key
                        )
                )

                self.bind_tooltip(
                    name_label,
                    self.status_tooltip_text(
                        key
                    ),
                )

                if key == "AUDIO_HEALTH":
                    meter_frame = ttk.Frame(
                        parent
                    )

                    meter_frame.grid(
                        row=row,
                        column=1,
                        sticky="ew",
                        padx=4,
                        pady=2,
                    )

                    # Keep the dB readout on the LEFT in a fixed-width
                    # field. This prevents changing values such as -23 dB
                    # and -4 dB from resizing/shifting the meter.
                    self.audio_meter_db_var = tk.StringVar(
                        value="-60 dB"
                    )

                    self.audio_meter_db_label = tk.Label(
                        meter_frame,
                        textvariable=self.audio_meter_db_var,
                        font=(
                            "Consolas",
                            8,
                            "bold"
                        ),
                        width=7,
                        anchor="e",
                        padx=3,
                        background="#F4F4F4",
                        foreground="#303030",
                    )

                    self.audio_meter_db_label.pack(
                        side="left",
                        padx=(
                            0,
                            5
                        ),
                    )

                    self.audio_meter_canvas = tk.Canvas(
                        meter_frame,
                        height=32,
                        width=250,
                        highlightthickness=0,
                        background="#F4F4F4",
                    )

                    self.audio_meter_canvas.pack(
                        side="left",
                        fill="x",
                        expand=True,
                    )

                    # The right side is now reserved only for exceptions.
                    # Give it a fixed width so warnings do not shove the
                    # meter around when they appear/disappear.
                    self.audio_meter_issue_var = tk.StringVar(
                        value=""
                    )

                    self.audio_meter_issue_label = tk.Label(
                        meter_frame,
                        textvariable=self.audio_meter_issue_var,
                        font=(
                            "Segoe UI",
                            8,
                            "bold"
                        ),
                        width=14,
                        anchor="center",
                        justify="center",
                        padx=3,
                        background="#F4F4F4",
                        foreground="#303030",
                    )

                    self.audio_meter_issue_label.pack(
                        side="right",
                        padx=(
                            5,
                            0
                        ),
                    )

                    self.status_labels[
                        key
                    ] = self.audio_meter_issue_label

                    for widget in (
                        meter_frame,
                        self.audio_meter_canvas,
                        self.audio_meter_db_label,
                        self.audio_meter_issue_label,
                    ):
                        try:
                            widget.configure(
                                cursor="hand2"
                            )
                        except Exception:
                            pass

                        widget.bind(
                            "<Button-1>",
                            lambda event, status_key=key:
                                self.show_status_detail(
                                    status_key
                                )
                        )

                        self.bind_tooltip(
                            widget,
                            self.status_tooltip_text(
                                key
                            ),
                        )

                    self.draw_live_audio_meter(
                        -120.0
                    )

                else:
                    status_label = tk.Label(
                        parent,
                        textvariable=var,
                        font=(
                            "Segoe UI",
                            8,
                            "bold"
                        ),
                        wraplength=250,
                        justify="left",
                        anchor="w",
                        padx=6,
                        pady=2,
                        relief="groove",
                        borderwidth=1,
                    )

                    status_label.grid(
                        row=row,
                        column=1,
                        sticky="ew",
                        padx=4,
                        pady=2,
                    )

                    self.status_labels[
                        key
                    ] = status_label

                    status_label.configure(
                        cursor="hand2"
                    )

                    status_label.bind(
                        "<Button-1>",
                        lambda event, status_key=key:
                            self.show_status_detail(
                                status_key
                            )
                    )

                    self.bind_tooltip(
                        status_label,
                        self.status_tooltip_text(
                            key
                        ),
                    )

            parent.columnconfigure(
                1,
                weight=1
            )

        add_status_items(
            important_frame,
            important_items
        )

        add_status_items(
            secondary_frame,
            secondary_items
        )

        self.status_detail_var = tk.StringVar(
            value=(
                "Hover over or click an item for a plain-language explanation."
            )
        )

        # Keep the help/tooltip line OUTSIDE the collapsible System Status
        # body so volunteers can still read button explanations when
        # Preflight is collapsed.
        # Reserve a fixed two-line area for tooltip help. This prevents
        # longer explanations from changing the window layout.
        tooltip_help_frame = tk.Frame(
            outer,
            height=38,
            background="#F0F0F0",
        )

        tooltip_help_frame.pack(
            fill="x",
            padx=4,
            pady=(
                6,
                0
            ),
        )

        tooltip_help_frame.pack_propagate(
            False
        )

        tooltip_prefix = tk.Label(
            tooltip_help_frame,
            text="Tooltip:",
            font=(
                "Segoe UI",
                8,
                "bold"
            ),
            background="#F0F0F0",
            anchor="nw",
        )

        tooltip_prefix.pack(
            side="left",
            anchor="nw",
            padx=(
                0,
                5
            ),
            pady=2,
        )

        tooltip_help_label = tk.Label(
            tooltip_help_frame,
            textvariable=self.status_detail_var,
            font=(
                "Segoe UI",
                8
            ),
            height=2,
            background="#F0F0F0",
            wraplength=980,
            justify="left",
            anchor="nw",
        )

        tooltip_help_label.pack(
            side="left",
            fill="x",
            expand=True,
            pady=2,
        )

        self.bind_tooltip(
            tooltip_help_frame,
            (
                "This help line mirrors the hover tooltips. Hover over any "
                "main status or control for a plain-language explanation; "
                "click a System Status item to show its current technical detail."
            ),
        )

        button_frame = ttk.LabelFrame(
            outer,
            text="Volunteer Controls — Follow the visible steps",
            padding=8,
        )

        self.volunteer_button_frame = button_frame
        self.workflow_label_widgets = {}

        button_frame.pack(
            fill="x",
            pady=(
                10,
                0
            )
        )

        # The workflow is intentionally one horizontal row per stage.
        # This keeps every normal volunteer control visible even while
        # the two-column System Status is expanded.

        def workflow_label(
            row,
            text_value,
            tooltip_text
        ):
            label_widget = ttk.Label(
                button_frame,
                text=text_value,
                font=(
                    "Segoe UI",
                    9,
                    "bold"
                ),
                width=18,
                anchor="w",
            )

            label_widget.grid(
                row=row,
                column=0,
                sticky="w",
                padx=(
                    4,
                    8
                ),
                pady=4,
            )

            self.bind_tooltip(
                label_widget,
                tooltip_text,
            )

            self.workflow_label_widgets[
                row
            ] = label_widget

            return label_widget

        # ---------------------------------------------------------
        # 1 — PREP
        # ---------------------------------------------------------
        workflow_label(
            0,
            "1 — SERVICE PREP",
            (
                "Start here. Launch the Sunday applications, then refresh System "
                "Status to make sure the service systems are ready."
            ),
        )

        self.launch_button = ttk.Button(
            button_frame,
            text="LAUNCH SUNDAY APPS",
            command=self.launch_apps,
        )

        self.launch_button.grid(
            row=0,
            column=1,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.launch_button,
            (
                "Starts the Sunday applications that SSS expects to use, "
                "such as OBS and Presenter. It does not start recording or "
                "streaming."
            ),
        )

        self.preflight_button = ttk.Button(
            button_frame,
            text="REFRESH STATUS",
            command=self.run_preflight_async,
        )

        self.preflight_button.grid(
            row=0,
            column=2,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.preflight_button,
            (
                "Refreshes System Status now. Yellow items should be reviewed; "
                "red items need attention before the service."
            ),
        )

        self.reset_chapters_button = ttk.Button(
            button_frame,
            text="RESET LT / CHAPTERS",
            command=self.reset_chapter_rotation,
        )

        self.reset_chapters_button.grid(
            row=0,
            column=3,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.reset_chapters_button,
            (
                "Resets the sermon lower-third/chapter sequence back to the "
                "beginning (Prayer). Only available while OBS is not "
                "recording, so it can't be used to disturb a live service."
            ),
        )

        # ---------------------------------------------------------
        # 2 — LIVE AUDIO / VIDEO
        # ---------------------------------------------------------
        workflow_label(
            1,
            "2 — LIVE A/V",
            (
                "These are the live-service audio/video controls. Start "
                "Recording first, then start the livestream. MUTE AUDIO toggles "
                "the configured program-audio inputs between muted and unmuted."
            ),
        )

        self.record_start_button = ttk.Button(
            button_frame,
            text="START RECORDING",
            command=self.start_recording,
        )

        self.record_start_button.grid(
            row=1,
            column=1,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.record_start_button,
            (
                "Manually starts the local OBS recording. Recording is never "
                "started automatically. A fresh recording resets the real "
                "sermon chapter sequence to Prayer."
            ),
        )

        self.stream_start_button = ttk.Button(
            button_frame,
            text="START STREAM",
            command=self.start_stream,
        )

        self.stream_start_button.grid(
            row=1,
            column=2,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.stream_start_button,
            (
                "Manually starts the YouTube livestream through OBS. "
                "Recording and streaming remain separate controls."
            ),
        )

        self.mute_button = ttk.Button(
            button_frame,
            text="MUTE AUDIO",
            command=self.emergency_mute,
        )

        self.mute_button.grid(
            row=1,
            column=3,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.mute_button,
            (
                "Toggles the configured program-audio inputs. Press MUTE "
                "AUDIO to mute them; the same button changes to UNMUTE AUDIO "
                "so you can restore sound."
            ),
        )

        # ---------------------------------------------------------
        # 3 — SCRIPTURE READING
        # ---------------------------------------------------------
        workflow_label(
            2,
            "3 — SCRIPTURE",
            (
                "Before the service, leave Presenter on the FIRST Scripture "
                "verse. START READING switches the Scripture view into Program "
                "and creates the Scripture chapter marker. During the reading, "
                "the main button sends Presenter NEXT using MIDI note 60. "
                "END READING sends Ctrl+F13 for webcam only, then Ctrl+Shift to transition it to Program."
            ),
        )

        self.scripture_back_button = ttk.Button(
            button_frame,
            text="FIRST VERSE SET BEFORE SERVICE",
            state="disabled",
        )

        self.scripture_back_button.grid(
            row=2,
            column=1,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.scripture_main_button = ttk.Button(
            button_frame,
            text="START READING",
            command=self.scripture_main_action,
        )

        self.scripture_main_button.grid(
            row=2,
            column=2,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.scripture_end_button = ttk.Button(
            button_frame,
            text="END READING",
            command=self.end_scripture_reading,
            state="disabled",
        )

        self.scripture_end_button.grid(
            row=2,
            column=3,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.scripture_back_button,
            (
                "Before the service, manually leave WorshipTools Presenter on "
                "the first verse of the sermon Scripture. SSS does not search "
                "for the passage or move Presenter when START is pressed."
            ),
        )

        self.bind_tooltip(
            self.scripture_main_button,
            (
                "Presenter should already be on the first Scripture verse. "
                "START sends Ctrl+F15, transitions the Scripture view to Program, "
                "and creates the Scripture chapter marker. After START, each "
                "press sends Presenter NEXT with MIDI note 60."
            ),
        )

        self.bind_tooltip(
            self.scripture_end_button,
            (
                "Ends the Scripture reading early or after the final verse. "
                "It sends Ctrl+Shift so OBS transitions back to the webcam that "
                "was left in Preview. Use this if the pastor does not read every "
                "verse in the planned passage."
            ),
        )

        # ---------------------------------------------------------
        # 4 — SERMON
        # ---------------------------------------------------------
        workflow_label(
            3,
            "4 — SERMON",
            (
                "This is the sermon lower-third and chapter-marker control "
                "inside OBS. The button follows the sermon sequence. When a "
                "step has a lower third, SSS activates the matching lower "
                "third; while OBS is recording, the same press also creates "
                "the matching named chapter marker in the recording."
            ),
        )

        self.chapter_action_descriptor_var = tk.StringVar(
            value=(
                "LOWER THIRD +\n"
                "CHAPTER MARKER"
            )
        )

        self.chapter_action_descriptor_label = ttk.Label(
            button_frame,
            textvariable=self.chapter_action_descriptor_var,
            font=(
                "Segoe UI",
                8,
                "bold"
            ),
            anchor="center",
            justify="center",
        )

        self.chapter_action_descriptor_label.grid(
            row=3,
            column=1,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.chapter_action_descriptor_label,
            (
                "This sermon control is tied to OBS lower thirds and recording "
                "chapters. For a sermon step with a lower third, SSS loads and "
                "shows that matching graphic. The same sermon-step action also "
                "creates its named chapter marker in the OBS recording."
            ),
        )

        self.chapter_button = ttk.Button(
            button_frame,
            text="NEXT SERMON CHAPTER",
            command=self.next_sermon_chapter,
        )

        self.chapter_button.grid(
            row=3,
            column=2,
            columnspan=2,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.chapter_button,
            (
                "Press this at the appropriate sermon moment. SSS uses OBS to "
                "activate the lower third assigned to the current sermon step "
                "and creates the matching named chapter marker in the recording. "
                "After it fires, the button advances to the next sermon step."
            ),
        )

        # ---------------------------------------------------------
        # 5 — CAMERA
        # ---------------------------------------------------------
        workflow_label(
            4,
            "5 — CAMERA VIEW",
            (
                "Switch the PTZ camera between the saved Worship view and "
                "Pastor view without changing recording or streaming."
            ),
        )

        self.worship_camera_button = ttk.Button(
            button_frame,
            text="WORSHIP VIEW",
            command=self.ptz_worship,
        )

        self.worship_camera_button.grid(
            row=4,
            column=1,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.worship_camera_button,
            (
                "Recalls the saved PTZ camera preset used for the Worship view."
            ),
        )

        self.pastor_camera_button = ttk.Button(
            button_frame,
            text="PASTOR VIEW",
            command=self.ptz_pastor,
        )

        self.pastor_camera_button.grid(
            row=4,
            column=2,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.pastor_camera_button,
            (
                "Recalls the saved PTZ camera preset used for the Pastor view."
            ),
        )

        # Leave the third cell visually quiet so camera controls remain
        # obviously grouped rather than filling every available space.
        ttk.Label(
            button_frame,
            text="",
        ).grid(
            row=4,
            column=3,
            sticky="ew",
        )

        # ---------------------------------------------------------
        # 6 — END SERVICE
        # ---------------------------------------------------------
        workflow_label(
            5,
            "6 — END SERVICE",
            (
                "Use these controls when the service is finished. Stop the "
                "livestream first, then stop the recording so the full local "
                "recording is safely completed."
            ),
        )

        self.stream_stop_button = ttk.Button(
            button_frame,
            text="STOP STREAM",
            command=self.stop_stream,
        )

        self.stream_stop_button.grid(
            row=5,
            column=1,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.stream_stop_button,
            (
                "Ends the YouTube livestream in OBS. At the end of the service, "
                "stop the stream before stopping the local recording."
            ),
        )

        self.record_stop_button = ttk.Button(
            button_frame,
            text="STOP RECORDING",
            command=self.stop_recording,
        )

        self.record_stop_button.grid(
            row=5,
            column=2,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.record_stop_button,
            (
                "Ends the local OBS recording. Use this after the livestream "
                "has been stopped so the complete service recording is saved."
            ),
        )

        self.end_service_hint = ttk.Label(
            button_frame,
            text="Stream first, then Recording",
            font=(
                "Segoe UI",
                8,
                "italic"
            ),
            anchor="center",
        )

        self.end_service_hint.grid(
            row=5,
            column=3,
            padx=4,
            pady=4,
            sticky="ew",
        )

        self.bind_tooltip(
            self.end_service_hint,
            (
                "Recommended shutdown order: stop the livestream first, then "
                "stop the local recording."
            ),
        )

        # Planning/YouTube maintenance controls are intentionally hidden
        # from the normal volunteer surface. They remain available through
        # ADMIN / TROUBLESHOOTING.
        self.planning_button = ttk.Button(
            button_frame,
            text="SYNC PLANNING SCRIPTURE",
            command=self.update_planning_async,
        )

        self.youtube_button = ttk.Button(
            button_frame,
            text="CHECK YOUTUBE UPLOAD",
            command=self.start_youtube_upload_waiter,
        )

        self.admin_button = ttk.Button(
            button_frame,
            text="ADMIN / TROUBLESHOOTING",
            command=self.open_admin_panel,
        )

        self.admin_button.grid(
            row=6,
            column=1,
            columnspan=3,
            padx=4,
            pady=(
                6,
                2
            ),
            sticky="ew",
        )

        self.bind_tooltip(
            self.admin_button,
            (
                "Opens maintenance, troubleshooting, PTZ settings, Chapter/LT "
                "test mode, reset tools, and other controls intended for an "
                "administrator rather than the normal volunteer workflow."
            ),
        )

        self.refresh_scripture_controls()
        self.apply_profile_capabilities()

        for column in (
            1,
            2,
            3,
        ):
            button_frame.columnconfigure(
                column,
                weight=1
            )

        sunday_log_wrapper = ttk.Frame(
            outer
        )

        sunday_log_wrapper.pack(
            fill="both",
            expand=True,
            pady=(
                12,
                0
            ),
        )

        self.sunday_log_header_button = ttk.Button(
            sunday_log_wrapper,
            text="▶ SUNDAY LOG",
            command=self.toggle_sunday_log,
        )

        self.sunday_log_header_button.pack(
            fill="x"
        )

        self.bind_tooltip(
            self.sunday_log_header_button,
            (
                "Click to expand or collapse the Sunday Log. The log keeps "
                "recording SSS activity even while it is collapsed."
            ),
        )

        self.sunday_log_content = ttk.Frame(
            sunday_log_wrapper,
            padding=(
                0,
                6,
                0,
                0
            ),
        )

        # Start collapsed. The Text widget still exists and continues to
        # receive log messages while this content frame is hidden.
        log_frame = ttk.Frame(
            self.sunday_log_content,
            padding=8,
        )

        log_frame.pack(
            fill="both",
            expand=True,
        )

        self.log_widget = tk.Text(
            log_frame,
            height=5,
            wrap="word",
            state="disabled",
            font=(
                "Consolas",
                10
            ),
        )

        self.log_widget.pack(
            fill="both",
            expand=True
        )

        self.bind_tooltip(
            self.log_widget,
            (
                "Technical activity log for SSS. Volunteers normally do not "
                "need to read this unless a yellow/red item needs more detail "
                "or an administrator is troubleshooting."
            ),
        )

    def toggle_preflight(
        self
    ):
        if (
            self.preflight_header_button is None
            or
            self.preflight_content is None
        ):
            return

        self.preflight_expanded = not (
            self.preflight_expanded
        )

        if self.preflight_expanded:
            self.preflight_content.pack(
                fill="x"
            )

            self.preflight_header_button.configure(
                text="▼ SYSTEM STATUS"
            )

        else:
            self.preflight_content.pack_forget()

            self.preflight_header_button.configure(
                text="▶ SYSTEM STATUS"
            )

    def toggle_sunday_log(
        self
    ):
        if (
            self.sunday_log_header_button is None
            or
            self.sunday_log_content is None
        ):
            return

        self.sunday_log_expanded = not (
            self.sunday_log_expanded
        )

        if self.sunday_log_expanded:
            self.sunday_log_content.pack(
                fill="both",
                expand=True,
            )

            self.sunday_log_header_button.configure(
                text="▼ SUNDAY LOG"
            )

        else:
            self.sunday_log_content.pack_forget()

            self.sunday_log_header_button.configure(
                text="▶ SUNDAY LOG"
            )

    def append_log(
        self,
        message
    ):
        stamp = time.strftime(
            "%H:%M:%S"
        )

        self.log_widget.configure(
            state="normal"
        )

        self.log_widget.insert(
            "end",
            f"[{stamp}] {message}\n"
        )

        self.log_widget.see(
            "end"
        )

        self.log_widget.configure(
            state="disabled"
        )

        # Keep a human-friendly cross-service event timeline.
        try:
            record_event(
                message
            )

            update_session_heartbeat(
                last_event=message,
                profile_name=self.active_profile_name,
            )

        except Exception:
            pass

        # Keep a durable per-service log outside the UI.
        try:
            plan = read_json(
                SERMON_PLAN_FILE,
                {}
            )

            service_date = (
                plan.get(
                    "service_date"
                )
                or
                now_local().date().isoformat()
            )

            append_system_log(
                message,
                service_date=service_date,
            )
        except Exception:
            pass

    def draw_live_audio_meter(
        self,
        level_db
    ):
        canvas = self.audio_meter_canvas

        if canvas is None:
            return

        try:
            level_db = float(
                level_db
            )
        except Exception:
            level_db = -120.0

        width = max(
            220,
            int(
                canvas.winfo_width()
                or
                250
            )
        )

        height = 32
        bar_top = 2
        bar_bottom = 16
        segment_count = 30
        gap = 1

        canvas.delete(
            "all"
        )

        # OBS-style dB scale: -60 to 0 dB.
        visible_db = max(
            -60.0,
            min(
                0.0,
                level_db
            )
        )

        segment_width = (
            width
            /
            segment_count
        )

        for index in range(
            segment_count
        ):
            segment_end_db = (
                -60.0
                +
                (
                    (
                        index
                        +
                        1
                    )
                    *
                    (
                        60.0
                        /
                        segment_count
                    )
                )
            )

            active = (
                visible_db
                >=
                segment_end_db
            )

            if active:
                if segment_end_db <= -18:
                    fill = "#32A852"

                elif segment_end_db <= -6:
                    fill = "#D6A900"

                else:
                    fill = "#C62828"

            else:
                fill = "#D9D9D9"

            x0 = (
                index
                *
                segment_width
            )

            x1 = (
                (
                    index
                    +
                    1
                )
                *
                segment_width
                -
                gap
            )

            canvas.create_rectangle(
                x0,
                bar_top,
                x1,
                bar_bottom,
                fill=fill,
                outline="",
            )

        ticks = [
            -60,
            -48,
            -36,
            -24,
            -18,
            -12,
            -6,
            0,
        ]

        for tick in ticks:
            x = (
                (
                    tick
                    +
                    60
                )
                /
                60
                *
                width
            )

            anchor = "center"

            if tick == -60:
                anchor = "w"

            elif tick == 0:
                anchor = "e"

            canvas.create_text(
                x,
                24,
                text=str(
                    tick
                ),
                anchor=anchor,
                font=(
                    "Segoe UI",
                    6
                ),
                fill="#555555",
            )

    def set_audio_meter_issue(
        self,
        text_value,
        level="normal"
    ):
        if self.audio_meter_issue_var is None:
            return

        self.audio_meter_issue_var.set(
            str(
                text_value
            )
        )

        label = self.audio_meter_issue_label

        if label is None:
            return

        if level == "problem":
            background = "#FFC7CE"
            foreground = "#9C0006"

        elif level == "review":
            background = "#FFEB9C"
            foreground = "#7F6000"

        else:
            background = "#F4F4F4"
            foreground = "#303030"

        try:
            label.configure(
                background=background,
                foreground=foreground,
            )
        except Exception:
            pass

    def update_live_audio_meter_from_payload(
        self,
        payload,
        *,
        stale=False
    ):
        if not isinstance(
            payload,
            dict
        ):
            payload = {}

        try:
            max_db = float(
                payload.get(
                    "max_db",
                    -120.0
                )
            )
        except Exception:
            max_db = -120.0

        try:
            silence_seconds = float(
                payload.get(
                    "silence_seconds",
                    0.0
                )
            )
        except Exception:
            silence_seconds = 0.0

        try:
            clip_seconds = float(
                payload.get(
                    "clip_seconds",
                    0.0
                )
            )
        except Exception:
            clip_seconds = 0.0

        state = str(
            payload.get(
                "state",
                ""
            )
        ).upper()

        # Feed the raw OBS peak into the smoother rather than drawing it
        # directly. Clamp the visible target to the meter's -60..0 range.
        self.audio_meter_target_db = max(
            -60.0,
            min(
                0.0,
                max_db
            )
        )

        no_audio_seconds = float(
            self.config.get(
                "audio_meter_no_audio_seconds",
                60
            )
        )

        if stale:
            self.set_audio_meter_issue(
                "METER OFFLINE",
                "review",
            )

        elif state == "INPUT_MISSING":
            self.set_audio_meter_issue(
                "INPUT MISSING",
                "problem",
            )

        elif state == "ERROR":
            self.set_audio_meter_issue(
                "METER ERROR",
                "problem",
            )

        elif (
            state == "CLIPPING"
            or
            clip_seconds
            >=
            float(
                self.config.get(
                    "audio_sanity_clip_seconds",
                    3
                )
            )
        ):
            self.set_audio_meter_issue(
                "CLIPPING",
                "problem",
            )

        elif silence_seconds >= no_audio_seconds:
            self.set_audio_meter_issue(
                (
                    "NO AUDIO "
                    f"{silence_seconds:.0f}s"
                ),
                "review",
            )

        elif state in {
            "STARTING",
            "WAITING_FOR_OBS",
        }:
            self.set_audio_meter_issue(
                "starting",
                "normal",
            )

        else:
            self.set_audio_meter_issue(
                "",
                "normal",
            )

    def _live_audio_meter_listener_worker(
        self
    ):
        port = int(
            self.config.get(
                "audio_meter_udp_port",
                49221
            )
        )

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        try:
            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1,
            )

            sock.bind(
                (
                    "127.0.0.1",
                    port,
                )
            )

            sock.settimeout(
                1.0
            )

            while True:
                try:
                    raw, address = sock.recvfrom(
                        4096
                    )

                except socket.timeout:
                    continue

                except Exception:
                    break

                try:
                    payload = json.loads(
                        raw.decode(
                            "utf-8",
                            errors="replace"
                        )
                    )

                    if not isinstance(
                        payload,
                        dict
                    ):
                        continue

                    self.audio_meter_latest = payload
                    self.audio_meter_last_packet = (
                        time.time()
                    )

                except Exception:
                    continue

        except Exception as exc:
            self.post_ui(
                self.append_log,
                (
                    "Live audio meter listener warning: "
                    f"{exc}. Using status-file fallback."
                ),
            )

        finally:
            try:
                sock.close()
            except Exception:
                pass

    def start_live_audio_meter_listener(
        self
    ):
        if self.audio_meter_listener_started:
            return

        if not self.config.get(
            "audio_sanity_enabled",
            True
        ):
            return

        self.audio_meter_listener_started = True

        threading.Thread(
            target=self._live_audio_meter_listener_worker,
            daemon=True,
        ).start()

    def refresh_live_audio_meter(
        self
    ):
        try:
            if not self.config.get(
                "audio_sanity_enabled",
                True
            ):
                self.audio_meter_target_db = -60.0
                self.audio_meter_display_db = -60.0

                self.draw_live_audio_meter(
                    -60.0
                )

                if self.audio_meter_db_var is not None:
                    self.audio_meter_db_var.set(
                        "-60 dB"
                    )

                self.set_audio_meter_issue(
                    "DISABLED",
                    "normal",
                )

            else:
                now = time.time()
                packet_age = (
                    now
                    -
                    self.audio_meter_last_packet
                    if self.audio_meter_last_packet
                    else
                    9999
                )

                if (
                    self.audio_meter_latest
                    and
                    packet_age <= 2.5
                ):
                    self.update_live_audio_meter_from_payload(
                        self.audio_meter_latest
                    )

                elif AUDIO_STATUS_FILE.exists():
                    file_age = (
                        now
                        -
                        AUDIO_STATUS_FILE.stat().st_mtime
                    )

                    payload = read_json(
                        AUDIO_STATUS_FILE,
                        {}
                    )

                    self.update_live_audio_meter_from_payload(
                        payload,
                        stale=(
                            file_age
                            >
                            15
                        ),
                    )

                else:
                    self.audio_meter_target_db = -60.0

                    self.set_audio_meter_issue(
                        "starting",
                        "normal",
                    )

                # Smooth movement:
                #   attack  = quick response when audio gets louder
                #   release = slower fall when audio gets quieter
                target = float(
                    self.audio_meter_target_db
                )

                current = float(
                    self.audio_meter_display_db
                )

                if target > current:
                    alpha = float(
                        self.config.get(
                            "audio_meter_attack_smoothing",
                            0.55
                        )
                    )
                else:
                    alpha = float(
                        self.config.get(
                            "audio_meter_release_smoothing",
                            0.16
                        )
                    )

                alpha = max(
                    0.01,
                    min(
                        1.0,
                        alpha
                    )
                )

                current = (
                    current
                    +
                    (
                        target
                        -
                        current
                    )
                    *
                    alpha
                )

                if abs(
                    target
                    -
                    current
                ) < 0.15:
                    current = target

                self.audio_meter_display_db = current

                self.draw_live_audio_meter(
                    current
                )

                if self.audio_meter_db_var is not None:
                    shown_db = int(
                        round(
                            current
                        )
                    )

                    self.audio_meter_db_var.set(
                        f"{shown_db:+d} dB"
                        if shown_db > 0
                        else
                        f"{shown_db:d} dB"
                    )

        except Exception:
            pass

        try:
            self.root.after(
                100,
                self.refresh_live_audio_meter
            )
        except Exception:
            pass

    def set_tooltip_help(
        self,
        text_value
    ):
        if self.status_detail_var is None:
            return

        value = " ".join(
            str(
                text_value
                or
                ""
            ).split()
        )

        max_chars = 220

        if len(value) > max_chars:
            value = (
                value[:max_chars - 1].rstrip()
                +
                "…"
            )

        self.status_detail_var.set(
            value
        )

    def bind_tooltip(
        self,
        widget,
        text_value
    ):
        """
        Center-bar tooltip only.

        Hovering over a control updates the fixed Tooltip: help area in the
        SSS window. No floating popup is created.
        """
        if widget is None:
            return

        text_value = str(
            text_value
            or
            ""
        ).strip()

        if not text_value:
            return

        try:
            widget.bind(
                "<Enter>",
                lambda event, value=text_value:
                    self.set_tooltip_help(
                        value
                    ),
                add="+",
            )
        except Exception:
            pass

    def status_tooltip_text(
        self,
        key
    ):
        tooltips = {
            "SERMON": (
                "This is the official sermon for this Sunday, loaded from "
                "the pastor's sermon plan. The row shows the sermon title."
            ),
            "SERMON_CHAPTERS": (
                "Shows whether the sermon chapter sequence is ready. "
                "During the sermon, SSS moves through Prayer, Scripture, "
                "the sermon points, Ending Prayer, and Benediction."
            ),
            "PTZ": (
                "Checks the PTZ camera connection and preset. The camera "
                "buttons below switch between the Worship and Pastor views."
            ),
            "OBS": (
                "Shows whether SSS can communicate with OBS. OBS handles "
                "the church recording, livestream, scenes, sources, lower "
                "thirds, and chapter markers."
            ),
            "PRESENTER": (
                "Checks the loopMIDI connection used for Scripture NEXT. "
                "Before the service, manually leave Presenter on the first "
                "Scripture verse. SSS sends MIDI note 60 for each next verse."
            ),
            "COLLECTION": (
                "Confirms that OBS is using the expected scene collection. In "
                "PROFILE mode this comes from the active church profile; "
                "LEGACY mode uses the current working SSS configuration."
            ),
            "AUDIO": (
                "Checks the audio-monitor path used by the church system "
                "so the expected TASCAM/program audio route is available."
            ),
            "AUDIO_HEALTH": (
                "Live program-audio level from OBS. The meter should move "
                "when sound is present. If audio stays too low for 60 "
                "seconds, SSS shows NO AUDIO."
            ),
            "RECORDING_HEALTH": (
                "Checks the OBS recording itself. During recording, SSS "
                "verifies that the output file exists and continues growing."
            ),
            "INPUTS": (
                "Confirms that the important OBS sources are present, "
                "including the main audio, room microphones, and lower thirds."
            ),
            "DISK": (
                "Shows available space on the drive where Sunday recordings "
                "are saved."
            ),
            "INTERNET": (
                "Checks the internet connection needed for the YouTube "
                "livestream and post-service upload."
            ),
            "PLANNING": (
                "Checks the WorshipTools Planning sermon Scripture sync for "
                "the upcoming service."
            ),
            "YOUTUBE": (
                "Shows the state of the sermon upload to the church YouTube "
                "channel after the service."
            ),
            "POST": (
                "Shows whether the automatic after-service jobs are idle, "
                "running, complete, or need attention."
            ),
            "FOLDERS": (
                "Confirms that the folders used for recordings, transcripts, "
                "shorts, and sermon processing can be written to."
            ),
            "SERMON_AI": (
                "Shows whether Sermon AI is running. It watches the service "
                "and handles sermon transcription and post-service processing."
            ),
            "CHAPTERS": (
                "Checks the chapter system that creates named markers in the "
                "OBS recording and keeps the sermon sequence synchronized."
            ),
            "TOOLS": (
                "Checks the background media tools used after the service, "
                "including FFmpeg and NVIDIA GPU support."
            ),
        }

        return tooltips.get(
            key,
            "Shows the current state of this Sunday-service component."
        )

    def show_status_detail(
        self,
        key
    ):
        if self.status_detail_var is None:
            return

        detail = self.status_detail_text.get(
            key,
            ""
        )

        if not detail:
            detail = "No additional details."

        label_names = {
            "SERMON": "Sermon",
            "SERMON_CHAPTERS": "Chapters",
            "PTZ": "Camera",
            "OBS": "OBS",
            "PRESENTER": "Presenter",
            "COLLECTION": "Scene",
            "AUDIO": "Audio monitor",
            "AUDIO_HEALTH": "Program audio",
            "RECORDING_HEALTH": "Recording",
            "INPUTS": "Sources",
            "DISK": "Storage",
            "INTERNET": "Internet",
            "PLANNING": "Planning",
            "YOUTUBE": "YouTube",
            "POST": "Post-service",
            "FOLDERS": "Folders",
            "SERMON_AI": "Sermon AI",
            "CHAPTERS": "Chapter system",
            "TOOLS": "Tools / GPU",
        }

        self.set_tooltip_help(
            (
                label_names.get(
                    key,
                    key
                )
                +
                " current status: "
                +
                detail
            )
        )

    def compact_status_text(
        self,
        key,
        ok,
        detail,
        warning=False
    ):
        raw = str(
            detail
            or
            ""
        ).strip()

        lower = raw.lower()

        if warning:
            prefix = "CHECK"

            if key == "SERMON_CHAPTERS":
                if "restart" in lower:
                    return "CHECK — Restart OBS"

                return "CHECK — Chapters"

            if key == "PLANNING":
                if (
                    "date"
                    in lower
                    or
                    "service"
                    in lower
                ):
                    return "CHECK — Date"

                return "CHECK — Planning"

            if key == "YOUTUBE":
                if (
                    "access is denied"
                    in lower
                    or
                    "permission"
                    in lower
                ):
                    return "CHECK — Access"

                if "waiting" in lower:
                    return "WAITING"

                return "CHECK — YouTube"

            if key == "POST":
                if "running" in lower:
                    return "RUNNING"

                return "CHECK"

            if key == "AUDIO_HEALTH":
                return "CHECK"

            if key == "PRESENTER":
                return "CHECK — MIDI"

            return prefix

        if not ok:
            if key == "OBS":
                return "FIX — OBS"

            if key == "PTZ":
                return "FIX — Camera"

            if key == "AUDIO":
                return "FIX — Audio"

            if key == "INPUTS":
                return "FIX — Source"

            if key == "DISK":
                return "FIX — Storage"

            if key == "INTERNET":
                return "FIX — Internet"

            if key == "TOOLS":
                return "FIX — Tools"

            if key == "PRESENTER":
                return "FIX — MIDI"

            return "FIX"

        # Healthy / normal states: show only the one useful fact.
        if key == "SERMON":
            # check_sermon_plan() returns:
            #   Title | Scripture | N point(s)
            #
            # The volunteer-facing row should show the actual sermon
            # TITLE. Scripture and point count are still available by
            # clicking the row for details.
            if "|" in raw:
                title = raw.split(
                    "|",
                    1
                )[0].strip()

                if title:
                    return title

            return (
                raw
                or
                "Loaded"
            )

        if key == "SERMON_CHAPTERS":
            point_match = re.search(
                r"(\d+)\s+point",
                lower,
            )

            if point_match:
                return (
                    point_match.group(
                        1
                    )
                    +
                    " points"
                )

            return "Ready"

        if key == "PTZ":
            preset_match = re.search(
                r"preset\s*(\d+)",
                lower,
            )

            if preset_match:
                return (
                    "Preset "
                    +
                    preset_match.group(
                        1
                    )
                )

            return "Ready"

        if key == "OBS":
            return "Connected"

        if key == "PRESENTER":
            return (
                "MIDI ready"
                if ok
                else
                "CHECK — MIDI"
            )

        if key == "COLLECTION":
            display = re.sub(
                r"\s*\(auto-selected\)\s*$",
                "",
                raw,
                flags=re.IGNORECASE,
            ).strip()

            if display:
                if len(
                    display
                ) > 34:
                    return (
                        display[:33].rstrip()
                        +
                        "…"
                    )

                return display

            return "Ready"

        if key == "AUDIO":
            if "tascam" in lower:
                return "TASCAM"

            return "Ready"

        if key == "RECORDING_HEALTH":
            if "idle" in lower:
                return "Idle"

            if "growing" in lower:
                size_match = re.search(
                    r"(\d+(?:\.\d+)?)\s*mb",
                    lower,
                )

                if size_match:
                    return (
                        size_match.group(
                            1
                        )
                        +
                        " MB"
                    )

                return "Recording"

            if "recording" in lower:
                return "Recording"

            return "Ready"

        if key == "INPUTS":
            return "All present"

        if key == "DISK":
            free_match = re.search(
                r"(\d+(?:\.\d+)?)\s*gb\s+free",
                lower,
            )

            if free_match:
                try:
                    gb = float(
                        free_match.group(
                            1
                        )
                    )

                    if gb >= 1000:
                        return (
                            f"{gb / 1000:.1f} TB free"
                        )

                    return (
                        f"{gb:.0f} GB free"
                    )

                except Exception:
                    pass

            return "Ready"

        if key == "INTERNET":
            return "Online"

        if key == "PLANNING":
            if "unchanged" in lower:
                return "Unchanged"

            if (
                "updated"
                in lower
                or
                "correct"
                in lower
                or
                "synced"
                in lower
            ):
                return "Synced"

            return "Ready"

        if key == "YOUTUBE":
            if (
                "complete"
                in lower
                or
                "uploaded"
                in lower
                or
                "published"
                in lower
            ):
                return "Uploaded"

            if "waiting" in lower:
                return "Waiting"

            return "Ready"

        if key == "POST":
            if "complete" in lower:
                return "Done"

            if "running" in lower:
                return "Running"

            return "Idle"

        if key == "FOLDERS":
            return "Ready"

        if key == "SERMON_AI":
            if "running" in lower:
                return "Running"

            return "Ready"

        if key == "CHAPTERS":
            return "Ready"

        if key == "TOOLS":
            return "Ready"

        return (
            raw
            or
            "OK"
        )

    def set_status(
        self,
        key,
        ok,
        text,
        warning=False
    ):
        detail = str(
            text
            or
            ""
        ).strip()

        detail = re.sub(
            r"^(?:READY|REVIEW|PROBLEM)\s*(?:—|-|:)\s*",
            "",
            detail,
            flags=re.IGNORECASE,
        ).strip()

        self.status_detail_text[
            key
        ] = detail

        # Program audio has its own live meter. Keep the detailed text
        # available on click, but do not replace the meter with words.
        if (
            key
            ==
            "AUDIO_HEALTH"
            and
            self.audio_meter_canvas is not None
        ):
            self.status_vars[
                key
            ].set(
                detail
            )

            return

        display_text = self.compact_status_text(
            key,
            ok,
            detail,
            warning=warning,
        )

        if warning:
            background = "#FFEB9C"
            foreground = "#7F6000"

        elif not ok:
            background = "#FFC7CE"
            foreground = "#9C0006"

        else:
            background = "#F4F4F4"
            foreground = "#202020"

        self.status_vars[
            key
        ].set(
            display_text
        )

        label = self.status_labels.get(
            key
        )

        if label is not None:
            try:
                label.configure(
                    background=background,
                    foreground=foreground,
                )
            except Exception:
                pass

    def start_hidden_helper(
        self,
        script,
        *args
    ):
        script = Path(
            script
        )

        if not script.exists():
            return False

        pythonw = (
            BASE
            /
            "venv"
            /
            "Scripts"
            /
            "pythonw.exe"
        )

        try:
            subprocess.Popen(
                [
                    str(
                        pythonw
                    ),
                    str(
                        script
                    ),
                    *[
                        str(
                            item
                        )
                        for item in args
                    ],
                ],
                cwd=BASE,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
            )

            return True

        except Exception:
            return False

    def start_weekly_snapshot_async(
        self,
        phase="current"
    ):
        def worker():
            try:
                destination = weekly_snapshot(
                    retention_weeks=int(
                        self.config.get(
                            "weekly_backup_retention_weeks",
                            12
                        )
                    ),
                    phase=phase,
                )

                self.post_ui(
                    self.append_log,
                    (
                        "Weekly rollback snapshot ready: "
                        f"{destination.name}"
                    )
                )

            except Exception as exc:
                self.post_ui(
                    self.append_log,
                    (
                        "Weekly snapshot warning: "
                        f"{exc}"
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def start_audio_sanity_monitor(
        self
    ):
        if not self.config.get(
            "audio_sanity_enabled",
            True
        ):
            return

        if not AUDIO_SANITY_SCRIPT.exists():
            return

        if process_running_contains(
            "audio_sanity_monitor.py"
        ):
            return

        if self.start_hidden_helper(
            AUDIO_SANITY_SCRIPT
        ):
            self.append_log(
                "Live audio sanity monitor started."
            )

    def start_post_service_supervisor(
        self
    ):
        if not POST_SERVICE_SCRIPT.exists():
            self.append_log(
                "Post-service supervisor is not installed."
            )
            return False

        if process_running_contains(
            "post_service_supervisor.py"
        ):
            return True

        if self.start_hidden_helper(
            POST_SERVICE_SCRIPT
        ):
            self.append_log(
                "Post-service completion supervisor started."
            )
            return True

        self.append_log(
            "Could not start post-service supervisor."
        )
        return False

    def resume_pending_post_service(
        self
    ):
        if process_running_contains(
            "post_service_supervisor.py"
        ):
            return

        plan = read_json(
            SERMON_PLAN_FILE,
            {}
        )

        try:
            plan_service_date = time.strptime(
                str(
                    plan.get(
                        "service_date",
                        ""
                    )
                ),
                "%Y-%m-%d"
            )

            plan_epoch_day = time.mktime(
                plan_service_date
            )

            today_struct = now_local().date().timetuple()
            today_epoch_day = time.mktime(
                today_struct
            )

            age_days = int(
                round(
                    (
                        today_epoch_day
                        -
                        plan_epoch_day
                    )
                    /
                    86400
                )
            )

        except Exception:
            return

        grace_days = int(
            self.config.get(
                "youtube_service_date_grace_days",
                3
            )
        )

        if (
            age_days
            <
            0
            or
            age_days
            >
            grace_days
        ):
            return

        existing = read_json(
            POST_STATUS_FILE,
            {}
        )

        if (
            existing.get(
                "plan_id"
            )
            ==
            plan.get(
                "plan_id"
            )
            and
            existing.get(
                "state"
            )
            ==
            "COMPLETE"
        ):
            return

        recording = find_full_sermon_recording(
            self.config,
            plan,
            require_stable=False,
            require_duration=False,
        )

        youtube = read_json(
            YOUTUBE_STATUS_FILE,
            {}
        )

        youtube_state = str(
            youtube.get(
                "state",
                ""
            )
        ).upper()

        if (
            recording is not None
            or
            youtube_state
            in {
                "UPLOADING",
                "PUBLISHING",
                "ERROR",
                "WAITING_FOR_RECORDING",
                "CHANNEL_VERIFIED",
            }
        ):
            self.append_log(
                "Incomplete Sunday work detected; resuming post-service jobs."
            )

            self.start_post_service_supervisor()

    def check_post_service_status(
        self
    ):
        if not POST_STATUS_FILE.exists():
            return True, (
                "idle — waiting for service"
            ), False

        try:
            payload = read_json(
                POST_STATUS_FILE,
                {}
            )

            current_plan = read_json(
                SERMON_PLAN_FILE,
                {}
            )

            if (
                payload.get(
                    "plan_id"
                )
                and
                current_plan.get(
                    "plan_id"
                )
                and
                payload.get(
                    "plan_id"
                )
                !=
                current_plan.get(
                    "plan_id"
                )
            ):
                return True, (
                    "idle — waiting for this service"
                ), False

            state = str(
                payload.get(
                    "state",
                    ""
                )
            ).upper()

            message = str(
                payload.get(
                    "message",
                    ""
                )
            ).strip()

            if state == "COMPLETE":
                return True, (
                    "complete — safe to shut down"
                ), False

            if state == "RUNNING":
                return True, (
                    message
                    or
                    "post-service jobs are running"
                ), False

            if state == "ATTENTION":
                return False, (
                    message
                    or
                    "post-service review required"
                ), True

            return True, (
                message
                or
                "idle"
            ), False

        except Exception as exc:
            return False, (
                f"status error: {exc}"
            ), True

    def check_audio_sanity_status(
        self
    ):
        if not self.config.get(
            "audio_sanity_enabled",
            True
        ):
            return True, (
                "disabled"
            ), True

        if not AUDIO_STATUS_FILE.exists():
            return True, (
                "starting"
            ), True

        try:
            age = (
                time.time()
                -
                AUDIO_STATUS_FILE.stat().st_mtime
            )

            payload = read_json(
                AUDIO_STATUS_FILE,
                {}
            )

            if age > 15:
                return False, (
                    "meter data stale"
                ), True

            state = str(
                payload.get(
                    "state",
                    ""
                )
            ).upper()

            detail = str(
                payload.get(
                    "detail",
                    ""
                )
            ).strip()

            if state == "OK":
                return True, (
                    detail
                    or
                    "levels active"
                ), False

            if state in {
                "SILENT",
                "CLIPPING",
                "INPUT_MISSING",
                "ERROR",
            }:
                return False, (
                    detail
                    or
                    state.lower()
                ), True

            return True, (
                detail
                or
                state.lower()
                or
                "starting"
            ), True

        except Exception as exc:
            return False, (
                f"meter status error: {exc}"
            ), True

    def check_recording_health(
        self
    ):
        if not self.last_recording_state:
            return True, (
                "idle"
            ), False

        if not self.active_recording_path:
            find_alarm = float(
                self.config.get(
                    "recording_file_find_alarm_seconds",
                    30
                )
            )

            if (
                self.recording_started_at
                and
                time.time()
                -
                self.recording_started_at
                >=
                find_alarm
            ):
                return False, (
                    "OBS recording active but output file not found"
                ), False

            return True, (
                "recording — locating output file"
            ), True

        elapsed = (
            time.time()
            -
            self.last_recording_growth_time
            if self.last_recording_growth_time
            else 0
        )

        alarm_seconds = float(
            self.config.get(
                "recording_growth_alarm_seconds",
                60
            )
        )

        if (
            self.last_recording_growth_time
            and
            elapsed
            >=
            alarm_seconds
        ):
            return False, (
                f"FILE NOT GROWING for {elapsed:.0f}s"
            ), False

        try:
            size_mb = (
                Path(
                    self.active_recording_path
                ).stat().st_size
                /
                (
                    1024 ** 2
                )
            )

            return True, (
                f"growing — {size_mb:.0f} MB"
            ), False

        except Exception:
            return True, (
                "recording active"
            ), True

    def locate_current_recording_path(
        self,
        client
    ):
        try:
            record_status = client.get_record_status()

            candidate = (
                getattr(
                    record_status,
                    "output_path",
                    ""
                )
                or
                getattr(
                    record_status,
                    "outputPath",
                    ""
                )
            )

            if candidate:
                candidate_path = Path(
                    candidate
                )

                if candidate_path.exists():
                    return candidate_path

        except Exception:
            pass

        folder = Path(
            self.config.get(
                "recording_folder",
                r"D:\2026"
            )
        )

        if not folder.exists():
            return None

        candidates = []

        for child in folder.iterdir():
            if not child.is_file():
                continue

            if child.suffix.lower() not in {
                ".mp4",
                ".mkv",
                ".mov",
            }:
                continue

            try:
                stat = child.stat()
            except OSError:
                continue

            if (
                self.recording_started_at
                and
                stat.st_mtime
                <
                self.recording_started_at
                -
                30
            ):
                continue

            candidates.append(
                (
                    stat.st_mtime,
                    stat.st_size,
                    child,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            reverse=True
        )

        return candidates[
            0
        ][
            2
        ]

    def update_recording_growth(
        self,
        client
    ):
        if not self.last_recording_state:
            self.active_recording_path = ""
            self.last_recording_size = 0
            self.last_recording_growth_time = 0.0
            return

        path = self.locate_current_recording_path(
            client
        )

        if path is None:
            find_alarm = float(
                self.config.get(
                    "recording_file_find_alarm_seconds",
                    30
                )
            )

            if (
                self.recording_started_at
                and
                time.time()
                -
                self.recording_started_at
                >=
                find_alarm
            ):
                self.alarm(
                    (
                        "OBS says recording, but no recording output file "
                        f"has appeared in {self.config.get('recording_folder', r'D:\2026')}."
                    )
                )

            return

        path_text = str(
            path
        )

        try:
            size = path.stat().st_size
        except OSError:
            return

        minimum_growth = int(
            self.config.get(
                "recording_growth_min_bytes",
                1048576
            )
        )

        if (
            self.active_recording_path
            !=
            path_text
        ):
            self.active_recording_path = path_text
            self.last_recording_size = size
            self.last_recording_growth_time = time.time()
            return

        if (
            size
            >=
            self.last_recording_size
            +
            minimum_growth
        ):
            self.last_recording_size = size
            self.last_recording_growth_time = time.time()
            return

        alarm_seconds = float(
            self.config.get(
                "recording_growth_alarm_seconds",
                60
            )
        )

        if (
            self.last_recording_growth_time
            and
            time.time()
            -
            self.last_recording_growth_time
            >=
            alarm_seconds
        ):
            self.alarm(
                (
                    "OBS says recording, but the recording file has "
                    f"not grown for {alarm_seconds:.0f} seconds."
                )
            )

    def update_sunday_freeze(
        self,
        *,
        recording,
        streaming
    ):
        active = bool(
            recording
            or
            streaming
        )

        if active and not is_frozen():
            set_freeze(
                True,
                "Recording or streaming is active."
            )

        elif (
            not active
            and
            is_frozen()
            and
            not self.service_ending
        ):
            set_freeze(
                False
            )

    def check_completion_notification(
        self
    ):
        if not POST_STATUS_FILE.exists():
            return

        payload = read_json(
            POST_STATUS_FILE,
            {}
        )

        current_plan = read_json(
            SERMON_PLAN_FILE,
            {}
        )

        if (
            payload.get(
                "plan_id"
            )
            and
            current_plan.get(
                "plan_id"
            )
            and
            payload.get(
                "plan_id"
            )
            !=
            current_plan.get(
                "plan_id"
            )
        ):
            return

        plan_id = payload.get(
            "plan_id"
        )

        state = str(
            payload.get(
                "state",
                ""
            )
        ).upper()

        if (
            not plan_id
            or
            plan_id
            ==
            self.last_completion_plan_id
        ):
            return

        if state not in {
            "COMPLETE",
            "ATTENTION",
        }:
            return

        stages = payload.get(
            "stages",
            {}
        )

        self.last_completion_plan_id = plan_id

        if state == "COMPLETE":
            # Completion is useful information, but it does not need to
            # interrupt the volunteer with a modal popup. SYSTEM STATUS
            # already shows Post-service = Done.
            self.append_log(
                "After-service work is complete. Safe to shut down."
            )

            return

        # ATTENTION is often a normal waiting/review state (recording still
        # stabilizing, transcript still processing, YouTube waiting, stale
        # Planning status, etc.). Do NOT interrupt the volunteer with a
        # technical wall-of-text every time SSS opens.
        #
        # Only interrupt for a likely LOCAL RECORDING problem where immediate
        # human attention may protect the service recording. Everything else
        # remains visible in SYSTEM STATUS > After Service.
        recording_item = stages.get(
            "recording",
            {}
        )

        recording_state = str(
            recording_item.get(
                "state",
                ""
            )
        ).upper()

        recording_detail = str(
            recording_item.get(
                "detail",
                ""
            )
        ).strip()

        recording_lower = (
            recording_detail.lower()
        )

        critical_recording_terms = (
            "not found",
            "missing",
            "failed",
            "failure",
            "corrupt",
            "unreadable",
            "cannot open",
            "could not open",
            "file not growing",
            "recording stopped unexpectedly",
        )

        critical_recording_problem = (
            recording_state
            ==
            "ATTENTION"
            and
            any(
                term
                in
                recording_lower
                for term
                in critical_recording_terms
            )
        )

        if critical_recording_problem:
            self.append_log(
                (
                    "After-service recording needs attention: "
                    +
                    (
                        recording_detail
                        or
                        "Check the Sunday recording."
                    )
                )
            )

            messagebox.showwarning(
                "Check Sunday Recording",
                (
                    "THE SUNDAY RECORDING MAY NEED ATTENTION\n\n"
                    +
                    (
                        recording_detail
                        or
                        "SSS found a possible problem with the recording."
                    )
                    +
                    "\n\nOpen SYSTEM STATUS or Admin / Troubleshooting "
                    "for more details."
                ),
            )

            return

        # Routine review/waiting conditions are quiet. The volunteer sees
        # the yellow After Service status instead of a startup popup.
        review_items = []

        for key, friendly in (
            (
                "recording",
                "Recording",
            ),
            (
                "transcript",
                "Transcript",
            ),
            (
                "sermon_ai",
                "Sermon processing",
            ),
            (
                "chapters",
                "Chapters",
            ),
            (
                "youtube",
                "YouTube",
            ),
            (
                "planning",
                "Planning",
            ),
            (
                "thumbnail",
                "Thumbnail",
            ),
        ):
            item = stages.get(
                key,
                {}
            )

            item_state = str(
                item.get(
                    "state",
                    ""
                )
            ).upper()

            if item_state in {
                "ATTENTION",
                "WAITING",
                "RUNNING",
            }:
                review_items.append(
                    friendly
                )

        if review_items:
            self.append_log(
                (
                    "After-service items are still waiting/reviewing: "
                    +
                    ", ".join(
                        review_items
                    )
                    +
                    ". See SYSTEM STATUS if needed."
                )
            )

        else:
            self.append_log(
                (
                    "After-service review is not complete yet. "
                    "See SYSTEM STATUS if needed."
                )
            )

    def open_logs_folder(
        self
    ):
        LOG_ROOT.mkdir(
            parents=True,
            exist_ok=True
        )

        try:
            os.startfile(
                LOG_ROOT
            )
        except Exception as exc:
            messagebox.showerror(
                "Logs",
                str(
                    exc
                )
            )

    def run_safe_test_mode(
        self
    ):
        if not TEST_MODE_SCRIPT.exists():
            messagebox.showerror(
                "Test Mode",
                "sss_test_mode.py is missing."
            )
            return

        python = (
            BASE
            /
            "venv"
            /
            "Scripts"
            /
            "python.exe"
        )

        try:
            subprocess.Popen(
                [
                    "cmd.exe",
                    "/k",
                    (
                        f'"{python}" '
                        f'"{TEST_MODE_SCRIPT}"'
                    ),
                ],
                cwd=BASE,
            )
        except Exception as exc:
            messagebox.showerror(
                "Test Mode",
                str(
                    exc
                )
            )

    def show_action_center(
        self
    ):
        suggestions = {
            "SERMON": (
                "Run Import-Latest-Sermon-Email.bat or verify the pastor "
                "email/sermon_plan.json."
            ),
            "SERMON_CHAPTERS": (
                "Use ADMIN → RESYNC SERMON CHAPTER HOTKEYS. If OBS was "
                "already open, close/reopen OBS before the service so the "
                "Additional Chapter Hotkeys plugin reloads the new labels."
            ),
            "PLANNING": (
                "Use ADMIN → SYNC PLANNING SCRIPTURE. If login expired, "
                "open the saved Planning browser profile."
            ),
            "YOUTUBE": (
                "Use ADMIN → RETRY / CHECK YOUTUBE UPLOAD. If Studio login "
                "expired, use OPEN YOUTUBE STUDIO LOGIN."
            ),
            "OBS": (
                "Wait for OBS to finish opening. If it stays red, verify "
                "OBS WebSocket is enabled on port 4455."
            ),
            "AUDIO": (
                "Check the TASCAM/Windows playback endpoint and USB connection."
            ),
            "AUDIO_HEALTH": (
                "Confirm the OBS 'main' source is receiving level and is not "
                "muted. Sustained silence/clipping will alarm during recording."
            ),
            "RECORDING_HEALTH": (
                "Check D:\\2026 immediately. OBS may say Recording even if "
                "the output file has stopped growing."
            ),
            "INTERNET": (
                "Local recording is still safe. Leave SSS running; YouTube "
                "will retry when internet returns."
            ),
            "POST": (
                "Use ADMIN → RESUME POST-SERVICE JOBS and review the stage "
                "that is marked for attention."
            ),
            "PTZ": (
                "Open ADMIN / TROUBLESHOOTING, enter the camera IP/address "
                "in PTZ Camera — Persistent Settings, then press SAVE & TEST."
            ),
            "PRESENTER": (
                "Make sure loopMIDI is running, Presenter is open with MIDI "
                "input set to Presenter, and the first Scripture verse is "
                "selected before the service."
            ),
        }

        lines = []

        for key, friendly in (
            ("SERMON", "Sermon"),
            ("SERMON_CHAPTERS", "Sermon chapters"),
            ("PLANNING", "Planning"),
            ("YOUTUBE", "YouTube"),
            ("OBS", "OBS"),
            ("PRESENTER", "Presenter"),
            ("AUDIO", "Audio endpoint"),
            ("AUDIO_HEALTH", "Audio sanity"),
            ("RECORDING_HEALTH", "Recording"),
            ("INTERNET", "Internet"),
            ("POST", "Post-service"),
            ("PTZ", "PTZ camera"),
        ):
            var = self.status_vars.get(
                key
            )

            if var is None:
                continue

            value = var.get()

            if (
                "⚠"
                in
                value
                or
                "❌"
                in
                value
                or
                value.upper().startswith(
                    "CHECK"
                )
                or
                value.upper().startswith(
                    "FIX"
                )
            ):
                lines.append(
                    (
                        f"{friendly}\n"
                        f"{value}\n"
                        f"Next: {suggestions.get(key, 'Review this item.')}"
                    )
                )

        if not lines:
            message = (
                "No current warning or failure needs attention."
            )
        else:
            message = "\n\n".join(
                lines
            )

        messagebox.showinfo(
            "SSS Action Center",
            message
        )

    def set_chapter_test_mode(
        self,
        enabled,
        *,
        quiet=False
    ):
        enabled = bool(
            enabled
        )

        if (
            enabled
            ==
            self.chapter_test_mode
        ):
            return True

        if (
            self.chapter_action_running
            and
            enabled
        ):
            if not quiet:
                messagebox.showwarning(
                    "Chapter / LT Test",
                    (
                        "Wait for the current chapter/lower-third "
                        "action to finish before turning Test Mode ON."
                    ),
                )

            if self.admin_chapter_test_var is not None:
                self.admin_chapter_test_var.set(
                    self.chapter_test_mode
                )

            return False

        if enabled:
            client = self.connect_obs()

            if client is None:
                if not quiet:
                    messagebox.showwarning(
                        "Chapter / LT Test",
                        (
                            "OBS must be open and reachable to test "
                            "the lower-third hotkeys."
                        ),
                    )

                if self.admin_chapter_test_var is not None:
                    self.admin_chapter_test_var.set(
                        False
                    )

                return False

            status = get_obs_status(
                client
            )

            if (
                status[
                    "recording"
                ]
                or
                status[
                    "streaming"
                ]
            ):
                if not quiet:
                    messagebox.showwarning(
                        "Chapter / LT Test",
                        (
                            "Test mode is only available while OBS is "
                            "NOT recording and NOT streaming.\n\n"
                            "This prevents a test lower third from "
                            "appearing in a live service."
                        ),
                    )

                if self.admin_chapter_test_var is not None:
                    self.admin_chapter_test_var.set(
                        False
                    )

                return False

            # IMPORTANT: do not call reset_rotation(). Test mode uses its
            # own index, leaving chapter_rotation_state.json untouched.
            self.chapter_test_mode = True
            self.chapter_test_index = 0

            if self.admin_chapter_test_var is not None:
                self.admin_chapter_test_var.set(
                    True
                )

            if self.admin_chapter_test_status_var is not None:
                real_position = next_button_text(
                    max_length=44
                )

                self.admin_chapter_test_status_var.set(
                    (
                        "TEST MODE ON — starts at Prayer. "
                        "No recording needed. "
                        f"Normal position preserved: {real_position}"
                    )
                )

            if hasattr(
                self,
                "chapter_action_descriptor_var"
            ):
                self.chapter_action_descriptor_var.set(
                    (
                        "TEST MODE\n"
                        "LOWER THIRD LIVE\n"
                        "marker simulated"
                    )
                )

            self.append_log(
                (
                    "ADMIN TEST MODE enabled: chapter/LT test sequence "
                    "reset to Prayer; real sermon chapter position preserved."
                )
            )

        else:
            # If the Scripture-reading visual was being tested, return OBS
            # to the webcam before leaving Test Mode.
            if self.scripture_reading_active:
                try:
                    send_studio_transition()
                except Exception:
                    pass

                self.scripture_reading_active = False
                self.scripture_reading_busy = False
                self.scripture_verse_index = -1

            self.chapter_test_mode = False
            self.chapter_test_index = 0

            if self.admin_chapter_test_var is not None:
                self.admin_chapter_test_var.set(
                    False
                )

            if self.admin_chapter_test_status_var is not None:
                real_position = next_button_text(
                    max_length=44
                )

                self.admin_chapter_test_status_var.set(
                    (
                        "OFF — normal service mode. "
                        f"Current position: {real_position}"
                    )
                )

            if hasattr(
                self,
                "chapter_action_descriptor_var"
            ):
                self.chapter_action_descriptor_var.set(
                    (
                        "LOWER THIRD +\n"
                        "CHAPTER MARKER"
                    )
                )

            if not quiet:
                self.append_log(
                    (
                        "ADMIN TEST MODE disabled: restored normal "
                        "chapter/LT controls at the real sermon position."
                    )
                )

        self.refresh_chapter_rotation_button()

        return True

    def on_admin_chapter_test_toggle(
        self
    ):
        if self.admin_chapter_test_var is None:
            return

        requested = bool(
            self.admin_chapter_test_var.get()
        )

        self.set_chapter_test_mode(
            requested
        )

    def close_admin_panel(
        self
    ):
        # Closing Admin ALWAYS leaves test mode. Because test mode has a
        # separate in-memory index, returning to normal instantly reveals
        # the exact real position that existed before testing.
        if self.chapter_test_mode:
            self.set_chapter_test_mode(
                False,
                quiet=True,
            )

            self.append_log(
                (
                    "Admin closed: Chapter/LT Test Mode automatically "
                    "turned OFF; real sermon position restored."
                )
            )

        window = self.admin_window

        self.admin_window = None
        self.admin_chapter_test_var = None
        self.admin_chapter_test_status_var = None

        if (
            window is not None
            and
            window.winfo_exists()
        ):
            try:
                window.unbind_all(
                    "<MouseWheel>"
                )
            except Exception:
                pass

            window.destroy()

    def open_admin_panel(
        self
    ):
        if (
            self.admin_window is not None
            and
            self.admin_window.winfo_exists()
        ):
            self.admin_window.lift()
            return

        window = tk.Toplevel(
            self.root
        )

        self.admin_window = window

        window.title(
            "SSS Admin / Troubleshooting"
        )

        if CHURCH_WINDOW_ICON.exists():
            try:
                window.iconbitmap(
                    str(
                        CHURCH_WINDOW_ICON
                    )
                )
            except Exception:
                pass

        window.geometry(
            "560x900"
        )

        window.protocol(
            "WM_DELETE_WINDOW",
            self.close_admin_panel,
        )

        scroll_container = ttk.Frame(
            window
        )

        scroll_container.pack(
            fill="both",
            expand=True
        )

        admin_canvas = tk.Canvas(
            scroll_container,
            highlightthickness=0,
        )

        admin_scrollbar = ttk.Scrollbar(
            scroll_container,
            orient="vertical",
            command=admin_canvas.yview,
        )

        admin_canvas.configure(
            yscrollcommand=admin_scrollbar.set
        )

        admin_canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        admin_scrollbar.pack(
            side="right",
            fill="y",
        )

        frame = ttk.Frame(
            admin_canvas,
            padding=14
        )

        admin_frame_window = admin_canvas.create_window(
            (0, 0),
            window=frame,
            anchor="nw",
        )

        def _admin_frame_configure(
            event,
            canvas=admin_canvas,
        ):
            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        frame.bind(
            "<Configure>",
            _admin_frame_configure,
        )

        def _admin_canvas_configure(
            event,
            canvas=admin_canvas,
            window_id=admin_frame_window,
        ):
            canvas.itemconfig(
                window_id,
                width=event.width,
            )

        admin_canvas.bind(
            "<Configure>",
            _admin_canvas_configure,
        )

        def _admin_mousewheel(
            event,
            canvas=admin_canvas,
        ):
            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units",
            )

        def _admin_bind_mousewheel(
            event,
            canvas=admin_canvas,
        ):
            canvas.bind_all(
                "<MouseWheel>",
                _admin_mousewheel,
            )

        def _admin_unbind_mousewheel(
            event,
            canvas=admin_canvas,
        ):
            canvas.unbind_all(
                "<MouseWheel>"
            )

        admin_canvas.bind(
            "<Enter>",
            _admin_bind_mousewheel,
        )

        admin_canvas.bind(
            "<Leave>",
            _admin_unbind_mousewheel,
        )

        ttk.Label(
            frame,
            text="ADMIN / TROUBLESHOOTING",
            font=(
                "Segoe UI",
                16,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                12
            )
        )

        freeze_text = (
            "SUNDAY FREEZE ACTIVE — configuration changes should wait."
            if is_frozen()
            else
            "Maintenance is currently unlocked."
        )

        ttk.Label(
            frame,
            text=freeze_text,
            wraplength=500,
        ).pack(
            pady=(
                0,
                12
            )
        )

        # Persistent PTZ camera configuration. This writes to
        # ptz_camera_config.json, NOT sunday_config.json, so replacing
        # normal SSS update files cannot erase the camera address.
        ptz_settings = self.get_ptz_settings()

        ptz_frame = ttk.LabelFrame(
            frame,
            text="PTZ Camera — Persistent Settings",
            padding=10,
        )

        ptz_frame.pack(
            fill="x",
            pady=(
                0,
                10
            )
        )

        self.admin_ptz_ip_var = tk.StringVar(
            value=str(
                ptz_settings.get(
                    "ptz_camera_ip",
                    ""
                )
            )
        )

        self.admin_ptz_worship_var = tk.StringVar(
            value=str(
                ptz_settings.get(
                    "ptz_worship_preset",
                    1
                )
            )
        )

        self.admin_ptz_pastor_var = tk.StringVar(
            value=str(
                ptz_settings.get(
                    "ptz_pastor_preset",
                    2
                )
            )
        )

        ttk.Label(
            ptz_frame,
            text="Camera IP / Address",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=4,
            pady=4,
        )

        ip_entry = ttk.Entry(
            ptz_frame,
            textvariable=self.admin_ptz_ip_var,
            width=25,
        )

        ip_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
            pady=4,
        )

        self.bind_tooltip(
            ip_entry,
            (
                "The PTZ camera's network address. This is stored in the "
                "persistent PTZ settings file so normal SSS updates do not "
                "erase it."
            ),
        )

        save_test_button = ttk.Button(
            ptz_frame,
            text="SAVE & TEST",
            command=self.save_admin_ptz_settings,
        )

        save_test_button.grid(
            row=0,
            column=2,
            sticky="ew",
            padx=4,
            pady=4,
        )

        self.bind_tooltip(
            save_test_button,
            (
                "Saves the PTZ camera address and preset numbers, then recalls "
                "the Pastor preset as a connection test."
            ),
        )

        ttk.Label(
            ptz_frame,
            text="Worship preset",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=4,
            pady=4,
        )

        worship_preset_entry = ttk.Entry(
            ptz_frame,
            textvariable=self.admin_ptz_worship_var,
            width=6,
        )

        worship_preset_entry.grid(
            row=1,
            column=1,
            sticky="w",
            padx=4,
            pady=4,
        )

        self.bind_tooltip(
            worship_preset_entry,
            (
                "PTZ preset number used by the WORSHIP VIEW button on the "
                "main volunteer screen."
            ),
        )

        ttk.Label(
            ptz_frame,
            text="Pastor / startup preset",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=4,
            pady=4,
        )

        pastor_preset_entry = ttk.Entry(
            ptz_frame,
            textvariable=self.admin_ptz_pastor_var,
            width=6,
        )

        pastor_preset_entry.grid(
            row=2,
            column=1,
            sticky="w",
            padx=4,
            pady=4,
        )

        self.bind_tooltip(
            pastor_preset_entry,
            (
                "PTZ preset number used by the PASTOR VIEW button and by the "
                "automatic camera position when SSS opens."
            ),
        )

        ttk.Label(
            ptz_frame,
            text=(
                "Press Enter in the camera-address box or click SAVE & TEST. "
                "The Pastor preset will move as the connection test."
            ),
            wraplength=500,
        ).grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="w",
            padx=4,
            pady=(
                4,
                0
            ),
        )

        ptz_frame.columnconfigure(
            1,
            weight=1
        )

        ip_entry.bind(
            "<Return>",
            lambda event:
                self.save_admin_ptz_settings()
        )

        chapter_test_frame = ttk.LabelFrame(
            frame,
            text="Chapter / Lower-Third Test",
            padding=10,
        )

        chapter_test_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        self.admin_chapter_test_var = tk.BooleanVar(
            value=False
        )

        self.admin_chapter_test_status_var = tk.StringVar(
            value=(
                "OFF — normal service mode. Current position: "
                +
                next_button_text(
                    max_length=44
                )
            )
        )

        chapter_test_toggle = ttk.Checkbutton(
            chapter_test_frame,
            text="ENABLE CHAPTER / LT TEST MODE",
            variable=self.admin_chapter_test_var,
            command=self.on_admin_chapter_test_toggle,
        )

        chapter_test_toggle.pack(
            anchor="w"
        )

        self.bind_tooltip(
            chapter_test_toggle,
            (
                "Admin-only test mode for the sermon button. It starts a "
                "temporary test sequence at Prayer, lets you verify the lower "
                "third actions without recording, and never changes the real "
                "sermon chapter position. Closing Admin turns it off."
            ),
        )

        ttk.Label(
            chapter_test_frame,
            textvariable=self.admin_chapter_test_status_var,
            wraplength=500,
        ).pack(
            fill="x",
            anchor="w",
            pady=(
                4,
                0
            ),
        )

        ttk.Label(
            chapter_test_frame,
            text=(
                "While ON, use the normal SERMON button on the main SSS. "
                "The test starts at Prayer and steps through Scripture, "
                "points, Ending Prayer, and Benediction. LT1 point graphics "
                "still run for 11 seconds. No real chapter marker is written."
            ),
            wraplength=500,
        ).pack(
            fill="x",
            anchor="w",
            pady=(
                5,
                0
            ),
        )

        actions = [
            (
                "WHAT NEEDS ATTENTION?",
                self.show_action_center,
            ),
            (
                "FULL SYSTEM DIAGNOSTICS (READ-ONLY)",
                self.open_full_system_diagnostics,
            ),
            (
                "BACKUP / RECOVERY",
                self.open_recovery_center,
            ),
            (
                "EVENT HISTORY",
                self.open_event_history,
            ),
            (
                "SECURITY / SECRETS VAULT",
                self.open_security_center,
            ),
            (
                "SOFTWARE UPDATES / ROLLBACK",
                self.open_updates_center,
            ),
            (
                "RESET SERMON CHAPTER ROTATION",
                self.reset_sermon_chapter_rotation,
            ),
            (
                "ADD MANUAL CHAPTER",
                self.manual_chapter,
            ),
            (
                "RESYNC SERMON CHAPTER HOTKEYS",
                self.sync_chapter_hotkeys_async,
            ),
            (
                "SYNC PLANNING SCRIPTURE",
                self.update_planning_async,
            ),
            (
                "RETRY / CHECK YOUTUBE UPLOAD",
                self.start_youtube_upload_waiter,
            ),
            (
                "RESUME POST-SERVICE JOBS",
                self.start_post_service_supervisor,
            ),
            (
                "RUN SAFE TEST MODE",
                self.run_safe_test_mode,
            ),
            (
                "OPEN LOGS FOLDER",
                self.open_logs_folder,
            ),
        ]

        if YOUTUBE_STUDIO_LOGIN.exists():
            actions.append(
                (
                    "OPEN YOUTUBE STUDIO LOGIN",
                    lambda:
                        os.startfile(
                            YOUTUBE_STUDIO_LOGIN
                        ),
                )
            )

        admin_action_tooltips = {
            "WHAT NEEDS ATTENTION?": (
                "Summarizes the items that currently need review or action."
            ),
            "FULL SYSTEM DIAGNOSTICS (READ-ONLY)": (
                "Runs the full SSS readiness check without starting or stopping "
                "recording/streaming, moving cameras/slides, or changing audio mute."
            ),
            "BACKUP / RECOVERY": (
                "Creates a fresh weekly rollback snapshot, then opens recovery "
                "snapshots, Last Known Good, and guarded restore. Restore is "
                "blocked during live outputs. Also covers checking/migrating "
                "older church profile formats (Advanced page)."
            ),
            "EVENT HISTORY": (
                "Shows a human-friendly timeline of SSS actions and warnings across services."
            ),
            "SECURITY / SECRETS VAULT": (
                "Manages local protected credentials in Windows Credential Manager. "
                "Secrets remain outside portable church profiles."
            ),
            "SOFTWARE UPDATES / ROLLBACK": (
                "Opens the application updater. Updates are blocked during live OBS "
                "Recording/Streaming and keep church data separate from app files."
            ),
            "RESET SERMON CHAPTER ROTATION": (
                "Returns the sermon chapter sequence to Prayer. In Chapter/LT "
                "Test Mode, this resets only the temporary test sequence."
            ),
            "ADD MANUAL CHAPTER": (
                "Adds a generic manual chapter marker to the current OBS "
                "recording. OBS must be recording."
            ),
            "RESYNC SERMON CHAPTER HOTKEYS": (
                "Rebuilds the named sermon chapter hotkeys from the active "
                "SSS sermon plan."
            ),
            "SYNC PLANNING SCRIPTURE": (
                "Checks and updates the sermon Scripture in WorshipTools "
                "Planning for the correct upcoming service."
            ),
            "RETRY / CHECK YOUTUBE UPLOAD": (
                "Checks or retries the automatic YouTube Studio sermon upload."
            ),
            "RESUME POST-SERVICE JOBS": (
                "Restarts unfinished after-service processing such as chapter "
                "verification, sermon processing, and upload supervision."
            ),
            "RUN SAFE TEST MODE": (
                "Runs the SSS reliability checks without starting a recording "
                "or livestream."
            ),
            "OPEN LOGS FOLDER": (
                "Opens the SSS logs folder for troubleshooting."
            ),
            "OPEN YOUTUBE STUDIO LOGIN": (
                "Opens the dedicated YouTube Studio browser/profile so its "
                "login can be refreshed when needed."
            ),
        }

        for label, command in actions:
            action_button = ttk.Button(
                frame,
                text=label,
                command=command,
            )

            action_button.pack(
                fill="x",
                pady=5,
            )

            self.bind_tooltip(
                action_button,
                admin_action_tooltips.get(
                    label,
                    "Administrative maintenance action.",
                ),
            )

        ttk.Label(
            frame,
            text=(
                "Volunteer controls stay on the main screen. "
                "These maintenance actions are intentionally separated."
            ),
            wraplength=470,
        ).pack(
            pady=(
                15,
                0
            )
        )

    def get_ptz_settings(
        self
    ):
        """
        Return camera settings in the legacy PTZ-shaped structure used by
        the existing SSS camera workflow.

        PROFILE camera settings are translated here; LEGACY still reads the
        existing persistent ptz_camera_config.json.
        """
        try:
            profile_camera = get_profile_camera_settings(
                load_active_profile()
            )

            if (
                profile_camera.get(
                    "settings_source"
                )
                ==
                "profile"
            ):
                provider = profile_camera.get(
                    "provider",
                    "Not configured"
                )

                movable = (
                    provider
                    ==
                    "PTZOptics / HTTP-CGI"
                )

                return {
                    "ptz_camera_enabled": movable,
                    "ptz_camera_ip": profile_camera.get(
                        "host",
                        ""
                    ),
                    "ptz_camera_port": profile_camera.get(
                        "port",
                        80
                    ),
                    "ptz_camera_provider": provider,
                    "ptz_profile_mode": True,
                    "ptz_auto_recall_on_sss_start": bool(
                        profile_camera.get(
                            "auto_recall_on_start",
                            True
                        )
                    )
                    and
                    movable,
                    "ptz_startup_preset": int(
                        profile_camera.get(
                            "startup_preset",
                            2
                        )
                    ),
                    "ptz_worship_preset": int(
                        profile_camera.get(
                            "worship_preset",
                            1
                        )
                    ),
                    "ptz_pastor_preset": int(
                        profile_camera.get(
                            "pastor_preset",
                            2
                        )
                    ),
                }

        except Exception:
            pass

        try:
            settings = load_ptz_settings(
                self.config
            )

            settings[
                "ptz_profile_mode"
            ] = False

            return settings

        except Exception:
            return {
                "ptz_camera_enabled": True,
                "ptz_camera_ip": "",
                "ptz_auto_recall_on_sss_start": True,
                "ptz_startup_preset": 2,
                "ptz_worship_preset": 1,
                "ptz_pastor_preset": 2,
                "ptz_profile_mode": False,
            }

    def save_admin_ptz_settings(
        self,
        *,
        test_after_save=True
    ):
        if (
            self.admin_ptz_ip_var is None
            or
            self.admin_ptz_worship_var is None
            or
            self.admin_ptz_pastor_var is None
        ):
            return

        camera_ip = self.admin_ptz_ip_var.get().strip()
        worship_text = self.admin_ptz_worship_var.get().strip()
        pastor_text = self.admin_ptz_pastor_var.get().strip()

        if not camera_ip:
            messagebox.showwarning(
                "PTZ Camera",
                "Enter the PTZ camera IP/address first."
            )
            return

        try:
            worship = int(
                worship_text
            )

            pastor = int(
                pastor_text
            )

            settings = save_ptz_settings(
                {
                    "ptz_camera_enabled": True,
                    "ptz_camera_ip": camera_ip,
                    "ptz_worship_preset": worship,
                    "ptz_pastor_preset": pastor,
                    "ptz_startup_preset": pastor,
                    "ptz_auto_recall_on_sss_start": True,
                },
                self.config,
            )

        except Exception as exc:
            messagebox.showerror(
                "PTZ Camera",
                (
                    "Could not save PTZ settings:\n\n"
                    f"{exc}"
                ),
            )
            return

        # Keep this running SSS session in sync too. The durable source
        # remains ptz_camera_config.json.
        self.config.update(
            {
                key: value
                for key, value in settings.items()
                if key.startswith(
                    "ptz_"
                )
            }
        )

        self.admin_ptz_ip_var.set(
            settings.get(
                "ptz_camera_ip",
                ""
            )
        )

        self.admin_ptz_worship_var.set(
            str(
                settings.get(
                    "ptz_worship_preset",
                    1
                )
            )
        )

        self.admin_ptz_pastor_var.set(
            str(
                settings.get(
                    "ptz_pastor_preset",
                    2
                )
            )
        )

        self.append_log(
            (
                "PTZ settings saved permanently: "
                f"{settings.get('ptz_camera_ip', '')} | "
                f"Worship {settings.get('ptz_worship_preset', 1)} | "
                f"Pastor {settings.get('ptz_pastor_preset', 2)}"
            )
        )

        self.run_preflight_async()

        if test_after_save:
            self.recall_ptz_preset_async(
                int(
                    settings.get(
                        "ptz_pastor_preset",
                        2
                    )
                ),
                "Pastor / test"
            )
        else:
            messagebox.showinfo(
                "PTZ Camera",
                (
                    "PTZ settings saved.\n\n"
                    "They are stored separately from sunday_config.json "
                    "and will survive normal SSS updates."
                ),
            )

    def check_ptz_status(
        self
    ):
        settings = self.get_ptz_settings()

        if settings.get(
            "ptz_profile_mode",
            False
        ):
            provider = str(
                settings.get(
                    "ptz_camera_provider",
                    "Not configured"
                )
            )

            if provider in {
                "Fixed camera",
                "None",
            }:
                return True, (
                    provider
                    +
                    " — no PTZ controls"
                ), True

            ready, detail = profile_camera_ready()

            return (
                ready,
                detail,
                not ready,
            )

        if not settings.get(
            "ptz_camera_enabled",
            True
        ):
            return True, (
                "disabled"
            ), True

        camera_ip = str(
            settings.get(
                "ptz_camera_ip",
                ""
            )
        ).strip()

        if not camera_ip:
            return False, (
                "camera IP missing — enter it in Admin"
            ), True

        if PTZ_CAMERA_STATUS.exists():
            try:
                payload = read_json(
                    PTZ_CAMERA_STATUS,
                    {}
                )

                age = (
                    time.time()
                    -
                    PTZ_CAMERA_STATUS.stat().st_mtime
                )

                state = str(
                    payload.get(
                        "state",
                        ""
                    )
                ).upper()

                message = str(
                    payload.get(
                        "message",
                        ""
                    )
                ).strip()

                if (
                    state
                    ==
                    "ERROR"
                    and
                    age
                    <
                    300
                ):
                    return False, (
                        message
                        or
                        "camera control error"
                    ), True

                if (
                    state
                    ==
                    "OK"
                    and
                    age
                    <
                    300
                ):
                    return True, (
                        message
                        or
                        f"{camera_ip} ready"
                    ), False

            except Exception:
                pass

        return True, (
            f"{camera_ip} configured"
        ), False

    def recall_ptz_preset_async(
        self,
        preset,
        label
    ):
        settings = self.get_ptz_settings()

        if not settings.get(
            "ptz_camera_enabled",
            True
        ):
            self.append_log(
                "PTZ camera control is disabled."
            )
            return

        camera_ip = str(
            settings.get(
                "ptz_camera_ip",
                ""
            )
        ).strip()

        if not camera_ip:
            messagebox.showwarning(
                "PTZ Camera",
                (
                    "PTZ camera IP is not configured.\n\n"
                    "Open ADMIN / TROUBLESHOOTING and enter the "
                    "camera address in the PTZ Camera section."
                ),
            )
            return

        if not PTZ_CAMERA_SCRIPT.exists():
            messagebox.showerror(
                "PTZ Camera",
                "ptz_camera_control.py is missing."
            )
            return

        def worker():
            if settings.get(
                "ptz_profile_mode",
                False
            ):
                try:
                    recall_profile_camera_preset(
                        int(
                            preset
                        )
                    )

                    self.post_ui(
                        self.append_log,
                        (
                            "Camera PROFILE → "
                            +
                            str(
                                label
                            )
                            +
                            " (preset "
                            +
                            str(
                                preset
                            )
                            +
                            ")."
                        ),
                    )

                    self.post_ui(
                        self.run_preflight_async
                    )

                except Exception as exc:
                    self.post_ui(
                        self.append_log,
                        (
                            "Camera PROFILE "
                            +
                            str(
                                label
                            )
                            +
                            " failed: "
                            +
                            str(
                                exc
                            )
                        ),
                    )

                    self.post_ui(
                        messagebox.showwarning,
                        "Camera",
                        (
                            "Profile camera did not move.\n\n"
                            +
                            str(
                                exc
                            )
                        ),
                    )

                return

            python = (
                BASE
                /
                "venv"
                /
                "Scripts"
                /
                "python.exe"
            )

            try:
                cp = subprocess.run(
                    [
                        str(
                            python
                        ),
                        str(
                            PTZ_CAMERA_SCRIPT
                        ),
                        str(
                            int(
                                preset
                            )
                        ),
                    ],
                    cwd=BASE,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if os.name
                        ==
                        "nt"
                        else 0
                    ),
                )

                if cp.returncode == 0:
                    self.post_ui(
                        self.append_log,
                        (
                            f"PTZ camera → {label} "
                            f"(preset {preset})."
                        )
                    )

                    self.post_ui(
                        self.run_preflight_async
                    )

                else:
                    detail = (
                        cp.stderr.strip()
                        or
                        cp.stdout.strip()
                        or
                        "unknown PTZ error"
                    )

                    self.post_ui(
                        self.append_log,
                        (
                            f"PTZ {label} failed: "
                            f"{detail}"
                        )
                    )

                    self.post_ui(
                        self.run_preflight_async
                    )

            except Exception as exc:
                self.post_ui(
                    self.append_log,
                    (
                        f"PTZ {label} failed: "
                        f"{exc}"
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def ptz_startup_position(
        self
    ):
        settings = self.get_ptz_settings()

        preset = int(
            settings.get(
                "ptz_startup_preset",
                2
            )
        )

        self.recall_ptz_preset_async(
            preset,
            "Pastor / startup"
        )

    def ptz_worship(
        self
    ):
        settings = self.get_ptz_settings()

        preset = int(
            settings.get(
                "ptz_worship_preset",
                1
            )
        )

        self.recall_ptz_preset_async(
            preset,
            "Worship"
        )

    def ptz_pastor(
        self
    ):
        settings = self.get_ptz_settings()

        preset = int(
            settings.get(
                "ptz_pastor_preset",
                2
            )
        )

        self.recall_ptz_preset_async(
            preset,
            "Pastor"
        )

    def active_profile_obs_settings(
        self
    ):
        try:
            return get_profile_obs_settings(
                load_active_profile()
            )
        except Exception:
            return {
                "settings_source": "legacy",
                "scene_collection": "",
                "normal_scene": "",
                "scripture_scene": "",
                "sermon_scene": "",
            }

    def obs_profile_mode_enabled(
        self
    ):
        settings = self.active_profile_obs_settings()

        return (
            settings.get(
                "settings_source"
            )
            ==
            "profile"
        )

    def load_obs_view_to_preview(
        self,
        role,
        legacy_callback
    ):
        """
        Load a profile-mapped OBS scene into Preview when PROFILE mode is on.

        Any missing profile setting or WebSocket failure immediately falls back
        to the existing Perry hotkey path. This is the migration safety net.
        """
        settings = self.active_profile_obs_settings()

        if settings.get(
            "settings_source"
        ) != "profile":
            legacy_callback()
            return (
                "legacy",
                ""
            )

        key = (
            "scripture_scene"
            if role == "scripture"
            else
            "normal_scene"
        )

        scene_name = str(
            settings.get(
                key,
                ""
            )
            or
            ""
        ).strip()

        if not scene_name:
            self.post_ui(
                self.append_log,
                (
                    "OBS profile has no "
                    +
                    role
                    +
                    " scene; using legacy hotkey fallback."
                ),
            )

            legacy_callback()
            return (
                "legacy-fallback",
                ""
            )

        try:
            client = self.connect_obs()

            if client is None:
                raise RuntimeError(
                    "OBS WebSocket is not reachable."
                )

            load_scene_to_preview(
                client,
                scene_name,
            )

            self.post_ui(
                self.append_log,
                (
                    "OBS PROFILE -> Preview: "
                    +
                    scene_name
                ),
            )

            return (
                "profile",
                scene_name,
            )

        except Exception as exc:
            self.post_ui(
                self.append_log,
                (
                    "OBS PROFILE scene failed ("
                    +
                    str(
                        exc
                    )
                    +
                    "); using legacy hotkey fallback."
                ),
            )

            legacy_callback()

            return (
                "legacy-fallback",
                scene_name,
            )

    def connect_obs(
        self
    ):
        try:
            return connect_obs_with_vault(
                self.config,
                timeout=4
            )
        except Exception:
            return None

    def ensure_scene_collection(
        self,
        client
    ):
        profile_obs = self.active_profile_obs_settings()

        if (
            profile_obs.get(
                "settings_source"
            )
            ==
            "profile"
            and
            profile_obs.get(
                "scene_collection"
            )
        ):
            expected = profile_obs.get(
                "scene_collection",
                ""
            )
        else:
            expected = self.config.get(
                "scene_collection",
                ""
            )

        if not expected:
            return True, (
                "not configured"
            )

        try:
            response = (
                client.get_scene_collection_list()
            )

            current = getattr(
                response,
                "current_scene_collection_name",
                ""
            )

            if current == expected:
                return True, current

            if (
                self.config.get(
                    "auto_fix_scene_collection",
                    True
                )
            ):
                status = (
                    get_obs_status(
                        client
                    )
                )

                if not (
                    status[
                        "recording"
                    ]
                    or
                    status[
                        "streaming"
                    ]
                ):
                    client.send(
                        "SetCurrentSceneCollection",
                        {
                            "sceneCollectionName":
                                expected
                        },
                        raw=True,
                    )

                    time.sleep(
                        2
                    )

                    return True, (
                        f"{expected} "
                        "(auto-selected)"
                    )

            return False, (
                f"currently: {current}"
            )

        except Exception as exc:
            return False, str(
                exc
            )

    def check_audio(
        self
    ):
        """
        Audio readiness.

        PROFILE + OBS Audio Inputs validates the selected OBS inputs.
        PROFILE + None is a valid no-audio-control configuration.

        LEGACY keeps the existing Windows endpoint discovery exactly as before.
        """
        try:
            profile_audio = get_profile_audio_settings(
                load_active_profile()
            )

            if (
                profile_audio.get(
                    "settings_source"
                )
                ==
                "profile"
            ):
                ready, detail = profile_audio_ready()

                return (
                    ready,
                    detail,
                )

        except Exception:
            pass

        target = str(
            self.config.get(
                "audio_loopback_name",
                ""
            )
        ).strip()

        endpoint_name = re.sub(
            r"\s*\[Loopback\]\s*$",
            "",
            target,
            flags=re.IGNORECASE
        ).strip()

        label = self.config.get(
            "audio_loopback_label",
            "Audio Interface"
        )

        if not endpoint_name:
            return False, (
                f"{label} endpoint not configured"
            )

        ps = (
            "$ErrorActionPreference='SilentlyContinue'; "
            "$names = @(); "
            "try { "
            "  $names += Get-PnpDevice -Class AudioEndpoint | "
            "    Where-Object { $_.Status -eq 'OK' } | "
            "    ForEach-Object { $_.FriendlyName }; "
            "} catch {} ; "
            "try { "
            "  $names += Get-CimInstance Win32_SoundDevice | "
            "    Where-Object { $_.Status -eq 'OK' } | "
            "    ForEach-Object { $_.Name }; "
            "} catch {} ; "
            "$names | Sort-Object -Unique"
        )

        try:
            cp = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    ps,
                ],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
            )

            names = [
                line.strip()
                for line in (
                    cp.stdout
                    or
                    ""
                ).splitlines()
                if line.strip()
            ]

            endpoint_lower = endpoint_name.lower()

            found = any(
                name.lower()
                ==
                endpoint_lower
                for name in names
            )

            if not found:
                found = any(
                    endpoint_lower
                    in
                    name.lower()
                    or
                    name.lower()
                    in
                    endpoint_lower
                    for name in names
                )

            if found:
                return True, (
                    f"{label} ready"
                )

            return False, (
                f"{label} missing"
            )

        except Exception as exc:
            return False, (
                f"{label} check failed: {exc}"
            )


    def check_inputs(
        self,
        client
    ):
        try:
            response = (
                client.get_input_list()
            )

            names = {
                item.get(
                    "inputName",
                    ""
                )
                for item in getattr(
                    response,
                    "inputs",
                    []
                )
                if isinstance(
                    item,
                    dict
                )
            }

            missing = [
                name
                for name in self.config.get(
                    "critical_inputs",
                    []
                )
                if name not in names
            ]

            if missing:
                return False, (
                    "missing: "
                    +
                    ", ".join(
                        missing
                    )
                )

            return True, (
                "main + room mics + lower thirds"
            )

        except Exception as exc:
            return False, str(
                exc
            )

    def check_disk(
        self
    ):
        try:
            folder = Path(
                self.config[
                    "recording_folder"
                ]
            )

            usage = shutil.disk_usage(
                folder
            )

            free_gb = (
                usage.free
                /
                (
                    1024 ** 3
                )
            )

            minimum = float(
                self.config.get(
                    "minimum_free_gb",
                    100
                )
            )

            critical = float(
                self.config.get(
                    "critical_free_gb",
                    25
                )
            )

            if free_gb < critical:
                return False, (
                    f"{free_gb:.0f} GB free"
                ), False

            if free_gb < minimum:
                return False, (
                    f"{free_gb:.0f} GB free"
                ), True

            return True, (
                f"{free_gb:.0f} GB free"
            ), False

        except Exception as exc:
            return False, str(
                exc
            ), False

    def check_folders(
        self
    ):
        bad = []

        for raw in self.config.get(
            "critical_folders",
            []
        ):
            path = Path(
                raw
            )

            if not path.exists():
                bad.append(
                    path.name
                )

                continue

            probe = (
                path
                /
                ".sunday_mode_test.tmp"
            )

            try:
                probe.write_text(
                    "ok",
                    encoding="utf-8"
                )

                probe.unlink(
                    missing_ok=True
                )

            except Exception:
                bad.append(
                    path.name
                )

        if bad:
            return False, (
                "problem: "
                +
                ", ".join(
                    bad
                )
            )

        return True, (
            "writable"
        )

    def check_internet(
        self
    ):
        host = (
            self.config.get(
                "internet_test_host",
                "www.youtube.com"
            )
        )

        port = int(
            self.config.get(
                "internet_test_port",
                443
            )
        )

        try:
            with socket.create_connection(
                (
                    host,
                    port
                ),
                timeout=3,
            ):
                return True, (
                    f"{host} reachable"
                )

        except OSError:
            return False, (
                f"{host} unreachable"
            )

    def check_tools(
        self
    ):
        names = [
            "ffmpeg",
            "ffprobe",
            "nvidia-smi",
        ]

        missing = [
            name
            for name in names
            if not shutil.which(
                name
            )
        ]

        if missing:
            return False, (
                "missing: "
                +
                ", ".join(
                    missing
                )
            )

        return True, (
            "FFmpeg + NVIDIA ready"
        )

    def check_bridge(
        self
    ):
        if not BRIDGE_STATUS.exists():
            return False, (
                "not running yet"
            )

        try:
            payload = json.loads(
                BRIDGE_STATUS.read_text(
                    encoding="utf-8"
                )
            )

            state = payload.get(
                "state",
                "UNKNOWN"
            )

            detail = payload.get(
                "detail",
                ""
            )

            okay = state in {
                "READY",
                "RECORDING",
                "STARTING",
                "WAITING_FOR_OBS",
            }

            text = state

            if detail:
                text += (
                    f" — {detail}"
                )

            return okay, text

        except Exception as exc:
            return False, str(
                exc
            )

    def check_all(
        self
    ):
        results = {}

        sermon = (
            self.check_sermon_plan()
        )

        results[
            "SERMON"
        ] = (
            sermon[0],
            sermon[1],
            not sermon[0],
        )

        sermon_chapters = (
            self.check_sermon_chapter_sequence()
        )

        results[
            "SERMON_CHAPTERS"
        ] = (
            sermon_chapters[0],
            sermon_chapters[1],
            sermon_chapters[2],
        )

        planning = (
            self.check_planning_status()
        )

        results[
            "PLANNING"
        ] = (
            planning[0],
            planning[1],
            planning[2],
        )

        youtube = (
            self.check_youtube_status()
        )

        results[
            "YOUTUBE"
        ] = (
            youtube[0],
            youtube[1],
            youtube[2],
        )

        post_service = (
            self.check_post_service_status()
        )

        results[
            "POST"
        ] = (
            post_service[0],
            post_service[1],
            post_service[2],
        )

        ptz = (
            self.check_ptz_status()
        )

        results[
            "PTZ"
        ] = (
            ptz[0],
            ptz[1],
            ptz[2],
        )

        obs_ok = (
            obs_port_open(
                self.config
            )
        )

        results[
            "OBS"
        ] = (
            obs_ok,
            (
                "connected"
                if obs_ok
                else
                "waiting for OBS / WebSocket"
            ),
            False,
        )

        presentation_settings = (
            get_profile_presentation_settings(
                load_active_profile()
            )
        )

        if (
            presentation_settings.get(
                "settings_source"
            )
            ==
            "profile"
        ):
            presenter_ok, presenter_detail = (
                profile_adapter_ready()
            )

            if presenter_ok:
                presenter_detail = (
                    presentation_settings.get(
                        "provider",
                        "Presentation"
                    )
                    +
                    " ready"
                )

        else:
            presenter_ok, presenter_detail = (
                midi_port_available(
                    self._presenter_midi_port_name()
                )
            )

            if presenter_ok:
                presenter_detail = (
                    "MIDI ready — preset first Scripture verse before service"
                )

        results[
            "PRESENTER"
        ] = (
            presenter_ok,
            presenter_detail,
            not presenter_ok,
        )

        client = (
            self.connect_obs()
            if obs_ok
            else None
        )

        if client:
            collection = (
                self.ensure_scene_collection(
                    client
                )
            )

            results[
                "COLLECTION"
            ] = (
                collection[0],
                collection[1],
                False,
            )

            inputs = (
                self.check_inputs(
                    client
                )
            )

            results[
                "INPUTS"
            ] = (
                inputs[0],
                inputs[1],
                False,
            )

        else:
            results[
                "COLLECTION"
            ] = (
                False,
                "cannot check",
                False,
            )

            results[
                "INPUTS"
            ] = (
                False,
                "cannot check",
                False,
            )

        audio = (
            self.check_audio()
        )

        results[
            "AUDIO"
        ] = (
            audio[0],
            audio[1],
            False,
        )

        audio_health = (
            self.check_audio_sanity_status()
        )

        results[
            "AUDIO_HEALTH"
        ] = (
            audio_health[0],
            audio_health[1],
            audio_health[2],
        )

        recording_health = (
            self.check_recording_health()
        )

        results[
            "RECORDING_HEALTH"
        ] = (
            recording_health[0],
            recording_health[1],
            recording_health[2],
        )

        disk = (
            self.check_disk()
        )

        results[
            "DISK"
        ] = disk

        folders = (
            self.check_folders()
        )

        results[
            "FOLDERS"
        ] = (
            folders[0],
            folders[1],
            False,
        )

        sermon_ai_ok = (
            process_running_contains(
                "sermon_ai.py"
            )
        )

        results[
            "SERMON_AI"
        ] = (
            sermon_ai_ok,
            (
                "running"
                if sermon_ai_ok
                else
                "not running"
            ),
            False,
        )

        bridge = (
            self.check_bridge()
        )

        results[
            "CHAPTERS"
        ] = (
            bridge[0],
            bridge[1],
            False,
        )

        internet = (
            self.check_internet()
        )

        results[
            "INTERNET"
        ] = (
            internet[0],
            (
                internet[1]
                if internet[0]
                else
                (
                    "offline — local recording continues; "
                    "YouTube will retry later"
                )
            ),
            not internet[0],
        )

        tools = (
            self.check_tools()
        )

        results[
            "TOOLS"
        ] = (
            tools[0],
            tools[1],
            False,
        )

        return (
            results,
            client
        )

    def run_preflight_async(
        self
    ):
        # Do not allow periodic refresh + launch button + manual
        # preflight to pile up simultaneous checks.
        if self.preflight_running:
            return

        self.preflight_running = True

        try:
            self.preflight_button.configure(
                state="disabled"
            )
        except Exception:
            pass

        threading.Thread(
            target=self._preflight_worker,
            daemon=True,
        ).start()

    def _preflight_worker(
        self
    ):
        try:
            results, client = (
                self.check_all()
            )

            self.post_ui(
                self._finish_preflight,
                results
            )

        except Exception as exc:
            self.post_ui(
                self._preflight_failed,
                str(
                    exc
                )
            )

    def _finish_preflight(
        self,
        results
    ):
        try:
            self.apply_results(
                results
            )
        finally:
            self.preflight_running = False

            try:
                self.preflight_button.configure(
                    state="normal"
                )
            except Exception:
                pass

    def _preflight_failed(
        self,
        message
    ):
        self.preflight_running = False

        try:
            self.preflight_button.configure(
                state="normal"
            )
        except Exception:
            pass

        self.append_log(
            f"System status check failed: {message}"
        )

    def apply_results(
        self,
        results
    ):
        for key, (
            ok,
            text,
            warning
        ) in results.items():
            self.set_status(
                key,
                ok,
                text,
                warning=warning
            )

        hard_failures = [
            key
            for key, (
                ok,
                text,
                warning
            ) in results.items()
            if (
                not ok
                and
                not warning
            )
        ]

        if hard_failures:
            message = (
                "System status needs attention: "
                +
                ", ".join(
                    hard_failures
                )
            )
        else:
            message = (
                "System status: "
                "ready."
            )

        # Only log when the overall preflight result changes. The UI
        # still refreshes every cycle, but the Sunday Log no longer
        # fills with the same message every five seconds.
        if message != self.last_preflight_message:
            self.append_log(
                message
            )
            self.last_preflight_message = (
                message
            )

    def launch_background_helpers(
        self
    ):
        if (
            self.config.get(
                "auto_start_sermon_ai",
                True
            )
            and
            not process_running_contains(
                "sermon_ai.py"
            )
        ):
            launcher = Path(
                self.config[
                    "sermon_ai_launcher"
                ]
            )

            if launcher.exists():
                try:
                    os.startfile(
                        launcher
                    )

                    self.append_log(
                        "Started Sermon AI."
                    )
                except Exception as exc:
                    self.append_log(
                        "Could not start "
                        f"Sermon AI: {exc}"
                    )

        if (
            self.config.get(
                "auto_start_chapter_bridge",
                True
            )
            and
            not process_running_contains(
                "chapter_bridge.py"
            )
            and
            BRIDGE_SCRIPT.exists()
        ):
            try:
                pythonw = (
                    BASE
                    /
                    "venv"
                    /
                    "Scripts"
                    /
                    "pythonw.exe"
                )

                subprocess.Popen(
                    [
                        str(
                            pythonw
                        ),
                        str(
                            BRIDGE_SCRIPT
                        ),
                    ],
                    cwd=BASE,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if os.name == "nt"
                        else 0
                    ),
                )

                self.append_log(
                    "Started Chapter Bridge."
                )

            except Exception as exc:
                self.append_log(
                    "Could not start "
                    f"Chapter Bridge: {exc}"
                )

    def start_sermon_plan_services(
        self
    ):
        """
        Prepare this week's sermon BEFORE OBS opens.

        1. If Gmail is authorized, import the newest pastor sermon email.
        2. Embed sermon_plan.json directly into control-panel.html.
        3. Rename/create Additional Chapter Hotkeys entries from the
           official Gmail Scripture + sermon points BEFORE OBS opens.
        4. OBS can then load both the weekly lower thirds and the weekly
           named chapter hotkeys on startup.
        """
        python = (
            BASE
            /
            "venv"
            /
            "Scripts"
            /
            "python.exe"
        )

        sermon_source = get_profile_sermon_source_settings(
            load_active_profile()
        )

        profile_sermon_mode = (
            sermon_source.get(
                "settings_source"
            )
            ==
            "profile"
        )

        profile_sermon_provider = sermon_source.get(
            "provider",
            "Manual"
        )

        if (
            profile_sermon_mode
            and
            profile_sermon_provider
            in {
                "Manual",
                "Imported File",
            }
        ):
            try:
                result = materialize_profile_sermon_plan()
                plan = result.get(
                    "plan",
                    {}
                )

                self.append_log(
                    (
                        "Profile sermon plan prepared: "
                        +
                        str(
                            plan.get(
                                "title",
                                "sermon"
                            )
                        )
                    )
                )

            except Exception as exc:
                self.append_log(
                    (
                        "Profile sermon source could not be prepared: "
                        +
                        str(
                            exc
                        )
                    )
                )

        token_file = Path(
            self.config.get(
                "gmail_token_file",
                str(
                    BASE
                    /
                    "gmail_token.json"
                )
            )
        )

        # Import first, synchronously, so a new Friday email is already
        # available before OBS opens the lower-third browser dock.
        should_import_email = (
            (
                not profile_sermon_mode
            )
            or
            (
                profile_sermon_provider
                ==
                "Pastor Email"
            )
        )

        email_auto_refresh = (
            bool(
                sermon_source.get(
                    "email_auto_refresh",
                    True
                )
            )
            if (
                profile_sermon_mode
                and
                profile_sermon_provider
                ==
                "Pastor Email"
            )
            else
            bool(
                self.config.get(
                    "auto_import_sermon_email",
                    True
                )
            )
        )

        if (
            should_import_email
            and
            email_auto_refresh
            and
            token_file.exists()
            and
            GMAIL_IMPORTER.exists()
        ):
            try:
                cp = subprocess.run(
                    [
                        str(
                            python
                        ),
                        str(
                            GMAIL_IMPORTER
                        ),
                        "--quiet",
                    ],
                    cwd=BASE,
                    capture_output=True,
                    text=True,
                    timeout=25,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if os.name == "nt"
                        else 0
                    ),
                )

                if cp.returncode == 0:
                    self.append_log(
                        (
                            "Upcoming-Sunday pastor sermon email imported."
                            if profile_sermon_provider == "Pastor Email"
                            or not profile_sermon_mode
                            else
                            "Sermon source refreshed."
                        )
                    )
                else:
                    details = (
                        cp.stderr.strip()
                        or
                        cp.stdout.strip()
                        or
                        "unknown Gmail importer error"
                    )

                    self.append_log(
                        (
                            "Upcoming-Sunday sermon email was not imported: "
                            +
                            details
                        )
                    )

            except Exception as exc:
                self.append_log(
                    "Sermon email check failed; "
                    "using the existing sermon plan. "
                    f"{exc}"
                )

        # Always embed the currently available plan.
        if (
            SERMON_PLAN_FILE.exists()
            and
            SERMON_PLAN_SYNC.exists()
        ):
            try:
                cp = subprocess.run(
                    [
                        str(
                            python
                        ),
                        str(
                            SERMON_PLAN_SYNC
                        ),
                    ],
                    cwd=BASE,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if os.name == "nt"
                        else 0
                    ),
                )

                if cp.returncode == 0:
                    self.append_log(
                        "This week's sermon embedded into lower thirds."
                    )
                else:
                    details = (
                        cp.stderr.strip()
                        or
                        cp.stdout.strip()
                        or
                        "unknown error"
                    )

                    self.append_log(
                        "Lower-third sermon embed failed: "
                        f"{details}"
                    )

            except Exception as exc:
                self.append_log(
                    "Could not embed sermon plan into lower thirds: "
                    f"{exc}"
                )

        # Sync the Additional Chapter Hotkeys plugin while OBS is still
        # closed. The plugin stores these hotkeys in the scene collection,
        # so this preserves existing bindings while keeping Prayer /
        # Reference / Ending Prayer / Benediction fixed and changing Point slots to this
        # week's official Gmail sermon-point wording.
        if (
            self.config.get(
                "chapter_sync_named_hotkeys_from_gmail",
                True
            )
            and
            SERMON_PLAN_FILE.exists()
            and
            CHAPTER_HOTKEY_SYNC_SCRIPT.exists()
        ):
            try:
                cp = subprocess.run(
                    [
                        str(
                            python
                        ),
                        str(
                            CHAPTER_HOTKEY_SYNC_SCRIPT
                        ),
                    ],
                    cwd=BASE,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if os.name == "nt"
                        else 0
                    ),
                )

                status = read_json(
                    CHAPTER_HOTKEY_SYNC_STATUS,
                    {}
                )

                state = str(
                    status.get(
                        "state",
                        ""
                    )
                ).upper()

                if state == "SYNCED":
                    self.append_log(
                        "Sermon points synced to OBS named chapter hotkeys."
                    )

                elif state == "DEFERRED_OBS_RUNNING":
                    self.append_log(
                        "Chapter hotkey labels are waiting for an OBS restart; "
                        "SSS chapter button will still use the correct names."
                    )

                elif cp.returncode != 0:
                    detail = (
                        cp.stderr.strip()
                        or
                        cp.stdout.strip()
                        or
                        status.get(
                            "message",
                            "unknown error"
                        )
                    )

                    self.append_log(
                        "Named chapter hotkey sync warning: "
                        f"{detail}"
                    )

            except Exception as exc:
                self.append_log(
                    "Could not sync Gmail points to chapter hotkeys: "
                    f"{exc}"
                )

    def upcoming_service_date(
        self
    ):
        today = now_local().date()

        days_until_sunday = (
            6
            -
            today.weekday()
        ) % 7

        return (
            today
            +
            datetime.timedelta(
                days=days_until_sunday
            )
        )

    def sermon_plan_is_for_upcoming_service(
        self,
        plan
    ):
        if not isinstance(
            plan,
            dict
        ):
            return (
                False,
                "no sermon plan loaded",
            )

        target = self.upcoming_service_date()

        service_date_raw = str(
            plan.get(
                "service_date",
                ""
            )
            or
            ""
        ).strip()

        if not service_date_raw:
            return (
                False,
                (
                    "sermon plan has no service date; upcoming Sunday is "
                    +
                    target.isoformat()
                ),
            )

        try:
            loaded_date = (
                datetime.date.fromisoformat(
                    service_date_raw
                )
            )
        except Exception:
            return (
                False,
                (
                    "sermon plan service date is invalid: "
                    +
                    service_date_raw
                ),
            )

        if loaded_date != target:
            return (
                False,
                (
                    "loaded sermon is for "
                    +
                    loaded_date.isoformat()
                    +
                    "; upcoming Sunday is "
                    +
                    target.isoformat()
                ),
            )

        return (
            True,
            target.isoformat(),
        )

    def check_sermon_plan(
        self
    ):
        source_settings = get_profile_sermon_source_settings(
            load_active_profile()
        )

        if (
            source_settings.get(
                "settings_source"
            )
            ==
            "profile"
        ):
            source_ok, source_detail = profile_sermon_source_ready()

            if not source_ok:
                return False, (
                    "sermon source: "
                    +
                    str(
                        source_detail
                    )
                )

        if not SERMON_PLAN_FILE.exists():
            return False, (
                "no sermon plan loaded"
            )

        try:
            plan = json.loads(
                SERMON_PLAN_FILE.read_text(
                    encoding="utf-8"
                )
            )

            date_ok, date_detail = (
                self.sermon_plan_is_for_upcoming_service(
                    plan
                )
            )

            if not date_ok:
                return (
                    False,
                    date_detail,
                )

            title = str(
                plan.get(
                    "title",
                    ""
                )
            ).strip()

            scripture = str(
                plan.get(
                    "scripture",
                    ""
                )
            ).strip()

            points = plan.get(
                "points",
                []
            )

            if (
                title
                and
                scripture
                and
                isinstance(
                    points,
                    list
                )
                and
                points
            ):
                source_suffix = ""

                if (
                    source_settings.get(
                        "settings_source"
                    )
                    ==
                    "profile"
                ):
                    source_suffix = (
                        " | "
                        +
                        str(
                            source_settings.get(
                                "provider",
                                "Profile"
                            )
                        )
                    )

                return True, (
                    f"{title} | {scripture} | "
                    f"{len(points)} point(s)"
                    +
                    source_suffix
                )

            return False, (
                "sermon plan incomplete"
            )

        except Exception as exc:
            return False, (
                f"plan error: {exc}"
            )


    def _finish_planning_update(
        self,
        message
    ):
        self.append_log(
            message
        )

        try:
            self.planning_button.configure(
                state="normal"
            )
        except Exception:
            pass

        self.run_preflight_async()

    def check_youtube_status(
        self
    ):
        if not self.config.get(
            "auto_upload_youtube",
            True
        ):
            return True, (
                "automatic upload disabled"
            ), True

        if (
            str(
                self.config.get(
                    "youtube_upload_mode",
                    "studio"
                )
            ).lower()
            !=
            "studio"
        ):
            return False, (
                "YouTube mode is not Studio"
            ), True

        profile = Path(
            self.config.get(
                "youtube_studio_profile_folder",
                str(
                    BASE
                    /
                    "YouTube_Studio_Profile"
                )
            )
        )

        if not profile.exists():
            return False, (
                "Studio login/profile required"
            ), True

        plan = read_json(
            SERMON_PLAN_FILE,
            {}
        )

        history = read_json(
            YOUTUBE_HISTORY_FILE,
            {
                "uploads": []
            }
        )

        current_entry = None

        for entry in history.get(
            "uploads",
            []
        ):
            if (
                entry.get(
                    "plan_id"
                )
                ==
                plan.get(
                    "plan_id"
                )
                and
                plan.get(
                    "plan_id"
                )
            ):
                current_entry = entry
                break

        if current_entry is not None:
            return True, (
                (
                    "uploaded"
                    +
                    (
                        f" — {current_entry.get('video_url')}"
                        if current_entry.get(
                            "video_url"
                        )
                        else
                        ""
                    )
                )
            ), False

        if not YOUTUBE_STATUS_FILE.exists():
            return True, (
                "Studio ready — waiting for sermon"
            ), False

        try:
            payload = json.loads(
                YOUTUBE_STATUS_FILE.read_text(
                    encoding="utf-8"
                )
            )

            # Ignore stale API-mode status from v20.
            if (
                payload.get(
                    "mode"
                )
                not in
                (
                    None,
                    "studio",
                )
            ):
                return True, (
                    "Studio ready — waiting for sermon"
                ), False

            state = str(
                payload.get(
                    "state",
                    ""
                )
            ).strip()

            if state in {
                "UPLOADED",
                "ALREADY_UPLOADED",
            }:
                # No matching current-plan history entry was found above,
                # so this completion state belongs to an older service.
                return True, (
                    "Studio ready — waiting for this sermon"
                ), False

            message = str(
                payload.get(
                    "message",
                    ""
                )
            ).strip()

            progress = payload.get(
                "progress"
            )

            if (
                state
                ==
                "UPLOADING"
                and
                progress is not None
            ):
                message = (
                    f"uploading — {progress}%"
                )

            ok_states = {
                "CHANNEL_VERIFIED",
                "UPLOADED",
                "ALREADY_UPLOADED",
                "WAITING_FOR_RECORDING",
                "UPLOADING",
                "PUBLISHING",
                "PREVIEW_READY",
            }

            warning_states = {
                "SKIPPED_DATE",
                "NO_RECORDING",
                "ERROR",
                "PREVIEW_NONE",
                "DRY_RUN",
            }

            if not message:
                message = (
                    state
                    or
                    "Studio ready"
                )

            return (
                state in ok_states,
                message,
                state in warning_states,
            )

        except Exception as exc:
            return False, (
                f"status error: {exc}"
            ), True

    def start_youtube_upload_waiter(
        self
    ):
        if not self.config.get(
            "auto_upload_youtube",
            True
        ):
            return

        if not YOUTUBE_UPLOAD_SCRIPT.exists():
            self.post_ui(
                self.append_log,
                "YouTube Studio upload worker is not installed."
            )
            return

        if process_running_contains(
            "youtube_studio_upload_worker.py"
        ):
            self.post_ui(
                self.append_log,
                "YouTube Studio upload worker is already waiting/running."
            )
            return

        profile = Path(
            self.config.get(
                "youtube_studio_profile_folder",
                str(
                    BASE
                    /
                    "YouTube_Studio_Profile"
                )
            )
        )

        if not profile.exists():
            self.post_ui(
                self.append_log,
                "YouTube Studio login/profile setup is required."
            )
            return

        pythonw = (
            BASE
            /
            "venv"
            /
            "Scripts"
            /
            "pythonw.exe"
        )

        try:
            subprocess.Popen(
                [
                    str(
                        pythonw
                    ),
                    str(
                        YOUTUBE_UPLOAD_SCRIPT
                    ),
                    "--quiet",
                ],
                cwd=BASE,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
            )

            channel_name = str(
                self.config.get(
                    "youtube_expected_channel_name",
                    ""
                )
            ).strip() or "the configured"

            self.post_ui(
                self.append_log,
                (
                    "YouTube Studio worker started. "
                    f"It will verify the {channel_name} channel, "
                    "choose the largest valid full sermon, and upload it."
                )
            )

        except Exception as exc:
            self.post_ui(
                self.append_log,
                (
                    "Could not start YouTube Studio upload worker: "
                    f"{exc}"
                )
            )

    def check_planning_status(
        self
    ):
        if not PLANNING_STATUS_FILE.exists():
            return False, (
                "not checked yet"
            ), True

        try:
            payload = json.loads(
                PLANNING_STATUS_FILE.read_text(
                    encoding="utf-8"
                )
            )

            status = str(
                payload.get(
                    "status",
                    ""
                )
            ).strip()

            message = str(
                payload.get(
                    "message",
                    ""
                )
            ).strip()

            ok = bool(
                payload.get(
                    "ok",
                    False
                )
            )

            warning = bool(
                payload.get(
                    "warning",
                    not ok
                )
            )

            if not message:
                message = (
                    status
                    or
                    "unknown"
                )

            return (
                ok,
                message,
                warning,
            )

        except Exception as exc:
            return False, (
                f"status error: {exc}"
            ), True

    def update_planning_async(
        self
    ):
        if self.planning_update_running:
            return

        if not PLANNING_UPDATE_SCRIPT.exists():
            self.append_log(
                "Planning updater is not installed."
            )
            return

        self.planning_update_running = True

        try:
            self.planning_button.configure(
                state="disabled"
            )
        except Exception:
            pass

        threading.Thread(
            target=self._planning_update_worker,
            daemon=True,
        ).start()

    def _planning_update_worker(
        self
    ):
        message = ""

        try:
            python = (
                BASE
                /
                "venv"
                /
                "Scripts"
                /
                "python.exe"
            )

            timeout = int(
                self.config.get(
                    "planning_update_timeout_seconds",
                    60
                )
            )

            subprocess.run(
                [
                    str(
                        python
                    ),
                    str(
                        PLANNING_UPDATE_SCRIPT
                    ),
                    "--quiet",
                ],
                cwd=BASE,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
            )

            if PLANNING_STATUS_FILE.exists():
                try:
                    payload = json.loads(
                        PLANNING_STATUS_FILE.read_text(
                            encoding="utf-8"
                        )
                    )

                    message = str(
                        payload.get(
                            "message",
                            ""
                        )
                    ).strip()

                except Exception:
                    pass

            if not message:
                message = (
                    "Planning Scripture sync finished."
                )

        except subprocess.TimeoutExpired:
            message = (
                "Planning Scripture sync timed out."
            )

        except Exception as exc:
            message = (
                "Planning Scripture sync failed: "
                f"{exc}"
            )

        finally:
            self.planning_update_running = False

            self.post_ui(
                self._finish_planning_update,
                message
            )

    def start_obs_cleanup_helper(
        self
    ):
        if not OBS_CLEANUP_SCRIPT.exists():
            return

        if process_running_contains(
            "obs_startup_cleanup.py"
        ):
            return

        try:
            pythonw = (
                BASE
                /
                "venv"
                /
                "Scripts"
                /
                "pythonw.exe"
            )

            subprocess.Popen(
                [
                    str(
                        pythonw
                    ),
                    str(
                        OBS_CLEANUP_SCRIPT
                    ),
                ],
                cwd=BASE,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
            )

            self.append_log(
                "OBS startup popup cleaner active."
            )

        except Exception as exc:
            self.append_log(
                "Could not start OBS popup cleaner: "
                f"{exc}"
            )

    def ensure_obs_running(
        self,
        retry_count=0
    ):
        """
        Make sure OBS is running whenever Sunday Service System opens.

        Behavior:
        - If OBS WebSocket is reachable, OBS is ready and nothing is done.
        - If obs64.exe is already running, do not launch a duplicate; wait
          for WebSocket to come online.
        - If OBS is not running, launch it.
        - Retry for about 30 seconds so a slow OBS startup still becomes
          READY without the volunteer doing anything.

        This NEVER starts recording or streaming.
        """
        # Fully ready.
        if obs_port_open(
            self.config
        ):
            if retry_count:
                self.append_log(
                    "OBS is ready."
                )
            return

        # OBS process exists but WebSocket is still starting.
        if process_name_running(
            "obs64.exe"
        ):
            if retry_count == 0:
                self.append_log(
                    "OBS is already open; "
                    "waiting for WebSocket..."
                )

            if retry_count < 10:
                self.root.after(
                    3000,
                    lambda: self.ensure_obs_running(
                        retry_count + 1
                    )
                )
            else:
                self.append_log(
                    "OBS is open, but WebSocket "
                    "did not become ready."
                )

            return

        # OBS is not running. Launch it on the first attempt only.
        if retry_count == 0:
            self.append_log(
                "OBS is not open. Starting OBS..."
            )

            shortcut_raw = self.config.get(
                "obs_shortcut",
                ""
            )

            shortcut = (
                Path(shortcut_raw)
                if shortcut_raw
                else None
            )

            launched = False

            # Preferred route: the same Windows shortcut normally used.
            if (
                shortcut is not None
                and
                shortcut.exists()
            ):
                try:
                    os.startfile(
                        shortcut
                    )

                    launched = True

                    self.append_log(
                        "OBS launch command sent."
                    )

                except Exception as exc:
                    self.append_log(
                        "OBS shortcut launch failed: "
                        f"{exc}"
                    )

            # Fallback: launch obs64.exe directly.
            if not launched:
                obs_exe_raw = self.config.get(
                    "obs_exe",
                    r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"
                )

                obs_exe = Path(
                    obs_exe_raw
                )

                if obs_exe.exists():
                    try:
                        subprocess.Popen(
                            [
                                str(
                                    obs_exe
                                )
                            ],
                            cwd=obs_exe.parent,
                            creationflags=(
                                subprocess.CREATE_NO_WINDOW
                                if os.name == "nt"
                                else 0
                            ),
                        )

                        launched = True

                        self.append_log(
                            "OBS started directly."
                        )

                    except Exception as exc:
                        self.append_log(
                            "Direct OBS launch failed: "
                            f"{exc}"
                        )
                else:
                    self.append_log(
                        "OBS executable was not found: "
                        f"{obs_exe}"
                    )

            if not launched:
                return

        # Wait and verify that OBS actually started.
        if retry_count < 10:
            self.root.after(
                3000,
                lambda: self.ensure_obs_running(
                    retry_count + 1
                )
            )
        else:
            self.append_log(
                "OBS did not become ready after startup."
            )


    def ensure_presenter_running(
        self
    ):
        """
        Make sure WorshipTools Presenter is open.

        SSS no longer needs to control Presenter's internal UI. Scripture
        positioning is done through Presenter's own MIDI commands and verified
        from the OBS webcam TP view.
        """
        if (
            process_name_running(
                "Presenter.exe"
            )
            or
            process_running_contains(
                "Presenter.exe"
            )
            or
            process_running_contains(
                "WorshipTools Presenter"
            )
        ):
            return True

        shortcut_raw = self.config.get(
            "presenter_shortcut",
            ""
        )

        shortcut = (
            Path(
                shortcut_raw
            )
            if shortcut_raw
            else None
        )

        # The church PC diagnostic confirmed this installation path. Use it
        # if the configured shortcut is unavailable.
        direct_exe = Path(
            r"C:\Program Files\Presenter\Presenter.exe"
        )

        try:
            if (
                shortcut is not None
                and
                shortcut.exists()
            ):
                os.startfile(
                    shortcut
                )

                self.append_log(
                    "Opened Presenter automatically."
                )

                return True

            if direct_exe.exists():
                os.startfile(
                    direct_exe
                )

                self.append_log(
                    "Opened Presenter automatically."
                )

                return True

        except Exception as exc:
            self.append_log(
                "Presenter start failed: "
                f"{exc}"
            )

            return False

        self.append_log(
            "Presenter was not found."
        )

        return False

    def launch_apps(
        self
    ):
        self.start_sermon_plan_services()
        self.start_obs_cleanup_helper()
        self.ensure_obs_running()

        if self.config.get(
            "auto_update_planning_scripture",
            True
        ):
            self.update_planning_async()

        # Presenter is normally launched automatically when SSS opens.
        # This acts as a safe retry if it was closed or failed to start.
        self.ensure_presenter_running()

        self.launch_background_helpers()

        # One delayed refresh is enough. run_preflight_async itself is
        # guarded, so it cannot overlap an existing periodic preflight.
        self.root.after(
            3500,
            self.run_preflight_async
        )

    def start_recording(
        self
    ):
        if (
            self.chapter_test_mode
            and
            self.chapter_action_running
        ):
            messagebox.showwarning(
                "Chapter / LT Test",
                (
                    "Wait for the current test lower third to finish "
                    "before starting the service recording."
                ),
            )
            return

        if self.chapter_test_mode:
            self.set_chapter_test_mode(
                False
            )

        results, client = (
            self.check_all()
        )

        if client is None:
            messagebox.showerror(
                "Sunday Mode",
                "OBS is not ready."
            )
            return

        critical_failures = [
            key
            for key in [
                "OBS",
                "COLLECTION",
                "AUDIO",
                "INPUTS",
                "DISK",
                "FOLDERS",
                "SERMON_AI",
                "TOOLS",
            ]
            if (
                key in results
                and
                not results[key][0]
                and
                not results[key][2]
            )
        ]

        if critical_failures:
            okay = (
                messagebox.askyesno(
                    "System Status warning",
                    (
                        "These checks are not ready:\n\n"
                        +
                        "\n".join(
                            critical_failures
                        )
                        +
                        "\n\nStart recording anyway?"
                    ),
                )
            )

            if not okay:
                return

        try:
            status = (
                get_obs_status(
                    client
                )
            )

            was_recording = bool(
                status[
                    "recording"
                ]
            )

            if not was_recording:
                client.start_record()

                # Every fresh sermon recording starts the rotating chapter
                # sequence from Prayer. Re-clicking START while already
                # recording does not erase current chapter progress.
                reset_rotation()

                self.scripture_reading_active = False
                self.scripture_reading_busy = False
                self.scripture_verse_index = -1

                self.refresh_chapter_rotation_button()
                self.refresh_scripture_controls()

            self.service_commanded = True
            self.service_ending = False
            self.recording_started_at = time.time()
            self.last_recording_state = True
            self.sync_reset_chapters_button()
            self.active_recording_path = ""
            self.last_recording_size = 0
            self.last_recording_growth_time = time.time()

            set_freeze(
                True,
                "Sunday recording is active."
            )

            self.append_log(
                "Recording START requested. Sunday Freeze enabled."
            )

            self.root.after(
                2500,
                self.run_preflight_async
            )

        except Exception as exc:
            messagebox.showerror(
                "Sunday Mode",
                f"Could not start recording:\n{exc}"
            )

    def stop_recording(
        self
    ):
        if not messagebox.askyesno(
            "Stop Recording",
            "Stop the OBS recording?"
        ):
            return

        client = (
            self.connect_obs()
        )

        if client is None:
            messagebox.showerror(
                "Sunday Mode",
                "OBS is not reachable."
            )
            return

        self.service_ending = True

        try:
            status = (
                get_obs_status(
                    client
                )
            )

            if status[
                "recording"
            ]:
                client.stop_record()

            self.service_commanded = False

            self.append_log(
                "Recording STOP requested. "
                "Post-service automation will take over."
            )

            # Start the YouTube worker immediately. It still refuses
            # tiny/short files and waits for the real same-date sermon
            # recording to become large enough and stable.
            self.start_youtube_upload_waiter()

            # The post-service supervisor tracks recording stability,
            # transcript/shorts processing, chapters, Planning, YouTube,
            # thumbnail handoff, cleanup, and crash/reboot recovery.
            self.start_post_service_supervisor()

            self.root.after(
                4000,
                self.run_preflight_async
            )

        except Exception as exc:
            messagebox.showerror(
                "Sunday Mode",
                f"Could not stop recording:\n{exc}"
            )

        finally:
            self.root.after(
                5000,
                self._clear_ending
            )

    def start_stream(
        self
    ):
        if (
            self.chapter_test_mode
            and
            self.chapter_action_running
        ):
            messagebox.showwarning(
                "Chapter / LT Test",
                (
                    "Wait for the current test lower third to finish "
                    "before starting the livestream."
                ),
            )
            return

        if self.chapter_test_mode:
            self.set_chapter_test_mode(
                False
            )

        client = (
            self.connect_obs()
        )

        if client is None:
            messagebox.showerror(
                "Sunday Mode",
                "OBS is not reachable."
            )
            return

        try:
            status = (
                get_obs_status(
                    client
                )
            )

            if status[
                "streaming"
            ]:
                self.append_log(
                    "Stream is already running."
                )
                return

            client.start_stream()

            set_freeze(
                True,
                "Sunday streaming is active."
            )

            self.append_log(
                "Stream START requested. Sunday Freeze enabled."
            )

        except Exception as exc:
            messagebox.showerror(
                "Sunday Mode",
                f"Could not start stream:\n{exc}"
            )

    def stop_stream(
        self
    ):
        if not messagebox.askyesno(
            "Stop Stream",
            "Stop the livestream?"
        ):
            return

        client = (
            self.connect_obs()
        )

        if client is None:
            messagebox.showerror(
                "Sunday Mode",
                "OBS is not reachable."
            )
            return

        try:
            status = (
                get_obs_status(
                    client
                )
            )

            if status[
                "streaming"
            ]:
                client.stop_stream()

            self.append_log(
                "Stream STOP requested."
            )

        except Exception as exc:
            messagebox.showerror(
                "Sunday Mode",
                f"Could not stop stream:\n{exc}"
            )

    def _clear_ending(
        self
    ):
        self.service_ending = False

        client = self.connect_obs()

        if client is not None:
            try:
                status = get_obs_status(
                    client
                )

                self.update_sunday_freeze(
                    recording=status[
                        "recording"
                    ],
                    streaming=status[
                        "streaming"
                    ],
                )
            except Exception:
                pass

    def refresh_mute_button_label(
        self,
        client=None
    ):
        if not hasattr(
            self,
            "mute_button"
        ):
            return

        try:
            profile_audio = get_profile_audio_settings(
                load_active_profile()
            )

            if (
                profile_audio.get(
                    "settings_source"
                )
                ==
                "profile"
            ):
                if (
                    profile_audio.get(
                        "provider"
                    )
                    !=
                    "OBS Audio Inputs"
                ):
                    return

                states_by_name = get_profile_mute_states()

                if not states_by_name:
                    return

                all_muted = all(
                    states_by_name.values()
                )

                self.mute_state = all_muted

                self.mute_button.configure(
                    text=(
                        "UNMUTE AUDIO"
                        if all_muted
                        else
                        "MUTE AUDIO"
                    )
                )

                return

        except Exception:
            # A failed profile-state read should not crash the dashboard.
            return

        if client is None:
            client = self.connect_obs()

        if client is None:
            return

        names = self.config.get(
            "emergency_mute_inputs",
            [
                "main",
                "room mics"
            ]
        )

        states = []

        for name in names:
            try:
                states.append(
                    bool(
                        client.get_input_mute(
                            name
                        ).input_muted
                    )
                )
            except Exception:
                pass

        if not states:
            return

        all_muted = all(
            states
        )

        self.mute_state = all_muted

        try:
            self.mute_button.configure(
                text=(
                    "UNMUTE AUDIO"
                    if all_muted
                    else
                    "MUTE AUDIO"
                )
            )
        except Exception:
            pass


    def emergency_mute(
        self
    ):
        try:
            profile_audio = get_profile_audio_settings(
                load_active_profile()
            )

            if (
                profile_audio.get(
                    "settings_source"
                )
                ==
                "profile"
            ):
                provider = profile_audio.get(
                    "provider",
                    "Not configured"
                )

                if provider == "None":
                    return

                if provider != "OBS Audio Inputs":
                    messagebox.showwarning(
                        "Sunday Mode",
                        (
                            "This profile's audio adapter is not live yet:\n\n"
                            +
                            str(
                                provider
                            )
                        ),
                    )
                    return

                try:
                    result = toggle_profile_mute()

                    self.mute_state = bool(
                        result.get(
                            "muted",
                            False
                        )
                    )

                    self.refresh_mute_button_label()

                    self.append_log(
                        (
                            "Program audio PROFILE "
                            +
                            (
                                "MUTED"
                                if self.mute_state
                                else
                                "UNMUTED"
                            )
                            +
                            " — "
                            +
                            ", ".join(
                                result.get(
                                    "inputs",
                                    []
                                )
                            )
                            +
                            "."
                        )
                    )

                except Exception as exc:
                    messagebox.showwarning(
                        "Audio",
                        (
                            "Profile audio mute did not complete.\n\n"
                            +
                            str(
                                exc
                            )
                        ),
                    )

                    self.append_log(
                        (
                            "Profile audio mute failed: "
                            +
                            str(
                                exc
                            )
                        )
                    )

                return

        except Exception:
            pass

        client = self.connect_obs()

        if client is None:
            messagebox.showerror(
                "Sunday Mode",
                "OBS is not reachable."
            )
            return

        names = self.config.get(
            "emergency_mute_inputs",
            [
                "main",
                "room mics"
            ]
        )

        current = []

        for name in names:
            try:
                current.append(
                    bool(
                        client.get_input_mute(
                            name
                        ).input_muted
                    )
                )
            except Exception:
                pass

        new_state = not (
            current
            and
            all(
                current
            )
        )

        for name in names:
            try:
                client.set_input_mute(
                    name,
                    new_state
                )
            except Exception as exc:
                self.append_log(
                    "Mute failed for "
                    f"{name}: {exc}"
                )

        self.mute_state = new_state

        self.refresh_mute_button_label(
            client
        )

        self.append_log(
            "Program audio "
            +
            (
                "MUTED."
                if new_state
                else
                "UNMUTED."
            )
        )


    def sync_chapter_hotkeys_async(
        self
    ):
        if not CHAPTER_HOTKEY_SYNC_SCRIPT.exists():
            messagebox.showerror(
                "Sermon Chapters",
                "sync_named_chapter_hotkeys.py is missing."
            )
            return

        def worker():
            python = (
                BASE
                /
                "venv"
                /
                "Scripts"
                /
                "python.exe"
            )

            try:
                cp = subprocess.run(
                    [
                        str(
                            python
                        ),
                        str(
                            CHAPTER_HOTKEY_SYNC_SCRIPT
                        ),
                    ],
                    cwd=BASE,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW
                        if os.name == "nt"
                        else 0
                    ),
                )

                status = read_json(
                    CHAPTER_HOTKEY_SYNC_STATUS,
                    {}
                )

                state = str(
                    status.get(
                        "state",
                        ""
                    )
                ).upper()

                message = str(
                    status.get(
                        "message",
                        ""
                    )
                ).strip()

                if state == "SYNCED":
                    self.post_ui(
                        self.append_log,
                        (
                            message
                            or
                            "Named sermon chapter hotkeys synced."
                        ),
                    )

                elif state == "DEFERRED_OBS_RUNNING":
                    self.post_ui(
                        self.append_log,
                        (
                            message
                            or
                            "OBS restart required to reload chapter hotkey labels."
                        ),
                    )

                else:
                    detail = (
                        message
                        or
                        cp.stderr.strip()
                        or
                        cp.stdout.strip()
                        or
                        "Unknown chapter hotkey sync result."
                    )

                    self.post_ui(
                        self.append_log,
                        f"Chapter hotkey sync: {detail}",
                    )

                self.post_ui(
                    self.refresh_chapter_rotation_button,
                    True,
                )

                self.post_ui(
                    self.run_preflight_async
                )

            except Exception as exc:
                self.post_ui(
                    self.append_log,
                    (
                        "Chapter hotkey sync failed: "
                        f"{exc}"
                    ),
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def check_sermon_chapter_sequence(
        self
    ):
        if not self.config.get(
            "chapter_rotation_enabled",
            True
        ):
            return True, (
                "disabled"
            ), True

        try:
            plan, sequence, state = (
                load_rotation()
            )

            points = [
                item
                for item in sequence
                if str(
                    item.get(
                        "role",
                        ""
                    )
                ).startswith(
                    "point"
                )
            ]

            if not sequence:
                return False, (
                    "no sermon chapter sequence"
                ), True

            sync = read_json(
                CHAPTER_HOTKEY_SYNC_STATUS,
                {}
            )

            sync_state = str(
                sync.get(
                    "state",
                    ""
                )
            ).upper()

            if (
                sync.get(
                    "plan_id"
                )
                and
                plan.get(
                    "plan_id"
                )
                and
                sync.get(
                    "plan_id"
                )
                !=
                plan.get(
                    "plan_id"
                )
            ):
                sync_state = ""

            if sync_state == "ERROR":
                return False, (
                    sync.get(
                        "message",
                        "named chapter hotkey sync error"
                    )
                ), True

            if sync_state == "DEFERRED_OBS_RUNNING":
                suffix = (
                    " | plugin labels need OBS restart"
                )

                warning = True

            elif sync_state == "SYNCED":
                suffix = (
                    " | named hotkeys synced"
                )

                warning = False

            else:
                suffix = (
                    " | chapter sequence ready"
                )

                warning = False

            scripture = str(
                plan.get(
                    "scripture",
                    ""
                )
            ).strip()

            detail = (
                "Prayer → "
                +
                (
                    scripture
                    if scripture
                    else
                    "Reference"
                )
                +
                f" → {len(points)} point(s)"
                +
                " → Ending Prayer → Benediction"
                +
                suffix
            )

            return True, (
                detail
            ), warning

        except Exception as exc:
            return False, (
                f"chapter sequence error: {exc}"
            ), True

    def _presenter_midi_port_name(
        self
    ):
        configured = str(
            self.config.get(
                "presenter_midi_port",
                "Presenter"
            )
            or
            "Presenter"
        ).strip()

        # Earlier SSS Scripture builds used the placeholder name
        # "Presenter". The actual church-PC loopMIDI port is
        # named "Presenter". Transparently correct the old value so an
        # existing sunday_config.json cannot keep breaking Scripture MIDI.
        if configured.lower() == "loopmidi port":
            return "Presenter"

        return configured

    def _scripture_midi_settings(
        self
    ):
        # EXACT match to the working Stream Deck Presenter controls.
        #
        # NEXT VERSE:
        #   Port: Presenter
        #   Channel: 10
        #   Note: 60
        #   Velocity: 126
        #   Event: Note On ONLY (no release / Note Off)
        #
        # PREVIOUS VERSE:
        #   Port: Presenter
        #   Channel: 10
        #   Note: 62
        #   Velocity: 126
        #   Event: Note On ONLY (no release / Note Off)
        #
        # These values are deliberately NOT read from sunday_config.json,
        # preventing older experimental Note 64 settings from leaking in.
        return {
            "port_name": "Presenter",
            "channel": 10,
            "next_note": 60,
            "back_note": 62,
            "velocity": 126,
        }

    def _current_rotation_item(
        self
    ):
        plan, sequence, state = (
            load_rotation()
        )

        if self.chapter_test_mode:
            index = int(
                self.chapter_test_index
            )
        else:
            index = int(
                state.get(
                    "next_index",
                    0
                )
            )

        item = (
            sequence[
                index
            ]
            if (
                0
                <=
                index
                <
                len(
                    sequence
                )
            )
            else
            None
        )

        return (
            plan,
            sequence,
            state,
            index,
            item,
        )

    def refresh_scripture_controls(
        self
    ):
        if not hasattr(
            self,
            "scripture_main_button"
        ):
            return

        try:
            plan = read_json(
                SERMON_PLAN_FILE,
                {}
            )

            date_ok, date_detail = (
                self.sermon_plan_is_for_upcoming_service(
                    plan
                )
            )

            reference = " ".join(
                str(
                    plan.get(
                        "scripture",
                        ""
                    )
                ).split()
            )

            if not date_ok:
                self.scripture_reference = ""
                self.scripture_verses = []
                self.scripture_verses_exact = False
                self.scripture_verse_index = -1

                self.scripture_main_button.configure(
                    text="UPDATE SERMON PLAN",
                    state="disabled",
                )

                self.scripture_back_button.configure(
                    text="FIRST VERSE SET BEFORE SERVICE",
                    state="disabled",
                )

                self.scripture_end_button.configure(
                    text="END READING",
                    state="disabled",
                )

                return

            parsed = parse_scripture_reference(
                reference
            )

            if (
                reference
                !=
                self.scripture_reference
                and
                not self.scripture_reading_active
            ):
                self.scripture_reference = reference
                self.scripture_verses = list(
                    parsed.get(
                        "verses",
                        []
                    )
                )
                self.scripture_verses_exact = bool(
                    parsed.get(
                        "exact",
                        False
                    )
                )
                self.scripture_verse_index = -1

            if self.scripture_reading_busy:
                self.scripture_main_button.configure(
                    text="WORKING…",
                    state="disabled",
                )

                self.scripture_back_button.configure(
                    text="FIRST VERSE SET BEFORE SERVICE",
                    state="disabled",
                )

                self.scripture_end_button.configure(
                    state="disabled"
                )

                return

            if not self.scripture_reading_active:
                first_label = (
                    self.scripture_verses[
                        0
                    ]
                    if self.scripture_verses
                    else
                    (
                        reference
                        or
                        "SCRIPTURE"
                    )
                )

                if len(
                    first_label
                ) > 28:
                    first_label = (
                        first_label[
                            :27
                        ].rstrip()
                        +
                        "…"
                    )

                can_start = False
                waiting_text = ""

                try:
                    (
                        _plan,
                        _sequence,
                        _state,
                        _index,
                        current_item,
                    ) = self._current_rotation_item()

                    current_role = (
                        str(
                            current_item.get(
                                "role",
                                ""
                            )
                        ).lower()
                        if current_item
                        else
                        ""
                    )

                    can_start = (
                        current_role
                        ==
                        "reference"
                    )

                    if (
                        current_item
                        and
                        not can_start
                    ):
                        waiting_name = " ".join(
                            str(
                                current_item.get(
                                    "chapter_name",
                                    ""
                                )
                                or
                                current_item.get(
                                    "display",
                                    ""
                                )
                            ).split()
                        )

                        if current_role == "prayer":
                            waiting_text = "AFTER PRAYER"
                        elif current_role.startswith(
                            "point"
                        ):
                            waiting_text = "READING DONE"
                        else:
                            waiting_text = (
                                "WAITING"
                                if waiting_name
                                else
                                ""
                            )

                except Exception:
                    can_start = bool(
                        reference
                    )

                self.scripture_main_button.configure(
                    text=(
                        (
                            "START — "
                            +
                            first_label
                        )
                        if can_start
                        else
                        (
                            waiting_text
                            or
                            "START READING"
                        )
                    ),
                    state=(
                        "normal"
                        if (
                            reference
                            and
                            can_start
                        )
                        else
                        "disabled"
                    ),
                )

                self.scripture_back_button.configure(
                    text="FIRST VERSE SET BEFORE SERVICE",
                    state="disabled",
                )

                self.scripture_end_button.configure(
                    text="END READING",
                    state="disabled",
                )

                return

            # Reading is active.
            self.scripture_end_button.configure(
                text="END READING",
                state="normal",
            )

            self.scripture_back_button.configure(
                text="FIRST VERSE SET BEFORE SERVICE",
                state="disabled",
            )

            if (
                self.scripture_verses_exact
                and
                self.scripture_verses
            ):
                next_index = (
                    self.scripture_verse_index
                    +
                    1
                )

                if next_index >= len(
                    self.scripture_verses
                ):
                    self.scripture_main_button.configure(
                        text="FINISH READING",
                        state="normal",
                    )

                else:
                    next_label = self.scripture_verses[
                        next_index
                    ]

                    self.scripture_main_button.configure(
                        text=(
                            "NEXT — "
                            +
                            next_label
                        ),
                        state="normal",
                    )

            else:
                # Cross-chapter/unusual references use a generic manual
                # progression. END READING is the safe stop.
                self.scripture_main_button.configure(
                    text="NEXT VERSE",
                    state="normal",
                )

        except Exception as exc:
            self.scripture_main_button.configure(
                text="START READING",
                state="normal",
            )

            self.append_log(
                (
                    "Could not refresh Scripture controls: "
                    f"{exc}"
                )
            )

    def _consume_scripture_chapter(
        self
    ):
        (
            plan,
            sequence,
            state,
            index,
            item,
        ) = self._current_rotation_item()

        if item is None:
            raise RuntimeError(
                "The sermon chapter sequence is already complete."
            )

        role = str(
            item.get(
                "role",
                ""
            )
        ).lower()

        if role != "reference":
            current_name = str(
                item.get(
                    "chapter_name",
                    ""
                )
                or
                item.get(
                    "display",
                    ""
                )
                or
                role
            )

            raise RuntimeError(
                (
                    "The Scripture reading is not the next sermon step yet.\n\n"
                    "Next chapter: "
                    +
                    current_name
                    +
                    "\n\nMark the earlier chapter first."
                )
            )

        if self.chapter_test_mode:
            result = fire_item(
                item,
                test_mode=True,
            )

            self.chapter_test_index = (
                index
                +
                1
            )

            return {
                "item": item,
                "result": result,
            }

        # Normal Sunday mode must have a real recording so the Scripture
        # chapter can actually be written into the file.
        client = self.connect_obs()

        if client is None:
            raise RuntimeError(
                "OBS is not reachable."
            )

        status = get_obs_status(
            client
        )

        if not status.get(
            "recording"
        ):
            raise RuntimeError(
                (
                    "Start Recording before the Scripture reading.\n\n"
                    "SSS needs the recording active so it can create the "
                    "Scripture chapter marker."
                )
            )

        return fire_next()

    def scripture_main_action(
        self
    ):
        if self.scripture_reading_busy:
            return

        if not self.scripture_reading_active:
            self.start_scripture_reading()
            return

        if (
            self.scripture_verses_exact
            and
            self.scripture_verses
            and
            (
                self.scripture_verse_index
                +
                1
            )
            >=
            len(
                self.scripture_verses
            )
        ):
            self.end_scripture_reading()
            return

        self.scripture_next_verse()

    def start_scripture_reading(
        self
    ):
        if self.scripture_reading_busy:
            return

        plan = read_json(
            SERMON_PLAN_FILE,
            {}
        )

        date_ok, date_detail = (
            self.sermon_plan_is_for_upcoming_service(
                plan
            )
        )

        if not date_ok:
            messagebox.showwarning(
                "Scripture Reading",
                (
                    "The loaded sermon plan is not for the upcoming Sunday.\n\n"
                    +
                    date_detail
                    +
                    "\n\nRefresh the pastor sermon email before starting "
                    "the Scripture reading."
                ),
            )
            return

        reference = " ".join(
            str(
                plan.get(
                    "scripture",
                    ""
                )
            ).split()
        )

        if not reference:
            messagebox.showwarning(
                "Scripture Reading",
                "No Scripture reference is loaded for this sermon."
            )
            return

        parsed = parse_scripture_reference(
            reference
        )

        self.scripture_reference = reference
        self.scripture_verses = list(
            parsed.get(
                "verses",
                []
            )
        )
        self.scripture_verses_exact = bool(
            parsed.get(
                "exact",
                False
            )
        )
        self.scripture_verse_index = -1
        self.scripture_reading_busy = True
        self.refresh_scripture_controls()

        def worker():
            transitioned = False
            chapter_consumed = False

            try:
                # Validate the chapter order BEFORE changing what viewers see.
                (
                    _plan,
                    _sequence,
                    _state,
                    _index,
                    item,
                ) = self._current_rotation_item()

                if (
                    item is None
                    or
                    str(
                        item.get(
                            "role",
                            ""
                        )
                    ).lower()
                    !=
                    "reference"
                ):
                    current_name = (
                        str(
                            item.get(
                                "chapter_name",
                                ""
                            )
                            or
                            item.get(
                                "display",
                                ""
                            )
                        )
                        if item
                        else
                        "Chapters complete"
                    )

                    raise RuntimeError(
                        (
                            "Scripture is not the next chapter yet. "
                            "Next: "
                            +
                            current_name
                        )
                    )

                # In normal mode, verify recording before touching Preview.
                if not self.chapter_test_mode:
                    client = self.connect_obs()

                    if client is None:
                        raise RuntimeError(
                            "OBS is not reachable."
                        )

                    status = get_obs_status(
                        client
                    )

                    if not status.get(
                        "recording"
                    ):
                        raise RuntimeError(
                            (
                                "Start Recording first. The Scripture button "
                                "also creates the Scripture chapter marker."
                            )
                        )

                # Presenter is deliberately prepared before the service.
                # START assumes the first Scripture verse is already selected.
                # No Presenter MIDI is sent until the volunteer presses NEXT.
                self.post_ui(
                    self.append_log,
                    (
                        "Scripture START: Presenter preset to first verse of "
                        +
                        reference
                        +
                        "."
                    ),
                )

                # Scripture / presentation -> Preview.
                # PROFILE mode uses the scene name discovered/saved in the
                # active church profile. LEGACY mode keeps the existing
                # Ctrl+F15 path. Any profile failure also falls back to F15.
                self.load_obs_view_to_preview(
                    "scripture",
                    send_webcam_tp_to_preview,
                )

                time.sleep(
                    float(
                        self.config.get(
                            "scripture_preview_settle_seconds",
                            0.30
                        )
                    )
                )

                # Preview -> Program.
                send_studio_transition()
                transitioned = True

                time.sleep(
                    float(
                        self.config.get(
                            "scripture_transition_settle_seconds",
                            0.25
                        )
                    )
                )

                # Consume the existing Scripture/reference chapter so the
                # normal sermon button automatically advances to Point 1.
                chapter_result = (
                    self._consume_scripture_chapter()
                )
                chapter_consumed = True

                # Visual discovery selected the Scripture service item and
                # used Presenter's Change Slide command with velocity 0, so
                # the first verse is already active. Do NOT send an extra NEXT.
                first_midi_error = ""
                first_index = 0

                self.post_ui(
                    self._finish_start_scripture_reading,
                    chapter_result,
                    first_index,
                    first_midi_error,
                )

            except Exception as exc:
                if transitioned and not chapter_consumed:
                    try:
                        send_studio_transition()
                    except Exception:
                        pass

                self.post_ui(
                    self._fail_scripture_action,
                    str(
                        exc
                    ),
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _finish_start_scripture_reading(
        self,
        chapter_result,
        first_index,
        midi_error
    ):
        self.scripture_reading_busy = False
        self.scripture_reading_active = True
        self.scripture_verse_index = int(
            first_index
        )

        chapter_name = self.scripture_reference

        self.append_log(
            (
                "Scripture reading started: "
                +
                chapter_name
                +
                (
                    " [TEST — marker simulated]"
                    if self.chapter_test_mode
                    else
                    " [chapter marker added]"
                )
            )
        )

        if midi_error:
            self.append_log(
                (
                    "Presenter did not advance to the first verse: "
                    +
                    midi_error
                )
            )

            reason = " ".join(
                str(
                    midi_error
                    or
                    "MIDI did not send."
                ).split()
            )

            messagebox.showwarning(
                "Presenter",
                (
                    "Presenter did not advance to the first verse.\n\n"
                    f"MIDI: {reason}\n\n"
                    "The Scripture view and chapter are already correct. "
                    "After fixing MIDI, press NEXT once."
                ),
            )

        self.refresh_scripture_controls()
        self.refresh_chapter_rotation_button()

    def _fail_scripture_action(
        self,
        message
    ):
        self.scripture_reading_busy = False
        self.scripture_reading_active = False
        self.scripture_verse_index = -1

        self.refresh_scripture_controls()
        self.refresh_chapter_rotation_button()

        messagebox.showwarning(
            "Scripture Reading",
            str(
                message
            ),
        )

    def scripture_next_verse(
        self
    ):
        if (
            not self.scripture_reading_active
            or
            self.scripture_reading_busy
        ):
            return

        self.scripture_reading_busy = True
        self.refresh_scripture_controls()

        def worker():
            try:
                presentation = get_profile_presentation_settings(
                    load_active_profile()
                )

                if (
                    presentation.get(
                        "settings_source"
                    )
                    ==
                    "profile"
                ):
                    self.post_ui(
                        self.append_log,
                        (
                            "Presentation adapter NEXT -> "
                            +
                            presentation.get(
                                "provider",
                                "Presentation"
                            )
                        ),
                    )

                    next_slide_profile()

                else:
                    settings = (
                        self._scripture_midi_settings()
                    )

                    self.post_ui(
                        self.append_log,
                        (
                            "Presenter NEXT verse -> Port Presenter | Ch 10 | Note 60 | Vel 126 | Note On only"
                        ),
                    )

                    presenter_next(
                        port_name=settings[
                            "port_name"
                        ],
                        channel=settings[
                            "channel"
                        ],
                        note=settings[
                            "next_note"
                        ],
                        velocity=settings[
                            "velocity"
                        ],
                    )

                self.post_ui(
                    self._finish_scripture_next
                )

            except Exception as exc:
                self.post_ui(
                    self._fail_scripture_midi,
                    str(
                        exc
                    ),
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _finish_scripture_next(
        self
    ):
        self.scripture_reading_busy = False
        self.scripture_verse_index += 1

        if (
            self.scripture_verses_exact
            and
            self.scripture_verses
        ):
            self.scripture_verse_index = min(
                self.scripture_verse_index,
                len(
                    self.scripture_verses
                )
                -
                1,
            )

            current = self.scripture_verses[
                self.scripture_verse_index
            ]

            self.append_log(
                (
                    "Presenter Scripture: "
                    +
                    current
                )
            )

        else:
            self.append_log(
                "Presenter advanced one Scripture verse."
            )

        self.refresh_scripture_controls()

    def scripture_back_verse(
        self
    ):
        if (
            not self.scripture_reading_active
            or
            self.scripture_reading_busy
        ):
            return

        if self.scripture_verse_index <= 0:
            return

        self.scripture_reading_busy = True
        self.refresh_scripture_controls()

        def worker():
            try:
                presentation = get_profile_presentation_settings(
                    load_active_profile()
                )

                if (
                    presentation.get(
                        "settings_source"
                    )
                    ==
                    "profile"
                ):
                    self.post_ui(
                        self.append_log,
                        (
                            "Presentation adapter PREVIOUS -> "
                            +
                            presentation.get(
                                "provider",
                                "Presentation"
                            )
                        ),
                    )

                    previous_slide_profile()

                else:
                    settings = (
                        self._scripture_midi_settings()
                    )

                    self.post_ui(
                        self.append_log,
                        (
                            "Presenter PREVIOUS verse -> Port Presenter | Ch 10 | Note 62 | Vel 126 | Note On only"
                        ),
                    )

                    presenter_back(
                        port_name=settings[
                            "port_name"
                        ],
                        channel=settings[
                            "channel"
                        ],
                        note=settings[
                            "back_note"
                        ],
                        velocity=settings[
                            "velocity"
                        ],
                    )

                self.post_ui(
                    self._finish_scripture_back
                )

            except Exception as exc:
                self.post_ui(
                    self._fail_scripture_midi,
                    str(
                        exc
                    ),
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _finish_scripture_back(
        self
    ):
        self.scripture_reading_busy = False
        self.scripture_verse_index = max(
            0,
            self.scripture_verse_index
            -
            1,
        )

        if (
            self.scripture_verses_exact
            and
            self.scripture_verses
        ):
            self.append_log(
                (
                    "Presenter Scripture: "
                    +
                    self.scripture_verses[
                        self.scripture_verse_index
                    ]
                )
            )

        else:
            self.append_log(
                "Presenter moved back one Scripture verse."
            )

        self.refresh_scripture_controls()

    def _fail_scripture_midi(
        self,
        message
    ):
        self.scripture_reading_busy = False
        self.refresh_scripture_controls()

        messagebox.showwarning(
            "Presenter",
            (
                "Presenter did not move.\n\n"
                +
                str(
                    message
                )
            ),
        )

    def end_scripture_reading(
        self
    ):
        if (
            not self.scripture_reading_active
            or
            self.scripture_reading_busy
        ):
            return

        self.scripture_reading_busy = True
        self.refresh_scripture_controls()

        def worker():
            try:
                # End Scripture by loading the Normal / webcam view into
                # OBS Preview, then performing the normal Studio Mode
                # transition to Program. PROFILE mode uses the mapped scene;
                # LEGACY mode keeps Ctrl+F13. Profile failures fall back to F13.
                self.load_obs_view_to_preview(
                    "normal",
                    send_webcam_only,
                )

                time.sleep(
                    float(
                        self.config.get(
                            "scripture_preview_settle_seconds",
                            0.30
                        )
                    )
                )

                send_studio_transition()

                time.sleep(
                    float(
                        self.config.get(
                            "scripture_transition_settle_seconds",
                            0.25
                        )
                    )
                )

                self.post_ui(
                    self._finish_end_scripture_reading
                )

            except Exception as exc:
                self.post_ui(
                    self._fail_end_scripture_reading,
                    str(
                        exc
                    ),
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _finish_end_scripture_reading(
        self
    ):
        self.scripture_reading_busy = False
        self.scripture_reading_active = False
        self.scripture_verse_index = -1

        self.append_log(
            (
                "Scripture reading ended; webcam only loaded to Preview (Ctrl+F13) and transitioned to Program (Ctrl+Shift)."
            )
        )

        self.refresh_scripture_controls()
        self.refresh_chapter_rotation_button()

    def _fail_end_scripture_reading(
        self,
        message
    ):
        self.scripture_reading_busy = False
        self.refresh_scripture_controls()

        messagebox.showwarning(
            "Scripture Reading",
            (
                "Could not switch OBS back to webcam only.\n\n"
                +
                str(
                    message
                )
            ),
        )

    def refresh_chapter_rotation_button(
        self,
        reset_if_plan_changed=False
    ):
        if not hasattr(
            self,
            "chapter_button"
        ):
            return

        try:
            if reset_if_plan_changed:
                # load_rotation automatically resets the REAL sequence only
                # if the sermon plan itself changed.
                load_rotation()

            complete = False
            use_scripture_control = False

            if self.chapter_test_mode:
                plan, sequence, state = (
                    load_rotation()
                )

                index = int(
                    self.chapter_test_index
                )

                if index >= len(
                    sequence
                ):
                    label = "TEST COMPLETE"
                    complete = True

                else:
                    item = sequence[
                        index
                    ]

                    if (
                        str(
                            item.get(
                                "role",
                                ""
                            )
                        ).lower()
                        ==
                        "reference"
                    ):
                        label = "USE SCRIPTURE BUTTON ↑"
                        use_scripture_control = True

                    else:
                        name = " ".join(
                            str(
                                item.get(
                                    "chapter_name",
                                    ""
                                )
                                or
                                item.get(
                                    "display",
                                    ""
                                )
                            ).split()
                        )

                        label = (
                            "TEST — "
                            +
                            (
                                name
                                or
                                "NEXT CHAPTER"
                            )
                        )

                        if len(
                            label
                        ) > 54:
                            label = (
                                label[
                                    :53
                                ].rstrip()
                                +
                                "…"
                            )

            else:
                plan, sequence, state = (
                    load_rotation()
                )

                index = int(
                    state.get(
                        "next_index",
                        0
                    )
                )

                if index >= len(
                    sequence
                ):
                    label = "CHAPTERS COMPLETE"
                    complete = True

                else:
                    item = sequence[
                        index
                    ]

                    if (
                        str(
                            item.get(
                                "role",
                                ""
                            )
                        ).lower()
                        ==
                        "reference"
                    ):
                        # Scripture has its own dedicated full-service
                        # controller now. Prevent a volunteer from firing the
                        # same reference from two different buttons.
                        label = "USE SCRIPTURE BUTTON ↑"
                        use_scripture_control = True

                    else:
                        label = next_button_text(
                            max_length=54
                        )

            self.chapter_button.configure(
                text=label,
                state=(
                    "disabled"
                    if (
                        complete
                        or
                        use_scripture_control
                        or
                        self.chapter_action_running
                    )
                    else
                    "normal"
                ),
            )

            self.refresh_scripture_controls()

        except Exception as exc:
            self.chapter_button.configure(
                text=(
                    "TEST — NEXT SERMON CHAPTER"
                    if self.chapter_test_mode
                    else
                    "NEXT SERMON CHAPTER"
                ),
                state=(
                    "disabled"
                    if self.chapter_action_running
                    else
                    "normal"
                ),
            )

            self.append_log(
                (
                    "Could not refresh chapter button: "
                    f"{exc}"
                )
            )

    def reset_sermon_chapter_rotation(
        self
    ):
        try:
            if self.chapter_test_mode:
                # Reset ONLY the disposable test sequence. The actual
                # service position remains untouched.
                self.chapter_test_index = 0

                self.refresh_chapter_rotation_button()

                self.append_log(
                    (
                        "TEST MODE chapter sequence reset to Prayer; "
                        "real sermon position unchanged."
                    )
                )

            else:
                reset_rotation()

                self.refresh_chapter_rotation_button()

                self.append_log(
                    "Sermon chapter rotation reset to Prayer."
                )

        except Exception as exc:
            messagebox.showerror(
                "Sermon Chapters",
                (
                    "Could not reset sermon chapters:\n"
                    f"{exc}"
                ),
            )

    def _finish_next_sermon_chapter(
        self,
        result,
        error
    ):
        self.chapter_action_running = False

        if error:
            self.refresh_chapter_rotation_button()

            messagebox.showwarning(
                "Sermon Chapter",
                str(
                    error
                ),
            )

            return

        item = result[
            "item"
        ]

        action = result[
            "result"
        ]

        chapter_name = str(
            item.get(
                "chapter_name",
                ""
            )
        )

        method = str(
            action.get(
                "chapter_method",
                ""
            )
        )

        is_test = bool(
            action.get(
                "test_mode",
                False
            )
        )

        if item.get(
            "lt_hotkey"
        ):
            if (
                str(
                    item.get(
                        "lt_hotkey",
                        ""
                    )
                ).upper().startswith(
                    "LT1_SLT"
                )
            ):
                if action.get(
                    "lt_switch_triggered"
                ):
                    seconds = action.get(
                        "lt_display_seconds",
                        11
                    )

                    lt_text = (
                        f" + LT1 lower third ({seconds:g} sec)"
                    )

                elif action.get(
                    "lt_triggered"
                ):
                    lt_text = (
                        " (LT1 slot loaded, but LT1 ON/OFF toggle failed)"
                    )

                else:
                    lt_text = (
                        " (LT1 slot hotkey unavailable)"
                    )

            else:
                lt_text = (
                    " + lower-third slot"
                    if action.get(
                        "lt_triggered"
                    )
                    else
                    " (lower-third hotkey unavailable)"
                )

        else:
            lt_text = ""

        if is_test:
            self.append_log(
                (
                    f"TEST ONLY — {chapter_name} "
                    "[chapter marker simulated / not written]"
                    f"{lt_text}"
                )
            )

        else:
            self.append_log(
                (
                    f"Sermon chapter: {chapter_name}"
                    f" [{method}]"
                    f"{lt_text}"
                )
            )

        self.refresh_chapter_rotation_button()
        self.run_preflight_async()

    def sync_reset_chapters_button(
        self
    ):
        if not hasattr(
            self,
            "reset_chapters_button"
        ):
            return

        try:
            self.reset_chapters_button.configure(
                state=(
                    "disabled"
                    if self.last_recording_state
                    else "normal"
                )
            )
        except Exception:
            pass

    def reset_chapter_rotation(
        self
    ):
        if self.last_recording_state:
            self.append_log(
                (
                    "RESET LT / CHAPTERS ignored: OBS is currently "
                    "recording. Stop recording first."
                )
            )
            return

        try:
            reset_rotation()

        except Exception as exc:
            self.append_log(
                f"Could not reset the chapter/lower-third sequence: {exc}"
            )
            return

        self.append_log(
            "Sermon lower-third/chapter sequence reset to the beginning."
        )

        self.refresh_chapter_rotation_button()

    def next_sermon_chapter(
        self
    ):
        if not self.config.get(
            "chapter_rotation_enabled",
            True
        ):
            messagebox.showwarning(
                "Sermon Chapters",
                "Sermon chapter rotation is disabled."
            )
            return

        if self.chapter_action_running:
            return

        self.chapter_action_running = True

        # Disable immediately to prevent a volunteer double-click from
        # advancing two chapter markers or overlapping 11-second LTs.
        try:
            self.chapter_button.configure(
                state="disabled"
            )
        except Exception:
            pass

        if self.chapter_test_mode:
            test_index = int(
                self.chapter_test_index
            )

            def worker():
                try:
                    plan, sequence, state = (
                        load_rotation()
                    )

                    if test_index >= len(
                        sequence
                    ):
                        raise RuntimeError(
                            "The Chapter / LT test sequence is complete."
                        )

                    item = sequence[
                        test_index
                    ]

                    result = fire_item(
                        item,
                        test_mode=True,
                    )

                    # Advance ONLY the disposable in-memory test pointer.
                    # chapter_rotation_state.json is never changed.
                    self.chapter_test_index = (
                        test_index
                        +
                        1
                    )

                    payload = {
                        "item": item,
                        "result": result,
                    }

                    self.post_ui(
                        self._finish_next_sermon_chapter,
                        payload,
                        None,
                    )

                except Exception as exc:
                    self.post_ui(
                        self._finish_next_sermon_chapter,
                        None,
                        str(
                            exc
                        ),
                    )

        else:
            def worker():
                try:
                    result = fire_next()

                    self.post_ui(
                        self._finish_next_sermon_chapter,
                        result,
                        None,
                    )

                except Exception as exc:
                    self.post_ui(
                        self._finish_next_sermon_chapter,
                        None,
                        str(
                            exc
                        ),
                    )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def manual_chapter(
        self
    ):
        client = (
            self.connect_obs()
        )

        if client is None:
            messagebox.showerror(
                "Sunday Mode",
                "OBS is not reachable."
            )

            return

        status = (
            get_obs_status(
                client
            )
        )

        if not status[
            "recording"
        ]:
            messagebox.showwarning(
                "Sunday Mode",
                "OBS is not recording."
            )

            return

        try:
            client.send(
                "CreateRecordChapter",
                {
                    "chapterName":
                        "Manual Chapter"
                },
                raw=True,
            )

            self.append_log(
                "Manual chapter marker added."
            )

        except Exception as exc:
            messagebox.showerror(
                "Sunday Mode",
                f"Chapter failed:\n{exc}"
            )

    def alarm(
        self,
        message
    ):
        now = time.time()

        if (
            now
            -
            self.last_alarm_time
            <
            45
        ):
            return

        self.last_alarm_time = (
            now
        )

        self.post_ui(
            self.append_log,
            (
                "WATCHDOG: "
                +
                message
            )
        )

        if winsound:
            try:
                winsound.MessageBeep(
                    winsound.MB_ICONHAND
                )
            except Exception:
                pass

    def watchdog(
        self
    ):
        client = (
            self.connect_obs()
        )

        if client is None:
            if self.service_commanded:
                self.alarm(
                    "OBS disconnected during service."
                )

            return

        status = (
            get_obs_status(
                client
            )
        )

        current_recording_state = bool(
            status[
                "recording"
            ]
        )

        previous_recording_state = (
            self.last_recording_state
        )

        self.last_recording_state = (
            current_recording_state
        )

        self.sync_reset_chapters_button()

        self.update_sunday_freeze(
            recording=current_recording_state,
            streaming=bool(
                status[
                    "streaming"
                ]
            ),
        )

        # Verify the actual output file is growing, not merely that OBS
        # reports "recording".
        self.update_recording_growth(
            client
        )

        # If recording was started directly in OBS, adopt it into the
        # Sunday watchdog so file-growth/audio protections still apply.
        if (
            previous_recording_state is not True
            and
            current_recording_state is True
        ):
            self.recording_started_at = time.time()
            self.last_recording_growth_time = time.time()
            self.last_recording_size = 0
            self.active_recording_path = ""
            self.service_commanded = True

            try:
                reset_rotation()

                self.post_ui(
                    self.refresh_chapter_rotation_button
                )
            except Exception:
                pass

            self.post_ui(
                self.append_log,
                (
                    "Detected recording started directly in OBS; "
                    "SSS watchdog protections are now active."
                )
            )

        # Catch a recording stop made directly in OBS rather than through
        # the SSS STOP RECORDING button.
        if (
            previous_recording_state is True
            and
            current_recording_state is False
        ):
            self.service_commanded = False

            self.post_ui(
                self.start_youtube_upload_waiter
            )

            self.post_ui(
                self.start_post_service_supervisor
            )

        if (
            self.service_commanded
            and
            not self.service_ending
        ):
            if not current_recording_state:
                self.alarm(
                    "Recording is OFF."
                )

            audio_ok, detail = (
                self.check_audio()
            )

            if not audio_ok:
                self.alarm(
                    "OBS monitor audio device disappeared."
                )

            # Live level sanity comes from a completely separate helper
            # process, so a meter/driver failure cannot crash the SSS GUI.
            grace = float(
                self.config.get(
                    "audio_sanity_start_grace_seconds",
                    90
                )
            )

            if (
                self.config.get(
                    "audio_sanity_enabled",
                    True
                )
                and
                self.recording_started_at
                and
                time.time()
                -
                self.recording_started_at
                >=
                grace
            ):
                meter_ok, meter_detail, meter_warning = (
                    self.check_audio_sanity_status()
                )

                if not meter_ok:
                    payload = read_json(
                        AUDIO_STATUS_FILE,
                        {}
                    )

                    meter_state = str(
                        payload.get(
                            "state",
                            ""
                        )
                    ).upper()

                    if meter_state in {
                        "SILENT",
                        "CLIPPING",
                    }:
                        self.alarm(
                            meter_detail
                        )

            disk_ok, detail, warning = (
                self.check_disk()
            )

            if not disk_ok:
                self.alarm(
                    "Recording drive problem: "
                    f"{detail}"
                )

        if (
            self.config.get(
                "auto_start_sermon_ai",
                True
            )
            and
            not process_running_contains(
                "sermon_ai.py"
            )
        ):
            launcher = Path(
                self.config[
                    "sermon_ai_launcher"
                ]
            )

            if launcher.exists():
                try:
                    os.startfile(
                        launcher
                    )

                    self.post_ui(
                        self.append_log,
                        "Watchdog restarted Sermon AI."
                    )

                except Exception:
                    pass

    def periodic_refresh(
        self
    ):
        self.run_preflight_async()
        self.check_completion_notification()
        self.refresh_chapter_rotation_button(
            reset_if_plan_changed=True
        )

        # Keep MUTE / UNMUTE wording synchronized with OBS even if someone
        # changed the mute state directly in OBS or from another controller.
        try:
            self.refresh_mute_button_label()
        except Exception:
            pass

        if not self.watchdog_running:
            self.watchdog_running = True

            threading.Thread(
                target=self._watchdog_worker,
                daemon=True,
            ).start()

        refresh_ms = int(
            float(
                self.config.get(
                    "dashboard_refresh_seconds",
                    5
                )
            )
            *
            1000
        )

        self.root.after(
            refresh_ms,
            self.periodic_refresh
        )

    def _watchdog_worker(
        self
    ):
        try:
            self.watchdog()
        finally:
            self.watchdog_running = False


def _update_health_check_requested():
    return (
        "--update-health-check"
        in
        sys.argv
    )


def _argument_value(
    name,
    default=""
):
    try:
        index = sys.argv.index(
            name
        )

        return sys.argv[
            index
            +
            1
        ]

    except Exception:
        return default


def run_update_health_check():
    """
    Safe updater handshake.

    Reaching this function means the newly-built EXE successfully imported the
    full Sunday Mode dependency graph. It intentionally does NOT create
    SundayModeApp, open OBS, launch Presenter, recall a PTZ preset, touch Gmail,
    migrate profiles, or start/stop Recording/Streaming.
    """
    result_path = _argument_value(
        "--update-health-check",
        ""
    )

    expected_version = _argument_value(
        "--expected-version",
        ""
    )

    result = {
        "ok": False,
        "version": APP_VERSION,
        "app_id": APP_ID,
        "detail": "",
        "timestamp": datetime.datetime.now().astimezone().isoformat(),
        "safe_startup_only": True,
    }

    try:
        if (
            expected_version
            and
            str(
                expected_version
            )
            !=
            str(
                APP_VERSION
            )
        ):
            raise RuntimeError(
                (
                    "Expected version "
                    +
                    str(
                        expected_version
                    )
                    +
                    " but this EXE reports "
                    +
                    str(
                        APP_VERSION
                    )
                    +
                    "."
                )
            )

        # Verify that the two core installed-app launch modules are importable
        # without invoking their UI or live-service actions.
        import sss_settings
        import sss_updater_core

        _ = sss_settings
        _ = sss_updater_core

        result[
            "ok"
        ] = True

        result[
            "detail"
        ] = (
            "Sunday Service System import/startup health check passed."
        )

    except Exception as exc:
        result[
            "detail"
        ] = str(
            exc
        )

    if result_path:
        try:
            path = Path(
                result_path
            )

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temp = path.with_suffix(
                path.suffix
                +
                ".tmp"
            )

            temp.write_text(
                json.dumps(
                    result,
                    indent=2,
                    ensure_ascii=False,
                )
                +
                "\n",
                encoding="utf-8",
            )

            os.replace(
                temp,
                path,
            )

        except Exception:
            return 3

    return (
        0
        if result.get(
            "ok"
        )
        else
        2
    )


def main():
    if _update_health_check_requested():
        raise SystemExit(
            run_update_health_check()
        )

    set_windows_app_user_model_id()

    root = tk.Tk()

    if not CONFIG_PATH.exists():
        from sss_first_run import run_first_run_setup

        if not run_first_run_setup(root):
            root.destroy()
            return

    SundayModeApp(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()
