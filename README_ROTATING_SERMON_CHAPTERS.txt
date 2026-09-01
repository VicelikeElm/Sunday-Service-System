SSS — COMPACT ROTATING SERMON CHAPTERS
=======================================

ROTATION
--------
The main SSS chapter button now rotates through:

  Prayer
  Reference
  [Official Gmail Point 1]
  [Official Gmail Point 2]
  ...however many official sermon points exist...
  Ending Prayer
  Benediction

The extra Ending Prayer is always placed AFTER the final sermon point
and BEFORE Benediction.

COMPACT BUTTON
--------------
The SSS button now shows ONLY the pertinent chapter information.

Examples:

  Prayer

  Reference

  The King’s Kingdom of Saving-Gracefilled Relationship!

  Ending Prayer

  Benediction

It no longer adds:
  NEXT CHAPTER:
  Point 1 —
  Point 2 —

This keeps the volunteer-control area smaller and easier to read.

When all chapters have been used, the button becomes:

  CHAPTERS COMPLETE

and disables itself instead of rotating back to Prayer.


GMAIL SERMON POINTS
-------------------
The pastor's official Gmail sermon points still become the ACTUAL
point chapter names and the LT1 slots.

Example:

  Gmail Point 1
      ↓
  Additional Chapter Hotkeys named chapter
      ↓
  SSS rotating button
      ↓
  LT1_SLT01

Point 2 uses LT1_SLT02, and so on.


FIXED SERVICE CHAPTERS
----------------------
The fixed chapter names are:

  Prayer
  Reference
  Ending Prayer
  Benediction

Reference remains named "Reference" in the recording chapter list.


ONE BUTTON PRESS
----------------
Prayer:
  Fires the named Prayer chapter.

Reference:
  Fires Reference + LT2 Slot 1.

Pastor Point:
  Fires the exact Gmail point chapter + corresponding LT1 slot.

Ending Prayer:
  Fires the named Ending Prayer chapter.

Benediction:
  Fires the named Benediction chapter.


STREAM DECK
-----------
The rotating Stream Deck action remains:

  StreamDeck_NEXT_SERMON_CHAPTER.bat

It uses the same chapter rotation/state as the SSS button.


CHAPTER HOTKEY SYNC
-------------------
When SSS starts before OBS, it can update the Additional Chapter Hotkeys
scene-collection entries from the current Gmail sermon plan.

It preserves the existing chapter hotkey IDs/bindings where possible.

The sync now manages:

  Prayer
  Reference
  Point 1 ... Point N
  Ending Prayer
  Benediction


DUPLICATE PROTECTION
--------------------
The explicit rotating chapter action owns chapter creation.

Chapter Bridge does NOT automatically create another chapter merely
because the lower third changed.


SAFETY
------
If OBS is not recording:
  - no chapter is created
  - no LT action is fired
  - the sequence does not advance

Each fresh recording resets the rotating sequence to Prayer.

The old manual chapter action remains under:

  ADMIN / TROUBLESHOOTING
    -> ADD MANUAL CHAPTER
