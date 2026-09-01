SSS v2.8 — STANDALONE EXE / INSTALLER FOUNDATION
=================================================

This is the first Windows packaging stage.

It does NOT replace the existing Python launch method automatically. The goal
of v2.8 is to make the current SSS code buildable as real Windows application
executables and an installer while preserving every existing church workflow.


WINDOWS APPLICATIONS
--------------------
The build creates two real GUI executables:

  SundayServiceSystem.exe

  SundayServiceSystemSettings.exe

PyInstaller uses ONEDIR mode rather than ONEFILE.

Reasons:
  faster startup
  simpler support/diagnostics
  fewer antivirus false positives
  easier future updater/rollback work
  Settings can remain a separate real Windows process


STABLE WINDOWS IDENTITY
-----------------------
The application continues using:

  SundayServiceSystem.Desktop

as its Windows AppUserModelID.

With a real EXE, Windows can now identify the running application by its own
executable instead of python.exe/pythonw.exe.

The EXE also receives:
  product version 2.8.0
  file version 2.8.0.0
  Per-Monitor V2 DPI manifest
  long-path awareness
  asInvoker execution level


FROZEN-EXE SETTINGS LAUNCH
--------------------------
The main SSS previously opened Settings by launching:

  pythonw.exe sss_settings.py

That does not work correctly after freezing.

v2.8 adds sss_runtime.py.

Python compatibility mode:
  Sunday Mode
    -> pythonw.exe
    -> sss_settings.py

Installed EXE mode:
  SundayServiceSystem.exe
    -> SundayServiceSystemSettings.exe

Diagnostics, Recovery, Event History, Profile Upgrades, and Security all use
the same frozen-aware Settings launcher.


EXISTING CHURCH COMPATIBILITY
-----------------------------
The current runtime/data root remains:

  C:\Church\SermonAI

for this packaging stage.

This prevents the installer foundation from breaking existing:
  sermon automation
  lower-third helper scripts
  chapter helper scripts
  Planning integration
  PTZ helper scripts
  audio monitor
  YouTube/post-service helpers
  current recording/transcript paths

The installed application itself lives under:

  C:\Program Files\Sunday Service System

The installer creates C:\Church\SermonAI if it is missing but does not delete
it on uninstall.


PROFILES / SECRETS
------------------
Profiles remain under the existing SSS profile system, normally ProgramData.

Windows Credential Manager remains completely outside the installer.

The build/installer deliberately does NOT package:

  .env
  church profile JSON
  sunday_config.json
  ptz_camera_config.json
  sermon_plan.json
  Gmail token
  Gmail credentials
  YouTube OAuth token
  OBS password
  Recovery snapshots
  Event History
  diagnostic ZIPs


SAFE COMPATIBILITY PAYLOAD
--------------------------
Some existing SSS features launch helper scripts by filename from
C:\Church\SermonAI.

During the Windows build, build_sss_windows.py stages ONLY an explicit allow-list
of non-secret helper scripts into:

  installer-payload\RuntimeSupport

It never sweeps the whole SermonAI folder into the installer.

The v2.8 installer uses ONLYIFDOESNTEXIST for those compatibility helpers.

Therefore installing v2.8 over the current church system does not overwrite
the already-working local helper scripts.

This is intentionally conservative for the installer FOUNDATION.

A later production installer/updater can version these helpers explicitly.


BUILD ENVIRONMENT
-----------------
Run on the Windows church/build PC:

  Build-SSS-Windows-Installer.bat

The build creates an isolated environment:

  C:\Church\SermonAI\.sss-build-venv

and installs:

  PyInstaller

into that build-only environment.

It does not install PyInstaller into the production SSS venv.


EXE BUILD OUTPUT
----------------
After PyInstaller succeeds:

  C:\Church\SermonAI\dist\
    SundayServiceSystem\
      SundayServiceSystem.exe
      ...

    SundayServiceSystemSettings\
      SundayServiceSystemSettings.exe
      ...


INSTALLER
---------
The included installer definition uses Inno Setup 6:

  installer\SundayServiceSystem.iss

If Inno Setup 6 is installed, the full build script automatically compiles the
installer after the two EXEs.

Expected output:

  C:\Church\SermonAI\installer-output\
    SundayServiceSystem-Setup-v2.8.0.exe

If Inno Setup is not installed, the EXE build still completes and tells you to
install Inno Setup 6.

After installing Inno Setup, run:

  Build-SSS-Installer-Only.bat


INSTALLER SHORTCUTS
-------------------
The installer creates Start Menu entries for:

  Sunday Service System
  SSS Setup & Settings
  Uninstall Sunday Service System

It optionally creates a Desktop shortcut.


UNINSTALL BEHAVIOR
------------------
Uninstall removes the compiled application from Program Files.

It deliberately does NOT delete:

  C:\Church\SermonAI
  ProgramData SSS profiles
  Windows Credential Manager credentials
  recordings
  sermon files
  Recovery snapshots
  Event History

Compatibility helper files installed on a clean machine are also marked
UNINSNEVERUNINSTALL in this foundation.


INSTALLER DOES NOT CONTROL THE SERVICE
--------------------------------------
The installer is not allowed to automatically close OBS or alter a live
service.

Inno Setup is configured:

  CloseApplications=no
  RestartApplications=no

The optional post-install SSS launch is safe because SSS itself still NEVER
auto-starts Recording or Streaming.


BUILD FILES INCLUDED
--------------------
  sss_build_info.py
  sss_runtime.py
  sss_app.manifest
  sss_version_info.txt
  sss_settings_version_info.txt
  requirements-build.txt
  build_sss_windows.py
  Build-SSS-Windows-Installer.bat
  Build-SSS-Installer-Only.bat
  installer\SundayServiceSystem.iss
  Check-SSS-Installed-App.bat


DIAGNOSTICS
-----------
Full System Diagnostics now includes:

  Application Runtime

Possible result:

  INFO
    SSS 2.8.0 — Python compatibility mode

or:

  READY
    SSS 2.8.0 — Installed Windows EXE


SETTINGS
--------
Settings -> Advanced now shows:

  Version
  Python compatibility mode / Installed Windows EXE
  executable path
  install root

and includes:

  OPEN APPLICATION INSTALL FOLDER


WHAT v2.8 DOES NOT DO YET
-------------------------
This is not yet the final new-PC commercial installer.

The next packaging work still includes:
  fully versioning external compatibility helper scripts
  updater + rollback integration
  signed installer / code signing
  clean first-install dependency/bootstrap experience
  dedicated installed runtime/data path migration
  automatic installer preflight
  production release channel/version metadata

For the current church PC, v2.8 is intentionally designed so the new EXE can be
tested beside the proven Python launch method.


RECOMMENDED TEST ORDER
----------------------
1. Install this v2.8 PATCH into C:\Church\SermonAI as usual.

2. Confirm the existing Python SSS still opens and behaves normally.

3. Run:
     Build-SSS-Windows-Installer.bat

4. After the EXE build, run directly:
     dist\SundayServiceSystem\SundayServiceSystem.exe

5. Verify:
     SSS opens
     Settings opens from the Profile/Admin controls
     Full Diagnostics works
     OBS connects
     Presenter controls work
     Camera controls work
     Audio mute works

6. DO NOT use Recording/Streaming merely to test packaging.
   Those controls remain manual; package validation can be done without
   starting either output.

7. If the EXE test is good, build/install the Inno Setup installer.

8. Run:
     Check-SSS-Installed-App.bat


PROFILE SCHEMA
--------------
v2.8 does not change profile data structure.

Current schema remains:

  schema_version: 7


SAFETY
------
No Sunday behavior changes are intended.

Recording and Streaming remain:
  separate
  manual
  human-gated

v2.8 does not auto-start or auto-stop either output.
