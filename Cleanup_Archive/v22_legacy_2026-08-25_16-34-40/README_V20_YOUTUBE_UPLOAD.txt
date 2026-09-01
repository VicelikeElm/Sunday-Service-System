SUNDAY MODE v20 — AUTOMATIC FULL-SERMON YOUTUBE UPLOAD
======================================================

WHAT GETS UPLOADED
------------------
Only the original full OBS sermon recording directly inside:

  D:\2026

The uploader does NOT recurse into subfolders and therefore will not
upload:
- shorts
- Ready clips
- SRT files
- Sermon Data
- trimmed/rendered sermon versions

HOW IT AVOIDS A 2-SECOND MISCLICK
---------------------------------
The automatic uploader requires ALL of these:

1. sermon_plan.json service_date must equal today.
2. Recording must be directly inside D:\2026.
3. Filename must begin with the same service date:
     YYYY-MM-DD ...
4. File must be at least 500 MB by default.
5. Video duration must be at least 20 minutes by default.
6. File must be unchanged/stable for 5 minutes.
7. Automatic mode only considers recordings that ended near or after
   the recording-stop event that woke the worker.
8. If several files qualify, the LARGEST eligible file wins.
9. Upload history prevents a duplicate sermon upload.

A tiny accidental Record/Stop file cannot qualify.

If someone accidentally stops recording early and later records the real
sermon, the worker waits for up to 6 hours. The later full recording can
become the valid candidate after it finishes.

YOUTUBE LABEL / TITLE
---------------------
The uploaded YouTube title is taken from the pastor email:

  sermon_plan.json -> title

It does not use the OBS filename and does not generate a shorts title.

The description contains:
- sermon title
- Scripture
- preacher if available
- sermon outline

AUTOMATIC TRIGGER
-----------------
The worker starts when recording stops.

It works when:
- STOP RECORDING is pressed in SSS
- recording is stopped directly in OBS, if SSS observed the transition

SSS gets a new preflight row:

  YouTube sermon upload

Typical states:
- setup required
- authorized — waiting for sermon
- waiting for full-size stable recording
- uploading — 42%
- retrying
- uploaded
- uploaded but YouTube forced it private

ONE-TIME SETUP
--------------
1. In the same Google Cloud project already used for Gmail, enable:

     YouTube Data API v3

2. Copy all v20 files to:

     C:\Church\SermonAI

3. Run:

     Setup-YouTube-Upload.bat

4. Sign into the Google account that owns/manages the church YouTube
   channel.

The setup reuses the existing OAuth CLIENT file:

  gmail_credentials.json

but creates a separate YouTube TOKEN:

  youtube_token.json

It also saves:

  youtube_channel.json

The uploader checks that channel identity before every upload so a
different Google/YouTube account cannot silently receive the sermon.

PUBLIC / PRIVATE
----------------
sunday_config.json currently requests:

  "youtube_privacy_status": "public"

YouTube may force API uploads to PRIVATE if the Google Cloud project is
not verified for public YouTube uploads. If that happens, the video is
still uploaded, SSS reports the condition, and the video ID/URL is
saved.

MANUAL TEST / FALLBACK
----------------------
Preview-YouTube-Sermon-Candidate.bat

  Does NOT upload anything. It shows the file that would be selected.

Upload-Current-Sermon-To-YouTube.bat

  Manual fallback upload. It still enforces date, size, duration,
  stability, largest-file selection, and duplicate protection.

FILES CREATED DURING USE
------------------------
youtube_token.json
  YouTube OAuth authorization.

youtube_channel.json
  Authorized church channel identity.

youtube_upload_status.json
  Current upload status shown by SSS.

youtube_upload_history.json
  Successful upload history/video IDs. Prevents duplicates.

youtube_upload.log
  Upload/retry log.

DEFAULT SAFETY THRESHOLDS
-------------------------
youtube_min_file_mb:              500
youtube_min_duration_minutes:     20
youtube_file_stable_seconds:      300
youtube_trigger_lookback_minutes: 15
youtube_candidate_wait_minutes:   360

These are editable in sunday_config.json.
