"""Tests for SavedVariables file writer."""

import os
from pathlib import Path

import pytest
from companion.heuristic import ClaudeStatus
from companion.savedvariables import format_saved_variables, write_saved_variables


class TestFormatSavedVariables:
    def test_idle_status(self):
        result = format_saved_variables(ClaudeStatus.IDLE, timestamp=1709654400)
        assert '"status"] = "idle"' in result
        assert '"lastUpdate"] = 1709654400' in result
        assert result.startswith("ClaudeGuardDB = {")

    def test_working_status(self):
        result = format_saved_variables(ClaudeStatus.WORKING, timestamp=100)
        assert '"status"] = "working"' in result

    def test_closed_status(self):
        result = format_saved_variables(ClaudeStatus.CLOSED, timestamp=100)
        assert '"status"] = "closed"' in result

    def test_default_timestamp_is_current(self):
        import time
        before = int(time.time())
        result = format_saved_variables(ClaudeStatus.IDLE)
        after = int(time.time())
        # Extract timestamp from result
        for line in result.splitlines():
            if "lastUpdate" in line:
                ts = int(line.split("= ")[1].rstrip(","))
                assert before <= ts <= after


class TestWriteSavedVariables:
    def test_writes_file(self, tmp_path):
        path = tmp_path / "SavedVariables" / "ClaudeGuard.lua"
        write_saved_variables(path, ClaudeStatus.IDLE)
        assert path.exists()
        content = path.read_text()
        assert '"status"] = "idle"' in content

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "ClaudeGuard.lua"
        write_saved_variables(path, ClaudeStatus.WORKING)
        assert path.exists()

    def test_overwrites_existing(self, tmp_path):
        path = tmp_path / "ClaudeGuard.lua"
        write_saved_variables(path, ClaudeStatus.IDLE)
        write_saved_variables(path, ClaudeStatus.WORKING)
        content = path.read_text()
        assert '"status"] = "working"' in content
        assert "idle" not in content

    def test_no_temp_files_left_behind(self, tmp_path):
        path = tmp_path / "ClaudeGuard.lua"
        write_saved_variables(path, ClaudeStatus.IDLE)
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "ClaudeGuard.lua"

    def test_valid_lua_syntax(self, tmp_path):
        path = tmp_path / "ClaudeGuard.lua"
        write_saved_variables(path, ClaudeStatus.IDLE)
        content = path.read_text()
        # Basic structural checks for valid Lua
        assert content.count("{") == content.count("}")
        assert content.strip().endswith("}")
        assert "ClaudeGuardDB" in content
