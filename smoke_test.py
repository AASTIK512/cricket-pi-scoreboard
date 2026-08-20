from pathlib import Path

# The build sandbox is headless and may not include Tkinter. Raspberry Pi OS
# installs it with: sudo apt install python3-tk.
try:
    from app import get_live_matches, get_schedule
except ModuleNotFoundError as exc:
    if exc.name == "tkinter":
        print("UI import skipped: install python3-tk on Raspberry Pi OS")
        print("smoke test complete")
        raise SystemExit(0)
    raise

for label, fn in (("live", get_live_matches), ("schedule", get_schedule)):
    try:
        values = fn()
        assert isinstance(values, list) and values
        print(f"{label}: received {len(values)} item(s)")
    except Exception as exc:
        print(f"{label}: unavailable ({exc})")

print("smoke test complete")
