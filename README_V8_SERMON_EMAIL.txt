SUNDAY MODE V8 — FRIDAY SERMON EMAIL → LOWER THIRDS
===================================================

WHAT V8 ADDS
------------
This version connects the sermon plan to the existing lower-third pattern.

When a valid sermon_plan.json exists:

LOWER THIRD 1
  Active:
    Point 1
    Scripture

  Slot 1:
    Point 1
    Scripture

  Slot 2:
    Point 2
    Scripture

  Slot 3:
    Point 3
    Scripture

  ...up to 10 points.

LOWER THIRD 2
  Active:
    Sermon Title
    Scripture

  Slot 1:
    Sermon Title
    Scripture

  Slot 2:
    Sermon Title
    Pastor Philip Lowther

LT3 AND LT4 ARE NOT TOUCHED.

The loader only writes from INSIDE control-panel.html using the same
browser localStorage the lower-thirds system already uses. Python does
not write directly into OBS's LevelDB database.

FILES
-----
gmail_sermon_importer.py
  Reads the latest sermon-notes email using the Gmail API and creates:
    C:\Church\SermonAI\sermon_plan.json

sermon_plan_server.py
  Serves sermon_plan.json only on:
    http://127.0.0.1:8765

sermon_plan_loader.js
  Runs inside the existing lower-thirds control panel and updates LT1/LT2.

install_sermon_plan_loader.py
  Safely patches control-panel.html and backs it up first.

SETUP — LOWER THIRDS
--------------------
1. Copy the V8 files into:
     C:\Church\SermonAI

2. Close OBS.

3. Run:
     Install-Lower-Third-Sermon-Loader.bat

4. The installer makes a backup in:
     C:\Church\SermonAI\LowerThird_Backups

5. Reopen OBS.

SETUP — GMAIL (ONE TIME)
------------------------
The local church PC cannot use ChatGPT's Gmail connection directly.
It needs its own Gmail OAuth token.

You will need a Google OAuth Desktop App credentials JSON file.

Rename that downloaded credentials file to:

  gmail_credentials.json

and place it at:

  C:\Church\SermonAI\gmail_credentials.json

Then run:

  Setup-Gmail-Sermon-Import.bat

That installs Google's Gmail API Python packages, opens a browser for
one-time authorization, saves:

  C:\Church\SermonAI\gmail_token.json

and tests the latest sermon-notes import.

NORMAL SUNDAY USE
-----------------
After the one-time setup:

1. Helper opens START SUNDAY MODE.
2. Sunday Mode starts the local sermon-plan server.
3. Sunday Mode checks the latest recent sermon email.
4. gmail_sermon_importer.py writes sermon_plan.json atomically.
5. The lower-thirds control panel sees the new plan.
6. LT1/LT2 update themselves and reload once.
7. Chapter Bridge uses the OFFICIAL points from sermon_plan.json.
8. LT3/LT4 remain untouched.

EMAIL PARSER
------------
The importer is intentionally tolerant of the formats used in recent
sermon emails:

  Title: ...
  Text: ...

  Outline:
  1. Point
  2. Point

and also messages where the outline lines are not numbered.

The configured sender is:

  pastorlowther@gmail.com

The default lookback is:

  14 days

These are editable in sunday_config.json.

SAFETY
------
- The control-panel HTML is backed up before patching.
- The loader never edits OBS Browser LevelDB directly.
- sermon_plan.json is written to a temporary file first and then replaced.
- LT3/LT4 are untouched.
- The server listens only on 127.0.0.1.
- Sunday Mode does not start the stream automatically.


V9 EMAIL FORMATTING CLEANUP
---------------------------
The Gmail importer now strips literal asterisk emphasis markers that
can survive Gmail/HTML extraction.

Example:
  The Demonic Danger of *Self-Centered Reformation*!
becomes:
  The Demonic Danger of Self-Centered Reformation!

This prevents formatting artifacts from appearing in LT1/LT2,
chapter names, thumbnail prep, or the YouTube package.

If sermon_plan.json was created before V9, run:
  Clean-Current-Sermon-Plan.bat
or simply rerun:
  Import-Latest-Sermon-Email.bat
after installing V9.
