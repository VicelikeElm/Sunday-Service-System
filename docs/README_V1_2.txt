YOUTUBE STUDIO DIAGNOSTIC v1.2 — PROFILE LOCK FIX
===================================================

YOUR V1.1 RESULT
----------------
The saved login profile was still being used by a Chrome/Edge process.

That is why Playwright reported:

  Opening in existing browser session

V1.2 fixes the workflow.

STEP 1 — LOGIN NORMALLY
-----------------------
Run:

  Open-YouTube-Studio-Normal-Login.bat

Sign into your Google account and switch Studio to:

  Baptist Church of Perry
  @baptistchurchofperry

Then CLOSE every window from that dedicated Studio browser.

The helper now waits until Windows confirms that the dedicated profile
is completely released.

STEP 2 — IF THE PROFILE STILL WILL NOT CLOSE
---------------------------------------------
Run:

  Close-Dedicated-YouTube-Studio-Browser.bat

This targets ONLY Chrome/Edge processes whose command line uses:

  C:\Church\SermonAI\YouTube_Studio_Profile

It does not target your normal Chrome/Edge profile.

STEP 3 — RUN DIAGNOSTIC
-----------------------
Run:

  YouTube-Studio-Diagnostic-v1.2.bat

If the profile is still locked, v1.2 stops immediately and tells you
instead of producing the long Playwright browser error.

OUTPUT
------
When it succeeds, upload:

  C:\Church\SermonAI\YouTube_Studio_Diagnostic.txt

No video file is selected and nothing is uploaded.
