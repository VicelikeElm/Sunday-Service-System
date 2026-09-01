SSS — COLLAPSIBLE PREFLIGHT UPDATE
=================================

The Preflight area is now collapsible.

EXPANDED:
  ▼ PREFLIGHT

COLLAPSED:
  ▶ PREFLIGHT

Click anywhere on the PREFLIGHT header button to open or close it.

When collapsed:
  - the status checks keep running in the background
  - RUN PREFLIGHT still works
  - no monitoring is disabled
  - the Volunteer Controls and Sunday Log get more visible space

The two-column Important / Secondary preflight layout is unchanged
when expanded.

INSTALL
-------
Close SSS.

Copy sunday_mode.py from this patch into:

  C:\Church\SermonAI

and overwrite the existing file.

No configuration files are included in this patch, so the persistent
PTZ camera address and the rest of the current SSS settings are not
changed.
