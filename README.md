# Sunday Service System (SSS)

Automation for a church's Sunday livestream/recording workflow: OBS control, PTZ camera presets (PTZOptics/HTTP-CGI or VISCA-over-IP), sermon lower-thirds and chapter markers synced from the pastor's sermon email or WorshipTools Planning, and automatic post-service YouTube upload.

Originally built for Baptist Church of Perry, but every integration is individually toggleable and a first-run setup wizard walks a new install through its own church name, OBS connection, recording folder, audio, camera, presentation software, sermon source, and YouTube — nothing here is hardcoded to one specific church.

## Install

1. Download the latest `SundayServiceSystem-Setup-v*.exe` from [Releases](https://github.com/VicelikeElm/Sunday-Service-System/releases/latest).
2. Run it (Windows will show a SmartScreen prompt since the certificate isn't from a CA Windows trusts by default — click **More info → Run anyway**).
3. First launch opens the setup wizard automatically. See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for the full walkthrough.

Once it's running day to day, see [docs/VOLUNTEER_SUNDAY_GUIDE.txt](docs/VOLUNTEER_SUNDAY_GUIDE.txt) for normal Sunday operation.

## What it does

- Drives OBS (via `obsws_python`) for recording/streaming, scene switching, and chapter markers
- Moves a PTZ camera to worship/pastor presets, over PTZOptics HTTP-CGI or VISCA-over-IP
- Pulls the week's sermon title/Scripture/outline from a Gmail sermon-notes email (or WorshipTools Planning) and syncs it into lower-thirds, OBS chapter hotkeys, and Planning
- Uploads the finished full-service recording to YouTube automatically after the service (either via a signed-in YouTube Studio browser session, or via the YouTube Data API)
- Ships an Admin/Troubleshooting panel for diagnostics, backup/recovery, and manual overrides
- Checks for new releases in the background and offers to update, or you can check anytime from Settings

## Requirements

- Windows 10/11, OBS Studio with obs-websocket enabled
- A PTZ camera speaking PTZOptics HTTP-CGI or VISCA-over-IP, if camera presets are used

## Credentials (not included in this repo)

Nothing in this repo can talk to Gmail, YouTube, or WorshipTools Planning until you provide your own credentials locally — none are committed here (see `.gitignore`). The setup wizard's Sermon Source and YouTube pages link to these directly, or run them yourself:

- **Gmail sermon import:** `tools\Setup-Gmail-Sermon-Import.bat`
- **YouTube upload — browser automation (current default):** `tools\Open-YouTube-Studio-Normal-Login.bat` signs the dedicated `YouTube_Studio_Profile` Chrome profile in as a channel manager
- **YouTube upload — Data API (alternative path):** `tools\Authorize-YouTube-API.bat` runs a one-time OAuth consent flow and writes `youtube_token.json` locally. Note: an unverified Google Cloud OAuth project forces API uploads private unless the uploading account is added as a *Test user* on that project's OAuth consent screen first.

## Admin / Troubleshooting

Inside the running app, the Admin panel covers diagnostics, backup/recovery, event history, security/secrets, software updates, chapter tools, Planning sync, and YouTube upload retry — see the in-app tooltips on each button.

## Building from source (developers / maintainers)

1. `tools\Build-SSS-Windows-Installer.bat` — builds signed Main/Settings/Updater executables and an installer via PyInstaller + Inno Setup (requires `sss_signing_config.json`, see `tools\Configure-SSS-Code-Signing.bat`)
2. Run the resulting `installer-output\SundayServiceSystem-Setup-*.exe`

To run directly from source without building: `scripts\Start-Sunday-Mode-Debug.bat` (requires the pinned `venv\` environment and `ffprobe`/`ffmpeg` on PATH).

Repo layout: `core\` holds the application's Python source; `tools\` holds setup/build/diagnostic scripts; a small fixed set of files stay at the repo root because external tools (a physical Stream Deck, a Windows Scheduled Task) point at them by a path that can never change — see the comments in `sunday_action.py` and `ptz_camera_control.py`.
