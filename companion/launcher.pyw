"""ClaudeGuard Launcher — starts companion, launches Battle.net, monitors WoW lifecycle."""

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

# Logging to file since .pyw has no console
LOG_DIR = Path(__file__).parent
LOG_FILE = LOG_DIR / "launcher.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("launcher")

CONFIG_PATH = Path(__file__).parent / "config.json"
LOCKFILE = Path(tempfile.gettempdir()) / "claudeguard_launcher.lock"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    config.setdefault("battlenet_path", "C:/Program Files (x86)/Battle.net/Battle.net Launcher.exe")
    config.setdefault("wow_process_name", "WowClassic.exe")
    config.setdefault("wow_detection_timeout_minutes", 30)
    config.setdefault("wow_exit_grace_seconds", 60)
    return config


def acquire_lock() -> bool:
    """Acquire a lockfile to prevent duplicate instances. Returns True if acquired."""
    try:
        if LOCKFILE.exists():
            # Check if the PID in the lockfile is still running
            try:
                pid = int(LOCKFILE.read_text().strip())
                if psutil.pid_exists(pid):
                    try:
                        proc = psutil.Process(pid)
                        if proc.is_running() and "python" in proc.name().lower():
                            logger.info("Another launcher instance is running (PID %d), exiting", pid)
                            return False
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (ValueError, OSError):
                pass
            # Stale lockfile — remove it
            LOCKFILE.unlink(missing_ok=True)

        LOCKFILE.write_text(str(os.getpid()))
        return True
    except OSError as e:
        logger.error("Failed to acquire lock: %s", e)
        return False


def release_lock():
    try:
        LOCKFILE.unlink(missing_ok=True)
    except OSError:
        pass


def is_process_running(name: str) -> bool:
    """Check if a process with the given name is running."""
    name_lower = name.lower()
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == name_lower:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def find_process(name: str) -> psutil.Process | None:
    """Find and return a process by name."""
    name_lower = name.lower()
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == name_lower:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def start_companion() -> subprocess.Popen:
    """Start the companion monitor as a subprocess."""
    python = sys.executable
    companion_module = "companion.claude_monitor"
    project_root = Path(__file__).parent.parent

    # Use pythonw.exe if available to avoid console window
    pythonw = Path(python).parent / "pythonw.exe"
    exe = str(pythonw) if pythonw.exists() else python

    logger.info("Starting companion: %s -m %s", exe, companion_module)
    proc = subprocess.Popen(
        [exe, "-m", companion_module],
        cwd=str(project_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    logger.info("Companion started (PID %d)", proc.pid)
    return proc


def ensure_companion_running(companion_proc: subprocess.Popen | None) -> subprocess.Popen:
    """Restart companion if it crashed."""
    if companion_proc is not None and companion_proc.poll() is None:
        return companion_proc
    if companion_proc is not None:
        logger.warning("Companion process exited (code %s), restarting", companion_proc.returncode)
    return start_companion()


def launch_battlenet(config: dict):
    """Launch Battle.net if not already running."""
    bnet_path = Path(config["battlenet_path"])

    if is_process_running("Battle.net.exe"):
        logger.info("Battle.net is already running, skipping launch")
        return

    if not bnet_path.exists():
        logger.warning("Battle.net not found at %s, skipping launch", bnet_path)
        return

    logger.info("Launching Battle.net: %s", bnet_path)
    subprocess.Popen(
        [str(bnet_path)],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def wait_for_wow(config: dict) -> bool:
    """Poll for WoW process. Returns True if found, False if timed out."""
    wow_name = config["wow_process_name"]
    timeout_minutes = config["wow_detection_timeout_minutes"]
    deadline = time.monotonic() + (timeout_minutes * 60)

    if is_process_running(wow_name):
        logger.info("WoW is already running")
        return True

    logger.info("Waiting for %s (timeout: %d minutes)...", wow_name, timeout_minutes)
    while time.monotonic() < deadline:
        if is_process_running(wow_name):
            logger.info("WoW detected")
            return True
        time.sleep(5)

    logger.warning("Timed out waiting for WoW after %d minutes", timeout_minutes)
    return False


def monitor_wow_exit(config: dict):
    """Monitor for WoW exit with a grace period for relaunches."""
    wow_name = config["wow_process_name"]
    grace_seconds = config["wow_exit_grace_seconds"]

    logger.info("Monitoring WoW process for exit (grace period: %ds)", grace_seconds)

    while True:
        if is_process_running(wow_name):
            time.sleep(10)
            continue

        # WoW disappeared — start grace period
        logger.info("WoW process gone, waiting %ds for possible relaunch...", grace_seconds)
        grace_deadline = time.monotonic() + grace_seconds

        while time.monotonic() < grace_deadline:
            if is_process_running(wow_name):
                logger.info("WoW relaunched during grace period, resuming monitoring")
                break
            time.sleep(5)
        else:
            # Grace period expired, WoW is truly gone
            logger.info("WoW did not relaunch, shutting down")
            return


def main():
    logger.info("ClaudeGuard Launcher starting")

    if not acquire_lock():
        sys.exit(0)

    companion_proc = None
    try:
        config = load_config()

        # Start companion
        companion_proc = start_companion()

        # Launch Battle.net
        launch_battlenet(config)

        # Wait for WoW
        if not wait_for_wow(config):
            logger.info("WoW never started, shutting down")
            return

        # Monitor WoW, restarting companion if it crashes
        wow_name = config["wow_process_name"]
        grace_seconds = config["wow_exit_grace_seconds"]

        while True:
            companion_proc = ensure_companion_running(companion_proc)

            if is_process_running(wow_name):
                time.sleep(10)
                continue

            # WoW gone — grace period
            logger.info("WoW process gone, waiting %ds for relaunch...", grace_seconds)
            grace_deadline = time.monotonic() + grace_seconds
            relaunched = False

            while time.monotonic() < grace_deadline:
                if is_process_running(wow_name):
                    logger.info("WoW relaunched, resuming")
                    relaunched = True
                    break
                time.sleep(5)

            if not relaunched:
                logger.info("WoW exited for good, shutting down")
                return

    except Exception:
        logger.exception("Launcher error")
    finally:
        if companion_proc and companion_proc.poll() is None:
            logger.info("Terminating companion (PID %d)", companion_proc.pid)
            companion_proc.terminate()
            try:
                companion_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                companion_proc.kill()
        release_lock()
        logger.info("Launcher exited")


if __name__ == "__main__":
    main()
