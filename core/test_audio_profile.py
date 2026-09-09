from sss_audio_adapters import (
    discover_obs_audio_inputs,
    profile_audio_ready,
)
from sss_profile import (
    get_profile_audio_settings,
    load_active_profile,
)

settings = get_profile_audio_settings(
    load_active_profile()
)

print()
print("SSS Audio Profile Diagnostic")
print("============================")
print("Source:", settings.get("settings_source", "legacy"))
print("Provider:", settings.get("provider", "OBS Audio Inputs"))
print("Selected mute inputs:", settings.get("mute_inputs", []))
print()

if settings.get("settings_source") != "profile":
    print("Audio PROFILE mode is not active.")
    print("Legacy SSS audio settings remain authoritative.")
elif settings.get("provider") == "None":
    print("No volunteer audio mute control is configured.")
else:
    data = discover_obs_audio_inputs()
    print("OBS inputs discovered:")
    for name in data.get("inputs", []):
        print(" -", name)

    print()
    ready, detail = profile_audio_ready()
    print("Ready:", ready)
    print("Detail:", detail)

print()
print("This diagnostic is READ-ONLY.")
print("It DOES NOT mute/unmute audio and DOES NOT affect recording or streaming.")
