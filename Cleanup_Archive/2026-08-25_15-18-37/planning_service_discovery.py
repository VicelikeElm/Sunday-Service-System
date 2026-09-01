import re
import traceback
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(r"C:\Church\SermonAI")
PROFILE = BASE / "WorshipTools_Planning_Profile"
OUTPUT = BASE / "Planning_Service_Discovery.txt"
ERROR_LOG = BASE / "Planning_Service_Discovery_Error.txt"
SCREENSHOT = BASE / "Planning_Service_Discovery.png"

PLANNING_URL = "https://planning.worshiptools.com"


def next_sunday(today=None):
    today = today or datetime.now().date()
    days = (6 - today.weekday()) % 7
    if days == 0:
        days = 7
    return today + timedelta(days=days)


def clean(value):
    if value is None:
        return ""
    return re.sub(
        r"\s+",
        " ",
        str(value)
    ).strip()


def safe_write(lines):
    OUTPUT.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main():
    lines = []

    def add(value=""):
        lines.append(str(value))

    target = next_sunday()

    add("WORSHIPTOOLS PLANNING SERVICE DISCOVERY V3.1")
    add("=" * 90)
    add(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    add(f"Target Sunday: {target.isoformat()}")
    add()

    # Create the text file immediately so a partial result always exists.
    safe_write(lines)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        add("ERROR: Playwright is not installed.")
        add("Run Setup-Planning-Diagnostic.bat first.")
        safe_write(lines)
        print("\n".join(lines))
        input("Press Enter to close...")
        return 1

    print()
    print("=" * 72)
    print(" WorshipTools Planning - Service Discovery Diagnostic v3.1")
    print("=" * 72)
    print()
    print(f"Looking for upcoming Sunday: {target.strftime('%A, %B')} {target.day}, {target.year}")
    print()
    print("This diagnostic is READ ONLY.")
    print()

    PROFILE.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            context = None
            launch_errors = []

            for channel in ("chrome", "msedge"):
                try:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir=str(PROFILE),
                        channel=channel,
                        headless=False,
                        viewport=None,
                        args=["--start-maximized"],
                    )
                    add(f"Browser channel: {channel}")
                    break
                except Exception as exc:
                    launch_errors.append(
                        f"{channel}: {exc}"
                    )

            if context is None:
                add("ERROR: Could not launch Chrome or Edge.")
                add("\n".join(launch_errors))
                safe_write(lines)
                print("\n".join(lines))
                input("Press Enter to close...")
                return 1

            page = context.pages[0] if context.pages else context.new_page()

            try:
                page.goto(
                    PLANNING_URL,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
            except Exception as exc:
                add(f"Initial navigation warning: {exc}")

            page.wait_for_timeout(750)

            # Try to open Services automatically.
            for locator in (
                page.get_by_role(
                    "link",
                    name="Back to Services",
                    exact=True,
                ),
                page.get_by_role(
                    "link",
                    name="Services",
                    exact=True,
                ),
            ):
                try:
                    if locator.count():
                        locator.first.click()
                        page.wait_for_timeout(1200)
                        break
                except Exception:
                    pass

            print("A Planning browser window is open.")
            print()
            print("If the Services list is not visible, open Services manually.")
            print("Make sure the upcoming Sunday service is visible in the list.")
            print()
            input("Press Enter when the Services list is ready...")

            page.wait_for_timeout(700)

            add(f"URL: {page.url}")
            add(f"Page title: {page.title()}")
            add()

            try:
                body_text = page.locator("body").inner_text(
                    timeout=5000
                )
            except Exception as exc:
                body_text = f"[Could not read body text: {exc}]"

            add("VISIBLE PAGE TEXT")
            add("-" * 90)
            add(body_text)
            add()

            add("SERVICE-LIKE LINKS")
            add("-" * 90)

            links = page.locator(
                'a[href*="/service/"]'
            )

            link_count = min(
                links.count(),
                300
            )

            add(f"Count: {link_count}")

            for index in range(link_count):
                item = links.nth(index)

                try:
                    text = clean(
                        item.inner_text(timeout=300)
                    )
                except Exception:
                    text = ""

                try:
                    href = clean(
                        item.get_attribute("href")
                    )
                except Exception:
                    href = ""

                try:
                    outer = item.evaluate(
                        "(el) => el.outerHTML"
                    )
                except Exception:
                    outer = ""

                add(f"[{index:03d}] text={text!r}")
                add(f"       href={href!r}")
                add(f"       html={outer[:3000]}")

            add()

            # Windows-safe date variants. No %-d formatting.
            date_strings = [
                f"{target.strftime('%b')} {target.day}",
                f"{target.strftime('%B')} {target.day}",
                f"{target.month}/{target.day}/{target.year}",
                f"{target.month}/{target.day}",
                f"{target.strftime('%a')}, {target.strftime('%b')} {target.day}, {target.year}",
                f"{target.strftime('%A')}, {target.strftime('%B')} {target.day}, {target.year}",
            ]

            deduped = []
            for value in date_strings:
                value = clean(value)
                if value and value not in deduped:
                    deduped.append(value)

            add("UPCOMING-SUNDAY TEXT MATCHES")
            add("-" * 90)

            for date_text in deduped:
                try:
                    loc = page.get_by_text(
                        date_text,
                        exact=False
                    )

                    count = min(
                        loc.count(),
                        30
                    )

                    add(
                        f"{date_text!r}: {count} match(es)"
                    )

                    for index in range(count):
                        item = loc.nth(index)

                        try:
                            outer = item.evaluate(
                                "(el) => el.outerHTML"
                            )
                        except Exception:
                            outer = ""

                        add(f"--- match {index + 1} ---")
                        add(outer[:6000])

                        try:
                            ancestor = item.locator(
                                "xpath=ancestor::*[self::tr or self::li or self::article or contains(@class,'card') or contains(@class,'row')][1]"
                            )

                            if ancestor.count():
                                anc_html = ancestor.first.evaluate(
                                    "(el) => el.outerHTML"
                                )
                                add("--- nearest row/card ancestor ---")
                                add(anc_html[:12000])
                        except Exception:
                            pass

                except Exception as exc:
                    add(f"{date_text!r}: ERROR {exc}")

            try:
                page.screenshot(
                    path=str(SCREENSHOT),
                    full_page=True,
                )
            except Exception as exc:
                add(f"Screenshot warning: {exc}")

            # Write before waiting for the user to close anything.
            safe_write(lines)

            print()
            print("Diagnostic complete.")
            print()
            print("Created:")
            print(f"  {OUTPUT}")
            print(f"  {SCREENSHOT}")
            print()
            print("No service was changed.")
            print()
            print("Upload Planning_Service_Discovery.txt to ChatGPT.")
            print()

            input("Press Enter to close the diagnostic browser...")

            context.close()

        return 0

    except Exception:
        error_text = traceback.format_exc()

        add()
        add("FATAL ERROR")
        add("-" * 90)
        add(error_text)

        safe_write(lines)

        ERROR_LOG.write_text(
            error_text,
            encoding="utf-8",
        )

        print()
        print("The diagnostic hit an error, but a text file was still created:")
        print(f"  {OUTPUT}")
        print()
        print("Error log:")
        print(f"  {ERROR_LOG}")
        print()
        input("Press Enter to close...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
