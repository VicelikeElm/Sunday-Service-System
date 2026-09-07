SSS PROFILE LAYER v1.4 — PROFILE-BACKED OBS SETUP
==================================================

WHAT IS NEW
-----------
Profile Manager now has:

  CONFIGURE OBS FOR THIS PROFILE

That opens a dedicated OBS setup window for the currently selected church.


SAFE LEGACY / PROFILE SWITCH
----------------------------
Every church profile has an OBS configuration source:

  LEGACY
    Uses the current working SSS / sunday_config OBS behavior.
    This is the default for Baptist Church of Perry.

  PROFILE
    Uses the active profile's scene collection and direct OBS scene mappings.

Nothing switches to PROFILE automatically. It must be explicitly selected
and saved in Profile Manager.


AUTOMATIC OBS DISCOVERY
-----------------------
Open OBS and click:

  CONNECT & DISCOVER OBS

SSS reads OBS WebSocket and populates dropdowns for:

  Scene collection
  Normal / webcam scene
  Scripture / presentation scene
  Main / sermon scene (optional / saved for later)

For the current Perry system it will try to recognize familiar names such as:

  webcam only
  webcam TP

but the user always sees and chooses from the actual OBS scene list.


WHAT PROFILE MODE DOES NOW
--------------------------
The first real profile-backed OBS behavior is the Scripture transition.

START SCRIPTURE
  PROFILE:
    selected Scripture / presentation scene -> OBS Preview by WebSocket
    Ctrl+Shift -> transition Preview to Program

  LEGACY:
    existing Ctrl+F15 behavior
    Ctrl+Shift -> transition Preview to Program

END SCRIPTURE
  PROFILE:
    selected Normal / webcam scene -> OBS Preview by WebSocket
    Ctrl+Shift -> transition Preview to Program

  LEGACY:
    existing Ctrl+F13 behavior
    Ctrl+Shift -> transition Preview to Program


AUTOMATIC FALLBACK
------------------
Even when PROFILE is selected, if SSS cannot load the mapped scene by
OBS WebSocket, it immediately falls back to the existing legacy hotkey:

  Scripture failure -> Ctrl+F15 fallback
  Normal failure    -> Ctrl+F13 fallback

Ctrl+Shift still performs the actual transition afterward.

This gives Perry a safety net while we migrate.


SCENE COLLECTION
----------------
LEGACY mode:
  uses the existing sunday_config scene_collection.

PROFILE mode:
  uses the active profile's saved scene collection.

The main SSS System Status now displays the actual scene collection name,
which also makes sense for churches that do not call theirs "Church".


SAFE PREVIEW TESTS
------------------
OBS Setup includes:

  TEST NORMAL IN PREVIEW
  TEST SCRIPTURE IN PREVIEW

These only load the selected scene into OBS Preview.
They do NOT transition it to Program.

Preview tests are blocked while OBS is recording or streaming.


CREDENTIALS / EXPORT SAFETY
---------------------------
OBS WebSocket credentials still come from this PC's existing local SSS
configuration/.env.

They are NOT stored in the .sssprofile file and are NOT exported.

A future installer/setup step can add per-PC local credential setup without
putting passwords into portable church profiles.


READ-ONLY DIAGNOSTIC
--------------------
Included:

  Test-SSS-OBS-Discovery.bat

It prints the OBS endpoint, collection, Program/Preview scene, all scene
collections, and all scenes. It does not transition or start/stop anything.


INSTALL
-------
Close SSS and Profile Manager.

Copy into:
  C:\Church\SermonAI

and overwrite/add:
  sunday_mode.py
  sss_profile.py
  sss_profile_manager.py
  sss_obs_profile.py
  test_sss_obs_discovery.py
  Test-SSS-OBS-Discovery.bat

No sunday_config.json, .env, PTZ settings, credentials, or runtime profile
files are included or overwritten.


RECOMMENDED FIRST PERRY TEST
----------------------------
1. Leave configuration source on LEGACY and save.
2. Confirm normal SSS behavior is unchanged.
3. Open Profile Manager -> CONFIGURE OBS FOR THIS PROFILE.
4. CONNECT & DISCOVER OBS.
5. Confirm the dropdowns contain the expected scenes.
6. Use TEST NORMAL IN PREVIEW / TEST SCRIPTURE IN PREVIEW.
7. Only after those are correct, select PROFILE and SAVE OBS SETTINGS.

At any point, switch back to LEGACY for the old known-good behavior.
