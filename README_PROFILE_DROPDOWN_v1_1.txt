SSS PROFILE LAYER v1.1 — MAIN-WINDOW DROPDOWN
==============================================

The static:

  Profile: Baptist Church of Perry

label is now a real selector:

  Profile: [ Baptist Church of Perry ▼ ] [ MANAGE ]


WHAT THE DROPDOWN DOES
----------------------
It lists every valid profile installed in the SSS Profiles folder.

Selecting another profile changes the persistent ACTIVE PROFILE pointer.

The next time SSS opens, that profile stays selected.


IMPORTANT — STILL ZERO LIVE BEHAVIOR CHANGE
-------------------------------------------
Profile Layer v1.1 is still compatibility-only.

Changing the dropdown does NOT yet change:
  OBS
  scene names
  recording
  streaming
  Presenter
  MIDI
  PTZ
  sermon email
  Planning
  chapters
  lower thirds
  audio
  YouTube
  Sermon AI

Your current existing configuration remains authoritative.


MANAGE BUTTON
-------------
The new MANAGE button opens the Profile Manager.

From there you can:
  EXPORT PROFILE
  IMPORT PROFILE
  OPEN PROFILE FOLDER

After importing a profile, click/open the dropdown again. It refreshes its
profile list automatically; SSS does not need to be restarted.


WHY ONLY ONE ITEM MAY SHOW RIGHT NOW
------------------------------------
At first the dropdown will probably contain only:

  Baptist Church of Perry

That is expected.

Once another .sssprofile is imported, both churches will appear in the same
dropdown.


PERSISTENCE
-----------
The selected profile is remembered outside normal patch ZIPs.

Future updates should not overwrite it.


INSTALL
-------
Close SSS.

Copy into:
  C:\Church\SermonAI

and overwrite:
  sunday_mode.py
  sss_profile.py
  sss_profile_manager.py

Open-SSS-Profile-Manager.bat can remain from v1.

No existing live configuration files are included or changed.
