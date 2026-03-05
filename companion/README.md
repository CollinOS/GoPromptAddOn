# ClaudeGuard Companion Script

Monitors Claude Code's process activity and writes status to the WoW addon's `CompanionData.lua` file. On state transitions, sends `/reload` keystrokes to WoW.

## Quick Start

```bash
pip install -r requirements.txt
# Edit config.json with your WoW path and account name
python -m companion.claude_monitor --debug
```

## How It Works

1. Uses `psutil` to find Claude Code processes by name/cmdline
2. Measures CPU usage (process + children) over a sampling interval
3. Applies a grace-period heuristic to determine idle vs. working status
4. Writes status to `<wow_path>/Interface/AddOns/ClaudeGuard/CompanionData.lua`
5. On state transitions, sends keystrokes to WoW to trigger `/reload`

## Keystroke Sending

- **Windows**: Uses `ctypes` `SendInput` (no dependencies beyond stdlib)
- **Linux**: Uses `xdotool` (`sudo apt install xdotool`)

## Running Tests

```bash
python -m pytest companion/tests/ -v
```
