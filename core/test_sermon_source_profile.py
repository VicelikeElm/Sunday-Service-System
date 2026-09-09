from sss_profile import (
    get_profile_sermon_source_settings,
    load_active_profile,
)
from sss_sermon_sources import (
    profile_sermon_source_ready,
    read_canonical_sermon_plan,
)

settings = get_profile_sermon_source_settings(
    load_active_profile()
)

print()
print("SSS Sermon Source Diagnostic")
print("============================")
print("Source:", settings.get("settings_source", "legacy"))
print("Provider:", settings.get("provider", "Manual"))
print()

ready, detail = profile_sermon_source_ready()
print("Profile source ready:", ready)
print("Detail:", detail)
print()

plan = read_canonical_sermon_plan()

if plan:
    print("Current canonical sermon_plan.json:")
    print(" Service date:", plan.get("service_date", ""))
    print(" Title:", plan.get("title", ""))
    print(" Scripture:", plan.get("scripture", ""))
    print(" Points:", len(plan.get("points", []) or []))
    print(" Plan ID:", plan.get("plan_id", ""))
else:
    print("No canonical sermon_plan.json is currently loaded.")

print()
print("This diagnostic is READ-ONLY.")
print("It does NOT refresh Gmail and does NOT overwrite sermon_plan.json.")
