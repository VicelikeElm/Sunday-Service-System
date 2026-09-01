SSS v2.4 — BACKUP / RESTORE + LAST KNOWN GOOD
==============================================

This implements the next application-polish roadmap item:

  Recovery Snapshots
  Last Known Good
  Guarded Restore


WHERE TO OPEN IT
----------------
1. SSS Setup & Settings
     -> Recovery

2. Main SSS
     -> ADMIN / TROUBLESHOOTING
     -> BACKUP / RECOVERY

3. Debug launcher:
     Open-SSS-Recovery.bat


RECOVERY PAGE
-------------
The Recovery page contains:

  [ CREATE RECOVERY SNAPSHOT ]

  [ SAVE READY SYSTEM AS LAST KNOWN GOOD ]

  AVAILABLE RECOVERY SNAPSHOTS
  -------------------------------------------------
  CREATED | TYPE | PROFILE | DIAGNOSTIC | FILES

  [ REFRESH LIST ]
  [ RESTORE SELECTED ]
  [ RESTORE LAST KNOWN GOOD ]
  [ OPEN RECOVERY FOLDER ]


MANUAL RECOVERY SNAPSHOT
------------------------
CREATE RECOVERY SNAPSHOT can be used at any time.

It snapshots the rollback boundary for the SSS application:

  top-level SSS/Python scripts
  BAT/CMD/VBS launchers
  sunday_config.json
  ptz_camera_config.json
  active profile pointer
  all SSS profile files

It intentionally does NOT back up:

  venv
  CUDA
  logs
  media / recordings
  AI models
  generated Diagnostics
  Recovery itself
  sermon_plan.json
  chapter runtime state
  status JSON files
  Gmail credentials/tokens
  .env
  OAuth/password/token/secret files


SUNDAY_CONFIG SECRET PROTECTION
-------------------------------
sunday_config.json is treated specially.

Secret-like keys such as:
  password
  secret
  token
  OAuth
  credential
  API key

are removed from the unencrypted recovery ZIP.

During restore, recovered NON-SECRET settings are merged with the current
sunday_config.json so existing secret values on that PC are preserved.

This allows rollback of normal settings without creating an unencrypted copy
of account secrets.


LAST KNOWN GOOD
---------------
SAVE READY SYSTEM AS LAST KNOWN GOOD requires the current Settings session to
have a Full System Diagnostics report with:

  Overall: READY

If Diagnostics is CHECK or FIX, SSS refuses to mark it Last Known Good.

When saved, Recovery keeps a pointer to that specific snapshot.

A diagnostic_reference.json is also stored in snapshots created from a
diagnostic run so the recovery point has context about the READY system.


RESTORE SAFETY
--------------
Restore is NEVER automatic.

Before restore, SSS checks OBS.

Restore is BLOCKED if:
  Recording is active
  Streaming is active

If OBS appears to be running but WebSocket state cannot be verified, Restore
is also blocked. Close OBS and try again.

If OBS is not running, Restore is allowed.


AUTOMATIC PRE-RESTORE SNAPSHOT
------------------------------
Every successful restore attempt first creates:

  PRE-RESTORE

snapshot of the system as it exists immediately before rollback.

That means even if someone restores the wrong snapshot, the state from right
before Restore is preserved as another recovery point.


WHAT RESTORE CHANGES
--------------------
Restore can replace:

  SSS application Python scripts
  SSS BAT/CMD/VBS launchers
  normal sunday_config settings
  ptz_camera_config.json
  SSS profile store / active profile pointer

Restoring ptz_camera_config.json happens ONLY because the user explicitly chose
a Recovery restore. Normal SSS update ZIPs still never contain or overwrite
that persistent camera configuration.


WHAT RESTORE DOES NOT CHANGE
----------------------------
Restore does NOT replace:

  .env
  Gmail credentials
  Gmail OAuth token
  passwords
  secret files
  sermon_plan.json
  current week's chapter runtime state
  recordings
  shorts
  transcripts
  YouTube files
  OBS configuration itself
  WorshipTools / ProPresenter files

The weekly sermon plan is excluded specifically so restoring application code
does not accidentally bring back a stale Sunday's sermon.


AFTER RESTORE
-------------
Settings closes after a successful Restore.

Restart Sunday Service System before using it.

This prevents the currently-running Python process from mixing newer code
already loaded in memory with older files just restored to disk.


RECOVERY STORAGE
----------------
Snapshots are stored in:

  C:\Church\SermonAI\Recovery\Snapshots

Last Known Good pointer:

  C:\Church\SermonAI\Recovery\last_known_good.json


INTEGRITY
---------
Every recoverable file in the ZIP is recorded in manifest.json with:

  destination group
  relative destination
  size
  SHA-256 checksum
  restore mode

Restore verifies all snapshot checksums BEFORE replacing any SSS files.


READ-ONLY SNAPSHOT CHECK
------------------------
Included:

  Check-SSS-Recovery-Snapshots.bat

It lists and SHA-256 verifies every Recovery ZIP.

It never restores anything.


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

Logical next polish item:

  Crash / startup recovery screen + human-friendly event history


INSTALL
-------
Close SSS and Settings.

Copy all files from this ZIP into:

  C:\Church\SermonAI

Overwrite matching code files.

No recovery snapshot, profile JSON, sunday_config.json, ptz_camera_config.json,
sermon_plan.json, .env, Gmail token, OBS password, or runtime credential is
included in this update ZIP.
