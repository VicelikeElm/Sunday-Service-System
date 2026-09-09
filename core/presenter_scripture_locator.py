import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path


BASE = Path(r"C:\Church\SermonAI")
LOCATOR_PS1 = BASE / "presenter_scripture_locator.ps1"

DEFAULT_CONTROL_HOST = "127.0.0.1"
DEFAULT_CONTROL_PORT = 9223


def _normalize_reference(reference):
    return " ".join(
        str(reference or "")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .split()
    )


def _read_json_url(url, *, timeout=1.5):
    with urllib.request.urlopen(
        url,
        timeout=float(timeout),
    ) as response:
        return json.loads(
            response.read().decode(
                "utf-8",
                errors="replace",
            )
        )


def _cdp_targets(
    *,
    host=DEFAULT_CONTROL_HOST,
    port=DEFAULT_CONTROL_PORT
):
    last_error = None

    for url in (
        f"http://{host}:{int(port)}/json/list",
        f"http://{host}:{int(port)}/json",
    ):
        try:
            payload = _read_json_url(url)

            if isinstance(payload, list):
                return payload

        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    return []


def _cdp_call(ws, message_id, method, params=None):
    request = {
        "id": int(message_id),
        "method": str(method),
    }

    if params:
        request["params"] = params

    ws.send(json.dumps(request))

    deadline = time.time() + 5

    while time.time() < deadline:
        payload = json.loads(ws.recv())

        if payload.get("id") == int(message_id):
            return payload

    raise RuntimeError("Presenter control timed out.")


def _evaluate(ws, message_id, expression):
    payload = _cdp_call(
        ws,
        message_id,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
            "userGesture": True,
        },
    )

    if "error" in payload:
        raise RuntimeError(str(payload["error"]))

    result = payload.get(
        "result",
        {}
    ).get(
        "result",
        {}
    )

    if result.get("subtype") == "error":
        raise RuntimeError(
            str(
                result.get(
                    "description",
                    "Presenter JavaScript error."
                )
            )
        )

    return result.get("value")


def _scripture_target_js(reference):
    wanted_json = json.dumps(
        _normalize_reference(reference)
    )

    js = r'''
(() => {
    const wantedRaw = __WANTED__;

    const norm = (value) => String(value || "")
        .toLowerCase()
        .replace(/[\u2013\u2014\u2212]/g, "-")
        .replace(/\s+/g, " ")
        .trim();

    const wanted = norm(wantedRaw);

    const visible = (el) => {
        try {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();

            return (
                style.display !== "none" &&
                style.visibility !== "hidden" &&
                Number(style.opacity || "1") !== 0 &&
                rect.width > 0 &&
                rect.height > 0
            );
        } catch (e) {
            return false;
        }
    };

    const textFor = (el) => norm(
        el.innerText ||
        el.textContent ||
        ""
    );

    const clickableAncestor = (el) => {
        let current = el;

        for (
            let depth = 0;
            depth < 8 && current;
            depth++, current = current.parentElement
        ) {
            try {
                const tag = String(
                    current.tagName || ""
                ).toLowerCase();

                const role = norm(
                    current.getAttribute &&
                    current.getAttribute("role")
                );

                const style = window.getComputedStyle(
                    current
                );

                if (
                    tag === "button" ||
                    tag === "a" ||
                    role === "button" ||
                    role === "option" ||
                    role === "listitem" ||
                    role === "treeitem" ||
                    role === "menuitem" ||
                    current.onclick ||
                    current.tabIndex >= 0 ||
                    style.cursor === "pointer"
                ) {
                    return current;
                }
            } catch (e) {}
        }

        return el;
    };

    const all = Array.from(
        document.querySelectorAll("body *")
    );

    const scored = [];

    for (const el of all) {
        const text = textFor(el);

        if (!text) {
            continue;
        }

        let score = -1;

        if (text === wanted) {
            score = 1000;
        } else if (
            text.startsWith(wanted + " ") ||
            text.startsWith(wanted + "(")
        ) {
            score = 900;
        } else if (text.includes(wanted)) {
            score = 650;
        } else {
            continue;
        }

        if (visible(el)) {
            score += 120;
        }

        if (
            String(el.innerText || "").trim().length
            <=
            wantedRaw.length + 20
        ) {
            score += 60;
        }

        const clickEl = clickableAncestor(el);

        if (clickEl !== el) {
            score += 40;
        }

        try {
            const rect = clickEl.getBoundingClientRect();

            // Prefer the matching service item in Presenter's left sidebar.
            if (rect.left < 420) {
                score += 180;
            }
        } catch (e) {}

        scored.push({
            el,
            clickEl,
            text,
            score,
        });
    }

    scored.sort(
        (a, b) => b.score - a.score
    );

    if (!scored.length) {
        const sermonCandidates = all.filter(
            (el) => (
                textFor(el) === "sermon" &&
                visible(el)
            )
        );

        if (sermonCandidates.length) {
            const sermonClick = clickableAncestor(
                sermonCandidates[0]
            );

            try {
                sermonClick.scrollIntoView({
                    block: "center",
                    inline: "nearest",
                });

                const sermonRect = sermonClick.getBoundingClientRect();

                return {
                    success: false,
                    retry: true,
                    action: "expand-sermon",
                    x: sermonRect.left + sermonRect.width / 2,
                    y: sermonRect.top + sermonRect.height / 2,
                    reason: "The Sermon section needs to be expanded.",
                };
            } catch (e) {}
        }

        return {
            success: false,
            retry: false,
            reason: "Scripture text was not found in the Presenter DOM.",
        };
    }

    const chosen = scored[0];
    const target = chosen.clickEl || chosen.el;

    try {
        target.scrollIntoView({
            block: "center",
            inline: "nearest",
        });
    } catch (e) {}

    const rect = target.getBoundingClientRect();

    return {
        success: true,
        retry: false,
        method: "Presenter native CDP click",
        found_text: chosen.text,
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height / 2,
        width: rect.width,
        height: rect.height,
        clicked_tag: String(
            target.tagName || ""
        ),
        clicked_role: String(
            target.getAttribute &&
            target.getAttribute("role") ||
            ""
        ),
    };
})()
'''

    return js.replace(
        "__WANTED__",
        wanted_json,
    )


def _dispatch_real_click(
    ws,
    start_id,
    x,
    y
):
    """Send a real Chromium mouse click, not JavaScript element.click()."""
    x = float(x)
    y = float(y)

    _cdp_call(
        ws,
        start_id,
        "Input.dispatchMouseEvent",
        {
            "type": "mouseMoved",
            "x": x,
            "y": y,
            "button": "none",
        },
    )

    _cdp_call(
        ws,
        start_id + 1,
        "Input.dispatchMouseEvent",
        {
            "type": "mousePressed",
            "x": x,
            "y": y,
            "button": "left",
            "buttons": 1,
            "clickCount": 1,
        },
    )

    time.sleep(0.06)

    _cdp_call(
        ws,
        start_id + 2,
        "Input.dispatchMouseEvent",
        {
            "type": "mouseReleased",
            "x": x,
            "y": y,
            "button": "left",
            "buttons": 0,
            "clickCount": 1,
        },
    )


def _cue_via_cdp(
    reference,
    *,
    timeout=8,
    host=DEFAULT_CONTROL_HOST,
    port=DEFAULT_CONTROL_PORT
):
    try:
        import websocket
    except Exception as exc:
        return {
            "success": False,
            "method": "Presenter DOM",
            "reason": (
                "Python websocket-client is unavailable: "
                + str(exc)
            ),
            "reference": reference,
        }

    try:
        targets = _cdp_targets(
            host=host,
            port=port,
        )
    except Exception as exc:
        return {
            "success": False,
            "method": "Presenter DOM",
            "reason": (
                "Presenter SSS control channel is not available. "
                + str(exc)
            ),
            "reference": reference,
        }

    page_targets = [
        target
        for target in targets
        if (
            str(target.get("type", "")).lower()
            in {"page", "webview"}
            and target.get("webSocketDebuggerUrl")
        )
    ]

    if not page_targets:
        return {
            "success": False,
            "method": "Presenter DOM",
            "reason": (
                "Presenter control is open, but no page target was found."
            ),
            "reference": reference,
        }

    last_reason = "Scripture text was not found in Presenter."
    deadline = time.time() + float(timeout)

    for target in page_targets:
        if time.time() >= deadline:
            break

        ws_url = str(
            target.get("webSocketDebuggerUrl")
        )

        try:
            ws = websocket.create_connection(
                ws_url,
                timeout=min(
                    4.0,
                    max(
                        1.0,
                        deadline - time.time()
                    )
                ),
                origin=f"http://{host}:{int(port)}",
            )
        except Exception as exc:
            last_reason = str(exc)
            continue

        try:
            _cdp_call(
                ws,
                1,
                "Runtime.enable",
            )

            result = _evaluate(
                ws,
                2,
                _scripture_target_js(reference),
            )

            if isinstance(result, dict):
                if (
                    result.get("success")
                    and result.get("x") is not None
                    and result.get("y") is not None
                ):
                    _dispatch_real_click(
                        ws,
                        30,
                        result["x"],
                        result["y"],
                    )

                    time.sleep(0.35)

                    return {
                        "success": True,
                        "method": "Presenter native CDP click",
                        "reference": reference,
                        "found_name": str(
                            result.get(
                                "found_text",
                                reference
                            )
                        ),
                        "target_title": str(
                            target.get("title", "")
                        ),
                        "click_x": round(float(result["x"]), 1),
                        "click_y": round(float(result["y"]), 1),
                    }

                last_reason = str(
                    result.get(
                        "reason",
                        last_reason
                    )
                )

                if (
                    result.get("retry")
                    and result.get("action") == "expand-sermon"
                    and result.get("x") is not None
                    and result.get("y") is not None
                ):
                    _dispatch_real_click(
                        ws,
                        10,
                        result["x"],
                        result["y"],
                    )

                    time.sleep(0.45)

                    retry = _evaluate(
                        ws,
                        20,
                        _scripture_target_js(reference),
                    )

                    if (
                        isinstance(retry, dict)
                        and retry.get("success")
                        and retry.get("x") is not None
                        and retry.get("y") is not None
                    ):
                        _dispatch_real_click(
                            ws,
                            40,
                            retry["x"],
                            retry["y"],
                        )

                        time.sleep(0.35)

                        return {
                            "success": True,
                            "method": "Presenter native CDP click",
                            "reference": reference,
                            "found_name": str(
                                retry.get(
                                    "found_text",
                                    reference
                                )
                            ),
                            "target_title": str(
                                target.get("title", "")
                            ),
                            "click_x": round(float(retry["x"]), 1),
                            "click_y": round(float(retry["y"]), 1),
                        }

                    if isinstance(retry, dict):
                        last_reason = str(
                            retry.get(
                                "reason",
                                last_reason
                            )
                        )

        except Exception as exc:
            last_reason = str(exc)

        finally:
            try:
                ws.close()
            except Exception:
                pass

    return {
        "success": False,
        "method": "Presenter DOM",
        "reason": last_reason,
        "reference": reference,
    }


def _cue_via_uia_fallback(
    reference,
    *,
    timeout=5
):
    if not LOCATOR_PS1.exists():
        return {
            "success": False,
            "reason": "UI Automation fallback is missing.",
            "reference": reference,
        }

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
                str(LOCATOR_PS1),
                "-Reference",
                reference,
            ],
            cwd=BASE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=float(timeout),
            creationflags=creationflags,
        )
    except Exception as exc:
        return {
            "success": False,
            "reason": str(exc),
            "reference": reference,
        }

    output = (cp.stdout or "").strip()
    payload = None

    for line in reversed(output.splitlines()):
        line = line.strip()

        if not (
            line.startswith("{")
            and line.endswith("}")
        ):
            continue

        try:
            payload = json.loads(line)
            break
        except Exception:
            continue

    if not isinstance(payload, dict):
        return {
            "success": False,
            "reason": (
                output
                or (cp.stderr or "").strip()
                or "UI Automation fallback failed."
            ),
            "reference": reference,
        }

    payload.setdefault(
        "success",
        cp.returncode == 0,
    )
    payload.setdefault(
        "reference",
        reference,
    )

    return payload


def cue_presenter_scripture(
    reference,
    *,
    timeout=8
):
    reference = _normalize_reference(reference)

    if not reference:
        return {
            "success": False,
            "reason": "Scripture reference is blank.",
            "reference": "",
        }

    cdp = _cue_via_cdp(
        reference,
        timeout=timeout,
    )

    if cdp.get("success"):
        return cdp

    uia = _cue_via_uia_fallback(
        reference,
        timeout=min(
            5,
            float(timeout),
        ),
    )

    if uia.get("success"):
        return uia

    return {
        "success": False,
        "reference": reference,
        "method": "Presenter DOM + UIA fallback",
        "reason": (
            str(cdp.get("reason", ""))
            + " | UIA: "
            + str(uia.get("reason", ""))
        ).strip(),
    }
