# ⏰ Alarm Clock CLI

A simple, no-dependency command-line alarm clock written in Python.

## Features

- Set alarms with an optional label
- List all scheduled alarms
- Cancel alarms by time
- Live daemon mode that watches and triggers alarms
- Terminal bell notification when alarm fires
- Duplicate alarm prevention
- Alarms persist between sessions (stored in `alarms.json`)

## Requirements

- Python 3.7+
- No third-party packages needed

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/alarm-clock.git
cd alarm-clock
```

## Usage

### Set an alarm
```bash
python alarm.py set 07:30
python alarm.py set 09:00 --label "Stand-up meeting"
python alarm.py set 13:30 -l "Lunch"
```

### List all alarms
```bash
python alarm.py list
```

Output:
```
#    Time     Label                          Status
────────────────────────────────────────────────────
1    07:30    Alarm                          ✅ on
2    09:00    Stand-up meeting               ✅ on
3    13:30    Lunch                          ✅ on
```

### Cancel an alarm
```bash
python alarm.py cancel 07:30
```

### Run the alarm clock
```bash
python alarm.py run
```

Keep this running in a terminal. When an alarm time is reached, it prints a notification and rings the terminal bell.

```
════════════════════════════════════════════
  🔔  ALARM — 07:30  |  Wake up
════════════════════════════════════════════
```

Press `Ctrl+C` to stop.

## How it works

- Alarms are saved in `alarms.json` in the same directory
- The `run` command polls every minute and triggers any matching alarms
- Alarms reload live, so you can add/cancel alarms while `run` is active
- Each alarm fires only once per day

## Engineering Decisions

| Decision | Rationale |
|---|---|
| JSON file for storage | No database needed; simple, human-readable, meets the spec |
| Poll every minute | Alarms are minute-precise; sleeping to next full minute is efficient |
| Reload alarms each tick | Allows live add/cancel without restarting the daemon |
| Terminal bell (`\a`) | Zero dependencies; works on Linux/Mac/Windows terminals |
| Separate `run` command | Keeps CLI composable; daemon is opt-in |
| Duplicate prevention | Prevents confusing double-triggers at the same minute |

## Project Structure

```
alarm-clock/
├── alarm.py       # All logic: CLI parsing, storage, daemon, trigger
├── alarms.json    # Auto-created when first alarm is set
└── README.md
```
