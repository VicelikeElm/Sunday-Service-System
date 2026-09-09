SSS — VISUAL VOLUNTEER PREFLIGHT
================================

GOAL
----
Make the normal Sunday screen easier for a volunteer who does not know
what every technical component means.

The main Preflight now favors:
  short labels
  short status words
  color only when attention is needed
  click-for-details instead of always showing technical sentences


SHORTER LABELS
--------------
Examples:

  This week's sermon          -> Sermon
  Sermon chapter sequence     -> Chapters
  PTZ camera                  -> Camera
  OBS / WebSocket             -> OBS
  Church recording collection -> OBS scene
  Audio monitor loopback      -> Audio monitor
  Recording file health       -> Recording
  Critical OBS inputs         -> Sources
  Recording drive             -> Storage
  Internet / YouTube          -> Internet

The two groups are now simply:

  SERVICE
  AFTER SERVICE


SHORT STATUS EXAMPLES
---------------------
Instead of:

  READY — connected

SSS shows:

  Connected

Instead of:

  READY — PTZ preset 2 recalled.

SSS shows:

  Preset 2

Instead of:

  READY — 1392 GB free

SSS shows:

  1.4 TB free

Instead of a full chapter sentence:

  2 points

Warnings stay visually obvious:

  CHECK — Restart OBS
  CHECK — Date
  CHECK — Access

Actual failures are:

  FIX — OBS
  FIX — Audio
  FIX — Source
  FIX — Storage
  FIX — Internet


COLOR RULE
----------
No color = normal
Yellow   = CHECK
Red      = FIX

Healthy rows stay neutral so warning colors remain exceptional.


FULL TECHNICAL DETAILS ARE NOT LOST
-----------------------------------
Click the status name or status value.

A single details line below the Preflight will show the full original
technical message.

This keeps the normal volunteer view clean while still giving an admin
the exact diagnostic text when it is needed.


PROGRAM AUDIO
-------------
The live Program Audio meter remains unchanged:
  fixed dB readout
  smooth meter
  exception text only when needed

Clicking the audio meter also shows its detailed audio-sanity status.


INSTALL
-------
Close SSS.

Copy:

  sunday_mode.py

into:

  C:\Church\SermonAI

and overwrite the existing file.

No configuration files are included or changed.
