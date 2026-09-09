from sss_profile import (
    PROFILE_SCHEMA_VERSION,
    list_profile_migration_status,
    migration_backups_dir,
)

print()
print("SSS Profile Schema Check")
print("========================")
print("Current SSS schema:", PROFILE_SCHEMA_VERSION)
print()

items = list_profile_migration_status()

if not items:
    print("No installed profiles were found.")
else:
    for item in items:
        print(
            "["
            + str(item.get("status", "ERROR"))
            + "] "
            + str(item.get("profile_name", "Profile"))
        )
        print(
            "    schema:",
            item.get("schema_version", "?"),
            "-> current:",
            item.get("current_schema_version", PROFILE_SCHEMA_VERSION),
        )
        print(
            "    ",
            item.get("detail", ""),
        )

print()
print("Migration backups folder:")
print(migration_backups_dir())
print()
print("This check is READ-ONLY. It does not migrate inactive profiles.")
print(
    "The active profile may already have been automatically migrated during "
    "normal SSS/profile loading."
)
