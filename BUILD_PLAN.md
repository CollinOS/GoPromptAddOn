# ClaudeGuard — Build Plan

## Concept
A WoW TBC Classic addon that monitors whether Claude Code is actively working in your terminal. When Claude finishes and is idle (waiting for a prompt), the addon blocks gameplay until you give Claude more work. If you're in combat, a dungeon, raid, or PvP, it shows a non-blocking notification instead.

---

## Architecture Overview

WoW addons are sandboxed — they cannot read processes, hit APIs, or touch the filesystem directly. We need a **bridge** between the outside world and the addon. The standard approach is a companion app that writes state to a SavedVariables file, which the addon reads on a timer via `/reload` or by watching a file the addon can access.

**However**, the cleanest TBC-compatible approach is:

1. **Companion Script (Python)** — Monitors Claude Code's terminal process, detects idle vs. active state, and writes status to the addon's SavedVariables `.lua` file.
2. **WoW Addon (Lua)** — Reads the status variable on a polling interval (via a lightweight reload mechanism), determines player context (combat, dungeon, PvP), and either blocks the screen or shows a notification.

```
┌─────────────────┐       writes to       ┌──────────────────────────┐
│  Companion App  │ ───────────────────▶  │  SavedVariables .lua     │
│  (Python)       │    ClaudeGuardDB =    │  (WoW addon data file)   │
│                 │    { status = "idle" } │                          │
└────────┬────────┘                       └────────────┬─────────────┘
         │ monitors                                    │ read by
         ▼                                             ▼
┌─────────────────┐                       ┌──────────────────────────┐
│  Claude Code    │                       │  ClaudeGuard WoW Addon   │
│  (terminal)     │                       │  (Lua, in-game)          │
└─────────────────┘                       └──────────────────────────┘
```

---

## Component 1: Companion Script (Python)

### File: `companion/claude_monitor.py`

### Responsibilities
- Detect if Claude Code is running in a terminal session.
- Determine if Claude is **actively working** (streaming output / executing) vs. **idle** (waiting at the prompt for user input).
- Write the current status to the WoW addon's SavedVariables file every 2 seconds.

### Detection Strategy
Claude Code runs as a Node.js process (typically `claude` CLI). The monitor should:

1. **Find Claude Code processes** — Use `psutil` to find processes matching the Claude Code binary (e.g., process name contains `claude`).
2. **Determine active vs. idle state** — Two approaches, try in order:
   - **CPU-based heuristic**: If the Claude process (and child processes) CPU usage is above a threshold (~2-5%) sustained over a sample window, it's "working." If CPU is near-zero for several seconds, it's "idle" (waiting for input).
   - **PTY / stdout monitoring (advanced fallback)**: Monitor the terminal's PTY for output activity. Active output = working. No output for N seconds = idle.
3. **Determine if Claude Code is even open** — If no matching process is found, status is `"closed"`.

### Status Values
- `"working"` — Claude is actively processing a prompt.
- `"idle"` — Claude is open but waiting for user input. **This triggers the block.**
- `"closed"` — Claude Code is not running. Treat same as idle (you should be working!).

### SavedVariables Write Target
```
<WoW Install>/WTF/Account/<ACCOUNT>/SavedVariables/ClaudeGuard.lua
```

The script writes:
```lua
ClaudeGuardDB = {
    ["status"] = "idle",
    ["lastUpdate"] = 1709654400,
}
```

### Configuration
- `config.json` at the companion script's root:
  ```json
  {
    "wow_path": "C:/Program Files/World of Warcraft/_classic_",
    "account_name": "YOUR_ACCOUNT",
    "poll_interval_seconds": 2,
    "cpu_threshold_percent": 3.0,
    "idle_grace_seconds": 5
  }
  ```

### Dependencies
- `psutil` (process monitoring)
- Standard library only otherwise

### Key Implementation Notes
- Run as a background daemon / tray app.
- Must handle WoW not running gracefully (just keep writing the file).
- The `idle_grace_seconds` prevents flickering — Claude must be idle for N seconds before status flips to `"idle"`.
- On macOS, the Claude Code process tree may look different than Windows — detect both.
- Write the SavedVariables file atomically (write to temp, then rename) to avoid WoW reading a partial file.

---

## Component 2: WoW TBC Classic Addon (Lua)

### File Structure
```
ClaudeGuard/
├── ClaudeGuard.toc
├── ClaudeGuard.lua
├── Blocker.lua
├── Notification.lua
├── PlayerState.lua
└── Textures/
    ├── claude-icon.tga
    ├── blocker-bg.tga
    └── notification-bg.tga
```

### ClaudeGuard.toc
```toc
## Interface: 20504
## Title: ClaudeGuard
## Notes: Blocks gameplay when Claude Code is idle. Get back to work.
## SavedVariables: ClaudeGuardDB
## Version: 1.0.0
PlayerState.lua
Notification.lua
Blocker.lua
ClaudeGuard.lua
```

### Module: PlayerState.lua
Determines if the player is in a "protected" context where blocking would be disruptive.

**Player is "protected" if ANY of these are true:**
- `UnitAffectingCombat("player")` returns true (in combat)
- Player is in a dungeon or raid instance (`IsInInstance()` returns `true` with `instanceType` = `"party"` or `"raid"`)
- Player is in a battleground or arena (`instanceType` = `"pvp"` or `"arena"`)
- Player is in the LFG queue and a dungeon has popped (if applicable in TBC)

**Expose:**
- `ClaudeGuard.PlayerState.IsProtected()` → boolean
- Register for events: `PLAYER_REGEN_DISABLED`, `PLAYER_REGEN_ENABLED`, `ZONE_CHANGED_NEW_AREA`, `UPDATE_BATTLEFIELD_STATUS`

### Module: Blocker.lua
The full-screen block overlay.

**Behavior:**
- Creates a full-screen frame at a very high frame strata (`"FULLSCREEN_DIALOG"` or `"TOOLTIP"` level) that captures all mouse input and key input.
- Displays a message: *"Claude Code is waiting for a prompt. Get back to work!"*
- Shows the Claude icon.
- Includes a small "I need 2 more minutes" snooze button that temporarily dismisses for 120 seconds (limited to 3 uses per session to prevent abuse).
- The frame intercepts all clicks — the player literally cannot interact with the game world.
- A `/reload` UI will re-read SavedVariables and recheck status.

**Key API calls:**
- `frame:EnableMouse(true)` / `frame:EnableKeyboard(true)` to capture input
- `frame:SetFrameStrata("TOOLTIP")` to sit above everything
- `frame:SetAllPoints(UIParent)` for full screen
- `frame:SetPropagateKeyboardInput(false)` to eat key presses

**Important:** This cannot prevent the player from pressing Alt+F4 or `/reload` — that's fine and intended as an escape valve.

### Module: Notification.lua
The non-blocking notification for protected contexts.

**Behavior:**
- Small icon + text anchored to the top-center or minimap area.
- Pulses/glows gently to draw attention without obstructing gameplay.
- Text: *"Claude is ready for a prompt"*
- Plays a subtle sound on first appearance (use a built-in WoW sound file).
- Auto-transitions to the Blocker once the player leaves the protected state (e.g., combat ends, leaves instance).

### Module: ClaudeGuard.lua (Core)
Main controller that ties everything together.

**Initialization:**
1. Register `ADDON_LOADED` event.
2. When loaded, read `ClaudeGuardDB` (the SavedVariables table written by the companion script).
3. Start a polling ticker.

**Polling Loop (every 5 seconds via `C_Timer.NewTicker` or `OnUpdate` with elapsed tracking):**
1. Read `ClaudeGuardDB.status`.
2. **Problem**: SavedVariables are only read on login/reload. The companion script writes the file, but the addon won't see changes until `/reload`.

**Solving the Polling Problem — Two Options:**

**Option A: Frequent `/reload` (simple but janky)**
- Not recommended. Causes screen flash.

**Option B: Use a WeakAura-style file-read trick (not available in TBC)**
- Not viable in TBC Classic's sandboxed Lua.

**Option C (Recommended): Companion script uses a lightweight local HTTP server + addon uses the `SendAddonMessage` approach via a WoW-external bridge.**

Actually — the most practical TBC-compatible approach:

**Option D: Companion script directly modifies a .lua file AND triggers an in-game `/reload` only on state transitions.**
- The companion script watches for state changes (`working` → `idle` or `idle` → `working`).
- On change, it writes the SavedVariables AND sends a signal.
- For signaling: the companion can use **AutoHotKey (Windows)** or **osascript (macOS)** to send a `/reload` command to the WoW chat window only when the state transitions.
- This means `/reload` only happens at transition moments (not every 2 seconds).
- On the `idle` → `working` transition reload, the blocker clears instantly.

**Refined flow:**
```
Claude goes idle
  → Companion detects idle (after grace period)
  → Companion writes status = "idle" to SavedVariables
  → Companion sends keystrokes to WoW: Enter → /reload → Enter
  → Addon loads, reads "idle", checks PlayerState
    → If protected: show Notification
    → If not protected: show Blocker

Claude starts working
  → Companion detects working
  → Companion writes status = "working" to SavedVariables
  → Companion sends /reload to WoW
  → Addon loads, reads "working", hides Blocker/Notification
```

### Slash Commands
- `/cg status` — Print current Claude status to chat.
- `/cg snooze` — Manually snooze for 2 minutes.
- `/cg disable` — Disable until next login (for when you actually want to just play).
- `/cg config` — Print configuration.

---

## Build Order

### Phase 1: Companion Script MVP
1. Set up Python project structure with `config.json`.
2. Implement process detection for Claude Code using `psutil`.
3. Implement CPU-based idle vs. working heuristic.
4. Implement SavedVariables file writer.
5. Implement state transition detection and grace period logic.
6. Add logging.
7. Test on macOS and/or Windows with Claude Code running.

### Phase 2: WoW Addon MVP
1. Create addon file structure and `.toc`.
2. Implement `PlayerState.lua` — combat, instance, and PvP detection.
3. Implement `Blocker.lua` — full-screen overlay with input capture.
4. Implement `Notification.lua` — non-blocking icon/text display.
5. Implement `ClaudeGuard.lua` — read SavedVariables on load, show/hide UI.
6. Test with manually edited SavedVariables (no companion needed yet).

### Phase 3: Integration
1. Implement the keystroke-sending reload trigger in the companion script.
   - Windows: `pyautogui` or `ctypes` `SendInput`.
   - macOS: `osascript` with `System Events`.
2. Test full loop: Claude idle → WoW blocks → give Claude a prompt → WoW unblocks.
3. Handle edge cases:
   - WoW not in focus when reload is triggered.
   - Player is mid-loading-screen.
   - Multiple WoW windows.
   - Claude Code restarted.

### Phase 4: Polish
1. Add textures / visual polish to blocker and notification.
2. Add the snooze button with usage limits.
3. Add slash commands.
4. Add a "first run" setup guide printed to chat.
5. Add companion script auto-start on system boot (optional).
6. Write a README with installation instructions.

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `/reload` during gameplay is disruptive | Medium | Only trigger on state transitions; never during protected states (companion can check a flag file the addon writes before triggering reload) |
| CPU heuristic gives false positives/negatives | Medium | Tune thresholds; add grace period; allow user calibration |
| WoW ToS concerns with external keystroke sending | High | The `/reload` keystroke is the sketchiest part. Alternative: accept that the user must manually `/reload` and just have the blocker appear on next natural load. Or use a WeakAura companion approach if available. |
| TGA texture format requirements | Low | Use a converter; or skip custom textures and use built-in WoW textures |
| macOS vs Windows process detection differences | Low | Abstract platform-specific code; test both |

---

## File Manifest

```
claudeguard/
├── companion/
│   ├── claude_monitor.py       # Main monitoring daemon
│   ├── config.json             # User configuration
│   ├── requirements.txt        # psutil, pyautogui (optional)
│   └── README.md               # Companion setup instructions
├── addon/
│   └── ClaudeGuard/
│       ├── ClaudeGuard.toc     # Addon metadata
│       ├── ClaudeGuard.lua     # Core controller
│       ├── Blocker.lua         # Full-screen block overlay
│       ├── Notification.lua    # Non-blocking notification
│       ├── PlayerState.lua     # Combat/instance/PvP detection
│       └── Textures/
│           └── (placeholder)   # .tga texture files
└── README.md                   # Top-level project overview & install guide
```
