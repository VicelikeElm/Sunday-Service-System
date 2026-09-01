SSS — PRESENTER MIDI SINGLE-EVENT FIX
=====================================

Your suspicion makes sense: SSS was sending a MIDI Note On followed by a
MIDI Note Off. If Presenter treats both as command events, one SSS press can
look like two activations.

This patch changes Presenter command MIDI to ONE event only:

NEXT VERSE
  Port: Presenter
  Channel: 10
  Note: 60 / C3
  Velocity: 126
  Event: Note On only

PREVIOUS VERSE
  Port: Presenter
  Channel: 10
  Note: 62 / D3
  Velocity: 126
  Event: Note On only

No Note Off is sent.

This is safe for SSS because these notes are being used as command triggers,
not as musical notes that need to be held and released.

TEST
----
Run:
  Test-Presenter-NEXT-Single-Event.bat

Presenter should advance exactly ONE slide.

Then:
  Test-Presenter-PREVIOUS-Single-Event.bat

Presenter should go back exactly ONE slide.

INSTALL
-------
Close SSS.

Copy into:
  C:\Church\SermonAI

and overwrite:
  sss_scripture_reading.py

Also copy the test files if you want the isolated tests.

No config files are changed.
