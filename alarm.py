#!/usr/bin/env python3
"""
Alarm Clock CLI
================
Commands:
  python alarm.py set HH:MM [--label "Wake up"]   # Set a new alarm
  python alarm.py list                              # Show all alarms
  python alarm.py cancel HH:MM                     # Delete an alarm
  python alarm.py run                               # Start the clock
"""

import argparse
import json
import os
import sys
import time
import warnings
from datetime import datetime, timedelta

ALARMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarms.json")


# ──────────────────────────────────────────────
#  Storage
# ──────────────────────────────────────────────

def load_alarms() -> list:
    """Read alarms from JSON file. Returns empty list if file missing."""
    if not os.path.exists(ALARMS_FILE):
        return []
    try:
        with open(ALARMS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print("⚠️  Could not read alarms file. Starting fresh.")
        return []


def save_alarms(alarms: list) -> None:
    """Write alarms list to JSON file."""
    try:
        with open(ALARMS_FILE, "w") as f:
            json.dump(alarms, f, indent=2)
    except IOError as e:
        print(f"❌  Could not save alarms: {e}")
        sys.exit(1)


# ──────────────────────────────────────────────
#  Time validation
# ──────────────────────────────────────────────

def parse_time(time_str: str) -> str:
    """
    Accept multiple formats and normalise to HH:MM (24-hour).
    Supported: 07:30 / 7:30 / 07:30AM / 7:30 PM
    """
    for fmt in ("%H:%M", "%I:%M%p", "%I:%M %p", "%I:%M%P", "%I:%M %P"):
        try:
            return datetime.strptime(time_str.strip(), fmt).strftime("%H:%M")
        except ValueError:
            continue
    print(f"❌  Invalid time '{time_str}'. Use 24-hour HH:MM format, e.g. 07:30 or 19:00")
    sys.exit(1)


# ──────────────────────────────────────────────
#  Commands
# ──────────────────────────────────────────────

def cmd_set(args) -> None:
    """Set a new alarm."""
    time_str = parse_time(args.time)
    label = args.label.strip() if args.label else "Alarm"
    print(time_str, label)
    alarms = load_alarms()

    # Prevent duplicate at same time
    for alarm in alarms:
        if alarm["time"] == time_str:
            print(f"⚠️  Alarm already exists at {time_str} ('{alarm['label']}').")
            print("    Use 'cancel' first if you want to replace it.")
            sys.exit(1)

    alarms.append({
        "time": time_str,
        "label": label,
        "enabled": True,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    # Keep alarms sorted by time
    alarms.sort(key=lambda a: a["time"])
    save_alarms(alarms)
    print(f"✅  Alarm set for {time_str} — '{label}'")


def cmd_list(args) -> None:
    """Display all alarms in a table."""
    alarms = load_alarms()
    if not alarms:
        print("📭  No alarms set.")
        print("    Try: python alarm.py set 07:30 --label \"Wake up\"")
        return

    now = datetime.now().strftime("%H:%M")
    print(f"\n{'#':<4} {'Time':<8} {'Label':<30} {'Status':<10}")
    print("─" * 56)
    alarms = sorted(alarms, key=lambda a: a["time"])
    for i, alarm in enumerate(alarms, 1):
        status = "ON" if alarm.get("enabled", True) else "OFF"
        upcoming = " ← next" if alarm["time"] > now and alarm.get("enabled", True) else ""
        print(f"{i:<4} {alarm['time']:<8} {alarm['label']:<30} {status}{upcoming}")
    print()

def cancel(time_str):

    alarms = load_alarms()
    new_alarms = []
    for a in alarms:
        if a["time"] == time_str:
            a["enabled"] = False
        new_alarms.append(a)

    save_alarms(new_alarms)
    print(f"🗑️  Alarm at {time_str} cancelled.")



def cmd_cancel(args) -> None:
    """Remove an alarm by time """
    time_str = parse_time(args.time)
    cancel(time_str)



def cmd_delete(args) -> None:
    """Remove an alarm by time."""

    if args.time == None:
        save_alarms([])
        print("Successfully removed all alarms.")
        sys.exit(0)

    time_str = parse_time(args.time)
    alarms = load_alarms()

    new_alarms = [a for a in alarms if a["time"] != time_str]
    if len(new_alarms) == len(alarms):
        print(f"❌  No alarm found at {time_str}.")
        print("    Use 'list' to see all alarms.")
        sys.exit(1)

    save_alarms(new_alarms)
    print(f"🗑️  Alarm at {time_str} deleted.")

def run():

    print("🕐  Alarm clock is running. Press Ctrl+C to stop.")
    print(cmd_list(list))
    print("(Use CTRL + C for another terminal to add/cancel alarms)\n")

    triggered_today: set = set()
    last_minute = None

    try:
        while True:
            now = datetime.now()
            current_minute = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")

            # Only check alarms once per minute
            if current_minute != last_minute:
                last_minute = current_minute
                alarms = load_alarms()

                for alarm in alarms:
                    if not alarm.get("enabled", True):
                        continue

                    key = f"{current_date}_{alarm['time']}"
                    if alarm["time"] == current_minute and key not in triggered_today:
                        triggered_today.add(key)
                        trigger_alarm(alarm)

                # Flush old keys at midnight to avoid memory growth
                triggered_today = {
                    k for k in triggered_today
                    if k.startswith(current_date)
                }

                # Show a subtle heartbeat so user knows it's alive
                print(f"  ⏱  Watching... {current_minute}  ({len(alarms)} alarm(s) set)", end="\r")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n👋  Alarm clock stopped.")


def cmd_run(args) -> None:
    """
    Start the alarm daemon.
    - Checks time every second (for accuracy)
    - Reloads alarms.json each minute (picks up live changes)
    - Each alarm fires only once per calendar day
    """
    run()

# ──────────────────────────────────────────────
#  Alarm snooze
# ──────────────────────────────────────────────

def alarm_update(time):
    """Update alarm time"""

    new_alarms = []
    alarms = load_alarms()
    for alarm in alarms:
        if alarm["time"] == time:
            new_time = (
                    datetime.strptime(time, "%H:%M") + timedelta(minutes=5)
            ).strftime("%H:%M")
            alarm["time"] = new_time
        new_alarms.append(alarm)
    save_alarms(new_alarms)

def alarm_snooze(time: str) -> None:
    """Set Snooze and Update Alarm and Pass to trigger"""

    print(" Type 'Yes' for snooze or 'No' for cancel ")
    response = input()
    if len(response) != 0:
        if response.lower() == "yes":
            alarm_update(time)
            run()

        elif response.lower() == "no":
            cancel(time)
        sys.exit(0)

# ──────────────────────────────────────────────
#  Alarm trigger
# ──────────────────────────────────────────────

def trigger_alarm(alarm: dict) -> None:
    """Print a loud notification and ring the terminal bell."""
    label    = alarm["label"]
    time_str = alarm["time"]

    border = "═" * 50
    print(f"\n{border}")
    print(f"  🔔  ALARM  ──  {time_str}  ──  {label}")
    print(f"{border}")
    print("  Press Ctrl+C to stop the alarm clock.\n")

    # Ring bell 5 times, 1 second apart
    for _ in range(5):
        sys.stdout.write("\a")
        sys.stdout.flush()
        time.sleep(1)
        alarm_snooze(time_str)


# ──────────────────────────────────────────────
#  CLI entry point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="alarm",
        description="⏰  Command-line alarm clock",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python alarm.py set 07:30
  python alarm.py set 09:00 --label "Stand-up"
  python alarm.py list
  python alarm.py delete 07:30
  python alarm.py run
        """
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # -- 1.set
    p_set = subparsers.add_parser("set", help="Set a new alarm")
    p_set.add_argument("time",           help="Time in HH:MM format (24-hour)")
    p_set.add_argument("--label", "-l",  help="Label for the alarm", default="Alarm")
    p_set.set_defaults(func=cmd_set)

    # -- 2.list
    p_list = subparsers.add_parser("list", help="List all alarms")
    p_list.set_defaults(func=cmd_list)

    # -- 3. delete
    p_delete = subparsers.add_parser("delete", help="Delete an alarm by time")
    p_delete.add_argument("time", nargs="?", help="Time of the alarm to delete. If omitted, all alarms will be deleted.")

    p_delete.set_defaults(func=cmd_delete)

    # -- 4. cancel
    p_cancel = subparsers.add_parser("cancel", help="Cancel an alarm by time")
    p_cancel.add_argument("time", help="Time of the alarm to cancel")
    p_cancel.set_defaults(func=cmd_cancel)

    # -- 5. run
    #    1. includes snooze & cancel
    p_run = subparsers.add_parser("run", help="Start the alarm clock daemon")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
