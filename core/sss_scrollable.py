# -*- coding: utf-8 -*-
"""Shared vertical-scroll-fallback helper for the SSS Settings and Sunday
Mode Tkinter GUIs.

Extracted from the scrollable Canvas+Scrollbar pattern already shipped
inside sunday_mode.py's Admin panel (Canvas + ttk.Scrollbar + inner Frame
via create_window, <Configure>-driven scrollregion sync, <Enter>/<Leave>-
scoped mouse-wheel binding) so both apps get the same proven mechanism
instead of a second, different implementation.

Windows-only: mouse-wheel handling uses the Windows <MouseWheel>/
event.delta convention only, matching how both apps already gate other
platform-specific behavior on os.name == "nt".
"""

import tkinter as tk
from tkinter import ttk


def add_vertical_scroll(parent, *, stretch_width=True, inner_padding=0):
    """Turn parent into a scrollable region; return (canvas, inner_frame).

    parent must be empty - this grids a Canvas + vertical Scrollbar into
    it. Callers build UI onto the returned inner frame exactly as they
    would onto any plain ttk.Frame.

    stretch_width=True: the inner frame's width tracks the canvas's
    width, so content uses the full available width (a Settings page,
    the Sunday Mode dashboard body).

    stretch_width=False: the inner frame keeps its own natural width and
    the canvas is sized to match it, so only vertical scrolling applies
    (a fixed-width column such as the Settings nav sidebar).
    """
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)

    # tk.Canvas defaults to a "10c x 7c" (~378x265px) requested size
    # when unset, which can force a grid cell wider/taller than intended
    # before layout settles. Explicit width=1/height=1 avoids that; the
    # geometry stretch below (sticky="nsew" + weight=1) takes over
    # immediately once real content exists.
    canvas = tk.Canvas(
        parent,
        highlightthickness=0,
        width=1,
        height=1,
    )

    scrollbar = ttk.Scrollbar(
        parent,
        orient="vertical",
        command=canvas.yview,
    )

    canvas.configure(
        yscrollcommand=scrollbar.set
    )

    canvas.grid(
        row=0,
        column=0,
        sticky="nsew",
    )

    scrollbar.grid(
        row=0,
        column=1,
        sticky="ns",
    )

    inner = ttk.Frame(
        canvas,
        padding=inner_padding,
    )

    inner_window = canvas.create_window(
        (0, 0),
        window=inner,
        anchor="nw",
    )

    def _sync_scrollregion(event=None):
        canvas.configure(
            scrollregion=canvas.bbox("all")
        )

        if not stretch_width:
            canvas.configure(
                width=inner.winfo_reqwidth()
            )

    inner.bind(
        "<Configure>",
        _sync_scrollregion,
    )

    if stretch_width:
        def _on_canvas_configure(event):
            canvas.itemconfig(
                inner_window,
                width=event.width,
            )

        canvas.bind(
            "<Configure>",
            _on_canvas_configure,
        )

    def _on_mousewheel(event):
        canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units",
        )

    def _bind_wheel(event=None):
        canvas.bind_all(
            "<MouseWheel>",
            _on_mousewheel,
        )

    def _unbind_wheel(event=None):
        canvas.unbind_all(
            "<MouseWheel>"
        )

    canvas.bind(
        "<Enter>",
        _bind_wheel,
    )

    canvas.bind(
        "<Leave>",
        _unbind_wheel,
    )

    return canvas, inner
