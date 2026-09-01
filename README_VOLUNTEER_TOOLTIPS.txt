SSS — VOLUNTEER TOOLTIPS
========================

PURPOSE
-------
The main SSS screen is designed for volunteers, so the interface now
explains what each status and control does in plain language.

HOVER TOOLTIPS
--------------
Hover over the main SSS items and a small tooltip appears.

Tooltips have been added to:
  - SSS title/help/color guide
  - Preflight expand/collapse
  - every SERVICE / AFTER SERVICE status
  - Program Audio meter
  - every numbered volunteer workflow heading
  - Launch Sunday Apps
  - Run Preflight
  - Start Recording
  - Start Stream
  - Emergency Mute
  - Sermon lower-third/chapter control
  - Worship View
  - Pastor View
  - Stop Stream
  - Stop Recording
  - Admin / Troubleshooting
  - Sunday Log
  - the main interactive Admin controls

TOOLTIP HELP BAR
----------------
There is now a clearly labeled line:

  Tooltip:  <plain-language explanation>

It sits OUTSIDE the collapsible Preflight panel, so it stays visible even
when Preflight is closed.

Hovering an item updates this line as well as showing the popup tooltip.

Clicking a Preflight status changes the Tooltip line to the exact current
technical status for troubleshooting.


3 — SERMON
----------
The 3 — SERMON tooltip now explains the OBS relationship in plain language:

  This is the sermon lower-third and chapter-marker control inside OBS.
  The button follows the sermon sequence. When a step has a lower third,
  SSS activates the matching lower third; while OBS is recording, the same
  press also creates the matching named chapter marker in the recording.

The sermon button itself explains:

  Press this at the appropriate sermon moment. SSS uses OBS to activate
  the lower third assigned to the current sermon step and creates the
  matching named chapter marker in the recording. After it fires, the
  button advances to the next sermon step.

This wording is intentionally written for someone who does not need to
understand the underlying OBS hotkeys or plugin details.


ADMIN
-----
The important Admin buttons and PTZ/Chapter-LT test controls also have
hover tooltips explaining what they do.


INSTALL
-------
Close SSS.

Copy:

  sunday_mode.py

into:

  C:\Church\SermonAI

and overwrite the existing file.

No configuration files are included or changed.
