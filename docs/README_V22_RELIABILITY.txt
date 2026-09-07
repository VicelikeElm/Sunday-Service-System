SUNDAY SERVICE SYSTEM v22 — RELIABILITY & RECOVERY SUITE
================================================================

V22 IS BUILT ON THE WORKING V21 YOUTUBE STUDIO VERSION.

The goal of v22 is not to add more volunteer work. It is to make the
existing automation recoverable, verifiable, and difficult to break.

----------------------------------------------------------------
1. POST-SERVICE "EVERYTHING FINISHED" SUPERVISOR
----------------------------------------------------------------
When recording stops, SSS starts post_service_supervisor.py.

It tracks:
  Recording finished/stable
  Full sermon SRT
  Sermon AI / shorts processing
  Embedded MP4 chapter markers
  WorshipTools Planning status
  YouTube Studio upload
  Thumbnail handoff

When all blocking jobs finish, SSS displays an automatic summary.

Successful result:
  EVERYTHING FINISHED
  Safe to shut down.

If processing is finished but an important item needs review, SSS shows
POST-SERVICE REVIEW instead of falsely declaring success.

Status file:
  C:\Church\SermonAI\State\post_service_status.json


----------------------------------------------------------------
2. YOUTUBE DESCRIPTION + CHAPTER TIMESTAMPS
----------------------------------------------------------------
The YouTube Studio uploader still uploads ONLY the original full OBS
recording in D:\2026.

Before filling the YouTube description, v22 runs ffprobe against the
embedded MP4 chapters.

The description can now contain:
  Pastor sermon title
  Scripture
  Preacher
  Sermon outline
  Chapters / timestamps

If the first embedded chapter does not begin at 0:00, v22 adds:
  0:00 Sermon

No trimmed sermon is created.


----------------------------------------------------------------
3. THUMBNAIL HANDOFF
----------------------------------------------------------------
After the full transcript exists, v22 creates:

  D:\2026\shorts\ai shorts\Sermon Data\
      YYYY-MM-DD_Thumbnail_Handoff\

Containing:
  sermon_title.txt
  scripture.txt
  outline.txt
  transcript_excerpt.txt
  thumbnail_prompt.txt

This keeps thumbnail work separate from the volunteer Sunday workflow.


----------------------------------------------------------------
4. CRASH / REBOOT RECOVERY
----------------------------------------------------------------
When SSS starts, it checks for unfinished post-service work.

If a valid sermon recording exists and the current sermon has unfinished
YouTube/post-processing work, SSS resumes the supervisor.

YouTube recovery may continue for up to 3 days after the service date.
The file must STILL match the sermon plan's service date and all normal
size/duration safeguards.

This allows recovery after:
  Windows reboot
  SSS crash
  internet outage
  YouTube Studio temporary failure


----------------------------------------------------------------
5. AUTOMATIC WEEKLY SNAPSHOTS
----------------------------------------------------------------
SSS creates rollback copies under:

  C:\Church\SermonAI\Weekly_Backups\YYYY-MM-DD\

Two snapshots are taken:
  pre_start
  current

Important plan/config/status/scripts are copied.

Default retention:
  12 weeks


----------------------------------------------------------------
6. SUNDAY FREEZE
----------------------------------------------------------------
When recording or streaming is active, SSS creates:

  C:\Church\SermonAI\State\Sunday_Freeze.json

The Admin window visibly reports that Sunday Freeze is active.

SSS operational actions remain available for recovery, but configuration
and cleanup work should wait until the service ends.


----------------------------------------------------------------
7. VOLUNTEER VS ADMIN
----------------------------------------------------------------
Normal screen:
  LAUNCH SUNDAY APPS
  RUN PREFLIGHT
  START / STOP RECORDING
  START / STOP STREAM
  EMERGENCY MUTE
  ADD MANUAL CHAPTER
  ADMIN / TROUBLESHOOTING

Planning sync, YouTube retry, snapshots, logs, test mode, and login
maintenance are moved into ADMIN / TROUBLESHOOTING.


----------------------------------------------------------------
8. ACTION CENTER
----------------------------------------------------------------
Admin contains:
  WHAT NEEDS ATTENTION?

It shows current yellow/red items plus a suggested next action.

Examples:
  YouTube login expired
    -> Open YouTube Studio login

  Internet offline
    -> Local recording is safe; leave SSS running for retry

  Recording file stalled
    -> Check D:\2026 immediately


----------------------------------------------------------------
9. RECORDING FILE GROWTH WATCHDOG
----------------------------------------------------------------
V22 no longer trusts only OBS's "Recording" status.

While recording, it identifies the current file in D:\2026 and checks
that the file is actually increasing in size.

Default:
  At least 1 MB of growth within 60 seconds.

If OBS says Recording but the file stops growing:
  WATCHDOG alarm
  Recording file health turns red


----------------------------------------------------------------
10. LIVE AUDIO SANITY MONITOR
----------------------------------------------------------------
audio_sanity_monitor.py runs as a SEPARATE Python process.

It reads OBS WebSocket InputVolumeMeters for:
  main

This keeps audio-meter code outside the SSS Tkinter process.

Conservative defaults:
  Silence threshold: -55 dB
  Silence alarm: 120 seconds
  Clipping threshold: -0.5 dB
  Clipping alarm: 3 seconds
  Start grace: 90 seconds

The audio meter can fail/restart without crashing SSS.

Dependency:
  websocket-client

Install with:
  Setup-SSS-v22.bat


----------------------------------------------------------------
11. INTERNET LOSS BEHAVIOR
----------------------------------------------------------------
Internet loss does NOT affect local recording.

SSS displays:
  offline — local recording continues; YouTube will retry later

post_service_supervisor.py retries the YouTube Studio worker after the
connection returns.

Retry cooldown default:
  5 minutes


----------------------------------------------------------------
12. SAFE TEST MODE
----------------------------------------------------------------
Run:
  Run-Safe-SSS-Test-Mode.bat

Or:
  ADMIN -> RUN SAFE TEST MODE

It checks:
  configuration
  sermon plan
  writable folders
  FFmpeg / ffprobe / NVIDIA
  OBS WebSocket
  Planning profile
  YouTube Studio profile
  production script syntax

IT DOES NOT:
  start recording
  start streaming
  change Planning
  select a YouTube video
  upload/publish anything

Report:
  C:\Church\SermonAI\SSS_Test_Report.txt


----------------------------------------------------------------
13. VERSION DISPLAY
----------------------------------------------------------------
Main window now displays:
  SUNDAY SERVICE SYSTEM • v22


----------------------------------------------------------------
14. CONSOLIDATED LOGS
----------------------------------------------------------------
SSS writes per-service logs to:

  C:\Church\SermonAI\Logs\YYYY-MM-DD\

After post-service completion it also copies known helper logs there.

Default log retention:
  90 days


----------------------------------------------------------------
15. SAFE AUTOMATIC OPERATIONAL CLEANUP
----------------------------------------------------------------
Only after a fully successful post-service result, v22 may run:

  operational_cleanup.py

It only removes conservative local temporary/cache files and expired
SSS log folders.

IT DOES NOT DELETE:
  original D:\2026 recordings
  SRT files
  shorts
  Ready clips
  Sermon Data
  YouTube upload history

If Sunday Freeze is active, cleanup refuses to run.


----------------------------------------------------------------
INSTALL
----------------------------------------------------------------
1. Close SSS.

2. Copy ALL v22 files into:
     C:\Church\SermonAI
   and overwrite existing files.

3. Run once:
     Setup-SSS-v22.bat

4. Run:
     Run-Safe-SSS-Test-Mode.bat

5. Start SSS normally.

OBS and Presenter still auto-launch.

Recording and streaming are STILL human-controlled.
SSS never automatically starts either one.


----------------------------------------------------------------
YOUTUBE CHANNEL SAFETY REMAINS
----------------------------------------------------------------
YouTube Studio upload is still hard-locked to:

  Channel ID:
    UCXwqRxA_JKNM3g6JDe76DcQ

  Channel:
    Baptist Church of Perry

  Permission text:
    You're a manager

Wrong channel:
  upload blocked before selecting a file.


----------------------------------------------------------------
IMPORTANT: YOUTUBE AUDIENCE
----------------------------------------------------------------
V22 still uses:

  "youtube_audience": "channel_default"

It does NOT guess the Made for Kids / not Made for Kids classification.

If Studio requires a choice and there is no channel default, upload
stops before publishing for review.
