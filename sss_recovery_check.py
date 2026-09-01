from sss_recovery import (
    last_known_good_snapshot,
    list_recovery_snapshots,
    verify_recovery_snapshot,
)

print()
print("SSS Recovery Snapshot Check")
print("===========================")

items = list_recovery_snapshots()

if not items:
    print("No recovery snapshots exist yet.")
else:
    for item in items:
        path = item.get("path")

        print()
        print(item.get("filename", "snapshot"))
        print("  Type:", item.get("kind", ""))
        print("  Created:", item.get("created_at", ""))
        print("  Profile:", item.get("profile_name", ""))
        print("  Diagnostic:", item.get("diagnostic_overall", ""))

        try:
            manifest = verify_recovery_snapshot(path)
            print(
                "  Verify: OK —",
                manifest.get("file_count", 0),
                "file(s)",
            )
        except Exception as exc:
            print("  Verify: FAILED —", exc)

known_good = last_known_good_snapshot()

print()
print(
    "Last Known Good:",
    known_good if known_good is not None else "Not saved",
)
print()
print("This check is READ-ONLY and does not restore anything.")
