"""
First-run orchestration: shown only when sunday_config.json does not
exist yet (a brand-new install for a new church). Handles Tk-level
sequencing only - the actual config file is built by
sss_config_bootstrap.py and the wizard UI lives in sss_setup_wizard.py.
"""

import tkinter as tk
from tkinter import simpledialog, messagebox


def _center_on_screen(window, width=1, height=1):
    window.update_idletasks()
    x = max(0, (window.winfo_screenwidth() - width) // 2)
    y = max(0, (window.winfo_screenheight() - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")


def _ask_church_name(root):
    # root must stay mapped (not withdrawn) here, or the dialog it parents
    # inherits an off-screen/unfocused position and never becomes visible.
    _center_on_screen(root)
    root.deiconify()
    root.lift()
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    root.focus_force()

    name = simpledialog.askstring(
        "Sunday Service System - First-Time Setup",
        (
            "Welcome! It looks like this is a brand-new install.\n\n"
            "What is the name of your church?"
        ),
        parent=root,
    )

    if name:
        name = " ".join(name.split())

    return name or ""


def run_first_run_setup(root):
    """
    Returns True if setup completed and sunday_config.json now exists,
    False if the user cancelled (caller should exit cleanly).
    """
    from sss_profile import active_profile_pointer, create_profile
    from sss_setup_wizard import open_setup_wizard
    from sss_config_bootstrap import CONFIG_PATH

    if not active_profile_pointer().exists():
        church_name = _ask_church_name(root)

        if not church_name:
            return False

        try:
            create_profile(church_name, make_active=True)
        except Exception as exc:
            messagebox.showerror(
                "Setup Failed",
                f"Could not create a new church profile:\n\n{exc}",
                parent=root,
            )
            return False

    # The wizard itself is not transient to root during first_run (see
    # SetupWizard.__init__), so root can go back to being fully hidden.
    root.withdraw()

    completed = {"ok": False}

    def _on_saved():
        completed["ok"] = True

    wizard = open_setup_wizard(root, on_saved=_on_saved, first_run=True)
    root.wait_window(wizard.window)

    ok = completed["ok"] and CONFIG_PATH.exists()

    if ok:
        # main() proceeds to build SundayModeApp(root) right after this -
        # root must be visible again for that window to actually show.
        root.deiconify()

    return ok
