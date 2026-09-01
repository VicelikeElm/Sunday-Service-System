SSS v3.0 — CODE SIGNING + SIGNED UPDATE MANIFESTS
=================================================

v3.0 creates the trust boundary required before Sunday Service System should
ever be allowed to download/install updates from an online release feed.

REMOTE ONE-CLICK UPDATES ARE STILL DISABLED IN v3.0.

The purpose of this release is to make the local release itself authenticatable.


WHAT v3.0 SIGNS
---------------
A signed release build now signs and RFC 3161 timestamps:

  SundayServiceSystem.exe
  SundayServiceSystemSettings.exe
  SundayServiceSystemUpdater.exe

and, when Inno Setup 6 is installed:

  SundayServiceSystem-Setup-v3.0.0.exe

Authenticode uses:

  SHA-256 file digest
  RFC 3161 timestamping
  SHA-256 timestamp digest


SIGNED UPDATE MANIFEST
----------------------
The .sssupdate package now uses package format 2.

It contains:

  manifest.json
  manifest.p7s
  README.txt

  payload\SundayServiceSystem\...
  payload\SundayServiceSystemSettings\...
  payload\SundayServiceSystemUpdater\...

manifest.p7s is a DETACHED CMS / PKCS#7 signature over the exact bytes of
manifest.json.

The manifest contains SHA-256 + size for every payload file.

Therefore the trust chain is:

  trusted/pinned release certificate
              |
              v
       CMS signed manifest
              |
              v
       SHA-256 file hashes
              |
              v
  Main + Settings + Updater payload

The three application EXEs are ALSO independently required to have valid
Windows Authenticode signatures from a trusted SSS release signer.


SIGNER PINNING
--------------
The signed release build generates:

  sss_release_trust.py

before PyInstaller runs.

That file contains ONLY PUBLIC trust metadata:

  SIGNED_UPDATES_REQUIRED = True
  TRUSTED_UPDATE_SIGNER_THUMBPRINTS = (...)

The trusted certificate thumbprint(s) are then compiled into:

  Main
  Settings
  Updater

An update signed by a different certificate is rejected even if its CMS
signature is cryptographically valid.

This is important before enabling a network update feed.


SIGNING CONFIGURATION
---------------------
Local release/build selection is stored in:

  C:\Church\SermonAI\sss_signing_config.json

It contains only:

  certificate thumbprint
  Windows certificate store location
  optional separate manifest signer thumbprint
  RFC 3161 timestamp URL
  optional SignTool path
  publisher label

It does NOT contain:

  private key
  PFX
  PFX password
  account password
  OAuth token

The actual signing private key remains in the Windows certificate/private-key
provider.


SETUP TOOLS
-----------
Included:

  Configure-SSS-Code-Signing.bat
  Configure-SSS-Code-Signing.ps1

This lists code-signing certificates with accessible private keys from the
Windows certificate store and writes sss_signing_config.json.

Also included:

  Check-SSS-Code-Signing.bat
  Check-SSS-Code-Signing.ps1

The checker verifies:

  configured certificate exists
  private key is available
  Microsoft SignTool exists
  RFC 3161 timestamp URL is configured


LOCAL DEVELOPMENT CERTIFICATE
-----------------------------
For testing the signing pipeline on ONE PC only:

  Create-SSS-Development-Signing-Certificate.bat

This creates a self-signed RSA/SHA-256 Code Signing certificate in:

  CurrentUser\My

and trusts the PUBLIC certificate for the current user under:

  CurrentUser\TrustedPeople

The development private key is marked non-exportable.

IMPORTANT:

  This self-signed certificate is for LOCAL TESTING ONLY.

Do NOT use it for:

  public downloads
  public installer distribution
  a real online updater
  customer/church deployments outside the machine where it is explicitly trusted

Before public distribution, replace it with a real trusted code-signing
certificate and rebuild the release.


SIGNED RELEASE BUILD
--------------------
Build-SSS-Windows-Installer.bat is now a SIGNED RELEASE build.

It refuses to start unless:

  sss_signing_config.json exists
  certificate exists
  private key is available
  SignTool exists
  RFC 3161 timestamp URL exists

Build order:

  1. validate release signing certificate
  2. write trusted signer pins
  3. build Main EXE
  4. Authenticode sign + timestamp Main
  5. build Settings EXE
  6. Authenticode sign + timestamp Settings
  7. build Updater EXE
  8. Authenticode sign + timestamp Updater
  9. build CMS-signed .sssupdate package
  10. build Inno Setup installer when available
  11. Authenticode sign + timestamp installer


UPDATE PACKAGE BUILD
--------------------
After signed EXEs already exist:

  Build-SSS-Update-Package-Only.bat

rebuilds:

  update-output\SundayServiceSystem-Update-v3.0.0.sssupdate

It refuses to create a release package unless Main, Settings, and Updater
already have valid Authenticode signatures from the configured release signer.


RELEASE VERIFICATION
--------------------
Run:

  Verify-SSS-Signed-Release.bat

It verifies:

  local signing configuration
  Main Authenticode signature
  Settings Authenticode signature
  Updater Authenticode signature
  detached CMS manifest signature
  pinned manifest signer
  every SHA-256 payload hash
  installer Authenticode signature when an installer exists

If verification fails:

  DO NOT DISTRIBUTE THE BUILD.


UPDATER SELF-UPDATE
-------------------
v2.9 intentionally left the installed Updater outside normal .sssupdate
replacement.

v3.0 fixes that before remote updates.

A v3.0 update package contains:

  Main
  Settings
  Updater

When installed Settings launches an update, it does NOT run the updater
directly out of Program Files.

Instead it copies the whole Updater onedir application to:

  C:\ProgramData\Sunday Service System\Updates\UpdaterRuntime

and runs that temporary external copy.

Because the running updater is outside Program Files, it can safely replace:

  installed Main
  installed Settings
  installed Updater

as one versioned release.

Old temporary updater-runtime copies are pruned later.


SIGNED UPDATE ACCEPTANCE POLICY
-------------------------------
The v3.0 updater rejects:

  unsigned manifest
  missing manifest.p7s
  invalid CMS signature
  signer not pinned in the installed SSS build
  manifest signer mismatch
  wrong SSS App ID
  unsupported package format
  path traversal
  symbolic-link payload entries
  unmanifested files
  missing manifest files
  invalid file sizes
  invalid SHA-256 hashes
  unsigned/untrusted Main EXE
  unsigned/untrusted Settings EXE
  unsigned/untrusted Updater EXE

It then verifies every INSTALLED file again against the signed manifest after
copying it into Program Files.


UPDATE / ROLLBACK SAFETY
------------------------
Existing v2.9 protections remain:

  Recording active -> UPDATE BLOCKED
  Streaming active -> UPDATE BLOCKED

If OBS is open but SSS cannot verify its output state:

  UPDATE BLOCKED

The updater never:

  starts Recording
  stops Recording
  starts Streaming
  stops Streaming
  changes cameras
  changes slides
  changes audio mute
  changes sermon_plan.json


AUTOMATIC ROLLBACK
------------------
Before installation, v3.0 backs up ALL THREE installed application folders:

  SundayServiceSystem
  SundayServiceSystemSettings
  SundayServiceSystemUpdater

Rollback backups include SHA-256 integrity metadata.

If the updated application fails:

  signed package verification
  file installation
  post-install hash verification
  safe startup health check

then the previous application is automatically restored.

The updater itself therefore rolls back with the Main and Settings apps.


CHURCH DATA REMAINS OUTSIDE RELEASE SIGNING
-------------------------------------------
Application updates still do NOT replace:

  profiles
  sss_signing_config.json
  Windows Credential Manager credentials
  .env
  Gmail OAuth
  YouTube OAuth
  sunday_config.json
  ptz_camera_config.json
  sermon_plan.json
  recordings
  transcripts
  shorts
  Event History
  Recovery snapshots


DIAGNOSTICS
-----------
Full System Diagnostics now includes:

  Release Signatures

Installed EXE mode verifies:

  Main signature
  Settings signature
  Updater signature
  signer thumbprint against the compiled trusted release signer list

If any is missing/invalid/untrusted:

  FIX


FIRST LOCAL TEST
----------------
If you do NOT yet own a public code-signing certificate:

1. Copy the v3.0 patch into:
     C:\Church\SermonAI

2. Run:
     Create-SSS-Development-Signing-Certificate.bat

3. Run:
     Configure-SSS-Code-Signing.bat

4. Run:
     Check-SSS-Code-Signing.bat

5. Run:
     Build-SSS-Windows-Installer.bat

6. Run:
     Verify-SSS-Signed-Release.bat

7. Close installed SSS Main + Settings.

8. Confirm OBS Recording and Streaming are STOPPED.

9. Run:
     Apply-Built-v3.0-Update.bat

10. After update, run Full System Diagnostics and confirm:
      Application Runtime   READY
      Application Updater   READY
      Release Signatures    READY


PUBLIC / ONLINE RELEASE REQUIREMENT
-----------------------------------
Before enabling a real online one-click update feed:

  replace the development self-signed certificate with a real trusted
  code-signing certificate

then:

  Configure-SSS-Code-Signing.bat
  Build-SSS-Windows-Installer.bat
  Verify-SSS-Signed-Release.bat

A release must be rebuilt after changing the trusted signer because the signer
pin is compiled into the installed applications.


NOT YET ENABLED
---------------
v3.0 intentionally does NOT yet include:

  remote update URL
  automatic update download
  release-feed polling
  silent internet update
  unattended update installation

Those should be implemented only AFTER a real production signing certificate
is chosen and this signed release pipeline is proven on Windows.


PROFILE SCHEMA
--------------
No profile migration is required.

Current profile schema remains:

  schema_version: 7
