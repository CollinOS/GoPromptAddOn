"""Tests for CompanionData file writer."""

import os
from pathlib import Path

import pytest
from companion.heuristic import ClaudeStatus
from companion.savedvariables import format_saved_variables, write_saved_variables


class TestFormatSavedVariables:
    def test_idle_status(self):
        result = format_saved_variables(ClaudeStatus.IDLE, timestamp=1709654400)
        assert 'CLAUDEGUARD_COMPANION_STATUS = "idle"' in result
        assert "CLAUDEGUARD_COMPANION_TIMESTAMP = 1709654400" in result

    def test_working_status(self):
        result = format_saved_variables(ClaudeStatus.WORKING, timestamp=100)
        assert 'CLAUDEGUARD_COMPANION_STATUS = "working"' in result

    def test_closed_status(self):
        result = format_saved_variables(ClaudeStatus.CLOSED, timestamp=100)
        assert 'CLAUDEGUARD_COMPANION_STATUS = "closed"' in result

    def test_default_timestamp_is_current(self):
        import time
        before = int(time.time())
        result = format_saved_variables(ClaudeStatus.IDLE)
        after = int(time.time())
        for line in result.splitlines():
            if "CLAUDEGUARD_COMPANION_TIMESTAMP" in line:
                ts = int(line.split("= ")[1].strip())
                assert before <= ts <= after


class TestWriteSavedVariables:
    def test_writes_file(self, tmp_path):
        path = tmp_path / "CompanionData.lua"
        write_saved_variables(path, ClaudeStatus.IDLE)
        assert path.exists()
        content = path.read_text()
        assert 'CLAUDEGUARD_COMPANION_STATUS = "idle"' in content

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "CompanionData.lua"
        write_saved_variables(path, ClaudeStatus.WORKING)
        assert path.exists()

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "CompanionData.lua"
        write_saved_variables(path, ClaudeStatus.IDLE)
        write_saved_variables(path, ClaudeStatus.WORKING)
        content = path.read_text()
        assert '"working"' in content
        assert "idle" not in content

    def test_no_temp_files_left_behind(self, tmp_path):
        path = tmp_path / "CompanionData.lua"
        write_saved_variables(path, ClaudeStatus.IDLE)
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "CompanionData.lua"

    def test_valid_lua(self, tmp_path):
        path = tmp_path / "CompanionData.lua"
        write_saved_variables(path, ClaudeStatus.IDLE)
        content = path.read_text()
        assert "CLAUDEGUARD_COMPANION_STATUS" in content
        assert "CLAUDEGUARD_COMPANION_TIMESTAMP" in content
