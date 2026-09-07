import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from sss_obs_profile import discover_obs
from sss_profile import (
    get_profile_obs_settings,
    get_profile_setup_status,
    load_active_profile,
    save_active_obs_settings,
    save_active_setup_choices,
)

PRESENTATION_OPTIONS = (
    "Not configured",
    "ProPresenter",
    "WorshipTools Presenter",
    "Bitfocus Companion",
    "PowerPoint / Keyboard",
    "None",
)

CAMERA_OPTIONS = (
    "Not configured",
    "PTZOptics / HTTP-CGI",
    "VISCA over IP",
    "Fixed camera",
    "None",
)

SERMON_SOURCE_OPTIONS = (
    "Manual",
    "Pastor Email",
    "Planning Software",
    "Imported File",
    "Other",
)

YOUTUBE_PRIVACY_OPTIONS = ("public", "unlisted", "private")

YOUTUBE_AUDIENCE_OPTIONS = ("channel_default", "not_made_for_kids", "made_for_kids")

PLANNING_TRANSLATION_OPTIONS = ("ESV", "NIV", "KJV", "NASB", "NLT", "Other")

# Steps shown only during a brand-new-church first run (in addition to the
# existing welcome/church/obs/review steps every wizard run already has).
FIRST_RUN_EXTRA_STEPS = (
    "recording",
    "audio",
    "camera",
    "presentation",
    "sermon_source",
    "youtube",
)


def choose_guess(values, current, guesses):
    values = list(values or [])
    current = str(current or "").strip()

    if current in values:
        return current

    lower = {value.lower(): value for value in values}

    for guess in guesses:
        if guess.lower() in lower:
            return lower[guess.lower()]

    for guess in guesses:
        for value in values:
            if guess.lower() in value.lower():
                return value

    return values[0] if values else ""


class SetupWizard:
    def __init__(self, parent, on_saved=None, first_run=False):
        self.parent = parent
        self.on_saved = on_saved
        self.first_run = bool(first_run)
        self.profile = load_active_profile()
        self.profile_name = str(
            self.profile.get("profile_name", "Church Profile")
        )

        saved_obs = get_profile_obs_settings(self.profile)
        integrations = self.profile.get("integrations", {})

        self.church_name_var = tk.StringVar(
            value=str(
                self.profile.get("church", {}).get(
                    "name",
                    self.profile_name,
                )
            )
        )

        self.obs_source_var = tk.StringVar(
            value=saved_obs.get("settings_source", "legacy")
        )
        self.obs_collection_var = tk.StringVar(
            value=saved_obs.get("scene_collection", "")
        )
        self.obs_normal_var = tk.StringVar(
            value=saved_obs.get("normal_scene", "")
        )
        self.obs_scripture_var = tk.StringVar(
            value=saved_obs.get("scripture_scene", "")
        )
        self.obs_sermon_var = tk.StringVar(
            value=saved_obs.get("sermon_scene", "")
        )
        self.discovered_at = saved_obs.get("discovered_at", "")

        self.presentation_var = tk.StringVar(
            value=str(
                integrations.get("presentation", {}).get(
                    "provider",
                    "Not configured",
                )
                or
                "Not configured"
            )
        )
        self.camera_var = tk.StringVar(
            value=str(
                integrations.get("camera", {}).get(
                    "provider",
                    "Not configured",
                )
                or
                "Not configured"
            )
        )
        self.sermon_source_var = tk.StringVar(
            value=str(
                integrations.get("sermon_source", {}).get(
                    "provider",
                    "Manual",
                )
                or
                "Manual"
            )
        )

        # --- First-run-only fields (Recording / Audio / Camera details /
        # Sermon source details / YouTube). Harmless to create even when
        # first_run is False; they're just never shown or read from then.
        camera = integrations.get("camera", {})
        camera_connection = camera.get("connection", {})
        camera_presets = camera.get("presets", {})
        audio = integrations.get("audio", {})
        youtube = integrations.get("youtube", {})

        self.recording_folder_var = tk.StringVar(value="")

        self.audio_enabled_var = tk.BooleanVar(
            value=bool(audio.get("enabled", False))
        )
        self.audio_loopback_name_var = tk.StringVar(value="")
        self.audio_loopback_label_var = tk.StringVar(value="Audio Interface")
        self.critical_inputs_var = tk.StringVar(value="")
        self.recommended_inputs_var = tk.StringVar(value="")
        self.emergency_mute_inputs_var = tk.StringVar(value="")
        self.audio_sanity_inputs_var = tk.StringVar(value="")

        self.camera_enabled_var = tk.BooleanVar(
            value=bool(camera.get("enabled", False))
        )
        self.ptz_ip_var = tk.StringVar(value=str(camera_connection.get("host", "")))
        self.ptz_scheme_var = tk.StringVar(value="http")
        self.ptz_port_var = tk.StringVar(value="")
        self.ptz_username_var = tk.StringVar(value="")
        self.ptz_password_var = tk.StringVar(value="")
        self.ptz_startup_preset_var = tk.StringVar(
            value=str(camera_presets.get("startup", 2))
        )
        self.ptz_worship_preset_var = tk.StringVar(
            value=str(camera_presets.get("worship", 1))
        )
        self.ptz_pastor_preset_var = tk.StringVar(
            value=str(camera_presets.get("pastor", 2))
        )
        self.camera_test_status_var = tk.StringVar(value="")

        self.gmail_sender_var = tk.StringVar(value="")
        self.planning_account_id_var = tk.StringVar(value="")
        self.planning_translation_var = tk.StringVar(value="ESV")
        self.planning_service_time_var = tk.StringVar(value="")
        self.default_preacher_var = tk.StringVar(value="")
        self.help_contact_var = tk.StringVar(value="")

        self.youtube_enabled_var = tk.BooleanVar(
            value=bool(youtube.get("enabled", False))
        )
        self.youtube_channel_id_var = tk.StringVar(value="")
        self.youtube_channel_name_var = tk.StringVar(value="")
        self.youtube_handle_var = tk.StringVar(value="")
        self.youtube_privacy_var = tk.StringVar(value="public")
        self.youtube_category_var = tk.StringVar(value="29")
        self.youtube_notify_var = tk.BooleanVar(value=True)
        self.youtube_audience_var = tk.StringVar(value="channel_default")
        self.youtube_test_status_var = tk.StringVar(value="")

        self.discovery_status_var = tk.StringVar(
            value="Open OBS, then click CONNECT & DISCOVER."
        )
        self.review_var = tk.StringVar()
        self.progress_var = tk.StringVar()
        self.obs_combos = []

        self.window = tk.Toplevel(parent)
        self.window.title("Sunday Service System — Setup Wizard")
        self.window.minsize(760, 640)

        if not self.first_run:
            # A Toplevel marked transient to its parent can't be shown by
            # Windows while that parent is withdrawn/hidden. During a
            # first run, `parent` is just a bookkeeping root with nothing
            # to be transient to, so skip it entirely and let the wizard
            # behave as its own independent top-level window.
            try:
                self.window.transient(parent)
            except Exception:
                pass

        self.current_step = 0
        self.build()
        self.show_step(0)
        self._center_and_raise()

    def _center_and_raise(self):
        """
        A Toplevel created under a withdrawn parent root doesn't reliably
        get an on-screen position or foreground focus on Windows - without
        this, the wizard can silently open off-screen/behind other windows
        while the console stays open, looking like nothing happened.
        """
        self.window.update_idletasks()

        width = max(self.window.winfo_reqwidth(), 820)
        height = max(self.window.winfo_reqheight(), 690)
        x = max(0, (self.window.winfo_screenwidth() - width) // 2)
        y = max(0, (self.window.winfo_screenheight() - height) // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

        self.window.deiconify()
        self.window.lift()
        self.window.attributes("-topmost", True)
        self.window.after(300, lambda: self.window.attributes("-topmost", False))
        self.window.focus_force()

    def build(self):
        outer = ttk.Frame(self.window, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="SSS FIRST-RUN SETUP",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(0, 4))

        ttk.Label(
            outer,
            text="Profile: " + self.profile_name,
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(0, 8))

        ttk.Label(
            outer,
            textvariable=self.progress_var,
        ).pack(pady=(0, 8))

        self.body = ttk.Frame(outer)
        self.body.pack(fill="both", expand=True)
        self.body.rowconfigure(0, weight=1)
        self.body.columnconfigure(0, weight=1)

        self.step_names = ["welcome", "church", "obs"]

        if self.first_run:
            self.step_names += list(FIRST_RUN_EXTRA_STEPS)
        else:
            self.step_names.append("integrations")

        self.step_names.append("review")

        self.pages = [
            getattr(self, "build_" + name)()
            for name in self.step_names
        ]

        nav = ttk.Frame(outer)
        nav.pack(fill="x", pady=(12, 0))
        nav.columnconfigure(1, weight=1)

        self.back_button = ttk.Button(
            nav,
            text="BACK",
            command=self.go_back,
        )
        self.back_button.grid(row=0, column=0, sticky="w")

        ttk.Button(
            nav,
            text="CLOSE",
            command=self.window.destroy,
        ).grid(row=0, column=1)

        self.next_button = ttk.Button(
            nav,
            text="NEXT",
            command=self.go_next,
        )
        self.next_button.grid(row=0, column=2, sticky="e")

    def page(self):
        page = ttk.Frame(self.body, padding=12)
        page.grid(row=0, column=0, sticky="nsew")
        return page

    def build_welcome(self):
        page = self.page()

        ttk.Label(
            page,
            text="Welcome",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        status = get_profile_setup_status(self.profile)

        intro = (
            "This wizard sets up Sunday Service System for your church "
            "from scratch. Each integration below can be skipped and "
            "turned on later - nothing here starts recording or streaming."
            if self.first_run
            else (
                "This wizard builds the portable configuration for this "
                "church profile. It never starts recording or streaming, "
                "and Legacy behavior remains available as a fallback."
            )
        )

        ttk.Label(
            page,
            text=intro,
            wraplength=720,
            justify="left",
        ).pack(anchor="w", fill="x")

        ttk.Label(
            page,
            text=f"Current setup: {status['completed']}/{status['total']} complete",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(18, 8))

        if not self.first_run:
            ttk.Label(
                page,
                text=(
                    "OBS, Presentation, Camera, Audio, and Sermon Source now have "
                    "profile-backed paths. The wizard chooses the provider; the "
                    "dedicated Settings page is where live PROFILE mode is tested "
                    "and explicitly activated."
                ),
                wraplength=720,
                justify="left",
            ).pack(anchor="w", fill="x")

        return page

    def build_church(self):
        page = self.page()

        ttk.Label(
            page,
            text="Church",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(
            page,
            text="Church name",
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)

        ttk.Entry(
            page,
            textvariable=self.church_name_var,
            width=50,
        ).grid(row=1, column=1, sticky="ew", pady=6)

        if self.first_run:
            ttk.Label(
                page,
                text="Lead pastor / preacher name (optional)",
            ).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)

            ttk.Entry(
                page,
                textvariable=self.default_preacher_var,
                width=50,
            ).grid(row=2, column=1, sticky="ew", pady=6)

            ttk.Label(
                page,
                text="Volunteer help contact (optional)",
            ).grid(row=3, column=0, sticky="w", padx=(0, 10), pady=6)

            ttk.Entry(
                page,
                textvariable=self.help_contact_var,
                width=50,
            ).grid(row=3, column=1, sticky="ew", pady=6)

            ttk.Label(
                page,
                text=(
                    "Shown on the main dashboard so volunteers know who to "
                    "ask for help - e.g. \"Call Jane Smith - 555-123-4567\". "
                    "Leave blank to hide it."
                ),
                wraplength=700,
                justify="left",
            ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(
            page,
            text=(
                "This travels with the profile instead of being hard-coded "
                "into the SSS application."
            ),
            wraplength=700,
            justify="left",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

        page.columnconfigure(1, weight=1)
        return page

    def build_obs(self):
        page = self.page()

        ttk.Label(
            page,
            text="OBS",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Radiobutton(
            page,
            text=(
                "SKIP FOR NOW — I haven't set up OBS scenes yet "
                "(configure this later from Settings)"
                if self.first_run
                else "LEGACY — keep current working SSS / OBS behavior"
            ),
            variable=self.obs_source_var,
            value="legacy",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Radiobutton(
            page,
            text="PROFILE — use the scene mappings below",
            variable=self.obs_source_var,
            value="profile",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Button(
            page,
            text="CONNECT & DISCOVER OBS",
            command=self.discover_obs_now,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 6))

        ttk.Label(
            page,
            textvariable=self.discovery_status_var,
            wraplength=700,
            justify="left",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 10))

        rows = (
            ("Scene collection", self.obs_collection_var),
            ("Normal / webcam scene", self.obs_normal_var),
            ("Scripture / presentation scene", self.obs_scripture_var),
            ("Main / sermon scene (optional)", self.obs_sermon_var),
        )

        for row_num, (label, var) in enumerate(rows, start=5):
            ttk.Label(
                page,
                text=label,
            ).grid(row=row_num, column=0, sticky="w", padx=(0, 10), pady=5)

            combo = ttk.Combobox(
                page,
                textvariable=var,
                state="readonly",
            )
            combo.grid(row=row_num, column=1, sticky="ew", pady=5)
            self.obs_combos.append(combo)

        page.columnconfigure(1, weight=1)
        return page

    def build_recording(self):
        page = self.page()

        ttk.Label(
            page,
            text="Recording",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(
            page,
            text="Recording folder",
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)

        ttk.Entry(
            page,
            textvariable=self.recording_folder_var,
            width=45,
        ).grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Button(
            page,
            text="BROWSE...",
            command=self.browse_recording_folder,
        ).grid(row=1, column=2, sticky="w", padx=(8, 0), pady=6)

        ttk.Label(
            page,
            text=(
                "This is where OBS saves the full-service recording, and "
                "where sermon clips/shorts get processed. Choose a drive "
                "with plenty of free space."
            ),
            wraplength=700,
            justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))

        page.columnconfigure(1, weight=1)
        return page

    def browse_recording_folder(self):
        chosen = filedialog.askdirectory(parent=self.window)
        if chosen:
            self.recording_folder_var.set(chosen)

    def build_audio(self):
        page = self.page()

        ttk.Label(
            page,
            text="Audio",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Checkbutton(
            page,
            text="Enable audio sanity monitoring (silence/clipping alerts)",
            variable=self.audio_enabled_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        fields = (
            ("OBS-monitor audio device name", self.audio_loopback_name_var),
            ("Audio device display label", self.audio_loopback_label_var),
            ("Critical inputs (comma-separated)", self.critical_inputs_var),
            ("Recommended inputs (comma-separated)", self.recommended_inputs_var),
            ("Emergency-mute inputs (comma-separated)", self.emergency_mute_inputs_var),
            ("Audio-sanity-monitored inputs (comma-separated)", self.audio_sanity_inputs_var),
        )

        for row_num, (label, var) in enumerate(fields, start=2):
            ttk.Label(
                page,
                text=label,
            ).grid(row=row_num, column=0, sticky="w", padx=(0, 10), pady=5)

            ttk.Entry(
                page,
                textvariable=var,
                width=45,
            ).grid(row=row_num, column=1, sticky="ew", pady=5)

        ttk.Label(
            page,
            text=(
                "Input names must match your OBS source names exactly. "
                "You can leave these blank and fill them in later from "
                "Settings once OBS is set up."
            ),
            wraplength=700,
            justify="left",
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 0))

        page.columnconfigure(1, weight=1)
        return page

    def build_camera(self):
        page = self.page()

        ttk.Label(
            page,
            text="Camera",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Checkbutton(
            page,
            text="This church has a PTZ camera to control",
            variable=self.camera_enabled_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(
            page,
            text="Camera type",
        ).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)

        ttk.Combobox(
            page,
            textvariable=self.camera_var,
            values=CAMERA_OPTIONS,
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", pady=5)

        fields = (
            ("Camera IP address", self.ptz_ip_var),
            ("HTTP port (blank = default)", self.ptz_port_var),
            ("Username (if required)", self.ptz_username_var),
            ("Password (if required)", self.ptz_password_var),
            ("Worship preset number", self.ptz_worship_preset_var),
            ("Pastor / startup preset number", self.ptz_pastor_preset_var),
        )

        for row_num, (label, var) in enumerate(fields, start=3):
            ttk.Label(
                page,
                text=label,
            ).grid(row=row_num, column=0, sticky="w", padx=(0, 10), pady=5)

            ttk.Entry(
                page,
                textvariable=var,
                width=35,
            ).grid(row=row_num, column=1, sticky="ew", pady=5)

        ttk.Button(
            page,
            text="TEST CONNECTION",
            command=self.test_camera_connection,
        ).grid(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 4))

        ttk.Label(
            page,
            textvariable=self.camera_test_status_var,
            wraplength=700,
            justify="left",
        ).grid(row=10, column=0, columnspan=2, sticky="w")

        page.columnconfigure(1, weight=1)
        return page

    def test_camera_connection(self):
        from sss_camera_adapters import check_tcp_connection

        host = self.ptz_ip_var.get().strip()

        if not host:
            self.camera_test_status_var.set(
                "Enter the camera's IP address first."
            )
            return

        try:
            port = int(self.ptz_port_var.get().strip() or "80")
        except ValueError:
            self.camera_test_status_var.set(
                "Port must be a number, or leave it blank."
            )
            return

        self.camera_test_status_var.set("Testing...")
        self.window.update_idletasks()

        try:
            result = check_tcp_connection(host, port, timeout=3.0)
            self.camera_test_status_var.set(
                f"Reachable — {result['host']}:{result['port']} responded."
            )
        except Exception as exc:
            self.camera_test_status_var.set(
                f"Could not reach the camera: {exc}"
            )

    def build_presentation(self):
        page = self.page()

        ttk.Label(
            page,
            text="Presentation Software",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(
            page,
            text="Presentation software",
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=7)

        ttk.Combobox(
            page,
            textvariable=self.presentation_var,
            values=PRESENTATION_OPTIONS,
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", pady=7)

        ttk.Label(
            page,
            text=(
                "Choose \"None\" or \"Not configured\" to skip this - it "
                "can be turned on later from Settings."
            ),
            wraplength=700,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(18, 0))

        page.columnconfigure(1, weight=1)
        return page

    def build_sermon_source(self):
        page = self.page()

        ttk.Label(
            page,
            text="Sermon Information Source",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(
            page,
            text="How does the sermon title/Scripture/outline get to SSS?",
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=7)

        combo = ttk.Combobox(
            page,
            textvariable=self.sermon_source_var,
            values=SERMON_SOURCE_OPTIONS,
            state="readonly",
        )
        combo.grid(row=1, column=1, sticky="ew", pady=7)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda event: self.refresh_sermon_source_fields(),
        )

        self.sermon_source_detail = ttk.Frame(page)
        self.sermon_source_detail.grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0)
        )
        self.sermon_source_detail.columnconfigure(1, weight=1)

        page.columnconfigure(1, weight=1)
        self.refresh_sermon_source_fields()
        return page

    def refresh_sermon_source_fields(self):
        for child in self.sermon_source_detail.winfo_children():
            child.destroy()

        provider = self.sermon_source_var.get()

        if provider == "Pastor Email":
            ttk.Label(
                self.sermon_source_detail,
                text="Pastor's sermon-email address",
            ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)

            ttk.Entry(
                self.sermon_source_detail,
                textvariable=self.gmail_sender_var,
                width=40,
            ).grid(row=0, column=1, sticky="ew", pady=5)

        elif provider == "Planning Software":
            fields = (
                ("Planning account ID", self.planning_account_id_var, "entry"),
                ("Bible translation", self.planning_translation_var, "combo"),
                ("Service time (e.g. 9:00am)", self.planning_service_time_var, "entry"),
            )

            for row_num, (label, var, kind) in enumerate(fields):
                ttk.Label(
                    self.sermon_source_detail,
                    text=label,
                ).grid(row=row_num, column=0, sticky="w", padx=(0, 10), pady=5)

                if kind == "combo":
                    ttk.Combobox(
                        self.sermon_source_detail,
                        textvariable=var,
                        values=PLANNING_TRANSLATION_OPTIONS,
                        state="readonly",
                        width=37,
                    ).grid(row=row_num, column=1, sticky="ew", pady=5)
                else:
                    ttk.Entry(
                        self.sermon_source_detail,
                        textvariable=var,
                        width=40,
                    ).grid(row=row_num, column=1, sticky="ew", pady=5)

    def build_youtube(self):
        page = self.page()

        ttk.Label(
            page,
            text="YouTube Upload",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Checkbutton(
            page,
            text="Automatically upload the full sermon recording to YouTube",
            variable=self.youtube_enabled_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(
            page,
            text="YouTube channel ID",
        ).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(
            page, textvariable=self.youtube_channel_id_var, width=40
        ).grid(row=2, column=1, sticky="ew", pady=5)

        ttk.Label(
            page,
            text="YouTube channel name",
        ).grid(row=3, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(
            page, textvariable=self.youtube_channel_name_var, width=40
        ).grid(row=3, column=1, sticky="ew", pady=5)

        ttk.Label(
            page,
            text="Channel handle (e.g. @yourchurch)",
        ).grid(row=4, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(
            page, textvariable=self.youtube_handle_var, width=40
        ).grid(row=4, column=1, sticky="ew", pady=5)

        ttk.Label(
            page,
            text="Privacy status",
        ).grid(row=5, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Combobox(
            page,
            textvariable=self.youtube_privacy_var,
            values=YOUTUBE_PRIVACY_OPTIONS,
            state="readonly",
        ).grid(row=5, column=1, sticky="ew", pady=5)

        ttk.Label(
            page,
            text="Category ID (29 = Nonprofits & Activism)",
        ).grid(row=6, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(
            page, textvariable=self.youtube_category_var, width=10
        ).grid(row=6, column=1, sticky="w", pady=5)

        ttk.Checkbutton(
            page,
            text="Notify subscribers on upload",
            variable=self.youtube_notify_var,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(
            page,
            text="Made-for-kids audience",
        ).grid(row=8, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Combobox(
            page,
            textvariable=self.youtube_audience_var,
            values=YOUTUBE_AUDIENCE_OPTIONS,
            state="readonly",
        ).grid(row=8, column=1, sticky="ew", pady=5)

        ttk.Button(
            page,
            text="TEST CHANNEL",
            command=self.test_youtube_channel,
        ).grid(row=9, column=0, columnspan=2, sticky="ew", pady=(10, 4))

        ttk.Label(
            page,
            textvariable=self.youtube_test_status_var,
            wraplength=700,
            justify="left",
        ).grid(row=10, column=0, columnspan=2, sticky="w")

        page.columnconfigure(1, weight=1)
        return page

    def test_youtube_channel(self):
        import re
        import urllib.request

        channel_id = self.youtube_channel_id_var.get().strip()
        handle = self.youtube_handle_var.get().strip()

        if not channel_id and not handle:
            self.youtube_test_status_var.set(
                "Enter a channel ID or handle first."
            )
            return

        if channel_id:
            url = f"https://www.youtube.com/channel/{channel_id}"
        else:
            url = "https://www.youtube.com/@" + handle.lstrip("@")

        self.youtube_test_status_var.set("Looking up channel...")
        self.window.update_idletasks()

        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36"
                    )
                },
            )

            with urllib.request.urlopen(request, timeout=6) as response:
                if response.status != 200:
                    raise RuntimeError(f"YouTube returned HTTP {response.status}.")

                html = response.read(2_000_000).decode("utf-8", errors="replace")

            title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""
            title = title.removesuffix(" - YouTube").strip()

            if not title or title.lower() == "youtube":
                raise RuntimeError("No channel found at that ID/handle.")

            self.youtube_test_status_var.set(f"Found channel: \"{title}\"")

        except Exception as exc:
            self.youtube_test_status_var.set(
                f"Could not verify the channel: {exc}"
            )

    def build_integrations(self):
        page = self.page()

        ttk.Label(
            page,
            text="Other Integrations",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        rows = (
            ("Presentation software", self.presentation_var, PRESENTATION_OPTIONS),
            ("Camera", self.camera_var, CAMERA_OPTIONS),
            ("Sermon information", self.sermon_source_var, SERMON_SOURCE_OPTIONS),
        )

        for row_num, (label, var, values) in enumerate(rows, start=1):
            ttk.Label(
                page,
                text=label,
            ).grid(row=row_num, column=0, sticky="w", padx=(0, 10), pady=7)

            ttk.Combobox(
                page,
                textvariable=var,
                values=values,
                state="readonly",
            ).grid(row=row_num, column=1, sticky="ew", pady=7)

        ttk.Label(
            page,
            text=(
                "These choices identify the integrations used by this church. "
                "Changing a provider here never silently activates a new live "
                "adapter; use its dedicated Settings page to test and select PROFILE."
            ),
            wraplength=700,
            justify="left",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(18, 0))

        page.columnconfigure(1, weight=1)
        return page

    def build_review(self):
        page = self.page()

        ttk.Label(
            page,
            text="Review",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(
            page,
            textvariable=self.review_var,
            wraplength=720,
            justify="left",
        ).pack(anchor="w", fill="x")

        return page

    def discover_obs_now(self):
        try:
            data = discover_obs()
            collections = tuple(data.get("collections", []))
            scenes = tuple(data.get("scenes", []))

            self.obs_combos[0].configure(values=collections)

            for combo in self.obs_combos[1:]:
                combo.configure(values=scenes)

            current_collection = str(data.get("current_collection", ""))
            legacy_collection = str(data.get("legacy_collection", ""))

            if self.obs_collection_var.get() in collections:
                pass
            elif legacy_collection in collections:
                self.obs_collection_var.set(legacy_collection)
            elif current_collection in collections:
                self.obs_collection_var.set(current_collection)
            elif collections:
                self.obs_collection_var.set(collections[0])

            self.obs_normal_var.set(
                choose_guess(
                    scenes,
                    self.obs_normal_var.get(),
                    ("webcam only", "camera only", "normal camera", "camera"),
                )
            )

            self.obs_scripture_var.set(
                choose_guess(
                    scenes,
                    self.obs_scripture_var.get(),
                    ("webcam TP", "ProPresenter", "Presenter", "Scripture", "Presentation"),
                )
            )

            current_program = str(data.get("current_program_scene", ""))

            if not self.obs_sermon_var.get() and current_program in scenes:
                self.obs_sermon_var.set(current_program)

            self.discovered_at = str(data.get("discovered_at", ""))

            self.discovery_status_var.set(
                f"Connected — discovered {len(scenes)} scene(s) in "
                f"{current_collection or 'the current scene collection'}."
            )

        except Exception as exc:
            self.discovery_status_var.set(
                "OBS discovery failed: " + str(exc)
            )

    def validate_step(self):
        name = self.step_names[self.current_step]

        if name == "church" and not self.church_name_var.get().strip():
            messagebox.showwarning(
                "SSS Setup",
                "Church name is required.",
                parent=self.window,
            )
            return False

        if name == "obs" and self.obs_source_var.get() == "profile":
            missing = []

            if not self.obs_collection_var.get().strip():
                missing.append("scene collection")
            if not self.obs_normal_var.get().strip():
                missing.append("normal / webcam scene")
            if not self.obs_scripture_var.get().strip():
                missing.append("scripture / presentation scene")

            if missing:
                messagebox.showwarning(
                    "SSS Setup",
                    "PROFILE mode still needs: " + ", ".join(missing) + ".",
                    parent=self.window,
                )
                return False

        if name == "recording" and not self.recording_folder_var.get().strip():
            messagebox.showwarning(
                "SSS Setup",
                "Recording folder is required.",
                parent=self.window,
            )
            return False

        if name == "camera" and self.camera_enabled_var.get():
            if not self.ptz_ip_var.get().strip():
                messagebox.showwarning(
                    "SSS Setup",
                    "Enter the camera's IP address, or uncheck "
                    "\"This church has a PTZ camera\".",
                    parent=self.window,
                )
                return False

        if name == "youtube" and self.youtube_enabled_var.get():
            if not self.youtube_channel_id_var.get().strip():
                messagebox.showwarning(
                    "SSS Setup",
                    "Enter the YouTube channel ID, or uncheck automatic upload.",
                    parent=self.window,
                )
                return False

        return True

    def refresh_review(self):
        obs_mode = self.obs_source_var.get().upper()

        if obs_mode == "LEGACY":
            obs_detail = "current known-good SSS / OBS behavior"
        else:
            obs_detail = (
                f"{self.obs_collection_var.get()} | "
                f"normal={self.obs_normal_var.get()} | "
                f"scripture={self.obs_scripture_var.get()}"
            )

        lines = [
            "Church: " + self.church_name_var.get().strip(),
            "",
            "OBS: " + obs_mode + " — " + obs_detail,
        ]

        if self.first_run:
            lines += [
                "",
                "Recording folder: " + self.recording_folder_var.get().strip(),
                "",
                "Audio monitoring: "
                + ("ON" if self.audio_enabled_var.get() else "OFF (skipped)"),
                "",
                "Camera: "
                + (
                    f"{self.camera_var.get()} at {self.ptz_ip_var.get().strip()}"
                    if self.camera_enabled_var.get()
                    else "OFF (skipped)"
                ),
                "",
                "Presentation: " + self.presentation_var.get(),
                "",
                "Sermon source: " + self.sermon_source_var.get(),
                "",
                "YouTube upload: "
                + (
                    self.youtube_channel_name_var.get().strip()
                    or self.youtube_channel_id_var.get().strip()
                    if self.youtube_enabled_var.get()
                    else "OFF (skipped)"
                ),
                "",
                "FINISH & SAVE creates sunday_config.json and launches "
                "Sunday Service System. It never starts recording or streaming.",
            ]
        else:
            lines += [
                "",
                "Presentation: " + self.presentation_var.get(),
                "",
                "Camera: " + self.camera_var.get(),
                "",
                "Sermon information: " + self.sermon_source_var.get(),
                "",
                "FINISH & SAVE writes profile setup only. "
                "It never starts recording or streaming.",
            ]

        self.review_var.set("\n".join(lines))

    def show_step(self, index):
        self.current_step = max(0, min(len(self.pages) - 1, index))
        self.pages[self.current_step].tkraise()

        self.progress_var.set(
            f"Step {self.current_step + 1} of {len(self.pages)}"
        )
        self.back_button.configure(
            state="disabled" if self.current_step == 0 else "normal"
        )

        if self.current_step == len(self.pages) - 1:
            self.refresh_review()
            self.next_button.configure(text="FINISH & SAVE")
        else:
            self.next_button.configure(text="NEXT")

    def go_back(self):
        self.show_step(self.current_step - 1)

    def go_next(self):
        if not self.validate_step():
            return

        if self.current_step < len(self.pages) - 1:
            self.show_step(self.current_step + 1)
        else:
            self.finish()

    def _split_names(self, value):
        return [
            item.strip()
            for item in str(value or "").split(",")
            if item.strip()
        ]

    def _collect_answers(self):
        """First-run-only: gather every wizard field into a flat dict keyed
        by sunday_config.json field names, for sss_config_bootstrap."""
        answers = {
            "recording_folder": self.recording_folder_var.get().strip(),
            "default_preacher": self.default_preacher_var.get().strip(),
            "help_contact_text": self.help_contact_var.get().strip(),
            "audio_sanity_enabled": bool(self.audio_enabled_var.get()),
            "audio_loopback_name": self.audio_loopback_name_var.get().strip(),
            "audio_loopback_label": self.audio_loopback_label_var.get().strip(),
            "critical_inputs": self._split_names(self.critical_inputs_var.get()),
            "recommended_inputs": self._split_names(self.recommended_inputs_var.get()),
            "emergency_mute_inputs": self._split_names(self.emergency_mute_inputs_var.get()),
            "audio_sanity_inputs": self._split_names(self.audio_sanity_inputs_var.get()),
            "ptz_camera_enabled": bool(self.camera_enabled_var.get()),
            "auto_import_sermon_email": self.sermon_source_var.get() == "Pastor Email",
            "auto_upload_youtube": bool(self.youtube_enabled_var.get()),
        }

        scene_collection = self.obs_collection_var.get().strip()

        if scene_collection:
            answers["scene_collection"] = scene_collection

        if self.camera_enabled_var.get():
            answers.update({
                "ptz_camera_ip": self.ptz_ip_var.get().strip(),
                "ptz_camera_scheme": self.ptz_scheme_var.get().strip() or "http",
                "ptz_camera_http_port": self.ptz_port_var.get().strip(),
                "ptz_camera_username": self.ptz_username_var.get().strip(),
                "ptz_camera_password": self.ptz_password_var.get().strip(),
                "ptz_startup_preset": self._to_int(self.ptz_startup_preset_var.get(), 2),
                "ptz_worship_preset": self._to_int(self.ptz_worship_preset_var.get(), 1),
                "ptz_pastor_preset": self._to_int(self.ptz_pastor_preset_var.get(), 2),
            })

        if self.sermon_source_var.get() == "Pastor Email":
            sender = self.gmail_sender_var.get().strip()
            answers["gmail_sermon_sender"] = sender
            answers["gmail_sermon_senders"] = [sender] if sender else []

        if self.sermon_source_var.get() == "Planning Software":
            answers.update({
                "planning_account_id": self.planning_account_id_var.get().strip(),
                "planning_translation": self.planning_translation_var.get().strip(),
                "planning_service_time": self.planning_service_time_var.get().strip(),
            })

        if self.youtube_enabled_var.get():
            answers.update({
                "youtube_expected_channel_id": self.youtube_channel_id_var.get().strip(),
                "youtube_expected_channel_name": self.youtube_channel_name_var.get().strip(),
                "youtube_expected_handle": self.youtube_handle_var.get().strip(),
                "youtube_privacy_status": self.youtube_privacy_var.get().strip() or "public",
                "youtube_category_id": self.youtube_category_var.get().strip() or "29",
                "youtube_notify_subscribers": bool(self.youtube_notify_var.get()),
                "youtube_audience": self.youtube_audience_var.get().strip() or "channel_default",
            })

        return answers

    @staticmethod
    def _to_int(value, default):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    def finish(self):
        try:
            save_active_obs_settings(
                settings_source=self.obs_source_var.get(),
                scene_collection=self.obs_collection_var.get(),
                normal_scene=self.obs_normal_var.get(),
                scripture_scene=self.obs_scripture_var.get(),
                sermon_scene=self.obs_sermon_var.get(),
                discovered_at=self.discovered_at,
            )

            save_active_setup_choices(
                church_name=self.church_name_var.get(),
                presentation_provider=self.presentation_var.get(),
                camera_provider=self.camera_var.get(),
                sermon_source_provider=self.sermon_source_var.get(),
                wizard_completed=True,
            )

            if self.first_run:
                from sss_config_bootstrap import (
                    build_sunday_config,
                    provision_filesystem,
                    write_sunday_config,
                )

                config = build_sunday_config(self.profile, self._collect_answers())
                write_sunday_config(config)
                provision_filesystem(config)

            status = get_profile_setup_status()

            if callable(self.on_saved):
                try:
                    self.on_saved()
                except Exception:
                    pass

            messagebox.showinfo(
                "SSS Setup Complete",
                f"Setup saved.\n\n"
                f"{status['completed']}/{status['total']} setup areas complete.\n\n"
                "Recording and streaming were not touched.",
                parent=self.window,
            )
            self.window.destroy()

        except Exception as exc:
            messagebox.showerror(
                "SSS Setup Failed",
                str(exc),
                parent=self.window,
            )


def open_setup_wizard(parent, on_saved=None, first_run=False):
    return SetupWizard(parent, on_saved=on_saved, first_run=first_run)
