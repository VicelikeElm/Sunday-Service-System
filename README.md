# Sunday Service System (SSS)

Automation for Baptist Church of Perry's Sunday livestream/recording workflow: OBS control, PTZ camera presets, sermon lower-thirds and chapter markers synced from the pastor's sermon email, WorshipTools Planning sync, and automatic post-service YouTube upload.

This is a private, single-church operational tool, not a general-purpose distributable product. The instructions below are for reinstalling/rebuilding it on the church PC, not for a stranger setting it up from scratch.

## Install

**Signed release build (normal path):**
1. `Build-SSS-Windows-Installer.bat` — builds signed Main/Settings/Updater executables and an installer via PyInstaller + Inno Setup (requires `sss_signing_config.json`, see `Configure-SSS-Code-Signing.bat`)
2. Run the resulting `installer-output\SundayServiceSystem-Setup-*.exe` on the church PC

**Run from source (development/testing):**
1. `Start-Sunday-Mode-Debug.bat` runs the app directly from source, no build step

## What it does

- Drives OBS (via `obsws_python`) for recording/streaming, scene switching, and chapter markers
- Moves a PTZOptics PTZ camera to worship/pastor presets over HTTP-CGI
- Pulls the week's sermon title/Scripture/outline from a Gmail sermon-notes email and syncs it into lower-thirds, OBS chapter hotkeys, and WorshipTools Planning
- Uploads the finished full-service recording to YouTube automatically after the service (either via a signed-in YouTube Studio browser session, or via the YouTube Data API — see below)
- Ships an Admin/Troubleshooting panel for diagnostics, backup/recovery, and manual overrides

## Requirements

- Windows 10/11, OBS Studio with obs-websocket enabled
- Python (see `venv/` for the pinned environment) and `ffprobe`/`ffmpeg` on PATH
- A PTZOptics (or compatible HTTP-CGI) PTZ camera, if camera presets are used

## Credentials (not included in this repo)

Nothing in this repo can talk to Gmail, YouTube, or WorshipTools Planning until you provide your own credentials locally — none are committed here (see `.gitignore`):

- **Gmail sermon import:** `Setup-Gmail-Sermon-Import.bat`
- **YouTube upload — browser automation (current default):** `Open-YouTube-Studio-Normal-Login.bat` signs the dedicated `YouTube_Studio_Profile` Chrome profile in as a channel manager
- **YouTube upload — Data API (alternative path):** `Authorize-YouTube-API.bat` runs a one-time OAuth consent flow and writes `youtube_token.json` locally. Note: an unverified Google Cloud OAuth project forces API uploads private unless the uploading account is added as a *Test user* on that project's OAuth consent screen first.

## Admin / Troubleshooting

Inside the running app, the Admin panel covers diagnostics, backup/recovery, event history, security/secrets, software updates, chapter tools, Planning sync, and YouTube upload retry — see the in-app tooltips on each button.
