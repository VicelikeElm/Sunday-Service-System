SSS v3.1.4 — Timestamp + Build Preflight Hotfix
=================================================

This fixes three issues visible in the v3.1 signed-build log.

1. SIGNTOOL INVALID TIMESTAMP URL

The failed build used:

  https://timestamp.digicert.com

DigiCert's documented RFC3161 SignTool endpoint is:

  http://timestamp.digicert.com

v3.1.4:
- changes new signing configs to the documented endpoint
- automatically normalizes the old HTTPS DigiCert value inside sss_signing.py
- includes Fix-SSS-Timestamp-URL.bat for the existing local config

FASTEST CURRENT FIX:
  Run Fix-SSS-Timestamp-URL.bat
  Then Build-SSS-Windows-Installer.bat


2. POWERSHELL '^|' PARSER ERROR IN BUILD LOCK CHECK

The previous BAT sent a literal caret into PowerShell:

  ^|

PowerShell rejected it with:
  Unexpected token '^'

v3.1.4 moves this safety check into:
  Check-SSS-Packaged-Build-Locks.ps1

The build now FAILS CLOSED if the safety checker itself errors.


3. MIDO / RTMIDI HIDDEN IMPORT NOISE

The build log showed:
  Hidden import 'mido.backends.rtmidi' not found
  Hidden import 'rtmidi' not found

Those lines did NOT cause the build failure; the EXE build itself completed.

v3.1.4 only asks PyInstaller for these optional hidden imports when those
packages are actually installed in the production SSS Python environment.
Normal imported dependencies are still discovered by PyInstaller.


NO LIVE-SERVICE BEHAVIOR CHANGED

This hotfix does not change:
- Recording
- Streaming
- Presenter MIDI commands
- camera controls
- audio controls
- sermon workflow
- profiles
- credentials
- PTZ config

Recording and Streaming remain separate manual/human-gated controls.
