import argparse
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import (
    messagebox,
    ttk,
)

from sss_build_info import APP_VERSION
from sss_runtime import application_install_root
from sss_updater_core import (
    apply_update,
    read_update_manifest,
    rollback_last_update,
    verify_update_package,
)


class UpdaterWindow:
    def __init__(
        self,
        root,
        args
    ):
        self.root = root
        self.args = args

        self.root.title(
            "Sunday Service System — Updater"
        )

        self.root.geometry(
            "720x430"
        )

        self.root.minsize(
            650,
            390,
        )

        self.status_var = tk.StringVar(
            value="Preparing update…"
        )

        self.detail_var = tk.StringVar(
            value=(
                "SSS Updater never starts or stops Recording/Streaming."
            )
        )

        self.progress_var = tk.DoubleVar(
            value=0
        )

        self._build_ui()

        self.root.after(
            250,
            self.start_operation,
        )

    def _build_ui(
        self
    ):
        outer = ttk.Frame(
            self.root,
            padding=18,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            outer,
            text="SUNDAY SERVICE SYSTEM UPDATER",
            font=(
                "Segoe UI",
                17,
                "bold"
            ),
        ).pack(
            anchor="w"
        )

        ttk.Label(
            outer,
            text=(
                "Application updates are isolated from church profiles, "
                "credentials, sermon plans, PTZ settings, recordings, and media."
            ),
            wraplength=670,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                4,
                14
            ),
        )

        status_frame = ttk.LabelFrame(
            outer,
            text="Update Status",
            padding=12,
        )

        status_frame.pack(
            fill="x",
            pady=(
                0,
                12
            ),
        )

        ttk.Label(
            status_frame,
            textvariable=self.status_var,
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            wraplength=640,
            justify="left",
        ).pack(
            anchor="w"
        )

        ttk.Label(
            status_frame,
            textvariable=self.detail_var,
            wraplength=640,
            justify="left",
        ).pack(
            anchor="w",
            pady=(
                6,
                0
            ),
        )

        self.progress = ttk.Progressbar(
            outer,
            variable=self.progress_var,
            maximum=100,
            mode="indeterminate",
        )

        self.progress.pack(
            fill="x",
            pady=(
                0,
                12
            ),
        )

        self.progress.start(
            12
        )

        ttk.Label(
            outer,
            text=(
                "Live-service safety: the updater refuses to proceed while OBS "
                "Recording or Streaming is active. If OBS is running but its output "
                "state cannot be verified, the updater also refuses to proceed."
            ),
            wraplength=670,
            justify="left",
        ).pack(
            anchor="w"
        )

        self.close_button = ttk.Button(
            outer,
            text="CLOSE",
            command=self.root.destroy,
            state="disabled",
        )

        self.close_button.pack(
            fill="x",
            side="bottom",
            pady=(
                12,
                0
            ),
        )

        try:
            self.root.protocol(
                "WM_DELETE_WINDOW",
                self._close_requested,
            )
        except Exception:
            pass

    def _close_requested(
        self
    ):
        if str(
            self.close_button.cget(
                "state"
            )
        ) == "disabled":
            messagebox.showinfo(
                "SSS Updater",
                (
                    "The update/rollback operation is still running. "
                    "Wait for it to finish before closing this window."
                ),
                parent=self.root,
            )

            return

        self.root.destroy()

    def set_status(
        self,
        message
    ):
        self.root.after(
            0,
            lambda:
                self.status_var.set(
                    str(
                        message
                    )
                ),
        )

    def start_operation(
        self
    ):
        threading.Thread(
            target=self._run_operation,
            daemon=True,
        ).start()

    def _run_operation(
        self
    ):
        try:
            install_root = Path(
                self.args.install_root
                or
                application_install_root()
            )

            if self.args.apply:
                package = Path(
                    self.args.apply
                )

                manifest = read_update_manifest(
                    package
                )

                self.root.after(
                    0,
                    lambda:
                        self.detail_var.set(
                            (
                                "Installing "
                                +
                                str(
                                    manifest.get(
                                        "version",
                                        "update"
                                    )
                                )
                                +
                                " to "
                                +
                                str(
                                    install_root
                                )
                                +
                                "."
                            )
                        ),
                )

                state = apply_update(
                    package_path=package,
                    install_root=install_root,
                    current_version=(
                        self.args.current_version
                        or
                        APP_VERSION
                    ),
                    parent_pid=self.args.parent_pid,
                    allow_same_version=bool(
                        self.args.allow_same_version
                    ),
                    progress=self.set_status,
                )

            elif self.args.rollback_last:
                self.root.after(
                    0,
                    lambda:
                        self.detail_var.set(
                            (
                                "Restoring the previous installed application "
                                "version from the most recent rollback backup."
                            )
                        ),
                )

                state = rollback_last_update(
                    install_root=install_root,
                    parent_pid=self.args.parent_pid,
                    progress=self.set_status,
                )

            elif self.args.verify:
                self.set_status(
                    "Verifying update package…"
                )

                manifest = verify_update_package(
                    self.args.verify
                )

                state = {
                    "status": "VERIFIED",
                    "detail": (
                        "Package verified successfully: "
                        +
                        str(
                            manifest.get(
                                "version",
                                ""
                            )
                        )
                    ),
                }

            else:
                raise RuntimeError(
                    "No updater operation was requested."
                )

            self.root.after(
                0,
                lambda:
                    self._finish(
                        state,
                        None,
                    ),
            )

        except Exception as exc:
            self.root.after(
                0,
                lambda:
                    self._finish(
                        None,
                        str(
                            exc
                        ),
                    ),
            )

    def _finish(
        self,
        state,
        error
    ):
        try:
            self.progress.stop()
        except Exception:
            pass

        self.progress_var.set(
            100
        )

        self.close_button.configure(
            state="normal"
        )

        if error:
            self.status_var.set(
                "UPDATE STOPPED / FAILED"
            )

            self.detail_var.set(
                error
            )

            messagebox.showwarning(
                "SSS Updater",
                error,
                parent=self.root,
            )

            return

        status = str(
            state.get(
                "status",
                "SUCCESS"
            )
        ).upper()

        detail = str(
            state.get(
                "detail",
                ""
            )
        )

        if status == "SUCCESS":
            self.status_var.set(
                "SUCCESS"
            )

            self.detail_var.set(
                (
                    detail
                    +
                    "\n\nSSS Setup & Settings will reopen to the Updates page."
                )
            )

        elif status == "ROLLED_BACK":
            self.status_var.set(
                "UPDATE FAILED — AUTOMATIC ROLLBACK SUCCEEDED"
            )

            self.detail_var.set(
                detail
            )

            messagebox.showwarning(
                "SSS Automatic Rollback",
                (
                    "The new version did not pass update verification, so "
                    "Sunday Service System automatically restored the previous "
                    "installed application.\n\n"
                    +
                    detail
                ),
                parent=self.root,
            )

        elif status == "ROLLED_BACK_ROLLBACK":
            self.status_var.set(
                "ROLLBACK CANCELLED SAFELY"
            )

            self.detail_var.set(
                detail
            )

        elif status == "VERIFIED":
            self.status_var.set(
                "UPDATE PACKAGE VERIFIED"
            )

            self.detail_var.set(
                detail
            )

        else:
            self.status_var.set(
                status
            )

            self.detail_var.set(
                detail
            )


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Sunday Service System external updater/rollback helper."
        )
    )

    parser.add_argument(
        "--apply",
        help="Path to a .sssupdate package.",
    )

    parser.add_argument(
        "--verify",
        help="Verify a .sssupdate package without installing it.",
    )

    parser.add_argument(
        "--rollback-last",
        action="store_true",
        help="Restore the previous application backup.",
    )

    parser.add_argument(
        "--install-root",
        help="Installed Sunday Service System root.",
    )

    parser.add_argument(
        "--current-version",
        default="",
        help="Current installed application version.",
    )

    parser.add_argument(
        "--parent-pid",
        type=int,
        default=0,
        help="Settings process PID to wait for before replacing files.",
    )

    parser.add_argument(
        "--allow-same-version",
        action="store_true",
        help="Developer/testing only.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    root = tk.Tk()

    UpdaterWindow(
        root,
        args
    )

    root.mainloop()


if __name__ == "__main__":
    main()
