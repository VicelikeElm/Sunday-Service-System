SSS — EXACT STREAM DECK PRESENTER MIDI
======================================

SSS is back on MIDI for Presenter verse navigation.

The SSS mapping is now intentionally hard-coded to exactly match the working
Stream Deck controls.

NEXT VERSE
----------
Port:      Presenter
Channel:   10
Note:      60
Velocity:  126
Event:     Note On only
Release:   NONE
Note Off:  NONE

PREVIOUS VERSE
--------------
Port:      Presenter
Channel:   10
Note:      62
Velocity:  126
Event:     Note On only
Release:   NONE
Note Off:  NONE

IMPORTANT
---------
SSS does NOT send a second MIDI event when the button is released.

There is:
  no Note Off
  no velocity-0 release
  no midiOutReset
  no second trigger

The WinMM output handle is kept open briefly only so loopMIDI has time to
deliver the ONE Note On event, then the handle is closed.

Old sunday_config.json MIDI overrides are ignored for the Scripture controls,
so an old Note 64 value cannot be used accidentally.

PRESERVED
---------
This patch keeps the current Sunday workflow:
- upcoming-Sunday sermon/date protection
- Presenter manually preset on the first Scripture verse
- Scripture NEXT button
- Ctrl+F13 -> webcam only into Preview
- Ctrl+Shift -> transition back to Program at end of reading

TEST
----
Run:
  Test-Exact-StreamDeck-NEXT-MIDI.bat

Presenter should advance exactly one verse.

Then:
  Test-Exact-StreamDeck-PREVIOUS-MIDI.bat

Presenter should go back exactly one verse.

INSTALL
-------
Close SSS.

Copy into:
  C:\Church\SermonAI

and overwrite:
  sunday_mode.py
  sss_scripture_reading.py

The test files are optional.

No configuration files are included or changed.
