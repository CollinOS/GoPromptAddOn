"""ClaudeGuard Companion Script — monitors Claude Code and writes status to WoW SavedVariables."""

import argparse
import json
import logging
import platform
import time

from pathlib import Path

from companion.heuristic import ClaudeStatus, HeuristicConfig, IdleHeuristic
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
    return config


def saved_variables_path(config: dict) -> Path:
    """Return the full path to the ClaudeGuard SavedVariables file."""
    return (Path(config["wow_path"]) / "WTF" / "Account" /
            config["account_name"] / "SavedVariables" / "ClaudeGuard.lua")


def run_monitor_loop(config: dict) -> None:
    """Main monitor loop: detect Claude, evaluate heuristic, write on transitions."""
    detector = create_detector()
    heuristic = IdleHeuristic(config=HeuristicConfig(
        cpu_threshold_percent=config["cpu_threshold_percent"],
        idle_grace_seconds=config["idle_grace_seconds"],
        poll_interval_seconds=config["poll_interval_seconds"],
    ))
    sv_path = saved_variables_path(config)
    poll_interval = config["poll_interval_seconds"]
    last_written_status: ClaudeStatus | None = None

    logger.info("SavedVariables path: %s", sv_path)
    logger.info("Poll interval: %ss, CPU threshold: %.1f%%, Grace period: %ss",
                poll_interval, config["cpu_threshold_percent"], config["idle_grace_seconds"])

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

            # Write on state transitions only
            if status != last_written_status:
                logger.info("State transition: %s -> %s",
                            last_written_status.value if last_written_status else "none",
                            status.value)
                write_saved_variables(sv_path, status)
                last_written_status = status

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
