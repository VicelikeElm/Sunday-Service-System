from sss_profile import (
    get_profile_presentation_settings,
    load_active_profile,
)
from sss_propresenter_api import (
    connection_test,
    get_active_presentation,
)

settings = get_profile_presentation_settings(
    load_active_profile()
)

host = settings.get("host", "127.0.0.1")
port = settings.get("port", 50001)

print()
print("SSS ProPresenter API diagnostic")
print("==============================")
print("Host:", host)
print("Port:", port)
print()

result = connection_test(host, port, timeout=3.0)

print("Connection: OK")
print("Base URL:", result.get("base_url"))
print("Version:", result.get("version"))
print()

try:
    active = get_active_presentation(host, port, timeout=3.0)
    print("Active presentation:")
    print(active)
except Exception as exc:
    print("Active presentation check failed:", exc)

print()
print("This diagnostic DOES NOT change slides.")
