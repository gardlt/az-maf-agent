"""Synthetic containment fixture: no tools, secrets, model calls, or user data."""
import json
import signal
import time

# Deliberately does not implement application policy polling or run cancellation.
# Platform termination is still allowed; SIGTERM is not intercepted.
print(json.dumps({"event": "containment_fixture_started"}), flush=True)
while True:
    print(json.dumps({"event": "containment_fixture_tick"}), flush=True)
    time.sleep(5)
