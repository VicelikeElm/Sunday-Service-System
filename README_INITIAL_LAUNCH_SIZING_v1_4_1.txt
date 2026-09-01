SSS v1.4.1 — SMART INITIAL LAUNCH SIZING
=========================================

This patch fixes the MAIN SSS window's first-launch size and position.

WHAT CHANGED
------------
SSS now:

1. Finds the monitor where the mouse cursor currently is.
2. Uses that monitor's usable WORK AREA.
3. Excludes the Windows taskbar.
4. Centers SSS on that monitor.
5. Chooses a comfortable initial window size.
6. Immediately scales the UI to that actual size.
7. Rechecks the scale 250 ms later after Windows finishes DPI/layout setup.

This is especially useful on a multi-monitor PC with different monitor sizes
or Windows scaling percentages.


RESPONSIVE BASELINE FIX
-----------------------
The responsive UI now uses a stable design baseline:

  1200 x 840 = 100%

Previously the initial window dimensions themselves became the 100% baseline.
On a shorter monitor that could make the window smaller without shrinking the
controls enough, so the bottom could look cramped/clipped until the window was
resized.

Now:

  smaller initial window -> controls scale down
  maximize/fullscreen    -> controls scale up
  restore                -> controls scale back
  manual resize          -> controls follow the window


MULTI-MONITOR BEHAVIOR
----------------------
SSS opens on the monitor where your mouse cursor is when SSS starts.

That should make it much more predictable on the church's multi-monitor setup.


NO FUNCTIONAL CHANGES
---------------------
This patch does NOT change:

  profiles
  OBS profile discovery
  Legacy/Profile fallback
  recording / streaming
  Presenter / MIDI
  Scripture
  PTZ
  chapters
  lower thirds
  audio
  Planning
  YouTube
  Sermon AI


INSTALL
-------
Close SSS.

Copy:
  sunday_mode.py

into:
  C:\Church\SermonAI

and overwrite the existing file.

All v1.4 profile/OBS files can stay as they are.
