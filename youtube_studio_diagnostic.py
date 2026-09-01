import re
import traceback
from datetime import datetime
from pathlib import Path

BASE = Path(r"C:\Church\SermonAI")
PROFILE = BASE / "YouTube_Studio_Profile"
OUTPUT = BASE / "YouTube_Studio_Diagnostic.txt"
ERROR_LOG = BASE / "YouTube_Studio_Diagnostic_Error.txt"
SCREENSHOT = BASE / "YouTube_Studio_Diagnostic.png"

STUDIO_URL = "https://studio.youtube.com"
EXPECTED_HANDLE = "@baptistchurchofperry"
EXPECTED_NAME = "Baptist Church of Perry"


def clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def safe_write(lines):
    OUTPUT.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def collect_visible_elements(page, add):
    selectors = [
        ("BUTTON", "button"),
        ("LINK", "a"),
        ("INPUT", "input"),
        ("TEXTAREA", "textarea"),
        ("SELECT", "select"),
        ("ROLE-BUTTON", '[role="button"]'),
        ("ROLE-LINK", '[role="link"]'),
        ("ROLE-MENUITEM", '[role="menuitem"]'),
        ("ROLE-DIALOG", '[role="dialog"]'),
    ]

    for label, selector in selectors:
        try:
            loc = page.locator(selector)
            count = min(loc.count(), 350)
            add(f"[{label}] count={count}")

            for index in range(count):
                item = loc.nth(index)

                try:
                    if not item.is_visible():
                        continue
                except Exception:
                    continue

                try:
                    text = clean(item.inner_text(timeout=250))
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
                    "accept",
                    "href",
                ):
                    try:
                        attrs[attr] = clean(
                            item.get_attribute(attr)
                        )
                    except Exception:
                        attrs[attr] = ""

                try:
                    tag = clean(
                        item.evaluate("(el) => el.tagName")
                    )
                except Exception:
                    tag = ""

                add(
                    f"  {index:03d} "
                    f"tag={tag!r} "
                    f"text={text[:240]!r} "
                    f"aria={attrs['aria-label'][:180]!r} "
                    f"title={attrs['title'][:160]!r} "
                    f"placeholder={attrs['placeholder'][:160]!r} "
                    f"name={attrs['name'][:120]!r} "
                    f"type={attrs['type'][:80]!r} "
                    f"accept={attrs['accept'][:180]!r} "
                    f"href={attrs['href'][:220]!r}"
                )

            add()

        except Exception as exc:
            add(f"[{label}] ERROR: {exc}")
            add()


def try_click_account_menu(page):
    candidates = []

    # YouTube/Google changes aria labels periodically, so collect likely
    # profile/account/avatar controls and click only if there is one
    # strong visible candidate.
    for selector in (
        'button[aria-label*="Account" i]',
        'button[aria-label*="account" i]',
        'button[aria-label*="profile" i]',
        '[role="button"][aria-label*="Account" i]',
        '[role="button"][aria-label*="account" i]',
        'button[title*="Account" i]',
    ):
        try:
            loc = page.locator(selector)
            for i in range(min(loc.count(), 20)):
                item = loc.nth(i)
                if item.is_visible():
                    candidates.append(item)
        except Exception:
            pass

    if not candidates:
        return False

    try:
        candidates[0].click()
        page.wait_for_timeout(700)
        return True
    except Exception:
        return False


def try_open_upload_dialog(page):
    # First open Create.
    create = None

    for locator in (
        page.get_by_role("button", name="Create", exact=True),
        page.get_by_text("Create", exact=True),
        page.locator('button[aria-label*="Create" i]'),
    ):
        try:
            if locator.count():
                for i in range(min(locator.count(), 10)):
                    item = locator.nth(i)
                    if item.is_visible():
                        create = item
                        break
        except Exception:
            pass

        if create is not None:
            break

    if create is None:
        return False, "Create button not found"

    try:
        create.click()
        page.wait_for_timeout(600)
    except Exception as exc:
        return False, f"Create click failed: {exc}"

    # Then choose Upload videos.
    upload = None

    for locator in (
        page.get_by_text("Upload videos", exact=True),
        page.get_by_role("menuitem", name="Upload videos", exact=True),
        page.get_by_role("button", name="Upload videos", exact=True),
    ):
        try:
            if locator.count():
                for i in range(min(locator.count(), 10)):
                    item = locator.nth(i)
                    if item.is_visible():
                        upload = item
                        break
        except Exception:
            pass

        if upload is not None:
            break

    if upload is None:
        return False, "Upload videos menu item not found"

    try:
        upload.click()
        page.wait_for_timeout(900)
        return True, "Upload videos dialog opened"
    except Exception as exc:
        return False, f"Upload videos click failed: {exc}"


def main():
    lines = []

    def add(value=""):
        lines.append(str(value))

    add("YOUTUBE STUDIO DIAGNOSTIC V1")
    add("=" * 92)
    add(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    add(f"Expected handle: {EXPECTED_HANDLE}")
    add(f"Expected channel name: {EXPECTED_NAME}")
    add()

    safe_write(lines)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        add("ERROR: Playwright is not installed.")
        add("Run Setup-YouTube-Studio-Diagnostic.bat first.")
        safe_write(lines)
        print("\n".join(lines))
        input("Press Enter to close...")
        return 1

    print()
    print("=" * 72)
    print(" YouTube Studio - Read-Only Diagnostic")
    print("=" * 72)
    print()
    print("This diagnostic DOES NOT select a video file and DOES NOT upload.")
    print()
    print("Expected church channel:")
    print(f"  {EXPECTED_NAME}")
    print(f"  {EXPECTED_HANDLE}")
    print()

    PROFILE.mkdir(
        parents=True,
        exist_ok=True
    )

    try:
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
                    add(f"Browser channel: {channel}")
                    break
                except Exception as exc:
                    errors.append(f"{channel}: {exc}")

            if context is None:
                add("ERROR: Could not launch Chrome or Edge.")
                add("\n".join(errors))
                safe_write(lines)
                input("Press Enter to close...")
                return 1

            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )

            try:
                page.goto(
                    STUDIO_URL,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
            except Exception as exc:
                add(f"Initial navigation warning: {exc}")

            page.wait_for_timeout(1000)

            print("A dedicated YouTube Studio browser is open.")
            print()
            print("FIRST RUN:")
            print("  Sign in with YOUR Google account normally.")
            print()
            print("Then make sure YouTube Studio is switched to:")
            print(f"  {EXPECTED_NAME}")
            print(f"  {EXPECTED_HANDLE}")
            print()
            print("Do not upload anything.")
            print()
            input(
                "Press Enter when the church YouTube Studio dashboard is visible..."
            )

            page.wait_for_timeout(700)

            add(f"URL: {page.url}")
            add(f"Page title: {page.title()}")
            add()

            try:
                body = page.locator("body").inner_text(timeout=6000)
            except Exception as exc:
                body = f"[Could not read body: {exc}]"

            add("DASHBOARD VISIBLE TEXT")
            add("-" * 92)
            add(body)
            add()

            lower_body = body.lower()

            add("CHANNEL IDENTITY TEXT CHECK")
            add("-" * 92)
            add(
                f"Expected handle visible in dashboard text: "
                f"{EXPECTED_HANDLE.lower() in lower_body}"
            )
            add(
                f"Expected channel name visible in dashboard text: "
                f"{EXPECTED_NAME.lower() in lower_body}"
            )
            add()

            add("DASHBOARD INTERACTIVE ELEMENTS")
            add("-" * 92)
            collect_visible_elements(page, add)

            # Open account/profile menu if possible to capture channel identity.
            account_opened = try_click_account_menu(page)

            add("ACCOUNT / PROFILE MENU")
            add("-" * 92)
            add(f"Menu opened automatically: {account_opened}")

            if account_opened:
                try:
                    account_text = page.locator("body").inner_text(
                        timeout=5000
                    )
                except Exception as exc:
                    account_text = f"[Could not read menu text: {exc}]"

                add(account_text[-9000:])
                add()

                lower_account = account_text.lower()

                add(
                    f"Expected handle visible with account menu open: "
                    f"{EXPECTED_HANDLE.lower() in lower_account}"
                )
                add(
                    f"Expected channel name visible with account menu open: "
                    f"{EXPECTED_NAME.lower() in lower_account}"
                )
                add()

                collect_visible_elements(page, add)

                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(300)
                except Exception:
                    pass

            # Open Create -> Upload videos but never select a file.
            opened, detail = try_open_upload_dialog(page)

            add("CREATE / UPLOAD VIDEOS DIALOG")
            add("-" * 92)
            add(f"Automatic open result: {opened}")
            add(f"Detail: {detail}")
            add()

            if opened:
                try:
                    upload_text = page.locator("body").inner_text(
                        timeout=5000
                    )
                except Exception as exc:
                    upload_text = f"[Could not read upload dialog: {exc}]"

                add(upload_text[-10000:])
                add()

                add("UPLOAD-DIALOG INTERACTIVE ELEMENTS")
                add("-" * 92)
                collect_visible_elements(page, add)

                # Explicitly capture file inputs, including hidden ones.
                add("FILE INPUTS")
                add("-" * 92)

                try:
                    inputs = page.locator('input[type="file"]')
                    add(f"Count: {inputs.count()}")

                    for i in range(min(inputs.count(), 20)):
                        item = inputs.nth(i)

                        attrs = {}
                        for attr in (
                            "accept",
                            "name",
                            "id",
                            "multiple",
                            "aria-label",
                        ):
                            try:
                                attrs[attr] = clean(
                                    item.get_attribute(attr)
                                )
                            except Exception:
                                attrs[attr] = ""

                        try:
                            outer = item.evaluate(
                                "(el) => el.outerHTML"
                            )
                        except Exception:
                            outer = ""

                        add(
                            f"[{i}] accept={attrs['accept']!r} "
                            f"name={attrs['name']!r} "
                            f"id={attrs['id']!r} "
                            f"multiple={attrs['multiple']!r} "
                            f"aria={attrs['aria-label']!r}"
                        )
                        add(outer[:5000])

                except Exception as exc:
                    add(f"File input inspection error: {exc}")

                add()

            try:
                page.screenshot(
                    path=str(SCREENSHOT),
                    full_page=True,
                )
            except Exception as exc:
                add(f"Screenshot warning: {exc}")

            safe_write(lines)

            # Close upload dialog without choosing a file.
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(250)
            except Exception:
                pass

            print()
            print("Diagnostic complete.")
            print()
            print("Created:")
            print(f"  {OUTPUT}")
            print(f"  {SCREENSHOT}")
            print()
            print("No video file was selected or uploaded.")
            print()
            print("Upload YouTube_Studio_Diagnostic.txt to ChatGPT.")
            print()
            input("Press Enter to close the diagnostic browser...")

            context.close()

        return 0

    except Exception:
        error_text = traceback.format_exc()

        add()
        add("FATAL ERROR")
        add("-" * 92)
        add(error_text)
        safe_write(lines)

        ERROR_LOG.write_text(
            error_text,
            encoding="utf-8"
        )

        print()
        print("The diagnostic hit an error, but output files were still written.")
        print(f"  {OUTPUT}")
        print(f"  {ERROR_LOG}")
        print()
        input("Press Enter to close...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
