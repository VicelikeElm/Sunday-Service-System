import base64
import hashlib
import json
import math
import socket
import time

from sunday_common import load_config
from sss_reliability import (
    BASE,
    AUDIO_STATUS_FILE,
    atomic_json,
    now_iso,
)

ENV_FILE = BASE / ".env"


def read_env():
    result = {}

    if not ENV_FILE.exists():
        return result

    try:
        for raw in ENV_FILE.read_text(
            encoding="utf-8",
            errors="replace"
        ).splitlines():
            line = raw.strip()

            if not line:
                continue

            if line.startswith(
                "#"
            ):
                continue

            if "=" not in line:
                continue

            key, value = line.split(
                "=",
                1
            )

            result[
                key.strip()
            ] = value.strip().strip(
                '"'
            ).strip(
                "'"
            )

    except Exception:
        pass

    return result


def obs_auth_string(
    password,
    salt,
    challenge
):
    secret = base64.b64encode(
        hashlib.sha256(
            (
                password
                +
                salt
            ).encode(
                "utf-8"
            )
        ).digest()
    ).decode(
        "utf-8"
    )

    auth = base64.b64encode(
        hashlib.sha256(
            (
                secret
                +
                challenge
            ).encode(
                "utf-8"
            )
        ).digest()
    ).decode(
        "utf-8"
    )

    return auth


def multiplier_to_db(
    value
):
    try:
        value = float(
            value
        )
    except Exception:
        return -120.0

    if value <= 0:
        return -120.0

    return 20.0 * math.log10(
        value
    )


def flatten_numbers(
    value
):
    output = []

    if isinstance(
        value,
        (
            int,
            float,
        )
    ):
        output.append(
            float(
                value
            )
        )

    elif isinstance(
        value,
        list
    ):
        for item in value:
            output.extend(
                flatten_numbers(
                    item
                )
            )

    elif isinstance(
        value,
        dict
    ):
        for item in value.values():
            output.extend(
                flatten_numbers(
                    item
                )
            )

    return output


def write(
    *,
    state,
    detail,
    max_db=-120.0,
    silence_seconds=0.0,
    clip_seconds=0.0,
    input_name=""
):
    atomic_json(
        AUDIO_STATUS_FILE,
        {
            "updated": now_iso(),
            "state": state,
            "detail": detail,
            "max_db": round(
                float(
                    max_db
                ),
                1
            ),
            "silence_seconds": round(
                float(
                    silence_seconds
                ),
                1
            ),
            "clip_seconds": round(
                float(
                    clip_seconds
                ),
                1
            ),
            "input": input_name,
        }
    )


def run_once():
    config = load_config()
    env = read_env()

    host = str(
        config.get(
            "obs_host",
            env.get(
                "OBS_HOST",
                "localhost"
            )
        )
    )

    port = int(
        config.get(
            "obs_port",
            env.get(
                "OBS_PORT",
                4455
            )
        )
    )

    password = str(
        env.get(
            "OBS_PASSWORD",
            config.get(
                "obs_password",
                ""
            )
        )
    )

    monitored_inputs = config.get(
        "audio_sanity_inputs",
        [
            "main"
        ]
    )

    if not isinstance(
        monitored_inputs,
        list
    ):
        monitored_inputs = [
            str(
                monitored_inputs
            )
        ]

    monitored_lower = {
        str(
            item
        ).lower()
        for item in monitored_inputs
    }

    silence_db = float(
        config.get(
            "audio_sanity_silence_db",
            -55
        )
    )

    silence_limit = float(
        config.get(
            "audio_sanity_silence_seconds",
            120
        )
    )

    clip_db = float(
        config.get(
            "audio_sanity_clip_db",
            -0.5
        )
    )

    clip_limit = float(
        config.get(
            "audio_sanity_clip_seconds",
            3
        )
    )

    # Lightweight localhost-only live meter feed for the SSS dashboard.
    # This avoids making the Tkinter GUI maintain its own OBS websocket.
    # The normal JSON status file remains the durable fallback.
    meter_port = int(
        config.get(
            "audio_meter_udp_port",
            49221
        )
    )

    meter_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
    )

    meter_target = (
        "127.0.0.1",
        meter_port,
    )

    try:
        import websocket
    except ImportError as exc:
        raise RuntimeError(
            "websocket-client is not installed. "
            "Run Setup-SSS-v22.bat."
        ) from exc

    url = (
        f"ws://{host}:{port}"
    )

    ws = websocket.create_connection(
        url,
        timeout=10,
        http_proxy_host=None,
        http_proxy_port=None,
        subprotocols=[
            "obswebsocket.json"
        ],
    )

    try:
        hello = json.loads(
            ws.recv()
        )

        if hello.get(
            "op"
        ) != 0:
            raise RuntimeError(
                "Unexpected OBS WebSocket greeting."
            )

        hello_data = hello.get(
            "d",
            {}
        )

        identify = {
            "rpcVersion": int(
                hello_data.get(
                    "rpcVersion",
                    1
                )
            ),
            # InputVolumeMeters subscription bit.
            "eventSubscriptions": 65536,
        }

        auth_data = hello_data.get(
            "authentication"
        )

        if auth_data:
            identify[
                "authentication"
            ] = obs_auth_string(
                password,
                auth_data.get(
                    "salt",
                    ""
                ),
                auth_data.get(
                    "challenge",
                    ""
                ),
            )

        ws.send(
            json.dumps(
                {
                    "op": 1,
                    "d": identify,
                }
            )
        )

        identified = json.loads(
            ws.recv()
        )

        if identified.get(
            "op"
        ) != 2:
            raise RuntimeError(
                "OBS WebSocket audio monitor identification failed."
            )

        write(
            state="STARTING",
            detail="Waiting for OBS audio meter events.",
            input_name=", ".join(
                monitored_inputs
            ),
        )

        last_event = time.time()
        last_write = 0.0
        silence_started = None
        clip_started = None

        while True:
            try:
                raw = ws.recv()
            except Exception:
                if time.time() - last_event > 12:
                    raise
                continue

            message = json.loads(
                raw
            )

            if message.get(
                "op"
            ) != 5:
                continue

            data = message.get(
                "d",
                {}
            )

            if data.get(
                "eventType"
            ) != "InputVolumeMeters":
                continue

            last_event = time.time()

            inputs = data.get(
                "eventData",
                {}
            ).get(
                "inputs",
                []
            )

            maximum = 0.0
            found_names = []

            for item in inputs:
                name = str(
                    item.get(
                        "inputName",
                        ""
                    )
                )

                if name.lower() not in monitored_lower:
                    continue

                found_names.append(
                    name
                )

                values = flatten_numbers(
                    item.get(
                        "inputLevelsMul",
                        []
                    )
                )

                if values:
                    maximum = max(
                        maximum,
                        max(
                            values
                        ),
                    )

            max_db = multiplier_to_db(
                maximum
            )

            current = time.time()

            if max_db <= silence_db:
                if silence_started is None:
                    silence_started = current
            else:
                silence_started = None

            if max_db >= clip_db:
                if clip_started is None:
                    clip_started = current
            else:
                clip_started = None

            silence_seconds = (
                current
                -
                silence_started
                if silence_started is not None
                else 0.0
            )

            clip_seconds = (
                current
                -
                clip_started
                if clip_started is not None
                else 0.0
            )

            if not found_names:
                state = "INPUT_MISSING"
                detail = (
                    "OBS audio meter does not contain configured input(s): "
                    +
                    ", ".join(
                        monitored_inputs
                    )
                )

            elif clip_seconds >= clip_limit:
                state = "CLIPPING"
                detail = (
                    f"Audio has remained near clipping for "
                    f"{clip_seconds:.0f} seconds."
                )

            elif silence_seconds >= silence_limit:
                state = "SILENT"
                detail = (
                    f"Program audio has remained below "
                    f"{silence_db:.0f} dB for "
                    f"{silence_seconds:.0f} seconds."
                )

            else:
                state = "OK"
                detail = (
                    f"{', '.join(found_names)} "
                    f"peak {max_db:.1f} dB"
                )

            # Send the instantaneous meter level to SSS. This is
            # localhost-only and intentionally best-effort; a dashboard
            # restart must never interrupt the independent audio watchdog.
            try:
                meter_socket.sendto(
                    json.dumps(
                        {
                            "max_db": round(
                                float(
                                    max_db
                                ),
                                1
                            ),
                            "silence_seconds": round(
                                float(
                                    silence_seconds
                                ),
                                1
                            ),
                            "clip_seconds": round(
                                float(
                                    clip_seconds
                                ),
                                1
                            ),
                            "state": state,
                            "input": ", ".join(
                                found_names
                                or
                                monitored_inputs
                            ),
                            "sent_at": current,
                        }
                    ).encode(
                        "utf-8"
                    ),
                    meter_target,
                )
            except Exception:
                pass

            if (
                current
                -
                last_write
                >=
                1.0
            ):
                write(
                    state=state,
                    detail=detail,
                    max_db=max_db,
                    silence_seconds=silence_seconds,
                    clip_seconds=clip_seconds,
                    input_name=", ".join(
                        found_names
                        or
                        monitored_inputs
                    ),
                )

                last_write = current

    finally:
        try:
            ws.close()
        except Exception:
            pass

        try:
            meter_socket.close()
        except Exception:
            pass


def main():
    while True:
        try:
            run_once()

        except Exception as exc:
            write(
                state="ERROR",
                detail=str(
                    exc
                ),
            )

            time.sleep(
                5
            )


if __name__ == "__main__":
    main()
