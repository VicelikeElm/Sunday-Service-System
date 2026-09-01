from sss_build_info import APP_VERSION
from sss_update_feed import (
    check_release_feed,
    load_feed_config,
)

print()
print("SUNDAY SERVICE SYSTEM — TRUSTED ONLINE UPDATE FEED CHECK")
print("========================================================")
print()

config = load_feed_config()

print("Enabled:", config.get("enabled"))
print("Channel:", config.get("channel"))
print("Feed URL:", config.get("feed_url") or "(not configured)")
print()

if not config.get("enabled"):
    print("[INFO] Online update feed is not configured.")
    print("Configure it under SSS Setup & Settings -> Updates.")
    raise SystemExit(0)

try:
    result = check_release_feed(
        current_version=APP_VERSION
    )

    release = result.get(
        "latest_release"
    )

    print("[READY] Feed CMS signature and pinned signer verification passed.")
    print(
        "Signer:",
        result.get(
            "signature",
            {}
        ).get(
            "thumbprint",
            ""
        ),
    )

    if release:
        print("Latest:", release.get("version"))
        print("Package:", release.get("package_url"))
        print("Size:", release.get("package_size"))
        print("Update available:", result.get("update_available"))
        print("Client too old:", result.get("client_too_old"))
    else:
        print("No release is listed for the selected channel.")

except Exception as exc:
    print("[FIX] Trusted online update feed check failed:")
    print(exc)
    raise SystemExit(1)

print()
print("This check downloads ONLY the small feed + signature.")
print("It does not download/install an update and does not affect OBS.")
