import sounddevice as sd
import numpy as np

DEVICE = 1

device_info = sd.query_devices(DEVICE)
CHANNELS = int(device_info["max_input_channels"])
SAMPLERATE = int(device_info["default_samplerate"])

print("TASCAM channel tester")
print(f"Device: {device_info['name']}")
print(f"Channels: {CHANNELS}")
print(f"Sample rate: {SAMPLERATE}")
print()
print("Speak into the pastor microphone.")
print("Press Ctrl+C to stop.")
print()

def callback(indata, frames, time, status):
    if status:
        print("\nAudio status:", status)

    levels = np.sqrt(np.mean(indata ** 2, axis=0))
    db = 20 * np.log10(levels + 1e-10)

    output = []

    for i, level in enumerate(db):
        output.append(f"CH{i+1}:{level:6.1f}")

    print("\r" + "  ".join(output), end="", flush=True)

try:
    with sd.InputStream(
        device=DEVICE,
        channels=CHANNELS,
        samplerate=SAMPLERATE,
        dtype="float32",
        callback=callback
    ):
        while True:
            sd.sleep(100)

except KeyboardInterrupt:
    print("\n\nStopped.")