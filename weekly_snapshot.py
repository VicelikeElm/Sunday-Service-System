from sunday_common import load_config
from sss_reliability import weekly_snapshot


def main():
    config = load_config()

    destination = weekly_snapshot(
        retention_weeks=int(
            config.get(
                "weekly_backup_retention_weeks",
                12
            )
        )
    )

    print(
        f"Weekly snapshot ready: {destination}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
