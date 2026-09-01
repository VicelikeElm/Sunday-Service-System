SSS v3.1.6 — GitHub Repository Staging Hotfix
===============================================

The previous Stage-SSS-GitHub-Pages-Feed helper expected a LOCAL Windows
repository path.

Entering:

  https://github.com/VicelikeElm/Sunday-Service-System.git

caused PowerShell Resolve-Path to interpret "https:" as a Windows drive.

v3.1.6 fixes that.

Stage-SSS-GitHub-Pages-Feed.bat now accepts either:

  LOCAL path:
    C:\Users\Vicel\Documents\GitHub\Sunday-Service-System

or:

  GitHub URL:
    https://github.com/VicelikeElm/Sunday-Service-System.git

If a GitHub URL is entered and the repo is not already present at:

  C:\Church\SermonAI\GitHub\Sunday-Service-System

the helper checks for Git for Windows and asks before cloning it.

It NEVER commits or pushes automatically.

After staging it prints the exact commands:

  git add docs
  git commit -m "Publish SSS stable update feed"
  git push

The helper also only removes/replaces release files inside docs\stable or
docs\beta. It does not clear unrelated repository files.
