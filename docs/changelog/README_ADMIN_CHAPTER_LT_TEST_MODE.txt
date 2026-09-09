SSS — ADMIN CHAPTER / LOWER-THIRD TEST MODE
==========================================

NEW ADMIN CONTROL
-----------------
ADMIN / TROUBLESHOOTING now contains:

  Chapter / Lower-Third Test
    [ ] ENABLE CHAPTER / LT TEST MODE

It is OFF by default every time Admin is opened.


WHEN TEST MODE IS ENABLED
-------------------------
SSS creates a completely separate IN-MEMORY test chapter position.

The test sequence always starts at:

  Prayer

Then the normal SERMON button can be used without recording:

  Prayer
  Scripture
  Point 1
  Point 2
  ...
  Ending Prayer
  Benediction

For sermon points, the normal LT1 workflow is exercised:

  Load LT1 slot
  LT1 ON
  11 seconds
  LT1 OFF

The main sermon row visibly changes to:

  TEST MODE
  LOWER THIRD LIVE
  marker simulated

and the button is prefixed with:

  TEST —


REAL SERMON POSITION IS NEVER CHANGED
-------------------------------------
Test Mode does NOT call reset_rotation() and does NOT advance
chapter_rotation_state.json.

Example:

Normal service position before testing:
  Point 3

Enable Test Mode:
  Test starts at Prayer

Test through:
  Prayer
  Scripture
  Point 1
  Point 2

Turn Test Mode OFF:
  Normal button returns to Point 3

The same works if the preserved normal position was:
  Prayer
  Point 2
  Ending Prayer
  Benediction
  etc.


NO RECORDING REQUIRED
---------------------
Test Mode does not require OBS recording.

A real recording chapter marker cannot be embedded without a recording,
so Test Mode SIMULATES the chapter-marker portion while actually firing
the lower-third hotkeys.

No real chapter marker is written.


SAFETY
------
Test Mode cannot be enabled while OBS is:
  recording
  streaming

This prevents a test lower third from appearing in a live service.

Starting Recording or Stream while Test Mode is enabled automatically
returns SSS to normal mode first.

The chapter button remains disabled while an 11-second LT test is active.


TURNING TEST MODE OFF
---------------------
You can toggle Test Mode ON and OFF repeatedly while Admin stays open.

Every time it is turned ON:
  the disposable test sequence resets to Prayer.

Every time it is turned OFF:
  the main SERMON button returns to the untouched real sermon position.


CLOSING ADMIN
-------------
Closing the Admin window ALWAYS turns Chapter/LT Test Mode OFF.

The real sermon position immediately returns because it was never
modified in the first place.


INSTALL
-------
Close SSS.

Copy these files into:

  C:\Church\SermonAI

and overwrite the matching files:

  sunday_mode.py
  sermon_chapter_manager.py

No configuration file is included in this patch.
