import tkinter as tk
from tkinter import messagebox, ttk

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
    def __init__(self, parent, on_saved=None):
        self.parent = parent
        self.on_saved = on_saved
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

        self.discovery_status_var = tk.StringVar(
            value="Open OBS, then click CONNECT & DISCOVER."
        )
        self.review_var = tk.StringVar()
        self.progress_var = tk.StringVar()
        self.obs_combos = []

        self.window = tk.Toplevel(parent)
        self.window.title("Sunday Service System — Setup Wizard")
        self.window.geometry("820x690")
        self.window.minsize(760, 640)

        try:
            self.window.transient(parent)
        except Exception:
            pass

        self.current_step = 0
        self.build()
        self.show_step(0)

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

        self.pages = [
            self.build_welcome(),
            self.build_church(),
            self.build_obs(),
            self.build_integrations(),
            self.build_review(),
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

        ttk.Label(
            page,
            text=(
                "This wizard builds the portable configuration for this "
                "church profile. It never starts recording or streaming, "
                "and Legacy behavior remains available as a fallback."
            ),
            wraplength=720,
            justify="left",
        ).pack(anchor="w", fill="x")

        ttk.Label(
            page,
            text=f"Current setup: {status['completed']}/{status['total']} complete",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(18, 8))

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

        ttk.Label(
            page,
            text=(
                "This travels with the profile instead of being hard-coded "
                "into the SSS application."
            ),
            wraplength=700,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 0))

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
            text="LEGACY — keep current working SSS / OBS behavior",
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
        if self.current_step == 1 and not self.church_name_var.get().strip():
            messagebox.showwarning(
                "SSS Setup",
                "Church name is required.",
                parent=self.window,
            )
            return False

        if self.current_step == 2 and self.obs_source_var.get() == "profile":
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

        self.review_var.set(
            "Church: " + self.church_name_var.get().strip()
            + "\n\nOBS: " + obs_mode + " — " + obs_detail
            + "\n\nPresentation: " + self.presentation_var.get()
            + "\n\nCamera: " + self.camera_var.get()
            + "\n\nSermon information: " + self.sermon_source_var.get()
            + "\n\nFINISH & SAVE writes profile setup only. "
              "It never starts recording or streaming."
        )

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

            status = get_profile_setup_status()

            if callable(self.on_saved):
                try:
                    self.on_saved()
                except Exception:
                    pass

            messagebox.showinfo(
                "SSS Setup Complete",
                f"Profile setup saved.\n\n"
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


def open_setup_wizard(parent, on_saved=None):
    return SetupWizard(parent, on_saved=on_saved)
