SSS — COMPACT FULL-SCREEN WORKFLOW
==================================

This update fixes the problem where the Camera controls and Sunday Log
could fall below the bottom of the screen whenever Preflight was expanded.

WHAT CHANGED
------------
Volunteer Controls no longer use several tall nested boxes.

They are now one compact row per stage:

  1 — SERVICE PREP
      LAUNCH SUNDAY APPS | RUN PREFLIGHT

  2 — LIVE A/V
      START RECORDING | START STREAM | EMERGENCY MUTE

  3 — SERMON
      [current rotating sermon chapter]

  4 — CAMERA VIEW
      WORSHIP VIEW | PASTOR VIEW

  5 — END SERVICE
      STOP STREAM | STOP RECORDING

  ADMIN / TROUBLESHOOTING

This keeps the top-to-bottom temporal order while dramatically reducing
vertical space.

WINDOW SIZING
-------------
SSS now sizes itself from the actual monitor instead of opening with a
fixed 940-pixel height.

It can use extra width (up to 1200 pixels), which reduces wrapping in
the two-column Preflight and therefore reduces Preflight height.

SUNDAY LOG
----------
The visible log starts at 5 lines instead of 8. It still expands into
remaining space and still contains the same information.

PREFLIGHT
---------
The two-column Preflight remains collapsible. With this compact workflow,
normal controls should remain visible even while Preflight is expanded.
