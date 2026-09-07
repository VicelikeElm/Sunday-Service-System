SSS — LOCKED / STABLE TOOLTIPS
==============================

This fixes the SSS window shifting while hovering over different items.

WHAT CHANGED
------------
1. The on-screen "Tooltip:" area now has a FIXED two-line height.

   Longer or shorter tooltip text cannot push:
     Volunteer Controls
     Sunday Log
     other controls

   up or down.

2. The mirrored Tooltip text is normalized to one continuous sentence and
   capped to a safe length for the fixed area.

3. The normal hover popup still contains the full explanation.

4. Hover popup placement is now anchored to the CONTROL, not to the mouse
   pointer. Once it appears, it stays in a predictable place beneath the
   item rather than visually following small mouse movements.

RESULT
------
The SSS layout should stay physically locked in place while the volunteer
moves between controls and status items.

INSTALL
-------
Close SSS.

Copy:
  sunday_mode.py

into:
  C:\Church\SermonAI

and overwrite the existing file.

No configuration files are included or changed.
