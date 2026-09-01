SUNDAY MODE v18 — STABILITY FIX
===============================

WHY THIS VERSION EXISTS
-----------------------
A native "pythonw.exe - Application Error" appeared just after
LAUNCH SUNDAY APPS opened Presenter, and SSS terminated.

There were two risky patterns in v17 that can produce native crashes on
Windows even when ordinary Python exception handling cannot catch them:

1. The repeating preflight loaded PyAudioWPatch/PortAudio directly into
   the Sunday Mode pythonw.exe process.

2. Multiple background preflight/Planning threads could call Tkinter
   methods or schedule Tk callbacks while other refreshes were running.

V18 removes both risks.

CHANGES
-------
- SSS no longer imports or instantiates PyAudioWPatch.
- The TASCAM/audio preflight now uses Windows AudioEndpoint/PnP
  discovery through PowerShell.
- Only ONE preflight can run at a time.
- Only ONE watchdog can run at a time.
- Background workers no longer call Tkinter directly.
- Worker results are posted to a queue and handled by the Tk main
  thread.
- LAUNCH SUNDAY APPS schedules only one delayed preflight instead of
  two overlapping refresh opportunities.
- Planning sync remains background/date-guarded.
- OBS and Presenter launch behavior is unchanged.
- Recording and streaming remain manual.

INSTALL
-------
1. Close SSS.
2. Close OBS/Presenter if convenient.
3. Copy all v18 files into:
     C:\Church\SermonAI
   and overwrite the current files.
4. Start SSS normally.
5. Click LAUNCH SUNDAY APPS.

DEBUG FALLBACK
--------------
If SSS ever closes again, run:

  Start-Sunday-Mode-Debug.bat

This runs Sunday Mode with Python's faulthandler in a visible console so
we can capture a Python/native traceback instead of losing the details
inside pythonw.exe.
