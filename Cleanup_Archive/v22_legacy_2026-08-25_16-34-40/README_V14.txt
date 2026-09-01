V14 — PRESERVE LT2 STATIC PRESETS
=================================

V13 correctly loaded the weekly sermon, but it cleared all LT2 memory
slots. That removed the permanent church/pastor lower third.

V14 changes LT2 behavior:

  Slot 1:
    Weekly sermon title
    Scripture

  Slot 2:
    Weekly sermon title
    Preacher

  Slot 3:
    PRESERVED - not changed by Sermon AI

  Slots 4-10:
    PRESERVED - not changed by Sermon AI

Your static LT2 Slot 3 can remain:

  The Baptist Church of Perry
  Pastor Phil Lowther

LT1 is still treated as the weekly sermon-outline bank, so LT1 slots
1-10 are refreshed from the official sermon outline.

INSTALL
-------
1. Before installing, put your static church/pastor preset back into
   LT2 Slot 3 one time if v13 already erased it.

2. Close OBS.

3. Copy all v14 files to:
     C:\Church\SermonAI

4. Run:
     Install-Lower-Third-Sermon-Sync-v14.bat

5. Reopen OBS.

From then on the weekly sermon automation will only touch LT2 slots
1 and 2, leaving slot 3 and all later LT2 presets alone.
