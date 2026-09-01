V13 FIX — OBS LT1/LT2 SWITCH STATE
===================================

The screenshots revealed the root cause:

Chrome:
  LT1 and LT2 switches were OFF.
  The sermon plan applied.

OBS:
  LT1 and LT2 switches were ON (blue).
  V12 intentionally refused to replace active lower-third text.

Those switch states are saved in OBS Browser localStorage, so the same
HTML behaved differently in Chrome and OBS.

V13 removes that startup guard. Because the sermon plan is embedded
before OBS opens, the official sermon is applied once when the lower-
third panel loads, even if LT1/LT2 were left ON from the prior session.

INSTALL
-------
1. Close OBS.
2. Copy all v13 files to:
     C:\Church\SermonAI
3. Run:
     Install-Lower-Third-Sermon-Sync-v13.bat
4. Reopen OBS.

Expected:
  LT1 active = Point 1 / Scripture
  LT1 slots 1..N = official outline points
  LT2 active = Sermon Title / Scripture
  LT2 slot 1 = Title / Scripture
  LT2 slot 2 = Title / Preacher

LT3/LT4 remain untouched.
