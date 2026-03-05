"""Windows implementation of keystroke sender using ctypes."""

import ctypes
import ctypes.wintypes
import logging
import time

from companion.keystroke_sender import KeystrokeSender

logger = logging.getLogger("claude_monitor.keystroke_sender")

# Windows API constants
user32 = ctypes.windll.user32

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_RETURN = 0x0D
VK_ESCAPE = 0x1B

SW_RESTORE = 9

# Struct definitions for SendInput
# The union must include all input types so sizeof(INPUT) matches what Windows expects.
# On x64: MOUSEINPUT is the largest member (32 bytes), making INPUT 40 bytes total.
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.wintypes.DWORD),
        ("wParamL", ctypes.wintypes.WORD),
        ("wParamH", ctypes.wintypes.WORD),
    ]

class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),
            ("ki", KEYBDINPUT),
            ("hi", HARDWAREINPUT),
        ]
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


def _make_key_input(vk: int, flags: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.dwFlags = flags
    return inp


def _make_unicode_input(char: str, flags: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = 0
    inp.union.ki.wScan = ord(char)
    inp.union.ki.dwFlags = KEYEVENTF_UNICODE | flags
    return inp


def _send_inputs(inputs: list[INPUT]):
    arr = (INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))


def _press_key(vk: int):
    """Press and release a virtual key."""
    _send_inputs([
        _make_key_input(vk),
        _make_key_input(vk, KEYEVENTF_KEYUP),
    ])


def _type_string(text: str):
    """Type a string using unicode input events."""
    inputs = []
    for char in text:
        inputs.append(_make_unicode_input(char))
        inputs.append(_make_unicode_input(char, KEYEVENTF_KEYUP))
    _send_inputs(inputs)


WOW_WINDOW_TITLES = ["World of Warcraft"]


class WindowsKeystrokeSender(KeystrokeSender):
    """Sends keystrokes to WoW on Windows via SendInput."""

    def __init__(self):
        self._wow_hwnd = None

    def find_wow_window(self) -> bool:
        """Find the WoW window by enumerating top-level windows."""
        found_hwnds = []

        def _enum_callback(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    for wow_title in WOW_WINDOW_TITLES:
                        if wow_title in title:
                            found_hwnds.append(hwnd)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(_enum_callback), 0)

        if not found_hwnds:
            self._wow_hwnd = None
            return False

        if len(found_hwnds) > 1:
            logger.warning("Found %d WoW windows, targeting the first one", len(found_hwnds))

        self._wow_hwnd = found_hwnds[0]
        return True

    def send_reload(self) -> bool:
        """Send Escape -> Enter -> /reload -> Enter to WoW.

        The Escape clears any open chat input to prevent corrupting partially typed text.
        Then Enter opens the chat box, /reload is typed, and Enter sends it.
        """
        if not self.find_wow_window():
            logger.info("WoW window not found, skipping reload")
            return False

        hwnd = self._wow_hwnd
        logger.info("Sending /reload to WoW window (hwnd=%s)", hwnd)

        # Remember the currently focused window so we can restore it after
        prev_foreground = user32.GetForegroundWindow()

        # Bring WoW to foreground
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.15)

        # Escape — close any open chat/menu
        _press_key(VK_ESCAPE)
        time.sleep(0.1)

        # Enter — open chat box
        _press_key(VK_RETURN)
        time.sleep(0.1)

        # Type /reload
        _type_string("/reload")
        time.sleep(0.05)

        # Enter — send the command
        _press_key(VK_RETURN)

        # Restore the previously focused window
        if prev_foreground and prev_foreground != hwnd:
            time.sleep(0.1)
            user32.SetForegroundWindow(prev_foreground)

        logger.info("Reload command sent")
        return True
