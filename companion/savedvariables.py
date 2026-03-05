"""Writes ClaudeGuard status to WoW SavedVariables file."""

import logging
import os
import tempfile
import time
from pathlib import Path

from companion.heuristic import ClaudeStatus

logger = logging.getLogger("claude_monitor.savedvariables")

LUA_TEMPLATE = """\
-- CompanionData.lua
-- Written by the companion script. DO NOT EDIT.
-- WoW loads this file on /reload, reading the current status.
CLAUDEGUARD_COMPANION_STATUS = "{status}"
CLAUDEGUARD_COMPANION_TIMESTAMP = {timestamp}
"""


def format_saved_variables(status: ClaudeStatus, timestamp: int | None = None) -> str:
    """Format the CompanionData.lua content."""
    if timestamp is None:
        timestamp = int(time.time())
    return LUA_TEMPLATE.format(status=status.value, timestamp=timestamp)


def write_saved_variables(path: Path, status: ClaudeStatus) -> None:
    """Atomically write the SavedVariables file.

    Writes to a temp file in the same directory, then renames to avoid
    WoW reading a partial file.
    """
    content = format_saved_variables(status)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in the same directory (same filesystem for atomic rename)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix="ClaudeGuard_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        # On Windows, os.rename fails if target exists; use os.replace instead
        os.replace(tmp_path, path)
        logger.debug("Wrote SavedVariables: status=%s to %s", status.value, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
