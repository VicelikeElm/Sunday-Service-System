SSS v2.6 — VERSIONED PROFILE MIGRATIONS
=======================================

This implements the next portable-application roadmap item:

  Versioned profile schema migrations
  Automatic safe profile upgrades
  Pre-migration backups
  Future-schema protection


CURRENT PROFILE SCHEMA
----------------------
v2.6 uses:

  schema_version: 6

Older SSS builds kept schema_version at 1 while the profile gained more
features. v2.6 formalizes those generations so future versions can evolve the
profile format safely.


MIGRATION CHAIN
---------------
The migration engine upgrades one version at a time:

  Schema 1 -> 2
    First-run setup state
    Capability-based volunteer controls

  Schema 2 -> 3
    Presentation adapter connection structure

  Schema 3 -> 4
    Camera adapter connection / preset structure

  Schema 4 -> 5
    Audio adapter / OBS mute-target structure

  Schema 5 -> 6
    Sermon Source adapter structure
    Migration metadata/history


NO BEHAVIOR GUESSING
--------------------
Migration is additive/conservative.

It preserves:
  existing PROFILE integrations as PROFILE
  existing LEGACY integrations as LEGACY
  unknown/custom profile fields
  current church/profile identity
  existing configured values

It NEVER turns a LEGACY integration into PROFILE merely because the profile
was upgraded.

For an old profile that never had capability-based UI settings, Volunteer
Controls default to LEGACY/full UI so controls cannot disappear after upgrade.


AUTOMATIC ACTIVE-PROFILE MIGRATION
----------------------------------
When SSS loads the active profile:

  old schema detected
       ->
  original JSON copied to Migration Backups
       ->
  migrations run in memory
       ->
  final schema validates
       ->
  upgraded profile written atomically

The active profile is therefore automatically brought current when v2.6 first
uses it.


PRE-MIGRATION BACKUPS
---------------------
Before an installed profile is rewritten, its exact old JSON is copied to:

  <SSS profile root>\Migration Backups

Example:

  baptist_church_of_perry_schema1_to6_2026-08-28_15-43-00.json

These backups are separate from the v2.4 Recovery system.

Recovery snapshots intentionally do not recursively copy Migration Backups,
avoiding backup-inside-backup growth.


MIGRATION HISTORY
-----------------
Current profiles can contain:

  migration:
    history
    last_migrated_at
    last_migrated_from
    last_migrated_to

The history is bounded to the most recent 25 migration records.


FUTURE PROFILE PROTECTION
-------------------------
If a profile has a schema NEWER than this SSS build supports, v2.6 refuses to
migrate or rewrite it.

Example:

  installed SSS supports schema 6
  imported profile says schema 7

Result:

  NEWER / unsupported
  profile is NOT modified

SSS does not guess what a future profile means.


IMPORTS / EXPORTS
-----------------
Import:
  older .sssprofile files are upgraded in memory before installation
  future unsupported schemas are rejected
  imported secrets remain prohibited

Export:
  always exports the current schema
  credentials/tokens/passwords remain excluded


SETTINGS UI
-----------
Open:

  SSS Setup & Settings
    -> Advanced
    -> Profile Format / Versioned Upgrades

Controls:

  [ CHECK PROFILE SCHEMAS ]

  [ MIGRATE ALL INSTALLED PROFILES ]

  [ OPEN MIGRATION BACKUPS ]


ACTIVE VS INACTIVE PROFILES
---------------------------
The active profile upgrades automatically on load.

Inactive profiles are not silently rewritten just because they exist.

MIGRATE ALL INSTALLED PROFILES is the explicit bulk-upgrade command for
inactive profiles. It asks for confirmation and backs up each old profile
before rewrite.


ADMIN SHORTCUT
--------------
Main SSS:

  ADMIN / TROUBLESHOOTING
    -> PROFILE UPGRADES


DIRECT / DEBUG TOOLS
--------------------
Open Profile Upgrades UI:

  Open-SSS-Profile-Upgrades.bat

Read-only schema checker:

  Check-SSS-Profile-Schemas.bat

The read-only checker reports:
  CURRENT
  UPGRADE
  NEWER
  ERROR

It does not migrate inactive profiles.


DIAGNOSTICS
-----------
Full System Diagnostics now includes the active profile schema number in the
Church Profile result.


RECOVERY
--------
The existing v2.4 Recovery system still handles full application rollback.

Profile Migration Backups provide a second, smaller safety layer specifically
for schema conversion.

Normal update ZIPs still do NOT include or overwrite:
  profile JSON
  migration backups
  recovery snapshots
  sunday_config.json
  ptz_camera_config.json
  sermon_plan.json
  .env
  Gmail tokens
  credentials


TESTS PERFORMED
---------------
The v2.6 migration engine was tested with:

  schema 1 -> schema 6
  LEGACY settings remain LEGACY
  existing PROFILE settings remain PROFILE
  old profiles default Volunteer Controls safely to LEGACY
  future schema is rejected
  disk migration creates a pre-migration backup
  atomic migrated file reports CURRENT
  new profiles are created directly at schema 6


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

Logical next polish item:

  Secrets vault / Windows Credential Manager

That removes machine credentials from loose configuration files and creates a
clean separation between portable church profiles and local protected secrets.


INSTALL
-------
Close SSS and Settings.

Copy all files from this ZIP into:

  C:\Church\SermonAI

Overwrite matching code files.

On first load, the ACTIVE old profile may be automatically migrated. Its exact
pre-migration JSON is backed up before rewrite.

No live Recording/Streaming state is changed by profile migration.
