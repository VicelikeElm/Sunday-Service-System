SSS v2.8.2 — WINDOWS BUILD LOCK HOTFIX
=======================================

The v2.8.1 dependency fix worked:
  obsws_python READY
  PyInstaller READY
  obsws_python visible to builder

The new failure is unrelated to Python dependencies.

Windows reported:
  Access is denied
  The process cannot access the file because it is being used by another process

for files inside:
  C:\Church\SermonAI\dist\SundayServiceSystem

That means the OLD packaged SundayServiceSystem.exe was still running and
Windows was keeping its EXE/DLL files locked.


v2.8.2 FIX
----------
Before deleting dist/build output, the build now checks for processes whose
ExecutablePath is inside:

  C:\Church\SermonAI\dist

If one is running, the build STOPS cleanly and shows the process/PID instead of
half-deleting the folder and then failing inside shutil.rmtree.


STUCK OLD EXE HELPER
--------------------
Included:

  Close-Old-SSS-Build-EXEs.bat

It asks for confirmation, then can force-close ONLY:

  SundayServiceSystem.exe
  SundayServiceSystemSettings.exe

It does NOT close:
  OBS
  python.exe
  pythonw.exe

Because OBS is a separate process, this helper does not stop OBS Recording or
Streaming.


CLEANUP RETRY
-------------
build_sss_windows.py also now retries normal Windows file cleanup briefly.

If a packaged SSS EXE is the lock holder, it reports that explicitly.

If Windows/antivirus temporarily has a file open, cleanup gets several short
retries before failing with a clearer message.


WHAT TO DO NOW
--------------
1. Copy this hotfix into:
     C:\Church\SermonAI

2. Close the old SundayServiceSystem.exe error dialog/window.

3. If Windows still says the EXE is running, run:
     Close-Old-SSS-Build-EXEs.bat

4. Run:
     Build-SSS-Windows-Installer.bat

5. Test the fresh:
     C:\Church\SermonAI\dist\SundayServiceSystem\
       SundayServiceSystem.exe


SAFETY
------
This patch only changes packaging/build cleanup.

It does not alter Sunday Service System service behavior.

Recording and Streaming remain separate manual/human-gated OBS controls.
