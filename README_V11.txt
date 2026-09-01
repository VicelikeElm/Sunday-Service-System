SUNDAY MODE v11 — LOCAL LOWER-THIRD SERMON SYNC
================================================

WHY v10 DID NOT POPULATE LT1/LT2
--------------------------------
The lower-thirds control panel is a file:// page inside OBS Chromium.

V10 attempted to fetch:
  http://127.0.0.1:8765/sermon-plan

The panel itself stayed working, but OBS Chromium can block or restrict
file:// pages from fetching localhost/private-network HTTP resources.

V11 removes that dependency entirely.

HOW V11 WORKS
-------------
sermon_plan.json
      |
      v
sync_sermon_plan_to_lower_thirds.py
      |
      v
C:\Users\Vicel\Documents\Animated-Lower-Thirds\lower thirds\
    sermon-plan-data.js
      |
      v
control-panel.html loads that SAME-FOLDER JavaScript file
      |
      v
LT1 / LT2 update through the panel's native localStorage + refreshData()

No localhost HTTP fetch is used.

MAPPING
-------
LT1:
  Active = Point 1 / Scripture
  Slots 1..N = official points / Scripture

LT2:
  Active = Sermon Title / Scripture
  Slot 1 = Sermon Title / Scripture
  Slot 2 = Sermon Title / Preacher

LT3 / LT4 are untouched.

INSTALL
-------
1. Close OBS.

2. Copy all normal v11 Python/JSON/BAT files into:
     C:\Church\SermonAI

3. From the extracted v11 package run:
     Install-Lower-Third-Sermon-Sync-v11.bat

4. Run:
     C:\Church\SermonAI\Sync-Current-Sermon-Plan.bat

   It should say that it wrote:
     ...\lower thirds\sermon-plan-data.js

5. Reopen OBS.

6. Launch Sunday Mode.

The lower-third panel checks the same-folder plan file every 3 seconds,
so LT1/LT2 can update even if OBS was already open.

GMAIL
-----
The updated gmail_sermon_importer.py automatically writes both:
  C:\Church\SermonAI\sermon_plan.json

and:
  ...\lower thirds\sermon-plan-data.js

So future Friday/Sunday imports stay synchronized automatically.

SAFETY
------
- The actual uploaded Animated Lower Thirds v1.6 control panel was used.
- No LevelDB writing.
- No localhost HTTP access from OBS Browser.
- No page reload loop.
- LT3/LT4 untouched.
- LT1/LT2 will not be replaced while either is switched ON.
- Backup is created before installing.

ROLLBACK
--------
Close OBS and run:
  Restore-Pre-v11-Control-Panel.bat
