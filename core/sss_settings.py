import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import (
    filedialog,
    messagebox,
    ttk,
)

from sss_profile import (
    active_profile_path,
    get_profile_audio_settings,
    get_profile_camera_settings,
    get_profile_capabilities,
    get_profile_obs_settings,
    get_profile_presentation_settings,
    get_profile_sermon_source_settings,
    get_profile_setup_status,
    load_active_profile,
    list_profile_migration_status,
    migrate_all_installed_profiles,
    migration_backups_dir,
    PROFILE_SCHEMA_VERSION,
    profile_root,
    set_windows_app_user_model_id,
)

from sss_profile_manager import ProfileManager

from sss_diagnostics import (
    export_diagnostic_bundle,
    run_full_system_test,
)

from sss_recovery import (
    create_recovery_snapshot,
    last_known_good_snapshot,
    list_recovery_snapshots,
    restore_recovery_snapshot,
    restore_safety_status,
)

from sss_event_history import (
    EVENT_ROOT,
    export_event_history_text,
    format_event_time,
    get_last_unexpected_shutdown,
    read_recent_events,
)

from sss_secrets_vault import (
    OBS_SECRET_NAME,
    copy_legacy_obs_password_to_vault,
    delete_obs_vault_password,
    obs_vault_status,
    remove_legacy_obs_password,
    security_overview,
    set_obs_vault_password,
    test_obs_vault_connection,
    vault_available,
)

from sss_runtime import (
    application_install_root,
    launch_updater,
    open_install_folder,
    runtime_info,
)

from sss_updater_core import (
    UPDATE_ROOT,
    installed_app_processes,
    read_update_manifest,
    update_status,
    verify_update_package,
    version_is_newer,
)

from sss_release_trust import (
    SIGNED_UPDATES_REQUIRED,
    TRUSTED_UPDATE_SIGNER_THUMBPRINTS,
)
from sss_signing import (
    release_signing_status,
)

from sss_update_feed import (
    DOWNLOAD_ROOT,
    check_release_feed,
    download_release_package,
    load_feed_config,
    online_update_status,
    save_feed_config,
)










class SSSSettings(ProfileManager):
    """
    Full SSS Setup / Settings shell.

    The Settings shell reuses the already-proven ProfileManager setup dialogs
    instead of duplicating live configuration logic. The new shell organizes
    everything by application area so future adapters can be added one page at
    a time without cluttering the Sunday volunteer dashboard.
    """

    def __init__(
        self,
        root
    ):
        self.root = root

        self.root.title(
            "Sunday Service System — Setup & Settings"
        )

        self.root.geometry(
            "1040x720"
        )

        self.root.minsize(
            900,
            640
        )

        # Some pages (Updates, Recovery) have enough stacked content that
        # the fixed 1040x720 default clips the bottom of the page. Open
        # maximized so everything is visible without a manual resize;
        # 1040x720 remains as the restore size if the user un-maximizes.
        try:
            self.root.state(
                "zoomed"
            )
        except Exception:
            pass

        self.name_var = tk.StringVar()
        self.mode_var = tk.StringVar()
        self.path_var = tk.StringVar()
        self.setup_status_var = tk.StringVar()
        self.profile_selector_var = tk.StringVar()
        self.profile_selector_map = {}

        self.page_title_var = tk.StringVar()
        self.page_subtitle_var = tk.StringVar()

        self.summary_vars = {
            "church": tk.StringVar(),
            "obs": tk.StringVar(),
            "presentation": tk.StringVar(),
            "camera": tk.StringVar(),
            "audio": tk.StringVar(),
            "sermon": tk.StringVar(),
            "streaming": tk.StringVar(),
            "automation": tk.StringVar(),
            "updates": tk.StringVar(),
            "security": tk.StringVar(),
            "advanced": tk.StringVar(),
        }

        self.pages = {}
        self.nav_buttons = {}
        self.active_page = "church"

        self.diagnostic_report = None
        self.diagnostic_running = False
        self.diagnostic_overall_var = tk.StringVar(
            value="NOT RUN — Full System Test has not been run yet."
        )
        self.diagnostic_detail_var = tk.StringVar(
            value=(
                "The test is read-only: it will not start/stop recording or "
                "streaming, move cameras/slides, or change audio mute state."
            )
        )
        self.diagnostic_tree = None
        self.diagnostic_run_button = None

        self.recovery_status_var = tk.StringVar(
            value="Recovery snapshots have not been loaded yet."
        )
        self.recovery_safety_var = tk.StringVar(
            value="Restore safety has not been checked yet."
        )
        self.recovery_tree = None
        self.recovery_item_paths = {}

        self.history_status_var = tk.StringVar(
            value="Event History has not been loaded yet."
        )
        self.history_crash_var = tk.StringVar(
            value="No unexpected-shutdown information loaded yet."
        )
        self.history_filter_var = tk.StringVar(
            value="ALL"
        )
        self.history_tree = None
        self.history_events = []

        self.migration_status_var = tk.StringVar(
            value=(
                "Profile schema status has not been checked yet."
            )
        )

        self.security_status_var = tk.StringVar(
            value="Security status has not been checked yet."
        )
        self.security_detail_var = tk.StringVar(
            value=(
                "SSS prefers Windows Credential Manager for supported secrets "
                "while keeping church profiles credential-free."
            )
        )
        self.obs_secret_entry_var = tk.StringVar()

        self.runtime_status_var = tk.StringVar(
            value="Runtime packaging status has not been loaded yet."
        )

        self.update_package_var = tk.StringVar()
        self.update_status_var = tk.StringVar(
            value="Update status has not been loaded yet."
        )
        self.update_detail_var = tk.StringVar(
            value=(
                "v3.1 can check a signed HTTPS release feed, download a signed "
                ".sssupdate package, verify it, and hand it to the protected updater."
            )
        )
        self.selected_update_manifest = None

        self.update_feed_url_var = tk.StringVar()
        self.update_channel_var = tk.StringVar(
            value="stable"
        )
        self.online_update_status_var = tk.StringVar(
            value="Online update feed has not been checked yet."
        )
        self.online_release = None
        self.online_busy = False

        self._build_settings_ui()
        self.refresh()
        self.show_page(
            "church"
        )

    def _build_settings_ui(
        self
    ):
        outer = ttk.Frame(
            self.root,
            padding=14,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        header = ttk.Frame(
            outer
        )

        header.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            header,
            text="SSS SETUP & SETTINGS",
            font=(
                "Segoe UI",
                20,
                "bold"
            ),
        ).pack(
            side="left"
        )

        ttk.Label(
            header,
            textvariable=self.setup_status_var,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
        ).pack(
            side="right"
        )

        profile_bar = ttk.LabelFrame(
            outer,
            text="Active Church Profile",
            padding=9,
        )

        profile_bar.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        profile_bar.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            profile_bar,
            text="Profile",
            font=(
                "Segoe UI",
                9,
                "bold"
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
        )

        self.profile_selector = ttk.Combobox(
            profile_bar,
            textvariable=self.profile_selector_var,
            state="readonly",
            postcommand=self.refresh_profile_selector,
            width=46,
        )

        self.profile_selector.grid(
            row=0,
            column=1,
            sticky="ew",
        )

        self.profile_selector.bind(
            "<<ComboboxSelected>>",
            self.on_profile_selected,
            add="+",
        )

        ttk.Button(
            profile_bar,
            text="NEW PROFILE",
            command=self.new_profile,
        ).grid(
            row=0,
            column=2,
            padx=(
                8,
                0
            ),
        )

        body = ttk.Frame(
            outer
        )

        body.pack(
            fill="both",
            expand=True,
        )

        body.columnconfigure(
            1,
            weight=1
        )

        body.rowconfigure(
            0,
            weight=1
        )

        nav = ttk.LabelFrame(
            body,
            text="Settings",
            padding=8,
        )

        nav.grid(
            row=0,
            column=0,
            sticky="nsw",
            padx=(
                0,
                10
            ),
        )

        content = ttk.Frame(
            body
        )

        content.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        content.rowconfigure(
            1,
            weight=1
        )

        content.columnconfigure(
            0,
            weight=1
        )

        title_frame = ttk.Frame(
            content
        )

        title_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(
                0,
                8
            ),
        )

        ttk.Label(
            title_frame,
            textvariable=self.page_title_var,
            font=(
                "Segoe UI",
                17,
                "bold"
            ),
        ).pack(
            anchor="w"
        )

        ttk.Label(
            title_frame,
            textvariable=self.page_subtitle_var,
            wraplength=720,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                3,
                0
            ),
        )

        self.page_host = ttk.Frame(
            content
        )

        self.page_host.grid(
            row=1,
            column=0,
            sticky="nsew",
        )

        self.page_host.rowconfigure(
            0,
            weight=1
        )

        self.page_host.columnconfigure(
            0,
            weight=1
        )

        sections = (
            (
                "church",
                "Church",
            ),
            (
                "obs",
                "OBS",
            ),
            (
                "presentation",
                "Presentation",
            ),
            (
                "camera",
                "Camera",
            ),
            (
                "audio",
                "Audio",
            ),
            (
                "sermon",
                "Sermon",
            ),
            (
                "streaming",
                "Streaming",
            ),
            (
                "automation",
                "Automation",
            ),
            (
                "updates",
                "Updates",
            ),
            (
                "security",
                "Security",
            ),
            (
                "diagnostics",
                "Diagnostics",
            ),
            (
                "recovery",
                "Recovery",
            ),
            (
                "history",
                "Event History",
            ),
            (
                "advanced",
                "Advanced",
            ),
        )

        for row, (
            key,
            label
        ) in enumerate(
            sections
        ):
            button = ttk.Button(
                nav,
                text=label,
                command=lambda k=key:
                    self.show_page(
                        k
                    ),
                width=18,
            )

            button.grid(
                row=row,
                column=0,
                sticky="ew",
                pady=3,
            )

            self.nav_buttons[
                key
            ] = button

        self._build_pages()

        footer = ttk.Frame(
            outer
        )

        footer.pack(
            fill="x",
            pady=(
                10,
                0
            ),
        )

        ttk.Button(
            footer,
            text="RUN / EDIT SETUP WIZARD",
            command=self.open_setup_wizard,
        ).pack(
            side="left"
        )

        ttk.Button(
            footer,
            text="RUN FULL SYSTEM TEST",
            command=self.open_and_run_diagnostics,
        ).pack(
            side="left",
            padx=(
                8,
                0
            ),
        )

        ttk.Button(
            footer,
            text="CLOSE",
            command=self.root.destroy,
        ).pack(
            side="right"
        )

    def _new_page(
        self,
        key
    ):
        page = ttk.Frame(
            self.page_host,
            padding=12,
        )

        page.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.pages[
            key
        ] = page

        return page

    def _summary_box(
        self,
        parent,
        key,
        title="Current Profile"
    ):
        frame = ttk.LabelFrame(
            parent,
            text=title,
            padding=12,
        )

        frame.pack(
            fill="x",
            pady=(
                0,
                12
            ),
        )

        ttk.Label(
            frame,
            textvariable=self.summary_vars[
                key
            ],
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            fill="x"
        )

        return frame

    def _action_button(
        self,
        parent,
        text,
        command
    ):
        ttk.Button(
            parent,
            text=text,
            command=command,
        ).pack(
            fill="x",
            pady=4,
        )

    def _build_pages(
        self
    ):
        # Church --------------------------------------------------
        page = self._new_page(
            "church"
        )

        self._summary_box(
            page,
            "church",
            "Church / Profile",
        )

        self._action_button(
            page,
            "RUN / EDIT FIRST-RUN SETUP WIZARD",
            self.open_setup_wizard,
        )

        profile_actions = ttk.LabelFrame(
            page,
            text="Profile Management",
            padding=10,
        )

        profile_actions.pack(
            fill="x",
            pady=(
                8,
                0
            ),
        )

        for text, command in (
            (
                "NEW PROFILE",
                self.new_profile,
            ),
            (
                "EXPORT ACTIVE PROFILE",
                self.export_profile,
            ),
            (
                "IMPORT PROFILE",
                self.import_profile_file,
            ),
            (
                "OPEN PROFILE FOLDER",
                self.open_folder,
            ),
        ):
            self._action_button(
                profile_actions,
                text,
                command,
            )

        # OBS -----------------------------------------------------
        page = self._new_page(
            "obs"
        )

        self._summary_box(
            page,
            "obs",
            "OBS Profile Configuration",
        )

        self._action_button(
            page,
            "CONFIGURE OBS FOR THIS PROFILE",
            self.open_obs_setup,
        )

        ttk.Label(
            page,
            text=(
                "OBS is already a live profile-backed integration. Keep LEGACY "
                "for the existing known-good path, or explicitly select PROFILE "
                "after scene discovery and testing."
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=8,
        )

        # Presentation -------------------------------------------
        page = self._new_page(
            "presentation"
        )

        self._summary_box(
            page,
            "presentation",
            "Presentation Integration",
        )

        self._action_button(
            page,
            "CONFIGURE PRESENTATION FOR THIS PROFILE",
            self.open_presentation_setup,
        )

        ttk.Label(
            page,
            text=(
                "Live adapters currently include WorshipTools Presenter and "
                "ProPresenter. Companion and generic keyboard adapters remain "
                "reserved for later implementation."
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=8,
        )

        # Camera --------------------------------------------------
        page = self._new_page(
            "camera"
        )

        self._summary_box(
            page,
            "camera",
            "Camera Integration",
        )

        self._action_button(
            page,
            "CONFIGURE CAMERA FOR THIS PROFILE",
            self.open_camera_setup,
        )

        self._action_button(
            page,
            "EDIT CAMERA TYPE IN SETUP WIZARD",
            self.open_setup_wizard,
        )

        ttk.Label(
            page,
            text=(
                "v2.0 supports a live profile-backed PTZOptics / HTTP-CGI "
                "camera adapter while retaining the existing machine-local "
                "legacy PTZ configuration as the safe fallback."
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=8,
        )

        # Audio ---------------------------------------------------
        page = self._new_page(
            "audio"
        )

        self._summary_box(
            page,
            "audio",
            "Audio",
        )

        self._action_button(
            page,
            "CONFIGURE AUDIO FOR THIS PROFILE",
            self.open_audio_setup,
        )

        self._action_button(
            page,
            "CONFIGURE VOLUNTEER CONTROLS",
            self.open_capability_setup,
        )

        ttk.Label(
            page,
            text=(
                "v2.1 can profile-back the volunteer MUTE/UNMUTE action using "
                "actual OBS audio inputs discovered from OBS. The production "
                "live level meter remains on its current proven path for now."
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=8,
        )

        # Sermon --------------------------------------------------
        page = self._new_page(
            "sermon"
        )

        self._summary_box(
            page,
            "sermon",
            "Sermon Information",
        )

        self._action_button(
            page,
            "CONFIGURE SERMON SOURCE FOR THIS PROFILE",
            self.open_sermon_source_setup,
        )

        self._action_button(
            page,
            "EDIT SERMON SOURCE TYPE IN SETUP WIZARD",
            self.open_setup_wizard,
        )

        self._action_button(
            page,
            "CONFIGURE VOLUNTEER SERMON CONTROLS",
            self.open_capability_setup,
        )

        ttk.Label(
            page,
            text=(
                "v2.2 supports live profile-backed Manual, Pastor Email, and "
                "Imported File sermon sources. The existing Friday-email workflow "
                "remains the LEGACY fallback, and downstream chapters/lower thirds "
                "continue using the normal sermon_plan.json pipeline."
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=8,
        )

        # Streaming ----------------------------------------------
        page = self._new_page(
            "streaming"
        )

        self._summary_box(
            page,
            "streaming",
            "Recording / Streaming",
        )

        self._action_button(
            page,
            "CONFIGURE VOLUNTEER CONTROLS",
            self.open_capability_setup,
        )

        ttk.Label(
            page,
            text=(
                "Recording and streaming remain separate, manual, human-gated "
                "buttons. Settings never starts either output automatically."
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=8,
        )

        # Automation ---------------------------------------------
        page = self._new_page(
            "automation"
        )

        self._summary_box(
            page,
            "automation",
            "Automation",
        )

        self._action_button(
            page,
            "RUN / EDIT SETUP WIZARD",
            self.open_setup_wizard,
        )

        ttk.Label(
            page,
            text=(
                "Sermon source is now profile-aware. This page remains the "
                "home for Planning sync, YouTube/post-service behavior, startup "
                "helpers, and other optional automation as those pieces are "
                "migrated one at a time."
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=8,
        )

        # Updates -------------------------------------------------
        page = self._new_page(
            "updates"
        )

        self._summary_box(
            page,
            "updates",
            "Application Updates",
        )

        status_frame = ttk.LabelFrame(
            page,
            text="Updater / Automatic Rollback",
            padding=10,
        )

        status_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            status_frame,
            textvariable=self.update_status_var,
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            status_frame,
            textvariable=self.update_detail_var,
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                4,
                0
            ),
        )

        online_frame = ttk.LabelFrame(
            page,
            text="Trusted Online Release Feed",
            padding=10,
        )

        online_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        online_frame.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            online_frame,
            text="Feed URL",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                7
            ),
        )

        ttk.Entry(
            online_frame,
            textvariable=self.update_feed_url_var,
        ).grid(
            row=0,
            column=1,
            columnspan=3,
            sticky="ew",
        )

        ttk.Label(
            online_frame,
            text="Channel",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(
                0,
                7
            ),
            pady=(
                6,
                0
            ),
        )

        ttk.Combobox(
            online_frame,
            textvariable=self.update_channel_var,
            state="readonly",
            values=(
                "stable",
                "beta",
            ),
            width=12,
        ).grid(
            row=1,
            column=1,
            sticky="w",
            pady=(
                6,
                0
            ),
        )

        ttk.Button(
            online_frame,
            text="SAVE FEED",
            command=self.save_online_feed_settings,
        ).grid(
            row=1,
            column=2,
            sticky="ew",
            padx=(
                6,
                3
            ),
            pady=(
                6,
                0
            ),
        )

        ttk.Button(
            online_frame,
            text="CHECK ONLINE",
            command=self.check_online_updates,
        ).grid(
            row=1,
            column=3,
            sticky="ew",
            padx=(
                3,
                0
            ),
            pady=(
                6,
                0
            ),
        )

        ttk.Label(
            online_frame,
            textvariable=self.online_update_status_var,
            wraplength=675,
            justify="left",
        ).grid(
            row=2,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(
                7,
                5
            ),
        )

        online_actions = ttk.Frame(
            online_frame
        )

        online_actions.grid(
            row=3,
            column=0,
            columnspan=4,
            sticky="ew",
        )

        online_actions.columnconfigure(
            0,
            weight=1
        )
        online_actions.columnconfigure(
            1,
            weight=1
        )

        ttk.Button(
            online_actions,
            text="DOWNLOAD + VERIFY",
            command=self.download_online_update,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
        )

        ttk.Button(
            online_actions,
            text="DOWNLOAD + VERIFY + INSTALL",
            command=self.download_and_install_online_update,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

        package_frame = ttk.LabelFrame(
            page,
            text="Local / Downloaded SSS Update Package",
            padding=10,
        )

        package_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        package_frame.columnconfigure(
            0,
            weight=1
        )

        ttk.Entry(
            package_frame,
            textvariable=self.update_package_var,
            state="readonly",
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(
                0,
                7
            ),
        )

        ttk.Button(
            package_frame,
            text="SELECT .SSSUPDATE",
            command=self.select_update_package,
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
        )

        ttk.Button(
            package_frame,
            text="VERIFY PACKAGE",
            command=self.verify_selected_update_package,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=4,
        )

        ttk.Button(
            package_frame,
            text="INSTALL VERIFIED UPDATE",
            command=self.install_selected_update,
        ).grid(
            row=1,
            column=2,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

        package_frame.columnconfigure(
            1,
            weight=1
        )
        package_frame.columnconfigure(
            2,
            weight=1
        )

        rollback_frame = ttk.LabelFrame(
            page,
            text="Rollback",
            padding=10,
        )

        rollback_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        rollback_frame.columnconfigure(
            0,
            weight=1
        )
        rollback_frame.columnconfigure(
            1,
            weight=1
        )

        ttk.Button(
            rollback_frame,
            text="ROLL BACK LAST APPLICATION UPDATE",
            command=self.rollback_last_application_update,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
        )

        ttk.Button(
            rollback_frame,
            text="OPEN UPDATE / ROLLBACK FOLDER",
            command=self.open_update_folder,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

        ttk.Label(
            rollback_frame,
            text=(
                "Before replacing application files, the updater copies the "
                "currently installed Main + Settings + Updater folders into ProgramData. "
                "If the new EXE fails its safe startup health check, the previous "
                "application is restored automatically."
            ),
            wraplength=680,
            justify="left",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                8,
                0
            ),
        )

        ttk.Label(
            page,
            text=(
                "Safety rules: SSS windows must be closed before file replacement. "
                "The updater refuses to run while OBS Recording/Streaming is active "
                "or when OBS is running but its output state cannot be verified. "
                "Online checks/downloads are manual. Installation still uses the "
                "protected updater and never replaces church profiles, Windows Credential "
                "Manager secrets, sermon_plan.json, PTZ settings, recordings, or media."
            ),
            wraplength=710,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                2,
                0
            ),
        )

        # Security ------------------------------------------------
        page = self._new_page(
            "security"
        )

        status_frame = ttk.LabelFrame(
            page,
            text="Local Secrets / Windows Credential Manager",
            padding=10,
        )

        status_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            status_frame,
            textvariable=self.security_status_var,
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            status_frame,
            textvariable=self.security_detail_var,
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                4,
                0
            ),
        )

        obs_frame = ttk.LabelFrame(
            page,
            text="OBS WebSocket Password",
            padding=10,
        )

        obs_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        obs_frame.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            obs_frame,
            text="New / replacement password",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=4,
        )

        obs_entry = ttk.Entry(
            obs_frame,
            textvariable=self.obs_secret_entry_var,
            show="•",
        )

        obs_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Label(
            obs_frame,
            text=(
                "The password field is never populated from the vault. "
                "SSS only reports whether a protected credential exists."
            ),
            wraplength=675,
            justify="left",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                3,
                7
            ),
        )

        credential_buttons = ttk.Frame(
            obs_frame
        )

        credential_buttons.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        for column in range(
            2
        ):
            credential_buttons.columnconfigure(
                column,
                weight=1
            )

        ttk.Button(
            credential_buttons,
            text="SAVE PASSWORD TO WINDOWS CREDENTIAL MANAGER",
            command=self.save_obs_password_to_vault,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
            pady=3,
        )

        ttk.Button(
            credential_buttons,
            text="COPY EXISTING OBS PASSWORD TO VAULT",
            command=self.copy_existing_obs_password_to_vault,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
            pady=3,
        )

        ttk.Button(
            credential_buttons,
            text="TEST VAULTED OBS CONNECTION",
            command=self.test_vaulted_obs_connection,
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
            pady=3,
        )

        ttk.Button(
            credential_buttons,
            text="REMOVE LEGACY LOOSE OBS PASSWORD",
            command=self.remove_loose_obs_password,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
            pady=3,
        )

        ttk.Button(
            credential_buttons,
            text="DELETE VAULTED OBS PASSWORD",
            command=self.delete_vaulted_obs_password_ui,
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
            pady=3,
        )

        ttk.Button(
            credential_buttons,
            text="OPEN WINDOWS CREDENTIAL MANAGER",
            command=self.open_windows_credential_manager,
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
            pady=3,
        )

        oauth_frame = ttk.LabelFrame(
            page,
            text="OAuth / Account Credentials",
            padding=10,
        )

        oauth_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            oauth_frame,
            text=(
                "Gmail OAuth: LEGACY LOCAL FILE in v2.7\n"
                "YouTube OAuth: LEGACY LOCAL FILE in v2.7\n\n"
                "These token formats are refreshable application files. v2.7 does "
                "not move them into Credential Manager because doing so without "
                "updating the Google/YouTube token-refresh path could break login. "
                "They remain local-only and excluded from profiles, diagnostics, "
                "and Recovery snapshots."
            ),
            wraplength=690,
            justify="left",
        ).pack(
            anchor="w"
        )

        ttk.Button(
            page,
            text="REFRESH SECURITY STATUS",
            command=self.refresh_security_status,
        ).pack(
            fill="x"
        )

        ttk.Label(
            page,
            text=(
                "Protected credentials are stored per Windows user/machine and "
                "per SSS church profile ID. Exporting a .sssprofile never exports "
                "the password itself."
            ),
            wraplength=710,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                9,
                0
            ),
        )

        # Diagnostics --------------------------------------------
        page = self._new_page(
            "diagnostics"
        )

        status_frame = ttk.LabelFrame(
            page,
            text="Overall Readiness",
            padding=10,
        )

        status_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            status_frame,
            textvariable=self.diagnostic_overall_var,
            font=(
                "Segoe UI",
                12,
                "bold"
            ),
        ).pack(
            anchor="w"
        )

        ttk.Label(
            status_frame,
            textvariable=self.diagnostic_detail_var,
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                4,
                0
            ),
        )

        results_frame = ttk.LabelFrame(
            page,
            text="Full System Test Results",
            padding=8,
        )

        results_frame.pack(
            fill="both",
            expand=True,
            pady=(
                0,
                10
            ),
        )

        tree_wrapper = ttk.Frame(
            results_frame
        )

        tree_wrapper.pack(
            fill="both",
            expand=True,
        )

        self.diagnostic_tree = ttk.Treeview(
            tree_wrapper,
            columns=(
                "status",
                "check",
                "detail",
            ),
            show="headings",
            height=15,
        )

        self.diagnostic_tree.heading(
            "status",
            text="STATUS"
        )
        self.diagnostic_tree.heading(
            "check",
            text="CHECK"
        )
        self.diagnostic_tree.heading(
            "detail",
            text="DETAIL"
        )

        self.diagnostic_tree.column(
            "status",
            width=75,
            minwidth=70,
            stretch=False,
            anchor="center",
        )
        self.diagnostic_tree.column(
            "check",
            width=145,
            minwidth=120,
            stretch=False,
        )
        self.diagnostic_tree.column(
            "detail",
            width=500,
            minwidth=250,
            stretch=True,
        )

        self.diagnostic_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        tree_scroll = ttk.Scrollbar(
            tree_wrapper,
            orient="vertical",
            command=self.diagnostic_tree.yview,
        )

        tree_scroll.pack(
            side="right",
            fill="y",
        )

        self.diagnostic_tree.configure(
            yscrollcommand=tree_scroll.set
        )

        button_frame = ttk.Frame(
            page
        )

        button_frame.pack(
            fill="x"
        )

        for column in range(
            3
        ):
            button_frame.columnconfigure(
                column,
                weight=1
            )

        self.diagnostic_run_button = ttk.Button(
            button_frame,
            text="RUN FULL SYSTEM TEST",
            command=self.run_full_system_test_async,
        )

        self.diagnostic_run_button.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
        )

        ttk.Button(
            button_frame,
            text="EXPORT DIAGNOSTIC ZIP",
            command=self.export_last_diagnostics,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
        )

        ttk.Button(
            button_frame,
            text="OPEN DIAGNOSTICS FOLDER",
            command=self.open_diagnostics_folder,
        ).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

        ttk.Label(
            page,
            text=(
                "Checks include profile completeness, OBS, active OBS outputs, "
                "Presentation, Camera, Audio, Sermon Source, sermon chapters, "
                "Secrets Vault, recording storage, critical folders, FFmpeg/NVIDIA "
                "tools, lower thirds, and network reachability. FIX means a service-"
                "critical item needs attention; CHECK means review is recommended."
            ),
            wraplength=710,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                9,
                0
            ),
        )

        # Recovery -----------------------------------------------
        page = self._new_page(
            "recovery"
        )

        status_frame = ttk.LabelFrame(
            page,
            text="Backup / Recovery",
            padding=10,
        )

        status_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            status_frame,
            textvariable=self.recovery_status_var,
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            status_frame,
            textvariable=self.recovery_safety_var,
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                4,
                0
            ),
        )

        create_frame = ttk.LabelFrame(
            page,
            text="Create Recovery Point",
            padding=8,
        )

        create_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        create_frame.columnconfigure(
            0,
            weight=1
        )
        create_frame.columnconfigure(
            1,
            weight=1
        )

        ttk.Button(
            create_frame,
            text="CREATE RECOVERY SNAPSHOT",
            command=self.create_manual_recovery_snapshot,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
        )

        ttk.Button(
            create_frame,
            text="SAVE READY SYSTEM AS LAST KNOWN GOOD",
            command=self.save_last_known_good,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

        ttk.Label(
            create_frame,
            text=(
                "Manual Snapshot can be created at any time. Last Known Good "
                "requires the most recent Full System Diagnostics result to be READY."
            ),
            wraplength=690,
            justify="left",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                7,
                0
            ),
        )

        snapshot_frame = ttk.LabelFrame(
            page,
            text="Available Recovery Snapshots",
            padding=8,
        )

        snapshot_frame.pack(
            fill="both",
            expand=True,
            pady=(
                0,
                10
            ),
        )

        tree_wrapper = ttk.Frame(
            snapshot_frame
        )

        tree_wrapper.pack(
            fill="both",
            expand=True,
        )

        self.recovery_tree = ttk.Treeview(
            tree_wrapper,
            columns=(
                "created",
                "type",
                "profile",
                "diagnostic",
                "files",
            ),
            show="headings",
            height=12,
        )

        headings = (
            (
                "created",
                "CREATED",
                175,
            ),
            (
                "type",
                "TYPE",
                115,
            ),
            (
                "profile",
                "PROFILE",
                190,
            ),
            (
                "diagnostic",
                "DIAGNOSTIC",
                95,
            ),
            (
                "files",
                "FILES",
                60,
            ),
        )

        for key, label, width in headings:
            self.recovery_tree.heading(
                key,
                text=label,
            )
            self.recovery_tree.column(
                key,
                width=width,
                minwidth=55,
                stretch=(
                    key
                    ==
                    "profile"
                ),
            )

        self.recovery_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        recovery_scroll = ttk.Scrollbar(
            tree_wrapper,
            orient="vertical",
            command=self.recovery_tree.yview,
        )

        recovery_scroll.pack(
            side="right",
            fill="y",
        )

        self.recovery_tree.configure(
            yscrollcommand=recovery_scroll.set
        )

        action_frame = ttk.Frame(
            page
        )

        action_frame.pack(
            fill="x"
        )

        for column in range(
            4
        ):
            action_frame.columnconfigure(
                column,
                weight=1
            )

        ttk.Button(
            action_frame,
            text="REFRESH LIST",
            command=self.refresh_recovery_snapshots,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                3
            ),
        )

        ttk.Button(
            action_frame,
            text="RESTORE SELECTED",
            command=self.restore_selected_snapshot,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=3,
        )

        ttk.Button(
            action_frame,
            text="RESTORE LAST KNOWN GOOD",
            command=self.restore_last_known_good,
        ).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=3,
        )

        ttk.Button(
            action_frame,
            text="OPEN RECOVERY FOLDER",
            command=self.open_recovery_folder,
        ).grid(
            row=0,
            column=3,
            sticky="ew",
            padx=(
                3,
                0
            ),
        )

        ttk.Label(
            page,
            text=(
                "Restore is explicit and blocked while Recording/Streaming is active. "
                "Before any restore, SSS automatically creates a PRE-RESTORE safety "
                "snapshot. Secrets/OAuth/password/token files and the current weekly "
                "sermon_plan.json are not restored."
            ),
            wraplength=710,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                9,
                0
            ),
        )

        # Event History ------------------------------------------
        page = self._new_page(
            "history"
        )

        summary_frame = ttk.LabelFrame(
            page,
            text="Session / Crash History",
            padding=10,
        )

        summary_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            summary_frame,
            textvariable=self.history_status_var,
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            summary_frame,
            textvariable=self.history_crash_var,
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                4,
                0
            ),
        )

        filter_frame = ttk.Frame(
            page
        )

        filter_frame.pack(
            fill="x",
            pady=(
                0,
                8
            ),
        )

        ttk.Label(
            filter_frame,
            text="Show",
        ).pack(
            side="left",
            padx=(
                0,
                6
            ),
        )

        category_filter = ttk.Combobox(
            filter_frame,
            textvariable=self.history_filter_var,
            state="readonly",
            width=20,
            values=(
                "ALL",
                "SYSTEM",
                "RECOVERY",
                "UPDATES",
                "SECURITY",
                "OBS",
                "RECORDING",
                "STREAMING",
                "PRESENTATION",
                "CAMERA",
                "AUDIO",
                "SCRIPTURE",
                "SERMON",
                "PLANNING",
                "YOUTUBE",
            ),
        )

        category_filter.pack(
            side="left"
        )

        category_filter.bind(
            "<<ComboboxSelected>>",
            lambda event:
                self.render_event_history(),
            add="+",
        )

        ttk.Label(
            filter_frame,
            text="Last 14 days / newest 500 events",
        ).pack(
            side="right"
        )

        history_frame = ttk.LabelFrame(
            page,
            text="Human-Friendly Timeline",
            padding=8,
        )

        history_frame.pack(
            fill="both",
            expand=True,
            pady=(
                0,
                10
            ),
        )

        tree_wrapper = ttk.Frame(
            history_frame
        )

        tree_wrapper.pack(
            fill="both",
            expand=True,
        )

        self.history_tree = ttk.Treeview(
            tree_wrapper,
            columns=(
                "time",
                "category",
                "level",
                "event",
            ),
            show="headings",
            height=15,
        )

        headings = (
            (
                "time",
                "TIME",
                155,
            ),
            (
                "category",
                "CATEGORY",
                105,
            ),
            (
                "level",
                "TYPE",
                80,
            ),
            (
                "event",
                "EVENT",
                430,
            ),
        )

        for key, label, width in headings:
            self.history_tree.heading(
                key,
                text=label,
            )

            self.history_tree.column(
                key,
                width=width,
                minwidth=70,
                stretch=(
                    key
                    ==
                    "event"
                ),
            )

        self.history_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        history_scroll = ttk.Scrollbar(
            tree_wrapper,
            orient="vertical",
            command=self.history_tree.yview,
        )

        history_scroll.pack(
            side="right",
            fill="y",
        )

        self.history_tree.configure(
            yscrollcommand=history_scroll.set
        )

        buttons = ttk.Frame(
            page
        )

        buttons.pack(
            fill="x"
        )

        for column in range(
            3
        ):
            buttons.columnconfigure(
                column,
                weight=1
            )

        ttk.Button(
            buttons,
            text="REFRESH HISTORY",
            command=self.refresh_event_history,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
        )

        ttk.Button(
            buttons,
            text="EXPORT HISTORY TXT",
            command=self.export_event_history,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
        )

        ttk.Button(
            buttons,
            text="OPEN EVENT HISTORY FOLDER",
            command=self.open_event_history_folder,
        ).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

        ttk.Label(
            page,
            text=(
                "This timeline is separate from raw troubleshooting logs. It records "
                "human-readable actions and warnings such as Recording START/STOP, "
                "Stream START/STOP, Scripture actions, camera changes, audio mute "
                "actions, sermon/chapter preparation, diagnostics, recovery, and "
                "normal/unexpected SSS sessions."
            ),
            wraplength=710,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                9,
                0
            ),
        )

        # Advanced -----------------------------------------------
        page = self._new_page(
            "advanced"
        )

        self._summary_box(
            page,
            "advanced",
            "Advanced / Compatibility",
        )

        packaging_frame = ttk.LabelFrame(
            page,
            text="Windows Application / Installer",
            padding=10,
        )

        packaging_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            packaging_frame,
            textvariable=self.runtime_status_var,
            wraplength=690,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                0,
                8
            ),
        )

        ttk.Button(
            packaging_frame,
            text="OPEN APPLICATION INSTALL FOLDER",
            command=self.open_application_install_folder,
        ).pack(
            fill="x"
        )

        ttk.Button(
            packaging_frame,
            text="REFRESH RELEASE SIGNING STATUS",
            command=self.refresh_runtime_status,
        ).pack(
            fill="x",
            pady=(
                5,
                0
            ),
        )

        ttk.Label(
            packaging_frame,
            text=(
                "Installed EXE mode uses the same church profiles, protected "
                "credentials, diagnostics, and recovery data as Python compatibility "
                "mode. Recording and Streaming remain separate manual controls."
            ),
            wraplength=690,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                7,
                0
            ),
        )

        migration_frame = ttk.LabelFrame(
            page,
            text="Profile Format / Versioned Upgrades",
            padding=10,
        )

        migration_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            migration_frame,
            textvariable=self.migration_status_var,
            wraplength=690,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                0,
                8
            ),
        )

        migration_buttons = ttk.Frame(
            migration_frame
        )

        migration_buttons.pack(
            fill="x"
        )

        for column in range(
            3
        ):
            migration_buttons.columnconfigure(
                column,
                weight=1
            )

        ttk.Button(
            migration_buttons,
            text="CHECK PROFILE SCHEMAS",
            command=self.refresh_profile_migration_status,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
        )

        ttk.Button(
            migration_buttons,
            text="MIGRATE ALL INSTALLED PROFILES",
            command=self.migrate_all_profiles_ui,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
        )

        ttk.Button(
            migration_buttons,
            text="OPEN MIGRATION BACKUPS",
            command=self.open_migration_backups,
        ).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

        ttk.Label(
            migration_frame,
            text=(
                "The active profile upgrades automatically when SSS opens. "
                "Each old profile file is copied to Migration Backups before "
                "an automatic rewrite. Migration adds missing structure only "
                "and never changes a LEGACY integration to PROFILE."
            ),
            wraplength=690,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                8,
                0
            ),
        )

        self._action_button(
            page,
            "CONFIGURE VOLUNTEER CONTROLS",
            self.open_capability_setup,
        )

        self._action_button(
            page,
            "OPEN PROFILE FOLDER",
            self.open_folder,
        )

        self._action_button(
            page,
            "EXPORT ACTIVE PROFILE",
            self.export_profile,
        )

        ttk.Label(
            page,
            text=(
                "Advanced remains the safe place for compatibility and migration "
                "controls. Profiles created by a newer unsupported SSS schema are "
                "refused without modification instead of being guessed at. Secrets, "
                "OAuth tokens, OBS passwords, and machine-specific credentials "
                "remain outside portable profile exports."
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w",
            pady=8,
        )

    def show_page(
        self,
        key
    ):
        if key not in self.pages:
            key = "church"

        self.active_page = key

        titles = {
            "church": (
                "Church",
                "Profile identity, first-run setup, import/export, and profile management.",
            ),
            "obs": (
                "OBS",
                "Scene discovery, profile mappings, and Legacy/Profile fallback.",
            ),
            "presentation": (
                "Presentation",
                "Choose and configure the presentation-software adapter.",
            ),
            "camera": (
                "Camera",
                "Profile-backed camera adapter, PTZ connection, presets, and Legacy fallback.",
            ),
            "audio": (
                "Audio",
                "Profile-backed OBS audio mute targets plus the existing live meter.",
            ),
            "sermon": (
                "Sermon",
                "Profile-backed sermon source, Scripture workflow, chapters, lower thirds, and related automation.",
            ),
            "streaming": (
                "Streaming",
                "Manual recording/streaming capability and future output configuration.",
            ),
            "automation": (
                "Automation",
                "Optional background workflows and post-service processing.",
            ),
            "updates": (
                "Updates",
                "Pinned-signer HTTPS release feed, verified downloads, installation, and automatic rollback.",
            ),
            "security": (
                "Security",
                "Windows Credential Manager, local protected secrets, and OAuth storage status.",
            ),
            "diagnostics": (
                "Diagnostics",
                "One read-only readiness test across SSS integrations, storage, and support tools.",
            ),
            "recovery": (
                "Recovery",
                "Recovery snapshots, Last Known Good, and guarded rollback.",
            ),
            "history": (
                "Event History",
                "Human-friendly service timeline and unexpected-shutdown history.",
            ),
            "advanced": (
                "Advanced",
                "Compatibility, recovery, profile files, and migration controls.",
            ),
        }

        title, subtitle = titles[
            key
        ]

        self.page_title_var.set(
            title
        )

        self.page_subtitle_var.set(
            subtitle
        )

        self.pages[
            key
        ].tkraise()

        if key == "recovery":
            try:
                self.refresh_recovery_snapshots()
            except Exception:
                pass

        elif key == "history":
            try:
                self.refresh_event_history()
            except Exception:
                pass

        elif key == "advanced":
            try:
                self.refresh_runtime_status()
            except Exception:
                pass

            try:
                self.refresh_profile_migration_status()
            except Exception:
                pass

        elif key == "security":
            try:
                self.refresh_security_status()
            except Exception:
                pass

        elif key == "updates":
            try:
                self.refresh_update_status()
            except Exception:
                pass

    def _set_online_update_status(
        self,
        text
    ):
        try:
            self.root.after(
                0,
                lambda:
                    self.online_update_status_var.set(
                        str(
                            text
                        )
                    ),
            )
        except Exception:
            pass

    def _finish_online_worker(
        self
    ):
        self.online_busy = False

    def _start_online_worker(
        self,
        target
    ):
        if self.online_busy:
            messagebox.showinfo(
                "SSS Online Updates",
                "An online update check/download is already running.",
                parent=self.root,
            )
            return False

        self.online_busy = True

        threading.Thread(
            target=target,
            daemon=True,
        ).start()

        return True

    def save_online_feed_settings(
        self
    ):
        try:
            feed_url = str(
                self.update_feed_url_var.get()
                or
                ""
            ).strip()

            channel = str(
                self.update_channel_var.get()
                or
                "stable"
            ).strip().lower()

            config = save_feed_config(
                feed_url=feed_url,
                channel=channel,
                enabled=bool(
                    feed_url
                ),
            )

            self.online_release = None

            if config.get(
                "enabled"
            ):
                self.online_update_status_var.set(
                    (
                        "Feed saved. Click CHECK ONLINE to verify the signed "
                        "release feed."
                    )
                )
            else:
                self.online_update_status_var.set(
                    "Online update feed disabled."
                )

            self.refresh_update_status()

        except Exception as exc:
            messagebox.showwarning(
                "SSS Online Updates",
                str(
                    exc
                ),
                parent=self.root,
            )

    def check_online_updates(
        self
    ):
        try:
            feed_url = str(
                self.update_feed_url_var.get()
                or
                ""
            ).strip()

            if not feed_url:
                raise RuntimeError(
                    "Enter an HTTPS release feed URL first."
                )

            save_feed_config(
                feed_url=feed_url,
                channel=str(
                    self.update_channel_var.get()
                    or
                    "stable"
                ),
                enabled=True,
            )

            self.online_release = None

        except Exception as exc:
            messagebox.showwarning(
                "SSS Online Updates",
                str(
                    exc
                ),
                parent=self.root,
            )
            return

        def worker():
            try:
                self._set_online_update_status(
                    "Downloading and verifying signed release feed…"
                )

                info = runtime_info()

                result = check_release_feed(
                    current_version=str(
                        info.get(
                            "version",
                            ""
                        )
                    )
                )

                release = result.get(
                    "latest_release"
                )

                self.online_release = release

                if not release:
                    text = (
                        "Signed feed verified, but it contains no release for "
                        "the selected channel."
                    )

                elif result.get(
                    "client_too_old"
                ):
                    text = (
                        "SIGNED FEED VERIFIED — latest release "
                        +
                        str(
                            release.get(
                                "version",
                                ""
                            )
                        )
                        +
                        " requires update client "
                        +
                        str(
                            release.get(
                                "minimum_update_client_version",
                                ""
                            )
                        )
                        +
                        " or newer. Use a newer installer/update client first."
                    )

                elif result.get(
                    "update_available"
                ):
                    text = (
                        "UPDATE AVAILABLE — SSS "
                        +
                        str(
                            release.get(
                                "version",
                                ""
                            )
                        )
                        +
                        " | Signed feed verified | Package "
                        +
                        (
                            "{:.1f} MB".format(
                                float(
                                    release.get(
                                        "package_size",
                                        0
                                    )
                                )
                                /
                                (
                                    1024
                                    *
                                    1024
                                )
                            )
                        )
                    )

                    notes = str(
                        release.get(
                            "summary",
                            ""
                        )
                        or
                        ""
                    ).strip()

                    if notes:
                        text += (
                            "\n"
                            +
                            notes
                        )

                else:
                    text = (
                        "UP TO DATE — signed feed verified. Latest "
                        +
                        str(
                            release.get(
                                "version",
                                ""
                            )
                        )
                        +
                        ", current "
                        +
                        str(
                            info.get(
                                "version",
                                ""
                            )
                        )
                        +
                        "."
                    )

                self._set_online_update_status(
                    text
                )

            except Exception as exc:
                self.online_release = None

                self._set_online_update_status(
                    (
                        "ONLINE UPDATE CHECK FAILED — "
                        +
                        str(
                            exc
                        )
                    )
                )

                self.root.after(
                    0,
                    lambda e=str(exc):
                        messagebox.showwarning(
                            "SSS Online Update Check",
                            e,
                            parent=self.root,
                        ),
                )

            finally:
                self.root.after(
                    0,
                    self._finish_online_worker,
                )

        self._start_online_worker(
            worker
        )

    def _online_download_worker(
        self,
        *,
        install_after=False
    ):
        try:
            info = runtime_info()

            release = self.online_release

            if not release:
                self._set_online_update_status(
                    "Checking signed release feed before download…"
                )

                result = check_release_feed(
                    current_version=str(
                        info.get(
                            "version",
                            ""
                        )
                    )
                )

                release = result.get(
                    "latest_release"
                )

                self.online_release = release

                if result.get(
                    "client_too_old"
                ):
                    raise RuntimeError(
                        (
                            "The newest signed release requires update client "
                            +
                            str(
                                release.get(
                                    "minimum_update_client_version",
                                    ""
                                )
                            )
                            +
                            " or newer. Use the full installer or a newer updater first."
                        )
                    )

                if not result.get(
                    "update_available"
                ):
                    if release:
                        raise RuntimeError(
                            (
                                "No newer update is available. Latest signed "
                                "release is "
                                +
                                str(
                                    release.get(
                                        "version",
                                        ""
                                    )
                                )
                                +
                                "."
                            )
                        )

                    raise RuntimeError(
                        "The signed feed contains no release for this channel."
                    )

            if not version_is_newer(
                str(
                    release.get(
                        "version",
                        ""
                    )
                ),
                str(
                    info.get(
                        "version",
                        ""
                    )
                ),
            ):
                raise RuntimeError(
                    "The online release is not newer than the current SSS build."
                )

            self._set_online_update_status(
                (
                    "Downloading SSS "
                    +
                    str(
                        release.get(
                            "version",
                            ""
                        )
                    )
                    +
                    "…"
                )
            )

            def progress(
                received,
                total
            ):
                if total:
                    percent = (
                        float(
                            received
                        )
                        /
                        float(
                            total
                        )
                        *
                        100.0
                    )

                    self._set_online_update_status(
                        (
                            "Downloading SSS "
                            +
                            str(
                                release.get(
                                    "version",
                                    ""
                                )
                            )
                            +
                            " — "
                            +
                            "{:.0f}%".format(
                                percent
                            )
                            +
                            " ("
                            +
                            "{:.1f}".format(
                                float(
                                    received
                                )
                                /
                                (
                                    1024
                                    *
                                    1024
                                )
                            )
                            +
                            " / "
                            +
                            "{:.1f}".format(
                                float(
                                    total
                                )
                                /
                                (
                                    1024
                                    *
                                    1024
                                )
                            )
                            +
                            " MB)"
                        )
                    )

            downloaded = download_release_package(
                release,
                progress=progress,
            )

            path = str(
                downloaded.get(
                    "path",
                    ""
                )
            )

            manifest = downloaded.get(
                "manifest"
            )

            self.selected_update_manifest = manifest

            def finished():
                self.update_package_var.set(
                    path
                )

                self.online_update_status_var.set(
                    (
                        "DOWNLOADED + VERIFIED — SSS "
                        +
                        str(
                            release.get(
                                "version",
                                ""
                            )
                        )
                        +
                        "\nSigned feed, package SHA-256, signed package manifest, "
                        "and Authenticode payload checks all passed."
                    )
                )

                self._finish_online_worker()

                if install_after:
                    self.install_selected_update()

            self.root.after(
                0,
                finished,
            )

        except Exception as exc:
            self._set_online_update_status(
                (
                    "ONLINE UPDATE DOWNLOAD FAILED — "
                    +
                    str(
                        exc
                    )
                )
            )

            self.root.after(
                0,
                lambda e=str(exc):
                    messagebox.showwarning(
                        "SSS Online Update",
                        e,
                        parent=self.root,
                    ),
            )

            self.root.after(
                0,
                self._finish_online_worker,
            )

    def download_online_update(
        self
    ):
        try:
            feed_url = str(
                self.update_feed_url_var.get()
                or
                ""
            ).strip()

            if not feed_url:
                raise RuntimeError(
                    "Enter an HTTPS release feed URL first."
                )

            save_feed_config(
                feed_url=feed_url,
                channel=str(
                    self.update_channel_var.get()
                    or
                    "stable"
                ),
                enabled=True,
            )

            self.online_release = None

        except Exception as exc:
            messagebox.showwarning(
                "SSS Online Updates",
                str(
                    exc
                ),
                parent=self.root,
            )
            return

        self._start_online_worker(
            lambda:
                self._online_download_worker(
                    install_after=False
                )
        )

    def download_and_install_online_update(
        self
    ):
        try:
            feed_url = str(
                self.update_feed_url_var.get()
                or
                ""
            ).strip()

            if not feed_url:
                raise RuntimeError(
                    "Enter an HTTPS release feed URL first."
                )

            save_feed_config(
                feed_url=feed_url,
                channel=str(
                    self.update_channel_var.get()
                    or
                    "stable"
                ),
                enabled=True,
            )

            self.online_release = None

            info = runtime_info()

            if not info.get(
                "frozen"
            ):
                raise RuntimeError(
                    (
                        "Online installation requires Installed Windows EXE mode. "
                        "The signed feed can still be checked and downloaded in "
                        "Python compatibility mode."
                    )
                )

            approved = messagebox.askyesno(
                "Download and Install SSS Update",
                (
                    "Check the trusted HTTPS release feed, download the newest "
                    "signed update, verify every trust layer, and then continue "
                    "to the normal protected installation confirmation?\n\n"
                    "Nothing will install if any feed signature, package hash, "
                    "manifest signature, signer pin, or Authenticode check fails.\n\n"
                    "Recording and Streaming are still checked again immediately "
                    "before installation."
                ),
                parent=self.root,
            )

            if not approved:
                return

            self._start_online_worker(
                lambda:
                    self._online_download_worker(
                        install_after=True
                    )
            )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Online Update",
                str(
                    exc
                ),
                parent=self.root,
            )

    def refresh_update_status(
        self
    ):
        try:
            info = runtime_info()
            install_root = application_install_root()

            feed_status = online_update_status()
            feed_config = feed_status.get(
                "config",
                {}
            )
            feed_state = feed_status.get(
                "state",
                {}
            )

            self.update_feed_url_var.set(
                str(
                    feed_config.get(
                        "feed_url",
                        ""
                    )
                )
            )

            self.update_channel_var.set(
                str(
                    feed_config.get(
                        "channel",
                        "stable"
                    )
                    or
                    "stable"
                )
            )

            if feed_state.get(
                "last_checked_at"
            ):
                if feed_state.get(
                    "update_available"
                ):
                    self.online_update_status_var.set(
                        (
                            "Last signed-feed check found SSS "
                            +
                            str(
                                feed_state.get(
                                    "latest_version",
                                    ""
                                )
                            )
                            +
                            " available."
                        )
                    )
                else:
                    self.online_update_status_var.set(
                        (
                            "Last signed-feed check: no newer release was available."
                        )
                    )
            elif feed_config.get(
                "enabled"
            ):
                self.online_update_status_var.set(
                    "Online feed configured. Click CHECK ONLINE."
                )
            else:
                self.online_update_status_var.set(
                    "Online feed is not configured."
                )

            status = update_status(
                install_root=install_root
            )

            state = status.get(
                "state",
                {}
            )

            runtime_mode = str(
                info.get(
                    "mode",
                    ""
                )
            )

            last_status = str(
                state.get(
                    "status",
                    "NONE"
                )
                or
                "NONE"
            )

            self.update_status_var.set(
                (
                    "Current SSS: "
                    +
                    str(
                        info.get(
                            "version",
                            ""
                        )
                    )
                    +
                    " | "
                    +
                    runtime_mode
                    +
                    " | Last update state: "
                    +
                    last_status
                )
            )

            details = []

            if state:
                details.append(
                    (
                        "Last operation: "
                        +
                        str(
                            state.get(
                                "operation",
                                "update"
                            )
                        )
                        +
                        " | "
                        +
                        str(
                            state.get(
                                "from_version",
                                "?"
                            )
                        )
                        +
                        " -> "
                        +
                        str(
                            state.get(
                                "to_version",
                                "?"
                            )
                        )
                    )
                )

                if state.get(
                    "detail"
                ):
                    details.append(
                        str(
                            state.get(
                                "detail"
                            )
                        )
                    )

            if status.get(
                "rollback_available"
            ):
                details.append(
                    "Rollback backup: READY"
                )
            else:
                details.append(
                    "Rollback backup: none recorded"
                )

            if not info.get(
                "frozen"
            ):
                details.append(
                    (
                        "Install/rollback buttons require Installed Windows EXE "
                        "mode. Package verification is still available here."
                    )
                )

            trusted = [
                str(
                    value
                )
                for value in TRUSTED_UPDATE_SIGNER_THUMBPRINTS
                if str(
                    value
                )
            ]

            details.append(
                (
                    "Signed update manifests required: "
                    +
                    (
                        "YES"
                        if SIGNED_UPDATES_REQUIRED
                        else
                        "NO"
                    )
                )
            )

            details.append(
                (
                    "Trusted update signer(s): "
                    +
                    (
                        ", ".join(
                            trusted
                        )
                        if trusted
                        else
                        "NONE COMPILED — signed updates cannot be installed"
                    )
                )
            )

            details.append(
                (
                    "Update package sources: trusted signed HTTPS feed or local "
                    "signed .sssupdate file."
                )
            )

            self.update_detail_var.set(
                "\n".join(
                    details
                )
            )

            details.append(
                (
                    "Online feed: "
                    +
                    (
                        "CONFIGURED / "
                        +
                        str(
                            feed_config.get(
                                "channel",
                                "stable"
                            )
                        ).upper()
                        if feed_config.get(
                            "enabled"
                        )
                        else
                        "NOT CONFIGURED"
                    )
                )
            )

            self.summary_vars[
                "updates"
            ].set(
                (
                    "Version: "
                    +
                    str(
                        info.get(
                            "version",
                            ""
                        )
                    )
                    +
                    "\nRuntime: "
                    +
                    runtime_mode
                    +
                    "\nRollback available: "
                    +
                    (
                        "YES"
                        if status.get(
                            "rollback_available"
                        )
                        else
                        "NO"
                    )
                    +
                    "\nOnline feed: "
                    +
                    (
                        "CONFIGURED"
                        if feed_config.get(
                            "enabled"
                        )
                        else
                        "NOT CONFIGURED"
                    )
                )
            )

        except Exception as exc:
            self.update_status_var.set(
                "Update status failed: "
                +
                str(
                    exc
                )
            )

    def select_update_package(
        self
    ):
        path = filedialog.askopenfilename(
            title="Select Sunday Service System Update",
            filetypes=(
                (
                    "Sunday Service System Update",
                    "*.sssupdate",
                ),
                (
                    "All files",
                    "*.*",
                ),
            ),
            parent=self.root,
        )

        if not path:
            return

        self.update_package_var.set(
            path
        )

        self.selected_update_manifest = None

        self.update_detail_var.set(
            (
                "Selected update package. Click VERIFY PACKAGE before installing."
            )
        )

    def verify_selected_update_package(
        self
    ):
        path = str(
            self.update_package_var.get()
            or
            ""
        ).strip()

        if not path:
            messagebox.showinfo(
                "SSS Updates",
                "Select a .sssupdate package first.",
                parent=self.root,
            )
            return

        try:
            manifest = verify_update_package(
                path
            )

            self.selected_update_manifest = manifest

            info = runtime_info()

            candidate = str(
                manifest.get(
                    "version",
                    ""
                )
            )

            current = str(
                info.get(
                    "version",
                    ""
                )
            )

            newer = version_is_newer(
                candidate,
                current
            )

            self.update_detail_var.set(
                (
                    "VERIFIED — package "
                    +
                    candidate
                    +
                    " | "
                    +
                    str(
                        len(
                            manifest.get(
                                "files",
                                []
                            )
                        )
                    )
                    +
                    " file(s) passed SHA-256/size checks."
                    +
                    (
                        "\nPackage is newer than the current installed build."
                        if newer
                        else
                        "\nPackage is NOT newer than the current build and will not be installed normally."
                    )
                    +
                    "\nPackage signature: "
                    +
                    (
                        "SIGNED / TRUSTED"
                        if manifest.get(
                            "signed"
                        )
                        else
                        "UNSIGNED"
                    )
                    +
                    (
                        "\nSigner: "
                        +
                        str(
                            manifest.get(
                                "signer_thumbprint",
                                ""
                            )
                        )
                        if manifest.get(
                            "signed"
                        )
                        else
                        ""
                    )
                )
            )

        except Exception as exc:
            self.selected_update_manifest = None

            messagebox.showwarning(
                "Update Package Verification",
                str(
                    exc
                ),
                parent=self.root,
            )

    def _update_install_preflight(
        self
    ):
        info = runtime_info()

        if not info.get(
            "frozen"
        ):
            raise RuntimeError(
                (
                    "Application update installation is enabled only in "
                    "Installed Windows EXE mode. Build/install SSS first."
                )
            )

        install_root = application_install_root()

        blockers = installed_app_processes(
            install_root,
            exclude_pid=os.getpid(),
        )

        if blockers:
            lines = []

            for item in blockers:
                lines.append(
                    (
                        str(
                            item.get(
                                "Name",
                                "SSS process"
                            )
                        )
                        +
                        " (PID "
                        +
                        str(
                            item.get(
                                "ProcessId",
                                "?"
                            )
                        )
                        +
                        ")"
                    )
                )

            raise RuntimeError(
                (
                    "Close the other Sunday Service System window(s) first:\n"
                    +
                    "\n".join(
                        lines
                    )
                    +
                    "\n\nLeave this Settings window open; it will close itself "
                    "after the elevated updater starts."
                )
            )

        safety = restore_safety_status()

        if not safety.get(
            "safe"
        ):
            raise RuntimeError(
                (
                    "Update is blocked for live-service safety.\n\n"
                    +
                    str(
                        safety.get(
                            "detail",
                            ""
                        )
                    )
                )
            )

        return (
            info,
            install_root,
        )

    def install_selected_update(
        self
    ):
        path = str(
            self.update_package_var.get()
            or
            ""
        ).strip()

        if not path:
            messagebox.showinfo(
                "SSS Updates",
                "Select and verify a .sssupdate package first.",
                parent=self.root,
            )
            return

        try:
            manifest = verify_update_package(
                path
            )

            self.selected_update_manifest = manifest

            info, install_root = self._update_install_preflight()

            candidate = str(
                manifest.get(
                    "version",
                    ""
                )
            )

            current = str(
                info.get(
                    "version",
                    ""
                )
            )

            if not version_is_newer(
                candidate,
                current
            ):
                raise RuntimeError(
                    (
                        "Selected package "
                        +
                        candidate
                        +
                        " is not newer than current SSS "
                        +
                        current
                        +
                        "."
                    )
                )

            approved = messagebox.askyesno(
                "Install SSS Update",
                (
                    "Install Sunday Service System "
                    +
                    candidate
                    +
                    "?\n\n"
                    "Current version: "
                    +
                    current
                    +
                    "\n\n"
                    "The updater will:\n"
                    "• create an automatic pre-update application backup\n"
                    "• replace only compiled Main + Settings + Updater application files\n"
                    "• launch the NEW Main EXE in safe health-check mode\n"
                    "• automatically restore the previous application if verification fails\n\n"
                    "Profiles, credentials, sermon plans, PTZ settings, recordings, "
                    "and media are not replaced.\n\n"
                    "This Settings window will close after the updater starts."
                ),
                parent=self.root,
            )

            if not approved:
                return

            launch_updater(
                "--apply",
                path,
                "--install-root",
                str(
                    install_root
                ),
                "--current-version",
                current,
                "--parent-pid",
                str(
                    os.getpid()
                ),
            )

            self.root.after(
                350,
                self.root.destroy,
            )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Update",
                str(
                    exc
                ),
                parent=self.root,
            )

    def rollback_last_application_update(
        self
    ):
        try:
            info, install_root = self._update_install_preflight()

            status = update_status(
                install_root=install_root
            )

            if not status.get(
                "rollback_available"
            ):
                raise RuntimeError(
                    "No last-update rollback backup is available."
                )

            state = status.get(
                "state",
                {}
            )

            approved = messagebox.askyesno(
                "Roll Back SSS Application",
                (
                    "Restore the previous application version from the recorded "
                    "rollback backup?\n\n"
                    "Current build: "
                    +
                    str(
                        info.get(
                            "version",
                            ""
                        )
                    )
                    +
                    "\nRecorded previous version: "
                    +
                    str(
                        state.get(
                            "from_version",
                            "unknown"
                        )
                    )
                    +
                    "\n\nBefore rollback, the updater creates another application "
                    "backup of the current build. Church profiles, credentials, "
                    "sermon plans, PTZ settings, recordings, and media are untouched.\n\n"
                    "This Settings window will close after the updater starts."
                ),
                parent=self.root,
            )

            if not approved:
                return

            launch_updater(
                "--rollback-last",
                "--install-root",
                str(
                    install_root
                ),
                "--parent-pid",
                str(
                    os.getpid()
                ),
            )

            self.root.after(
                350,
                self.root.destroy,
            )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Rollback",
                str(
                    exc
                ),
                parent=self.root,
            )

    def open_update_folder(
        self
    ):
        try:
            UPDATE_ROOT.mkdir(
                parents=True,
                exist_ok=True,
            )

            if os.name == "nt":
                os.startfile(
                    str(
                        UPDATE_ROOT
                    )
                )
            else:
                subprocess.Popen(
                    [
                        "xdg-open",
                        str(
                            UPDATE_ROOT
                        ),
                    ]
                )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Updates",
                str(
                    exc
                ),
                parent=self.root,
            )

    def refresh_security_status(
        self
    ):
        try:
            overview = security_overview()

            vault_text = (
                "AVAILABLE"
                if overview.get(
                    "vault_available"
                )
                else
                "UNAVAILABLE"
            )

            obs_text = (
                "PROTECTED"
                if overview.get(
                    "obs_vault_stored"
                )
                else
                "NOT STORED"
            )

            legacy_text = (
                "YES"
                if overview.get(
                    "legacy_obs_password_present"
                )
                else
                "NO"
            )

            self.security_status_var.set(
                (
                    "Windows Credential Manager: "
                    +
                    vault_text
                    +
                    " | OBS password: "
                    +
                    obs_text
                    +
                    " | Legacy loose OBS password detected: "
                    +
                    legacy_text
                )
            )

            gmail = (
                "present"
                if overview.get(
                    "gmail_oauth_file_present"
                )
                else
                "not detected"
            )

            youtube = (
                "present"
                if overview.get(
                    "youtube_oauth_file_present"
                )
                else
                "not detected"
            )

            self.security_detail_var.set(
                (
                    "Runtime OBS connections prefer the vault whenever a "
                    "protected password exists. If no vault password exists, "
                    "SSS keeps the current legacy connection path. "
                    "Gmail OAuth file: "
                    +
                    gmail
                    +
                    " | YouTube OAuth file: "
                    +
                    youtube
                    +
                    "."
                )
            )

        except Exception as exc:
            self.security_status_var.set(
                "Security status failed: "
                +
                str(
                    exc
                )
            )

    def save_obs_password_to_vault(
        self
    ):
        password = str(
            self.obs_secret_entry_var.get()
            or
            ""
        )

        if not password:
            messagebox.showinfo(
                "SSS Security",
                "Enter the OBS WebSocket password first.",
                parent=self.root,
            )
            return

        try:
            set_obs_vault_password(
                password
            )

            self.obs_secret_entry_var.set(
                ""
            )

            self.refresh_security_status()

            messagebox.showinfo(
                "OBS Password Protected",
                (
                    "The OBS WebSocket password is now stored in Windows "
                    "Credential Manager for this SSS church profile.\n\n"
                    "SSS will prefer the protected credential on future OBS "
                    "connections."
                ),
                parent=self.root,
            )

        except Exception as exc:
            self.obs_secret_entry_var.set(
                ""
            )

            messagebox.showwarning(
                "SSS Security",
                str(
                    exc
                ),
                parent=self.root,
            )

    def copy_existing_obs_password_to_vault(
        self
    ):
        try:
            copy_legacy_obs_password_to_vault()

            self.refresh_security_status()

            messagebox.showinfo(
                "OBS Password Copied",
                (
                    "The existing OBS WebSocket password was copied into "
                    "Windows Credential Manager without displaying it.\n\n"
                    "The legacy copy has NOT been removed yet. Test the vault "
                    "connection first, then use REMOVE LEGACY LOOSE OBS PASSWORD."
                ),
                parent=self.root,
            )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Security",
                str(
                    exc
                ),
                parent=self.root,
            )

    def test_vaulted_obs_connection(
        self
    ):
        try:
            result = test_obs_vault_connection()

            detail = (
                "Vault authentication succeeded at "
                +
                str(
                    result.get(
                        "host",
                        ""
                    )
                )
                +
                ":"
                +
                str(
                    result.get(
                        "port",
                        ""
                    )
                )
            )

            if result.get(
                "obs_version"
            ):
                detail += (
                    "\nOBS: "
                    +
                    str(
                        result.get(
                            "obs_version"
                        )
                    )
                )

            self.refresh_security_status()

            messagebox.showinfo(
                "Vault Connection Test",
                detail,
                parent=self.root,
            )

        except Exception as exc:
            messagebox.showwarning(
                "Vault Connection Test",
                (
                    "The protected OBS connection did not succeed.\n\n"
                    +
                    str(
                        exc
                    )
                    +
                    "\n\nThe test did not change Recording or Streaming."
                ),
                parent=self.root,
            )

    def remove_loose_obs_password(
        self
    ):
        approved = messagebox.askyesno(
            "Remove Legacy OBS Password",
            (
                "Remove the loose OBS_PASSWORD entry after verifying the "
                "Windows Credential Manager copy?\n\n"
                "SSS will first perform a protected OBS connection test. "
                "If that test fails, nothing is removed.\n\n"
                "This only targets OBS_PASSWORD in .env / known SSS config. "
                "It does not touch Gmail or YouTube credentials."
            ),
            parent=self.root,
        )

        if not approved:
            return

        try:
            result = remove_legacy_obs_password(
                require_vault_test=True
            )

            self.refresh_security_status()

            removed = result.get(
                "removed",
                []
            )

            if removed:
                detail = (
                    "Removed:\n\n"
                    +
                    "\n".join(
                        removed
                    )
                )
            else:
                detail = (
                    "Protected connection succeeded, but no known loose "
                    "OBS password entry was found."
                )

            messagebox.showinfo(
                "Legacy OBS Password Cleanup",
                detail,
                parent=self.root,
            )

        except Exception as exc:
            messagebox.showwarning(
                "Legacy OBS Password Cleanup",
                (
                    "Nothing was removed.\n\n"
                    +
                    str(
                        exc
                    )
                ),
                parent=self.root,
            )

    def delete_vaulted_obs_password_ui(
        self
    ):
        overview = security_overview()

        if not overview.get(
            "obs_vault_stored"
        ):
            messagebox.showinfo(
                "SSS Security",
                "No vaulted OBS password is stored for this profile.",
                parent=self.root,
            )
            return

        warning = (
            "Delete the protected OBS password from Windows Credential Manager?\n\n"
        )

        if not overview.get(
            "legacy_obs_password_present"
        ):
            warning += (
                "WARNING: no legacy loose OBS password is currently detected. "
                "Deleting the vault credential may prevent SSS from connecting "
                "to password-protected OBS until another password is saved."
            )
        else:
            warning += (
                "A legacy OBS password is still detected, so SSS can fall back "
                "to the current legacy connection path."
            )

        approved = messagebox.askyesno(
            "Delete Vaulted OBS Password",
            warning,
            parent=self.root,
        )

        if not approved:
            return

        try:
            delete_obs_vault_password()
            self.refresh_security_status()

            messagebox.showinfo(
                "SSS Security",
                "Vaulted OBS password deleted.",
                parent=self.root,
            )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Security",
                str(
                    exc
                ),
                parent=self.root,
            )

    def open_windows_credential_manager(
        self
    ):
        if os.name != "nt":
            messagebox.showinfo(
                "Windows Credential Manager",
                "Windows Credential Manager is only available on Windows.",
                parent=self.root,
            )
            return

        try:
            subprocess.Popen(
                [
                    "control.exe",
                    "/name",
                    "Microsoft.CredentialManager",
                ],
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0
                ),
            )

        except Exception as exc:
            messagebox.showwarning(
                "Windows Credential Manager",
                str(
                    exc
                ),
                parent=self.root,
            )

    def refresh_runtime_status(
        self
    ):
        try:
            info = runtime_info()

            signing = release_signing_status()

            trusted = signing.get(
                "trusted_thumbprints",
                ()
            )

            self.runtime_status_var.set(
                (
                    "Version "
                    +
                    str(
                        info.get(
                            "version",
                            ""
                        )
                    )
                    +
                    " | "
                    +
                    str(
                        info.get(
                            "mode",
                            ""
                        )
                    )
                    +
                    "\nExecutable: "
                    +
                    str(
                        info.get(
                            "executable",
                            ""
                        )
                    )
                    +
                    "\nInstall root: "
                    +
                    str(
                        info.get(
                            "install_root",
                            ""
                        )
                    )
                    +
                    "\nSigned updates required: "
                    +
                    (
                        "YES"
                        if signing.get(
                            "signed_updates_required"
                        )
                        else
                        "NO"
                    )
                    +
                    "\nTrusted release signer(s): "
                    +
                    (
                        ", ".join(
                            trusted
                        )
                        if trusted
                        else
                        "NONE"
                    )
                    +
                    "\nLocal release-signing key: "
                    +
                    (
                        "READY"
                        if signing.get(
                            "local_signing_ready"
                        )
                        else
                        "not available / not configured"
                    )
                )
            )

        except Exception as exc:
            self.runtime_status_var.set(
                "Runtime packaging status failed: "
                +
                str(
                    exc
                )
            )

    def open_application_install_folder(
        self
    ):
        try:
            open_install_folder()

        except Exception as exc:
            messagebox.showwarning(
                "SSS Application Folder",
                str(
                    exc
                ),
                parent=self.root,
            )

    def refresh_profile_migration_status(
        self
    ):
        try:
            items = list_profile_migration_status()

            current = 0
            upgrade = 0
            newer = 0
            errors = 0

            details = []

            for item in items:
                status = str(
                    item.get(
                        "status",
                        "ERROR"
                    )
                ).upper()

                if status == "CURRENT":
                    current += 1
                elif status == "UPGRADE":
                    upgrade += 1
                elif status == "NEWER":
                    newer += 1
                else:
                    errors += 1

                if status != "CURRENT":
                    details.append(
                        (
                            str(
                                item.get(
                                    "profile_name",
                                    "Profile"
                                )
                            )
                            +
                            ": "
                            +
                            status
                            +
                            " — "
                            +
                            str(
                                item.get(
                                    "detail",
                                    ""
                                )
                            )
                        )
                    )

            text = (
                "Current SSS profile schema: "
                +
                str(
                    PROFILE_SCHEMA_VERSION
                )
                +
                " | "
                +
                str(
                    current
                )
                +
                " current"
                +
                " | "
                +
                str(
                    upgrade
                )
                +
                " upgrade available"
                +
                " | "
                +
                str(
                    newer
                )
                +
                " newer/unsupported"
                +
                " | "
                +
                str(
                    errors
                )
                +
                " error(s)"
            )

            if details:
                text += (
                    "\n"
                    +
                    "\n".join(
                        details[
                            :6
                        ]
                    )
                )

            self.migration_status_var.set(
                text
            )

        except Exception as exc:
            self.migration_status_var.set(
                "Profile schema check failed: "
                +
                str(
                    exc
                )
            )

    def migrate_all_profiles_ui(
        self
    ):
        try:
            items = list_profile_migration_status()

            needs_upgrade = [
                item
                for item in items
                if item.get(
                    "needs_migration"
                )
            ]

            if not needs_upgrade:
                self.refresh_profile_migration_status()

                messagebox.showinfo(
                    "Profile Upgrades",
                    (
                        "No installed profile needs migration."
                    ),
                    parent=self.root,
                )
                return

            approved = messagebox.askyesno(
                "Migrate Installed Profiles",
                (
                    "Upgrade "
                    +
                    str(
                        len(
                            needs_upgrade
                        )
                    )
                    +
                    " installed profile(s) to schema "
                    +
                    str(
                        PROFILE_SCHEMA_VERSION
                    )
                    +
                    "?\n\nEach old profile is backed up before it is rewritten. "
                    "LEGACY integrations remain LEGACY."
                ),
                parent=self.root,
            )

            if not approved:
                return

            results = migrate_all_installed_profiles()

            migrated = [
                item
                for item in results
                if item.get(
                    "status"
                )
                ==
                "MIGRATED"
            ]

            problems = [
                item
                for item in results
                if item.get(
                    "status"
                )
                in {
                    "ERROR",
                    "NEWER",
                }
            ]

            self.refresh_profile_migration_status()
            self.refresh()

            detail = (
                str(
                    len(
                        migrated
                    )
                )
                +
                " profile(s) migrated."
            )

            if problems:
                detail += (
                    "\n\n"
                    +
                    str(
                        len(
                            problems
                        )
                    )
                    +
                    " profile(s) were not changed because they need review."
                )

            messagebox.showinfo(
                "Profile Upgrades",
                detail,
                parent=self.root,
            )

        except Exception as exc:
            messagebox.showwarning(
                "Profile Upgrades",
                str(
                    exc
                ),
                parent=self.root,
            )

    def open_migration_backups(
        self
    ):
        try:
            folder = migration_backups_dir()

            if os.name == "nt":
                os.startfile(
                    str(
                        folder
                    )
                )
            else:
                subprocess.Popen(
                    [
                        "xdg-open",
                        str(
                            folder
                        ),
                    ]
                )

        except Exception as exc:
            messagebox.showwarning(
                "Profile Migration Backups",
                str(
                    exc
                ),
                parent=self.root,
            )

    def refresh_event_history(
        self
    ):
        try:
            self.history_events = read_recent_events(
                limit=500,
                days=14,
            )

            self.history_status_var.set(
                (
                    str(
                        len(
                            self.history_events
                        )
                    )
                    +
                    " recent event(s) loaded."
                )
            )

            crash = get_last_unexpected_shutdown()

            if crash:
                recording = crash.get(
                    "recording"
                )

                streaming = crash.get(
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

                self.history_crash_var.set(
                    (
                        "Last unexpected shutdown detected "
                        +
                        str(
                            crash.get(
                                "detected_at",
                                ""
                            )
                        )
                        +
                        " | previous heartbeat "
                        +
                        str(
                            crash.get(
                                "heartbeat_at",
                                ""
                            )
                        )
                        +
                        " | Recording: "
                        +
                        state_text(
                            recording
                        )
                        +
                        " | Streaming: "
                        +
                        state_text(
                            streaming
                        )
                        +
                        " | Last event: "
                        +
                        str(
                            crash.get(
                                "last_event",
                                "(none)"
                            )
                        )
                    )
                )

            else:
                self.history_crash_var.set(
                    "No unexpected SSS shutdown has been recorded."
                )

            self.render_event_history()

        except Exception as exc:
            self.history_status_var.set(
                "Could not load Event History: "
                +
                str(
                    exc
                )
            )

    def render_event_history(
        self
    ):
        if self.history_tree is None:
            return

        try:
            for item in self.history_tree.get_children():
                self.history_tree.delete(
                    item
                )
        except Exception:
            pass

        selected_category = str(
            self.history_filter_var.get()
            or
            "ALL"
        ).upper()

        shown = 0

        for event in self.history_events:
            category = str(
                event.get(
                    "category",
                    "SYSTEM"
                )
            ).upper()

            if (
                selected_category
                !=
                "ALL"
                and
                category
                !=
                selected_category
            ):
                continue

            try:
                self.history_tree.insert(
                    "",
                    "end",
                    values=(
                        format_event_time(
                            event.get(
                                "timestamp",
                                ""
                            )
                        ),
                        category,
                        event.get(
                            "level",
                            "INFO"
                        ),
                        event.get(
                            "message",
                            ""
                        ),
                    ),
                )

                shown += 1

            except Exception:
                pass

        self.history_status_var.set(
            (
                str(
                    shown
                )
                +
                " event(s) shown"
                +
                (
                    " — filter: "
                    +
                    selected_category
                    if selected_category
                    !=
                    "ALL"
                    else
                    ""
                )
            )
        )

    def export_event_history(
        self
    ):
        try:
            path = export_event_history_text(
                limit=1500,
                days=30,
            )

            messagebox.showinfo(
                "Event History Exported",
                (
                    "Created:\n\n"
                    +
                    str(
                        path
                    )
                ),
                parent=self.root,
            )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Event History",
                str(
                    exc
                ),
                parent=self.root,
            )

    def open_event_history_folder(
        self
    ):
        try:
            EVENT_ROOT.mkdir(
                parents=True,
                exist_ok=True,
            )

            if os.name == "nt":
                os.startfile(
                    str(
                        EVENT_ROOT
                    )
                )
            else:
                subprocess.Popen(
                    [
                        "xdg-open",
                        str(
                            EVENT_ROOT
                        ),
                    ]
                )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Event History",
                str(
                    exc
                ),
                parent=self.root,
            )

    def refresh_recovery_snapshots(
        self
    ):
        if self.recovery_tree is None:
            return

        try:
            safety = restore_safety_status()

            self.recovery_safety_var.set(
                (
                    "Restore safety: "
                    +
                    (
                        "READY — "
                        if safety.get(
                            "safe"
                        )
                        else
                        "BLOCKED — "
                    )
                    +
                    str(
                        safety.get(
                            "detail",
                            ""
                        )
                    )
                )
            )

        except Exception as exc:
            self.recovery_safety_var.set(
                "Restore safety check failed: "
                +
                str(
                    exc
                )
            )

        try:
            for item in self.recovery_tree.get_children():
                self.recovery_tree.delete(
                    item
                )
        except Exception:
            pass

        self.recovery_item_paths = {}

        try:
            snapshots = list_recovery_snapshots()

            known_good = last_known_good_snapshot()
            known_good_name = (
                known_good.name
                if known_good is not None
                else
                ""
            )

            if known_good_name:
                self.recovery_status_var.set(
                    (
                        "Last Known Good: "
                        +
                        known_good_name
                        +
                        " — "
                        +
                        str(
                            len(
                                snapshots
                            )
                        )
                        +
                        " snapshot(s) available"
                    )
                )
            else:
                self.recovery_status_var.set(
                    (
                        "No Last Known Good is saved yet — "
                        +
                        str(
                            len(
                                snapshots
                            )
                        )
                        +
                        " snapshot(s) available"
                    )
                )

            for index, snapshot in enumerate(
                snapshots
            ):
                path = snapshot.get(
                    "path"
                )

                item_id = (
                    "snapshot_"
                    +
                    str(
                        index
                    )
                )

                kind = str(
                    snapshot.get(
                        "kind",
                        "manual"
                    )
                ).replace(
                    "_",
                    " "
                ).upper()

                if (
                    path is not None
                    and
                    path.name
                    ==
                    known_good_name
                ):
                    kind = "LAST KNOWN GOOD"

                created = str(
                    snapshot.get(
                        "created_at",
                        ""
                    )
                )

                if "T" in created:
                    created = created.replace(
                        "T",
                        " "
                    )[:19]

                self.recovery_tree.insert(
                    "",
                    "end",
                    iid=item_id,
                    values=(
                        created,
                        kind,
                        snapshot.get(
                            "profile_name",
                            ""
                        ),
                        snapshot.get(
                            "diagnostic_overall",
                            ""
                        ),
                        snapshot.get(
                            "file_count",
                            0
                        ),
                    ),
                )

                if path is not None:
                    self.recovery_item_paths[
                        item_id
                    ] = path

        except Exception as exc:
            self.recovery_status_var.set(
                "Could not load recovery snapshots: "
                +
                str(
                    exc
                )
            )

    def create_manual_recovery_snapshot(
        self
    ):
        try:
            path = create_recovery_snapshot(
                kind="manual",
                label="settings",
                diagnostic_report=self.diagnostic_report,
            )

            self.refresh_recovery_snapshots()

            messagebox.showinfo(
                "Recovery Snapshot Created",
                (
                    "Created:\n\n"
                    +
                    str(
                        path
                    )
                    +
                    "\n\nSecrets and transient sermon/runtime state were excluded."
                ),
                parent=self.root,
            )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Recovery",
                str(
                    exc
                ),
                parent=self.root,
            )

    def save_last_known_good(
        self
    ):
        try:
            path = create_recovery_snapshot(
                kind="last_known_good",
                label="ready",
                diagnostic_report=self.diagnostic_report,
                require_ready=True,
            )

            self.refresh_recovery_snapshots()

            messagebox.showinfo(
                "Last Known Good Saved",
                (
                    "Current READY system saved as Last Known Good:\n\n"
                    +
                    str(
                        path
                    )
                ),
                parent=self.root,
            )

        except Exception as exc:
            messagebox.showwarning(
                "Last Known Good",
                str(
                    exc
                ),
                parent=self.root,
            )

    def _confirm_and_restore(
        self,
        snapshot_path
    ):
        if snapshot_path is None:
            messagebox.showinfo(
                "SSS Recovery",
                "No recovery snapshot is selected.",
                parent=self.root,
            )
            return

        safety = restore_safety_status()

        if not safety.get(
            "safe"
        ):
            messagebox.showwarning(
                "Restore Blocked",
                str(
                    safety.get(
                        "detail",
                        "Restore is not safe right now."
                    )
                ),
                parent=self.root,
            )
            return

        approved = messagebox.askyesno(
            "Restore SSS Recovery Snapshot",
            (
                "Restore this snapshot?\n\n"
                +
                str(
                    snapshot_path
                )
                +
                "\n\nBefore restoring, SSS will automatically create a "
                "PRE-RESTORE snapshot of the current system.\n\n"
                "Secrets and the current weekly sermon_plan.json will not be "
                "replaced.\n\n"
                "SSS must be restarted after restore."
            ),
            parent=self.root,
        )

        if not approved:
            return

        try:
            result = restore_recovery_snapshot(
                snapshot_path,
                create_pre_restore=True,
            )

            pre_restore = result.get(
                "pre_restore_snapshot"
            )

            messagebox.showinfo(
                "SSS Restore Complete",
                (
                    "Recovery snapshot restored successfully.\n\n"
                    "Automatic pre-restore backup:\n"
                    +
                    str(
                        pre_restore
                    )
                    +
                    "\n\nClose and restart Sunday Service System before using it."
                ),
                parent=self.root,
            )

            # The running Settings process may now be executing code from a
            # newer version than the restored files on disk. Close it to avoid
            # mixing two versions in one session.
            self.root.destroy()

        except Exception as exc:
            messagebox.showwarning(
                "SSS Restore Failed",
                str(
                    exc
                ),
                parent=self.root,
            )

    def restore_selected_snapshot(
        self
    ):
        if self.recovery_tree is None:
            return

        selection = self.recovery_tree.selection()

        if not selection:
            messagebox.showinfo(
                "SSS Recovery",
                "Select a recovery snapshot first.",
                parent=self.root,
            )
            return

        path = self.recovery_item_paths.get(
            selection[
                0
            ]
        )

        self._confirm_and_restore(
            path
        )

    def restore_last_known_good(
        self
    ):
        path = last_known_good_snapshot()

        if path is None:
            messagebox.showinfo(
                "Last Known Good",
                (
                    "No Last Known Good snapshot has been saved yet.\n\n"
                    "Run Full System Diagnostics, get an overall READY result, "
                    "then choose SAVE READY SYSTEM AS LAST KNOWN GOOD."
                ),
                parent=self.root,
            )
            return

        self._confirm_and_restore(
            path
        )

    def open_recovery_folder(
        self
    ):
        folder = Path(
            r"C:\Church\SermonAI\Recovery\Snapshots"
        )

        try:
            folder.mkdir(
                parents=True,
                exist_ok=True,
            )

            if os.name == "nt":
                os.startfile(
                    str(
                        folder
                    )
                )
            else:
                subprocess.Popen(
                    [
                        "xdg-open",
                        str(
                            folder
                        ),
                    ]
                )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Recovery",
                str(
                    exc
                ),
                parent=self.root,
            )

    def open_and_run_diagnostics(
        self
    ):
        self.show_page(
            "diagnostics"
        )

        self.run_full_system_test_async()

    def _clear_diagnostic_tree(
        self
    ):
        if self.diagnostic_tree is None:
            return

        try:
            for item in self.diagnostic_tree.get_children():
                self.diagnostic_tree.delete(
                    item
                )
        except Exception:
            pass

    def run_full_system_test_async(
        self
    ):
        if self.diagnostic_running:
            return

        self.diagnostic_running = True
        self.diagnostic_overall_var.set(
            "RUNNING — Full System Test in progress…"
        )
        self.diagnostic_detail_var.set(
            (
                "Read-only checks are running. Recording, Streaming, camera "
                "presets, presentation cues, and audio mute state will not be changed."
            )
        )

        self._clear_diagnostic_tree()

        if self.diagnostic_run_button is not None:
            try:
                self.diagnostic_run_button.configure(
                    state="disabled",
                    text="TESTING…",
                )
            except Exception:
                pass

        def worker():
            try:
                report = run_full_system_test()

                self.root.after(
                    0,
                    lambda:
                        self._finish_full_system_test(
                            report,
                            None,
                        ),
                )

            except Exception as exc:
                self.root.after(
                    0,
                    lambda:
                        self._finish_full_system_test(
                            None,
                            str(
                                exc
                            ),
                        ),
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def _finish_full_system_test(
        self,
        report,
        error
    ):
        self.diagnostic_running = False

        if self.diagnostic_run_button is not None:
            try:
                self.diagnostic_run_button.configure(
                    state="normal",
                    text="RUN FULL SYSTEM TEST",
                )
            except Exception:
                pass

        if error:
            self.diagnostic_overall_var.set(
                "FIX — Diagnostic engine could not complete"
            )
            self.diagnostic_detail_var.set(
                error
            )
            return

        self.diagnostic_report = report

        overall = str(
            report.get(
                "overall",
                "CHECK"
            )
        ).upper()

        counts = report.get(
            "counts",
            {}
        )

        self.diagnostic_overall_var.set(
            (
                overall
                +
                " — "
                +
                str(
                    counts.get(
                        "READY",
                        0
                    )
                )
                +
                " READY / "
                +
                str(
                    counts.get(
                        "CHECK",
                        0
                    )
                )
                +
                " CHECK / "
                +
                str(
                    counts.get(
                        "FIX",
                        0
                    )
                )
                +
                " FIX"
            )
        )

        self.diagnostic_detail_var.set(
            (
                "Completed "
                +
                str(
                    report.get(
                        "generated_at",
                        ""
                    )
                )
                +
                ". Test was read-only and did not change live service state."
                +
                (
                    " This READY result can now be saved as Last Known Good on the Recovery page."
                    if overall == "READY"
                    else
                    ""
                )
            )
        )

        self._clear_diagnostic_tree()

        if self.diagnostic_tree is not None:
            for result in report.get(
                "results",
                []
            ):
                try:
                    self.diagnostic_tree.insert(
                        "",
                        "end",
                        values=(
                            result.get(
                                "level",
                                "CHECK"
                            ),
                            result.get(
                                "name",
                                "Diagnostic"
                            ),
                            result.get(
                                "detail",
                                ""
                            ),
                        ),
                    )
                except Exception:
                    pass

    def export_last_diagnostics(
        self
    ):
        if self.diagnostic_report is None:
            messagebox.showinfo(
                "SSS Diagnostics",
                (
                    "Run FULL SYSTEM TEST first, then export the report."
                ),
                parent=self.root,
            )
            return

        try:
            bundle = export_diagnostic_bundle(
                self.diagnostic_report
            )

            messagebox.showinfo(
                "Diagnostic ZIP Created",
                (
                    "Created:\n\n"
                    +
                    str(
                        bundle
                    )
                    +
                    "\n\nPassword/token/secret-like configuration keys are "
                    "redacted from the bundle."
                ),
                parent=self.root,
            )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Diagnostics",
                str(
                    exc
                ),
                parent=self.root,
            )

    def open_diagnostics_folder(
        self
    ):
        folder = Path(
            r"C:\Church\SermonAI\Diagnostics"
        )

        try:
            folder.mkdir(
                parents=True,
                exist_ok=True,
            )

            if os.name == "nt":
                os.startfile(
                    str(
                        folder
                    )
                )
            else:
                subprocess.Popen(
                    [
                        "xdg-open",
                        str(
                            folder
                        ),
                    ]
                )

        except Exception as exc:
            messagebox.showwarning(
                "SSS Diagnostics",
                str(
                    exc
                ),
                parent=self.root,
            )

    def refresh(
        self
    ):
        # Reuse the proven profile selector / identity logic from
        # ProfileManager.
        super().refresh()

        profile = load_active_profile()

        profile_name = str(
            profile.get(
                "profile_name",
                "Church Profile"
            )
        )

        church_name = str(
            profile.get(
                "church",
                {}
            ).get(
                "name",
                profile_name
            )
        )

        setup = get_profile_setup_status(
            profile
        )

        obs = get_profile_obs_settings(
            profile
        )

        presentation = get_profile_presentation_settings(
            profile
        )

        camera_settings = get_profile_camera_settings(
            profile
        )

        audio_settings = get_profile_audio_settings(
            profile
        )

        sermon_source_settings = get_profile_sermon_source_settings(
            profile
        )

        capabilities = get_profile_capabilities(
            profile
        )

        integrations = profile.get(
            "integrations",
            {}
        )

        if not isinstance(
            integrations,
            dict
        ):
            integrations = {}

        camera = camera_settings

        sermon = integrations.get(
            "sermon_source",
            {}
        )

        if not isinstance(
            sermon,
            dict
        ):
            sermon = {}

        self.summary_vars[
            "church"
        ].set(
            (
                "Church: "
                +
                church_name
                +
                "\nProfile: "
                +
                profile_name
                +
                "\nSetup: "
                +
                str(
                    setup[
                        "completed"
                    ]
                )
                +
                "/"
                +
                str(
                    setup[
                        "total"
                    ]
                )
                +
                (
                    " complete — READY"
                    if setup[
                        "ready"
                    ]
                    else
                    " complete"
                )
            )
        )

        self.summary_vars[
            "obs"
        ].set(
            (
                "Source: "
                +
                str(
                    obs.get(
                        "settings_source",
                        "legacy"
                    )
                ).upper()
                +
                "\nCollection: "
                +
                (
                    obs.get(
                        "scene_collection",
                        ""
                    )
                    or
                    "(not mapped)"
                )
                +
                "\nNormal: "
                +
                (
                    obs.get(
                        "normal_scene",
                        ""
                    )
                    or
                    "(not mapped)"
                )
                +
                "\nScripture: "
                +
                (
                    obs.get(
                        "scripture_scene",
                        ""
                    )
                    or
                    "(not mapped)"
                )
            )
        )

        presentation_text = (
            "Source: "
            +
            str(
                presentation.get(
                    "settings_source",
                    "legacy"
                )
            ).upper()
            +
            "\nProvider: "
            +
            str(
                presentation.get(
                    "provider",
                    "Not configured"
                )
            )
        )

        if presentation.get(
            "provider"
        ) == "ProPresenter":
            presentation_text += (
                "\nAPI: "
                +
                str(
                    presentation.get(
                        "host",
                        "127.0.0.1"
                    )
                )
                +
                ":"
                +
                str(
                    presentation.get(
                        "port",
                        50001
                    )
                )
            )

        self.summary_vars[
            "presentation"
        ].set(
            presentation_text
        )

        camera_provider = str(
            camera.get(
                "provider",
                "Not configured"
            )
            or
            "Not configured"
        )

        camera_source = str(
            camera.get(
                "settings_source",
                "legacy"
            )
        ).upper()

        if (
            camera_source
            ==
            "PROFILE"
            and
            camera_provider
            ==
            "PTZOptics / HTTP-CGI"
        ):
            camera_detail = (
                "\nCamera: "
                +
                (
                    camera.get(
                        "host",
                        ""
                    )
                    or
                    "(host missing)"
                )
                +
                ":"
                +
                str(
                    camera.get(
                        "port",
                        80
                    )
                )
                +
                "\nWorship preset: "
                +
                str(
                    camera.get(
                        "worship_preset",
                        1
                    )
                )
                +
                " | Pastor preset: "
                +
                str(
                    camera.get(
                        "pastor_preset",
                        2
                    )
                )
            )

        elif camera_source == "PROFILE":
            camera_detail = (
                "\n"
                +
                camera_provider
                +
                " requires no movable PTZ controls."
                if camera_provider in {
                    "Fixed camera",
                    "None",
                }
                else
                "\nPortable adapter is not active for this provider."
            )

        else:
            camera_detail = (
                "\nExisting machine-local PTZ configuration remains authoritative."
            )

        volunteer_camera = bool(
            capabilities.get(
                "camera_controls",
                True
            )
        )

        if (
            camera_source
            ==
            "PROFILE"
            and
            camera_provider
            in {
                "Fixed camera",
                "None",
            }
        ):
            volunteer_camera = False

        self.summary_vars[
            "camera"
        ].set(
            (
                "Source: "
                +
                camera_source
                +
                "\nProvider: "
                +
                camera_provider
                +
                camera_detail
                +
                "\nVolunteer camera controls: "
                +
                (
                    "ON"
                    if volunteer_camera
                    else
                    "OFF"
                )
            )
        )

        audio_source = str(
            audio_settings.get(
                "settings_source",
                "legacy"
            )
        ).upper()

        audio_provider = str(
            audio_settings.get(
                "provider",
                "OBS Audio Inputs"
            )
        )

        audio_inputs = list(
            audio_settings.get(
                "mute_inputs",
                []
            )
            or
            []
        )

        if audio_source == "PROFILE":
            audio_detail = (
                "\nMute targets: "
                +
                (
                    ", ".join(
                        audio_inputs
                    )
                    if audio_inputs
                    else
                    "(none selected)"
                )
            )
        else:
            audio_detail = (
                "\nExisting SSS emergency_mute_inputs remain authoritative."
            )

        volunteer_audio = bool(
            capabilities.get(
                "audio_mute",
                True
            )
        )

        if (
            audio_source
            ==
            "PROFILE"
            and
            audio_provider
            ==
            "None"
        ):
            volunteer_audio = False

        self.summary_vars[
            "audio"
        ].set(
            (
                "Source: "
                +
                audio_source
                +
                "\nProvider: "
                +
                audio_provider
                +
                audio_detail
                +
                "\nVolunteer mute control: "
                +
                (
                    "ON"
                    if volunteer_audio
                    else
                    "OFF"
                )
                +
                "\nLive meter: existing production monitor path"
            )
        )

        sermon_provider = str(
            sermon_source_settings.get(
                "provider",
                "Manual"
            )
            or
            "Manual"
        )

        sermon_source_mode = str(
            sermon_source_settings.get(
                "settings_source",
                "legacy"
            )
        ).upper()

        if (
            sermon_source_mode
            ==
            "PROFILE"
            and
            sermon_provider
            ==
            "Manual"
        ):
            stored_plan = sermon_source_settings.get(
                "manual_plan",
                {}
            )

        elif (
            sermon_source_mode
            ==
            "PROFILE"
            and
            sermon_provider
            ==
            "Imported File"
        ):
            stored_plan = sermon_source_settings.get(
                "imported_plan",
                {}
            )

        else:
            stored_plan = {}

        plan_detail = ""

        if isinstance(
            stored_plan,
            dict
        ) and stored_plan:
            plan_detail = (
                "\nStored plan: "
                +
                str(
                    stored_plan.get(
                        "title",
                        "(no title)"
                    )
                )
                +
                " | "
                +
                str(
                    stored_plan.get(
                        "scripture",
                        "(no Scripture)"
                    )
                )
            )

        elif (
            sermon_source_mode
            ==
            "PROFILE"
            and
            sermon_provider
            ==
            "Pastor Email"
        ):
            plan_detail = (
                "\nBackend: existing date-guarded Gmail importer"
            )

        self.summary_vars[
            "sermon"
        ].set(
            (
                "Source: "
                +
                sermon_source_mode
                +
                "\nProvider: "
                +
                sermon_provider
                +
                plan_detail
                +
                "\nScripture controls: "
                +
                (
                    "ON"
                    if capabilities.get(
                        "scripture",
                        True
                    )
                    else
                    "OFF"
                )
                +
                "\nSermon chapter/lower-third controls: "
                +
                (
                    "ON"
                    if capabilities.get(
                        "sermon_controls",
                        True
                    )
                    else
                    "OFF"
                )
            )
        )

        self.summary_vars[
            "streaming"
        ].set(
            (
                "Recording controls: "
                +
                (
                    "ON"
                    if capabilities.get(
                        "recording",
                        True
                    )
                    else
                    "OFF"
                )
                +
                "\nStreaming controls: "
                +
                (
                    "ON"
                    if capabilities.get(
                        "streaming",
                        True
                    )
                    else
                    "OFF"
                )
                +
                "\nOutputs remain manual and separate."
            )
        )

        self.summary_vars[
            "automation"
        ].set(
            (
                "Sermon source: "
                +
                sermon_source_mode
                +
                " / "
                +
                sermon_provider
                +
                "\nCurrent production automation remains unchanged."
                +
                "\nFuture adapters will move optional automation here one "
                "feature at a time."
            )
        )

        self.summary_vars[
            "advanced"
        ].set(
            (
                self.mode_var.get()
                +
                "\n"
                +
                self.path_var.get()
                +
                "\nProfile root: "
                +
                str(
                    profile_root()
                )
                +
                "\nProfile schema: "
                +
                str(
                    profile.get(
                        "schema_version",
                        "?"
                    )
                )
                +
                " / current "
                +
                str(
                    PROFILE_SCHEMA_VERSION
                )
                +
                "\nPortable exports exclude credentials/secrets."
            )
        )


def main():
    set_windows_app_user_model_id()

    root = tk.Tk()

    app = SSSSettings(
        root
    )

    if "--diagnostics" in sys.argv:
        app.show_page(
            "diagnostics"
        )

        root.after(
            250,
            app.run_full_system_test_async,
        )

    elif "--recovery" in sys.argv:
        app.show_page(
            "recovery"
        )

    elif "--history" in sys.argv:
        app.show_page(
            "history"
        )

    elif "--migrations" in sys.argv:
        app.show_page(
            "advanced"
        )

    elif "--security" in sys.argv:
        app.show_page(
            "security"
        )

    elif "--updates" in sys.argv:
        app.show_page(
            "updates"
        )

    root.mainloop()


if __name__ == "__main__":
    main()
