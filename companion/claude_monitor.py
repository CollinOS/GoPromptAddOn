"""ClaudeGuard Companion Script — monitors Claude Code and writes status to WoW SavedVariables."""

import argparse
import json
import logging
import platform
import time

from pathlib import Path

from companion.heuristic import ClaudeStatus, HeuristicConfig, IdleHeuristic
from companion.keystroke_sender import create_keystroke_sender
from companion.process_detector import create_detector
from companion.savedvariables import write_saved_variables

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
    # Default for reload_delay_seconds if not present (backwards compat)
    config.setdefault("reload_delay_seconds", 10)
    return config


def companion_data_path(config: dict) -> Path:
    """Return the full path to the CompanionData.lua file in the addon directory."""
    return (Path(config["wow_path"]) / "Interface" / "AddOns" /
            "ClaudeGuard" / "CompanionData.lua")


def run_monitor_loop(config: dict) -> None:
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

    # Pending reload state: when we transition to idle/closed, we schedule a
    # delayed reload. This tracks when the reload should fire.
    pending_reload_at: float | None = None

    logger.info("SavedVariables path: %s", sv_path)
    logger.info("Poll interval: %ss, CPU threshold: %.1f%%, Grace period: %ss, Reload delay: %ss",
                poll_interval, config["cpu_threshold_percent"],
                config["idle_grace_seconds"], reload_delay)

    while True:
        try:
            # Detect Claude processes
            processes = detector.find_claude_processes()

            if not processes:
                cpu = None
            else:
                # Use the highest CPU across all Claude processes
                cpu = max(p.cpu_percent for p in processes)

            # Evaluate heuristic
            status = heuristic.update(cpu)

            # Handle state transitions
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
                    # Unblocking the player — send reload immediately
                    pending_reload_at = None
                    logger.info("Claude is working — sending reload immediately")
                    keystroke_sender.send_reload()

                elif is_becoming_idle:
                    # Blocking transition — schedule delayed reload
                    pending_reload_at = time.monotonic() + reload_delay
                    logger.info("Claude is %s — reload scheduled in %ss",
                                status.value, reload_delay)

            # Check if a pending delayed reload should fire
            if pending_reload_at is not None and time.monotonic() >= pending_reload_at:
                logger.info("Delayed reload firing now")
                keystroke_sender.send_reload()
                pending_reload_at = None

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Shutting down.")
            break
        except Exception:
            logger.exception("Error in monitor loop")
            time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="ClaudeGuard companion — monitors Claude Code activity")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.json")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config = load_config(args.config)
    logger.info("ClaudeGuard companion started. Platform: %s", platform.system())
    logger.info("WoW path: %s", config["wow_path"])
    logger.info("Account: %s", config["account_name"])

    if config["account_name"] == "YOUR_ACCOUNT":
        logger.warning("account_name is still set to YOUR_ACCOUNT — "
                        "update config.json with your actual WoW account name")

    run_monitor_loop(config)


if __name__ == "__main__":
    main()
