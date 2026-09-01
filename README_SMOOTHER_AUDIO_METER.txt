SSS — SMOOTHER PROGRAM AUDIO METER
=================================

This update addresses the visual movement shown in the test video.

WHAT CHANGED
------------
1. The live dB number moved to the LEFT side of the meter.

   BEFORE:
     [ meter......................... ]  -23 dB

   NOW:
     -23 dB  [ meter......................... ]

2. The dB field has a FIXED WIDTH.

   Changing from:
     -28 dB
     -4 dB
     0 dB

   no longer changes the width of the meter or makes the layout move.

3. The right side is now reserved ONLY for exceptions.

   Normal:
     -23 dB  [ meter......................... ]

   Silence:
     -60 dB  [ meter......................... ]  NO AUDIO 60s

   Other examples:
     CLIPPING
     INPUT MISSING
     METER ERROR
     METER OFFLINE

   The warning field is also fixed-width, so a warning appearing does
   not shove the level meter around.

4. The meter movement is smoothed.

   OBS's raw peak meter changes very quickly. The SSS dashboard now uses:

     Fast attack  = responds quickly when sound gets louder
     Slow release = falls more gently when sound gets quieter

   The animation refreshes about every 100 ms.

   This should feel much calmer while still showing real changes in
   program audio.


OPTIONAL TUNING
---------------
No config changes are required.

If desired later, sunday_config.json can override:

  "audio_meter_attack_smoothing": 0.55
  "audio_meter_release_smoothing": 0.16

Higher numbers move faster.
Lower numbers move more smoothly/slower.


INSTALL
-------
Close SSS.

Copy:

  sunday_mode.py

into:

  C:\Church\SermonAI

and overwrite the existing file.

The audio_sanity_monitor.py from the previous Live Program Audio Meter
update does NOT need to be changed again for this patch.
