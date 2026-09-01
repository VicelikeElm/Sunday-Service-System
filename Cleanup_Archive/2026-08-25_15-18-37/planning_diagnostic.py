import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path

BASE = Path(r"C:\Church\SermonAI")
PROFILE = BASE / "WorshipTools_Planning_Profile"
OUTPUT = BASE / "Planning_Diagnostic.txt"
SCREENSHOT = BASE / "Planning_Diagnostic.png"
PLAN = BASE / "sermon_plan.json"

PLANNING_URL = "https://planning.worshiptools.com"


def load_sermon_plan():
    if not PLAN.exists():
        return None

    try:
        return json.loads(
            PLAN.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return None


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print()
        print("Playwright is not installed.")
        print("Run Setup-Planning-Diagnostic.bat first.")
        print()
        input("Press Enter to close...")
        return 1

    plan = load_sermon_plan()

    print()
    print("=" * 68)
    print(" WorshipTools Planning - Read-Only Diagnostic")
    print("=" * 68)
    print()
    print("This does NOT change the WorshipTools service.")
    print()

    if plan:
        print("Current sermon plan:")
        print(f"  Title: {safe_text(plan.get('title'))}")
        print(f"  Scripture: {safe_text(plan.get('scripture'))}")
        print(f"  Points: {len(plan.get('points', []))}")
        print()

    PROFILE.mkdir(
        parents=True,
        exist_ok=True
    )

    with sync_playwright() as p:
        context = None

        # Prefer installed Google Chrome. If Playwright cannot find it,
        # fall back to installed Microsoft Edge.
        launch_errors = []

        for channel in ("chrome", "msedge"):
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE),
                    channel=channel,
                    headless=False,
                    viewport=None,
                    args=[
                        "--start-maximized",
                    ],
                )
                print(f"Opened Planning with {channel}.")
                break
            except Exception as exc:
                launch_errors.append(
                    f"{channel}: {exc}"
                )

        if context is None:
            print()
            print("Could not launch Chrome or Edge.")
            print()
            for item in launch_errors:
                print(item)
            print()
            input("Press Enter to close...")
            return 1

        pages = context.pages

        if pages:
            page = pages[0]
        else:
            page = context.new_page()

        try:
            page.goto(
                PLANNING_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )
        except Exception:
            pass

        print()
        print("A WorshipTools Planning browser window is open.")
        print()
        print("FIRST RUN:")
        print("  Sign in normally if WorshipTools asks you to.")
        print()
        print("THEN:")
        print("  1. Open the upcoming Sunday service.")
        print("  2. Open its Order tab.")
        print("  3. Make sure the Sermon section is visible.")
        print("  4. Come back to this window and press Enter.")
        print()
        input("Press Enter when the upcoming service Order page is ready...")

        try:
            page.wait_for_timeout(
                1000
            )
        except Exception:
            pass

        lines = []

        def add(value=""):
            lines.append(
                safe_text(
                    value
                )
            )

        add("WORSHIPTOOLS PLANNING DIAGNOSTIC")
        add("=" * 80)
        add(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
        add(f"URL: {page.url}")
        add(f"Page title: {page.title()}")
        add()

        if plan:
            add("SERMON PLAN")
            add("-" * 80)
            add(f"Title: {safe_text(plan.get('title'))}")
            add(f"Scripture: {safe_text(plan.get('scripture'))}")
            add("Points:")

            for index, point in enumerate(
                plan.get(
                    "points",
                    []
                ),
                start=1,
            ):
                add(
                    f"  {index}. {safe_text(point)}"
                )

            add()

        add("VISIBLE PAGE TEXT")
        add("-" * 80)

        try:
            body_text = page.locator("body").inner_text(
                timeout=5000
            )
        except Exception as exc:
            body_text = (
                f"[Could not read body text: {exc}]"
            )

        add(body_text)
        add()

        add("INTERACTIVE ELEMENTS")
        add("-" * 80)

        selectors = [
            ("BUTTON", "button"),
            ("LINK", "a"),
            ("INPUT", "input"),
            ("TEXTAREA", "textarea"),
            ("SELECT", "select"),
            ("ROLE-BUTTON", '[role="button"]'),
            ("ROLE-LINK", '[role="link"]'),
            ("ROLE-TEXTBOX", '[role="textbox"]'),
            ("ROLE-MENUITEM", '[role="menuitem"]'),
            ("ROLE-OPTION", '[role="option"]'),
        ]

        for label, selector in selectors:
            try:
                locator = page.locator(
                    selector
                )

                count = min(
                    locator.count(),
                    250
                )

                add(
                    f"[{label}] count={count}"
                )

                for index in range(
                    count
                ):
                    item = locator.nth(
                        index
                    )

                    try:
                        text = safe_text(
                            item.inner_text(
                                timeout=500
                            )
                        )
                    except Exception:
                        text = ""

                    try:
                        aria = safe_text(
                            item.get_attribute(
                                "aria-label"
                            )
                        )
                    except Exception:
                        aria = ""

                    try:
                        title = safe_text(
                            item.get_attribute(
                                "title"
                            )
                        )
                    except Exception:
                        title = ""

                    try:
                        placeholder = safe_text(
                            item.get_attribute(
                                "placeholder"
                            )
                        )
                    except Exception:
                        placeholder = ""

                    try:
                        tag = safe_text(
                            item.evaluate(
                                "(el) => el.tagName"
                            )
                        )
                    except Exception:
                        tag = ""

                    add(
                        f"  {index:03d} "
                        f"tag={tag!r} "
                        f"text={text[:180]!r} "
                        f"aria={aria[:120]!r} "
                        f"title={title[:120]!r} "
                        f"placeholder={placeholder[:120]!r}"
                    )

                add()

            except Exception as exc:
                add(
                    f"[{label}] ERROR: {exc}"
                )
                add()

        add("SERMON MATCHES")
        add("-" * 80)

        try:
            sermon_matches = page.get_by_text(
                "Sermon",
                exact=True
            )

            count = sermon_matches.count()
            add(
                f'Exact visible text "Sermon": {count} match(es)'
            )

            for index in range(
                min(
                    count,
                    20
                )
            ):
                item = sermon_matches.nth(
                    index
                )

                try:
                    outer = item.evaluate(
                        "(el) => el.outerHTML"
                    )
                except Exception as exc:
                    outer = (
                        f"[outerHTML unavailable: {exc}]"
                    )

                add(
                    f"--- Sermon match {index + 1} ---"
                )
                add(
                    outer[:6000]
                )

        except Exception as exc:
            add(
                f'Sermon text lookup failed: {exc}'
            )

        add()
        add("CURRENT SCRIPTURE MATCHES")
        add("-" * 80)

        scripture = ""

        if plan:
            scripture = safe_text(
                plan.get(
                    "scripture"
                )
            )

        if scripture:
            try:
                matches = page.get_by_text(
                    scripture,
                    exact=False
                )
                count = matches.count()

                add(
                    f'{scripture!r}: {count} match(es)'
                )

                for index in range(
                    min(
                        count,
                        20
                    )
                ):
                    item = matches.nth(
                        index
                    )

                    try:
                        outer = item.evaluate(
                            "(el) => el.outerHTML"
                        )
                    except Exception as exc:
                        outer = (
                            f"[outerHTML unavailable: {exc}]"
                        )

                    add(
                        f"--- Scripture match {index + 1} ---"
                    )
                    add(
                        outer[:6000]
                    )

            except Exception as exc:
                add(
                    f"Scripture lookup failed: {exc}"
                )

        OUTPUT.write_text(
            "\n".join(
                lines
            ),
            encoding="utf-8",
        )

        try:
            page.screenshot(
                path=str(
                    SCREENSHOT
                ),
                full_page=True,
            )
        except Exception:
            pass

        print()
        print("Diagnostic complete.")
        print()
        print("Created:")
        print(f"  {OUTPUT}")
        print(f"  {SCREENSHOT}")
        print()
        print("Nothing in the WorshipTools service was changed.")
        print()
        print("Send Planning_Diagnostic.txt back to ChatGPT.")
        print()

        input("Press Enter to close the diagnostic browser...")

        context.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
