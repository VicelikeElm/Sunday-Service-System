import base64
import json
import os
import subprocess
from pathlib import Path


BASE = Path(r"C:\Church\SermonAI")
STATE_DIR = BASE / "State"
OCR_SCRIPT = BASE / "presenter_windows_ocr.ps1"


def _clean(value):
    return " ".join(
        str(value or "").split()
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


