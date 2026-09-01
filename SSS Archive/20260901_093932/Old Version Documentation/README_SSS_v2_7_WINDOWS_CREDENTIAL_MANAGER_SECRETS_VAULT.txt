SSS v2.7 — WINDOWS CREDENTIAL MANAGER / SECRETS VAULT
======================================================

This implements the next portable-application roadmap item:

  Local protected secrets
  Windows Credential Manager
  OBS WebSocket password migration
  Profile schema 7 security metadata


PROFILE SCHEMA
--------------
v2.7 advances the portable profile format:

  schema 6 -> schema 7

Schema 7 adds ONLY non-secret security metadata:

  security:
    credential_provider: Windows Credential Manager
    secrets_portable: false
    obs_websocket_password:
      storage: local_vault_preferred
      portable: false
    oauth:
      gmail: legacy_local_file
      youtube: legacy_local_file

No password or token value is placed in the church profile.

Existing schema-6 profiles are backed up and automatically migrated through the
versioned migration system from v2.6.


WINDOWS CREDENTIAL MANAGER
--------------------------
The first live protected credential in v2.7 is:

  OBS WebSocket password

It is stored as a Windows Generic Credential with a target similar to:

  SundayServiceSystem/<profile-id>/OBS_WEBSOCKET_PASSWORD

This means credentials are:
  local to the Windows installation/user context
  associated with the active SSS profile ID
  outside portable .sssprofile files
  outside diagnostic ZIPs
  outside Recovery snapshots


RUNTIME PRIORITY
----------------
OBS connection priority is now:

  Windows Credential Manager
            |
            v
      protected password
            |
            v
           OBS

If no protected OBS credential exists:

  existing sunday_common legacy OBS connection path

is used exactly as before.

Therefore installing v2.7 does NOT require immediate credential migration and
does NOT break the current church setup.


SETTINGS UI
-----------
New permanent Settings page:

  SSS Setup & Settings
    -> Security

It includes:

  SAVE PASSWORD TO WINDOWS CREDENTIAL MANAGER

  COPY EXISTING OBS PASSWORD TO VAULT

  TEST VAULTED OBS CONNECTION

  REMOVE LEGACY LOOSE OBS PASSWORD

  DELETE VAULTED OBS PASSWORD

  OPEN WINDOWS CREDENTIAL MANAGER

  REFRESH SECURITY STATUS


COPY EXISTING PASSWORD
----------------------
COPY EXISTING OBS PASSWORD TO VAULT:

  reads the existing OBS password through the current SSS configuration path
  stores it in Windows Credential Manager
  never displays the password
  does NOT remove the old copy

This allows the protected copy to be tested before anything is deleted.


VAULT CONNECTION TEST
---------------------
TEST VAULTED OBS CONNECTION:

  uses the protected Credential Manager password
  performs a harmless OBS GetVersion request
  confirms WebSocket authentication
  does NOT change Program/Preview
  does NOT start Recording
  does NOT stop Recording
  does NOT start Streaming
  does NOT stop Streaming


REMOVE LEGACY LOOSE OBS PASSWORD
--------------------------------
This action is intentionally separate.

Before removing anything, SSS:

  1. confirms a protected vault credential exists
  2. connects to OBS using the protected credential
  3. only continues when that connection succeeds

Then it removes ONLY known loose OBS password entries:

  C:\Church\SermonAI\.env
    OBS_PASSWORD=...

and/or known top-level SSS config keys:

  obs_password
  OBS_PASSWORD

It does NOT touch:
  Gmail OAuth
  YouTube OAuth
  unrelated passwords
  other .env settings

If the protected OBS test fails, nothing is removed.


DELETE VAULTED PASSWORD
-----------------------
Deletion requires explicit confirmation.

If SSS cannot detect a remaining legacy OBS password, the warning clearly
states that deleting the vault credential could prevent connection to
password-protected OBS.

There is no automatic deletion.


PASSWORD FIELD BEHAVIOR
-----------------------
The Security page NEVER loads an existing vault password into the text field.

It can report:

  PROTECTED
  NOT STORED

but does not reveal the credential value.


GMAIL / YOUTUBE OAUTH
---------------------
v2.7 deliberately does NOT move Gmail or YouTube OAuth refresh-token files.

Those are application-managed refreshable JSON files. Moving them into Windows
Credential Manager without changing the Google/YouTube token-refresh code could
break authorization renewal.

They remain:

  local-only
  excluded from .sssprofile exports
  excluded from diagnostic bundles
  excluded from Recovery snapshots

A later credential-adapter stage can migrate them together with their refresh
logic safely.


DIAGNOSTICS
-----------
Full System Diagnostics now includes:

  Secrets Vault

Typical results:

READY
  OBS password is protected and no known loose OBS password remains

CHECK
  protected copy exists but loose OBS_PASSWORD still remains

CHECK
  OBS password is still using loose legacy configuration

READY
  no password exists in either location and OBS authentication may be disabled

OBS connectivity itself is still independently verified by the normal OBS
diagnostic.


EVENT HISTORY
-------------
New event category:

  SECURITY

Event History records actions such as:

  OBS password stored in Windows Credential Manager
  legacy loose OBS password removed
  vaulted OBS password deleted

No secret values are logged.


ADMIN / DIRECT ACCESS
---------------------
Main SSS:

  ADMIN / TROUBLESHOOTING
    -> SECURITY / SECRETS VAULT

Direct Settings launcher:

  Open-SSS-Security.bat

Read-only command-line check:

  Check-SSS-Security.bat

The read-only check reports credential/storage status and may test the protected
OBS connection. It never prints the password.


RECOVERY
--------
Windows Credential Manager is intentionally OUTSIDE SSS Recovery snapshots.

Restoring application files or profiles does not roll back or reveal protected
Windows credentials.

Existing v2.4 Recovery protections still exclude:
  .env
  Gmail credentials
  Gmail OAuth token
  password/token/secret files

This creates a cleaner separation:

  Portable profile
       = church configuration, NO secrets

  Recovery
       = SSS application/config rollback, NO secrets

  Windows Credential Manager
       = local protected secrets


SAFETY
------
v2.7 does NOT alter the Sunday service-control model.

Recording and Streaming remain:
  separate
  manual
  human-gated

The Secrets Vault never:
  starts Recording
  stops Recording
  starts Streaming
  stops Streaming
  moves cameras
  changes slides
  changes audio mute
  refreshes Gmail
  changes sermon_plan.json


TESTS PERFORMED
---------------
v2.7 was checked for:

  schema 6 -> schema 7 migration
  security metadata contains no secret value
  LEGACY integration behavior remains unchanged
  loose .env OBS_PASSWORD detection/removal
  loose sunday_config OBS password removal
  no remaining direct obs_connection use in main SSS/OBS profile layer
  all Python files compile successfully

Windows Credential Manager itself must be live-tested on the church Windows PC
because this build environment is not Windows.


CURRENT PORTABLE SSS PROGRESS
-----------------------------
Profile Layer                         READY
Profile import/export/switch          READY
First-run setup wizard                READY
OBS profile adapter                   READY
WorshipTools Presenter adapter        READY
ProPresenter adapter                  READY
Capability-based volunteer UI         READY
Setup & Settings app                  READY
PTZOptics Camera adapter              READY
OBS Audio adapter                     READY
Sermon Source adapters                READY
Full System Diagnostics               READY
Backup / Restore                      READY
Last Known Good                       READY
Crash / startup recovery              READY
Human-friendly Event History          READY
Versioned profile migrations          READY
Windows Credential Manager vault      READY
OBS protected-password adapter        READY

Logical next polish item:

  Standalone EXE / installer foundation + stable Windows application identity

The app now has enough configuration, migration, diagnostics, recovery, and
credential separation to begin packaging without hard-coding this church's
machine-specific secrets into the installed application.


INSTALL
-------
Close SSS and Settings.

Copy all files from this ZIP into:

  C:\Church\SermonAI

Overwrite matching code files.

The active schema-6 profile may migrate automatically to schema 7. Its exact
old JSON is backed up first.

Recommended first test:

  1. Leave the current loose OBS password in place.
  2. Open Settings -> Security.
  3. Click COPY EXISTING OBS PASSWORD TO VAULT.
  4. Click TEST VAULTED OBS CONNECTION.
  5. Confirm normal SSS OBS controls still work.
  6. Only then use REMOVE LEGACY LOOSE OBS PASSWORD if desired.

No profile JSON, sunday_config.json, .env, credential, Gmail token, OAuth token,
sermon_plan.json, ptz_camera_config.json, or Recovery snapshot is included in
this patch ZIP.
