SSS — MUTE / UNMUTE + SYSTEM STATUS
==================================

1. AUDIO MUTE BUTTON
--------------------
The old button:

  EMERGENCY MUTE

is now a true two-state control:

  MUTE AUDIO

and when the configured program-audio inputs are muted it changes to:

  UNMUTE AUDIO

Pressing it again restores audio and changes the button back to:

  MUTE AUDIO

The button also refreshes from OBS periodically, so if someone changes
the mute state directly in OBS or from another controller, SSS updates
the wording to match the real state.


2. "PREFLIGHT" RENAMED
----------------------
The old volunteer-facing term:

  PREFLIGHT

has been replaced with:

  SYSTEM STATUS

This better matches what the panel actually does because it shows more
than just a one-time pre-service check. It displays:

  service readiness
  live system health
  recording/audio state
  after-service status

Expanded:
  ▼ SYSTEM STATUS

Collapsed:
  ▶ SYSTEM STATUS


3. BUTTON RENAMED
-----------------
The old:

  RUN PREFLIGHT

is now:

  REFRESH STATUS

The checks still run automatically in the background. This button simply
requests an immediate refresh.


4. LOG / TOOLTIP WORDING
------------------------
Volunteer-facing and Sunday Log wording now uses "System Status" instead
of "Preflight" where appropriate.

Examples:

  System status: ready.

  System status needs attention: ...

The Tooltip explanations were also updated to use the new wording.


INSTALL
-------
Close SSS.

Copy:

  sunday_mode.py

into:

  C:\Church\SermonAI

and overwrite the existing file.

No configuration files are included or changed.
