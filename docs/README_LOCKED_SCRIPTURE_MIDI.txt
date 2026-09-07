SSS — LOCKED SCRIPTURE MIDI MAPPING
===================================

The Scripture verse controls are now hard-locked to the exact mappings shown
in the Stream Deck screenshots.

NEXT VERSE
----------
Port:     Presenter
Channel:  10
Note:     60 / C3
Velocity: 126

PREVIOUS VERSE
--------------
Port:     Presenter
Channel:  10
Note:     62 / D3
Velocity: 126

WHY THIS PATCH
--------------
The previous code had the correct defaults, but it still allowed
sunday_config.json to override presenter_next_note and presenter_back_note.

That meant an older experimental config value such as Note 64
("Next Service Item" in Presenter) could override the correct Scripture
NEXT note even though the Python default was 60.

This patch ignores those old config overrides for Scripture verse navigation.

Note 64 is NOT used by the Scripture NEXT/PREVIOUS functions.

The Sunday Log also prints the exact MIDI mapping whenever NEXT or PREVIOUS
is sent, so troubleshooting is easy.

INSTALL
-------
Close SSS.

Copy:
  sunday_mode.py
  sss_scripture_reading.py

into:
  C:\Church\SermonAI

and overwrite the existing files.

No config files are changed.
