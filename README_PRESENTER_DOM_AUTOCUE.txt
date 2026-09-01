SSS — Presenter DOM Auto-Cue

The diagnostic proved Presenter is installed at:
  C:\Program Files\Presenter\Presenter.exe

It also proved Windows UI Automation exposes no Presenter top-level window and
no Scripture text. SSS therefore now uses a localhost-only Chromium DevTools
connection to control Presenter's rendered interface directly.

First test:
1. Close SSS.
2. Close Presenter completely.
3. Copy this patch into C:\Church\SermonAI.
4. Run Restart-Presenter-For-SSS-Control.bat.
5. It should end with: Control ready: True
6. Open SSS, enable Chapter/LT Test Mode, mark Prayer, and press Scripture START.

SSS will search Presenter's DOM for Matthew 12:43-50 and accept
Matthew 12:43-50 (ESV). If Sermon is collapsed, it attempts to expand it.

The control port is bound only to 127.0.0.1:9223.

If Control ready is False, run Check-Presenter-SSS-Control.bat and send the
displayed result.
