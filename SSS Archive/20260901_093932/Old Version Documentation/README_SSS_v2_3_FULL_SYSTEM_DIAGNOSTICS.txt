SSS v2.3 — FULL SYSTEM DIAGNOSTICS CENTER
=========================================

This implements the next application-polish roadmap item:

  One-button Full System Test / Diagnostics Center


WHERE TO OPEN IT
----------------
Three ways:

1. SSS Setup & Settings
     -> Diagnostics

2. Bottom of SSS Setup & Settings
     -> RUN FULL SYSTEM TEST

3. Main SSS
     -> ADMIN / TROUBLESHOOTING
     -> FULL SYSTEM DIAGNOSTICS (READ-ONLY)

There is also a visible debug launcher:

  Run-SSS-Full-System-Test.bat


THE TEST IS READ-ONLY
---------------------
The Full System Test DOES NOT:

  start recording
  stop recording
  start streaming
  stop streaming
  change OBS Program/Preview scenes
  move a PTZ camera
  advance or reverse presentation slides
  mute or unmute audio
  refresh Gmail
  change sermon_plan.json
  change lower thirds
  write chapter markers

It only reads configuration/status and performs safe connectivity checks.


STATUS LEVELS
-------------
READY
  The check passed.

CHECK
  The system can often still operate, but this item should be reviewed.

FIX
  A service-critical configured item is missing, unreachable, stale, or invalid.

INFO
  Informational live state, such as Recording currently active.

The overall result is:

  READY
  CHECK
  FIX

based on the most serious individual result.


CHECKS INCLUDED
---------------
Church Profile
  active profile loads
  setup completeness

OBS
  WebSocket connection
  current scene collection
  PROFILE scene collection mapping
  Normal scene mapping
  Scripture scene mapping

OBS Outputs
  reads current Recording/Streaming state
  never changes either output

Presentation
  PROFILE adapters use their existing safe readiness test
  ProPresenter uses the API connection check
  LEGACY WorshipTools checks for the Presenter MIDI output

Camera
  PROFILE uses the Camera adapter's connectivity check
  LEGACY reads the machine-local PTZ configuration
  PTZ checks are reachability-only
  NO preset recall is sent

Audio
  PROFILE validates selected OBS mute targets
  LEGACY validates emergency_mute_inputs against OBS
  checks the existing Windows audio endpoint when configured
  NO mute state is changed

Sermon Source
  validates active source
  validates canonical sermon_plan.json
  requires the upcoming Sunday service date
  validates title, Scripture, and sermon points
  DOES NOT refresh Gmail or overwrite the plan

Sermon Chapters
  compares named-hotkey sync status with the active sermon plan
  detects deferred OBS-restart state
  does not create chapter markers

Recording Storage
  recording folder exists
  free disk space against current minimum/critical thresholds

Critical Folders
  required folders exist
  basic writable permission is available
  no temporary probe file is created

Media / GPU Tools
  ffmpeg
  ffprobe
  nvidia-smi

Lower Thirds
  sync script
  Animated Lower Thirds control panel

Network
  uses the existing configured network test host/port
  network failure is CHECK, not FIX, because local recording/control can still work


DIAGNOSTICS PAGE
----------------
The Diagnostics page contains:

  OVERALL READINESS

  STATUS | CHECK | DETAIL
  --------------------------------
  READY  | OBS | ...
  FIX    | Audio | ...
  CHECK  | Sermon Chapters | ...

  [ RUN FULL SYSTEM TEST ]
  [ EXPORT DIAGNOSTIC ZIP ]
  [ OPEN DIAGNOSTICS FOLDER ]


DIAGNOSTIC ZIP
--------------
EXPORT DIAGNOSTIC ZIP creates:

  C:\Church\SermonAI\Diagnostics\
    SSS-Diagnostic_YYYY-MM-DD_HH-MM-SS.zip

The bundle contains:

  diagnostic_report.txt
  diagnostic_report.json
  active_profile_sanitized.json
  sunday_config_sanitized.json
  README.txt

Password/token/secret-like keys are automatically redacted.

The diagnostic bundle does NOT include:

  .env
  Gmail OAuth token
  Gmail credentials
  OBS password
  raw credential files
  PTZ legacy configuration file
  Sunday logs containing arbitrary historical text


WHY THIS IS USEFUL PORTABLY
---------------------------
A future church can run one test and immediately see whether its:

  OBS
  presentation software
  camera
  audio
  sermon source
  storage
  dependencies

are actually ready before a service.

If they need help, the sanitized Diagnostic ZIP gives a much cleaner support
starting point than asking them to find individual logs/config files.


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

Logical next polish item:

  Backup / Restore + Last Known Good recovery


INSTALL
-------
Close SSS and Settings.

Copy all files from this ZIP into:

  C:\Church\SermonAI

Overwrite matching code files.

No profile JSON, sunday_config.json, sermon_plan.json, .env, Gmail token,
OBS password, PTZ persistent configuration, or other runtime credentials
are included.
