SSS — PRESENTER ACCESSIBILITY / AUTO-CUE FIX
===========================================

WHAT THE SCREENSHOT CONFIRMED
-----------------------------
The Scripture item is visibly present in Presenter:

  Matthew 12:43-50 (ESV)

but Windows UI Automation reported that it was not visible.

That means the issue is not the sermon-plan text. Presenter is rendering
the item visually, but its Electron/Chromium accessibility tree is not
publishing that text to the SSS locator.


FIX
---
SSS now starts Presenter with:

  --force-renderer-accessibility

This tells Chromium/Electron to expose the rendered Presenter interface to
Windows accessibility/UI Automation.

The existing Scripture locator can then search for:

  Matthew 12:43-50

and also accept:

  Matthew 12:43-50 (ESV)


IMPORTANT FIRST RESTART
-----------------------
A running Presenter cannot gain this startup flag after it is already open.

After installing this patch:

  1. Close SSS.
  2. Close Presenter.
  3. Reopen SSS.

SSS will automatically start Presenter in SSS control mode.

For convenience, this patch also includes:

  Restart-Presenter-For-SSS-Control.bat

Do NOT use that restart helper during a live service.


NORMAL SUNDAY USE
-----------------
Once SSS is the application that starts Presenter, no extra volunteer step
should be required.

Scripture START should then:

  Select Matthew 12:43-50 (ESV) in Presenter
  -> Ctrl+F15
  -> Ctrl+Shift
  -> create Scripture chapter
  -> MIDI NEXT to first verse


FALLBACK
--------
If the church Presenter installation is unusual and SSS cannot resolve the
actual Presenter.exe behind the shortcut, SSS still opens the normal
shortcut. The Sunday Log will say that shortcut fallback was used.


INSTALL
-------
Close SSS and Presenter.

Copy these files into:

  C:\Church\SermonAI

and overwrite matching files:

  sunday_mode.py
  presenter_accessibility.py
  presenter_scripture_locator.py
  presenter_scripture_locator.ps1
  Restart-Presenter-For-SSS-Control.bat

Then reopen SSS and repeat the Admin Chapter/LT Test Mode test.

No sunday_config.json or PTZ persistent settings are included.
