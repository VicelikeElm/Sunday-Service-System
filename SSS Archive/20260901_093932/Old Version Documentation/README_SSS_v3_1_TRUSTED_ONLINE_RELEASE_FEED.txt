SSS v3.1 — TRUSTED ONLINE RELEASE FEED + ONE-CLICK VERIFIED DOWNLOAD
===================================================================

v3.1 is the next release-management stage after v3.0 code signing.

v3.0 established:
  Authenticode-signed Main / Settings / Updater
  pinned release signer thumbprints
  CMS/PKCS#7 signed .sssupdate manifests
  SHA-256 payload manifests
  automatic rollback

v3.1 now adds:
  signed HTTPS release feed
  feed signer verification
  safe remote package download
  package hash verification against the signed feed
  normal v3.0 signed-package verification again after download
  one-click DOWNLOAD + VERIFY + INSTALL path

NO AUTOMATIC BACKGROUND INSTALLATION is added.


TRUST CHAIN
-----------
The online update chain is now:

  HTTPS server
      |
      v
  latest.json
      |
      +--> latest.json.p7s
             |
             v
       pinned SSS signer
             |
             v
       signed release metadata
             |
             v
       package URL + SHA-256 + byte size
             |
             v
       downloaded .sssupdate
             |
             v
       signed package manifest.p7s
             |
             v
       SHA-256 payload files
             |
             v
       Authenticode Main + Settings + Updater
             |
             v
       protected updater + automatic rollback

HTTPS is required, but HTTPS is NOT the only trust check.

If the website/CDN is compromised but the attacker does not have the pinned
SSS signing private key, the forged feed/package is rejected.


SETTINGS -> UPDATES
-------------------
The Updates page now includes:

  Trusted Online Release Feed

  Feed URL:  [ https://.../latest.json ]
  Channel:   [ stable | beta ]

  [ SAVE FEED ]
  [ CHECK ONLINE ]

  [ DOWNLOAD + VERIFY ]
  [ DOWNLOAD + VERIFY + INSTALL ]

The existing local package controls remain available underneath.

The online feed is NOT checked automatically when Sunday Mode starts.


FEED CONFIGURATION
------------------
Feed settings are application-global and stored under the existing updater
ProgramData area:

  C:\ProgramData\Sunday Service System\Updates\feed_config.json

This is not a church profile and is not exported in .sssprofile files.

The feed URL must use HTTPS.

Embedded username/password URLs are rejected.

The normal signature URL is automatically:

  <feed-url>.p7s

Example:

  Feed:
    https://updates.example.com/stable/latest.json

  Signature:
    https://updates.example.com/stable/latest.json.p7s


DIRECT CONFIGURATION TOOL
-------------------------
You can configure the same setting outside the GUI with:

  Configure-SSS-Online-Update-Feed.bat

Then test only the small feed/signature with:

  Check-SSS-Online-Update-Feed.bat


SIGNED RELEASE FEED FORMAT
--------------------------
The signed feed uses:

  feed_format: 1

and contains:

  SSS App ID
  channel
  generated time
  signer thumbprint
  releases

Each release contains:

  version
  channel
  published time
  HTTPS package URL
  package SHA-256
  package byte size
  short summary
  optional HTTPS release-notes URL
  minimum update-client version
  withdrawn flag


FEED SIGNATURE
--------------
latest.json is signed as exact bytes with a detached CMS / PKCS#7 signature:

  latest.json.p7s

The client verifies:
  CMS signature
  signer certificate thumbprint
  signer pin compiled into the installed SSS build
  feed App ID
  feed format
  channel

If any of those checks fail:

  UPDATE FEED REJECTED


HTTPS RULES
-----------
v3.1 allows remote release traffic only over:

  https://

It rejects:

  http://
  file://
  embedded URL username/password credentials
  redirect from HTTPS to non-HTTPS

The client uses the Windows/Python trusted TLS certificate authorities.

Requests ask for:

  Accept-Encoding: identity

so a CDN/web server does not transparently recompress the exact signed JSON
bytes and invalidate the detached feed signature.


DOWNLOAD SAFETY
---------------
The signed feed commits to BOTH:

  package SHA-256
  package byte size

During download, SSS enforces:
  HTTPS
  final redirect URL still HTTPS
  maximum update size
  signed expected byte size
  streaming SHA-256

After the download completes, SSS THEN runs the full v3.0 package verifier:

  signed manifest
  pinned signer
  package-format check
  safe archive paths
  no symbolic links
  no unmanifested files
  payload SHA-256
  Authenticode Main
  Authenticode Settings
  Authenticode Updater

The downloaded file is not offered for installation unless all layers pass.


DOWNLOAD LOCATION
-----------------
Verified online packages are staged under:

  C:\ProgramData\Sunday Service System\Updates\Downloads

The feed/check state is stored in:

  C:\ProgramData\Sunday Service System\Updates\feed_state.json


ONE-CLICK INSTALL
-----------------
The button:

  DOWNLOAD + VERIFY + INSTALL

does the following:

  1. saves the currently-entered HTTPS feed URL/channel
  2. downloads and verifies the signed feed
  3. selects the newest compatible release
  4. downloads the package
  5. verifies feed SHA-256 + size
  6. verifies the package's signed manifest
  7. verifies Authenticode payloads
  8. hands the verified local package to the existing protected updater
  9. shows the normal final installation confirmation

The final updater still checks live-service safety immediately before replacing
files.


NO SILENT / BACKGROUND INSTALL
------------------------------
v3.1 does NOT:
  periodically poll the internet in Sunday Mode
  download an update without a user action
  install an update silently
  force restart SSS
  stop OBS
  stop Recording
  stop Streaming

Online checks/downloads are initiated by the operator.


LIVE-SERVICE SAFETY
-------------------
The final install/rollback path remains unchanged:

  OBS Recording active
      -> INSTALL BLOCKED

  OBS Streaming active
      -> INSTALL BLOCKED

  OBS running but output state cannot be verified
      -> INSTALL BLOCKED

Checking the small signed feed or downloading a package does not modify OBS.


BUILDING A SIGNED ONLINE FEED
-----------------------------
First build the normal signed release:

  Build-SSS-Windows-Installer.bat

Expected package:

  C:\Church\SermonAI\update-output\
    SundayServiceSystem-Update-v3.1.0.sssupdate

Then run:

  Build-SSS-Signed-Release-Feed.bat

It asks for:

  HTTPS base URL
  stable/beta channel
  optional short release summary
  optional release-notes URL

Example base URL:

  https://updates.example.com/stable

The builder creates:

  C:\Church\SermonAI\release-feed-output\stable\
    latest.json
    latest.json.p7s
    SundayServiceSystem-Update-v3.1.0.sssupdate
    README_UPLOAD.txt

Upload the CONTENTS of that folder to the HTTPS base URL.

Do not edit latest.json after signing it.

If latest.json changes by one byte, latest.json.p7s no longer verifies.


LOCAL RELEASE-FEED VERIFICATION
-------------------------------
Before uploading:

  Verify-SSS-Release-Feed.bat

This verifies:
  local latest.json CMS signature
  pinned feed signer
  package SHA-256
  package byte size
  package signed manifest
  package Authenticode payloads

The main release gate:

  Verify-SSS-Signed-Release.bat

also verifies the stable feed automatically when one has been built.


HOSTING
-------
v3.1 is host/provider agnostic.

The release folder can be hosted on any static HTTPS service that serves files
without modifying their bytes.

Examples could include:
  a normal HTTPS web server
  static object storage/CDN
  a release-download host

The SSS client does not require hosting credentials.

Do NOT embed private upload credentials into SSS.


CHANNELS
--------
Supported client channels:

  stable
  beta

The feed may contain releases for either channel.

A client configured for STABLE ignores BETA entries.

A BETA client only selects BETA entries from that feed.


MINIMUM UPDATE CLIENT VERSION
-----------------------------
A release can declare:

  minimum_update_client_version

If the current installed SSS update client is older than that requirement, the
feed is still cryptographically verified, but SSS refuses the package and tells
the operator to use a newer installer/update client.

This prevents a future package-protocol change from being handed to a client
that cannot safely understand it.


WITHDRAWN RELEASES
------------------
A feed entry can set:

  withdrawn: true

The v3.1 client ignores that release.

Because the feed itself is signed, withdrawing/replacing a release requires a
new valid feed signature.


EVENT HISTORY
-------------
Successful online operations record UPDATES events such as:

  Signed online release feed checked
  Online update downloaded and fully verified

No passwords or private signing-key data are logged.


DIAGNOSTICS
-----------
Full System Diagnostics now includes:

  Online Update Feed

The diagnostic is deliberately NON-NETWORKING.

It checks:
  feed configured or not
  HTTPS URL format
  trusted release signer pins exist

It does not contact the update server during a normal Full System Test.

For an explicit real network check use:

  Check-SSS-Online-Update-Feed.bat


FIRST v3.0 -> v3.1 TEST
-----------------------
1. Copy this patch into:
     C:\Church\SermonAI

2. Keep the SAME signing certificate/configuration that was used for the v3.0
   trusted release, unless intentionally rotating the release signer.

3. Run:
     Check-SSS-Code-Signing.bat

4. Run:
     Build-SSS-Windows-Installer.bat

5. Run:
     Verify-SSS-Signed-Release.bat

6. Close installed SSS Main + Settings.

7. Confirm OBS Recording/Streaming are stopped.

8. Run:
     Apply-Built-v3.1-Update.bat

9. Confirm Full System Diagnostics.

10. Build a test online feed:
      Build-SSS-Signed-Release-Feed.bat

11. Upload the feed folder to an HTTPS test location.

12. In:
      Settings -> Updates

    enter:
      https://YOUR-HOST/stable/latest.json

13. Click:
      CHECK ONLINE

14. For a future version newer than 3.1, use:
      DOWNLOAD + VERIFY + INSTALL


IMPORTANT TESTING NOTE
----------------------
A v3.1 client checking a feed whose latest release is also v3.1 correctly says
it is UP TO DATE.

To exercise the full online-download/upgrade path, the hosted feed must point
to a version newer than the installed client.


RELEASE SIGNING
---------------
All v3.0 signing requirements remain.

For public/production distribution, use a real trusted code-signing
certificate.

The development self-signed certificate remains for LOCAL TESTING ONLY.


PROFILE SCHEMA
--------------
No profile migration is required.

Current profile schema remains:

  schema_version: 7


WHAT v3.1 STILL DOES NOT DO
---------------------------
v3.1 deliberately does NOT add:

  automatic periodic update polling
  push update notifications
  forced/silent update
  automatic feed publishing/upload credentials
  automatic DNS/web-host configuration

Those are policy/hosting choices, not prerequisites for a secure manual
one-click online updater.

The cryptographic and download path is now in place.


SUNDAY RULE
-----------
Recording and Streaming remain separate manual/human-gated controls.

No update check, download, installation, or rollback starts or stops them.
