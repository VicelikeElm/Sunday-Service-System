SSS v2.8.1 — EXE BUILD DEPENDENCY HOTFIX
=========================================

FIXED ERROR
-----------
The first v2.8 Windows EXE could fail immediately with:

  ModuleNotFoundError: No module named 'obsws_python'

Root cause:

  v2.8 created a completely isolated build venv containing PyInstaller,
  but that build venv did NOT contain the production SSS runtime packages.

The normal Python SSS worked because obsws_python is installed in:

  C:\Church\SermonAI\venv

but the EXE builder could not see it, so PyInstaller omitted it.


v2.8.1 BUILD MODEL
------------------
The corrected build does this:

  Production SSS Python:
    C:\Church\SermonAI\venv\Scripts\python.exe
        |
        | provides all REAL SSS runtime dependencies
        | including obsws_python
        v
      PyInstaller analysis

PyInstaller itself is still isolated in:

  C:\Church\SermonAI\.sss-build-tools

It is installed with pip --target and exposed through PYTHONPATH only while
the build is running.

Therefore:
  SSS runtime dependencies are visible
  PyInstaller is NOT installed into the production venv


WHAT TO DO
----------
1. Copy this hotfix into:
     C:\Church\SermonAI
   and overwrite the v2.8 build files.

2. Run:
     Build-SSS-Windows-Installer.bat

3. The script automatically DELETES the previous:
     dist
     build
     installer-payload

   so the broken v2.8 EXE cannot be accidentally reused.

4. Test ONLY the newly-created:
     C:\Church\SermonAI\dist\SundayServiceSystem\
       SundayServiceSystem.exe


BUILD PREFLIGHT
---------------
Before PyInstaller starts, v2.8.1 now explicitly checks:

  import obsws_python

using the same production Python environment that will perform the build.

If that import fails, the build stops before producing another broken EXE.


PYINSTALLER
-----------
obsws_python is now also explicitly included with:

  --hidden-import obsws_python
  --collect-submodules obsws_python

in addition to PyInstaller's normal dependency analysis.


SAFETY
------
This hotfix only changes the Windows packaging/build process.

It does NOT change:
  Recording behavior
  Streaming behavior
  Camera behavior
  Presenter behavior
  Audio behavior
  Sermon workflow
  profiles
  credentials
  sermon_plan.json
  ptz_camera_config.json

Recording and Streaming remain separate manual/human-gated controls.
