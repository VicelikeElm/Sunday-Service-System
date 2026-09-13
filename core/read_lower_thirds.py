import re
import shutil
import tempfile
from pathlib import Path

from ccl_chromium_reader import ccl_chromium_localstorage

from sunday_common import load_config


SOURCE_LEVELDB = Path(
    load_config().get(
        "lower_thirds_leveldb",
        r"C:\Users\Vicel\AppData\Roaming\obs-studio"
        r"\plugin_config\obs-browser\Local Storage\leveldb",
    )
)


def copy_leveldb():
    temp_root = Path(
        tempfile.mkdtemp(
            prefix="sermon_ai_lowerthirds_"
        )
    )

    destination = temp_root / "leveldb"

    shutil.copytree(
        SOURCE_LEVELDB,
        destination,
        dirs_exist_ok=True
    )

    return temp_root, destination


def is_interesting_key(key):
    return re.fullmatch(
        r"alt-[1-4]-(?:name|info)-(?:[1-9]|10)",
        key
    ) is not None


def normalize_value(value):

    if value is None:
        return ""

    if isinstance(value, bytes):
        try:
            value = value.decode(
                "utf-8",
                errors="replace"
            )
        except Exception:
            value = str(value)

    value = str(value)

    # Clean a few common Chromium/encoding artifacts
    value = (
        value
        .replace("\x00", "")
        .replace("ΓÇÖ", "’")
        .replace("â€™", "’")
    )

    return value.strip()


def main():

    print()
    print("=" * 72)
    print("ANIMATED LOWER THIRDS - MEMORY SLOT READER")
    print("=" * 72)
    print()

    if not SOURCE_LEVELDB.exists():

        print("OBS lower-third LevelDB folder was not found:")
        print(SOURCE_LEVELDB)
        return

    temp_root = None

    try:

        print("Copying OBS browser storage...")

        temp_root, copied_leveldb = (
            copy_leveldb()
        )

        print("Copy complete.")
        print()

        values = {}

        with ccl_chromium_localstorage.LocalStoreDb(
            copied_leveldb
        ) as local_storage:

            for storage_key in (
                local_storage.iter_storage_keys()
            ):

                try:

                    records = (
                        local_storage
                        .iter_records_for_storage_key(
                            storage_key
                        )
                    )

                    for record in records:

                        key = normalize_value(
                            record.script_key
                        )

                        if not is_interesting_key(
                            key
                        ):
                            continue

                        value = normalize_value(
                            record.value
                        )

                        if not value:
                            continue

                        values[key] = value

                except Exception:
                    continue

        print(
            f"Found {len(values)} populated "
            f"sermon-relevant slot field(s)."
        )

        print()

        for lower_third in range(
            1,
            5
        ):

            print(
                f"LOWER THIRD {lower_third}"
            )

            print(
                "-" * 72
            )

            found_any = False

            for slot in range(
                1,
                11
            ):

                name_key = (
                    f"alt-{lower_third}"
                    f"-name-{slot}"
                )

                info_key = (
                    f"alt-{lower_third}"
                    f"-info-{slot}"
                )

                name = values.get(
                    name_key,
                    ""
                )

                info = values.get(
                    info_key,
                    ""
                )

                if not name and not info:
                    continue

                found_any = True

                print(
                    f"Slot {slot}"
                )

                print(
                    f"  Name: {name}"
                )

                print(
                    f"  Info: {info}"
                )

                print()

            if not found_any:

                print(
                    "(no populated slots)"
                )

                print()

    except Exception as error:

        print()
        print(
            "ERROR reading lower-third storage:"
        )

        print(error)

    finally:

        if temp_root is not None:

            try:

                shutil.rmtree(
                    temp_root,
                    ignore_errors=True
                )

            except Exception:
                pass


if __name__ == "__main__":
    main()
