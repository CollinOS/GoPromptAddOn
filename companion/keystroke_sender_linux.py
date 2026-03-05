"""Linux implementation of keystroke sender using xdotool."""

import logging
import shutil
import subprocess

from companion.keystroke_sender import KeystrokeSender

logger = logging.getLogger("claude_monitor.keystroke_sender")

WOW_WINDOW_NAME = "World of Warcraft"


class LinuxKeystrokeSender(KeystrokeSender):
    """Sends keystrokes to WoW on Linux via xdotool."""

    def __init__(self):
        self._window_id: str | None = None
        self._xdotool = shutil.which("xdotool")
        if not self._xdotool:
            logger.warning("xdotool not found in PATH — keystroke sending will not work. "
                           "Install with: sudo apt install xdotool")

    def _run_xdotool(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self._xdotool, *args],
            capture_output=True, text=True, timeout=5,
        )

    def find_wow_window(self) -> bool:
        """Find the WoW window using xdotool search."""
        if not self._xdotool:
            return False

        try:
            result = self._run_xdotool("search", "--name", WOW_WINDOW_NAME)
            if result.returncode != 0 or not result.stdout.strip():
                self._window_id = None
                return False

            window_ids = result.stdout.strip().split("\n")
            if len(window_ids) > 1:
                logger.warning("Found %d WoW windows, targeting the first one", len(window_ids))

            self._window_id = window_ids[0]
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._window_id = None
            return False

    def send_reload(self) -> bool:
        """Send Escape -> Enter -> /reload -> Enter to WoW via xdotool."""
        if not self._xdotool:
            logger.warning("xdotool not available, skipping reload")
            return False

        if not self.find_wow_window():
            logger.info("WoW window not found, skipping reload")
            return False

        wid = self._window_id
        logger.info("Sending /reload to WoW window (id=%s)", wid)

        try:
            # Activate the window
            self._run_xdotool("windowactivate", "--sync", wid)

            # Escape — close any open chat/menu
            self._run_xdotool("key", "--window", wid, "Escape")

            # Enter — open chat box
            self._run_xdotool("key", "--window", wid, "Return")

            # Type /reload
            self._run_xdotool("type", "--window", wid, "--delay", "20", "/reload")

            # Enter — send the command
            self._run_xdotool("key", "--window", wid, "Return")

            logger.info("Reload command sent")
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error("Failed to send reload: %s", e)
            return False
