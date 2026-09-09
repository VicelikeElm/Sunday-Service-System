import pyaudiowpatch as pyaudio
import numpy as np
import tempfile
import wave
import os
from faster_whisper import WhisperModel

DEVICE_INDEX = 44
CHUNK_SECONDS = 6

print("Loading Whisper model...")
model = WhisperModel(
    "small",
    device="cuda",
    compute_type="float16"
)
print("Model loaded.")

p = pyaudio.PyAudio()
device_info = p.get_device_info_by_index(DEVICE_INDEX)

RATE = int(device_info["defaultSampleRate"])
CHANNELS = int(device_info["maxInputChannels"])

print()
print(f"Listening to: {device_info['name']}")
print(f"Sample rate: {RATE}")
print(f"Channels: {CHANNELS}")
print("Press Ctrl+C to stop.")
print()

stream = p.open(
    format=pyaudio.paInt16,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    input_device_index=DEVICE_INDEX,
    frames_per_buffer=1024
)

try:
    while True:
        frames = []

        chunks_to_read = int(RATE / 1024 * CHUNK_SECONDS)

        for _ in range(chunks_to_read):
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as tmp:
            temp_path = tmp.name

        with wave.open(temp_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(RATE)
            wf.writeframes(b"".join(frames))

        segments, info = model.transcribe(
            temp_path,
            language="en",
            vad_filter=True,
            beam_size=5
        )

        text_parts = []

        for segment in segments:
            text = segment.text.strip()
            if text:
                text_parts.append(text)

        if text_parts:
            print(" ".join(text_parts))

        os.remove(temp_path)

except KeyboardInterrupt:
    print("\nStopped.")

finally:
    stream.stop_stream()
    stream.close()
    p.terminate()