SSS — EXCEPTION-ONLY PREFLIGHT STATUS
======================================

This update simplifies Preflight so color means "pay attention."

NORMAL / HEALTHY
----------------
Healthy rows are now neutral.

They do NOT say:
  READY —
  READY — READY —
  etc.

They simply show the useful result, for example:
  connected
  Church recording
  TASCAM Interface ready
  1392 GB free
  running

REVIEW
------
Only something that may need checking is highlighted YELLOW and starts:

  REVIEW —

PROBLEM
-------
Only something that actually needs action is highlighted RED and starts:

  PROBLEM —

WHY
---
Green was the normal state, so filling most of the screen with green
did not add useful information and made the exceptional rows less obvious.

Now color is reserved for exceptions and should draw the volunteer's eye
only when something needs attention.

This is a display-only change. It does not change any Preflight logic,
recording/streaming behavior, PTZ control, chapter handling, Planning,
YouTube, or watchdog behavior.
