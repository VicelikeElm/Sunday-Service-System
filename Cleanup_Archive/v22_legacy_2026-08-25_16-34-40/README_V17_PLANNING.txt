SUNDAY MODE v17 — WORSHIPTOOLS PLANNING SCRIPTURE SYNC
======================================================

WHAT THE DIAGNOSTICS CONFIRMED
------------------------------
The upcoming WorshipTools service contains a Sermon section with the
expected church pattern:

  Sermon
    [blank]
    Scripture item

The Scripture edit dialog exposes:
- Book
- From chapter
- From verse
- To chapter
- To verse
- Save / Cancel

V17 uses that structure.

NEW SERMON PLAN DATE GUARD
--------------------------
The Gmail importer now adds:

  service_date

to sermon_plan.json.

It is calculated from the pastor email's received date: the first
Sunday on/after that email.

Planning WILL NOT be changed unless:

  sermon_plan.json service_date
            ==
  today's Sunday / upcoming Sunday

This prevents an old pastor email from changing a future service.

EXAMPLE RIGHT NOW
-----------------
The currently loaded old sermon:
  Matthew 12:43-50

belongs to the prior Sunday.

The Planning service being prepared:
  August 30

contains:
  Matthew 9:1-4 (ESV)

After installing v17, rerun:
  Import-Latest-Sermon-Email.bat

The old email should receive its real service_date, and the Planning
updater should safely report that it belongs to the previous Sunday and
leave Aug 30 untouched.

NORMAL SSS STARTUP
------------------
1. Import latest pastor sermon email.
2. Embed title/outline into LT1/LT2.
3. Launch/check OBS.
4. In the background, check WorshipTools Planning.
5. If the pastor email belongs to the upcoming Sunday:
     - find that Sunday's Planning service
     - find Sermon
     - find exactly one Scripture item near Sermon
     - update the reference
     - keep the existing ESV translation
     - Save
     - verify the new reference
6. Presenter receives WorshipTools' normal Planning sync.

SAFETY
------
The updater refuses to save if:
- sermon_plan.json has no service_date
- email service_date does not equal the Sunday being prepared
- upcoming Sunday service cannot be identified
- the opened service date does not match
- Sermon cannot be uniquely identified
- exactly one Scripture item is not found near Sermon
- the Scripture editor layout does not match the diagnostic
- Save cannot be verified afterward

PLANNING STATUS IN SSS
----------------------
A new preflight row appears:

  Planning sermon Scripture

Green:
  UPDATED
  ALREADY_CORRECT

Yellow:
  old sermon email
  login needed
  service not found
  any condition where Planning was intentionally left unchanged

MANUAL BUTTON
-------------
SSS now has:

  SYNC PLANNING SCRIPTURE

for a manual retry.

MANUAL TOOLS
------------
Planning-Update-Sermon.bat
  Normal automatic/headless update.

Planning-Update-Sermon-Show.bat
  Show Chrome/Edge for login or troubleshooting.

Planning-Update-Sermon-Dry-Run.bat
  Open and fill the Scripture editor but click Cancel instead of Save.

FIRST INSTALL
-------------
1. Copy all v17 files into:
     C:\Church\SermonAI

2. Run:
     Setup-Planning-Automation.bat

3. Run:
     Import-Latest-Sermon-Email.bat

   Confirm it now prints:
     Service date: YYYY-MM-DD

4. Run:
     Planning-Update-Sermon.bat

For the current old sermon email, the expected result is a safe SKIPPED
message because the email belongs to the previous Sunday.

After the next correct pastor email arrives, SSS can perform the real
Planning Scripture update automatically.
