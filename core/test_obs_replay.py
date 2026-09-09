import getpass
import obsws_python as obs

HOST = "localhost"
PORT = 4455

password = getpass.getpass("OBS WebSocket password: ")

print("Connecting to OBS...")

client = obs.ReqClient(
    host=HOST,
    port=PORT,
    password=password,
    timeout=5
)

print("Connected.")

status = client.get_replay_buffer_status()

if not status.output_active:
    print("Replay Buffer is not running.")
    print("Starting Replay Buffer...")
    client.start_replay_buffer()
else:
    print("Replay Buffer is already running.")

input("\nPress ENTER to save the current Replay Buffer...")

client.save_replay_buffer()

print("Replay saved.")