Phase 1 is complete. Read `build_plan.md` to refresh on Phase 2 (WoW Addon MVP), then
`bd list --status=open` to see the existing Phase 2 beads. If any need adjusting based on
what we learned during Phase 1, update or create new beads as needed.

Work through Phase 2 in order. This is all Lua targeting the TBC Classic client
(Interface: 20504). Key reminders:

**PlayerState.lua** — Keep detection conservative. Use `UnitAffectingCombat("player")` for
combat, `IsInInstance()` for dungeons/raids/PvP/arenas. Register for `PLAYER_REGEN_DISABLED`,
`PLAYER_REGEN_ENABLED`, `ZONE_CHANGED_NEW_AREA`, and `UPDATE_BATTLEFIELD_STATUS`. Expose a
single `ClaudeGuard.PlayerState.IsProtected()` function the other modules can call.

**Blocker.lua** — This is the core of the addon experience. The full-screen overlay must
actually eat all input — mouse and keyboard. Use `TOOLTIP` frame strata, `EnableMouse(true)`,
`EnableKeyboard(true)`, `SetPropagateKeyboardInput(false)`. The snooze button (2 min, max 3
per session) is important — don't skip it. Use built-in WoW textures and fonts rather than
custom TGA files for now; we can polish visuals in Phase 4.

**Notification.lua** — Keep it simple. A small frame anchored near the top of the screen with
an icon and text that pulses. Use a built-in WoW sound for the initial alert. This must
auto-transition to the Blocker when `IsProtected()` flips to false (e.g. combat ends).

**ClaudeGuard.lua** — Read `ClaudeGuardDB` on `ADDON_LOADED`. Since SavedVariables only load
on login/reload, the logic here is straightforward for now: read status, check PlayerState,
show the right UI. Wire up the slash commands (`/cg status`, `/cg snooze`, `/cg disable`).

Test each module by manually editing the SavedVariables file before loading into WoW. You
don't need the companion script running — just set `ClaudeGuardDB = { status = "idle" }` or
`"working"` in the saved variables file and `/reload` to verify behavior.

Don't start Phase 3 until all Phase 2 beads are closed. Stop and check in with me when done.