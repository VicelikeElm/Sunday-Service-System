SUNDAY MODE v19 — AUTO-LAUNCH OBS + PRESENTER
=============================================

NEW STARTUP FLOW
----------------
As soon as START SUNDAY MODE opens SSS:

  SSS
   ├─ imports/checks the pastor sermon plan
   ├─ checks OBS
   │    └─ launches OBS if it is not already open
   ├─ checks Presenter
   │    └─ launches Presenter if it is not already open
   ├─ starts/checks Sermon AI + Chapter Bridge
   └─ runs the date-guarded Planning Scripture sync

Recording and streaming are STILL manual.

LAUNCH SUNDAY APPS
------------------
The button remains available as a retry/check button.

If OBS or Presenter was closed after SSS started, pressing
LAUNCH SUNDAY APPS will reopen what is missing without intentionally
launching a duplicate copy.

CONFIG
------
sunday_config.json now includes:

  "auto_start_presenter": true

Set it to false only if you ever want Presenter to wait for the
LAUNCH SUNDAY APPS button again.

INSTALL
-------
1. Close SSS.
2. Copy all v19 files into:
     C:\Church\SermonAI
3. Overwrite the current files.
4. Use your normal START SUNDAY MODE shortcut.

EXPECTED RESULT
---------------
You should only need to click:

  START SUNDAY MODE

and then both OBS and Presenter should begin opening automatically.

SSS does NOT automatically start recording or streaming.
