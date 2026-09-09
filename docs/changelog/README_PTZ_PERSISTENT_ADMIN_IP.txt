SSS — PERSISTENT PTZ CAMERA ADDRESS + ADMIN EDITOR
====================================================

WHY YOU KEPT HAVING TO RUN SETUP-PTZ-CAMERA.bat
------------------------------------------------
The older PTZ setup stored the camera IP inside:

  C:\Church\SermonAI\sunday_config.json

Each SSS update ZIP also contained sunday_config.json.

So when you copied a new SSS package over the old one, the packaged
default configuration could replace the camera IP with a blank value.

That is why the PTZ setup seemed to "forget" the camera.


NEW PERMANENT PTZ CONFIG
------------------------
The camera settings now live in their own file:

  C:\Church\SermonAI\ptz_camera_config.json

Normal SSS update ZIPs should NOT include or replace that file.

It stores:
  camera IP/address
  Worship preset
  Pastor preset
  startup preset
  PTZ connection settings


AUTOMATIC MIGRATION
-------------------
If ptz_camera_config.json does not exist yet, SSS looks at the existing
PTZ values in sunday_config.json.

If an IP is already there, SSS automatically copies those values into
ptz_camera_config.json.

You should not need to type the address again if the current
sunday_config.json still has it.


ADMIN / TROUBLESHOOTING
-----------------------
There is now a section at the top of Admin:

  PTZ Camera — Persistent Settings

It contains:

  Camera IP / Address     [________________] [SAVE & TEST]

  Worship preset          [ 1 ]

  Pastor / startup preset [ 2 ]

You can either:
  click SAVE & TEST

or:
  type the camera address and press Enter.

SAVE & TEST:
  1. validates the address/presets
  2. writes ptz_camera_config.json
  3. updates the currently running SSS
  4. sends the Pastor preset as the connection test

So you do NOT need to close/reopen SSS after changing the address.


SETUP-PTZ-CAMERA.bat
--------------------
The old setup BAT still works, but it now writes the separate persistent
PTZ config instead of sunday_config.json.

Normally you should be able to use the Admin textbox instead.


INSTALL THIS PATCH
------------------
Close SSS.

Copy the files from this patch into:

  C:\Church\SermonAI

and replace the matching files.

IMPORTANT:
This patch intentionally does NOT contain sunday_config.json.

That prevents the currently saved settings from being overwritten while
the new persistent PTZ file is being migrated.

Then open SSS.

If the existing address is still in sunday_config.json, it should migrate
automatically.

If the PTZ row says the camera IP is missing:
  ADMIN / TROUBLESHOOTING
    -> PTZ Camera — Persistent Settings
    -> enter IP/address
    -> SAVE & TEST

After that, future normal SSS updates should leave the PTZ address alone.
