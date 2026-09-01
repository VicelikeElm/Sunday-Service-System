from sss_obs_profile import discover_obs

data = discover_obs()

print()
print("SSS OBS DISCOVERY")
print("=================")
print("Endpoint:          " + str(data.get("host")) + ":" + str(data.get("port")))
print("Current collection:" , data.get("current_collection"))
print("Legacy collection: " , data.get("legacy_collection"))
print("Current Program:   " , data.get("current_program_scene"))
print("Current Preview:   " , data.get("current_preview_scene"))
print()
print("Collections:")
for name in data.get("collections", []):
    print("  - " + name)
print()
print("Scenes:")
for name in data.get("scenes", []):
    print("  - " + name)
print()
