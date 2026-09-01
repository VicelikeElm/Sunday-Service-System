SUNDAY MODE v21 — YOUTUBE STUDIO AUTOMATIC SERMON UPLOAD
=========================================================

CHANNEL LOCK CONFIRMED BY THE DIAGNOSTIC
----------------------------------------
YouTube Studio identified:

  Channel ID:
    UCXwqRxA_JKNM3g6JDe76DcQ

  Channel name:
    Baptist Church of Perry

  Permission:
    You're a manager

V21 hard-locks uploads to BOTH the exact channel ID and the visible
channel name/Manager role.

If any of those checks fail, NO FILE is selected and NO UPLOAD starts.

WHY CHANNEL ID IS THE PRIMARY LOCK
----------------------------------
The Studio dashboard did not display @baptistchurchofperry in its
visible dashboard text, but its URL contains the exact channel ID.

Channel IDs are stronger than names/handles because names and handles
can be changed. V21 therefore requires:

  URL channel ID = UCXwqRxA_JKNM3g6JDe76DcQ
  AND visible name = Baptist Church of Perry
  AND visible permission = You're a manager

FULL SERMON SELECTION
---------------------
Only files directly inside:

  D:\2026

are considered.

Requirements:
- sermon_plan service_date = today
- filename date = sermon service date
- minimum size = 500 MB
- minimum duration = 20 minutes
- unchanged/stable for 5 minutes
- automatic stop-event time window
- largest qualifying file wins

No shorts or generated subfolder files are scanned.

YOUTUBE TITLE
-------------
Title is always:

  sermon_plan.json -> title

which comes from the pastor's sermon-notes email.

DESCRIPTION
-----------
V21 fills:
- pastor sermon title
- Scripture
- preacher if available
- sermon outline

AUDIENCE / MADE FOR KIDS
------------------------
V21 intentionally does NOT assume the legal audience classification.

Current config:

  "youtube_audience": "channel_default"

If YouTube Studio already has an audience choice selected from the
channel's upload defaults, V21 preserves it.

If Studio requires an audience choice and no default is selected, V21
STOPS before publishing and reports the issue.

Possible explicit settings, if you later choose one:

  "channel_default"
  "not_made_for_kids"
  "made_for_kids"

VISIBILITY
----------
Current setting:

  "youtube_privacy_status": "public"

NORMAL FLOW
-----------
STOP RECORDING
  ↓
Studio worker starts
  ↓
wait for valid full sermon file
  ↓
verify church channel ID/name/Manager role
  ↓
select D:\2026 sermon
  ↓
title = pastor's message
  ↓
description = Scripture + outline
  ↓
preserve/verify audience setting
  ↓
Next → Video elements → Checks → Visibility
  ↓
stop if YouTube reports a blocking issue
  ↓
Public
  ↓
Publish/Save
  ↓
record video ID/URL
  ↓
duplicate protection for future runs

FIRST TEST
----------
Before Sunday, run:

  Preview-YouTube-Studio-Sermon-Candidate.bat

This does NOT open Studio or upload anything. It only shows which
D:\2026 recording passes the safety rules.

MANUAL FALLBACK
---------------
  Upload-Current-Sermon-To-YouTube-Studio.bat

This runs the same production upload with all safeguards.

DRY RUN
-------
  YouTube-Studio-Upload-Dry-Run.bat

This is NOT a zero-upload test: it selects the video file in Studio and
the browser may begin transferring it. It stops before Next/Publish.
Only use it intentionally.

PROFILE
-------
Dedicated browser profile:

  C:\Church\SermonAI\YouTube_Studio_Profile

If login expires, run:

  Open-YouTube-Studio-Normal-Login.bat

and sign in normally with the manager account.

IMPORTANT
---------
The old YouTube Data API uploader is no longer used by SSS in v21.
The file may still be present for rollback/history, but SSS invokes:

  youtube_studio_upload_worker.py
