SSS — RESPONSIVE WINDOW SCALING
================================

This patch makes the main Sunday Service System UI scale with the window.

WHAT IT DOES
------------
Normal/restored window:
  SSS uses its normal control/font sizes.

Maximized or fullscreen-sized window:
  fonts, status text, button text, padding, wrap lengths, meter height, and
  general control spacing grow to use the extra screen space.

Restore the window:
  everything shrinks back automatically.

Manually resize the window:
  the UI follows the new size in both directions.


HOW THE SCALE IS CALCULATED
---------------------------
SSS treats its normal startup window size as 100%.

It looks at BOTH the current width and height and chooses the smaller scale.
This keeps controls from becoming so large that the bottom of the volunteer
workflow falls off-screen.

The scale is bounded from about 78% to 150% for readability.


NO WORKFLOW CHANGES
-------------------
This patch only changes presentation/layout behavior.

It does NOT change:
  recording
  streaming
  OBS controls
  Presenter MIDI
  Scripture logic
  sermon chapters
  lower thirds
  PTZ
  upcoming-Sunday sermon-plan protection

Your exact Stream Deck-style Presenter MIDI behavior remains unchanged.


INSTALL
-------
Close SSS.

Copy:
  sunday_mode.py

into:
  C:\Church\SermonAI

and overwrite the existing file.

Then reopen SSS and try:
  - normal window
  - Windows Maximize
  - Restore
  - manually drag the window larger/smaller

No config files are included or changed.
