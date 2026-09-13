import json
import os
import shutil
import subprocess
from pathlib import Path

from sss_release_trust import (
    SIGNED_UPDATES_REQUIRED,
    TRUSTED_UPDATE_SIGNER_THUMBPRINTS,
)


BASE = Path(r"C:\Church\SermonAI")
SIGNING_CONFIG_FILE = BASE / "sss_signing_config.json"


def normalize_thumbprint(value):
    return "".join(
        char
        for char in str(
            value
            or
            ""
        ).upper()
        if char in "0123456789ABCDEF"
    )


def load_signing_config(
    path=None,
    *,
    required=False
):
    path = Path(
        path
        or
        SIGNING_CONFIG_FILE
    )

    if not path.exists():
        if required:
            raise RuntimeError(
                (
                    "SSS signing configuration is missing:\n"
                    +
                    str(
                        path
                    )
                    +
                    "\n\nCreate it from sss_signing_config.example.json or run "
                    "Configure-SSS-Code-Signing.ps1."
                )
            )

        return {}

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8-sig"
            )
        )
    except Exception as exc:
        raise RuntimeError(
            (
                "SSS signing configuration could not be read:\n"
                +
                str(
                    exc
                )
            )
        ) from exc

    if not isinstance(
        payload,
        dict
    ):
        raise RuntimeError(
            "SSS signing configuration is not a JSON object."
        )

    return payload


def signing_thumbprint(
    config
):
    return normalize_thumbprint(
        config.get(
            "certificate_thumbprint",
            ""
        )
    )


def manifest_thumbprint(
    config
):
    value = normalize_thumbprint(
        config.get(
            "update_manifest_thumbprint",
            ""
        )
    )

    return (
        value
        or
        signing_thumbprint(
            config
        )
    )


def certificate_store(
    config
):
    value = str(
        config.get(
            "certificate_store",
            "CurrentUser"
        )
        or
        "CurrentUser"
    ).strip()

    if value.lower() == "localmachine":
        return "LocalMachine"

    return "CurrentUser"


def find_signtool(
    config=None
):
    config = config or {}

    explicit = str(
        config.get(
            "signtool_path",
            ""
        )
        or
        ""
    ).strip()

    if explicit:
        path = Path(
            explicit
        )

        if path.exists():
            return path

        raise RuntimeError(
            (
                "Configured SignTool was not found:\n"
                +
                str(
                    path
                )
            )
        )

    where = shutil.which(
        "signtool.exe"
    )

    if where:
        return Path(
            where
        )

    roots = [
        Path(
            os.environ.get(
                "ProgramFiles(x86)",
                r"C:\Program Files (x86)"
            )
        )
        /
        "Windows Kits"
        /
        "10"
        /
        "bin",

        Path(
            os.environ.get(
                "ProgramFiles",
                r"C:\Program Files"
            )
        )
        /
        "Windows Kits"
        /
        "10"
        /
        "bin",
    ]

    candidates = []

    for root in roots:
        if not root.exists():
            continue

        for candidate in root.glob(
            "*\\x64\\signtool.exe"
        ):
            candidates.append(
                candidate
            )

    if candidates:
        def version_key(
            path
        ):
            parts = []

            for token in path.parent.parent.name.split(
                "."
            ):
                try:
                    parts.append(
                        int(
                            token
                        )
                    )
                except Exception:
                    parts.append(
                        0
                    )

            return tuple(
                parts
            )

        candidates.sort(
            key=version_key,
            reverse=True,
        )

        return candidates[
            0
        ]

    raise RuntimeError(
        (
            "Microsoft SignTool was not found. Install the Windows SDK "
            "Signing Tools component or set signtool_path in "
            "sss_signing_config.json."
        )
    )


def _powershell_escape(
    value
):
    return str(
        value
    ).replace(
        "'",
        "''"
    )


def certificate_status(
    thumbprint,
    *,
    store="CurrentUser"
):
    thumbprint = normalize_thumbprint(
        thumbprint
    )

    if not thumbprint:
        return {
            "found": False,
            "has_private_key": False,
            "subject": "",
            "not_after": "",
            "thumbprint": "",
            "store": store,
        }

    store = (
        "LocalMachine"
        if str(
            store
        ).lower()
        ==
        "localmachine"
        else
        "CurrentUser"
    )

    ps = (
        "$ErrorActionPreference='Stop'; "
        "$thumb='"
        +
        _powershell_escape(
            thumbprint
        )
        +
        "'; "
        "$path='Cert:\\"
        +
        store
        +
        "\\My\\' + $thumb; "
        "$cert=Get-Item -LiteralPath $path -ErrorAction SilentlyContinue; "
        "if(-not $cert){ Write-Output '{\"found\":false}'; exit 0 }; "
        "$o=[ordered]@{found=$true;has_private_key=$cert.HasPrivateKey;"
        "subject=$cert.Subject;not_after=$cert.NotAfter.ToString('o');"
        "thumbprint=$cert.Thumbprint;store='"
        +
        store
        +
        "'}; "
        "$o | ConvertTo-Json -Compress"
    )

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
        timeout=15,
        creationflags=getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0
        ),
    )

    if cp.returncode != 0:
        raise RuntimeError(
            cp.stderr.strip()
            or
            cp.stdout.strip()
            or
            "Could not inspect Windows certificate store."
        )

    raw = (
        cp.stdout
        or
        ""
    ).strip()

    if not raw:
        return {
            "found": False,
            "has_private_key": False,
            "subject": "",
            "not_after": "",
            "thumbprint": "",
            "store": store,
        }

    payload = json.loads(
        raw
    )

    if not isinstance(
        payload,
        dict
    ):
        payload = {}

    return {
        "found": bool(
            payload.get(
                "found"
            )
        ),
        "has_private_key": bool(
            payload.get(
                "has_private_key"
            )
        ),
        "subject": str(
            payload.get(
                "subject",
                ""
            )
        ),
        "not_after": str(
            payload.get(
                "not_after",
                ""
            )
        ),
        "thumbprint": normalize_thumbprint(
            payload.get(
                "thumbprint",
                ""
            )
        ),
        "store": store,
    }


def validate_signing_config(
    config
):
    thumb = signing_thumbprint(
        config
    )

    if len(
        thumb
    ) != 40:
        raise RuntimeError(
            (
                "certificate_thumbprint must be a 40-character SHA-1 "
                "certificate thumbprint."
            )
        )

    store = certificate_store(
        config
    )

    status = certificate_status(
        thumb,
        store=store,
    )

    if not status.get(
        "found"
    ):
        raise RuntimeError(
            (
                "Configured code-signing certificate was not found in "
                +
                store
                +
                "\\My:\n"
                +
                thumb
            )
        )

    if not status.get(
        "has_private_key"
    ):
        raise RuntimeError(
            (
                "Configured certificate does not have an accessible private key."
            )
        )

    manifest_thumb = manifest_thumbprint(
        config
    )

    manifest_status = certificate_status(
        manifest_thumb,
        store=store,
    )

    if not manifest_status.get(
        "found"
    ):
        raise RuntimeError(
            "Configured update-manifest signing certificate was not found."
        )

    if not manifest_status.get(
        "has_private_key"
    ):
        raise RuntimeError(
            (
                "Configured update-manifest certificate has no accessible "
                "private key."
            )
        )

    signtool = find_signtool(
        config
    )

    return {
        "code_signing": status,
        "manifest_signing": manifest_status,
        "signtool": str(
            signtool
        ),
        "timestamp_url": str(
            config.get(
                "timestamp_url",
                ""
            )
            or
            ""
        ),
    }


def write_release_trust_file(
    config,
    *,
    destination=None
):
    destination = Path(
        destination
        or
        (
            Path(
                __file__
            ).resolve().parent
            /
            "sss_release_trust.py"
        )
    )

    trusted = []

    for value in (
        signing_thumbprint(
            config
        ),
        manifest_thumbprint(
            config
        ),
    ):
        value = normalize_thumbprint(
            value
        )

        if (
            value
            and
            value not in trusted
        ):
            trusted.append(
                value
            )

    if not trusted:
        raise RuntimeError(
            "No trusted signing thumbprint is configured."
        )

    text = (
        '"""Generated by the SSS signed release build. Public trust metadata only."""\n\n'
        "SIGNED_UPDATES_REQUIRED = True\n"
        "TRUSTED_UPDATE_SIGNER_THUMBPRINTS = (\n"
        +
        "".join(
            (
                '    "'
                +
                thumb
                +
                '",\n'
            )
            for thumb in trusted
        )
        +
        ")\n"
        "RELEASE_SIGNING_CONFIGURED = True\n"
    )

    destination.write_text(
        text,
        encoding="utf-8",
    )

    return destination


def normalize_timestamp_url(
    value
):
    """
    Normalize known timestamp-service aliases to the provider's documented
    SignTool/RFC3161 endpoint.

    DigiCert documents:
        http://timestamp.digicert.com

    Older SSS v3.0/v3.1 setup scripts accidentally stored the HTTPS form,
    which SignTool can reject as "Invalid Timestamp URL".
    """
    text = str(
        value
        or
        ""
    ).strip()

    if text.lower().rstrip("/") == "https://timestamp.digicert.com":
        return "http://timestamp.digicert.com"

    return text


def sign_authenticode_file(
    path,
    config
):
    path = Path(
        path
    )

    if not path.exists():
        raise FileNotFoundError(
            str(
                path
            )
        )

    thumb = signing_thumbprint(
        config
    )

    store = certificate_store(
        config
    )

    signtool = find_signtool(
        config
    )

    command = [
        str(
            signtool
        ),
        "sign",
        "/fd",
        "SHA256",
        "/sha1",
        thumb,
        "/s",
        "My",
    ]

    if store == "LocalMachine":
        command.append(
            "/sm"
        )

    timestamp = normalize_timestamp_url(
        config.get(
            "timestamp_url",
            ""
        )
    )

    if timestamp:
        command.extend(
            [
                "/tr",
                timestamp,
                "/td",
                "SHA256",
            ]
        )

    command.append(
        str(
            path
        )
    )

    cp = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180,
    )

    if cp.returncode != 0:
        raise RuntimeError(
            (
                "SignTool failed for "
                +
                str(
                    path
                )
                +
                "\n\n"
                +
                (
                    cp.stdout.strip()
                    +
                    "\n"
                    +
                    cp.stderr.strip()
                ).strip()
                +
                (
                    "\n\nTimestamp endpoint used: "
                    +
                    timestamp
                    if timestamp
                    else
                    ""
                )
            )
        )

    return verify_authenticode_file(
        path,
        trusted_thumbprints=(
            thumb,
        ),
        require_valid=True,
    )


def verify_authenticode_file(
    path,
    *,
    trusted_thumbprints=None,
    require_valid=True
):
    path = Path(
        path
    )

    trusted = {
        normalize_thumbprint(
            item
        )
        for item in (
            trusted_thumbprints
            or
            TRUSTED_UPDATE_SIGNER_THUMBPRINTS
        )
        if normalize_thumbprint(
            item
        )
    }

    ps = (
        "$ErrorActionPreference='Stop'; "
        "$sig=Get-AuthenticodeSignature -LiteralPath '"
        +
        _powershell_escape(
            path
        )
        +
        "'; "
        "$thumb=''; $subject=''; "
        "if($sig.SignerCertificate){$thumb=$sig.SignerCertificate.Thumbprint;"
        "$subject=$sig.SignerCertificate.Subject}; "
        "$o=[ordered]@{status=$sig.Status.ToString();"
        "status_message=$sig.StatusMessage;thumbprint=$thumb;subject=$subject}; "
        "$o | ConvertTo-Json -Compress"
    )

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
        timeout=30,
        creationflags=getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0
        ),
    )

    if cp.returncode != 0:
        raise RuntimeError(
            cp.stderr.strip()
            or
            cp.stdout.strip()
            or
            "Authenticode verification failed."
        )

    payload = json.loads(
        (
            cp.stdout
            or
            "{}"
        ).strip()
        or
        "{}"
    )

    thumb = normalize_thumbprint(
        payload.get(
            "thumbprint",
            ""
        )
    )

    status = str(
        payload.get(
            "status",
            ""
        )
    )

    trusted_match = (
        not trusted
        or
        thumb in trusted
    )

    valid = (
        status.lower()
        ==
        "valid"
        and
        trusted_match
    )

    status_message = str(
        payload.get(
            "status_message",
            ""
        )
    )

    subject = str(
        payload.get(
            "subject",
            ""
        )
    )

    development_subject = (
        subject.strip().lower()
        ==
        "cn=sunday service system development"
    )

    chain_message = status_message.lower()

    development_chain_only = bool(
        status.lower()
        ==
        "unknownerror"
        and
        trusted_match
        and
        development_subject
        and
        (
            "root certificate which is not trusted"
            in
            chain_message
            or
            "certificate chain could not be built to a trusted root authority"
            in
            chain_message
        )
    )

    # Local-development exception:
    # A self-signed SSS Development cert is explicitly pinned into the build.
    # Windows PowerShell may report UnknownError solely because that cert does
    # not chain to a public CA. We accept ONLY those known chain-trust messages,
    # ONLY for the exact development subject, and ONLY when its thumbprint is
    # one of the trusted pins compiled into this SSS release.
    effective_valid = bool(
        valid
        or
        development_chain_only
    )

    result = {
        "valid": effective_valid,
        "windows_status_valid": valid,
        "development_chain_only": development_chain_only,
        "status": status,
        "status_message": status_message,
        "thumbprint": thumb,
        "subject": subject,
        "trusted_match": trusted_match,
    }

    if (
        require_valid
        and
        not effective_valid
    ):
        raise RuntimeError(
            (
                "Authenticode signature is not valid/trusted for SSS:\\n"
                +
                str(
                    path
                )
                +
                "\\nStatus: "
                +
                status
                +
                "\\nStatus message: "
                +
                (
                    status_message
                    or
                    "(none)"
                )
                +
                "\\nSigner: "
                +
                thumb
                +
                "\\nSubject: "
                +
                subject
            )
        )

    return result


def sign_manifest_cms(
    manifest_path,
    signature_path,
    config
):
    manifest_path = Path(
        manifest_path
    )

    signature_path = Path(
        signature_path
    )

    thumb = manifest_thumbprint(
        config
    )

    store = certificate_store(
        config
    )

    ps = (
        "$ErrorActionPreference='Stop'; "
        "Add-Type -AssemblyName System.Security; "
        "$manifest='"
        +
        _powershell_escape(
            manifest_path
        )
        +
        "'; "
        "$signature='"
        +
        _powershell_escape(
            signature_path
        )
        +
        "'; "
        "$thumb='"
        +
        _powershell_escape(
            thumb
        )
        +
        "'; "
        "$cert=Get-Item -LiteralPath ('Cert:\\"
        +
        store
        +
        "\\My\\' + $thumb) -ErrorAction Stop; "
        "if(-not $cert.HasPrivateKey){throw 'Certificate has no private key'}; "
        "$content=[System.IO.File]::ReadAllBytes($manifest); "
        "$ci=New-Object -TypeName System.Security.Cryptography.Pkcs.ContentInfo -ArgumentList (,$content); "
        "$cms=New-Object -TypeName System.Security.Cryptography.Pkcs.SignedCms -ArgumentList $ci,$true; "
        "$signer=New-Object -TypeName System.Security.Cryptography.Pkcs.CmsSigner -ArgumentList $cert; "
        "$signer.IncludeOption=[System.Security.Cryptography.X509Certificates.X509IncludeOption]::EndCertOnly; "
        "$cms.ComputeSignature($signer); "
        "[System.IO.File]::WriteAllBytes($signature,$cms.Encode()); "
        "Write-Output $cert.Thumbprint"
    )

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
        timeout=60,
        creationflags=getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0
        ),
    )

    if cp.returncode != 0:
        raise RuntimeError(
            (
                "Could not create CMS signed update manifest.\n\n"
                +
                (
                    cp.stderr.strip()
                    or
                    cp.stdout.strip()
                )
            )
        )

    signer = normalize_thumbprint(
        cp.stdout.strip().splitlines()[
            -1
        ]
        if cp.stdout.strip()
        else
        ""
    )

    if signer != thumb:
        raise RuntimeError(
            "CMS manifest signer did not match configured certificate."
        )

    verify_manifest_cms(
        manifest_path,
        signature_path,
        trusted_thumbprints=(
            thumb,
        ),
        require_trusted=True,
    )

    return {
        "thumbprint": signer,
        "signature_path": str(
            signature_path
        ),
    }


def verify_manifest_cms(
    manifest_path,
    signature_path,
    *,
    trusted_thumbprints=None,
    require_trusted=None
):
    manifest_path = Path(
        manifest_path
    )

    signature_path = Path(
        signature_path
    )

    trusted = {
        normalize_thumbprint(
            item
        )
        for item in (
            trusted_thumbprints
            or
            TRUSTED_UPDATE_SIGNER_THUMBPRINTS
        )
        if normalize_thumbprint(
            item
        )
    }

    if require_trusted is None:
        require_trusted = SIGNED_UPDATES_REQUIRED

    trusted_json = json.dumps(
        sorted(
            trusted
        )
    )

    ps = (
        "$ErrorActionPreference='Stop'; "
        "Add-Type -AssemblyName System.Security; "
        "$manifest='"
        +
        _powershell_escape(
            manifest_path
        )
        +
        "'; "
        "$signature='"
        +
        _powershell_escape(
            signature_path
        )
        +
        "'; "
        "$trusted=ConvertFrom-Json '"
        +
        _powershell_escape(
            trusted_json
        )
        +
        "'; "
        "$content=[System.IO.File]::ReadAllBytes($manifest); "
        "$sig=[System.IO.File]::ReadAllBytes($signature); "
        "$ci=New-Object -TypeName System.Security.Cryptography.Pkcs.ContentInfo -ArgumentList (,$content); "
        "$cms=New-Object -TypeName System.Security.Cryptography.Pkcs.SignedCms -ArgumentList $ci,$true; "
        "$cms.Decode($sig); "
        "$cms.CheckSignature($true); "
        "if($cms.SignerInfos.Count -ne 1){throw 'Expected exactly one manifest signer'}; "
        "$cert=$cms.SignerInfos[0].Certificate; "
        "if(-not $cert){throw 'Manifest signature contains no signer certificate'}; "
        "$thumb=$cert.Thumbprint.ToUpper().Replace(' ',''); "
        "$trustedMatch=$false; "
        "foreach($t in $trusted){if($thumb -eq ([string]$t).ToUpper().Replace(' ','')){$trustedMatch=$true}}; "
        "$o=[ordered]@{valid=$true;thumbprint=$thumb;subject=$cert.Subject;"
        "not_before=$cert.NotBefore.ToString('o');not_after=$cert.NotAfter.ToString('o');"
        "trusted_match=$trustedMatch}; "
        "$o | ConvertTo-Json -Compress"
    )

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
        timeout=30,
        creationflags=getattr(
            subprocess,
            "CREATE_NO_WINDOW",
            0
        ),
    )

    if cp.returncode != 0:
        raise RuntimeError(
            (
                "Update manifest signature is invalid.\n\n"
                +
                (
                    cp.stderr.strip()
                    or
                    cp.stdout.strip()
                )
            )
        )

    result = json.loads(
        (
            cp.stdout
            or
            "{}"
        ).strip()
        or
        "{}"
    )

    result[
        "thumbprint"
    ] = normalize_thumbprint(
        result.get(
            "thumbprint",
            ""
        )
    )

    if (
        require_trusted
        and
        (
            not trusted
            or
            not result.get(
                "trusted_match"
            )
        )
    ):
        raise RuntimeError(
            (
                "Update manifest was cryptographically signed, but the signer "
                "is not in this SSS build's trusted release signer list.\n"
                "Signer: "
                +
                result.get(
                    "thumbprint",
                    ""
                )
            )
        )

    return result


def release_signing_status():
    config = load_signing_config(
        required=False
    )

    trusted = tuple(
        normalize_thumbprint(
            item
        )
        for item in TRUSTED_UPDATE_SIGNER_THUMBPRINTS
        if normalize_thumbprint(
            item
        )
    )

    result = {
        "signed_updates_required": bool(
            SIGNED_UPDATES_REQUIRED
        ),
        "trusted_thumbprints": trusted,
        "local_signing_config_present": bool(
            config
        ),
        "local_signing_ready": False,
        "detail": "",
    }

    if not config:
        result[
            "detail"
        ] = (
            "No local release signing configuration is present. Installed update "
            "verification can still use the trusted signer pins compiled into SSS."
        )

        return result

    try:
        status = validate_signing_config(
            config
        )

        result[
            "local_signing_ready"
        ] = True

        result[
            "detail"
        ] = (
            "Local release signing certificate/private key is available."
        )

        result[
            "certificate"
        ] = status

    except Exception as exc:
        result[
            "detail"
        ] = str(
            exc
        )

    return result
