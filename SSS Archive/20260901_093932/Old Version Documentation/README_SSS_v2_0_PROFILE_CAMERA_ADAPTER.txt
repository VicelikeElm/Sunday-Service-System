SSS v2.0 — PROFILE-BACKED CAMERA ADAPTER
=========================================

This implements the next portable-app roadmap item:

  Profile-backed Camera integration


LIVE CAMERA ADAPTERS
--------------------
PTZOptics / HTTP-CGI     READY
Fixed camera              READY (no movement controls)
None                      READY (no camera controls)
VISCA over IP             PLANNED


SETUP & SETTINGS
----------------
Open:

  Profile label
    -> Camera
    -> CONFIGURE CAMERA FOR THIS PROFILE

Camera Setup now contains:

  Configuration Source
    LEGACY
    PROFILE

  Camera Provider
    PTZOptics / HTTP-CGI
    VISCA over IP
    Fixed camera
    None

  Camera IP / host
  HTTP port
  Worship preset
  Pastor preset
  Startup preset
  Recall startup preset when SSS opens

  CHECK CAMERA CONNECTION
  TEST WORSHIP VIEW
  TEST PASTOR VIEW
  SAVE


LEGACY SAFETY
-------------
LEGACY remains the safe path for existing churches.

LEGACY:
  existing machine-local ptz_camera_config.json
    -> existing ptz_camera_control.py
    -> current camera behavior

PROFILE:
  active .sssprofile
    -> sss_camera_adapters.py
    -> selected camera provider

The existing ptz_camera_config.json is NEVER overwritten by Camera Setup.


PTZOPTICS PROFILE CONTROL
-------------------------
The live PTZOptics adapter uses the existing proven HTTP-CGI preset recall:

  /cgi-bin/ptzctrl.cgi?ptzcmd&poscall&<preset>

The main SSS buttons:

  WORSHIP VIEW
  PASTOR VIEW

and the optional startup preset now use the profile adapter when Camera is
explicitly set to PROFILE.


CONNECTION / TEST SAFETY
------------------------
CHECK CAMERA CONNECTION:
  read-only TCP reachability check
  does NOT move the camera

TEST WORSHIP VIEW:
  intentionally recalls the Worship preset

TEST PASTOR VIEW:
  intentionally recalls the Pastor preset

The setup screen clearly labels that preset tests move the camera.


WHY PROFILE FAILURE DOES NOT AUTO-MOVE THE LEGACY CAMERA
--------------------------------------------------------
OBS can safely fall back to a known local scene/hotkey.

A camera is different: on a portable/new-church installation, a stale legacy
camera address could point to the wrong physical device.

Therefore:
  LEGACY is always available as an explicit fallback
  PROFILE failures are reported
  SSS does NOT silently move a different legacy camera after a PROFILE failure

This is safer for a portable multi-church application.


CAPABILITY-BASED UI
-------------------
If Camera is:

  PROFILE + Fixed camera
or
  PROFILE + None

the entire CAMERA VIEW workflow row is automatically removed from the
volunteer SSS dashboard and the remaining steps are renumbered.

PTZOptics keeps the Camera row visible unless the profile's volunteer
capability setting explicitly disables camera controls.


SYSTEM STATUS
-------------
In PROFILE PTZOptics mode, Camera status checks the profile camera connection.

It no longer relies on the old legacy PTZ status file for a profile-backed
camera.

Fixed camera / None report as valid configurations with no PTZ controls.


FIRST-RUN WIZARD
----------------
The wizard still chooses the church's Camera provider.

Changing provider in the general wizard does NOT silently activate a new live
camera adapter. If a live PROFILE camera was configured and the provider is
changed, Camera returns to the safe LEGACY path until Camera Setup is tested
and PROFILE is explicitly saved again.


DIAGNOSTIC
----------
Included:

  Test-Camera-Connection.bat

It checks the active PROFILE PTZOptics host/port without moving the camera.


UNCHANGED
---------
Recording and streaming remain separate, manual, human-gated controls.

This patch does not change:
  OBS behavior
  Presentation behavior
  audio
  sermon email / Planning
  chapters / lower thirds
  YouTube
  Sermon AI

No profile JSON, ptz_camera_config.json, sunday_config.json, .env, passwords,
OAuth tokens, or Gmail credentials are included.


INSTALL
-------
Close SSS and Settings.

Copy all files from this ZIP into:

  C:\Church\SermonAI

Overwrite matching code files.

Then:
  SSS -> click Profile -> Camera
