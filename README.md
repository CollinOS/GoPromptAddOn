# ClaudeGuard

**Stop playing WoW when Claude Code is waiting for a prompt.** ClaudeGuard monitors Claude Code's process activity and blocks your gameplay with a full-screen overlay when Claude is idle. When Claude is working, the overlay dismisses automatically.

<!-- Screenshot placeholder: ![ClaudeGuard blocker overlay](docs/screenshot.png) -->

## How It Works

ClaudeGuard has two parts:

1. **Companion Script** (Python) — Runs on your desktop, monitors Claude Code's CPU usage to determine if it's working or idle, and writes status to a Lua file in the WoW addon directory. On state transitions, it sends a `/reload` command to WoW.

2. **WoW Addon** (Lua) — Reads the status on load. If Claude is idle, it shows a full-screen blocker overlay. If you're in combat, a dungeon, or PvP, it shows a non-blocking notification instead.

## Prerequisites

- Python 3.10+ with `psutil`
- World of Warcraft (Classic Anniversary Edition or TBC Classic)
- Windows or Linux

## Installation

### 1. Install the WoW Addon

Copy the `addon/ClaudeGuard` folder to your WoW AddOns directory:

**Windows:**
```
xcopy /E /I addon\ClaudeGuard "C:\Program Files (x86)\World of Warcraft\_anniversary_\Interface\AddOns\ClaudeGuard"
```

**Linux:**
```
cp -r addon/ClaudeGuard ~/.wine/drive_c/.../Interface/AddOns/ClaudeGuard
```

### 2. Install the Companion Script

```bash
cd companion
pip install -r requirements.txt
```

### 3. Configure

Edit `companion/config.json`:

```json
{
  "wow_path": "C:/Program Files (x86)/World of Warcraft/_anniversary_",
  "account_name": "YOUR_ACCOUNT",
  "poll_interval_seconds": 2,
  "cpu_threshold_percent": 3.0,
  "idle_grace_seconds": 5,
  "reload_delay_seconds": 10
}
```

**Finding your account name:** Look in `<wow_path>/WTF/Account/` — the folder name there is your account name.

### 4. Run

```bash
python -m companion.claude_monitor --debug
```

Then launch WoW. The addon will appear in your AddOns list at character select.

## Configuration Reference

| Field | Type | Default | Description |
|---|---|---|---|
| `wow_path` | string | — | Path to your WoW installation directory |
| `account_name` | string | — | WoW account folder name (from `WTF/Account/`) |
| `poll_interval_seconds` | number | 2 | How often to check Claude's CPU usage |
| `cpu_threshold_percent` | number | 3.0 | CPU% above which Claude is considered "working" |
| `idle_grace_seconds` | number | 5 | Seconds of low CPU before transitioning to "idle" |
| `reload_delay_seconds` | number | 10 | Delay before sending /reload on working→idle transitions |

## Companion Script Flags

| Flag | Description |
|---|---|
| `--debug` | Enable debug-level logging |
| `--config PATH` | Use a custom config.json path |
| `--dry-run` | Run without sending keystrokes to WoW |
| `--version` | Print version and exit |

## Slash Commands

| Command | Description |
|---|---|
| `/cg` | Compact status summary |
| `/cg status` | Detailed status info |
| `/cg snooze [seconds]` | Snooze blocker (default 120s, max 300s, 3 uses per session) |
| `/cg reset` | Reset snooze counter |
| `/cg sound on\|off` | Toggle sound effects |
| `/cg disable` | Disable until next login/reload |
| `/cg enable` | Re-enable after disable |
| `/cg help` | List all commands |

## Known Limitations

- **Reload disruption**: State transitions trigger a `/reload` in WoW, which briefly interrupts the UI. The companion delays idle-transition reloads by 10 seconds (configurable) to minimize disruption.
- **Single WoW window**: The companion targets the first WoW window found. Multiple WoW instances are not supported.
- **Focus stealing**: The companion must briefly focus the WoW window to send keystrokes. It restores the previous foreground window afterward, but there may be a brief flicker.
- **No macOS support**: Currently Windows and Linux only.

## Troubleshooting

**Companion can't find Claude Code:**
- Make sure Claude Code is running in a terminal
- Run with `--debug` to see process detection output
- The companion looks for processes named `claude` or `claude.exe`, or with `@anthropic-ai/claude-code` in the binary path

**WoW path wrong:**
- The companion validates the path on startup and will error if it doesn't exist
- Make sure `wow_path` points to the version-specific directory (e.g., `_anniversary_`, `_classic_`)

**Addon not loading:**
- Check the AddOns list at character select — enable "Load out of date AddOns" if needed
- Verify the addon files are in `Interface/AddOns/ClaudeGuard/`
- Type `/cg` in chat — if nothing happens, the addon isn't loaded

**Overlay doesn't appear:**
- Check the companion logs for "State transition" messages
- Verify `CompanionData.lua` is being written: check the file in `Interface/AddOns/ClaudeGuard/`
- Try `/reload` manually in WoW

**Overlay doesn't dismiss:**
- The companion sends `/reload` automatically when Claude starts working
- You can also click the "Reload UI" button on the overlay
- Check companion logs for "sending reload immediately" messages
