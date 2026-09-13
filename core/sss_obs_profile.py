from datetime import datetime

from sunday_common import (
    get_obs_endpoint,
    get_obs_status,
    load_config,
)

from sss_secrets_vault import (
    connect_obs_with_vault,
)



def _clean(value):
    return " ".join(
        str(
            value
            or
            ""
        ).split()
    )


def _get_value(
    value,
    *names
):
    for name in names:
        if isinstance(
            value,
            dict
        ):
            if name in value:
                return value.get(
                    name
                )
        else:
            try:
                result = getattr(
                    value,
                    name
                )

                if result is not None:
                    return result
            except Exception:
                pass

    return None


def _extract_scene_names(
    response
):
    raw_scenes = _get_value(
        response,
        "scenes",
    ) or []

    names = []

    for item in raw_scenes:
        name = _get_value(
            item,
            "sceneName",
            "scene_name",
            "name",
        )

        name = _clean(
            name
        )

        if name and name not in names:
            names.append(
                name
            )

    return names


def _extract_collection_names(
    response
):
    raw = _get_value(
        response,
        "scene_collections",
        "sceneCollections",
    ) or []

    names = []

    for item in raw:
        if isinstance(
            item,
            str
        ):
            name = item
        else:
            name = _get_value(
                item,
                "sceneCollectionName",
                "scene_collection_name",
                "name",
            )

        name = _clean(
            name
        )

        if name and name not in names:
            names.append(
                name
            )

    return names


def _extract_input_names(
    response
):
    raw = _get_value(
        response,
        "inputs",
    ) or []

    names = []

    for item in raw:
        name = _get_value(
            item,
            "inputName",
            "input_name",
            "name",
        )

        name = _clean(
            name
        )

        if name and name not in names:
            names.append(
                name
            )

    return names


def connect_local_obs(
    timeout=4
):
    """
    Connect using this PC's existing local SSS/OBS credentials.

    Credentials intentionally remain local and are never stored in or
    exported with the church profile.
    """
    config = load_config()

    client = connect_obs_with_vault(
        config,
        timeout=timeout,
    )

    host, port, _password = get_obs_endpoint(
        config
    )

    return (
        client,
        config,
        host,
        port,
    )


def discover_obs():
    client, config, host, port = connect_local_obs(
        timeout=5
    )

    collection_response = client.get_scene_collection_list()
    scene_response = client.get_scene_list()

    collections = _extract_collection_names(
        collection_response
    )

    current_collection = _clean(
        _get_value(
            collection_response,
            "current_scene_collection_name",
            "currentSceneCollectionName",
        )
    )

    if (
        current_collection
        and
        current_collection not in collections
    ):
        collections.insert(
            0,
            current_collection,
        )

    scenes = _extract_scene_names(
        scene_response
    )

    current_program = _clean(
        _get_value(
            scene_response,
            "current_program_scene_name",
            "currentProgramSceneName",
        )
    )

    current_preview = _clean(
        _get_value(
            scene_response,
            "current_preview_scene_name",
            "currentPreviewSceneName",
        )
    )

    legacy_collection = _clean(
        config.get(
            "scene_collection",
            ""
        )
    )

    try:
        input_response = client.get_input_list()
        inputs = _extract_input_names(input_response)
    except Exception:
        inputs = []

    return {
        "host": str(
            host
        ),
        "port": int(
            port
        ),
        "collections": collections,
        "current_collection": current_collection,
        "legacy_collection": legacy_collection,
        "scenes": scenes,
        "current_program_scene": current_program,
        "current_preview_scene": current_preview,
        "inputs": inputs,
        "discovered_at": datetime.now().astimezone().isoformat(),
    }


def load_scene_to_preview(
    client,
    scene_name
):
    scene_name = _clean(
        scene_name
    )

    if not scene_name:
        raise ValueError(
            "OBS scene name is blank."
        )

    # Raw OBS WebSocket request keeps this compatible across the
    # obsws-python convenience-method naming differences.
    return client.send(
        "SetCurrentPreviewScene",
        {
            "sceneName": scene_name,
        },
        raw=True,
    )


def test_profile_preview_scene(
    scene_name
):
    client, _config, _host, _port = connect_local_obs(
        timeout=5
    )

    status = get_obs_status(
        client
    )

    if (
        status.get(
            "recording"
        )
        or
        status.get(
            "streaming"
        )
    ):
        raise RuntimeError(
            "Preview testing is disabled while OBS is recording or streaming."
        )

    load_scene_to_preview(
        client,
        scene_name,
    )

    return True
