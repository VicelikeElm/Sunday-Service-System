import re
import traceback
import subprocess
import os
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


def visible_elements(page, add):
    selectors = [
        ("BUTTON", "button"),
        ("LINK", "a"),
        ("INPUT", "input"),
        ("TEXTAREA", "textarea"),
        ("ROLE-BUTTON", '[role="button"]'),
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
                    f"text={text[:220]!r} "
                    f"aria={attrs['aria-label'][:180]!r} "
                    f"title={attrs['title'][:150]!r} "
                    f"placeholder={attrs['placeholder'][:150]!r} "
                    f"name={attrs['name'][:120]!r} "
                    f"type={attrs['type'][:80]!r} "
                    f"accept={attrs['accept'][:160]!r} "
                    f"href={attrs['href'][:220]!r}"
                )

            add()

        except Exception as exc:
            add(f"[{label}] ERROR: {exc}")
            add()


def try_open_upload(page):
    create_candidates = [
        page.get_by_role("button", name="Create", exact=True),
        page.get_by_text("Create", exact=True),
        page.locator('button[aria-label*="Create" i]'),
    ]

    create = None

    for locator in create_candidates:
        try:
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

    create.click()
    page.wait_for_timeout(500)

    upload_candidates = [
        page.get_by_text("Upload videos", exact=True),
        page.get_by_role("menuitem", name="Upload videos", exact=True),
        page.get_by_role("button", name="Upload videos", exact=True),
    ]

    upload = None

    for locator in upload_candidates:
        try:
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
        return False, "Upload videos item not found"

    upload.click()
    page.wait_for_timeout(700)
    return True, "Upload videos dialog opened"



def dedicated_profile_in_use():
    profile_text = str(PROFILE).replace("'", "''")

    ps = (
        "$profile = '" + profile_text + "'; "
        "$escaped = [Regex]::Escape($profile); "
        "$p = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
        "Where-Object { "
        "$_.CommandLine -and $_.CommandLine -match $escaped -and "
        "($_.Name -ieq 'chrome.exe' -or $_.Name -ieq 'msedge.exe') "
        "}; "
        "if ($p) { $p.ProcessId }"
    )

    try:
        cp = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                ps,
            ],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=(
                subprocess.CREATE_NO_WINDOW
                if os.name == "nt"
                else 0
            ),
        )

        return bool(cp.stdout.strip())

    except Exception:
        return False

def main():
    lines = []

    def add(value=""):
        lines.append(str(value))

    add("YOUTUBE STUDIO DIAGNOSTIC V1.2")
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
        safe_write(lines)
        print("Run Setup-YouTube-Studio-Diagnostic.bat first.")
        input("Press Enter to close...")
        return 1

    print()
    print("=" * 72)
    print(" YouTube Studio Diagnostic v1.2")
    print("=" * 72)
    print()
    print("IMPORTANT:")
    print("Use Open-YouTube-Studio-Normal-Login.bat FIRST.")
    print("Sign in there, switch to the church channel, and close it.")
    print()
    print("This diagnostic should NOT be used for Google sign-in.")
    print()

    PROFILE.mkdir(parents=True, exist_ok=True)

    if dedicated_profile_in_use():
        add("ERROR: Dedicated YouTube Studio profile is still open/in use.")
        add(
            "Run Close-Dedicated-YouTube-Studio-Browser.bat, "
            "then rerun this diagnostic."
        )
        safe_write(lines)

        print()
        print("The dedicated YouTube Studio profile is STILL OPEN.")
        print()
        print("Run:")
        print("  Close-Dedicated-YouTube-Studio-Browser.bat")
        print()
        print("Then run this diagnostic again.")
        print()
        input("Press Enter to close...")
        return 3

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
                add("ERROR: Could not launch browser.")
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
                add(f"Navigation warning: {exc}")

            page.wait_for_timeout(1200)

            add(f"URL: {page.url}")
            add(f"Page title: {page.title()}")
            add()

            try:
                body = page.locator("body").inner_text(timeout=6000)
            except Exception as exc:
                body = f"[Could not read body: {exc}]"

            add("VISIBLE TEXT")
            add("-" * 92)
            add(body)
            add()

            lower = body.lower()

            signed_in = (
                "couldn’t sign you in" not in lower
                and
                "couldn't sign you in" not in lower
                and
                "sign in" not in lower[:700]
            )

            channel_name_visible = EXPECTED_NAME.lower() in lower
            handle_visible = EXPECTED_HANDLE.lower() in lower

            add("IDENTITY CHECK")
            add("-" * 92)
            add(f"Appears signed in: {signed_in}")
            add(f"Expected channel name visible: {channel_name_visible}")
            add(f"Expected handle visible: {handle_visible}")
            add()

            if not signed_in:
                add(
                    "RESULT: NOT READY — run the NORMAL login helper, "
                    "sign in, close that browser, then rerun this diagnostic."
                )
                safe_write(lines)

                print()
                print("The dedicated profile is not signed into Studio.")
                print("Close this window and run:")
                print("  Open-YouTube-Studio-Normal-Login.bat")
                print()
                input("Press Enter to close...")

                context.close()
                return 2

            add("DASHBOARD CONTROLS")
            add("-" * 92)
            visible_elements(page, add)

            opened = False
            detail = ""

            try:
                opened, detail = try_open_upload(page)
            except Exception as exc:
                detail = f"Upload dialog open error: {exc}"

            add("UPLOAD DIALOG")
            add("-" * 92)
            add(f"Opened: {opened}")
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

                add("UPLOAD DIALOG CONTROLS")
                add("-" * 92)
                visible_elements(page, add)

                add("FILE INPUTS")
                add("-" * 92)

                inputs = page.locator('input[type="file"]')
                add(f"Count: {inputs.count()}")

                for i in range(min(inputs.count(), 20)):
                    item = inputs.nth(i)

                    try:
                        outer = item.evaluate(
                            "(el) => el.outerHTML"
                        )
                    except Exception:
                        outer = ""

                    add(f"[{i}] {outer[:6000]}")

                add()

            try:
                page.screenshot(
                    path=str(SCREENSHOT),
                    full_page=True,
                )
            except Exception as exc:
                add(f"Screenshot warning: {exc}")

            safe_write(lines)

            try:
                page.keyboard.press("Escape")
            except Exception:
                pass

            print()
            print("Diagnostic complete.")
            print()
            print(f"Created: {OUTPUT}")
            print()
            print("No video file was selected or uploaded.")
            print()
            print("Upload YouTube_Studio_Diagnostic.txt to ChatGPT.")
            print()

            input("Press Enter to close...")
            context.close()

        return 0

    except Exception:
        error_text = traceback.format_exc()
        add()
        add("FATAL ERROR")
        add(error_text)
        safe_write(lines)

        ERROR_LOG.write_text(
            error_text,
            encoding="utf-8"
        )

        print()
        print("Diagnostic error. Files were still written:")
        print(f"  {OUTPUT}")
        print(f"  {ERROR_LOG}")
        print()
        input("Press Enter to close...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
