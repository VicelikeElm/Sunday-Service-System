from sss_camera_adapters import check_tcp_connection
from sss_profile import (
    get_profile_camera_settings,
    load_active_profile,
)

settings = get_profile_camera_settings(
    load_active_profile()
)

print()
print("SSS Camera Connection Diagnostic")
print("================================")
print("Source:", settings.get("settings_source", "legacy"))
print("Provider:", settings.get("provider", "Not configured"))
print("Host:", settings.get("host", ""))
print("Port:", settings.get("port", 80))
print()

if settings.get("settings_source") != "profile":
    print("Camera PROFILE mode is not active.")
    print("This diagnostic does not inspect the legacy PTZ file.")
elif settings.get("provider") != "PTZOptics / HTTP-CGI":
    print("No network PTZ connection test is required for this provider.")
else:
    result = check_tcp_connection(
        settings.get("host", ""),
        settings.get("port", 80),
        timeout=2.0,
    )
    print("Connection: REACHABLE")
    print("Host:", result.get("host"))
    print("Port:", result.get("port"))

print()
print("This diagnostic is READ-ONLY and DOES NOT move the camera.")
