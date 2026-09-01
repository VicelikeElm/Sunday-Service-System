import sys

from sss_scripture_reading import (
    send_midi_note,
)

mode = (
    sys.argv[1].strip().lower()
    if len(sys.argv) > 1
    else "next"
)

if mode in {"next", "60"}:
    note = 60
    label = "NEXT VERSE"
elif mode in {"back", "previous", "prev", "62"}:
    note = 62
    label = "PREVIOUS VERSE"
else:
    raise SystemExit(
        "Use: next or back"
    )

print()
print("Presenter exact Stream Deck MIDI test")
print("====================================")
print("Action:    ", label)
print("Port:       Presenter")
print("Channel:    10")
print("Note:      ", note)
print("Velocity:   126")
print("MIDI event: Note On ONLY")
print("Note Off:   NONE")
print()

actual = send_midi_note(
    port_name="Presenter",
    channel=10,
    note=note,
    velocity=126,
)

print("Sent through:", actual)
print("Only one MIDI event was sent.")
