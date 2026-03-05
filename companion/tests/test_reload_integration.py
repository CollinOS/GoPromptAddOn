"""Tests for reload trigger integration into the monitor loop."""

import json
import threading
import time
from unittest.mock import MagicMock, patch

from companion.claude_monitor import load_config, run_monitor_loop
from companion.keystroke_sender import KeystrokeSender


class FakeKeystrokeSender(KeystrokeSender):
    """Records reload calls for testing."""

    def __init__(self):
        self.reload_calls = []
        self.wow_running = True

    def find_wow_window(self) -> bool:
        return self.wow_running

    def send_reload(self) -> bool:
        if not self.find_wow_window():
            return False
        self.reload_calls.append(time.monotonic())
        return True


class TestReloadOnTransition:
    """Test that reload fires at the right times based on state transitions."""

    def _make_config(self, tmp_path, reload_delay=1):
        config = {
            "wow_path": str(tmp_path),
            "account_name": "TEST",
            "poll_interval_seconds": 0.2,
            "cpu_threshold_percent": 3.0,
            "idle_grace_seconds": 0.0,  # instant idle for testing
            "reload_delay_seconds": reload_delay,
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config))
        return load_config(config_path)

    @patch("companion.claude_monitor.create_keystroke_sender")
    @patch("companion.claude_monitor.create_detector")
    def test_working_to_idle_triggers_delayed_reload(self, mock_detector, mock_sender, tmp_path):
        fake_sender = FakeKeystrokeSender()
        mock_sender.return_value = fake_sender

        # Simulate: Claude detected with high CPU, then low CPU
        mock_proc_working = MagicMock()
        mock_proc_working.cpu_percent = 50.0
        mock_proc_idle = MagicMock()
        mock_proc_idle.cpu_percent = 0.0

        call_count = [0]
        def find_claude():
            call_count[0] += 1
            if call_count[0] <= 2:
                return [mock_proc_working]
            return [mock_proc_idle]

        mock_detector.return_value.find_claude_processes = find_claude

        config = self._make_config(tmp_path, reload_delay=1)

        # Run loop in thread, stop after enough time for transitions
        def run():
            run_monitor_loop(config)

        t = threading.Thread(target=run, daemon=True)
        t.start()

        # Wait for: 2 working polls + idle transition + 1s delay + margin
        time.sleep(3.5)

        # Should have 2 reload calls: one immediate on first detection (working),
        # and one delayed after idle transition
        # Actually: first transition is none->working (immediate reload),
        # then working->idle (delayed reload after 1s)
        assert len(fake_sender.reload_calls) >= 2

    @patch("companion.claude_monitor.create_keystroke_sender")
    @patch("companion.claude_monitor.create_detector")
    def test_idle_to_working_triggers_immediate_reload(self, mock_detector, mock_sender, tmp_path):
        fake_sender = FakeKeystrokeSender()
        mock_sender.return_value = fake_sender

        mock_proc_idle = MagicMock()
        mock_proc_idle.cpu_percent = 0.0
        mock_proc_working = MagicMock()
        mock_proc_working.cpu_percent = 50.0

        call_count = [0]
        def find_claude():
            call_count[0] += 1
            if call_count[0] <= 3:
                return [mock_proc_idle]
            return [mock_proc_working]

        mock_detector.return_value.find_claude_processes = find_claude

        config = self._make_config(tmp_path, reload_delay=60)  # Long delay

        t = threading.Thread(target=lambda: run_monitor_loop(config), daemon=True)
        t.start()

        # Wait for: idle detection + transition to working
        time.sleep(2.5)

        # The idle->working transition should send reload immediately,
        # even though reload_delay is 60s
        working_reloads = [c for c in fake_sender.reload_calls]
        assert len(working_reloads) >= 1

    @patch("companion.claude_monitor.create_keystroke_sender")
    @patch("companion.claude_monitor.create_detector")
    def test_wow_not_running_skips_reload(self, mock_detector, mock_sender, tmp_path):
        fake_sender = FakeKeystrokeSender()
        fake_sender.wow_running = False
        mock_sender.return_value = fake_sender

        mock_proc = MagicMock()
        mock_proc.cpu_percent = 50.0
        mock_detector.return_value.find_claude_processes.return_value = [mock_proc]

        config = self._make_config(tmp_path)

        t = threading.Thread(target=run_monitor_loop, args=(config,), daemon=True)
        t.start()
        time.sleep(1.5)

        # No reloads should have been sent
        assert len(fake_sender.reload_calls) == 0

    @patch("companion.claude_monitor.create_keystroke_sender")
    @patch("companion.claude_monitor.create_detector")
    def test_claude_not_running_writes_closed(self, mock_detector, mock_sender, tmp_path):
        fake_sender = FakeKeystrokeSender()
        mock_sender.return_value = fake_sender
        mock_detector.return_value.find_claude_processes.return_value = []

        config = self._make_config(tmp_path, reload_delay=0)

        t = threading.Thread(target=run_monitor_loop, args=(config,), daemon=True)
        t.start()
        time.sleep(1.5)

        # Should have written the CompanionData file with "closed"
        data_path = (tmp_path / "Interface" / "AddOns" /
                     "ClaudeGuard" / "CompanionData.lua")
        assert data_path.exists()
        content = data_path.read_text()
        assert '"closed"' in content

    @patch("companion.claude_monitor.create_keystroke_sender")
    @patch("companion.claude_monitor.create_detector")
    def test_claude_restart_transitions_through_closed(self, mock_detector, mock_sender, tmp_path):
        """Claude exit then restart should transition closed -> working."""
        fake_sender = FakeKeystrokeSender()
        mock_sender.return_value = fake_sender

        mock_proc_working = MagicMock()
        mock_proc_working.cpu_percent = 50.0

        call_count = [0]
        def find_claude():
            call_count[0] += 1
            if call_count[0] <= 2:
                return [mock_proc_working]  # working
            elif call_count[0] <= 4:
                return []  # Claude gone
            else:
                return [mock_proc_working]  # Claude back

        mock_detector.return_value.find_claude_processes = find_claude
        config = self._make_config(tmp_path, reload_delay=0)

        t = threading.Thread(target=run_monitor_loop, args=(config,), daemon=True)
        t.start()
        time.sleep(3.0)

        # Should have multiple reload calls:
        # none->working, working->closed, closed->working
        assert len(fake_sender.reload_calls) >= 2

    @patch("companion.claude_monitor.create_keystroke_sender")
    @patch("companion.claude_monitor.create_detector")
    def test_wow_not_running_still_writes_savedvariables(self, mock_detector, mock_sender, tmp_path):
        """Even when WoW isn't running, SavedVariables should still be written."""
        fake_sender = FakeKeystrokeSender()
        fake_sender.wow_running = False
        mock_sender.return_value = fake_sender

        mock_proc = MagicMock()
        mock_proc.cpu_percent = 50.0
        mock_detector.return_value.find_claude_processes.return_value = [mock_proc]

        config = self._make_config(tmp_path)

        t = threading.Thread(target=run_monitor_loop, args=(config,), daemon=True)
        t.start()
        time.sleep(1.5)

        data_path = (tmp_path / "Interface" / "AddOns" /
                     "ClaudeGuard" / "CompanionData.lua")
        assert data_path.exists()
        content = data_path.read_text()
        assert '"working"' in content
        assert len(fake_sender.reload_calls) == 0
