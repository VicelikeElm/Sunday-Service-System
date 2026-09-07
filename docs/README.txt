Presenter UI Diagnostic
=======================

This does NOT change Presenter, OBS, MIDI, SSS, recording, or streaming.

1. Keep Presenter open on the normal Sunday service screen where the Scripture
   item is visible.
2. Copy these two files into C:\Church\SermonAI.
3. Run Diagnose-Presenter-UI.bat.
4. Notepad will open:
     C:\Church\SermonAI\presenter_ui_diagnostic.txt
5. Send that TXT file back here.

The diagnostic records:
- Presenter executable and command line
- Presenter top-level window information
- the Windows UI Automation elements Presenter exposes
- whether Matthew 12:43-50 is actually visible to automation

This is the next useful test because the Scripture text is visibly present in
Presenter, but both normal UI Automation and forced renderer accessibility
still reported that it was not visible.
