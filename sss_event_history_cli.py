from sss_event_history import (
    format_event_time,
    get_last_unexpected_shutdown,
    read_recent_events,
)

print()
print("SUNDAY SERVICE SYSTEM — RECENT EVENT HISTORY")
print("============================================")

crash = get_last_unexpected_shutdown()

if crash:
    print()
    print("Last unexpected shutdown:")
    print("  Detected:", crash.get("detected_at", ""))
    print("  Last heartbeat:", crash.get("heartbeat_at", ""))
    print("  Recording:", crash.get("recording", "unknown"))
    print("  Streaming:", crash.get("streaming", "unknown"))
    print("  Last event:", crash.get("last_event", ""))
else:
    print()
    print("No unexpected shutdown has been recorded.")

print()
print("Recent events:")
print()

events = read_recent_events(
    limit=100,
    days=14,
)

for event in reversed(events):
    print(
        "["
        + format_event_time(event.get("timestamp", ""))
        + "] ["
        + str(event.get("category", "SYSTEM"))
        + "] ["
        + str(event.get("level", "INFO"))
        + "] "
        + str(event.get("message", ""))
    )

print()
print("This viewer is READ-ONLY.")
