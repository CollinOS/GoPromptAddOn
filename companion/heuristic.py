"""CPU-based heuristic for determining if Claude Code is idle or working."""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

logger = logging.getLogger("claude_monitor.heuristic")


class ClaudeStatus(Enum):
    WORKING = "working"
    IDLE = "idle"
    CLOSED = "closed"


@dataclass
class HeuristicConfig:
    cpu_threshold_percent: float = 3.0
    idle_grace_seconds: float = 5.0
    poll_interval_seconds: float = 2.0


@dataclass
class HeuristicState:
    """Tracks the internal state of the idle/working heuristic."""
    current_status: ClaudeStatus = ClaudeStatus.CLOSED
    # When we first see CPU drop below threshold, record the time.
    # Only transition to IDLE after idle_grace_seconds of sustained low CPU.
    idle_since: float | None = None
    # Track recent CPU samples for debugging/logging
    recent_cpu_samples: list[float] = field(default_factory=list)
    MAX_SAMPLES: ClassVar[int] = 30

    def add_sample(self, cpu: float):
        self.recent_cpu_samples.append(cpu)
        if len(self.recent_cpu_samples) > self.MAX_SAMPLES:
            self.recent_cpu_samples.pop(0)


class IdleHeuristic:
    """Determines if Claude Code is idle or working based on CPU usage samples."""

    def __init__(self, config: HeuristicConfig | None = None,
                 time_fn=None):
        self.config = config or HeuristicConfig()
        self._time = time_fn or time.monotonic
        self.state = HeuristicState()

    def update(self, cpu_percent: float | None) -> ClaudeStatus:
        """Feed a new CPU sample and get the current status.

        Args:
            cpu_percent: Combined CPU% of Claude + children, or None if process not found.

        Returns:
            The current ClaudeStatus after processing this sample.
        """
        now = self._time()

        # Process not found
        if cpu_percent is None:
            self.state.idle_since = None
            prev = self.state.current_status
            self.state.current_status = ClaudeStatus.CLOSED
            if prev != ClaudeStatus.CLOSED:
                logger.info("Claude Code process not found — status: closed")
            return ClaudeStatus.CLOSED

        self.state.add_sample(cpu_percent)

        if cpu_percent >= self.config.cpu_threshold_percent:
            # CPU is above threshold — Claude is working
            self.state.idle_since = None
            prev = self.state.current_status
            self.state.current_status = ClaudeStatus.WORKING
            if prev != ClaudeStatus.WORKING:
                logger.info("Claude is working (CPU: %.1f%%)", cpu_percent)
            return ClaudeStatus.WORKING

        # CPU is below threshold — potentially idle
        if self.state.idle_since is None:
            # First low-CPU sample — start the grace timer
            self.state.idle_since = now
            logger.debug("CPU dropped below threshold (%.1f%%), starting grace period", cpu_percent)

        elapsed_idle = now - self.state.idle_since

        if elapsed_idle >= self.config.idle_grace_seconds:
            # Grace period has elapsed — Claude is idle
            prev = self.state.current_status
            self.state.current_status = ClaudeStatus.IDLE
            if prev != ClaudeStatus.IDLE:
                logger.info("Claude is idle (CPU: %.1f%%, idle for %.1fs)", cpu_percent, elapsed_idle)
            return ClaudeStatus.IDLE

        # Still in grace period — maintain previous status
        logger.debug("In grace period (%.1fs / %.1fs), maintaining %s",
                     elapsed_idle, self.config.idle_grace_seconds, self.state.current_status.value)
        return self.state.current_status
