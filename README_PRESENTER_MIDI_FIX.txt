SSS — PRESENTER MIDI FIX
=========================

ROOT CAUSE
----------
The prior patch changed the default port inside sss_scripture_reading.py,
but sunday_mode.py was still explicitly passing the old placeholder:

  loopMIDI Port

That overrode the helper's new default, which is why the Scripture view and
chapter worked but Presenter did not advance.

FIX
---
SSS now uses the actual loopMIDI port:

  Presenter

everywhere:
  - Scripture START
  - NEXT VERSE
  - BACK VERSE
  - System Status Presenter check
  - troubleshooting text

LEGACY CONFIG SAFETY
--------------------
If sunday_config.json happens to contain the old value:

  "presenter_midi_port": "loopMIDI Port"

SSS now automatically treats that as:

  Presenter

without rewriting or overwriting the config file.

MIDI MAPPING
------------
Port:     Presenter
Channel:  10
NEXT:     C3 / Note 60 / Velocity 126
BACK:     D3 / Note 62 / Velocity 126

The Presenter failure popup also now shows the actual MIDI error if another
problem remains.

INSTALL
-------
Close SSS.

Copy both files into:
  C:\Church\SermonAI

and overwrite:
  sunday_mode.py
  sss_scripture_reading.py

Then reopen SSS.
