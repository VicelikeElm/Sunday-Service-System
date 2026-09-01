SSS v1.9 — SETUP & SETTINGS APPLICATION SHELL

This implements the next polish roadmap item: a real Settings application.

Main SSS:
Clicking the active Profile label now opens SSS SETUP & SETTINGS.
If the new Settings shell is missing, SSS falls back to the existing Profile Manager.

Settings sections:
- Church
- OBS
- Presentation
- Camera
- Audio
- Sermon
- Streaming
- Automation
- Advanced

Church:
- active profile
- setup completeness
- first-run wizard
- create/import/export profiles
- open profile folder

OBS:
- Legacy/Profile source
- scene collection
- normal scene
- Scripture scene
- launches the existing proven OBS setup dialog

Presentation:
- Legacy/Profile source
- provider
- ProPresenter host/port when applicable
- launches the existing presentation setup dialog

Camera:
- permanent Settings home now exists
- current Perry PTZ live path is NOT changed in v1.9
- portable camera adapter is the logical next integration step

Audio:
- current volunteer audio-mute capability
- existing live meter/mute behavior stays unchanged
- future profile-backed audio mappings live here

Sermon:
- sermon information source
- Scripture controls
- sermon chapter/lower-third controls
- existing Gmail, Planning, chapter, lower-third, and Sermon AI behavior stays unchanged

Streaming:
- recording controls enabled/disabled
- streaming controls enabled/disabled
- recording and streaming remain separate manual human-gated buttons

Automation:
- permanent home for sermon-plan import, Planning sync, YouTube/post-service,
  startup helpers, and optional automation
- v1.9 does not migrate production automation yet

Advanced:
- compatibility mode
- active profile path
- profile root
- export / volunteer visibility controls

Architecture:
sss_profile_manager.py is retained as the proven setup-dialog implementation.
sss_settings.py is the new organized Settings shell and reuses those dialogs.

No profiles, credentials, .env, Gmail tokens, OBS passwords, PTZ runtime
settings, or sunday_config.json are included.
