SSS — PRESENTER SCRIPTURE LOCATOR PARSER FIX
=============================================

The error shown in the popup happened before Presenter automation ran.

ROOT CAUSE
----------
Windows PowerShell 5.1 read the previous .ps1 with the wrong text encoding.
The smart-dash characters in the script became garbled and caused the chain
of parser errors.

FIX
---
This replacement presenter_scripture_locator.ps1:

  - is saved as UTF-8 WITH BOM for Windows PowerShell 5.1
  - contains no literal smart-dash characters
  - uses ASCII-safe Unicode regex escapes
  - simplifies the Presenter-window check for PowerShell 5.1

INSTALL
-------
Close SSS.

Copy:
  presenter_scripture_locator.ps1

into:
  C:\Church\SermonAI

and overwrite the existing file.

Then reopen SSS and repeat the Admin Chapter/LT Test Mode test.

No Python or config files need to be replaced for this parser fix.
