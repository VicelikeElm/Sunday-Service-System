from sunday_common import load_config, obs_connection, obs_port_open, get_obs_status
from sss_reliability import FREEZE_FILE, set_freeze


def main():
    if not FREEZE_FILE.exists():
        return 0

    config = load_config()

    if obs_port_open(
        config
    ):
        try:
            client = obs_connection(
                config,
                timeout=4
            )

            status = get_obs_status(
                client
            )

            if (
                status[
                    "recording"
                ]
                or
                status[
                    "streaming"
                ]
            ):
                print()
                print(
                    "SUNDAY FREEZE: MAINTENANCE BLOCKED"
                )
                print(
                    "=" * 60
                )
                print(
                    "OBS is currently recording or streaming."
                )
                print(
                    "Configuration/maintenance changes are locked "
                    "until the service ends."
                )
                print()
                return 9

            # OBS is reachable and definitely inactive: clear a stale
            # marker automatically.
            set_freeze(
                False
            )

            print(
                "A stale Sunday Freeze marker was cleared; "
                "OBS is not recording/streaming."
            )

            return 0

        except Exception:
            pass

    print()
    print(
        "SUNDAY FREEZE: MAINTENANCE BLOCKED"
    )
    print(
        "=" * 60
    )
    print(
        "The Sunday Freeze marker is active and OBS state could not "
        "be safely verified."
    )
    print()
    print(
        "If the service is truly over, use the Admin/Troubleshooting "
        "screen or Unlock-Sunday-Freeze.bat."
    )
    print()

    return 9


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
