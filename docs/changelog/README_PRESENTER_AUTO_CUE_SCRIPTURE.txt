SSS — PRESENTER AUTO-CUE TO WEEKLY SCRIPTURE
===========================================

PROBLEM
-------
Previously, Scripture START assumed WorshipTools Presenter was already on
the correct Scripture service item.

That meant the operator had to manually click:

  Matthew 12:43-50

before pressing START in SSS.


NEW BEHAVIOR
------------
SSS now tries to select the exact weekly Scripture item in Presenter first.

For example, when the sermon plan says:

  Matthew 12:43-50

pressing Scripture START now does this:

  1. Find "Matthew 12:43-50" in the open Presenter service.
     "Matthew 12:43-50 (ESV)" is also accepted.

  2. Select that Presenter service item.

  3. Wait briefly for Presenter to load it.

  4. Ctrl + F15
     Put Webcam TP into OBS Preview.

  5. Ctrl + Shift
     Transition Preview to Program.

  6. Create the Matthew 12:43-50 recording chapter.

  7. Send Presenter MIDI NEXT:
       Port: Presenter
       Channel: 10
       C3 / Note 60
       Velocity 126

     Because SSS already selected the Scripture item, this NEXT command
     should fire the FIRST verse rather than depending on whatever slide
     Presenter was previously using.


HOW SSS FINDS IT
----------------
The new helper uses Windows UI Automation against the open WorshipTools
Presenter window.

It searches for the exact weekly Scripture reference in Presenter's UI,
then activates the matching service item.

It does NOT use fixed mouse coordinates.


FAIL-SAFE
---------
This happens BEFORE SSS changes the OBS view or writes the Scripture chapter.

If SSS cannot find/select the correct Scripture item, START stops and shows
a warning such as:

  Presenter could not select Matthew 12:43-50.

That means a failed Presenter search cannot accidentally:
  - change the church Program view
  - create the Scripture chapter
  - advance the sermon chapter sequence


TESTING
-------
Use the existing Admin:

  ENABLE CHAPTER / LT TEST MODE

Then:

  1. Open Presenter with the correct Sunday service.
  2. Deliberately click a DIFFERENT service item/slide.
  3. Mark Prayer in the SSS test sequence.
  4. Press Scripture START.

Expected result:

  Presenter jumps to the weekly Scripture item automatically,
  then fires its first verse.

The OBS view-transition portion still runs in Test Mode, while the recording
chapter remains simulated.


IMPORTANT
---------
WorshipTools currently documents keyboard shortcuts for:
  next/previous slide
  next/previous service item

but does not document a public command for jumping directly to a named
service item. This SSS helper therefore uses Windows accessibility/UI
Automation to select the exact Scripture item by its visible reference.


OPTIONAL TUNING
---------------
No configuration changes are required.

Optional sunday_config.json values:

  "presenter_scripture_locator_timeout_seconds": 8
  "presenter_scripture_select_settle_seconds": 0.45


INSTALL
-------
Close SSS.

Copy these files into:

  C:\Church\SermonAI

and overwrite sunday_mode.py:

  sunday_mode.py
  presenter_scripture_locator.py
  presenter_scripture_locator.ps1

Keep the existing:
  sss_scripture_reading.py

from the Presenter MIDI actual-port fix.

No sunday_config.json or persistent PTZ settings are included.
