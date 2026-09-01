SSS v3.1.2 — Release Feed Preflight Hotfix
===========================================

This fixes the confusing release-feed workflow.

The v3.1 feed builder could ask for URL/channel/summary/notes and only THEN
discover that the signed .sssupdate package had not been built.

v3.1.2 checks FIRST for:

  C:\Church\SermonAI\update-output\
  SundayServiceSystem-Update-v3.1.0.sssupdate

If missing, it stops immediately and tells you to run:

  Build-SSS-Windows-Installer.bat

before building the release feed.

It also clarifies the optional prompts:

  Short release summary:
    type a short sentence, or press Enter to skip

  HTTPS release-notes URL:
    paste a real https:// URL, or press Enter to skip

Do not type "yes" for either prompt.

Recommended current flow:

  1. Build-SSS-Windows-Installer.bat
  2. Verify-SSS-Signed-Release.bat
  3. Build-SSS-Signed-Release-Feed.bat
  4. Stage-SSS-GitHub-Pages-Feed.bat
  5. Commit/push docs/
  6. Enable GitHub Pages from main /docs
  7. Check-SSS-Online-Update-Feed.bat
