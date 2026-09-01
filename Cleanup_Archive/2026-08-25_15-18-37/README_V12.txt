SUNDAY MODE v12 — EMBEDDED LOWER-THIRD SERMON PLAN
==================================================

WHY V11 DID NOT CHANGE LT1/LT2
------------------------------
V11 proved sermon_plan.json could be converted successfully, but the
OBS Browser dock still did not execute/reload the generated same-folder
JavaScript data file.

V12 removes ALL inter-file communication.

The actual sermon plan JSON is physically written into:
  control-panel.html

before OBS opens it.

There is:
- no localhost server
- no fetch()
- no CORS
- no external sermon-plan JavaScript
- no direct LevelDB writing

NORMAL STARTUP ORDER
--------------------
START SUNDAY MODE
      |
      v
Check/import latest pastor Gmail sermon notes
      |
      v
Write sermon_plan.json
      |
      v
Embed title/Scripture/points into control-panel.html
      |
      v
Launch OBS
      |
      v
Original lower-third page loads
      |
      v
LT1/LT2 populated through the page's own localStorage + refreshData()

MAPPING
-------
LT1:
  Active = Point 1 / Scripture
  Slot 1 = Point 1 / Scripture
  Slot 2 = Point 2 / Scripture
  ...

LT2:
  Active = Sermon Title / Scripture
  Slot 1 = Sermon Title / Scripture
  Slot 2 = Sermon Title / Preacher

LT3/LT4:
  untouched

INSTALL
-------
1. Close OBS.
2. Copy ALL v12 files into:
     C:\Church\SermonAI
3. Run:
     Install-Lower-Third-Sermon-Sync-v12.bat
4. Reopen OBS.

DIAGNOSTIC
----------
Run:
  Check-Lower-Third-Sermon-Embed.bat

Both of these should say YES:
  v12 markers present
  current sermon title physically embedded
  current Scripture physically embedded

ROLLBACK
--------
Close OBS and run:
  Restore-Pre-v12-Control-Panel.bat
