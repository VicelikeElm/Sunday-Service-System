SSS v2.2 — PROFILE-BACKED SERMON SOURCE ADAPTER
================================================

This implements the next portable-app roadmap item:

  Profile-backed Sermon Information sources


LIVE SERMON SOURCE ADAPTERS
---------------------------
Manual                READY
Pastor Email          READY
Imported File (JSON)  READY
Planning Software     PLANNED as a source
Other                 PLANNED


LEGACY SAFETY
-------------
Existing profiles remain LEGACY unless Sermon Source Setup explicitly saves
PROFILE.

LEGACY preserves the current Perry production workflow:

  Friday pastor email
    -> date-guarded gmail_sermon_importer.py
    -> sermon_plan.json
    -> lower thirds / chapters / Planning / post-service pipeline

Installing v2.2 does not switch the existing church away from that workflow.


SETUP & SETTINGS
----------------
Open:

  Profile label
    -> Sermon
    -> CONFIGURE SERMON SOURCE FOR THIS PROFILE

Choose:

  Configuration Source
    LEGACY
    PROFILE

  Provider
    Manual
    Pastor Email
    Imported File
    Planning Software
    Other


MANUAL SOURCE
-------------
Manual PROFILE mode stores inside the portable .sssprofile:

  service date
  sermon title
  Scripture
  preacher
  sermon points

The default new manual service date is the upcoming Sunday.

SAVE:
  saves configuration/profile data only
  does NOT immediately overwrite sermon_plan.json

APPLY PROFILE SOURCE NOW:
  intentionally writes the profile plan to the normal sermon_plan.json

When Sunday apps launch, a saved PROFILE + Manual plan is automatically
materialized before lower thirds and named chapter hotkeys are prepared.


PASTOR EMAIL SOURCE
-------------------
PROFILE + Pastor Email deliberately reuses the existing proven date-guarded
Gmail importer.

The profile stores:
  provider choice
  expected sender metadata
  whether to refresh Pastor Email automatically when Sunday apps launch

Machine-local files remain machine-local:
  gmail_credentials.json
  gmail_token.json
  OAuth credentials / tokens

They are NEVER exported in .sssprofile.

APPLY PROFILE SOURCE NOW with Pastor Email:
  explicitly runs the existing Gmail importer
  then reads the resulting sermon_plan.json

The existing importer's upcoming-Sunday/date guard remains authoritative.


IMPORTED FILE SOURCE
--------------------
v2.2 supports JSON sermon-plan imports.

IMPORT SERMON PLAN JSON:
  validates the selected JSON
  stores the normalized plan INSIDE the church profile

That means the imported sermon plan can travel with an exported .sssprofile
without depending on the original source-file path.

Required plan data:
  service_date
  title
  scripture
  one or more points

Accepted common aliases include:
  title / sermon_title
  scripture / text / reference
  points / outline
  preacher / speaker
  service_date / date

If plan_id is missing, SSS generates a stable profile plan ID.


CANONICAL PIPELINE
------------------
SSS deliberately keeps sermon_plan.json as the canonical runtime handoff.

This means the already-working downstream systems do not need to be rewritten:

  Scripture controls
  sermon chapter rotation
  lower-third synchronization
  named OBS chapter hotkeys
  Planning Scripture sync
  YouTube/post-service processing
  Sermon AI

PROFILE sources feed the same canonical file instead of creating a parallel
Sunday workflow.


IMPORTANT EMAIL PROTECTION
--------------------------
When the active Sermon Source is:

  PROFILE + Manual
or
  PROFILE + Imported File

SSS suppresses the automatic Gmail import so Friday email cannot overwrite the
explicit profile plan.

When the active source is:

  PROFILE + Pastor Email

the profile's Auto Refresh option controls the startup email refresh.

LEGACY keeps the existing auto_import_sermon_email setting.


PLANNING SOFTWARE
-----------------
Planning Software is recognized as a source adapter slot, but PROFILE mode is
not enabled yet.

The current WorshipTools Planning integration is an outbound sync:
  sermon_plan.json -> Planning Scripture item

It is not yet a reliable source for the whole sermon title/outline, so v2.2
refuses to activate Planning Software as a PROFILE source rather than guessing.


CHECK / APPLY SAFETY
--------------------
CHECK SOURCE:
  read-only against the saved source configuration

SAVE:
  saves profile configuration only

APPLY PROFILE SOURCE NOW:
  intentional action that updates sermon_plan.json
  or explicitly runs the Pastor Email importer

After an APPLY while SSS is already open, use LAUNCH SUNDAY APPS or restart SSS
before service so the existing lower-third/chapter-label preparation runs.


DIAGNOSTIC
----------
Included:

  Test-Sermon-Source-Profile.bat

It reads:
  active source
  adapter readiness
  current canonical sermon plan

It does NOT refresh Gmail and does NOT modify sermon_plan.json.


UNCHANGED
---------
Recording and streaming remain separate manual/human-gated controls.

This patch does not alter:
  OBS scene control
  Presentation
  Camera
  Audio
  Scripture Presenter MIDI
  PTZ legacy file
  YouTube
  Sermon AI

No profile JSON, sermon_plan.json, Gmail token, OAuth credentials, .env,
ptz_camera_config.json, sunday_config.json, or passwords are included.


INSTALL
-------
Close SSS and Settings.

Copy all files from this ZIP into:

  C:\Church\SermonAI

Overwrite matching code files.

Then:
  SSS -> Profile -> Sermon
