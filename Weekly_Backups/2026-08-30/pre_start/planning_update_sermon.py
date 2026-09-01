import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sunday_common import load_config

BASE = Path(r"C:\Church\SermonAI")
PLAN_PATH = BASE / "sermon_plan.json"
STATUS_PATH = BASE / "planning_update_status.json"
LOG_PATH = BASE / "planning_update.log"

BOOK_ALIASES = {
    "gen": "Genesis",
    "genesis": "Genesis",
    "ex": "Exodus",
    "exo": "Exodus",
    "exodus": "Exodus",
    "lev": "Leviticus",
    "leviticus": "Leviticus",
    "num": "Numbers",
    "numbers": "Numbers",
    "deut": "Deuteronomy",
    "deuteronomy": "Deuteronomy",
    "josh": "Joshua",
    "joshua": "Joshua",
    "judg": "Judges",
    "judges": "Judges",
    "ruth": "Ruth",
    "1 sam": "1 Samuel",
    "1 samuel": "1 Samuel",
    "2 sam": "2 Samuel",
    "2 samuel": "2 Samuel",
    "1 kings": "1 Kings",
    "2 kings": "2 Kings",
    "1 chron": "1 Chronicles",
    "1 chronicles": "1 Chronicles",
    "2 chron": "2 Chronicles",
    "2 chronicles": "2 Chronicles",
    "ezra": "Ezra",
    "neh": "Nehemiah",
    "nehemiah": "Nehemiah",
    "esth": "Esther",
    "esther": "Esther",
    "job": "Job",
    "ps": "Psalm",
    "psalm": "Psalm",
    "psalms": "Psalm",
    "prov": "Proverbs",
    "proverbs": "Proverbs",
    "eccl": "Ecclesiastes",
    "ecclesiastes": "Ecclesiastes",
    "song": "Song of Solomon",
    "song of solomon": "Song of Solomon",
    "isa": "Isaiah",
    "isaiah": "Isaiah",
    "jer": "Jeremiah",
    "jeremiah": "Jeremiah",
    "lam": "Lamentations",
    "lamentations": "Lamentations",
    "ezek": "Ezekiel",
    "ezekiel": "Ezekiel",
    "dan": "Daniel",
    "daniel": "Daniel",
    "hos": "Hosea",
    "hosea": "Hosea",
    "joel": "Joel",
    "amos": "Amos",
    "obad": "Obadiah",
    "obadiah": "Obadiah",
    "jonah": "Jonah",
    "mic": "Micah",
    "micah": "Micah",
    "nah": "Nahum",
    "nahum": "Nahum",
    "hab": "Habakkuk",
    "habakkuk": "Habakkuk",
    "zeph": "Zephaniah",
    "zephaniah": "Zephaniah",
    "hag": "Haggai",
    "haggai": "Haggai",
    "zech": "Zechariah",
    "zechariah": "Zechariah",
    "mal": "Malachi",
    "malachi": "Malachi",
    "mt": "Matthew",
    "matt": "Matthew",
    "matthew": "Matthew",
    "mk": "Mark",
    "mark": "Mark",
    "lk": "Luke",
    "luke": "Luke",
    "jn": "John",
    "john": "John",
    "acts": "Acts",
    "rom": "Romans",
    "romans": "Romans",
    "1 cor": "1 Corinthians",
    "1 corinthians": "1 Corinthians",
    "2 cor": "2 Corinthians",
    "2 corinthians": "2 Corinthians",
    "gal": "Galatians",
    "galatians": "Galatians",
    "eph": "Ephesians",
    "ephesians": "Ephesians",
    "phil": "Philippians",
    "philippians": "Philippians",
    "col": "Colossians",
    "colossians": "Colossians",
    "1 thess": "1 Thessalonians",
    "1 thessalonians": "1 Thessalonians",
    "2 thess": "2 Thessalonians",
    "2 thessalonians": "2 Thessalonians",
    "1 tim": "1 Timothy",
    "1 timothy": "1 Timothy",
    "2 tim": "2 Timothy",
    "2 timothy": "2 Timothy",
    "titus": "Titus",
    "philem": "Philemon",
    "philemon": "Philemon",
    "heb": "Hebrews",
    "hebrews": "Hebrews",
    "jas": "James",
    "james": "James",
    "1 pet": "1 Peter",
    "1 peter": "1 Peter",
    "2 pet": "2 Peter",
    "2 peter": "2 Peter",
    "1 jn": "1 John",
    "1 john": "1 John",
    "2 jn": "2 John",
    "2 john": "2 John",
    "3 jn": "3 John",
    "3 john": "3 John",
    "jude": "Jude",
    "rev": "Revelation",
    "revelation": "Revelation",
}


def now_iso():
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def write_log(message):
    line = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"{message}"
    )

    try:
        with LOG_PATH.open(
            "a",
            encoding="utf-8"
        ) as handle:
            handle.write(
                line
                +
                "\n"
            )
    except Exception:
        pass


def write_status(
    status,
    message,
    *,
    ok=False,
    warning=False,
    service_date="",
    desired_scripture="",
    current_scripture="",
    service_url=""
):
    payload = {
        "updated": now_iso(),
        "status": status,
        "ok": bool(
            ok
        ),
        "warning": bool(
            warning
        ),
        "message": message,
        "service_date": service_date,
        "desired_scripture": desired_scripture,
        "current_scripture": current_scripture,
        "service_url": service_url,
    }

    temp = STATUS_PATH.with_suffix(
        ".json.tmp"
    )

    temp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    temp.replace(
        STATUS_PATH
    )

    write_log(
        f"{status}: {message}"
    )

    return payload


def clean_book(value):
    value = str(
        value
        or
        ""
    ).strip()

    value = value.replace(
        ".",
        ""
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    return value


def parse_scripture_reference(value):
    text = str(
        value
        or
        ""
    ).strip()

    text = text.replace(
        "–",
        "-"
    ).replace(
        "—",
        "-"
    )

    text = re.sub(
        r"\s*\([^)]+\)\s*$",
        "",
        text
    ).strip()

    match = re.match(
        r"^(?P<book>[1-3]?\s*[A-Za-z. ]+?)\s+"
        r"(?P<from_chapter>\d+):(?P<from_verse>\d+)"
        r"(?:-(?:(?P<to_chapter>\d+):)?(?P<to_verse>\d+))?$",
        text,
        flags=re.IGNORECASE
    )

    if not match:
        raise ValueError(
            "Planning automation currently supports one contiguous "
            f"Scripture range, e.g. Matthew 9:1-4. Got: {value}"
        )

    raw_book = clean_book(
        match.group(
            "book"
        )
    )

    alias_key = raw_book.lower()

    book = BOOK_ALIASES.get(
        alias_key
    )

    if not book:
        # Full UI book names also work directly.
        title_book = " ".join(
            part.capitalize()
            if not part.isdigit()
            else part
            for part in raw_book.split()
        )

        book = BOOK_ALIASES.get(
            title_book.lower(),
            title_book
        )

    from_chapter = int(
        match.group(
            "from_chapter"
        )
    )

    from_verse = int(
        match.group(
            "from_verse"
        )
    )

    to_chapter = int(
        match.group(
            "to_chapter"
        )
        or
        from_chapter
    )

    to_verse = int(
        match.group(
            "to_verse"
        )
        or
        from_verse
    )

    if (
        from_chapter < 1
        or
        from_verse < 1
        or
        to_chapter < 1
        or
        to_verse < 1
    ):
        raise ValueError(
            "Chapter and verse numbers must be positive."
        )

    display = (
        f"{book} {from_chapter}:{from_verse}"
    )

    if (
        to_chapter != from_chapter
        or
        to_verse != from_verse
    ):
        if to_chapter == from_chapter:
            display += (
                f"-{to_verse}"
            )
        else:
            display += (
                f"-{to_chapter}:{to_verse}"
            )

    return {
        "book": book,
        "from_chapter": from_chapter,
        "from_verse": from_verse,
        "to_chapter": to_chapter,
        "to_verse": to_verse,
        "display": display,
    }


def service_target_date():
    today = datetime.now().astimezone().date()

    if today.weekday() == 6:
        return today

    return (
        today
        +
        timedelta(
            days=(
                6
                -
                today.weekday()
            ) % 7
        )
    )


def parse_iso_date(value):
    try:
        return datetime.strptime(
            str(
                value
            ),
            "%Y-%m-%d"
        ).date()
    except Exception:
        return None


def target_date_texts(target):
    return [
        f"Sunday, {target.strftime('%B')} {target.day}, {target.year}",
        f"{target.strftime('%b')} {target.day}",
        f"{target.strftime('%B')} {target.day}",
    ]


def service_url_is_specific(url):
    return bool(
        re.search(
            r"/service/[0-9a-fA-F-]{20,}(?:$|[/?#])",
            url
        )
    )


def page_matches_target_service(
    page,
    target
):
    try:
        text = page.locator(
            "body"
        ).inner_text(
            timeout=4000
        )
    except Exception:
        return False

    long_date = (
        f"Sunday, {target.strftime('%B')} "
        f"{target.day}, {target.year}"
    )

    return (
        service_url_is_specific(
            page.url
        )
        and
        long_date.lower()
        in
        text.lower()
    )


def find_target_service_href(
    page,
    target
):
    """
    Locate the upcoming Sunday service on WorshipTools' Services page.
    We use several strategies because Planning is a Vue SPA and the
    clickable element can vary as WorshipTools updates its markup.
    """
    long_date = (
        f"Sunday, {target.strftime('%B')} "
        f"{target.day}, {target.year}"
    )

    short_date = (
        f"{target.strftime('%b')} "
        f"{target.day}"
    )

    # Strategy 1: inspect all links that look like a specific service.
    anchors = page.locator(
        'a[href*="/service/"]'
    )

    for index in range(
        min(
            anchors.count(),
            500
        )
    ):
        anchor = anchors.nth(
            index
        )

        try:
            href = (
                anchor.get_attribute(
                    "href"
                )
                or
                ""
            )
        except Exception:
            href = ""

        if not re.search(
            r"/service/[0-9a-fA-F-]{20,}",
            href
        ):
            continue

        try:
            text = anchor.inner_text(
                timeout=300
            )
        except Exception:
            text = ""

        try:
            parent_text = anchor.evaluate(
                """
                (el) => {
                    const card =
                        el.closest('.card, tr, li, article, [class*="service"]');
                    return card ? card.innerText : el.parentElement?.innerText || '';
                }
                """
            )
        except Exception:
            parent_text = ""

        combined = (
            str(
                text
            )
            +
            "\n"
            +
            str(
                parent_text
            )
        ).lower()

        if (
            long_date.lower()
            in
            combined
            or
            short_date.lower()
            in
            combined
        ):
            return href

    # Strategy 2: locate date text, then look for a clickable service
    # link in its ancestors / card.
    for date_text in target_date_texts(
        target
    ):
        locator = page.get_by_text(
            date_text,
            exact=False
        )

        for index in range(
            min(
                locator.count(),
                20
            )
        ):
            item = locator.nth(
                index
            )

            try:
                href = item.evaluate(
                    """
                    (el) => {
                        let node = el;
                        for (let i = 0; i < 8 && node; i++, node = node.parentElement) {
                            if (node.tagName === 'A') {
                                const href = node.getAttribute('href') || '';
                                if (/\\/service\\/[0-9a-fA-F-]{20,}/.test(href)) {
                                    return href;
                                }
                            }

                            const link = node.querySelector?.(
                                'a[href*="/service/"]'
                            );

                            if (link) {
                                const href = link.getAttribute('href') || '';
                                if (/\\/service\\/[0-9a-fA-F-]{20,}/.test(href)) {
                                    return href;
                                }
                            }
                        }

                        return '';
                    }
                    """
                )
            except Exception:
                href = ""

            if href:
                return href

    return ""


def find_sermon_scripture_row(
    page
):
    rows = page.locator(
        "tr.draggable-item"
    )

    sermon_indexes = []

    for index in range(
        rows.count()
    ):
        row = rows.nth(
            index
        )

        try:
            matches = row.get_by_text(
                "Sermon",
                exact=True
            ).count()
        except Exception:
            matches = 0

        if matches:
            try:
                text = row.inner_text(
                    timeout=400
                ).strip()
            except Exception:
                text = ""

            if re.search(
                r"\bSermon\b",
                text
            ):
                sermon_indexes.append(
                    index
                )

    if len(
        sermon_indexes
    ) != 1:
        raise RuntimeError(
            "Could not uniquely identify the Sermon header "
            f"(found {len(sermon_indexes)} candidates)."
        )

    sermon_index = sermon_indexes[
        0
    ]

    # The church's established pattern is:
    #   Sermon header
    #   [blank]
    #   Scripture
    #
    # Search a small window after the Sermon header and require exactly
    # one Bible Scripture item.
    candidates = []

    stop = min(
        rows.count(),
        sermon_index + 7
    )

    for index in range(
        sermon_index + 1,
        stop
    ):
        row = rows.nth(
            index
        )

        try:
            if row.locator(
                'img[alt="Bible Scripture"]'
            ).count():
                candidates.append(
                    row
                )
        except Exception:
            pass

    if len(
        candidates
    ) != 1:
        raise RuntimeError(
            "Expected exactly one Scripture item immediately under "
            f"Sermon; found {len(candidates)}."
        )

    return candidates[
        0
    ]


def scripture_heading(
    row
):
    try:
        return row.locator(
            "h3"
        ).first.inner_text(
            timeout=1500
        ).strip()
    except Exception:
        return row.inner_text(
            timeout=1500
        ).strip()


def normalize_reference_for_compare(
    value
):
    parsed = parse_scripture_reference(
        value
    )

    return (
        parsed[
            "book"
        ].lower(),
        parsed[
            "from_chapter"
        ],
        parsed[
            "from_verse"
        ],
        parsed[
            "to_chapter"
        ],
        parsed[
            "to_verse"
        ],
    )


def select_scripture_form(
    dialog,
    desired
):
    form = dialog.locator(
        "form"
    ).first

    selects = form.locator(
        "select"
    )

    count = selects.count()

    if count < 5:
        raise RuntimeError(
            f"Scripture editor exposed only {count} select(s); expected at least 5."
        )

    book_index = None

    for index in range(
        count
    ):
        select = selects.nth(
            index
        )

        try:
            options = [
                text.strip()
                for text in select.locator(
                    "option"
                ).all_text_contents()
            ]
        except Exception:
            options = []

        if (
            "Genesis"
            in
            options
            and
            "Revelation"
            in
            options
        ):
            book_index = index
            break

    if book_index is None:
        raise RuntimeError(
            "Could not identify the Book selector."
        )

    if (
        book_index
        +
        4
        >=
        count
    ):
        raise RuntimeError(
            "Scripture selector ordering changed unexpectedly."
        )

    book_select = selects.nth(
        book_index
    )

    from_chapter = selects.nth(
        book_index + 1
    )

    from_verse = selects.nth(
        book_index + 2
    )

    to_chapter = selects.nth(
        book_index + 3
    )

    to_verse = selects.nth(
        book_index + 4
    )

    book_select.select_option(
        label=desired[
            "book"
        ]
    )

    dialog.page.wait_for_timeout(
        250
    )

    from_chapter.select_option(
        label=str(
            desired[
                "from_chapter"
            ]
        )
    )

    dialog.page.wait_for_timeout(
        250
    )

    from_verse.select_option(
        label=str(
            desired[
                "from_verse"
            ]
        )
    )

    to_chapter.select_option(
        label=str(
            desired[
                "to_chapter"
            ]
        )
    )

    dialog.page.wait_for_timeout(
        250
    )

    to_verse.select_option(
        label=str(
            desired[
                "to_verse"
            ]
        )
    )


def run_update(
    *,
    show=False,
    dry_run=False
):
    config = load_config()

    if not PLAN_PATH.exists():
        return write_status(
            "SKIPPED",
            "No sermon_plan.json is available.",
            warning=True
        )

    plan = json.loads(
        PLAN_PATH.read_text(
            encoding="utf-8"
        )
    )

    desired_text = str(
        plan.get(
            "scripture",
            ""
        )
    ).strip()

    if not desired_text:
        return write_status(
            "SKIPPED",
            "The sermon plan has no Scripture reference.",
            warning=True
        )

    desired = parse_scripture_reference(
        desired_text
    )

    target = service_target_date()

    plan_date = parse_iso_date(
        plan.get(
            "service_date",
            ""
        )
    )

    if plan_date is None:
        return write_status(
            "SKIPPED",
            (
                "Sermon plan has no service_date. "
                "Run Import-Latest-Sermon-Email.bat once with the v17 importer."
            ),
            warning=True,
            service_date=target.isoformat(),
            desired_scripture=desired[
                "display"
            ],
        )

    if plan_date != target:
        return write_status(
            "SKIPPED",
            (
                f"Pastor email belongs to {plan_date.isoformat()}, "
                f"not the upcoming service {target.isoformat()}. "
                "Planning was left unchanged."
            ),
            warning=True,
            service_date=target.isoformat(),
            desired_scripture=desired[
                "display"
            ],
        )

    account_id = str(
        config.get(
            "planning_account_id",
            ""
        )
    ).strip()

    if not account_id:
        return write_status(
            "ERROR",
            "planning_account_id is missing from sunday_config.json.",
            warning=True,
            service_date=target.isoformat(),
            desired_scripture=desired[
                "display"
            ],
        )

    profile = Path(
        config.get(
            "planning_profile_folder",
            str(
                BASE
                /
                "WorshipTools_Planning_Profile"
            )
        )
    )

    profile.mkdir(
        parents=True,
        exist_ok=True
    )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return write_status(
            "ERROR",
            (
                "Playwright is not installed. "
                "Run Setup-Planning-Automation.bat."
            ),
            warning=True,
            service_date=target.isoformat(),
            desired_scripture=desired[
                "display"
            ],
        )

    services_url = (
        "https://planning.worshiptools.com"
        f"/app/account/{account_id}/service"
    )

    with sync_playwright() as p:
        context = None
        launch_errors = []

        for channel in (
            "chrome",
            "msedge"
        ):
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(
                        profile
                    ),
                    channel=channel,
                    headless=(
                        not show
                    ),
                    viewport=(
                        None
                        if show
                        else {
                            "width": 1440,
                            "height": 1000,
                        }
                    ),
                    args=(
                        [
                            "--start-maximized"
                        ]
                        if show
                        else []
                    ),
                )

                break

            except Exception as exc:
                launch_errors.append(
                    f"{channel}: {exc}"
                )

        if context is None:
            return write_status(
                "ERROR",
                (
                    "Could not launch the Planning browser profile. "
                    "Close any Planning diagnostic browser and retry. "
                    +
                    " | ".join(
                        launch_errors
                    )
                ),
                warning=True,
                service_date=target.isoformat(),
                desired_scripture=desired[
                    "display"
                ],
            )

        try:
            page = (
                context.pages[
                    0
                ]
                if context.pages
                else context.new_page()
            )

            # If the persistent profile happened to reopen on the correct
            # target service, use it. Otherwise go to the Services list.
            try:
                page.goto(
                    services_url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )
            except Exception:
                pass

            page.wait_for_timeout(
                1200
            )

            # Detect login/auth problem.
            try:
                body_text = page.locator(
                    "body"
                ).inner_text(
                    timeout=5000
                )
            except Exception:
                body_text = ""

            if (
                "sign in"
                in
                body_text.lower()
                and
                "order of service"
                not in
                body_text.lower()
            ):
                return write_status(
                    "ERROR",
                    (
                        "WorshipTools Planning login is required. "
                        "Run Planning-Update-Sermon-Show.bat and sign in."
                    ),
                    warning=True,
                    service_date=target.isoformat(),
                    desired_scripture=desired[
                        "display"
                    ],
                    service_url=page.url,
                )

            if not page_matches_target_service(
                page,
                target
            ):
                href = find_target_service_href(
                    page,
                    target
                )

                if not href:
                    # One more fallback: click a visible target date and
                    # see if the SPA navigates to the service.
                    navigated = False

                    for date_text in target_date_texts(
                        target
                    ):
                        loc = page.get_by_text(
                            date_text,
                            exact=False
                        )

                        for index in range(
                            min(
                                loc.count(),
                                10
                            )
                        ):
                            candidate = loc.nth(
                                index
                            )

                            try:
                                if not candidate.is_visible():
                                    continue

                                candidate.click()
                                page.wait_for_timeout(
                                    1000
                                )

                                if page_matches_target_service(
                                    page,
                                    target
                                ):
                                    navigated = True
                                    break
                            except Exception:
                                pass

                        if navigated:
                            break

                    if not navigated:
                        return write_status(
                            "ERROR",
                            (
                                "Could not automatically find the upcoming "
                                f"Sunday service ({target.isoformat()})."
                            ),
                            warning=True,
                            service_date=target.isoformat(),
                            desired_scripture=desired[
                                "display"
                            ],
                            service_url=page.url,
                        )

                else:
                    if href.startswith(
                        "/"
                    ):
                        href = (
                            "https://planning.worshiptools.com"
                            +
                            href
                        )

                    try:
                        page.goto(
                            href,
                            wait_until="domcontentloaded",
                            timeout=30000
                        )
                    except Exception:
                        pass

                    page.wait_for_timeout(
                        1200
                    )

            if not page_matches_target_service(
                page,
                target
            ):
                return write_status(
                    "ERROR",
                    (
                        "A Planning service opened, but its date does not "
                        f"match {target.isoformat()}. Nothing was changed."
                    ),
                    warning=True,
                    service_date=target.isoformat(),
                    desired_scripture=desired[
                        "display"
                    ],
                    service_url=page.url,
                )

            row = find_sermon_scripture_row(
                page
            )

            current_heading = scripture_heading(
                row
            )

            try:
                current_key = normalize_reference_for_compare(
                    current_heading
                )

                desired_key = normalize_reference_for_compare(
                    desired[
                        "display"
                    ]
                )

                already_correct = (
                    current_key
                    ==
                    desired_key
                )

            except Exception:
                already_correct = (
                    desired[
                        "display"
                    ].lower()
                    in
                    current_heading.lower()
                )

            if already_correct:
                return write_status(
                    "ALREADY_CORRECT",
                    (
                        "Planning sermon Scripture is already "
                        f"{desired['display']}."
                    ),
                    ok=True,
                    service_date=target.isoformat(),
                    desired_scripture=desired[
                        "display"
                    ],
                    current_scripture=current_heading,
                    service_url=page.url,
                )

            edit = row.get_by_role(
                "button",
                name="Edit",
                exact=True
            )

            if edit.count() != 1:
                raise RuntimeError(
                    "Could not uniquely identify the Scripture Edit button."
                )

            edit.click()

            dialog = page.get_by_role(
                "dialog"
            ).last

            dialog.wait_for(
                state="visible",
                timeout=10000
            )

            select_scripture_form(
                dialog,
                desired
            )

            if dry_run:
                cancel = dialog.get_by_role(
                    "button",
                    name="Cancel",
                    exact=True
                )

                if cancel.count():
                    cancel.click()

                return write_status(
                    "DRY_RUN",
                    (
                        f"Would change {current_heading} "
                        f"to {desired['display']}."
                    ),
                    ok=True,
                    service_date=target.isoformat(),
                    desired_scripture=desired[
                        "display"
                    ],
                    current_scripture=current_heading,
                    service_url=page.url,
                )

            save = dialog.get_by_role(
                "button",
                name="Save",
                exact=True
            )

            if save.count() != 1:
                raise RuntimeError(
                    "Could not uniquely identify the Save button."
                )

            save.click()

            try:
                dialog.wait_for(
                    state="hidden",
                    timeout=12000
                )
            except Exception:
                page.wait_for_timeout(
                    1500
                )

            page.wait_for_timeout(
                900
            )

            new_row = find_sermon_scripture_row(
                page
            )

            new_heading = scripture_heading(
                new_row
            )

            try:
                verified = (
                    normalize_reference_for_compare(
                        new_heading
                    )
                    ==
                    normalize_reference_for_compare(
                        desired[
                            "display"
                        ]
                    )
                )
            except Exception:
                verified = (
                    desired[
                        "display"
                    ].lower()
                    in
                    new_heading.lower()
                )

            if not verified:
                return write_status(
                    "ERROR",
                    (
                        "Save was attempted, but the service did not "
                        f"verify as {desired['display']}. "
                        f"It currently shows: {new_heading}"
                    ),
                    warning=True,
                    service_date=target.isoformat(),
                    desired_scripture=desired[
                        "display"
                    ],
                    current_scripture=new_heading,
                    service_url=page.url,
                )

            return write_status(
                "UPDATED",
                (
                    f"Planning sermon Scripture changed from "
                    f"{current_heading} to {new_heading}."
                ),
                ok=True,
                service_date=target.isoformat(),
                desired_scripture=desired[
                    "display"
                ],
                current_scripture=new_heading,
                service_url=page.url,
            )

        finally:
            try:
                context.close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--show",
        action="store_true",
        help="Show the Planning browser for troubleshooting."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Open/fill the editor but click Cancel instead of Save."
    )

    parser.add_argument(
        "--quiet",
        action="store_true"
    )

    args = parser.parse_args()

    try:
        result = run_update(
            show=args.show,
            dry_run=args.dry_run
        )

        if not args.quiet:
            print()
            print(
                "WORSHIPTOOLS PLANNING"
            )
            print(
                "=" * 60
            )
            print(
                result[
                    "status"
                ]
            )
            print(
                result[
                    "message"
                ]
            )
            print()

        return (
            0
            if (
                result.get(
                    "ok"
                )
                or
                result.get(
                    "warning"
                )
            )
            else 1
        )

    except Exception as exc:
        result = write_status(
            "ERROR",
            str(
                exc
            ),
            warning=True
        )

        if not args.quiet:
            print()
            print(
                "Planning update failed:"
            )
            print(
                result[
                    "message"
                ]
            )
            print()

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
