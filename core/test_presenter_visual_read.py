import tempfile
from pathlib import Path

from sunday_common import (
    load_config,
    obs_connection,
)

from presenter_visual_cue import (
    _capture_source_png,
    _ocr_batch,
    _resolve_obs_source,
)


config = load_config()
client = obs_connection(
    config,
    timeout=4,
)

source = _resolve_obs_source(
    client,
    [
        config.get(
            "presenter_visual_source",
            "webcam TP"
        ),
        config.get(
            "presenter_visual_fallback_source",
            "Cam Link Pro HDMI4"
        ),
    ],
)

if not source:
    raise SystemExit(
        "Could not find webcam TP or Cam Link Pro HDMI4 in OBS."
    )

with tempfile.TemporaryDirectory(
    prefix="sss_presenter_read_"
) as temp_dir:
    image = (
        Path(
            temp_dir
        )
        /
        "presenter.png"
    )

    _capture_source_png(
        client,
        source,
        image,
        width=960,
        height=540,
    )

    result = _ocr_batch(
        [
            {
                "index": 0,
                "source": source,
                "path": str(
                    image
                ),
            }
        ]
    )

    print(
        "OBS source:",
        source
    )

    print(
        "\nWindows OCR text:\n"
    )

    print(
        result[
            0
        ].get(
            "text",
            ""
        )
        if result
        else
        "No OCR result."
    )
