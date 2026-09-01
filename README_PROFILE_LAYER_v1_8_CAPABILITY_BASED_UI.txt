SSS PROFILE LAYER v1.8 — CAPABILITY-BASED VOLUNTEER UI
======================================================

This implements the next application-polish roadmap item:

  Capability-based UI

The goal is simple:
  a church only sees volunteer controls that it actually uses.


PROFILE MANAGER
---------------
New button:

  CONFIGURE VOLUNTEER CONTROLS

Open it to choose:

  LEGACY
    Show the complete current SSS volunteer workflow.

  PROFILE
    Show only the controls enabled for this church.


PROFILE CAPABILITIES
--------------------
The current configurable controls are:

  Recording controls
    START RECORDING
    STOP RECORDING

  Streaming controls
    START STREAM
    STOP STREAM

  Program audio mute
    MUTE AUDIO / UNMUTE AUDIO

  Scripture controls
    Scripture START / NEXT / END workflow

  Sermon controls
    chapter / lower-third row

  Camera controls
    WORSHIP VIEW / PASTOR VIEW


DYNAMIC WORKFLOW
----------------
When PROFILE mode hides a complete workflow section, SSS removes that row
from the volunteer dashboard and renumbers the remaining visible steps.

Example church:
  recording = ON
  streaming = OFF
  scripture = ON
  sermon controls = OFF
  camera controls = OFF

Volunteer dashboard becomes roughly:

  1 — SERVICE PREP
  2 — LIVE A/V
      START RECORDING
  3 — SCRIPTURE
  4 — END SERVICE
      STOP RECORDING

No blank numbered gaps remain.


LEGACY SAFETY
-------------
Existing profiles that predate v1.8 automatically behave as LEGACY.

That means installing this patch CANNOT make controls disappear from the
existing Perry Sunday screen unless PROFILE capability mode is deliberately
selected and saved.

LEGACY always forces all existing volunteer controls visible.


VISIBILITY ONLY
---------------
Capability settings control the volunteer UI only.

They do NOT:
  start or stop recording
  start or stop streaming
  change OBS scenes
  send presentation commands
  move cameras
  change chapter state
  change lower thirds
  change audio

Admin / Troubleshooting always remains available.


END SERVICE ADAPTS
------------------
If the profile uses both Streaming and Recording:
  "Stream first, then Recording"

Recording only:
  "Finish by stopping Recording"

Streaming only:
  "Finish by stopping Stream"


CURRENT PORTABLE APP PROGRESS
-----------------------------
Profile Layer:
  READY

Profile create/import/export/switch:
  READY

First-run setup wizard:
  READY

OBS profile discovery / mapping:
  READY

Presentation adapter architecture:
  READY

WorshipTools Presenter adapter:
  READY

ProPresenter API adapter:
  READY

Capability-based volunteer UI:
  READY

Next roadmap item:
  Full SSS Setup / Settings application structure
  (Church, OBS, Presentation, Camera, Audio, Sermon, Streaming,
   Automation, Advanced)


INSTALL
-------
Close SSS and Profile Manager.

Copy all files from this ZIP into:

  C:\Church\SermonAI

Overwrite matching code files.

No profiles, credentials, .env, Gmail tokens, PTZ runtime settings,
or sunday_config.json are included.
