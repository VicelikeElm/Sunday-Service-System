import argparse
import base64
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from sunday_common import load_config
from sync_sermon_plan_to_lower_thirds import sync_plan

BASE = Path(r"C:\Church\SermonAI")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


def normalize_text(value):
    value = html.unescape(
        value or ""
    )

    value = value.replace(
        "\xa0",
        " "
    )

    value = value.replace(
        "\r\n",
        "\n"
    ).replace(
        "\r",
        "\n"
    )

    value = re.sub(
        r"[ \t]+",
        " ",
        value
    )

    return value.strip()


def html_to_text(value):
    value = re.sub(
        r"(?is)<(script|style).*?>.*?</\1>",
        "",
        value
    )

    value = re.sub(
        r"(?i)<br\s*/?>",
        "\n",
        value
    )

    value = re.sub(
        r"(?i)</p\s*>",
        "\n",
        value
    )

    value = re.sub(
        r"(?s)<[^>]+>",
        "",
        value
    )

    return normalize_text(
        value
    )


def decode_part_data(data):
    if not data:
        return ""

    padding = "=" * (
        (-len(data)) % 4
    )

    raw = base64.urlsafe_b64decode(
        data + padding
    )

    return raw.decode(
        "utf-8",
        errors="replace"
    )


def extract_body(payload):
    plain_parts = []
    html_parts = []

    def walk(part):
        mime = (
            part.get(
                "mimeType",
                ""
            )
            or
            ""
        ).lower()

        body = part.get(
            "body",
            {}
        )

        data = body.get(
            "data"
        )

        if data:
            decoded = decode_part_data(
                data
            )

            if mime == "text/plain":
                plain_parts.append(
                    decoded
                )
            elif mime == "text/html":
                html_parts.append(
                    decoded
                )

        for child in part.get(
            "parts",
            []
        ):
            walk(
                child
            )

    walk(
        payload
    )

    if plain_parts:
        return normalize_text(
            "\n".join(
                plain_parts
            )
        )

    if html_parts:
        return html_to_text(
            "\n".join(
                html_parts
            )
        )

    return ""


def header_map(payload):
    result = {}

    for header in payload.get(
        "headers",
        []
    ):
        result[
            header.get(
                "name",
                ""
            ).lower()
        ] = header.get(
            "value",
            ""
        )

    return result


def clean_line(line):
    line = normalize_text(
        line
    )

    line = re.sub(
        r"^[\-\u2022]+\s*",
        "",
        line
    )

    # Gmail/HTML extraction can preserve emphasis markers as literal
    # asterisks, e.g. "*Self-Centered Reformation*" or
    # "*Saving**-Gracefilled Relationship*". These are formatting,
    # not part of the sermon wording, so strip them before saving the
    # official sermon plan or sending text to the lower thirds.
    line = line.replace(
        "*",
        ""
    )

    return line.strip()


def looks_like_signoff(line):
    lower = line.lower().strip()

    prefixes = [
        "thanks",
        "thank you",
        "gratefully",
        "sincerely",
        "sent from",
        "pastor phil",
        "philip lowther",
    ]

    return any(
        lower.startswith(
            item
        )
        for item in prefixes
    )


def parse_sermon_notes(body, subject, default_preacher):
    body = normalize_text(
        body
    )

    # Stop before quoted reply history.
    body = re.split(
        r"(?im)^\s*On .+wrote:\s*$",
        body,
        maxsplit=1
    )[0]

    raw_lines = [
        clean_line(
            line
        )
        for line in body.splitlines()
    ]

    lines = [
        line
        for line in raw_lines
        if line
    ]

    title = ""
    scripture = ""

    title_match = re.search(
        r"(?im)^\s*Title\s*:\s*(.+?)\s*$",
        body
    )

    if title_match:
        title = clean_line(
            title_match.group(1)
        )

    scripture_match = re.search(
        r"(?im)^\s*(?:Text|Scripture)\s*:\s*(.+?)\s*$",
        body
    )

    if scripture_match:
        scripture = clean_line(
            scripture_match.group(1)
        )

    # Some emails put "(Text: Mt 12:33-37)" on the title line.
    if not scripture:
        inline_text = re.search(
            r"(?i)\(\s*Text\s*:\s*([^)]+)\)",
            body
        )

        if inline_text:
            scripture = clean_line(
                inline_text.group(1)
            )

    if title:
        title = re.sub(
            r"\s*\(\s*Text\s*:[^)]+\)\s*$",
            "",
            title,
            flags=re.IGNORECASE
        ).strip()

    # Subject fallback.
    if not scripture:
        subject_ref = re.search(
            r"(?i)\b(?:Matt(?:hew)?|Mt)\s+\d{1,3}:\d{1,3}(?:-\d{1,3})?",
            subject
        )

        if subject_ref:
            scripture = clean_line(
                subject_ref.group(0)
            )

    if not title:
        quoted = re.search(
            r'["“](.+?)["”]',
            subject
        )

        if quoted:
            title = clean_line(
                quoted.group(1)
            )

    points = []

    outline_index = None

    for index, line in enumerate(
        lines
    ):
        if re.match(
            r"(?i)^outline\s*:",
            line
        ):
            outline_index = index
            after = re.sub(
                r"(?i)^outline\s*:\s*",
                "",
                line
            ).strip()

            if after:
                points.append(
                    after
                )

            break

    start_index = (
        outline_index + 1
        if outline_index is not None
        else 0
    )

    # Find title/text lines so that unlabelled outlines can start after them.
    if outline_index is None:
        labeled_positions = []

        for index, line in enumerate(
            lines
        ):
            if re.match(
                r"(?i)^(?:title|text|scripture)\s*:",
                line
            ):
                labeled_positions.append(
                    index
                )

        if labeled_positions:
            start_index = max(
                labeled_positions
            ) + 1

    for line in lines[
        start_index:
    ]:
        if looks_like_signoff(
            line
        ):
            break

        if re.match(
            r"(?i)^(?:title|text|scripture|outline)\s*:",
            line
        ):
            continue

        # Ignore greeting / explanatory prose before an outline.
        lower = line.lower()

        if (
            lower.startswith(
                "hello "
            )
            or
            "here are the sermon notes" in lower
            or
            "here are the notes" in lower
            or
            "below you will find" in lower
        ):
            continue

        numbered = re.match(
            r"^\s*\d+\s*[\.\)]\s*(.+)$",
            line
        )

        if numbered:
            candidate = clean_line(
                numbered.group(1)
            )
        else:
            candidate = clean_line(
                line
            )

        if not candidate:
            continue

        # Most outline lines are concise and end in punctuation.
        # Keep them even if unnumbered because several real sermon emails
        # use plain one-line points rather than "1./2./3." formatting.
        if candidate not in points:
            points.append(
                candidate
            )

    # Remove obvious trailing conversational lines that slipped through.
    cleaned_points = []

    for point in points:
        if looks_like_signoff(
            point
        ):
            break

        if len(
            point
        ) < 3:
            continue

        cleaned_points.append(
            point
        )

    return {
        "title": title,
        "scripture": scripture,
        "points": cleaned_points[:10],
        "preacher": default_preacher,
    }


def credentials(config, interactive):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise RuntimeError(
            "Google Gmail API packages are not installed. "
            "Run Setup-Gmail-Sermon-Import.bat."
        )

    token_path = Path(
        config[
            "gmail_token_file"
        ]
    )

    credentials_path = Path(
        config[
            "gmail_credentials_file"
        ]
    )

    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(
            str(
                token_path
            ),
            SCOPES
        )

    if (
        creds
        and
        creds.expired
        and
        creds.refresh_token
    ):
        try:
            creds.refresh(
                Request()
            )
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if not interactive:
            raise RuntimeError(
                "Gmail importer is not authorized yet."
            )

        if not credentials_path.exists():
            raise RuntimeError(
                f"Missing {credentials_path}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(
                credentials_path
            ),
            SCOPES
        )

        creds = flow.run_local_server(
            port=0
        )

        token_path.write_text(
            creds.to_json(),
            encoding="utf-8"
        )

    return creds


def upcoming_service_date(
    reference_date=None
):
    """
    Sunday today if today is Sunday; otherwise the next Sunday.

    This is the service date SSS is preparing for.
    """
    if reference_date is None:
        reference_date = datetime.now().astimezone().date()

    days_until_sunday = (
        6
        -
        reference_date.weekday()
    ) % 7

    return (
        reference_date
        +
        timedelta(
            days=days_until_sunday
        )
    )


def service_date_from_message_timestamp(
    internal_ms
):
    """
    Pastor normally sends sermon notes before the upcoming Sunday.
    Treat the first Sunday on/after the email's local received date as
    the service date for that sermon plan.
    """
    received = datetime.fromtimestamp(
        int(
            internal_ms
        )
        /
        1000
    ).astimezone()

    received_date = received.date()

    days_until_sunday = (
        6
        -
        received_date.weekday()
    ) % 7

    service_date = (
        received_date
        +
        timedelta(
            days=days_until_sunday
        )
    )

    return (
        received,
        service_date
    )


def import_latest(interactive=False, authorize_only=False):
    config = load_config()
    creds = credentials(
        config,
        interactive=interactive
    )

    if authorize_only:
        return None

    from googleapiclient.discovery import build

    service = build(
        "gmail",
        "v1",
        credentials=creds,
        cache_discovery=False
    )

    sender_config = config.get(
        "gmail_sermon_senders",
        config.get(
            "gmail_sermon_sender",
            ""
        )
    )

    senders = (
        sender_config
        if isinstance(sender_config, list)
        else [sender_config]
    )

    days = int(
        config.get(
            "gmail_sermon_lookback_days",
            14
        )
    )

    # Do not require the word "sermon" in the Gmail search.
    # Pastor's Friday subject may be only the Scripture/title, e.g.
    #   Matt 13:10-17 "The Purpose of Parables!"
    # Fetch recent direct messages from the pastor and let the structured
    # Title/Text/Outline parser decide which one is a sermon plan.
    # The pastor sometimes sends from more than one personal address, so
    # match any of the configured senders rather than exactly one.
    sender_query = " OR ".join(
        f"from:{address}"
        for address in senders
    )

    query = (
        f"({sender_query}) "
        f"newer_than:{days}d "
        "-in:spam -in:trash"
    )

    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=20
    ).execute()

    ids = result.get(
        "messages",
        []
    )

    if not ids:
        raise RuntimeError(
            "No recent sermon-notes email was found."
        )

    messages = []

    for item in ids:
        message = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="full"
        ).execute()

        headers = header_map(
            message.get(
                "payload",
                {}
            )
        )

        from_header = headers.get(
            "from",
            ""
        ).lower()

        if not any(
            address.lower() in from_header
            for address in senders
        ):
            continue

        subject = headers.get(
            "subject",
            ""
        )

        body = extract_body(
            message.get(
                "payload",
                {}
            )
        )

        internal_ms = int(
            message.get(
                "internalDate",
                "0"
            )
        )

        messages.append({
            "id": message["id"],
            "subject": subject,
            "body": body,
            "internal_ms": internal_ms,
        })

    if not messages:
        raise RuntimeError(
            "No direct sermon-notes message from the configured pastor was found."
        )

    messages.sort(
        key=lambda item: item[
            "internal_ms"
        ],
        reverse=True
    )

    chosen = None
    parsed = None

    target_service_date = upcoming_service_date()

    valid_other_dates = []

    for message in messages:
        candidate = parse_sermon_notes(
            message["body"],
            message["subject"],
            config.get(
                "default_preacher",
                ""
            )
        )

        if not (
            candidate["title"]
            and
            candidate["scripture"]
            and
            candidate["points"]
        ):
            continue

        (
            candidate_received_at,
            candidate_service_date,
        ) = service_date_from_message_timestamp(
            message[
                "internal_ms"
            ]
        )

        if (
            candidate_service_date
            ==
            target_service_date
        ):
            chosen = message
            parsed = candidate
            break

        valid_other_dates.append(
            {
                "subject": message.get(
                    "subject",
                    ""
                ),
                "service_date": (
                    candidate_service_date.isoformat()
                ),
            }
        )

    if chosen is None:
        if valid_other_dates:
            newest_other = valid_other_dates[
                0
            ]

            raise RuntimeError(
                (
                    "No sermon email was found for upcoming Sunday "
                    +
                    target_service_date.isoformat()
                    +
                    ". Newest parseable sermon email is for "
                    +
                    newest_other[
                        "service_date"
                    ]
                    +
                    ". Existing sermon_plan.json was NOT overwritten."
                )
            )

        raise RuntimeError(
            (
                "Recent pastor email was found, but no Title/Text/Outline "
                "sermon plan could be parsed for upcoming Sunday "
                +
                target_service_date.isoformat()
                +
                ". Existing sermon_plan.json was NOT overwritten."
            )
        )

    updated = datetime.now().isoformat(
        timespec="seconds"
    )

    email_received_at, service_date = (
        service_date_from_message_timestamp(
            chosen[
                "internal_ms"
            ]
        )
    )

    raw_for_id = json.dumps(
        {
            "message_id": chosen["id"],
            **parsed,
        },
        ensure_ascii=False,
        sort_keys=True
    ).encode("utf-8")

    plan_id = hashlib.sha256(
        raw_for_id
    ).hexdigest()[:16]

    plan = {
        "plan_id": plan_id,
        "updated": updated,
        "source": "Gmail sermon-notes email",
        "source_message_id": chosen["id"],
        "source_subject": chosen["subject"],
        "source_email_received_at": email_received_at.isoformat(
            timespec="seconds"
        ),
        "service_date": service_date.isoformat(),
        **parsed,
    }

    output = Path(
        config.get(
            "sermon_plan_file",
            str(BASE / "sermon_plan.json")
        )
    )

    temp = output.with_suffix(
        ".json.tmp"
    )

    temp.write_text(
        json.dumps(
            plan,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    temp.replace(
        output
    )

    # Keep the lower-thirds same-folder JS feed synchronized too.
    try:
        sync_plan()
    except Exception:
        # The sermon import itself still succeeded. Sunday Mode will retry
        # the local lower-third sync on startup.
        pass

    return plan


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--interactive",
        action="store_true"
    )

    parser.add_argument(
        "--authorize-only",
        action="store_true"
    )

    parser.add_argument(
        "--quiet",
        action="store_true"
    )

    args = parser.parse_args()

    try:
        plan = import_latest(
            interactive=args.interactive,
            authorize_only=args.authorize_only
        )

        if args.authorize_only:
            if not args.quiet:
                print(
                    "Gmail authorization complete."
                )
            return 0

        if not args.quiet:
            print()
            print(
                "SERMON PLAN IMPORTED"
            )
            print(
                "=" * 60
            )
            print(
                f"Title: {plan['title']}"
            )
            print(
                f"Scripture: {plan['scripture']}"
            )
            print(
                f"Service date: {plan.get('service_date', 'unknown')}"
            )
            print(
                f"Points: {len(plan['points'])}"
            )

            for index, point in enumerate(
                plan[
                    "points"
                ],
                start=1
            ):
                print(
                    f"  {index}. {point}"
                )

        return 0

    except Exception as exc:
        if not args.quiet:
            print(
                f"Gmail sermon import: {exc}"
            )

        return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
