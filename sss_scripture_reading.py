import ctypes
import re
import sys
import time


def clean(value):
    return " ".join(
        str(value or "").split()
    )


def parse_scripture_reference(reference):
    """
    Return a simple verse progression for common single-chapter ranges.

    Examples:
      Matthew 12:43-50
      1 Corinthians 13:1-7
      John 3:16

    Cross-chapter ranges are returned as generic/manual progression because
    determining every intermediate verse would require a Bible verse-count
    database. The END READING button remains available in that case.
    """
    reference = clean(reference)

    result = {
        "reference": reference,
        "verses": [],
        "exact": False,
    }

    if not reference:
        return result

    match = re.match(
        r"^(?P<book>(?:[1-3]\s*)?[A-Za-z]+(?:\s+[A-Za-z]+)*)\s+"
        r"(?P<chapter>\d+)\s*:\s*(?P<start>\d+)"
        r"(?:\s*[-–—]\s*(?:(?P<end_chapter>\d+)\s*:\s*)?(?P<end>\d+))?$",
        reference,
        flags=re.IGNORECASE,
    )

    if not match:
        return result

    book = clean(
        match.group("book")
    )
    chapter = int(
        match.group("chapter")
    )
    start = int(
        match.group("start")
    )

    end_text = match.group(
        "end"
    )
    end_chapter_text = match.group(
        "end_chapter"
    )

    if end_text is None:
        result["verses"] = [
            f"{book} {chapter}:{start}"
        ]
        result["exact"] = True
        return result

    end = int(
        end_text
    )
    end_chapter = (
        int(
            end_chapter_text
        )
        if end_chapter_text
        else chapter
    )

    if end_chapter != chapter:
        # We know the endpoints, but not the number of verses in the
        # intervening chapter(s). Use generic NEXT VERSE controls.
        result["verses"] = [
            f"{book} {chapter}:{start}",
            f"{book} {end_chapter}:{end}",
        ]
        result["exact"] = False
        return result

    if end < start:
        return result

    # Protect the UI from malformed giant ranges.
    if (
        end
        -
        start
        >
        200
    ):
        return result

    result["verses"] = [
        f"{book} {chapter}:{verse}"
        for verse in range(
            start,
            end + 1,
        )
    ]
    result["exact"] = True

    return result


def _require_windows():
    if sys.platform != "win32":
        raise RuntimeError(
            "This control is only available on the Windows church PC."
        )


def send_key_chord(
    virtual_keys,
    *,
    hold_seconds=0.06
):
    _require_windows()

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002

    keys = [
        int(
            key
        )
        for key in virtual_keys
    ]

    try:
        for key in keys:
            user32.keybd_event(
                key,
                0,
                0,
                0,
            )

        time.sleep(
            max(
                0.01,
                float(
                    hold_seconds
                )
            )
        )

        for key in reversed(
            keys
        ):
            user32.keybd_event(
                key,
                0,
                KEYEVENTF_KEYUP,
                0,
            )

        return True

    except Exception as exc:
        raise RuntimeError(
            f"Could not send keyboard shortcut: {exc}"
        ) from exc


def send_webcam_tp_to_preview():
    # Ctrl + F15
    VK_CONTROL = 0x11
    VK_F15 = 0x7E

    return send_key_chord(
        [
            VK_CONTROL,
            VK_F15,
        ]
    )


def send_webcam_only():
    # Ctrl + F13
    # User's OBS hotkey for the normal "webcam only" view.
    VK_CONTROL = 0x11
    VK_F13 = 0x7C

    return send_key_chord(
        [
            VK_CONTROL,
            VK_F13,
        ],
        hold_seconds=0.08,
    )


def send_studio_transition():
    # User's OBS transition hotkey is Ctrl + Shift.
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10

    return send_key_chord(
        [
            VK_CONTROL,
            VK_SHIFT,
        ],
        hold_seconds=0.08,
    )


class MIDIOUTCAPSW(
    ctypes.Structure
):
    _fields_ = [
        ("wMid", ctypes.c_ushort),
        ("wPid", ctypes.c_ushort),
        ("vDriverVersion", ctypes.c_uint),
        ("szPname", ctypes.c_wchar * 32),
        ("wTechnology", ctypes.c_ushort),
        ("wVoices", ctypes.c_ushort),
        ("wNotes", ctypes.c_ushort),
        ("wChannelMask", ctypes.c_ushort),
        ("dwSupport", ctypes.c_uint),
    ]


def _winmm():
    _require_windows()

    winmm = ctypes.windll.winmm

    try:
        winmm.midiOutGetNumDevs.restype = ctypes.c_uint

        winmm.midiOutGetDevCapsW.argtypes = [
            ctypes.c_size_t,
            ctypes.POINTER(
                MIDIOUTCAPSW
            ),
            ctypes.c_uint,
        ]
        winmm.midiOutGetDevCapsW.restype = ctypes.c_uint

        winmm.midiOutOpen.argtypes = [
            ctypes.POINTER(
                ctypes.c_void_p
            ),
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint,
        ]
        winmm.midiOutOpen.restype = ctypes.c_uint

        winmm.midiOutShortMsg.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
        ]
        winmm.midiOutShortMsg.restype = ctypes.c_uint

        winmm.midiOutReset.argtypes = [
            ctypes.c_void_p,
        ]
        winmm.midiOutReset.restype = ctypes.c_uint

        winmm.midiOutClose.argtypes = [
            ctypes.c_void_p,
        ]
        winmm.midiOutClose.restype = ctypes.c_uint

    except Exception:
        # The functions can still be called without explicit argtypes on
        # normal Windows systems. This keeps the helper tolerant of unusual
        # ctypes/winmm wrappers.
        pass

    return winmm


def list_midi_output_ports():
    if sys.platform != "win32":
        return []

    winmm = _winmm()

    count = int(
        winmm.midiOutGetNumDevs()
    )

    ports = []

    for device_id in range(
        count
    ):
        caps = MIDIOUTCAPSW()

        result = winmm.midiOutGetDevCapsW(
            device_id,
            ctypes.byref(
                caps
            ),
            ctypes.sizeof(
                caps
            ),
        )

        if result == 0:
            ports.append(
                (
                    device_id,
                    str(
                        caps.szPname
                    ),
                )
            )

    return ports


def find_midi_output_port(
    preferred_name="loopMIDI Port"
):
    preferred = clean(
        preferred_name
    ).lower()

    ports = list_midi_output_ports()

    for device_id, name in ports:
        if name.lower() == preferred:
            return (
                device_id,
                name,
            )

    for device_id, name in ports:
        if preferred in name.lower():
            return (
                device_id,
                name,
            )

    return None


def midi_port_available(
    preferred_name="loopMIDI Port"
):
    found = find_midi_output_port(
        preferred_name
    )

    if found:
        return (
            True,
            found[1],
        )

    names = [
        name
        for _device_id, name in list_midi_output_ports()
    ]

    return (
        False,
        (
            "loopMIDI Port not found"
            if not names
            else
            (
                "loopMIDI Port not found; available: "
                +
                ", ".join(
                    names
                )
            )
        ),
    )


def send_midi_note(
    *,
    port_name="Presenter",
    channel=10,
    note=60,
    velocity=126,
    settle_seconds=0.10
):
    """
    Send exactly ONE Presenter command event.

    This intentionally matches the user's working Stream Deck behavior:
      - Port: Presenter
      - Channel: 10
      - Velocity: 126
      - NEXT: Note 60
      - PREVIOUS: Note 62

    IMPORTANT:
    SSS sends ONLY MIDI Note On.
    It does NOT send Note Off / release.
    """
    _require_windows()

    found = find_midi_output_port(
        port_name
    )

    if not found:
        raise RuntimeError(
            f"MIDI output '{port_name}' was not found."
        )

    device_id, actual_name = found

    winmm = _winmm()
    handle = ctypes.c_void_p()

    result = winmm.midiOutOpen(
        ctypes.byref(
            handle
        ),
        device_id,
        0,
        0,
        0,
    )

    if result != 0:
        raise RuntimeError(
            f"Could not open MIDI output '{actual_name}' (error {result})."
        )

    try:
        channel_zero = max(
            0,
            min(
                15,
                int(channel) - 1
            )
        )

        note = max(
            0,
            min(
                127,
                int(note)
            )
        )

        velocity = max(
            1,
            min(
                127,
                int(velocity)
            )
        )

        # MIDI Note On:
        # status 0x90 + zero-based channel
        # data1 = note
        # data2 = velocity
        message = (
            (0x90 | channel_zero)
            |
            (note << 8)
            |
            (velocity << 16)
        )

        result = winmm.midiOutShortMsg(
            handle,
            message,
        )

        if result != 0:
            raise RuntimeError(
                f"MIDI Note On failed (error {result})."
            )

        # Briefly keep the WinMM handle alive so loopMIDI can deliver the
        # single event. No Note Off and no midiOutReset are sent.
        time.sleep(
            max(
                0.03,
                float(settle_seconds)
            )
        )

        return actual_name

    finally:
        try:
            winmm.midiOutClose(
                handle
            )
        except Exception:
            pass


def presenter_next(
    *,
    port_name="loopMIDI Port",
    channel=10,
    note=60,
    velocity=126
):
    return send_midi_note(
        port_name=port_name,
        channel=channel,
        note=note,
        velocity=velocity,
    )


def presenter_back(
    *,
    port_name="loopMIDI Port",
    channel=10,
    note=62,
    velocity=126
):
    return send_midi_note(
        port_name=port_name,
        channel=channel,
        note=note,
        velocity=velocity,
    )
