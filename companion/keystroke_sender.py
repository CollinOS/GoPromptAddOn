"""Platform-abstracted keystroke sender for triggering /reload in WoW."""

import logging
import platform
from abc import ABC, abstractmethod

logger = logging.getLogger("claude_monitor.keystroke_sender")


class KeystrokeSender(ABC):
    """Abstract base for sending keystrokes to the WoW client."""

    @abstractmethod
    def find_wow_window(self) -> bool:
        """Find the WoW window. Returns True if found."""
        ...

    @abstractmethod
    def send_reload(self) -> bool:
        """Send the /reload command sequence to WoW. Returns True if sent."""
        ...


def create_keystroke_sender() -> KeystrokeSender:
    """Factory: return the appropriate sender for the current platform."""
    system = platform.system()
    if system == "Windows":
        from companion.keystroke_sender_windows import WindowsKeystrokeSender
        return WindowsKeystrokeSender()
    elif system == "Linux":
        from companion.keystroke_sender_linux import LinuxKeystrokeSender
        return LinuxKeystrokeSender()
    else:
        raise RuntimeError(f"Unsupported platform for keystroke sending: {system}")
