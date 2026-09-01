SSS — PRESENTER MIDI + WEBCAM TP VISUAL VERIFICATION
===================================================

This replaces the Presenter internal-UI automation approach.

DEFAULT VERIFICATION VIEW
-------------------------
SSS now reads the OBS scene:

  webcam TP

first.

If that cannot be captured, it falls back to:

  Cam Link Pro HDMI4


HOW SCRIPTURE START FINDS THE RIGHT ITEM
----------------------------------------
SSS uses Presenter's own MIDI commands shown in Presenter Settings:

  Change Service Item = Note 5
  Change Slide        = Note 4

The MIDI message velocity is used by Presenter as the zero-based item/slide
index.

The first time SSS sees a new sermon plan:

  1. Program stays on the webcam.
  2. SSS scans Presenter service-item indexes by MIDI.
  3. For each item it selects slide 0.
  4. OBS screenshots the webcam TP scene.
  5. Windows' built-in OCR reads the ACTUAL rendered output.
  6. SSS looks for the first Scripture verse, for example:
       Matthew 12:43
  7. When found, the item index is saved for the current sermon plan.
  8. Presenter is left on the verified Scripture item / first verse.
  9. Only THEN does SSS:
       Ctrl+F15
       Ctrl+Shift
       create the Scripture chapter marker

No extra MIDI NEXT is sent because Change Slide index 0 already selected the
first Scripture slide.


WEEKLY CACHE
------------
After SSS discovers the Scripture item, it stores that item number in:

  C:\Church\SermonAI\State\presenter_scripture_position.json

Later START presses for the same sermon verify that saved item first instead
of rescanning everything.


WHY WEBCAM TP
-------------
This verifies what OBS is actually able to render for the Scripture view,
rather than trusting Presenter's internal interface.

It also means SSS no longer needs Chromium debugging/accessibility control of
Presenter.


SAFETY
------
The scan happens BEFORE webcam TP is transitioned to Program.

If SSS cannot positively read the expected Scripture reference, it:
  - does not transition Scripture to Program
  - does not create the Scripture chapter
  - does not advance the real sermon sequence


FIRST TEST
----------
1. Close SSS and copy this patch into C:\Church\SermonAI.
2. Open OBS and Presenter normally.
3. Put Presenter on any slide.
4. Run:
     Test-Presenter-Visual-Read.bat

If Presenter is currently on Matthew 12:45, the printed OCR text should include
something close to:

  Matthew 12:45 (ESV)

5. Then use Admin Chapter/LT Test Mode and test Scripture START.


DEFAULTS
--------
  OBS visual source: webcam TP
  fallback source:   Cam Link Pro HDMI4
  Presenter MIDI port: Presenter
  MIDI channel: 10
  Change Service Item note: 5
  Change Slide note: 4
  scan: first 40 service items

No sunday_config.json is included.
