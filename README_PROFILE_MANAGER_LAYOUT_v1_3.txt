SSS PROFILE LAYER v1.3 — PROFILE CONTROLS MOVED INTO MANAGER

MAIN SSS
--------
The main Sunday Service System now shows only:

  Profile: Baptist Church of Perry

There is no profile dropdown, ADD PROFILE button, or MANAGE button on the
volunteer-facing dashboard.

The profile label itself is clickable and opens Profile Manager.

PROFILE MANAGER
---------------
All profile controls now live in the Profile Manager window.

At the top:

  Select Church Profile
  [ Baptist Church of Perry ▼ ]

Then the existing profile details and buttons:

  NEW PROFILE
  EXPORT PROFILE
  IMPORT PROFILE
  OPEN PROFILE FOLDER

Selecting another profile immediately changes the persistent active profile.
When the main SSS window regains focus, its simple profile label refreshes.

SAFE COMPATIBILITY MODE
-----------------------
This still does not change any live OBS, Presenter, MIDI, PTZ, recording,
streaming, sermon, Planning, chapter, lower-third, audio, YouTube, or Sermon AI
settings. Existing Sunday configuration remains authoritative.

INSTALL
-------
Close SSS and Profile Manager. Copy into C:\Church\SermonAI and overwrite:

  sunday_mode.py
  sss_profile_manager.py
  sss_profile.py

No live configuration files are included or changed.
