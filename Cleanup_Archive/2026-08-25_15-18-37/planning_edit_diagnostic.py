import json
import re
from datetime import datetime
from pathlib import Path

BASE = Path(r"C:\Church\SermonAI")
PROFILE = BASE / "WorshipTools_Planning_Profile"
OUTPUT = BASE / "Planning_Edit_Diagnostic.txt"
SCREENSHOT = BASE / "Planning_Edit_Diagnostic.png"
PLAN = BASE / "sermon_plan.json"

PLANNING_URL = "https://planning.worshiptools.com"

SCRIPTURE_RE = re.compile(
    r"\b(?:Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|"
    r"1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|Ezra|Nehemiah|"
    r"Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song of Solomon|Isaiah|Jeremiah|"
    r"Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|"
    r"Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|"
    r"Romans|1 Corinthians|2 Corinthians|Galatians|Ephesians|Philippians|"
    r"Colossians|1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|Titus|"
    r"Philemon|Hebrews|James|1 Peter|2 Peter|1 John|2 John|3 John|Jude|"
    r"Revelation)\s+\d+:\d+(?:-\d+)?(?:\s*\([A-Za-z0-9]+\))?\b",
    re.IGNORECASE,
)


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def load_plan():
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


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed.")
        print("Run Setup-Planning-Diagnostic.bat from v1 first.")
        input("Press Enter to close...")
        return 1

    plan = load_plan()

    print()
    print("=" * 72)
    print(" WorshipTools Planning - Scripture Edit Diagnostic v2")
    print("=" * 72)
    print()
    print("This diagnostic may OPEN the Scripture Edit dialog.")
    print("It will NOT click Save or make a service change.")
    print()

    PROFILE.mkdir(
        parents=True,
        exist_ok=True
    )

    with sync_playwright() as p:
        context = None
        errors = []

        for channel in ("chrome", "msedge"):
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE),
                    channel=channel,
                    headless=False,
                    viewport=None,
                    args=["--start-maximized"],
                )
                break
            except Exception as exc:
                errors.append(
                    f"{channel}: {exc}"
                )

        if context is None:
            print("Could not launch Chrome/Edge.")
            print("\n".join(errors))
            input("Press Enter to close...")
            return 1

        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto(
                PLANNING_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )
        except Exception:
            pass

        print("Open the upcoming Sunday service and its Order tab.")
        print("Make sure the Sermon section and its Scripture item are visible.")
        print()
        input("Press Enter when the Order page is ready...")

        page.wait_for_timeout(750)

        body = page.locator("body").inner_text(
            timeout=5000
        )

        candidates = []
        seen = set()

        for match in SCRIPTURE_RE.finditer(
            body
        ):
            value = re.sub(
                r"\s+",
                " ",
                match.group(0)
            ).strip()

            key = value.lower()

            if key not in seen:
                seen.add(
                    key
                )
                candidates.append(
                    value
                )

        print()
        print("Scripture-looking items found:")

        if not candidates:
            print("  None")
            print()
            input("Press Enter to close...")
            context.close()
            return 1

        for i, value in enumerate(
            candidates,
            start=1,
        ):
            print(
                f"  {i}. {value}"
            )

        choice = 1

        if len(candidates) > 1:
            print()
            while True:
                raw = input(
                    "Enter the number for the Scripture item under Sermon: "
                ).strip()

                try:
                    choice = int(
                        raw
                    )

                    if 1 <= choice <= len(
                        candidates
                    ):
                        break
                except Exception:
                    pass

                print(
                    "Please enter one of the listed numbers."
                )

        target_text = candidates[
            choice - 1
        ]

        lines = []

        def add(value=""):
            lines.append(
                clean(
                    value
                )
            )

        add("WORSHIPTOOLS PLANNING EDIT DIAGNOSTIC V2")
        add("=" * 90)
        add(
            f"Generated: {datetime.now().isoformat(timespec='seconds')}"
        )
        add(
            f"URL: {page.url}"
        )
        add(
            f"Page title: {page.title()}"
        )
        add()

        if plan:
            add("CURRENT SERMON PLAN")
            add("-" * 90)
            add(
                f"Title: {clean(plan.get('title'))}"
            )
            add(
                f"Scripture: {clean(plan.get('scripture'))}"
            )
            add()

        add("SELECTED CURRENT PLANNING SCRIPTURE")
        add("-" * 90)
        add(
            target_text
        )
        add()

        locator = page.get_by_text(
            target_text,
            exact=True
        )

        count = locator.count()

        add(
            f"Exact DOM text matches: {count}"
        )

        if count == 0:
            # Try text without translation suffix if needed.
            base_ref = re.sub(
                r"\s*\([^)]+\)\s*$",
                "",
                target_text
            ).strip()

            locator = page.get_by_text(
                base_ref,
                exact=False
            )

            count = locator.count()

            add(
                f"Fallback DOM text matches: {count}"
            )

        if count == 0:
            add(
                "Could not locate the selected Scripture text in the DOM."
            )
            OUTPUT.write_text(
                "\n".join(lines),
                encoding="utf-8",
            )
            context.close()
            return 1

        target = locator.first

        try:
            row = target.locator(
                "xpath=ancestor::*[.//button[normalize-space()='Edit']][1]"
            )

            row_html = row.evaluate(
                "(el) => el.outerHTML"
            )

            add()
            add("SCRIPTURE SERVICE-ITEM ROW HTML")
            add("-" * 90)
            add(
                row_html[:20000]
            )
            add()

        except Exception as exc:
            add(
                f"Could not identify Scripture row: {exc}"
            )
            OUTPUT.write_text(
                "\n".join(lines),
                encoding="utf-8",
            )
            context.close()
            return 1

        edit_button = row.get_by_role(
            "button",
            name="Edit",
            exact=True,
        )

        if edit_button.count() == 0:
            add(
                "No Edit button was found inside the Scripture row."
            )
            OUTPUT.write_text(
                "\n".join(lines),
                encoding="utf-8",
            )
            context.close()
            return 1

        add("Opening Scripture Edit UI...")
        add()

        edit_button.first.click()
        page.wait_for_timeout(
            800
        )

        add("PAGE TEXT AFTER CLICKING EDIT")
        add("-" * 90)

        try:
            after_text = page.locator(
                "body"
            ).inner_text(
                timeout=5000
            )

            add(
                after_text[-12000:]
            )
        except Exception as exc:
            add(
                f"Could not read page text: {exc}"
            )

        add()
        add("VISIBLE DIALOGS / FORMS")
        add("-" * 90)

        selectors = [
            ("DIALOG", '[role="dialog"]'),
            ("FORM", "form"),
            ("INPUT", "input"),
            ("TEXTAREA", "textarea"),
            ("SELECT", "select"),
            ("BUTTON", "button"),
            ("ROLE-TEXTBOX", '[role="textbox"]'),
            ("ROLE-COMBOBOX", '[role="combobox"]'),
            ("ROLE-OPTION", '[role="option"]'),
        ]

        for label, selector in selectors:
            try:
                loc = page.locator(
                    selector
                )

                count = min(
                    loc.count(),
                    200
                )

                add(
                    f"[{label}] count={count}"
                )

                for index in range(
                    count
                ):
                    item = loc.nth(
                        index
                    )

                    try:
                        visible = item.is_visible()
                    except Exception:
                        visible = False

                    if not visible:
                        continue

                    try:
                        text = clean(
                            item.inner_text(
                                timeout=300
                            )
                        )
                    except Exception:
                        text = ""

                    attrs = {}

                    for attr in (
                        "aria-label",
                        "title",
                        "placeholder",
                        "name",
                        "type",
                        "value",
                    ):
                        try:
                            attrs[attr] = clean(
                                item.get_attribute(
                                    attr
                                )
                            )
                        except Exception:
                            attrs[attr] = ""

                    try:
                        tag = clean(
                            item.evaluate(
                                "(el) => el.tagName"
                            )
                        )
                    except Exception:
                        tag = ""

                    add(
                        f"  {index:03d} "
                        f"tag={tag!r} "
                        f"text={text[:240]!r} "
                        f"aria={attrs['aria-label'][:160]!r} "
                        f"title={attrs['title'][:160]!r} "
                        f"placeholder={attrs['placeholder'][:160]!r} "
                        f"name={attrs['name'][:120]!r} "
                        f"type={attrs['type'][:80]!r} "
                        f"value={attrs['value'][:240]!r}"
                    )

                add()

            except Exception as exc:
                add(
                    f"[{label}] ERROR: {exc}"
                )
                add()

        try:
            page.screenshot(
                path=str(
                    SCREENSHOT
                ),
                full_page=True,
            )
        except Exception:
            pass

        OUTPUT.write_text(
            "\n".join(
                lines
            ),
            encoding="utf-8",
        )

        # Do not click any Save button. Escape is a safe best-effort close.
        try:
            page.keyboard.press(
                "Escape"
            )
            page.wait_for_timeout(
                300
            )
        except Exception:
            pass

        print()
        print("Diagnostic complete.")
        print()
        print("Created:")
        print(
            f"  {OUTPUT}"
        )
        print(
            f"  {SCREENSHOT}"
        )
        print()
        print("No Save button was clicked.")
        print()
        print("Upload Planning_Edit_Diagnostic.txt to ChatGPT.")
        print()

        input(
            "Press Enter to close the diagnostic browser..."
        )

        context.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
