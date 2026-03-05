"""Tests for the monitor loop's state transition and write logic."""

from pathlib import Path

import pytest
from companion.claude_monitor import load_config, saved_variables_path


class TestLoadConfig:
    def test_loads_valid_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"wow_path": "C:/WoW", "account_name": "TEST", '
                               '"poll_interval_seconds": 2, "cpu_threshold_percent": 3.0, '
                               '"idle_grace_seconds": 5}')
        config = load_config(config_file)
        assert config["wow_path"] == "C:/WoW"
        assert config["account_name"] == "TEST"

    def test_missing_key_raises(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"wow_path": "C:/WoW"}')
        with pytest.raises(KeyError, match="account_name"):
            load_config(config_file)


class TestSavedVariablesPath:
    def test_path_construction(self):
        config = {"wow_path": "C:/WoW/_classic_", "account_name": "MYACCOUNT"}
        path = saved_variables_path(config)
        assert path == Path("C:/WoW/_classic_/WTF/Account/MYACCOUNT/SavedVariables/ClaudeGuard.lua")
