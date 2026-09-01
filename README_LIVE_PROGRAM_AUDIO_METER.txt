SSS — LIVE PROGRAM AUDIO METER
==============================

WHAT CHANGED
------------
The old Preflight row:

  Live audio sanity
  REVIEW — Program audio has remained below -55 dB for 847 seconds.

has been replaced by a compact LIVE audio meter.

The row is now:

  Program audio level    [ moving dB meter ]   -23 dB

The meter follows the configured program/main OBS input.


METER SCALE
-----------
The meter uses a familiar OBS-style -60 dB to 0 dB scale.

  Green  = normal level range
  Yellow = getting hot
  Red    = near clipping

The meter moves from the live OBS InputVolumeMeters events rather than
waiting for the 5-second Preflight refresh.


EXCEPTION TEXT ONLY
-------------------
Normal audio does not produce a wall of text.

Normally the right side only shows the current level, for example:

  -23 dB

Text becomes attention-grabbing only when needed.

After 60 continuous seconds below the configured silence threshold:

  NO AUDIO 60s

The timer continues upward until audio returns.

Other possible exceptions:

  CLIPPING
  INPUT MISSING
  METER ERROR
  METER OFFLINE


IMPORTANT
---------
The 60-second "NO AUDIO" display is a dashboard warning.

The existing independent audio-sanity watchdog logic is still preserved.
This patch does not weaken the recording/streaming safety checks.


HOW THE LIVE METER WORKS
------------------------
audio_sanity_monitor.py already listens to OBS InputVolumeMeters.

It now sends only the instantaneous meter data over localhost UDP:

  127.0.0.1:49221

Nothing is sent over the church network or internet.

The normal audio_sanity_status.json file remains the fallback. If the
live feed is unavailable, SSS can still display the most recent level
from that file.


INSTALL / FIRST TEST
--------------------
1. Close SSS.
2. Copy the patch files into:

     C:\Church\SermonAI

3. Overwrite:
     sunday_mode.py
     audio_sanity_monitor.py

4. Run:
     Restart-Live-Audio-Meter.bat

5. Reopen SSS.

The restart BAT is only needed after installing this update so the
already-running hidden audio helper loads its new live-meter code.

No configuration files are included or overwritten.


OPTIONAL CONFIG VALUES
----------------------
These defaults work without changing sunday_config.json:

  "audio_meter_no_audio_seconds": 60
  "audio_meter_udp_port": 49221

The existing silence threshold remains controlled by:

  "audio_sanity_silence_db": -55
