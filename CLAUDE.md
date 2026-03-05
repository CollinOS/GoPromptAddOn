# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Beads Is Your Issue Tracker — Use It For EVERYTHING

**MANDATORY**: Use `bd` for ALL task tracking. Do NOT use TaskCreate, TodoWrite, or markdown files.

### Before Writing Code
1. `bd ready` — find available work, or identify what you're about to do
2. `bd create --title="..." --description="..." --type=task|bug|feature --priority=2` — create an issue for the work
3. `bd update <id> --status in_progress` — claim it before writing a single line

### During Work
- **Found a bug?** `bd create --type=bug --title="..." --description="..."`
- **Discovered follow-up work?** `bd create --type=task` and optionally `bd dep add`
- **Hit a blocker?** Create an issue, add the dependency, move on to something else
- Every fix, feature, refactor, or discovery gets its own bead — keep them granular

### After Completing Work
- `bd close <id>` — close each finished issue
- If partially done, leave it `in_progress` and note what remains

### Quick Reference
```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
bd create --title="Fix X" --description="Details" --type=bug --priority=2
bd list --status=open # All open issues
bd blocked            # Show blocked issues
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** — `bd create` for anything that needs follow-up
2. **Run quality gates** (if code changed) — `npx tsc --noEmit`, linters, builds
3. **Update issue status** — `bd close` finished work, update in-progress items
4. **PUSH TO REMOTE** — This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** — Clear stashes, prune remote branches
6. **Verify** — All changes committed AND pushed
7. **Hand off** — Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing — that leaves work stranded locally
- NEVER say "ready to push when you are" — YOU must push
- If push fails, resolve and retry until it succeeds
- If the user hasn't asked to land the plane, **remind them** before ending