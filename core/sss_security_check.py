from sss_secrets_vault import (
    obs_vault_status,
    security_overview,
    test_obs_vault_connection,
)

print()
print("SUNDAY SERVICE SYSTEM — SECURITY CHECK")
print("======================================")

overview = security_overview()

print("Windows Credential Manager available:", overview.get("vault_available"))
print("OBS password stored in vault:", overview.get("obs_vault_stored"))
print("Legacy loose OBS password detected:", overview.get("legacy_obs_password_present"))
print("Gmail OAuth file detected:", overview.get("gmail_oauth_file_present"))
print("YouTube OAuth file detected:", overview.get("youtube_oauth_file_present"))
print()

if overview.get("legacy_obs_locations"):
    print("Known loose OBS password location(s):")
    for item in overview.get("legacy_obs_locations", []):
        print(" -", item)
    print()

if overview.get("obs_vault_stored"):
    try:
        result = test_obs_vault_connection()
        print(
            "Vaulted OBS connection: READY at",
            str(result.get("host", "")) + ":" + str(result.get("port", "")),
        )
    except Exception as exc:
        print("Vaulted OBS connection: CHECK —", exc)
else:
    print("Vaulted OBS connection: not tested because no vaulted password exists.")

print()
print("No password/token value is displayed by this check.")
print("This check does NOT start/stop Recording or Streaming.")
