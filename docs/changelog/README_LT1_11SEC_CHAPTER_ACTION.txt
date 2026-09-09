SSS — LT1 CHAPTER + LOWER THIRD ACTION
====================================

WHAT WAS FIXED
--------------
Loading LT1_SLT01 / LT1_SLT02 / etc. only changes the selected LT1
memory slot. It does NOT turn Lower Third 1 on.

The rotating sermon-point action now recreates the Stream Deck behavior:

  1. Create the sermon-point chapter marker
  2. Load LT1 Slot 1 / 2 / 3 / etc.
  3. Wait briefly for the slot to load
  4. Toggle LT1 ON
  5. Keep it displayed for 11 seconds
  6. Toggle LT1 OFF

LT1 SWITCH
----------
SSS first triggers the Animated Lower Thirds OBS hotkey:

  A_SWITCH_1

That is the LT1 switch action corresponding to the church setup:

  Alt + Shift + F16

If the OBS named-hotkey trigger fails, Windows Alt+Shift+F16 is sent as
a fallback.

The default display time is 11 seconds.

Optional sunday_config.json overrides are supported if ever needed:

  "lt1_chapter_display_seconds": 11
  "lt1_slot_load_delay_seconds": 0.35
  "lt1_switch_hotkey_name": "A_SWITCH_1"

No config file is included in this patch, so existing settings are not
overwritten.


DOUBLE-CLICK PROTECTION
-----------------------
The chapter button remains disabled while the LT1 point is on screen.
After the 11-second display finishes and LT1 is switched back off, the
button advances to the next sermon chapter.

This intentionally prevents a volunteer from firing two point lower
thirds on top of each other.


SERMON ROW LAYOUT
-----------------
The sermon row now uses the three action columns like this:

  [ LOWER THIRD +      ][ current chapter button................ ]
  [ CHAPTER MARKER     ][ spans the remaining two-thirds........ ]
  [ points show 11 sec ]

The button was reduced by one-third rather than making the point text too
narrow to read.


IMPORTANT
---------
The LT1 switch is a toggle. This workflow assumes LT1 begins OFF, which
matches the existing Stream Deck sequence.

Prayer, Scripture reading, Ending Prayer, and Benediction are not changed
by this LT1 timing update.
