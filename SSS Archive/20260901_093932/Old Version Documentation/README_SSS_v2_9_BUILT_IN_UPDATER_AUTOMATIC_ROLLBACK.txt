SSS v2.9 — BUILT-IN UPDATER + AUTOMATIC ROLLBACK
=================================================

v2.9 adds the first installed-application update system for Sunday Service
System.

The updater is deliberately separated from church data and live-service
control.


THREE WINDOWS APPLICATIONS
--------------------------
The Windows build now creates:

  SundayServiceSystem.exe

  SundayServiceSystemSettings.exe

  SundayServiceSystemUpdater.exe

The Updater EXE has its own Windows manifest requesting Administrator rights
because Program Files application binaries cannot be replaced by a normal
user process.


SETTINGS -> UPDATES
-------------------
New permanent Settings page:

  SSS Setup & Settings
    -> Updates

It shows:
  current SSS version
  installed/Python runtime mode
  last update result
  whether a rollback backup exists

Controls:

  SELECT .SSSUPDATE
  VERIFY PACKAGE
  INSTALL VERIFIED UPDATE

  ROLL BACK LAST APPLICATION UPDATE
  OPEN UPDATE / ROLLBACK FOLDER


LOCAL UPDATE PACKAGE
--------------------
The v2.9 build creates:

  C:\Church\SermonAI\update-output\
    SundayServiceSystem-Update-v2.9.0.sssupdate

The package contains ONLY the compiled:

  SundayServiceSystem
  SundayServiceSystemSettings

application folders.

It does NOT contain:
  SundayServiceSystemUpdater itself
  church profiles
  ProgramData profile store
  Windows Credential Manager secrets
  .env
  Gmail OAuth
  YouTube OAuth
  sunday_config.json
  ptz_camera_config.json
  sermon_plan.json
  recordings
  transcripts
  shorts
  Event History
  Recovery snapshots
  diagnostics

The updater itself remains the installed stable update engine in v2.9.
Future installer releases can replace the updater engine when the package
protocol needs to change.


PACKAGE INTEGRITY
-----------------
Every update package contains manifest.json.

Every application file is recorded with:
  path
  byte size
  SHA-256 checksum

Before installation, SSS verifies ALL listed files.

The ZIP is also checked for:
  path traversal
  absolute paths
  symbolic links
  unmanifested payload files
  unsupported application targets

A package is rejected before installation if any integrity check fails.


IMPORTANT SIGNING LIMIT
-----------------------
v2.9 local update packages are NOT yet cryptographically signed with a release
signing key.

SHA-256 verifies that the package has not changed relative to its own manifest,
but it does not prove who created the package.

For that reason v2.9 is intentionally a LOCAL package updater.

Online automatic download/install is NOT enabled yet.

Code signing + signed update manifests should be added before a public/remote
update channel is enabled.


LIVE-SERVICE SAFETY
-------------------
Update and rollback both call the existing live-output safety check.

They refuse to proceed when:
  OBS Recording is active
  OBS Streaming is active

If OBS appears to be running but SSS cannot verify Recording/Streaming state,
update/rollback is also refused.

The updater NEVER:
  starts Recording
  stops Recording
  starts Streaming
  stops Streaming
  moves PTZ cameras
  advances presentation slides
  changes audio mute
  changes sermon_plan.json


SSS WINDOWS MUST BE CLOSED
--------------------------
The installed Main + Settings EXEs must be closed before their application
folders can be replaced.

Settings ignores its own process during preflight, because it launches the
Updater and then closes itself.

If the Main SSS window is still open, Settings reports the process/PID and asks
you to close it first.

OBS itself may remain open when its live outputs are safely stopped and
verifiable.


PRE-UPDATE APPLICATION BACKUP
-----------------------------
Before replacing any application files, the elevated Updater copies the
currently-installed:

  SundayServiceSystem
  SundayServiceSystemSettings

folders into:

  C:\ProgramData\Sunday Service System\Updates\Rollbacks

This is separate from the v2.4 church configuration Recovery system.

The two recovery layers have different jobs:

  v2.4 Recovery
    SSS scripts/settings/profile rollback

  v2.9 Application Rollback
    installed compiled EXE/application-folder rollback


UPDATE INSTALL FLOW
-------------------
The protected flow is:

  Verified .sssupdate
        |
        v
  Live-output safety check
        |
        v
  Close SSS Main/Settings
        |
        v
  Pre-update application backup
        |
        v
  Install new Main + Settings folders
        |
        v
  Run NEW Main EXE in SAFE HEALTH-CHECK MODE
        |
        +---- PASS ----> keep new version
        |
        +---- FAIL ----> AUTOMATIC ROLLBACK


SAFE POST-UPDATE HEALTH CHECK
-----------------------------
The Updater starts the NEW SundayServiceSystem.exe with:

  --update-health-check

This does NOT launch the normal Sunday dashboard.

The safe health-check path:
  imports the complete Sunday Mode dependency graph
  verifies the application build version
  imports Settings/update modules
  writes a small health-result JSON
  exits

It does NOT:
  create SundayModeApp
  launch OBS
  launch Presenter
  recall the startup PTZ preset
  refresh Gmail
  migrate the active profile
  start/stop Recording
  start/stop Streaming

This means a missing Python dependency like the earlier obsws_python packaging
problem is detected before the new installed version is accepted.


AUTOMATIC ROLLBACK
------------------
If:
  file installation fails
  the new EXE cannot start
  an import fails
  the expected health file is missing
  the reported version is wrong
  the health-check times out

the Updater automatically:

  removes the failed new Main + Settings folders
  restores the pre-update backup
  records ROLLED_BACK state
  reopens Settings from the restored application when possible

The operator does not need to manually copy Program Files folders back.


MANUAL ROLLBACK
---------------
Settings -> Updates also includes:

  ROLL BACK LAST APPLICATION UPDATE

Before manual rollback, SSS creates ANOTHER application backup of the current
version.

If the requested rollback itself fails verification, the updater attempts to
restore that immediately-pre-rollback application state.

This makes rollback reversible instead of destructive.


UPDATE STATE
------------
State is stored under:

  C:\ProgramData\Sunday Service System\Updates

including:
  update_state.json
  Rollbacks
  Staging
  Health

Update state does not contain account passwords or OAuth tokens.


AFTER SUCCESS
-------------
After a successful update, the updater opens:

  SSS Setup & Settings -> Updates

instead of launching the full Sunday Mode dashboard.

That is deliberate.

Opening the full dashboard could recall a startup camera preset or launch
normal Sunday helper applications. The updater does not need to trigger those
actions simply to report that an application update succeeded.


EVENT HISTORY / DIAGNOSTICS
---------------------------
Event History receives an UPDATES category for:
  successful updates
  automatic rollback
  manual rollback
  update failures

Full System Diagnostics now includes:
  Application Runtime
  Application Updater

and checks that the installed Updater EXE is present.


WINDOWS BUILD OUTPUT
--------------------
Run:

  Build-SSS-Windows-Installer.bat

v2.9 builds:

  dist\SundayServiceSystem\
    SundayServiceSystem.exe

  dist\SundayServiceSystemSettings\
    SundayServiceSystemSettings.exe

  dist\SundayServiceSystemUpdater\
    SundayServiceSystemUpdater.exe

and then:

  update-output\
    SundayServiceSystem-Update-v2.9.0.sssupdate

If Inno Setup 6 is installed it also builds:

  installer-output\
    SundayServiceSystem-Setup-v2.9.0.exe


INITIAL v2.8.2 -> v2.9 TEST
--------------------------
If v2.8.2 is already installed:

1. Install this v2.9 PATCH into:
     C:\Church\SermonAI

2. Run:
     Build-SSS-Windows-Installer.bat

3. Close the installed v2.8.2 Main and Settings windows.

4. Make sure OBS Recording and Streaming are STOPPED.

5. Run:
     Apply-Built-v2.9-Update.bat

That BAT:
  finds the installed version
  uses the freshly-built v2.9 Updater EXE
  applies the freshly-built v2.9 .sssupdate package
  uses the same automatic rollback flow

If there is no existing installed SSS, use the v2.9 installer instead.


BUILD PACKAGE ONLY
------------------
After the EXE folders already exist:

  Build-SSS-Update-Package-Only.bat

rebuilds the local .sssupdate package.


PROFILE SCHEMA
--------------
v2.9 does NOT change the profile data structure.

Current schema remains:

  schema_version: 7


WHAT COMES AFTER v2.9
---------------------
The next release-management work should be:

  code-signing foundation
  signed update manifest
  trusted update feed / release channel
  download staging
  updater self-update protocol
  installer/update release signing

Those pieces should be completed before remote one-click updates are enabled.


SAFETY RULE REMAINS
-------------------
Recording and Streaming remain:
  separate
  manual
  human-gated

No v2.9 updater operation starts or stops either output.
