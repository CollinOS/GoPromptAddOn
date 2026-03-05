"""Creates a Windows desktop shortcut for the ClaudeGuard launcher."""

import os
import sys
from pathlib import Path


def create_shortcut():
    try:
        import win32com.client
    except ImportError:
        print("ERROR: pywin32 is required. Install with: pip install pywin32")
        sys.exit(1)

    launcher_path = Path(__file__).parent / "launcher.pyw"
    if not launcher_path.exists():
        print(f"ERROR: launcher.pyw not found at {launcher_path}")
        sys.exit(1)

    desktop = Path(os.path.expanduser("~/Desktop"))
    shortcut_path = desktop / "ClaudeGuard WoW.lnk"

    # Find pythonw.exe for .pyw files
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.TargetPath = str(pythonw)
    shortcut.Arguments = f'"{launcher_path}"'
    shortcut.WorkingDirectory = str(launcher_path.parent.parent)
    shortcut.Description = "Launch WoW with ClaudeGuard companion"

    # Use WoW icon if available, otherwise use Python icon
    wow_icon = Path("C:/Program Files (x86)/World of Warcraft/_anniversary_/WowClassic.exe")
    if wow_icon.exists():
        shortcut.IconLocation = f"{wow_icon},0"

    shortcut.save()
    print(f"Shortcut created: {shortcut_path}")
    print()
    print("Double-click 'ClaudeGuard WoW' on your desktop to:")
    print("  1. Start the ClaudeGuard companion in the background")
    print("  2. Launch Battle.net")
    print("  3. Automatically shut down when you close WoW")


if __name__ == "__main__":
    create_shortcut()
