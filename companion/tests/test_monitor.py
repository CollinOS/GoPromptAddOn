"""Tests for config loading and path construction."""

from pathlib import Path

import pytest
from companion.claude_monitor import load_config, companion_data_path


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

    def test_reload_delay_defaults(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"wow_path": "C:/WoW", "account_name": "TEST", '
                               '"poll_interval_seconds": 2, "cpu_threshold_percent": 3.0, '
                               '"idle_grace_seconds": 5}')
        config = load_config(config_file)
        assert config["reload_delay_seconds"] == 10

    def test_reload_delay_from_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"wow_path": "C:/WoW", "account_name": "TEST", '
                               '"poll_interval_seconds": 2, "cpu_threshold_percent": 3.0, '
                               '"idle_grace_seconds": 5, "reload_delay_seconds": 30}')
        config = load_config(config_file)
        assert config["reload_delay_seconds"] == 30


class TestCompanionDataPath:
    def test_path_construction(self):
        config = {"wow_path": "C:/WoW/_classic_", "account_name": "MYACCOUNT"}
        path = companion_data_path(config)
        assert path == Path("C:/WoW/_classic_/Interface/AddOns/ClaudeGuard/CompanionData.lua")
