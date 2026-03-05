"""ClaudeGuard Companion Script — monitors Claude Code and writes status to WoW addon data."""

import argparse
import json
import logging
import platform
import signal
import sys
import time

from pathlib import Path

from companion.heuristic import ClaudeStatus, HeuristicConfig, IdleHeuristic
from companion.keystroke_sender import create_keystroke_sender
from companion.process_detector import create_detector
from companion.savedvariables import write_saved_variables

VERSION = "1.0.0"
logger = logging.getLogger("claude_monitor")


def load_config(config_path: Path | None = None) -> dict:
    """Load configuration from config.json."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.json"
    with open(config_path) as f:
        config = json.load(f)
    required = ["wow_path", "account_name", "poll_interval_seconds",
                "cpu_threshold_percent", "idle_grace_seconds"]
    for key in required:
        if key not in config:
            raise KeyError(f"Missing required config key: {key}")
    config.setdefault("reload_delay_seconds", 10)
    return config


def companion_data_path(config: dict) -> Path:
    """Return the full path to the CompanionData.lua file in the addon directory."""
    return (Path(config["wow_path"]) / "Interface" / "AddOns" /
            "ClaudeGuard" / "CompanionData.lua")


def validate_paths(config: dict) -> bool:
    """Validate that configured paths exist. Returns True if valid."""
    wow_path = Path(config["wow_path"])
    if not wow_path.exists():
        logger.error("WoW path does not exist: %s", wow_path)
        logger.error("Update wow_path in config.json to your WoW installation directory.")
        return False

    addon_dir = wow_path / "Interface" / "AddOns" / "ClaudeGuard"
    if not addon_dir.exists():
        logger.warning("ClaudeGuard addon not found at: %s", addon_dir)
        logger.warning("Install the addon before running the companion script.")

    return True


def run_monitor_loop(config: dict, dry_run: bool = False) -> None:
    """Main monitor loop: detect Claude, evaluate heuristic, write and reload on transitions."""
    detector = create_detector()
    heuristic = IdleHeuristic(config=HeuristicConfig(
        cpu_threshold_percent=config["cpu_threshold_percent"],
        idle_grace_seconds=config["idle_grace_seconds"],
        poll_interval_seconds=config["poll_interval_seconds"],
    ))
    keystroke_sender = create_keystroke_sender()
    sv_path = companion_data_path(config)
    poll_interval = config["poll_interval_seconds"]
    reload_delay = config["reload_delay_seconds"]
    last_written_status: ClaudeStatus | None = None

    pending_reload_at: float | None = None

    logger.info("CompanionData path: %s", sv_path)
    logger.info("Poll interval: %ss, CPU threshold: %.1f%%, Grace period: %ss, Reload delay: %ss",
                poll_interval, config["cpu_threshold_percent"],
                config["idle_grace_seconds"], reload_delay)
    if dry_run:
        logger.info("DRY RUN mode — keystrokes will not be sent to WoW")

    # Initial Claude detection
    initial_procs = detector.find_claude_processes()
    if initial_procs:
        logger.info("Claude Code detected (%d process(es))", len(initial_procs))
    else:
        logger.info("Claude Code not currently running")

    while True:
        try:
            processes = detector.find_claude_processes()

            if not processes:
                cpu = None
            else:
                cpu = max(p.cpu_percent for p in processes)

            status = heuristic.update(cpu)

            if status != last_written_status:
                prev = last_written_status
                logger.info("State transition: %s -> %s",
                            prev.value if prev else "none",
                            status.value)
                write_saved_variables(sv_path, status)
                last_written_status = status

                is_becoming_idle = status in (ClaudeStatus.IDLE, ClaudeStatus.CLOSED)
                is_becoming_active = status == ClaudeStatus.WORKING

                if is_becoming_active:
                    pending_reload_at = None
                    if dry_run:
                        logger.info("Claude is working — would send reload (dry run)")
                    else:
                        logger.info("Claude is working — sending reload immediately")
                        keystroke_sender.send_reload()

                elif is_becoming_idle:
                    pending_reload_at = time.monotonic() + reload_delay
                    logger.info("Claude is %s — reload scheduled in %ss",
                                status.value, reload_delay)

            if pending_reload_at is not None and time.monotonic() >= pending_reload_at:
                if dry_run:
                    logger.info("Delayed reload would fire now (dry run)")
                else:
                    logger.info("Delayed reload firing now")
                    keystroke_sender.send_reload()
                pending_reload_at = None

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Shutting down — writing 'working' status to unblock player")
            try:
                write_saved_variables(sv_path, ClaudeStatus.WORKING)
            except Exception:
                logger.exception("Failed to write shutdown status")
            break
        except Exception:
            logger.exception("Error in monitor loop")
            time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="ClaudeGuard companion — monitors Claude Code activity")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.json")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run without sending keystrokes to WoW")
    parser.add_argument("--version", action="version", version=f"ClaudeGuard companion v{VERSION}")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("ClaudeGuard companion v%s — Platform: %s", VERSION, platform.system())

    config = load_config(args.config)
    logger.info("WoW path: %s", config["wow_path"])
    logger.info("Account: %s", config["account_name"])

    if not validate_paths(config):
        sys.exit(1)

    if config["account_name"] == "YOUR_ACCOUNT":
        logger.warning("account_name is still set to YOUR_ACCOUNT — "
                        "update config.json with your actual WoW account name")

    # Register SIGTERM handler for clean shutdown
    sv_path = companion_data_path(config)

    def _sigterm_handler(signum, frame):
        logger.info("SIGTERM received — writing 'working' status to unblock player")
        try:
            write_saved_variables(sv_path, ClaudeStatus.WORKING)
        except Exception:
            logger.exception("Failed to write shutdown status")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _sigterm_handler)

    run_monitor_loop(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
