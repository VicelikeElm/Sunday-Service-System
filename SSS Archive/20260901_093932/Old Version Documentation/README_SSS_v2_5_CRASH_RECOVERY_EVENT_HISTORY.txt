SSS v2.5 — STARTUP CRASH RECOVERY + EVENT HISTORY
==================================================

This implements the next application-polish roadmap item:

  Startup crash / unexpected-shutdown recovery
  Human-friendly Event History


SESSION TRACKING
----------------
The main Sunday Service System now maintains a tiny session marker at:

  C:\Church\SermonAI\Event History\session_state.json

While SSS is open it records:

  process ID
  session start time
  last heartbeat
  active profile
  last human-readable event
  last known Recording state
  last known Streaming state

The heartbeat is read-only.

It checks OBS state approximately every 15 seconds and NEVER starts/stops
Recording or Streaming.


NORMAL CLOSE
------------
Closing the main SSS window now records a clean shutdown.

IMPORTANT:

  Closing SSS still does NOT stop OBS Recording.
  Closing SSS still does NOT stop OBS Streaming.

The close handler only marks the SSS application session as closed and then
closes the window.


UNEXPECTED SHUTDOWN DETECTION
-----------------------------
On startup, SSS checks the previous session marker.

If the previous SSS process is gone but its session still says RUNNING, SSS
records an unexpected shutdown.

This can identify situations such as:

  Python/Tk crash
  forced Windows restart
  power loss
  pythonw killed in Task Manager
  abnormal application termination

A copy of the detected prior-session state is saved as:

  C:\Church\SermonAI\Event History\last_unexpected_shutdown.json


STARTUP RECOVERY SCREEN
-----------------------
If an unexpected prior session is detected, a Startup Recovery window appears.

It shows:

  previous session start
  last heartbeat
  last recorded event
  whether Recording was active at the last heartbeat
  whether Streaming was active at the last heartbeat

If the previous heartbeat reported Recording or Streaming ACTIVE, the screen
clearly warns the operator.

SSS NEVER automatically stops those outputs.


SAFE STARTUP RECOVERY ACTIONS
-----------------------------
The Startup Recovery window offers:

  CONTINUE SUNDAY MODE

  RUN FULL SYSTEM DIAGNOSTICS

  OPEN BACKUP / RECOVERY

  VIEW EVENT HISTORY

None of those buttons automatically stops Recording/Streaming or moves a
camera/presentation.


EVENT HISTORY
-------------
New Settings page:

  SSS Setup & Settings
    -> Event History

It shows a human-friendly timeline with:

  TIME
  CATEGORY
  TYPE
  EVENT

Example events:

  Recording START requested
  Stream START requested
  Scripture reading started
  Presenter NEXT verse
  Camera PROFILE -> Pastor view
  Program audio MUTED
  Sermon points synced
  Full System Diagnostics completed
  Recovery snapshot created
  Recording STOP requested
  Sunday Service System closed normally


EVENT CATEGORIES
----------------
The timeline automatically organizes events into:

  SYSTEM
  RECOVERY
  OBS
  RECORDING
  STREAMING
  PRESENTATION
  CAMERA
  AUDIO
  SCRIPTURE
  SERMON
  PLANNING
  YOUTUBE

The Settings page has a category filter.


EVENT TYPES
-----------
INFO
  status/information

ACTION
  a human/system action such as start, stop, mute, move, save, or sync

WARNING
  a failure, missing item, warning, or problem


EVENT STORAGE
-------------
Daily history files:

  C:\Church\SermonAI\Event History\YYYY-MM-DD.jsonl

The main UI still keeps its existing Sunday Log and normal troubleshooting
logs. Event History is an additional cleaner operator timeline, not a
replacement for technical logs.

Daily JSONL Event History older than approximately 90 days is pruned when the
main SSS starts.


EVENT HISTORY EXPORT
--------------------
Settings -> Event History includes:

  REFRESH HISTORY
  EXPORT HISTORY TXT
  OPEN EVENT HISTORY FOLDER

Export creates a readable TXT file containing up to the recent 30 days.


ADMIN SHORTCUT
--------------
Main SSS:

  ADMIN / TROUBLESHOOTING
    -> EVENT HISTORY


DIRECT / DEBUG LAUNCHERS
------------------------
Open Event History UI:

  Open-SSS-Event-History.bat

Read-only console viewer:

  Show-SSS-Recent-Events.bat


DIAGNOSTICS + RECOVERY HISTORY
------------------------------
v2.5 also connects the newer maintenance systems to Event History.

Full System Diagnostics records its overall result.

Recovery records:

  Recovery snapshot created
  Last Known Good snapshot created
  Recovery snapshot restored


SAFETY
------
v2.5 does NOT change Sunday automation behavior.

It does NOT:

  auto-start Recording
  auto-start Streaming
  auto-stop Recording
  auto-stop Streaming
  move cameras during crash detection
  advance presentation slides
  change audio mute state
  refresh Gmail during crash detection
  alter sermon_plan.json
  create chapter markers

Startup Recovery is information + safe navigation only.


CURRENT PORTABLE SSS PROGRESS
-----------------------------
Profile Layer                         READY
Profile import/export/switch          READY
First-run setup wizard                READY
OBS profile adapter                   READY
WorshipTools Presenter adapter        READY
ProPresenter adapter                  READY
Capability-based volunteer UI         READY
Setup & Settings app                  READY
PTZOptics Camera adapter              READY
OBS Audio adapter                     READY
Sermon Source adapters                READY
Full System Diagnostics               READY
Backup / Restore                      READY
Last Known Good                       READY
Crash / startup recovery              READY
Human-friendly Event History          READY

Logical next polish item:

  Profile schema migrations + versioned upgrade system

That gives the portable app a safe way to open profiles created by older SSS
versions as the application continues to evolve.


INSTALL
-------
Close SSS and Settings.

Copy all files from this ZIP into:

  C:\Church\SermonAI

Overwrite matching code files.

No Event History, session state, crash record, recovery snapshot, profile JSON,
sunday_config.json, ptz_camera_config.json, sermon_plan.json, .env, Gmail
token, or credential is included in this update ZIP.
