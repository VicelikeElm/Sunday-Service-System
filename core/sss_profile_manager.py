import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import (
    filedialog,
    messagebox,
    ttk,
)

from sss_profile import (
    active_profile_path,
    create_profile,
    export_active_profile,
    get_profile_audio_settings,
    get_profile_camera_settings,
    get_profile_capabilities,
    get_profile_obs_settings,
    get_profile_presentation_settings,
    get_profile_sermon_source_settings,
    get_profile_setup_status,
    import_profile,
    list_profiles,
    load_active_profile,
    profile_root,
    save_active_audio_settings,
    save_active_camera_settings,
    save_active_capabilities,
    save_active_obs_settings,
    save_active_presentation_settings,
    save_active_sermon_source_settings,
    set_active_profile,
    set_windows_app_user_model_id,
)

from sss_setup_wizard import (
    open_setup_wizard,
)

from sss_presentation_adapters import (
    adapter_info,
)

from sss_propresenter_api import (
    connection_test as test_propresenter_connection,
)


from sss_audio_adapters import (
    adapter_info as audio_adapter_info,
    discover_obs_audio_inputs,
    profile_audio_ready,
    validate_obs_audio_inputs,
)

from sss_camera_adapters import (
    adapter_info as camera_adapter_info,
    check_tcp_connection as check_camera_connection,
    test_profile_camera_preset,
)

from sss_sermon_sources import (
    adapter_info as sermon_source_adapter_info,
    build_manual_plan,
    load_imported_plan_file,
    materialize_profile_sermon_plan,
    profile_sermon_source_ready,
    read_canonical_sermon_plan,
    refresh_pastor_email_now,
    upcoming_sunday_iso,
)

from sss_obs_profile import (
    discover_obs,
    test_profile_preview_scene,
)


class ProfileManager:
    def __init__(
        self,
        root
    ):
        self.root = root

        self.root.title(
            "Sunday Service System — Profile Manager"
        )

        self.root.geometry(
            "700x785"
        )

        self.root.minsize(
            650,
            720
        )

        outer = ttk.Frame(
            root,
            padding=18,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            outer,
            text="SSS PROFILE MANAGER",
            font=(
                "Segoe UI",
                18,
                "bold",
            ),
        ).pack(
            pady=(
                0,
                10
            )
        )

        self.name_var = tk.StringVar()
        self.mode_var = tk.StringVar()
        self.path_var = tk.StringVar()
        self.setup_status_var = tk.StringVar()
        self.profile_selector_var = tk.StringVar()
        self.profile_selector_map = {}

        selector_frame = ttk.LabelFrame(
            outer,
            text="Select Church Profile",
            padding=10,
        )

        selector_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        selector_frame.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            selector_frame,
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
            selector_frame,
            textvariable=self.profile_selector_var,
            state="readonly",
            width=42,
            postcommand=self.refresh_profile_selector,
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

        info = ttk.LabelFrame(
            outer,
            text="Active Church Profile",
            padding=12,
        )

        info.pack(
            fill="x"
        )

        ttk.Label(
            info,
            textvariable=self.name_var,
            font=(
                "Segoe UI",
                13,
                "bold",
            ),
        ).pack(
            anchor="w"
        )

        ttk.Label(
            info,
            textvariable=self.mode_var,
        ).pack(
            anchor="w",
            pady=(
                6,
                0
            ),
        )

        ttk.Label(
            info,
            textvariable=self.path_var,
            wraplength=580,
        ).pack(
            anchor="w",
            pady=(
                6,
                0
            ),
        )

        setup_frame = ttk.LabelFrame(
            outer,
            text="Profile Setup",
            padding=10,
        )
        setup_frame.pack(
            fill="x",
            pady=(10, 0),
        )
        setup_frame.columnconfigure(
            0,
            weight=1
        )

        ttk.Label(
            setup_frame,
            textvariable=self.setup_status_var,
            font=("Segoe UI", 10, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )

        ttk.Button(
            setup_frame,
            text="RUN / EDIT SETUP WIZARD",
            command=self.open_setup_wizard,
        ).grid(
            row=0,
            column=1,
            sticky="e",
        )

        note = ttk.Label(
            outer,
            text=(
                "SSS v2.2 keeps existing church behavior on safe LEGACY paths "
                "while OBS, Presentation, Camera, Audio, Sermon Source, and "
                "volunteer controls can be configured per profile intentionally."
            ),
            wraplength=590,
            justify="left",
        )

        note.pack(
            fill="x",
            pady=(
                14,
                14
            ),
        )

        ttk.Button(
            outer,
            text="CONFIGURE OBS FOR THIS PROFILE",
            command=self.open_obs_setup,
        ).pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Button(
            outer,
            text="CONFIGURE PRESENTATION FOR THIS PROFILE",
            command=self.open_presentation_setup,
        ).pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Button(
            outer,
            text="CONFIGURE CAMERA FOR THIS PROFILE",
            command=self.open_camera_setup,
        ).pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Button(
            outer,
            text="CONFIGURE AUDIO FOR THIS PROFILE",
            command=self.open_audio_setup,
        ).pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Button(
            outer,
            text="CONFIGURE SERMON SOURCE FOR THIS PROFILE",
            command=self.open_sermon_source_setup,
        ).pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Button(
            outer,
            text="CONFIGURE VOLUNTEER CONTROLS",
            command=self.open_capability_setup,
        ).pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x"
        )

        for column in range(
            4
        ):
            buttons.columnconfigure(
                column,
                weight=1
            )

        ttk.Button(
            buttons,
            text="NEW PROFILE",
            command=self.new_profile,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=4,
            pady=4,
        )

        ttk.Button(
            buttons,
            text="EXPORT PROFILE",
            command=self.export_profile,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
            pady=4,
        )

        ttk.Button(
            buttons,
            text="IMPORT PROFILE",
            command=self.import_profile_file,
        ).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=4,
            pady=4,
        )

        ttk.Button(
            buttons,
            text="OPEN PROFILE FOLDER",
            command=self.open_folder,
        ).grid(
            row=0,
            column=3,
            sticky="ew",
            padx=4,
            pady=4,
        )

        ttk.Button(
            outer,
            text="CLOSE",
            command=root.destroy,
        ).pack(
            fill="x",
            pady=(
                18,
                0
            ),
        )

        self.refresh()

    def refresh_profile_selector(
        self
    ):
        profiles = list_profiles()

        display_values = []
        mapping = {}
        selected_display = ""
        name_counts = {}

        for item in profiles:
            name = str(
                item.get(
                    "profile_name",
                    "Church Profile"
                )
            )

            name_counts[name] = (
                name_counts.get(
                    name,
                    0
                )
                +
                1
            )

        for item in profiles:
            name = str(
                item.get(
                    "profile_name",
                    "Church Profile"
                )
            )

            display = name

            if name_counts.get(
                name,
                0
            ) > 1:
                display = (
                    name
                    +
                    " — "
                    +
                    str(
                        item.get(
                            "profile_id",
                            ""
                        )
                    )
                )

            display_values.append(
                display
            )

            mapping[display] = str(
                item.get(
                    "profile_id",
                    ""
                )
            )

            if item.get(
                "active"
            ):
                selected_display = display

        self.profile_selector_map = mapping

        self.profile_selector.configure(
            values=tuple(
                display_values
            )
        )

        if selected_display:
            self.profile_selector_var.set(
                selected_display
            )
        elif display_values:
            self.profile_selector_var.set(
                display_values[0]
            )

    def on_profile_selected(
        self,
        event=None
    ):
        display = self.profile_selector_var.get()
        profile_id = self.profile_selector_map.get(
            display
        )

        if not profile_id:
            return

        try:
            set_active_profile(
                profile_id
            )
            self.refresh()

        except Exception as exc:
            messagebox.showerror(
                "Profile Selection Failed",
                str(exc),
            )
            self.refresh()

    def refresh(
        self
    ):
        self.refresh_profile_selector()

        profile = load_active_profile()

        self.name_var.set(
            "Profile: "
            +
            str(
                profile.get(
                    "profile_name",
                    "Church Profile"
                )
            )
        )

        compatibility = profile.get(
            "compatibility",
            {}
        )

        mode = str(
            compatibility.get(
                "mode",
                "unknown"
            )
        )

        self.mode_var.set(
            "Mode: "
            +
            mode
        )

        self.path_var.set(
            "Stored at: "
            +
            str(
                active_profile_path()
            )
        )

        setup_status = get_profile_setup_status(
            profile
        )

        self.setup_status_var.set(
            (
                "Setup: "
                +
                str(setup_status["completed"])
                +
                "/"
                +
                str(setup_status["total"])
                +
                (
                    " complete — READY"
                    if setup_status["ready"]
                    else
                    " complete"
                )
            )
        )

    def open_setup_wizard(
        self
    ):
        open_setup_wizard(
            self.root,
            on_saved=self.refresh,
        )

    def open_capability_setup(
        self
    ):
        profile = load_active_profile()
        profile_name = str(
            profile.get(
                "profile_name",
                "Church Profile"
            )
        )

        saved = get_profile_capabilities(
            profile
        )

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "SSS Volunteer Controls — "
            +
            profile_name
        )

        window.geometry(
            "650x590"
        )

        window.minsize(
            610,
            540,
        )

        try:
            window.transient(
                self.root
            )
        except Exception:
            pass

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
            text="VOLUNTEER CONTROLS",
            font=(
                "Segoe UI",
                16,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                4
            )
        )

        ttk.Label(
            outer,
            text=(
                "Profile: "
                +
                profile_name
            ),
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                12
            )
        )

        source_var = tk.StringVar(
            value=saved.get(
                "settings_source",
                "legacy"
            )
        )

        source_frame = ttk.LabelFrame(
            outer,
            text="Volunteer UI Source",
            padding=10,
        )

        source_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Radiobutton(
            source_frame,
            text="LEGACY — show the complete current SSS volunteer workflow",
            variable=source_var,
            value="legacy",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Radiobutton(
            source_frame,
            text="PROFILE — show only the controls enabled below",
            variable=source_var,
            value="profile",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Label(
            source_frame,
            text=(
                "LEGACY is the safe fallback for existing churches. PROFILE "
                "changes visibility only; it never automatically starts or "
                "stops any service."
            ),
            wraplength=580,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                6,
                0
            ),
        )

        options_frame = ttk.LabelFrame(
            outer,
            text="Controls This Church Uses",
            padding=10,
        )

        options_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        recording_var = tk.BooleanVar(
            value=saved.get(
                "recording",
                True
            )
        )
        streaming_var = tk.BooleanVar(
            value=saved.get(
                "streaming",
                True
            )
        )
        audio_mute_var = tk.BooleanVar(
            value=saved.get(
                "audio_mute",
                True
            )
        )
        scripture_var = tk.BooleanVar(
            value=saved.get(
                "scripture",
                True
            )
        )
        sermon_var = tk.BooleanVar(
            value=saved.get(
                "sermon_controls",
                True
            )
        )
        camera_var = tk.BooleanVar(
            value=saved.get(
                "camera_controls",
                True
            )
        )

        options = (
            (
                "Recording controls",
                recording_var,
                "START RECORDING and STOP RECORDING",
            ),
            (
                "Streaming controls",
                streaming_var,
                "START STREAM and STOP STREAM",
            ),
            (
                "Program audio mute",
                audio_mute_var,
                "MUTE AUDIO / UNMUTE AUDIO",
            ),
            (
                "Scripture controls",
                scripture_var,
                "START/NEXT/END Scripture workflow",
            ),
            (
                "Sermon chapter / lower-third controls",
                sermon_var,
                "SERMON chapter/lower-third row",
            ),
            (
                "Camera controls",
                camera_var,
                "WORSHIP VIEW / PASTOR VIEW row",
            ),
        )

        for row, (
            label,
            variable,
            detail
        ) in enumerate(
            options
        ):
            ttk.Checkbutton(
                options_frame,
                text=label,
                variable=variable,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                pady=4,
            )

            ttk.Label(
                options_frame,
                text=detail,
            ).grid(
                row=row,
                column=1,
                sticky="w",
                padx=(
                    12,
                    0
                ),
                pady=4,
            )

        options_frame.columnconfigure(
            1,
            weight=1
        )

        ttk.Label(
            outer,
            text=(
                "When a complete workflow row is not needed, SSS removes it "
                "from the volunteer dashboard and automatically renumbers the "
                "remaining steps. Admin / Troubleshooting always remains available."
            ),
            wraplength=590,
            justify="left",
        ).pack(
            fill="x",
            pady=(
                2,
                12
            ),
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x"
        )

        buttons.columnconfigure(
            0,
            weight=1
        )
        buttons.columnconfigure(
            1,
            weight=1
        )

        def save_now():
            try:
                save_active_capabilities(
                    settings_source=source_var.get(),
                    recording=recording_var.get(),
                    streaming=streaming_var.get(),
                    audio_mute=audio_mute_var.get(),
                    scripture=scripture_var.get(),
                    sermon_controls=sermon_var.get(),
                    camera_controls=camera_var.get(),
                )

                self.refresh()

                messagebox.showinfo(
                    "Volunteer Controls Saved",
                    (
                        "Volunteer control visibility saved.\n\n"
                        "Source: "
                        +
                        source_var.get().upper()
                        +
                        "\n\nReturn to the main SSS window to see the "
                        "updated volunteer workflow."
                    ),
                    parent=window,
                )

            except Exception as exc:
                messagebox.showwarning(
                    "Volunteer Controls",
                    str(
                        exc
                    ),
                    parent=window,
                )

        ttk.Button(
            buttons,
            text="SAVE",
            command=save_now,
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
            text="CLOSE",
            command=window.destroy,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

    def open_sermon_source_setup(
        self
    ):
        profile = load_active_profile()

        profile_name = str(
            profile.get(
                "profile_name",
                "Church Profile"
            )
        )

        saved = get_profile_sermon_source_settings(
            profile
        )

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "SSS Sermon Source Setup — "
            +
            profile_name
        )

        window.geometry(
            "800x800"
        )

        window.minsize(
            740,
            700,
        )

        try:
            window.transient(
                self.root
            )
        except Exception:
            pass

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
            text="SERMON SOURCE SETUP",
            font=(
                "Segoe UI",
                16,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                4
            )
        )

        ttk.Label(
            outer,
            text=(
                "Profile: "
                +
                profile_name
            ),
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                10
            )
        )

        source_var = tk.StringVar(
            value=saved.get(
                "settings_source",
                "legacy"
            )
        )

        source_frame = ttk.LabelFrame(
            outer,
            text="Configuration Source",
            padding=8,
        )

        source_frame.pack(
            fill="x",
            pady=(
                0,
                8
            ),
        )

        ttk.Radiobutton(
            source_frame,
            text="LEGACY — keep the current production sermon-plan workflow",
            variable=source_var,
            value="legacy",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Radiobutton(
            source_frame,
            text="PROFILE — use the selected sermon-source adapter",
            variable=source_var,
            value="profile",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Label(
            source_frame,
            text=(
                "LEGACY preserves the current Friday-email workflow. PROFILE "
                "must be explicitly selected and saved before SSS changes how "
                "the weekly sermon plan is sourced."
            ),
            wraplength=720,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                5,
                0
            ),
        )

        provider_frame = ttk.LabelFrame(
            outer,
            text="Sermon Source Adapter",
            padding=8,
        )

        provider_frame.pack(
            fill="x",
            pady=(
                0,
                8
            ),
        )

        provider_frame.columnconfigure(
            1,
            weight=1
        )

        provider_var = tk.StringVar(
            value=saved.get(
                "provider",
                "Manual"
            )
        )

        adapter_status_var = tk.StringVar()

        ttk.Label(
            provider_frame,
            text="Provider",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
        )

        provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=provider_var,
            state="readonly",
            values=(
                "Manual",
                "Pastor Email",
                "Imported File",
                "Planning Software",
                "Other",
            ),
        )

        provider_combo.grid(
            row=0,
            column=1,
            sticky="ew",
        )

        ttk.Label(
            provider_frame,
            textvariable=adapter_status_var,
            wraplength=700,
            justify="left",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                6,
                0
            ),
        )

        def refresh_adapter_status(
            event=None
        ):
            info = sermon_source_adapter_info(
                provider_var.get()
            )

            adapter_status_var.set(
                (
                    "LIVE ADAPTER READY — "
                    if info.get(
                        "live_supported"
                    )
                    else
                    "ADAPTER PLANNED — "
                )
                +
                str(
                    info.get(
                        "description",
                        ""
                    )
                )
            )

        provider_combo.bind(
            "<<ComboboxSelected>>",
            refresh_adapter_status,
            add="+",
        )

        refresh_adapter_status()

        manual_frame = ttk.LabelFrame(
            outer,
            text="Manual Sermon Plan",
            padding=8,
        )

        manual_frame.pack(
            fill="x",
            pady=(
                0,
                8
            ),
        )

        manual_frame.columnconfigure(
            1,
            weight=1
        )

        saved_manual = saved.get(
            "manual_plan",
            {}
        )

        if not isinstance(
            saved_manual,
            dict
        ):
            saved_manual = {}

        service_date_var = tk.StringVar(
            value=(
                str(
                    saved_manual.get(
                        "service_date",
                        ""
                    )
                ).strip()
                or
                upcoming_sunday_iso()
            )
        )

        title_var = tk.StringVar(
            value=str(
                saved_manual.get(
                    "title",
                    ""
                )
            )
        )

        scripture_var = tk.StringVar(
            value=str(
                saved_manual.get(
                    "scripture",
                    ""
                )
            )
        )

        preacher_var = tk.StringVar(
            value=str(
                saved_manual.get(
                    "preacher",
                    ""
                )
            )
        )

        fields = (
            (
                "Service date",
                service_date_var,
            ),
            (
                "Title",
                title_var,
            ),
            (
                "Scripture",
                scripture_var,
            ),
            (
                "Preacher",
                preacher_var,
            ),
        )

        for row, (
            label,
            variable
        ) in enumerate(
            fields
        ):
            ttk.Label(
                manual_frame,
                text=label,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(
                    0,
                    8
                ),
                pady=3,
            )

            ttk.Entry(
                manual_frame,
                textvariable=variable,
            ).grid(
                row=row,
                column=1,
                sticky="ew",
                pady=3,
            )

        ttk.Label(
            manual_frame,
            text="Sermon points — one per line",
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                5,
                2
            ),
        )

        points_text = tk.Text(
            manual_frame,
            height=5,
            wrap="word",
        )

        points_text.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        saved_points = saved_manual.get(
            "points",
            []
        )

        if isinstance(
            saved_points,
            list
        ):
            points_text.insert(
                "1.0",
                "\n".join(
                    str(
                        point
                    )
                    for point in saved_points
                ),
            )

        imported_frame = ttk.LabelFrame(
            outer,
            text="Imported Sermon Plan",
            padding=8,
        )

        imported_frame.pack(
            fill="x",
            pady=(
                0,
                8
            ),
        )

        imported_plan = dict(
            saved.get(
                "imported_plan",
                {}
            )
            or
            {}
        )

        imported_name_var = tk.StringVar(
            value=(
                saved.get(
                    "last_import_name",
                    ""
                )
                or
                "No JSON plan selected."
            )
        )

        ttk.Label(
            imported_frame,
            textvariable=imported_name_var,
            wraplength=690,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                0,
                5
            ),
        )

        def import_json_now():
            nonlocal imported_plan

            path = filedialog.askopenfilename(
                title="Import SSS Sermon Plan",
                filetypes=(
                    (
                        "JSON sermon plans",
                        "*.json",
                    ),
                    (
                        "All files",
                        "*.*",
                    ),
                ),
                parent=window,
            )

            if not path:
                return

            try:
                imported_plan = load_imported_plan_file(
                    path
                )

                imported_name_var.set(
                    (
                        Path(
                            path
                        ).name
                        +
                        " — "
                        +
                        str(
                            imported_plan.get(
                                "title",
                                ""
                            )
                        )
                        +
                        " | "
                        +
                        str(
                            imported_plan.get(
                                "scripture",
                                ""
                            )
                        )
                    )
                )

            except Exception as exc:
                messagebox.showwarning(
                    "Import Sermon Plan",
                    str(
                        exc
                    ),
                    parent=window,
                )

        ttk.Button(
            imported_frame,
            text="IMPORT SERMON PLAN JSON",
            command=import_json_now,
        ).pack(
            fill="x"
        )

        email_frame = ttk.LabelFrame(
            outer,
            text="Pastor Email",
            padding=8,
        )

        email_frame.pack(
            fill="x",
            pady=(
                0,
                8
            ),
        )

        email_sender_var = tk.StringVar(
            value=saved.get(
                "email_sender",
                ""
            )
        )

        email_auto_refresh_var = tk.BooleanVar(
            value=bool(
                saved.get(
                    "email_auto_refresh",
                    True
                )
            )
        )

        ttk.Label(
            email_frame,
            text="Expected sender (profile metadata)",
        ).pack(
            anchor="w"
        )

        ttk.Entry(
            email_frame,
            textvariable=email_sender_var,
        ).pack(
            fill="x",
            pady=(
                2,
                5
            ),
        )

        ttk.Checkbutton(
            email_frame,
            text="Refresh Pastor Email automatically when Sunday apps launch",
            variable=email_auto_refresh_var,
        ).pack(
            anchor="w",
            pady=(
                2,
                5
            ),
        )

        ttk.Label(
            email_frame,
            text=(
                "The current Gmail importer, OAuth token, and sender/date guard "
                "remain machine-local. The sender field is stored in the portable "
                "profile for the future fully portable email backend."
            ),
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w"
        )

        active_plan_var = tk.StringVar()

        status_frame = ttk.LabelFrame(
            outer,
            text="Active SSS Sermon Plan",
            padding=8,
        )

        status_frame.pack(
            fill="x",
            pady=(
                0,
                8
            ),
        )

        ttk.Label(
            status_frame,
            textvariable=active_plan_var,
            wraplength=700,
            justify="left",
        ).pack(
            anchor="w"
        )

        def refresh_active_plan():
            plan = read_canonical_sermon_plan()

            if not plan:
                active_plan_var.set(
                    "No sermon_plan.json is currently loaded."
                )
                return

            active_plan_var.set(
                (
                    str(
                        plan.get(
                            "service_date",
                            "(no date)"
                        )
                    )
                    +
                    " — "
                    +
                    str(
                        plan.get(
                            "title",
                            "(no title)"
                        )
                    )
                    +
                    " | "
                    +
                    str(
                        plan.get(
                            "scripture",
                            "(no Scripture)"
                        )
                    )
                    +
                    " | "
                    +
                    str(
                        len(
                            plan.get(
                                "points",
                                []
                            )
                            if isinstance(
                                plan.get(
                                    "points",
                                    []
                                ),
                                list
                            )
                            else
                            []
                        )
                    )
                    +
                    " point(s)"
                )
            )

        refresh_active_plan()

        def manual_plan_from_form():
            points = [
                line.strip()
                for line in points_text.get(
                    "1.0",
                    tk.END
                ).splitlines()
                if line.strip()
            ]

            return build_manual_plan(
                title=title_var.get(),
                scripture=scripture_var.get(),
                service_date=service_date_var.get(),
                preacher=preacher_var.get(),
                points=points,
            )

        def save_values(
            *,
            show_message=False
        ):
            provider = provider_var.get()
            manual_plan = dict(
                saved.get(
                    "manual_plan",
                    {}
                )
                or
                {}
            )

            if provider == "Manual":
                if (
                    source_var.get()
                    ==
                    "profile"
                ):
                    manual_plan = manual_plan_from_form()
                else:
                    # Keep partially-entered values portable in LEGACY mode
                    # without requiring a complete plan.
                    manual_plan = {
                        "service_date": service_date_var.get().strip(),
                        "title": title_var.get().strip(),
                        "scripture": scripture_var.get().strip(),
                        "preacher": preacher_var.get().strip(),
                        "points": [
                            line.strip()
                            for line in points_text.get(
                                "1.0",
                                tk.END
                            ).splitlines()
                            if line.strip()
                        ],
                    }

            result = save_active_sermon_source_settings(
                settings_source=source_var.get(),
                provider=provider,
                manual_plan=manual_plan,
                imported_plan=imported_plan,
                email_sender=email_sender_var.get(),
                email_auto_refresh=email_auto_refresh_var.get(),
                last_import_name=(
                    imported_name_var.get()
                    if imported_plan
                    else
                    ""
                ),
            )

            self.refresh()

            if show_message:
                messagebox.showinfo(
                    "Sermon Source Saved",
                    (
                        "Sermon source settings saved.\n\n"
                        "Source: "
                        +
                        source_var.get().upper()
                        +
                        "\nProvider: "
                        +
                        provider
                        +
                        "\n\nSaving configuration does not overwrite the active "
                        "sermon plan. Use APPLY PROFILE SOURCE NOW when you want "
                        "the profile source to become sermon_plan.json."
                    ),
                    parent=window,
                )

            return result

        action_status_var = tk.StringVar(
            value=(
                "SAVE changes configuration only. APPLY intentionally updates "
                "the active sermon plan."
            )
        )

        def check_source_now():
            try:
                # Read-only against the currently saved profile configuration.
                ready, detail = profile_sermon_source_ready()

                action_status_var.set(
                    (
                        "READY — "
                        if ready
                        else
                        "CHECK — "
                    )
                    +
                    str(
                        detail
                    )
                )

            except Exception as exc:
                action_status_var.set(
                    "CHECK FAILED — "
                    +
                    str(
                        exc
                    )
                )

        def apply_source_now():
            try:
                save_values(
                    show_message=False
                )

                provider = provider_var.get()

                if (
                    source_var.get()
                    !=
                    "profile"
                ):
                    raise RuntimeError(
                        "Select PROFILE before applying a profile sermon source."
                    )

                if provider == "Pastor Email":
                    plan = refresh_pastor_email_now()

                else:
                    result = materialize_profile_sermon_plan()
                    plan = result.get(
                        "plan",
                        {}
                    )

                refresh_active_plan()

                action_status_var.set(
                    (
                        "APPLIED — "
                        +
                        str(
                            plan.get(
                                "title",
                                "sermon plan"
                            )
                        )
                        +
                        " | "
                        +
                        str(
                            plan.get(
                                "scripture",
                                ""
                            )
                        )
                        +
                        ". Use LAUNCH SUNDAY APPS or restart SSS before the "
                        "service so lower thirds/chapter labels refresh."
                    )
                )

            except Exception as exc:
                action_status_var.set(
                    "APPLY FAILED — "
                    +
                    str(
                        exc
                    )
                )

        action_frame = ttk.Frame(
            outer
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
            text="CHECK SOURCE",
            command=check_source_now,
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
            text="APPLY PROFILE SOURCE NOW",
            command=apply_source_now,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=3,
        )

        def save_now():
            try:
                save_values(
                    show_message=True
                )

            except Exception as exc:
                messagebox.showwarning(
                    "Sermon Source",
                    str(
                        exc
                    ),
                    parent=window,
                )

        ttk.Button(
            action_frame,
            text="SAVE",
            command=save_now,
        ).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=3,
        )

        ttk.Button(
            action_frame,
            text="CLOSE",
            command=window.destroy,
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
            outer,
            textvariable=action_status_var,
            wraplength=720,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                8,
                0
            ),
        )

    def open_audio_setup(
        self
    ):
        profile = load_active_profile()

        profile_name = str(
            profile.get(
                "profile_name",
                "Church Profile"
            )
        )

        saved = get_profile_audio_settings(
            profile
        )

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "SSS Audio Setup — "
            +
            profile_name
        )

        window.geometry(
            "760x720"
        )

        window.minsize(
            700,
            650,
        )

        try:
            window.transient(
                self.root
            )
        except Exception:
            pass

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
            text="AUDIO SETUP",
            font=(
                "Segoe UI",
                16,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                4
            )
        )

        ttk.Label(
            outer,
            text=(
                "Profile: "
                +
                profile_name
            ),
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                12
            )
        )

        source_var = tk.StringVar(
            value=saved.get(
                "settings_source",
                "legacy"
            )
        )

        source_frame = ttk.LabelFrame(
            outer,
            text="Configuration Source",
            padding=10,
        )

        source_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Radiobutton(
            source_frame,
            text="LEGACY — keep the current working SSS audio/mute configuration",
            variable=source_var,
            value="legacy",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Radiobutton(
            source_frame,
            text="PROFILE — use this profile's selected OBS audio inputs",
            variable=source_var,
            value="profile",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Label(
            source_frame,
            text=(
                "LEGACY keeps the existing emergency_mute_inputs and current "
                "audio meter path. PROFILE changes the volunteer MUTE/UNMUTE "
                "targets only. It never starts recording or streaming."
            ),
            wraplength=680,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                6,
                0
            ),
        )

        provider_frame = ttk.LabelFrame(
            outer,
            text="Audio Adapter",
            padding=10,
        )

        provider_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        provider_frame.columnconfigure(
            1,
            weight=1
        )

        provider_var = tk.StringVar(
            value=saved.get(
                "provider",
                "OBS Audio Inputs"
            )
        )

        adapter_status_var = tk.StringVar()

        ttk.Label(
            provider_frame,
            text="Provider",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=5,
        )

        provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=provider_var,
            state="readonly",
            values=(
                "OBS Audio Inputs",
                "TASCAM Interface",
                "Windows Audio Endpoint",
                "None",
            ),
        )

        provider_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            provider_frame,
            textvariable=adapter_status_var,
            wraplength=650,
            justify="left",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                6,
                0
            ),
        )

        def refresh_adapter_status(
            event=None
        ):
            info = audio_adapter_info(
                provider_var.get()
            )

            adapter_status_var.set(
                (
                    "LIVE ADAPTER READY — "
                    if info.get(
                        "live_supported"
                    )
                    else
                    "ADAPTER PLANNED — "
                )
                +
                str(
                    info.get(
                        "description",
                        ""
                    )
                )
            )

        provider_combo.bind(
            "<<ComboboxSelected>>",
            refresh_adapter_status,
            add="+",
        )

        refresh_adapter_status()

        inputs_frame = ttk.LabelFrame(
            outer,
            text="OBS Inputs Muted Together",
            padding=10,
        )

        inputs_frame.pack(
            fill="both",
            expand=True,
            pady=(
                0,
                10
            ),
        )

        ttk.Label(
            inputs_frame,
            text=(
                "Select every OBS audio input that the volunteer MUTE AUDIO "
                "button should mute/unmute together."
            ),
            wraplength=660,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                0,
                6
            ),
        )

        list_wrapper = ttk.Frame(
            inputs_frame
        )

        list_wrapper.pack(
            fill="both",
            expand=True,
        )

        input_listbox = tk.Listbox(
            list_wrapper,
            selectmode=tk.EXTENDED,
            exportselection=False,
            height=9,
        )

        input_listbox.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar = ttk.Scrollbar(
            list_wrapper,
            orient="vertical",
            command=input_listbox.yview,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        input_listbox.configure(
            yscrollcommand=scrollbar.set
        )

        saved_inputs = list(
            saved.get(
                "mute_inputs",
                []
            )
            or
            []
        )

        discovered_inputs = []

        discovery_status_var = tk.StringVar(
            value="Open OBS, then click DISCOVER OBS AUDIO INPUTS."
        )

        def populate_inputs(
            names
        ):
            nonlocal discovered_inputs

            discovered_inputs = list(
                names
                or
                []
            )

            input_listbox.delete(
                0,
                tk.END
            )

            for name in discovered_inputs:
                input_listbox.insert(
                    tk.END,
                    name
                )

            for index, name in enumerate(
                discovered_inputs
            ):
                if name in saved_inputs:
                    input_listbox.selection_set(
                        index
                    )

        populate_inputs(
            saved_inputs
        )

        def discover_now():
            try:
                data = discover_obs_audio_inputs()

                populate_inputs(
                    data.get(
                        "inputs",
                        []
                    )
                )

                discovery_status_var.set(
                    (
                        "Connected to OBS — discovered "
                        +
                        str(
                            len(
                                discovered_inputs
                            )
                        )
                        +
                        " input(s)."
                    )
                )

            except Exception as exc:
                discovery_status_var.set(
                    (
                        "DISCOVERY FAILED — "
                        +
                        str(
                            exc
                        )
                    )
                )

        ttk.Button(
            inputs_frame,
            text="DISCOVER OBS AUDIO INPUTS",
            command=discover_now,
        ).pack(
            fill="x",
            pady=(
                8,
                4
            ),
        )

        ttk.Label(
            inputs_frame,
            textvariable=discovery_status_var,
            wraplength=660,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                2,
                0
            ),
        )

        monitor_frame = ttk.LabelFrame(
            outer,
            text="Level-Meter Metadata",
            padding=10,
        )

        monitor_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        monitor_frame.columnconfigure(
            1,
            weight=1
        )

        endpoint_var = tk.StringVar(
            value=saved.get(
                "monitor_endpoint",
                ""
            )
        )

        label_var = tk.StringVar(
            value=saved.get(
                "monitor_label",
                "Audio Interface"
            )
        )

        ttk.Label(
            monitor_frame,
            text="Windows endpoint",
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

        ttk.Entry(
            monitor_frame,
            textvariable=endpoint_var,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Label(
            monitor_frame,
            text="Display label",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=4,
        )

        ttk.Entry(
            monitor_frame,
            textvariable=label_var,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            pady=4,
        )

        ttk.Label(
            monitor_frame,
            text=(
                "Stored for portability now. The existing production live "
                "audio meter remains on its current proven configuration in v2.1."
            ),
            wraplength=650,
            justify="left",
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                6,
                0
            ),
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x"
        )

        buttons.columnconfigure(
            0,
            weight=1
        )
        buttons.columnconfigure(
            1,
            weight=1
        )
        buttons.columnconfigure(
            2,
            weight=1
        )

        def selected_inputs():
            return [
                str(
                    input_listbox.get(
                        index
                    )
                )
                for index in input_listbox.curselection()
            ]

        def save_values(
            *,
            show_message=False
        ):
            result = save_active_audio_settings(
                settings_source=source_var.get(),
                provider=provider_var.get(),
                mute_inputs=selected_inputs(),
                monitor_endpoint=endpoint_var.get(),
                monitor_label=label_var.get(),
            )

            self.refresh()

            if show_message:
                messagebox.showinfo(
                    "Audio Profile Saved",
                    (
                        "Audio settings saved.\n\n"
                        "Source: "
                        +
                        source_var.get().upper()
                        +
                        "\nProvider: "
                        +
                        provider_var.get()
                        +
                        "\n\nNo recording/streaming state was changed."
                    ),
                    parent=window,
                )

            return result

        def check_selected_now():
            try:
                if provider_var.get() != "OBS Audio Inputs":
                    discovery_status_var.set(
                        "Select OBS Audio Inputs to validate OBS mute targets."
                    )
                    return

                ready, detail = validate_obs_audio_inputs(
                    selected_inputs()
                )

                discovery_status_var.set(
                    (
                        "READY — "
                        if ready
                        else
                        "CHECK — "
                    )
                    +
                    str(
                        detail
                    )
                )

            except Exception as exc:
                discovery_status_var.set(
                    (
                        "CHECK FAILED — "
                        +
                        str(
                            exc
                        )
                    )
                )

        ttk.Button(
            buttons,
            text="CHECK SELECTED INPUTS",
            command=check_selected_now,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
        )

        def save_now():
            try:
                save_values(
                    show_message=True
                )

            except Exception as exc:
                messagebox.showwarning(
                    "Audio Profile",
                    str(
                        exc
                    ),
                    parent=window,
                )

        ttk.Button(
            buttons,
            text="SAVE",
            command=save_now,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=4,
        )

        ttk.Button(
            buttons,
            text="CLOSE",
            command=window.destroy,
        ).grid(
            row=0,
            column=2,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

    def open_camera_setup(
        self
    ):
        profile = load_active_profile()

        profile_name = str(
            profile.get(
                "profile_name",
                "Church Profile"
            )
        )

        saved = get_profile_camera_settings(
            profile
        )

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "SSS Camera Setup — "
            +
            profile_name
        )

        window.geometry(
            "720x690"
        )

        window.minsize(
            670,
            630,
        )

        try:
            window.transient(
                self.root
            )
        except Exception:
            pass

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
            text="CAMERA SETUP",
            font=(
                "Segoe UI",
                16,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                4
            )
        )

        ttk.Label(
            outer,
            text=(
                "Profile: "
                +
                profile_name
            ),
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                12
            )
        )

        source_var = tk.StringVar(
            value=saved.get(
                "settings_source",
                "legacy"
            )
        )

        source_frame = ttk.LabelFrame(
            outer,
            text="Configuration Source",
            padding=10,
        )

        source_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Radiobutton(
            source_frame,
            text="LEGACY — keep the current working PTZ camera configuration",
            variable=source_var,
            value="legacy",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Radiobutton(
            source_frame,
            text="PROFILE — use this church profile's camera adapter/settings",
            variable=source_var,
            value="profile",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Label(
            source_frame,
            text=(
                "LEGACY continues using the existing machine-local "
                "ptz_camera_config.json. PROFILE uses the portable settings "
                "below. The legacy camera file is never overwritten by this screen."
            ),
            wraplength=640,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                6,
                0
            ),
        )

        provider_frame = ttk.LabelFrame(
            outer,
            text="Camera Adapter",
            padding=10,
        )

        provider_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        provider_frame.columnconfigure(
            1,
            weight=1
        )

        provider_var = tk.StringVar(
            value=saved.get(
                "provider",
                "PTZOptics / HTTP-CGI"
            )
        )

        adapter_status_var = tk.StringVar()

        ttk.Label(
            provider_frame,
            text="Provider",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=5,
        )

        provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=provider_var,
            state="readonly",
            values=(
                "PTZOptics / HTTP-CGI",
                "VISCA over IP",
                "Fixed camera",
                "None",
            ),
        )

        provider_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            provider_frame,
            textvariable=adapter_status_var,
            wraplength=620,
            justify="left",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                6,
                0
            ),
        )

        def refresh_adapter_status(
            event=None
        ):
            info = camera_adapter_info(
                provider_var.get()
            )

            prefix = (
                "LIVE ADAPTER READY — "
                if info.get(
                    "live_supported"
                )
                else
                "ADAPTER PLANNED — "
            )

            adapter_status_var.set(
                prefix
                +
                str(
                    info.get(
                        "description",
                        ""
                    )
                )
            )

        provider_combo.bind(
            "<<ComboboxSelected>>",
            refresh_adapter_status,
            add="+",
        )

        refresh_adapter_status()

        connection_frame = ttk.LabelFrame(
            outer,
            text="Camera Connection / Presets",
            padding=10,
        )

        connection_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        connection_frame.columnconfigure(
            1,
            weight=1
        )

        host_var = tk.StringVar(
            value=saved.get(
                "host",
                ""
            )
        )

        port_var = tk.StringVar(
            value=str(
                saved.get(
                    "port",
                    80
                )
            )
        )

        worship_var = tk.StringVar(
            value=str(
                saved.get(
                    "worship_preset",
                    1
                )
            )
        )

        pastor_var = tk.StringVar(
            value=str(
                saved.get(
                    "pastor_preset",
                    2
                )
            )
        )

        startup_var = tk.StringVar(
            value=str(
                saved.get(
                    "startup_preset",
                    saved.get(
                        "pastor_preset",
                        2
                    )
                )
            )
        )

        auto_start_var = tk.BooleanVar(
            value=bool(
                saved.get(
                    "auto_recall_on_start",
                    True
                )
            )
        )

        fields = (
            (
                "Camera IP / host",
                host_var,
            ),
            (
                "HTTP port",
                port_var,
            ),
            (
                "Worship preset",
                worship_var,
            ),
            (
                "Pastor preset",
                pastor_var,
            ),
            (
                "Startup preset",
                startup_var,
            ),
        )

        for row, (
            label,
            variable
        ) in enumerate(
            fields
        ):
            ttk.Label(
                connection_frame,
                text=label,
            ).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(
                    0,
                    8
                ),
                pady=5,
            )

            ttk.Entry(
                connection_frame,
                textvariable=variable,
            ).grid(
                row=row,
                column=1,
                sticky="ew",
                pady=5,
            )

        ttk.Checkbutton(
            connection_frame,
            text="Recall startup preset when SSS opens",
            variable=auto_start_var,
        ).grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                6,
                2
            ),
        )

        connection_status_var = tk.StringVar(
            value=(
                "Connection check is read-only. Preset test buttons intentionally move the camera."
            )
        )

        def check_connection_now():
            if provider_var.get() != "PTZOptics / HTTP-CGI":
                connection_status_var.set(
                    "Connection check currently applies to PTZOptics / HTTP-CGI."
                )
                return

            try:
                result = check_camera_connection(
                    host_var.get(),
                    int(
                        port_var.get()
                    ),
                    timeout=2.0,
                )

                connection_status_var.set(
                    (
                        "REACHABLE — "
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
                                80
                            )
                        )
                    )
                )

            except Exception as exc:
                connection_status_var.set(
                    (
                        "CONNECTION FAILED — "
                        +
                        str(
                            exc
                        )
                    )
                )

        ttk.Button(
            connection_frame,
            text="CHECK CAMERA CONNECTION",
            command=check_connection_now,
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(
                8,
                4
            ),
        )

        ttk.Label(
            connection_frame,
            textvariable=connection_status_var,
            wraplength=620,
            justify="left",
        ).grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                4,
                0
            ),
        )

        test_frame = ttk.Frame(
            outer
        )

        test_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        test_frame.columnconfigure(
            0,
            weight=1
        )
        test_frame.columnconfigure(
            1,
            weight=1
        )

        def save_profile_values(
            *,
            show_message=False
        ):
            profile_saved = save_active_camera_settings(
                settings_source=source_var.get(),
                provider=provider_var.get(),
                host=host_var.get(),
                port=port_var.get(),
                worship_preset=worship_var.get(),
                pastor_preset=pastor_var.get(),
                startup_preset=startup_var.get(),
                auto_recall_on_start=auto_start_var.get(),
            )

            self.refresh()

            if show_message:
                messagebox.showinfo(
                    "Camera Profile Saved",
                    (
                        "Camera settings saved.\n\n"
                        "Source: "
                        +
                        source_var.get().upper()
                        +
                        "\nProvider: "
                        +
                        provider_var.get()
                        +
                        "\n\nThe existing legacy PTZ configuration file was not changed."
                    ),
                    parent=window,
                )

            return profile_saved

        def test_preset(
            which
        ):
            if (
                source_var.get()
                !=
                "profile"
                or
                provider_var.get()
                !=
                "PTZOptics / HTTP-CGI"
            ):
                messagebox.showwarning(
                    "Camera Test",
                    (
                        "Preset tests require PROFILE + PTZOptics / HTTP-CGI.\n\n"
                        "The test button intentionally moves the camera."
                    ),
                    parent=window,
                )
                return

            try:
                # Save the exact values visible in the dialog so the adapter
                # test uses those same profile settings.
                save_profile_values(
                    show_message=False
                )

                preset = (
                    int(
                        worship_var.get()
                    )
                    if which == "worship"
                    else
                    int(
                        pastor_var.get()
                    )
                )

                test_profile_camera_preset(
                    preset
                )

                connection_status_var.set(
                    (
                        "CAMERA MOVED — "
                        +
                        which.title()
                        +
                        " preset "
                        +
                        str(
                            preset
                        )
                    )
                )

            except Exception as exc:
                connection_status_var.set(
                    (
                        "CAMERA TEST FAILED — "
                        +
                        str(
                            exc
                        )
                    )
                )

        ttk.Button(
            test_frame,
            text="TEST WORSHIP VIEW",
            command=lambda:
                test_preset(
                    "worship"
                ),
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
            test_frame,
            text="TEST PASTOR VIEW",
            command=lambda:
                test_preset(
                    "pastor"
                ),
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
            outer,
            text=(
                "PROFILE + Fixed camera or None automatically removes the CAMERA VIEW row "
                "from the volunteer dashboard. VISCA over IP is recognized but cannot be "
                "activated as PROFILE until that adapter is implemented."
            ),
            wraplength=640,
            justify="left",
        ).pack(
            fill="x",
            pady=(
                2,
                10
            ),
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x"
        )

        buttons.columnconfigure(
            0,
            weight=1
        )
        buttons.columnconfigure(
            1,
            weight=1
        )

        def save_now():
            try:
                save_profile_values(
                    show_message=True
                )

            except Exception as exc:
                messagebox.showwarning(
                    "Camera Profile",
                    str(
                        exc
                    ),
                    parent=window,
                )

        ttk.Button(
            buttons,
            text="SAVE",
            command=save_now,
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
            text="CLOSE",
            command=window.destroy,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

    def open_presentation_setup(
        self
    ):
        profile = load_active_profile()

        profile_name = str(
            profile.get(
                "profile_name",
                "Church Profile"
            )
        )

        saved = get_profile_presentation_settings(
            profile
        )

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "SSS Presentation Setup — "
            +
            profile_name
        )

        window.geometry(
            "720x590"
        )

        window.minsize(
            670,
            540,
        )

        try:
            window.transient(
                self.root
            )
        except Exception:
            pass

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
            text="PRESENTATION SETUP",
            font=(
                "Segoe UI",
                16,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                4
            )
        )

        ttk.Label(
            outer,
            text=(
                "Profile: "
                +
                profile_name
            ),
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                12
            )
        )

        source_var = tk.StringVar(
            value=saved.get(
                "settings_source",
                "legacy"
            )
        )

        source_frame = ttk.LabelFrame(
            outer,
            text="Configuration Source",
            padding=10,
        )

        source_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        ttk.Radiobutton(
            source_frame,
            text="LEGACY — keep the current working SSS presentation behavior",
            variable=source_var,
            value="legacy",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Radiobutton(
            source_frame,
            text="PROFILE — route presentation actions through the selected adapter",
            variable=source_var,
            value="profile",
        ).pack(
            anchor="w",
            pady=2,
        )

        provider_frame = ttk.LabelFrame(
            outer,
            text="Presentation Adapter",
            padding=10,
        )

        provider_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        provider_frame.columnconfigure(
            1,
            weight=1
        )

        provider_var = tk.StringVar(
            value=saved.get(
                "provider",
                "WorshipTools Presenter"
            )
        )

        status_var = tk.StringVar()

        ttk.Label(
            provider_frame,
            text="Provider",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                10
            ),
            pady=5,
        )

        provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=provider_var,
            state="readonly",
            values=(
                "WorshipTools Presenter",
                "ProPresenter",
                "Bitfocus Companion",
                "PowerPoint / Keyboard",
                "None",
            ),
        )

        provider_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            provider_frame,
            textvariable=status_var,
            wraplength=630,
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

        def refresh_status(
            event=None
        ):
            info = adapter_info(
                provider_var.get()
            )

            status = (
                "LIVE ADAPTER READY — "
                if info.get(
                    "live_supported"
                )
                else
                "ADAPTER PLANNED — "
            )

            status += str(
                info.get(
                    "description",
                    ""
                )
            )

            status_var.set(
                status
            )

        provider_combo.bind(
            "<<ComboboxSelected>>",
            refresh_status,
            add="+",
        )

        refresh_status()

        connection_frame = ttk.LabelFrame(
            outer,
            text="ProPresenter API Connection",
            padding=10,
        )

        connection_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        connection_frame.columnconfigure(
            1,
            weight=1
        )

        host_var = tk.StringVar(
            value=saved.get(
                "host",
                "127.0.0.1"
            )
        )

        port_var = tk.StringVar(
            value=str(
                saved.get(
                    "port",
                    50001
                )
            )
        )

        ttk.Label(
            connection_frame,
            text="Host / IP",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=5,
        )

        ttk.Entry(
            connection_frame,
            textvariable=host_var,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            connection_frame,
            text="API port",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=5,
        )

        ttk.Entry(
            connection_frame,
            textvariable=port_var,
            width=12,
        ).grid(
            row=1,
            column=1,
            sticky="w",
            pady=5,
        )

        connection_status_var = tk.StringVar(
            value=(
                "Default: 127.0.0.1:50001. "
                "Use the ProPresenter PC's IP when it is on another computer."
            )
        )

        def test_connection_now():
            if provider_var.get() != "ProPresenter":
                connection_status_var.set(
                    "Select ProPresenter to test its API connection."
                )
                return

            try:
                result = test_propresenter_connection(
                    host_var.get(),
                    int(
                        port_var.get()
                    ),
                    timeout=3.0,
                )

                connection_status_var.set(
                    (
                        "CONNECTED — "
                        +
                        str(
                            result.get(
                                "base_url",
                                ""
                            )
                        )
                        +
                        " — version response: "
                        +
                        str(
                            result.get(
                                "version",
                                {}
                            )
                        )
                    )
                )

            except Exception as exc:
                connection_status_var.set(
                    (
                        "CONNECTION FAILED — "
                        +
                        str(
                            exc
                        )
                    )
                )

        ttk.Button(
            connection_frame,
            text="CHECK PROPRESENTER CONNECTION",
            command=test_connection_now,
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(
                8,
                5
            ),
        )

        ttk.Label(
            connection_frame,
            textvariable=connection_status_var,
            wraplength=630,
            justify="left",
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                4,
                0
            ),
        )

        ttk.Label(
            outer,
            text=(
                "v1.7 supports live PROFILE control for WorshipTools Presenter "
                "and ProPresenter. ProPresenter uses its direct API, so it does "
                "not need keyboard focus or MIDI. Companion and PowerPoint "
                "remain planned adapters."
            ),
            wraplength=650,
            justify="left",
        ).pack(
            fill="x",
            pady=(
                4,
                12
            ),
        )

        buttons = ttk.Frame(
            outer
        )

        buttons.pack(
            fill="x"
        )

        buttons.columnconfigure(
            0,
            weight=1
        )
        buttons.columnconfigure(
            1,
            weight=1
        )

        def save_now():
            try:
                save_active_presentation_settings(
                    settings_source=source_var.get(),
                    provider=provider_var.get(),
                    host=host_var.get(),
                    port=port_var.get(),
                )

                self.refresh()

                messagebox.showinfo(
                    "Presentation Profile Saved",
                    (
                        "Presentation settings saved.\n\n"
                        "Source: "
                        +
                        source_var.get().upper()
                        +
                        "\nProvider: "
                        +
                        provider_var.get()
                    ),
                    parent=window,
                )

            except Exception as exc:
                messagebox.showwarning(
                    "Presentation Profile",
                    str(
                        exc
                    ),
                    parent=window,
                )

        ttk.Button(
            buttons,
            text="SAVE",
            command=save_now,
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
            text="CLOSE",
            command=window.destroy,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

    def open_obs_setup(
        self
    ):
        profile = load_active_profile()
        profile_name = str(
            profile.get(
                "profile_name",
                "Church Profile"
            )
        )

        saved = get_profile_obs_settings(
            profile
        )

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "SSS OBS Setup — "
            +
            profile_name
        )

        window.geometry(
            "760x650"
        )

        window.minsize(
            700,
            610,
        )

        try:
            window.transient(
                self.root
            )
        except Exception:
            pass

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
            text="OBS SETUP",
            font=(
                "Segoe UI",
                16,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                4
            )
        )

        ttk.Label(
            outer,
            text=(
                "Profile: "
                +
                profile_name
            ),
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
        ).pack(
            pady=(
                0,
                12
            )
        )

        source_frame = ttk.LabelFrame(
            outer,
            text="Configuration Source",
            padding=10,
        )

        source_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        source_var = tk.StringVar(
            value=saved.get(
                "settings_source",
                "legacy"
            )
        )

        ttk.Radiobutton(
            source_frame,
            text="LEGACY — use the current working SSS / OBS settings",
            variable=source_var,
            value="legacy",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Radiobutton(
            source_frame,
            text="PROFILE — use the scene collection and scene mappings below",
            variable=source_var,
            value="profile",
        ).pack(
            anchor="w",
            pady=2,
        )

        ttk.Label(
            source_frame,
            text=(
                "LEGACY is the safe fallback. PROFILE must be selected and "
                "saved intentionally. OBS WebSocket credentials stay local "
                "on this PC and are never exported in the .sssprofile file."
            ),
            wraplength=680,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                6,
                0
            ),
        )

        discovery_frame = ttk.LabelFrame(
            outer,
            text="Automatic OBS Discovery",
            padding=10,
        )

        discovery_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        discovery_status_var = tk.StringVar(
            value="Open OBS, then click CONNECT & DISCOVER."
        )

        ttk.Button(
            discovery_frame,
            text="CONNECT & DISCOVER OBS",
            command=lambda: discover_now(),
        ).pack(
            fill="x"
        )

        ttk.Label(
            discovery_frame,
            textvariable=discovery_status_var,
            wraplength=680,
            justify="left",
        ).pack(
            fill="x",
            pady=(
                7,
                0
            ),
        )

        mapping_frame = ttk.LabelFrame(
            outer,
            text="Profile OBS Mapping",
            padding=10,
        )

        mapping_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )

        mapping_frame.columnconfigure(
            1,
            weight=1,
        )

        collection_var = tk.StringVar(
            value=saved.get(
                "scene_collection",
                ""
            )
        )
        normal_var = tk.StringVar(
            value=saved.get(
                "normal_scene",
                ""
            )
        )
        scripture_var = tk.StringVar(
            value=saved.get(
                "scripture_scene",
                ""
            )
        )
        sermon_var = tk.StringVar(
            value=saved.get(
                "sermon_scene",
                ""
            )
        )

        ttk.Label(
            mapping_frame,
            text="Scene collection",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=5,
        )

        collection_combo = ttk.Combobox(
            mapping_frame,
            textvariable=collection_var,
            state="readonly",
        )
        collection_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            mapping_frame,
            text="Normal / webcam scene",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=5,
        )

        normal_combo = ttk.Combobox(
            mapping_frame,
            textvariable=normal_var,
            state="readonly",
        )
        normal_combo.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            mapping_frame,
            text="Scripture / presentation scene",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=5,
        )

        scripture_combo = ttk.Combobox(
            mapping_frame,
            textvariable=scripture_var,
            state="readonly",
        )
        scripture_combo.grid(
            row=2,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            mapping_frame,
            text="Main / sermon scene (optional)",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=5,
        )

        sermon_combo = ttk.Combobox(
            mapping_frame,
            textvariable=sermon_var,
            state="readonly",
        )
        sermon_combo.grid(
            row=3,
            column=1,
            sticky="ew",
            pady=5,
        )

        ttk.Label(
            mapping_frame,
            text=(
                "In PROFILE mode SSS currently uses Normal and Scripture "
                "for the Scripture transition. Main / sermon is saved now "
                "for later portable-workflow steps."
            ),
            wraplength=680,
            justify="left",
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                7,
                0
            ),
        )

        test_frame = ttk.Frame(
            outer
        )
        test_frame.pack(
            fill="x",
            pady=(
                0,
                10
            ),
        )
        test_frame.columnconfigure(
            0,
            weight=1
        )
        test_frame.columnconfigure(
            1,
            weight=1
        )

        def test_scene(
            scene_var,
            label
        ):
            scene = str(
                scene_var.get()
                or
                ""
            ).strip()

            if not scene:
                messagebox.showwarning(
                    "OBS Setup",
                    (
                        "Choose the "
                        +
                        label
                        +
                        " scene first."
                    ),
                    parent=window,
                )
                return

            try:
                test_profile_preview_scene(
                    scene
                )

                messagebox.showinfo(
                    "OBS Preview Test",
                    (
                        scene
                        +
                        " was loaded into OBS Preview only.\n\n"
                        "Nothing was transitioned to Program."
                    ),
                    parent=window,
                )

            except Exception as exc:
                messagebox.showwarning(
                    "OBS Preview Test",
                    str(
                        exc
                    ),
                    parent=window,
                )

        ttk.Button(
            test_frame,
            text="TEST NORMAL IN PREVIEW",
            command=lambda: test_scene(
                normal_var,
                "Normal / webcam"
            ),
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
            test_frame,
            text="TEST SCRIPTURE IN PREVIEW",
            command=lambda: test_scene(
                scripture_var,
                "Scripture / presentation"
            ),
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

        discovered_at = saved.get(
            "discovered_at",
            ""
        )

        def choose_guess(
            scenes,
            current_value,
            preferred
        ):
            current_value = str(
                current_value
                or
                ""
            ).strip()

            if current_value in scenes:
                return current_value

            lowered = {
                scene.lower(): scene
                for scene in scenes
            }

            for candidate in preferred:
                if candidate.lower() in lowered:
                    return lowered[
                        candidate.lower()
                    ]

            for candidate in preferred:
                token = candidate.lower()

                for scene in scenes:
                    if token in scene.lower():
                        return scene

            return current_value

        def discover_now():
            nonlocal discovered_at

            discovery_status_var.set(
                "Connecting to OBS..."
            )
            window.update_idletasks()

            try:
                data = discover_obs()

                collections = tuple(
                    data.get(
                        "collections",
                        []
                    )
                )
                scenes = tuple(
                    data.get(
                        "scenes",
                        []
                    )
                )

                collection_combo.configure(
                    values=collections
                )
                normal_combo.configure(
                    values=scenes
                )
                scripture_combo.configure(
                    values=scenes
                )
                sermon_combo.configure(
                    values=scenes
                )

                current_collection = str(
                    data.get(
                        "current_collection",
                        ""
                    )
                )

                saved_collection = str(
                    collection_var.get()
                    or
                    ""
                )

                legacy_collection = str(
                    data.get(
                        "legacy_collection",
                        ""
                    )
                )

                if saved_collection in collections:
                    collection_var.set(
                        saved_collection
                    )
                elif legacy_collection in collections:
                    collection_var.set(
                        legacy_collection
                    )
                elif current_collection:
                    collection_var.set(
                        current_collection
                    )
                elif collections:
                    collection_var.set(
                        collections[0]
                    )

                normal_var.set(
                    choose_guess(
                        scenes,
                        normal_var.get(),
                        [
                            "webcam only",
                            "camera only",
                            "normal camera",
                            "camera",
                        ],
                    )
                )

                scripture_var.set(
                    choose_guess(
                        scenes,
                        scripture_var.get(),
                        [
                            "webcam TP",
                            "ProPresenter",
                            "Presenter",
                            "Scripture",
                            "Presentation",
                        ],
                    )
                )

                current_program = str(
                    data.get(
                        "current_program_scene",
                        ""
                    )
                )

                if (
                    not sermon_var.get()
                    and
                    current_program in scenes
                ):
                    sermon_var.set(
                        current_program
                    )

                discovered_at = str(
                    data.get(
                        "discovered_at",
                        ""
                    )
                )

                discovery_status_var.set(
                    (
                        "Connected to "
                        +
                        str(
                            data.get(
                                "host",
                                "localhost"
                            )
                        )
                        +
                        ":"
                        +
                        str(
                            data.get(
                                "port",
                                4455
                            )
                        )
                        +
                        " — collection: "
                        +
                        (
                            current_collection
                            or
                            "unknown"
                        )
                        +
                        " — discovered "
                        +
                        str(
                            len(
                                scenes
                            )
                        )
                        +
                        " scene(s)."
                    )
                )

            except Exception as exc:
                discovery_status_var.set(
                    (
                        "OBS discovery failed: "
                        +
                        str(
                            exc
                        )
                    )
                )

        def save_now():
            try:
                saved_profile = save_active_obs_settings(
                    settings_source=source_var.get(),
                    scene_collection=collection_var.get(),
                    normal_scene=normal_var.get(),
                    scripture_scene=scripture_var.get(),
                    sermon_scene=sermon_var.get(),
                    discovered_at=discovered_at,
                )

                self.refresh()

                mode = source_var.get().upper()

                messagebox.showinfo(
                    "OBS Profile Saved",
                    (
                        "OBS settings saved to:\n\n"
                        +
                        str(
                            saved_profile.get(
                                "profile_name",
                                "Church Profile"
                            )
                        )
                        +
                        "\n\nConfiguration source: "
                        +
                        mode
                        +
                        (
                            "\n\nCurrent Perry behavior remains on the legacy "
                            "path."
                            if mode == "LEGACY"
                            else
                            "\n\nSSS will use the profile scene mappings. If a "
                            "profile scene cannot be loaded, SSS falls back "
                            "to the legacy OBS hotkey for that action."
                        )
                    ),
                    parent=window,
                )

            except Exception as exc:
                messagebox.showwarning(
                    "OBS Profile Save",
                    str(
                        exc
                    ),
                    parent=window,
                )

        bottom = ttk.Frame(
            outer
        )
        bottom.pack(
            fill="x",
            side="bottom",
        )
        bottom.columnconfigure(
            0,
            weight=1
        )
        bottom.columnconfigure(
            1,
            weight=1
        )

        ttk.Button(
            bottom,
            text="SAVE OBS SETTINGS",
            command=save_now,
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
            bottom,
            text="CLOSE",
            command=window.destroy,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

    def new_profile(
        self
    ):
        dialog = tk.Toplevel(
            self.root
        )

        dialog.title(
            "New SSS Profile"
        )

        dialog.resizable(
            False,
            False,
        )

        frame = ttk.Frame(
            dialog,
            padding=14,
        )

        frame.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            frame,
            text="Church / Profile name",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(
                0,
                8
            ),
            pady=6,
        )

        name_var = tk.StringVar()

        entry = ttk.Entry(
            frame,
            textvariable=name_var,
            width=38,
        )

        entry.grid(
            row=0,
            column=1,
            sticky="ew",
            pady=6,
        )

        ttk.Label(
            frame,
            text=(
                "New profiles start in compatibility mode. "
                "No live Sunday settings are changed."
            ),
            wraplength=400,
            justify="left",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(
                6,
                12
            ),
        )

        def create_now():
            try:
                profile = create_profile(
                    name_var.get(),
                    make_active=True,
                )

                dialog.destroy()
                self.refresh()

                # A brand-new church profile immediately enters first-run
                # setup. The wizard is non-destructive and never starts
                # recording or streaming.
                self.root.after(
                    150,
                    self.open_setup_wizard,
                )

                messagebox.showinfo(
                    "Profile Created",
                    (
                        "Created and selected:\\n\\n"
                        +
                        str(
                            profile.get(
                                "profile_name",
                                "Church Profile"
                            )
                        )
                    ),
                )

            except Exception as exc:
                messagebox.showerror(
                    "Profile Creation Failed",
                    str(
                        exc
                    ),
                )

        ttk.Button(
            frame,
            text="CREATE & SELECT",
            command=create_now,
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=(
                0,
                4
            ),
        )

        ttk.Button(
            frame,
            text="CANCEL",
            command=dialog.destroy,
        ).grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(
                4,
                0
            ),
        )

        frame.columnconfigure(
            1,
            weight=1
        )

        entry.focus_set()

        dialog.bind(
            "<Return>",
            lambda event:
                create_now(),
        )

        dialog.bind(
            "<Escape>",
            lambda event:
                dialog.destroy(),
        )

    def export_profile(
        self
    ):
        profile = load_active_profile()

        initial = (
            str(
                profile.get(
                    "profile_name",
                    "Church Profile"
                )
            )
            .replace(
                " ",
                "_"
            )
            +
            ".sssprofile"
        )

        destination = filedialog.asksaveasfilename(
            title="Export SSS Profile",
            defaultextension=".sssprofile",
            filetypes=[
                (
                    "Sunday Service System Profile",
                    "*.sssprofile",
                ),
            ],
            initialfile=initial,
        )

        if not destination:
            return

        path = export_active_profile(
            destination
        )

        messagebox.showinfo(
            "Profile Exported",
            (
                "Profile exported successfully.\n\n"
                +
                str(
                    path
                )
                +
                "\n\nNo passwords, tokens, or credentials were included."
            ),
        )

    def import_profile_file(
        self
    ):
        source = filedialog.askopenfilename(
            title="Import SSS Profile",
            filetypes=[
                (
                    "Sunday Service System Profile",
                    "*.sssprofile",
                ),
                (
                    "JSON",
                    "*.json",
                ),
            ],
        )

        if not source:
            return

        try:
            profile = import_profile(
                source
            )

        except Exception as exc:
            messagebox.showerror(
                "Profile Import Failed",
                str(
                    exc
                ),
            )

            return

        self.refresh()

        messagebox.showinfo(
            "Profile Imported",
            (
                "Active profile is now:\n\n"
                +
                str(
                    profile.get(
                        "profile_name",
                        "Church Profile"
                    )
                )
                +
                "\n\nVersion 1 remains compatibility-only, so the existing "
                "Sunday configuration is still controlling the live system."
            ),
        )

    def open_folder(
        self
    ):
        path = profile_root()

        try:
            os.startfile(
                str(
                    path
                )
            )
        except Exception:
            subprocess.Popen(
                [
                    "explorer.exe",
                    str(
                        path
                    ),
                ]
            )


def main():
    set_windows_app_user_model_id()

    root = tk.Tk()

    ProfileManager(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()
