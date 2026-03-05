Read the `build_plan.md` and `claude.md` files in the project root. The build plan describes
"ClaudeGuard" — a two-part system with a Python companion script and a WoW TBC Classic addon.

Start by running `bd onboard`, then create beads for Phase 1 and Phase 2 from the build plan.
Break them into granular, individually-completable issues — roughly one bead per numbered step
in the plan. Don't create beads for Phase 3 or 4 yet; we'll get there after the foundations work.

Once the beads are created, begin working through Phase 1 (Companion Script MVP) in order.
Follow the claude.md workflow — claim each bead before starting, close it when done, and
create bug/task beads for anything unexpected you discover along the way.

For the companion script, target Windows first. Use `psutil` for process detection. Make sure
the config.json includes a sensible default `wow_path` for Windows
(e.g. `C:/Program Files (x86)/World of Warcraft/_anniversary_`) and document that the user needs
to update their account name. Linux support comes next — keep platform-specific logic
(process detection, paths, keystroke sending) behind clean abstractions so adding Linux
later is straightforward. No macOS support needed. Write real tests for the idle-vs-working
heuristic — that's the core logic and the hardest part to get right.

Don't start on Phase 2 (the addon Lua code) until all Phase 1 beads are closed. When you
finish Phase 1, stop and check in with me before moving on.