"""Platform-abstracted process detection for Claude Code."""

import logging
import platform
import time
from abc import ABC
from dataclasses import dataclass

import psutil

logger = logging.getLogger("claude_monitor.process_detector")


@dataclass
class ClaudeProcess:
    """Represents a detected Claude Code process."""
    pid: int
    name: str
    cpu_percent: float  # Combined CPU of process + children
    child_pids: list[int]


class ProcessDetector(ABC):
    """Abstract base for platform-specific process detection."""

    CLAUDE_PROCESS_NAMES: set[str] = set()

    def _is_claude_process(self, name: str, cmdline: list[str]) -> bool:
        name_lower = (name or "").lower()
        if name_lower in self.CLAUDE_PROCESS_NAMES:
            return True
        # Check if the first cmdline arg (the binary) is the claude CLI
        if cmdline:
            binary = cmdline[0].replace("\\", "/").lower()
            basename = binary.rsplit("/", 1)[-1]
            if basename in ("claude", "claude.exe"):
                return True
            # npm/npx-installed claude: check for @anthropic-ai/claude-code in binary path
            if "@anthropic-ai/claude-code" in binary:
                return True
        return False

    def find_claude_processes(self) -> list[ClaudeProcess]:
        """Find all running Claude Code processes and their CPU usage."""
        results = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                info = proc.info
                if not self._is_claude_process(info["name"], info.get("cmdline") or []):
                    continue

                cpu = self.get_cpu_usage(info["pid"])
                children = []
                try:
                    p = psutil.Process(info["pid"])
                    children = [c.pid for c in p.children(recursive=True)]
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

                results.append(ClaudeProcess(
                    pid=info["pid"],
                    name=info["name"],
                    cpu_percent=cpu,
                    child_pids=children,
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return results

    def get_cpu_usage(self, pid: int, interval: float = 0.5) -> float:
        """Get combined CPU% for process + all children over interval."""
        try:
            proc = psutil.Process(pid)
            proc.cpu_percent()
            children = proc.children(recursive=True)
            for child in children:
                try:
                    child.cpu_percent()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            time.sleep(interval)

            total_cpu = proc.cpu_percent()
            for child in children:
                try:
                    total_cpu += child.cpu_percent()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return total_cpu
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0


class WindowsProcessDetector(ProcessDetector):
    """Windows implementation of Claude Code process detection."""
    CLAUDE_PROCESS_NAMES = {"claude.exe", "claude"}


class LinuxProcessDetector(ProcessDetector):
    """Linux implementation of Claude Code process detection."""
    CLAUDE_PROCESS_NAMES = {"claude"}


def create_detector() -> ProcessDetector:
    """Factory: return the appropriate detector for the current platform."""
    system = platform.system()
    if system == "Windows":
        return WindowsProcessDetector()
    elif system == "Linux":
        return LinuxProcessDetector()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
