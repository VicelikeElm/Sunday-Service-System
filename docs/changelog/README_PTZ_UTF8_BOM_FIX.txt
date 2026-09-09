PTZ UTF-8 BOM FIX
==================

The PTZ setup wrote sunday_config.json using Windows PowerShell UTF-8,
which can include a BOM. Python's plain 'utf-8' JSON loader rejected it.

This patch fixes both sides:
1. sunday_common.py now reads config with 'utf-8-sig', which accepts
   both BOM and normal UTF-8 files.
2. Setup-PTZ-Camera.ps1 now writes UTF-8 without a BOM.

For the currently installed system, simply overwrite the files from
this package. Running Repair-Sunday-Config-UTF8.bat is optional because
the new loader already accepts the existing BOM, but it will normalize
the config file if you want to remove the BOM immediately.
