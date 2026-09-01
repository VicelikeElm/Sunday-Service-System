import base64
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from sss_scripture_reading import (
    send_midi_note,
)


BASE = Path(r"C:\Church\SermonAI")
STATE_DIR = BASE / "State"
CACHE_FILE = STATE_DIR / "presenter_scripture_position.json"
OCR_SCRIPT = BASE / "presenter_windows_ocr.ps1"


def _clean(value):
    return " ".join(
        str(value or "").split()
    )


def _normalize(value):
    value = (
        str(value or "")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .lower()
    )

    value = re.sub(
        r"[^a-z0-9:\-\s]",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def _reference_first_verse(reference):
    reference = _clean(reference)

    match = re.match(
        r"^(?P<book>(?:[1-3]\s*)?[A-Za-z]+(?:\s+[A-Za-z]+)*)\s+"
        r"(?P<chapter>\d+)\s*:\s*(?P<verse>\d+)",
        reference,
        flags=re.IGNORECASE,
    )

    if not match:
        return reference

    return (
        _clean(
            match.group("book")
        )
        +
        " "
        +
        str(
            int(
                match.group("chapter")
            )
        )
        +
        ":"
        +
        str(
            int(
                match.group("verse")
            )
        )
    )


def _reference_matches(
    ocr_text,
    reference
):
    haystack = _normalize(
        ocr_text
    )

    if not haystack:
        return False

    first = _normalize(
        _reference_first_verse(
            reference
        )
    )

    full = _normalize(
        reference
    )

    compact_haystack = re.sub(
        r"\s+",
        "",
        haystack,
    )

    compact_first = re.sub(
        r"\s+",
        "",
        first,
    )

    compact_full = re.sub(
        r"\s+",
        "",
        full,
    )

    return (
        bool(
            compact_first
        )
        and
        compact_first
        in
        compact_haystack
    ) or (
        bool(
            compact_full
        )
        and
        compact_full
        in
        compact_haystack
    )


def _atomic_json(
    path,
    payload
):
    path = Path(
        path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_suffix(
        path.suffix
        +
        ".tmp"
    )

    temp.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    os.replace(
        temp,
        path,
    )


def _read_json(
    path,
    default=None
):
    try:
        return json.loads(
            Path(
                path
            ).read_text(
                encoding="utf-8-sig"
            )
        )
    except Exception:
        return (
            {}
            if default is None
            else default
        )


def _response_image_data(
    response
):
    if response is None:
        return ""

    for attr in (
        "image_data",
        "imageData",
    ):
        value = getattr(
            response,
            attr,
            None,
        )

        if value:
            return str(
                value
            )

    if isinstance(
        response,
        dict
    ):
        for key in (
            "imageData",
            "image_data",
        ):
            if response.get(
                key
            ):
                return str(
                    response[
                        key
                    ]
                )

        data = response.get(
            "responseData",
            {}
        )

        if isinstance(
            data,
            dict
        ):
            for key in (
                "imageData",
                "image_data",
            ):
                if data.get(
                    key
                ):
                    return str(
                        data[
                            key
                        ]
                    )

    return ""


def _obs_source_names(
    client
):
    names = []

    try:
        response = client.get_scene_list()

        for scene in getattr(
            response,
            "scenes",
            []
        ) or []:
            if isinstance(
                scene,
                dict
            ):
                name = scene.get(
                    "sceneName",
                    ""
                )
            else:
                name = getattr(
                    scene,
                    "scene_name",
                    "",
                )

            if name:
                names.append(
                    str(
                        name
                    )
                )
    except Exception:
        pass

    try:
        response = client.get_input_list()

        for item in getattr(
            response,
            "inputs",
            []
        ) or []:
            if isinstance(
                item,
                dict
            ):
                name = item.get(
                    "inputName",
                    ""
                )
            else:
                name = getattr(
                    item,
                    "input_name",
                    "",
                )

            if name:
                names.append(
                    str(
                        name
                    )
                )
    except Exception:
        pass

    return names


def _resolve_obs_source(
    client,
    candidates
):
    available = _obs_source_names(
        client
    )

    by_lower = {
        name.lower(): name
        for name in available
    }

    for candidate in candidates:
        candidate = _clean(
            candidate
        )

        if not candidate:
            continue

        actual = by_lower.get(
            candidate.lower()
        )

        if actual:
            return actual

    # GetSourceScreenshot can sometimes resolve sources omitted from
    # GetInputList/GetSceneList, so allow the first configured name.
    for candidate in candidates:
        candidate = _clean(
            candidate
        )

        if candidate:
            return candidate

    return ""


def _capture_source_png(
    client,
    source_name,
    output_path,
    *,
    width=960,
    height=540
):
    image_data = ""

    try:
        response = client.get_source_screenshot(
            source_name,
            "png",
            int(
                width
            ),
            int(
                height
            ),
            -1,
        )

        image_data = _response_image_data(
            response
        )

    except Exception:
        try:
            response = client.send(
                "GetSourceScreenshot",
                {
                    "sourceName": source_name,
                    "imageFormat": "png",
                    "imageWidth": int(
                        width
                    ),
                    "imageHeight": int(
                        height
                    ),
                    "imageCompressionQuality": -1,
                },
                raw=True,
            )

            image_data = _response_image_data(
                response
            )

        except Exception as exc:
            raise RuntimeError(
                (
                    "OBS could not capture "
                    +
                    source_name
                    +
                    ": "
                    +
                    str(
                        exc
                    )
                )
            ) from exc

    if not image_data:
        raise RuntimeError(
            (
                "OBS returned no screenshot for "
                +
                source_name
                +
                "."
            )
        )

    if "," in image_data:
        image_data = image_data.split(
            ",",
            1
        )[1]

    try:
        png = base64.b64decode(
            image_data
        )
    except Exception as exc:
        raise RuntimeError(
            "OBS screenshot data could not be decoded."
        ) from exc

    output_path = Path(
        output_path
    )

    output_path.write_bytes(
        png
    )

    return output_path


def _ocr_batch(
    items,
    *,
    timeout=45
):
    if not OCR_SCRIPT.exists():
        raise RuntimeError(
            (
                "Windows OCR helper is missing: "
                +
                str(
                    OCR_SCRIPT
                )
            )
        )

    manifest_path = (
        STATE_DIR
        /
        "presenter_visual_ocr_manifest.json"
    )

    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_path.write_text(
        json.dumps(
            items,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    creationflags = (
        subprocess.CREATE_NO_WINDOW
        if os.name == "nt"
        else 0
    )

    try:
        cp = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(
                    OCR_SCRIPT
                ),
                "-ManifestPath",
                str(
                    manifest_path
                ),
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=float(
                timeout
            ),
            creationflags=creationflags,
        )
    except Exception as exc:
        raise RuntimeError(
            (
                "Windows OCR could not run: "
                +
                str(
                    exc
                )
            )
        ) from exc

    output = (
        cp.stdout
        or
        ""
    ).strip()

    payload = None

    for line in reversed(
        output.splitlines()
    ):
        line = line.strip()

        if not (
            line.startswith(
                "["
            )
            or
            line.startswith(
                "{"
            )
        ):
            continue

        try:
            payload = json.loads(
                line
            )
            break
        except Exception:
            continue

    if isinstance(
        payload,
        dict
    ):
        if not payload.get(
            "success",
            False
        ):
            raise RuntimeError(
                str(
                    payload.get(
                        "error",
                        "Windows OCR failed."
                    )
                )
            )

        payload = [
            payload
        ]

    if not isinstance(
        payload,
        list
    ):
        detail = (
            output
            or
            (
                cp.stderr
                or
                ""
            ).strip()
            or
            (
                "Windows OCR returned no results."
            )
        )

        raise RuntimeError(
            detail
        )

    return payload


def _send_presenter_index(
    *,
    port_name,
    channel,
    command_note,
    index
):
    return send_midi_note(
        port_name=port_name,
        channel=channel,
        note=int(
            command_note
        ),
        velocity=max(
            0,
            min(
                127,
                int(
                    index
                )
            )
        ),
        hold_seconds=0.04,
    )


def _select_item_first_slide(
    *,
    port_name,
    channel,
    item_index,
    service_item_note,
    change_slide_note,
    settle_seconds
):
    _send_presenter_index(
        port_name=port_name,
        channel=channel,
        command_note=service_item_note,
        index=item_index,
    )

    time.sleep(
        max(
            0.08,
            float(
                settle_seconds
            )
        )
    )

    # Presenter MIDI setting:
    #   Change Slide = Note 4
    #   velocity = zero-based slide index
    _send_presenter_index(
        port_name=port_name,
        channel=channel,
        command_note=change_slide_note,
        index=0,
    )

    time.sleep(
        max(
            0.08,
            float(
                settle_seconds
            )
        )
    )


def visual_system_ready(
    config,
    client=None
):
    if not OCR_SCRIPT.exists():
        return (
            False,
            "Windows OCR helper missing",
        )

    preferred = _clean(
        config.get(
            "presenter_visual_source",
            "webcam TP"
        )
    )

    fallback = _clean(
        config.get(
            "presenter_visual_fallback_source",
            "Cam Link Pro HDMI4"
        )
    )

    if client is None:
        return (
            True,
            (
                "visual verify configured: "
                +
                preferred
            ),
        )

    source = _resolve_obs_source(
        client,
        [
            preferred,
            fallback,
        ],
    )

    if not source:
        return (
            False,
            "Presenter visual source not found in OBS",
        )

    return (
        True,
        source,
    )


def locate_scripture_visually(
    client,
    config,
    *,
    reference,
    plan_id="",
    port_name="Presenter",
    channel=10
):
    """
    Locate the weekly Scripture by controlling Presenter through its
    own Change Service Item / Change Slide MIDI commands and verifying
    the actual OBS-rendered output with Windows OCR.

    The default verification source is the OBS scene "webcam TP".
    """
    reference = _clean(
        reference
    )

    if not reference:
        raise RuntimeError(
            "Scripture reference is blank."
        )

    preferred = _clean(
        config.get(
            "presenter_visual_source",
            "webcam TP"
        )
    )

    fallback = _clean(
        config.get(
            "presenter_visual_fallback_source",
            "Cam Link Pro HDMI4"
        )
    )

    source_name = _resolve_obs_source(
        client,
        [
            preferred,
            fallback,
        ],
    )

    if not source_name:
        raise RuntimeError(
            (
                "OBS could not find the Presenter verification view. "
                "Expected webcam TP or Cam Link Pro HDMI4."
            )
        )

    service_item_note = int(
        config.get(
            "presenter_change_service_item_note",
            5
        )
    )

    change_slide_note = int(
        config.get(
            "presenter_change_slide_note",
            4
        )
    )

    settle_seconds = float(
        config.get(
            "presenter_visual_settle_seconds",
            0.24
        )
    )

    max_items = int(
        config.get(
            "presenter_visual_scan_max_items",
            40
        )
    )

    max_items = max(
        1,
        min(
            128,
            max_items
        )
    )

    width = int(
        config.get(
            "presenter_visual_screenshot_width",
            960
        )
    )

    height = int(
        config.get(
            "presenter_visual_screenshot_height",
            540
        )
    )

    cache = _read_json(
        CACHE_FILE,
        {}
    )

    cached_index = None

    if (
        cache.get(
            "reference"
        )
        ==
        reference
        and
        (
            not plan_id
            or
            not cache.get(
                "plan_id"
            )
            or
            cache.get(
                "plan_id"
            )
            ==
            plan_id
        )
    ):
        try:
            cached_index = int(
                cache.get(
                    "item_index"
                )
            )
        except Exception:
            cached_index = None

    scan_order = []

    if (
        cached_index is not None
        and
        0
        <=
        cached_index
        <
        max_items
    ):
        scan_order.append(
            cached_index
        )

    for index in range(
        max_items
    ):
        if index not in scan_order:
            scan_order.append(
                index
            )

    # Cached item gets a fast single verification before a full scan.
    if scan_order:
        first_index = scan_order[
            0
        ]

        if (
            cached_index is not None
            and
            first_index
            ==
            cached_index
        ):
            _select_item_first_slide(
                port_name=port_name,
                channel=channel,
                item_index=first_index,
                service_item_note=service_item_note,
                change_slide_note=change_slide_note,
                settle_seconds=settle_seconds,
            )

            with tempfile.TemporaryDirectory(
                prefix="sss_presenter_cached_"
            ) as temp_dir:
                image_path = (
                    Path(
                        temp_dir
                    )
                    /
                    "cached.png"
                )

                _capture_source_png(
                    client,
                    source_name,
                    image_path,
                    width=width,
                    height=height,
                )

                ocr = _ocr_batch(
                    [
                        {
                            "index": first_index,
                            "source": source_name,
                            "path": str(
                                image_path
                            ),
                        }
                    ]
                )

                if (
                    ocr
                    and
                    _reference_matches(
                        ocr[
                            0
                        ].get(
                            "text",
                            ""
                        ),
                        reference,
                    )
                ):
                    return {
                        "success": True,
                        "item_index": first_index,
                        "source": source_name,
                        "reference": reference,
                        "ocr_text": ocr[
                            0
                        ].get(
                            "text",
                            ""
                        ),
                        "method": "cached MIDI + OBS visual verify",
                    }

    # Full scan. Capture every candidate first, then OCR them in ONE
    # Windows OCR process so the weekly discovery stays reasonably fast.
    with tempfile.TemporaryDirectory(
        prefix="sss_presenter_scan_"
    ) as temp_dir:
        temp_dir = Path(
            temp_dir
        )

        manifest = []

        for index in range(
            max_items
        ):
            _select_item_first_slide(
                port_name=port_name,
                channel=channel,
                item_index=index,
                service_item_note=service_item_note,
                change_slide_note=change_slide_note,
                settle_seconds=settle_seconds,
            )

            image_path = (
                temp_dir
                /
                f"item_{index:03d}.png"
            )

            _capture_source_png(
                client,
                source_name,
                image_path,
                width=width,
                height=height,
            )

            manifest.append(
                {
                    "index": index,
                    "source": source_name,
                    "path": str(
                        image_path
                    ),
                }
            )

        ocr_results = _ocr_batch(
            manifest,
            timeout=float(
                config.get(
                    "presenter_visual_ocr_timeout_seconds",
                    60
                )
            ),
        )

        for item in ocr_results:
            if not item.get(
                "success",
                False
            ):
                continue

            text = item.get(
                "text",
                ""
            )

            if not _reference_matches(
                text,
                reference,
            ):
                continue

            index = int(
                item.get(
                    "index"
                )
            )

            # Put Presenter back on the verified Scripture item and
            # its first slide before SSS transitions it to Program.
            _select_item_first_slide(
                port_name=port_name,
                channel=channel,
                item_index=index,
                service_item_note=service_item_note,
                change_slide_note=change_slide_note,
                settle_seconds=settle_seconds,
            )

            _atomic_json(
                CACHE_FILE,
                {
                    "plan_id": plan_id,
                    "reference": reference,
                    "item_index": index,
                    "source": source_name,
                    "verified_at": time.time(),
                },
            )

            return {
                "success": True,
                "item_index": index,
                "source": source_name,
                "reference": reference,
                "ocr_text": text,
                "method": "MIDI scan + OBS visual verify",
            }

    raise RuntimeError(
        (
            "SSS scanned Presenter but could not verify "
            +
            reference
            +
            " on "
            +
            source_name
            +
            "."
        )
    )
