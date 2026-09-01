SSS v3.1.7 — Safe Workspace Trim
==================================

This is a housekeeping patch for C:\Church\SermonAI.

It trims rebuildable development clutter while preserving the live Sunday
Service System and current signed-release work.

KEPT:
- all current runtime .py files
- venv
- .env
- sunday_config.json
- sermon_plan.json
- ptz_camera_config.json
- Gmail / YouTube credentials and tokens
- Windows Credential Manager secrets
- Profiles
- Diagnostics
- Event History
- Plugin_Backups
- CUDA
- dist
- update-output
- release-feed-output
- installer-output

DELETED AS REBUILDABLE:
- build
- installer-payload
- .sss-build-tools
- __pycache__
- loose .pyc/.pyo/.tmp/.download files
- abandoned update-output\.signing_* temporary folders

ARCHIVED INSTEAD OF DELETED:
- README_SSS_v*.txt version-history documents
- Apply-Built-v3.0-Update.bat
- superseded one-time timestamp/dev-certificate repair helpers

Archive location:
  C:\Church\SermonAI\SSS Archive\<timestamp>

Two launchers are included:

  Preview-SSS-Workspace-Trim.bat
    Shows what would change. Makes no changes.

  Trim-SSS-Workspace.bat
    Performs the safe trim after a confirmation prompt.

The tool never starts/stops OBS Recording or Streaming and does not alter
camera, Presenter, audio, sermon-plan, or profile behavior.
