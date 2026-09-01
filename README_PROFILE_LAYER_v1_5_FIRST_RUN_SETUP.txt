SSS PROFILE LAYER v1.5 — FIRST-RUN SETUP

Starts the application-polish roadmap with:
1) First-run setup wizard
2) Profile setup completeness/status

Profile Manager now shows:
  Setup: X/5 complete
and:
  RUN / EDIT SETUP WIZARD

Creating a NEW PROFILE automatically opens the wizard.

Wizard covers:
- Church name
- OBS Legacy/Profile mode
- automatic OBS scene discovery
- presentation software choice
- camera type
- sermon information source
- review/save

OBS can already be profile-backed.
Presentation, camera, and sermon-source choices are metadata only in v1.5.

Safety:
- wizard never starts recording or streaming
- Legacy OBS remains available
- Profile OBS keeps its legacy fallback
- no .env, passwords, OAuth tokens, PTZ runtime file, or sunday_config.json included
- existing Perry integration metadata counts toward setup completeness

Install all files into C:\Church\SermonAI and overwrite matching code files.
