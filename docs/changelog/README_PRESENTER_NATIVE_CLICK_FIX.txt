SSS — PRESENTER NATIVE CLICK FIX
================================

WHAT THE SCREENSHOT SHOWED
--------------------------
SSS got far enough to change the OBS Scripture view, but Presenter stayed on
Prayer -Offering- instead of selecting Matthew 12:43-50 (ESV).

The first DOM build found the Scripture text, but used JavaScript element.click().
Electron/React controls can ignore that synthetic click.

FIX
---
The locator now:
  1. Finds Matthew 12:43-50 / Matthew 12:43-50 (ESV) in Presenter's DOM.
  2. Prefers the matching element in the LEFT service list.
  3. Gets the actual on-screen center of that service item.
  4. Uses Chromium Input.dispatchMouseEvent to send a real mouse press/release
     directly to Presenter at that exact point.

This does NOT move the Windows mouse cursor.

If the Sermon section is collapsed, the same native Chromium click is used to
expand Sermon first, then the Scripture item is found and clicked.

PRESENTER MIDI DISCOVERY
------------------------
The screenshot also confirms Presenter has native MIDI commands for:
  Change Service Item = note 5
  Previous Service Item = note 2
  Next Service Item = note 64
  Change Slide = note 4
  Previous Slide = note 62
  Next Slide = note 60

That gives us a strong backup route if Presenter's service-item click still
behaves oddly. This patch first fixes the specific issue observed without
assuming a fixed service-item number from Sunday to Sunday.

INSTALL
-------
Close SSS.
Copy presenter_scripture_locator.py into:
  C:\Church\SermonAI
and overwrite the existing file.

Presenter can remain open IF it is already running in SSS control mode.
If unsure, close Presenter and run:
  Restart-Presenter-For-SSS-Control.bat

Then test again with Admin Chapter/LT Test Mode.
