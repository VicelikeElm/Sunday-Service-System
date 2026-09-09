from faster_whisper import WhisperModel

print("Loading Faster-Whisper on GPU...")

model = WhisperModel(
    "small",
    device="cuda",
    compute_type="float16"
)

print()
print("SUCCESS!")
print("Faster-Whisper loaded on the NVIDIA GPU.")
print("Your RTX 2070 Super is ready for transcription.")