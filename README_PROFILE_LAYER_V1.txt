SUNDAY SERVICE SYSTEM — PROFILE LAYER v1
=========================================

GOAL
----
Start turning the current Perry SSS into a portable church application
WITHOUT changing how the existing Perry Sunday system behaves.

THIS VERSION IS DELIBERATELY A FOUNDATION
-----------------------------------------
The active profile is loaded and displayed, but it does NOT yet override:

  OBS settings
  recording / streaming
  Presenter MIDI
  PTZ settings
  sermon email
  Planning
  lower thirds
  chapter markers
  audio
  YouTube
  Sermon AI

Your existing files remain authoritative.

That means this first profile step should be extremely low-risk.


WHAT HAPPENS ON FIRST START
---------------------------
If SSS has never created a profile layer before, it automatically creates:

  Baptist Church of Perry

Compatibility mode:
  legacy_existing_configuration

SSS then displays:

  Profile: Baptist Church of Perry

near the top of the main window.

The profile file is stored persistently outside normal patch ZIPs.

Preferred location:
  C:\ProgramData\Sunday Service System\Profiles\

If Windows does not allow that location yet, SSS automatically falls back to:

  %LOCALAPPDATA%\Sunday Service System\Profiles\

or:
  C:\Church\SermonAI\Profiles\

Future SSS patches should NOT overwrite that runtime profile.


.SSSPROFILE EXPORT
------------------
Run:

  Open-SSS-Profile-Manager.bat

It provides:

  EXPORT PROFILE
  IMPORT PROFILE
  OPEN PROFILE FOLDER

Exported profiles use:

  .sssprofile

The exported profile NEVER includes:
  passwords
  OBS WebSocket password
  Gmail OAuth token
  API tokens
  .env contents
  credentials


WHY IMPORT IS SAFE IN v1
------------------------
Imported profiles become the active profile identity, but Profile Layer v1
still leaves the existing live church configuration authoritative.

So this lets us prove:
  profile creation
  profile persistence
  import/export
  Windows paths
  schema/version handling

before allowing profiles to control any Sunday hardware.


WINDOWS APP IDENTITY
--------------------
This patch also gives the running Python SSS process the explicit Windows ID:

  SundayServiceSystem.Desktop

This is groundwork for the future:

  SundayServiceSystem.exe

It helps Windows recognize SSS as one application instead of treating the UI
as an arbitrary Python window.

We have NOT changed the current launch method or installed anything yet.


NEXT PROFILE MIGRATION STEPS
----------------------------
Once this foundation is confirmed working, settings can move into the profile
one safe category at a time.

Suggested order:

  1. Church identity / UI
  2. OBS connection + discovered scenes
  3. Presentation adapter
     - ProPresenter
     - WorshipTools Presenter
     - Companion
  4. Camera / PTZ
  5. Audio sources
  6. Sermon information source
  7. Optional advanced modules

Each category can keep a LEGACY / PROFILE toggle during migration so the
existing Perry setup always has a rollback path.


INSTALL
-------
Close SSS.

Copy into:
  C:\Church\SermonAI

and overwrite:
  sunday_mode.py

Also copy:
  sss_profile.py
  sss_profile_manager.py
  Open-SSS-Profile-Manager.bat

Then reopen SSS.

You should see:
  Profile: Baptist Church of Perry

No existing configuration files are included or changed.
