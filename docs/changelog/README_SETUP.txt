SUNDAY MODE PACKAGE
===================

This package is configured from the church-PC inventory taken on
2026-08-24.

EXPECTED SYSTEM
---------------
OBS scene collection:
  Church recording

OBS recording folder:
  D:\2026

Critical OBS inputs:
  main
  room mics
  lower thirds

OBS-monitor audio:
  Headphones (High Definition Audio Device) [Loopback]

Presenter shortcut:
  C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Presenter.lnk

WHAT THIS PACKAGE ADDS
----------------------
1. Sunday Mode dashboard
2. Pre-service health checks
3. Separate Start/Stop Recording controls
4. Separate Start/Stop Stream controls
5. Emergency audio mute / restore
6. Sermon AI watchdog
7. Automatic chapter bridge from sermon lower-third changes
8. Automatic "Start" chapter when recording begins
9. Stream Deck action batch files
10. Volunteer quick guide

INSTALL
-------
1. Copy every file in this package into:
      C:\Church\SermonAI

2. Do NOT replace or delete:
      .env
      sermon_ai.py
      process_shorts.py
      render_shorts.py
      prepare_sermon.py

3. Confirm syntax:
      cd C:\Church\SermonAI
      venv\Scripts\activate
      python -m py_compile sunday_common.py
      python -m py_compile sunday_action.py
      python -m py_compile chapter_bridge.py
      python -m py_compile sunday_mode.py

4. Create the desktop shortcut:
      Right-click install_desktop_shortcut.ps1
      Run with PowerShell

   If Windows blocks that method, run:
      powershell -ExecutionPolicy Bypass -File C:\Church\SermonAI\tools\install_desktop_shortcut.ps1

5. Open OBS normally.

6. Double-click the new "Sunday Mode" desktop shortcut.

FIRST TEST — DO NOT DO THIS DURING A REAL SERVICE
-------------------------------------------------
A. Run Sunday Mode with OBS open but not recording.
B. Confirm the preflight is mostly green.
C. Make a short test recording.
D. Change a sermon lower-third preset.
E. Stop recording.
F. Use ffprobe to confirm the test recording contains chapters.

The chapter bridge uses OBS's CreateRecordChapter WebSocket request.
It writes markers into the normal OBS recording.

STREAM DECK
-----------
The inventory showed a physical device named:
  Church Stream deck

You can assign Stream Deck "Open" actions to:

  StreamDeck_START_RECORDING.bat
  StreamDeck_STOP_RECORDING.bat
  StreamDeck_START_STREAM.bat
  StreamDeck_STOP_STREAM.bat
  StreamDeck_EMERGENCY_MUTE.bat
  StreamDeck_MANUAL_CHAPTER.bat

Suggested 5x3 church layout:

  [ REC ● ] [ REC ■ ] [ LIVE ● ] [ LIVE ■ ] [ SUNDAY MODE ]
  [ scene controls / Presenter controls as you already use them ]
  [ other church controls ]

IMPORTANT
---------
The dashboard does not automatically restart OBS if OBS crashes during
a live service. It alerts instead. Restarting OBS automatically during
a livestream is intentionally avoided because it can make a live
failure worse.

The watchdog may restart Sermon AI if Sermon AI itself is missing.

The Chapter Bridge reads a temporary COPY of OBS Browser LocalStorage;
it does not modify the lower-third database.


RECORDING AND STREAMING ARE SEPARATE
------------------------------------
Sunday Mode never starts the livestream automatically.

Use:
  START RECORDING
  STOP RECORDING

independently from:
  START STREAM
  STOP STREAM

This is intentional so a volunteer can begin local recording early
without accidentally sending anything live to YouTube.


V3 OBS STARTUP BEHAVIOR
-----------------------
Sunday Mode can now be opened before OBS.

If OBS is closed:
  - Sunday Mode starts OBS.
  - the dashboard displays "waiting for OBS / WebSocket"
  - no obsws-python connection traceback should appear
  - recording and streaming remain OFF

Once OBS finishes loading and WebSocket port 4455 becomes available,
the dashboard automatically recovers on its next refresh.


V4 AUDIO LABEL
--------------
Sunday Mode now displays the OBS-monitor loopback as:

  TASCAM Interface

Internally it still matches the real Windows device name:

  Headphones (High Definition Audio Device) [Loopback]

This avoids breaking device detection if Windows keeps its original name.


V5 OBS LAUNCH FIX
-----------------
LAUNCH SUNDAY APPS now starts OBS through the normal Start Menu shortcut:

  C:\ProgramData\Microsoft\Windows\Start Menu\Programs\OBS Studio.lnk

This was detected in the church-PC inventory.

If that shortcut ever disappears, Sunday Mode falls back to:

  C:\Program Files\obs-studio\bin\64bit\obs64.exe

If OBS is already running but WebSocket is not ready yet, Sunday Mode
does not launch a second copy. It waits for the existing OBS process.


V6 OBS STARTUP POPUP CLEANER
----------------------------
Sunday Mode now runs:

  C:\Church\SermonAI\core\obs_startup_cleanup.py

for the first 60 seconds around OBS startup.

It automatically closes ONLY these OBS-owned windows:
  Plugin Load Error
  Script Log

It does not click inside OBS, change plugins, remove scripts, or touch
recording/streaming settings.

A small log is written to:
  C:\Church\SermonAI\obs_startup_cleanup.log

This is a convenience workaround. The underlying plugin/script startup
warnings can still be repaired separately later.


V7 CHAPTER BRIDGE STARTUP FIX
-----------------------------
Fixed a process-detection bug in sunday_common.py.

The old process check could accidentally match the PowerShell process
performing the check because its own command line contained the text:

  chapter_bridge.py

That could make Sunday Mode believe Chapter Bridge was already running
and skip launching it.

V7 excludes the querying PowerShell process, so Chapter Bridge and the
OBS startup popup helper can now be detected correctly.

V7 also stops writing the exact same preflight warning to the Sunday Log
every five seconds. Status indicators still refresh normally.

Diagnostic helper:
  Check-Chapter-Bridge.bat
