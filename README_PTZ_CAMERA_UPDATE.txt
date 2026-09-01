SSS PTZ CAMERA CONTROL UPDATE
=============================

NEW STARTUP BEHAVIOR
--------------------
When SSS loads, it automatically recalls:

  PASTOR / STARTUP = Preset 2

This happens independently of recording and streaming.

NEW MAIN-SCREEN BUTTONS
-----------------------
  WORSHIP CAMERA
  PASTOR CAMERA

Defaults:
  Worship = Preset 1
  Pastor = Preset 2

If your Worship position is a different preset, the one-time PTZ setup
asks you for the correct number.

ONE-TIME SETUP
--------------
Run:

  Setup-PTZ-Camera.bat

Enter the PTZOptics camera's IP address.

The setup defaults to:
  Worship preset 1
  Pastor preset 2

The setup does not move the camera unless you explicitly type YES when
it offers the Pastor-preset test.

CAMERA CONTROL METHOD
---------------------
SSS talks directly to the PTZOptics camera using its HTTP-CGI preset
recall command.

This is more reliable than trying to electronically "press" a physical
Stream Deck button.

To keep Stream Deck and SSS using the same actions, this package also
includes:

  StreamDeck_PTZ_WORSHIP.bat
  StreamDeck_PTZ_PASTOR.bat

You can point Stream Deck System/Open actions at those BAT files.

PREFLIGHT
---------
SSS now has:

  PTZ camera

If the camera IP has not been configured, it displays:
  setup required — run Setup-PTZ-Camera.bat

If the last camera command failed, the PTZ row displays the error.

IMPORTANT
---------
Camera movement remains separate from:
  recording
  streaming
  OBS scenes
  YouTube
  Planning

SSS still NEVER automatically starts recording or streaming.
