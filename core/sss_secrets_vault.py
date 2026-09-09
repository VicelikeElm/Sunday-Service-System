import ctypes
import json
import os
import re
from ctypes import wintypes
from pathlib import Path

from sss_profile import load_active_profile


BASE = Path(r"C:\Church\SermonAI")
ENV_FILE = BASE / ".env"
SUNDAY_CONFIG_FILE = BASE / "sunday_config.json"

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168

OBS_SECRET_NAME = "OBS_WEBSOCKET_PASSWORD"


def _clean(value):
    return " ".join(
        str(
            value
            or
            ""
        ).split()
    )


def _active_profile_id():
    try:
        profile = load_active_profile()

        return _clean(
            profile.get(
                "profile_id",
                "default"
            )
        ) or "default"

    except Exception:
        return "default"


def credential_target(
    secret_name,
    *,
    profile_id=None
):
    name = _clean(
        secret_name
    )

    if not name:
        raise ValueError(
            "Secret name is required."
        )

    if profile_id is None:
        profile_id = _active_profile_id()

    profile_id = _clean(
        profile_id
    ) or "default"

    safe_profile = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        profile_id,
    )

    safe_name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        name,
    )

    return (
        "SundayServiceSystem/"
        +
        safe_profile
        +
        "/"
        +
        safe_name
    )


class FILETIME(ctypes.Structure):
    _fields_ = [
        (
            "dwLowDateTime",
            wintypes.DWORD,
        ),
        (
            "dwHighDateTime",
            wintypes.DWORD,
        ),
    ]


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        (
            "Flags",
            wintypes.DWORD,
        ),
        (
            "Type",
            wintypes.DWORD,
        ),
        (
            "TargetName",
            wintypes.LPWSTR,
        ),
        (
            "Comment",
            wintypes.LPWSTR,
        ),
        (
            "LastWritten",
            FILETIME,
        ),
        (
            "CredentialBlobSize",
            wintypes.DWORD,
        ),
        (
            "CredentialBlob",
            ctypes.POINTER(
                wintypes.BYTE
            ),
        ),
        (
            "Persist",
            wintypes.DWORD,
        ),
        (
            "AttributeCount",
            wintypes.DWORD,
        ),
        (
            "Attributes",
            ctypes.c_void_p,
        ),
        (
            "TargetAlias",
            wintypes.LPWSTR,
        ),
        (
            "UserName",
            wintypes.LPWSTR,
        ),
    ]


PCREDENTIALW = ctypes.POINTER(
    CREDENTIALW
)


def vault_available():
    return (
        os.name
        ==
        "nt"
        and
        hasattr(
            ctypes,
            "WinDLL"
        )
    )


def _advapi32():
    if not vault_available():
        raise RuntimeError(
            "Windows Credential Manager is only available on Windows."
        )

    library = ctypes.WinDLL(
        "Advapi32.dll",
        use_last_error=True,
    )

    library.CredWriteW.argtypes = [
        ctypes.POINTER(
            CREDENTIALW
        ),
        wintypes.DWORD,
    ]
    library.CredWriteW.restype = wintypes.BOOL

    library.CredReadW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(
            PCREDENTIALW
        ),
    ]
    library.CredReadW.restype = wintypes.BOOL

    library.CredDeleteW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    library.CredDeleteW.restype = wintypes.BOOL

    library.CredFree.argtypes = [
        ctypes.c_void_p,
    ]
    library.CredFree.restype = None

    return library


def set_secret(
    secret_name,
    secret_value,
    *,
    profile_id=None,
    username="Sunday Service System"
):
    value = str(
        secret_value
        or
        ""
    )

    if not value:
        raise ValueError(
            "Secret value is blank."
        )

    target = credential_target(
        secret_name,
        profile_id=profile_id,
    )

    library = _advapi32()

    blob = value.encode(
        "utf-16-le"
    )

    # Windows Generic Credentials allow a bounded credential blob. Keep the
    # vault API focused on small application secrets, not arbitrary files.
    if len(
        blob
    ) > 5000:
        raise ValueError(
            "Secret is too large for Windows Credential Manager."
        )

    buffer = ctypes.create_string_buffer(
        blob
    )

    credential = CREDENTIALW()
    credential.Flags = 0
    credential.Type = CRED_TYPE_GENERIC
    credential.TargetName = target
    credential.Comment = (
        "Sunday Service System local protected secret"
    )
    credential.CredentialBlobSize = len(
        blob
    )
    credential.CredentialBlob = ctypes.cast(
        buffer,
        ctypes.POINTER(
            wintypes.BYTE
        ),
    )
    credential.Persist = CRED_PERSIST_LOCAL_MACHINE
    credential.AttributeCount = 0
    credential.Attributes = None
    credential.TargetAlias = None
    credential.UserName = str(
        username
        or
        "Sunday Service System"
    )

    ok = library.CredWriteW(
        ctypes.byref(
            credential
        ),
        0,
    )

    if not ok:
        code = ctypes.get_last_error()

        raise OSError(
            code,
            (
                "Windows Credential Manager could not save the SSS secret."
            ),
        )

    return target


def get_secret(
    secret_name,
    *,
    profile_id=None
):
    target = credential_target(
        secret_name,
        profile_id=profile_id,
    )

    library = _advapi32()

    pointer = PCREDENTIALW()

    ok = library.CredReadW(
        target,
        CRED_TYPE_GENERIC,
        0,
        ctypes.byref(
            pointer
        ),
    )

    if not ok:
        code = ctypes.get_last_error()

        if code == ERROR_NOT_FOUND:
            return None

        raise OSError(
            code,
            (
                "Windows Credential Manager could not read the SSS secret."
            ),
        )

    try:
        credential = pointer.contents

        size = int(
            credential.CredentialBlobSize
        )

        if size <= 0:
            return ""

        raw = ctypes.string_at(
            credential.CredentialBlob,
            size,
        )

        return raw.decode(
            "utf-16-le"
        )

    finally:
        library.CredFree(
            ctypes.cast(
                pointer,
                ctypes.c_void_p,
            )
        )


def delete_secret(
    secret_name,
    *,
    profile_id=None
):
    target = credential_target(
        secret_name,
        profile_id=profile_id,
    )

    library = _advapi32()

    ok = library.CredDeleteW(
        target,
        CRED_TYPE_GENERIC,
        0,
    )

    if not ok:
        code = ctypes.get_last_error()

        if code == ERROR_NOT_FOUND:
            return False

        raise OSError(
            code,
            (
                "Windows Credential Manager could not delete the SSS secret."
            ),
        )

    return True


def secret_status(
    secret_name,
    *,
    profile_id=None
):
    if not vault_available():
        return {
            "available": False,
            "stored": False,
            "target": credential_target(
                secret_name,
                profile_id=profile_id,
            ),
            "detail": (
                "Windows Credential Manager is unavailable on this operating system."
            ),
        }

    try:
        value = get_secret(
            secret_name,
            profile_id=profile_id,
        )

        return {
            "available": True,
            "stored": value is not None,
            "target": credential_target(
                secret_name,
                profile_id=profile_id,
            ),
            "detail": (
                "Stored in Windows Credential Manager"
                if value is not None
                else
                "Not stored in Windows Credential Manager"
            ),
        }

    except Exception as exc:
        return {
            "available": True,
            "stored": False,
            "target": credential_target(
                secret_name,
                profile_id=profile_id,
            ),
            "detail": str(
                exc
            ),
        }


def get_obs_vault_password():
    return get_secret(
        OBS_SECRET_NAME
    )


def set_obs_vault_password(
    password
):
    target = set_secret(
        OBS_SECRET_NAME,
        password,
        username="OBS WebSocket",
    )

    try:
        from sss_event_history import record_event

        record_event(
            (
                "OBS WebSocket password stored in Windows Credential Manager."
            ),
            category="SECURITY",
            level="ACTION",
            source="SECRETS VAULT",
        )
    except Exception:
        pass

    return target


def delete_obs_vault_password():
    removed = delete_secret(
        OBS_SECRET_NAME
    )

    if removed:
        try:
            from sss_event_history import record_event

            record_event(
                (
                    "OBS WebSocket password removed from Windows Credential Manager."
                ),
                category="SECURITY",
                level="ACTION",
                source="SECRETS VAULT",
            )
        except Exception:
            pass

    return removed


def obs_vault_status():
    return secret_status(
        OBS_SECRET_NAME
    )


def _legacy_obs_password_from_config(
    config=None
):
    from sunday_common import (
        get_obs_endpoint,
        load_config,
    )

    if config is None:
        config = load_config()

    _host, _port, password = get_obs_endpoint(
        config
    )

    password = str(
        password
        or
        ""
    )

    return password


def legacy_obs_loose_locations():
    locations = []

    if ENV_FILE.exists():
        try:
            pattern = re.compile(
                r"^\s*(?:export\s+)?OBS_PASSWORD\s*=",
                flags=re.IGNORECASE,
            )

            for line in ENV_FILE.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines():
                if pattern.match(
                    line
                ):
                    locations.append(
                        str(
                            ENV_FILE
                        )
                        +
                        " : OBS_PASSWORD"
                    )
                    break

        except Exception:
            pass

    if SUNDAY_CONFIG_FILE.exists():
        try:
            payload = json.loads(
                SUNDAY_CONFIG_FILE.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(
                payload,
                dict
            ):
                for key in payload.keys():
                    if str(
                        key
                    ).lower() in {
                        "obs_password",
                    }:
                        locations.append(
                            str(
                                SUNDAY_CONFIG_FILE
                            )
                            +
                            " : "
                            +
                            str(
                                key
                            )
                        )

        except Exception:
            pass

    return locations


def legacy_obs_password_present(
    config=None
):
    try:
        return bool(
            _legacy_obs_password_from_config(
                config
            )
        )
    except Exception:
        return False


def copy_legacy_obs_password_to_vault(
    config=None
):
    password = _legacy_obs_password_from_config(
        config
    )

    if not password:
        raise RuntimeError(
            (
                "No legacy OBS WebSocket password was found. "
                "OBS authentication may be disabled or the password may already "
                "have been removed from loose configuration."
            )
        )

    target = set_obs_vault_password(
        password
    )

    return {
        "target": target,
        "copied": True,
    }


def connect_obs_with_vault(
    config,
    *,
    timeout=4
):
    """
    OBS connection path used by SSS.

    Vault credential wins when present.
    If no vault credential exists, the existing sunday_common legacy path is
    left completely unchanged.
    """
    from sunday_common import (
        get_obs_endpoint,
        obs_connection,
    )

    host, port, legacy_password = get_obs_endpoint(
        config
    )

    vault_password = None

    if vault_available():
        try:
            vault_password = get_obs_vault_password()
        except Exception:
            vault_password = None

    if vault_password is None:
        return obs_connection(
            config,
            timeout=timeout,
        )

    try:
        import obsws_python
    except Exception as exc:
        raise RuntimeError(
            (
                "OBS vault credential exists, but obsws_python could not be "
                "loaded for the protected connection path. "
                +
                str(
                    exc
                )
            )
        ) from exc

    return obsws_python.ReqClient(
        host=str(
            host
        ),
        port=int(
            port
        ),
        password=vault_password,
        timeout=float(
            timeout
        ),
    )


def test_obs_vault_connection(
    config=None,
    *,
    timeout=4
):
    from sunday_common import (
        get_obs_endpoint,
        load_config,
    )

    if config is None:
        config = load_config()

    status = obs_vault_status()

    if not status.get(
        "stored"
    ):
        raise RuntimeError(
            "No OBS WebSocket password is stored in Windows Credential Manager."
        )

    client = connect_obs_with_vault(
        config,
        timeout=timeout,
    )

    # Harmless read confirms authentication and request/response behavior.
    response = client.get_version()

    host, port, _legacy_password = get_obs_endpoint(
        config
    )

    return {
        "ok": True,
        "host": str(
            host
        ),
        "port": int(
            port
        ),
        "obs_version": str(
            getattr(
                response,
                "obs_version",
                getattr(
                    response,
                    "obsVersion",
                    ""
                )
            )
            or
            ""
        ),
    }


def _remove_env_key(
    path,
    key
):
    path = Path(
        path
    )

    if not path.exists():
        return False

    original = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = original.splitlines(
        keepends=True
    )

    pattern = re.compile(
        r"^\s*(?:export\s+)?"
        +
        re.escape(
            key
        )
        +
        r"\s*=",
        flags=re.IGNORECASE,
    )

    kept = []
    removed = False

    for line in lines:
        if pattern.match(
            line
        ):
            removed = True
            continue

        kept.append(
            line
        )

    if not removed:
        return False

    temp = path.with_suffix(
        path.suffix
        +
        ".sss_tmp"
    )

    temp.write_text(
        "".join(
            kept
        ),
        encoding="utf-8",
    )

    os.replace(
        temp,
        path,
    )

    return True


def _remove_json_keys(
    path,
    keys
):
    path = Path(
        path
    )

    if not path.exists():
        return []

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return []

    if not isinstance(
        payload,
        dict
    ):
        return []

    lowered = {
        str(
            key
        ).lower()
        for key in keys
    }

    removed = []

    for key in list(
        payload.keys()
    ):
        if str(
            key
        ).lower() in lowered:
            payload.pop(
                key,
                None,
            )
            removed.append(
                str(
                    key
                )
            )

    if not removed:
        return []

    temp = path.with_suffix(
        path.suffix
        +
        ".sss_tmp"
    )

    temp.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        +
        "\n",
        encoding="utf-8",
    )

    os.replace(
        temp,
        path,
    )

    return removed


def remove_legacy_obs_password(
    *,
    require_vault_test=True
):
    """
    Remove ONLY the known OBS password key from loose SSS configuration.

    This does not touch Gmail/YouTube OAuth files or unrelated secrets.
    """
    if require_vault_test:
        test_obs_vault_connection()

    removed = []

    if _remove_env_key(
        ENV_FILE,
        "OBS_PASSWORD",
    ):
        removed.append(
            str(
                ENV_FILE
            )
            +
            " : OBS_PASSWORD"
        )

    json_removed = _remove_json_keys(
        SUNDAY_CONFIG_FILE,
        {
            "OBS_PASSWORD",
            "obs_password",
        },
    )

    for key in json_removed:
        removed.append(
            str(
                SUNDAY_CONFIG_FILE
            )
            +
            " : "
            +
            key
        )

    try:
        from sss_event_history import record_event

        record_event(
            (
                "Legacy loose OBS password removed after protected vault "
                "connection test."
                if removed
                else
                "Legacy OBS password cleanup checked; no loose OBS password "
                "entry was found."
            ),
            category="SECURITY",
            level="ACTION",
            source="SECRETS VAULT",
        )
    except Exception:
        pass

    return {
        "removed": removed,
        "count": len(
            removed
        ),
    }


def security_overview(
    config=None
):
    vault = obs_vault_status()

    loose_locations = legacy_obs_loose_locations()
    legacy_present = bool(
        loose_locations
    )

    gmail_token = (
        BASE
        /
        "gmail_token.json"
    )

    youtube_candidates = [
        BASE
        /
        "youtube_token.json",
        BASE
        /
        "youtube_oauth_token.json",
        BASE
        /
        "youtube_credentials.json",
    ]

    return {
        "vault_available": bool(
            vault.get(
                "available"
            )
        ),
        "obs_vault_stored": bool(
            vault.get(
                "stored"
            )
        ),
        "obs_target": str(
            vault.get(
                "target",
                ""
            )
        ),
        "legacy_obs_password_present": bool(
            legacy_present
        ),
        "legacy_obs_locations": loose_locations,
        "gmail_oauth_file_present": gmail_token.exists(),
        "youtube_oauth_file_present": any(
            path.exists()
            for path in youtube_candidates
        ),
    }
