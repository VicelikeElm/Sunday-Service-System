V15 — RESET WEEKLY LOWER-THIRD DEFAULTS ON EVERY OBS START
==========================================================

WHY V14 DID NOT RESET AFTER YOU CHANGED LT1
-------------------------------------------
V14 saved the sermon plan ID in OBS Browser localStorage.

On the next OBS launch it saw:
  "This exact sermon has already been applied"

and intentionally left the current LT1/LT2 active values alone.

That was useful for preserving a point selection during a browser reload,
but it is NOT what you want for Sunday startup.

V15 changes that behavior.

EVERY FRESH OBS / LOWER-THIRD PAGE LOAD
---------------------------------------
LT1 active fields reset to:
  Point 1
  Scripture

LT2 active fields reset to:
  Sermon Title
  Scripture

LT1 slots 1-10:
  refreshed from the current sermon outline

LT2:
  Slot 1 = title / Scripture
  Slot 2 = title / preacher
  Slots 3-10 = PRESERVED

So this test should now work:

1. Open OBS.
2. Change LT1 to anything else.
3. Close OBS completely.
4. Reopen OBS.
5. LT1 returns to the official Point 1 / Scripture.

During the same OBS session, you can still click LT1 slot 2, slot 3,
etc. normally. V15 only resets defaults when the control panel itself
freshly loads.

INSTALL
-------
1. Close OBS.
2. Copy all v15 files into:
     C:\Church\SermonAI
3. Run:
     Install-Lower-Third-Sermon-Sync-v15.bat
4. Reopen OBS.
