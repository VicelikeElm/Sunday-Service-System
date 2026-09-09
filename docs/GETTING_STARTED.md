# Getting Started

This is the current setup path for a brand-new install — for any church, not just Baptist Church of Perry. If you're already running SSS and just want the day-to-day operating guide, see [VOLUNTEER_SUNDAY_GUIDE.txt](VOLUNTEER_SUNDAY_GUIDE.txt) instead.

## 1. Install

1. Download the latest `SundayServiceSystem-Setup-v*.exe` from the [Releases page](https://github.com/VicelikeElm/Sunday-Service-System/releases).
2. Run it. Windows will likely show a "Windows protected your PC" SmartScreen prompt — the installer is signed, but not by a certificate authority Windows already trusts by default, so this warning is expected. Click **More info → Run anyway**.
3. Follow the installer. It installs to Program Files and creates a Start Menu / Desktop shortcut.

You need, before you start: OBS Studio installed with the obs-websocket plugin enabled, and (if you're using one) your PTZ camera's IP address and your church's Gmail or WorshipTools Planning login handy. Everything else the wizard will ask for as it goes.

## 2. First launch — the setup wizard

The first time you run Sunday Service System on a machine, it detects there's no configuration yet and walks you through a setup wizard instead of the normal dashboard. It's ten short pages: **Welcome → Church name → OBS connection → Recording folder → Audio → Camera → Presentation software → Sermon source → YouTube → Review**.

A few things worth knowing going in:

- **Every integration past the basics is skippable.** No PTZ camera yet? No Planning account? Skip that page — you can always run the wizard again later from Settings to fill it in once you do.
- **Audio and camera setup use discovery, not typing.** Audio shows a checklist of the actual devices Windows sees; camera setup scans your local network for PTZ cameras and lets you click one to fill in the IP (a manual field is still there as a fallback if scanning doesn't find it).
- **Camera protocol**: pick PTZOptics/HTTP-CGI or VISCA-over-IP depending on what your camera actually speaks — most consumer/prosumer PTZ cameras marketed for churches (PTZOptics, and many others) support one of these two.
- If you close the wizard partway through, it saves your progress and offers to resume where you left off next time you open it.

When you finish, SSS writes your configuration and opens the normal dashboard.

## 3. StreamDeck (optional)

If your church uses a physical Elgato Stream Deck, the installed app ships a fixed set of `StreamDeck_*.bat` files (Start/Stop Recording, Start/Stop Stream, Emergency Mute, camera presets, chapter advance) that never move or get renamed between versions — point your Stream Deck's "Open" action at whichever ones match your layout, once, and they'll keep working across every future update.

## 4. Changing something later

Reopening the full wizard, adjusting a single integration, checking diagnostics, or recovering from a bad config — all of that lives in **Settings** (the second icon installed alongside the main app). You don't need to reinstall to fix or change your setup.

## 5. Running the actual service

Once everything's configured, see [VOLUNTEER_SUNDAY_GUIDE.txt](VOLUNTEER_SUNDAY_GUIDE.txt) for what a normal Sunday looks like operating the dashboard.
