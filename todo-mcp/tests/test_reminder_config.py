"""Tests for reminder configuration loading."""

from pathlib import Path
import tempfile

import pytest

from todo_mcp.reminder.config import ReminderConfig, load_reminder_config


class TestReminderConfig:
    """Tests for ReminderConfig dataclass."""

    def test_default_values(self):
        """Test that ReminderConfig has correct defaults."""
        config = ReminderConfig()

        assert config.enabled is False
        assert config.rules == []
        assert config.channels == {}

    def test_custom_values(self):
        """Test ReminderConfig with custom values."""
        config = ReminderConfig(
            enabled=True,
            rules=[{"type": "deadline", "days": 1}],
            channels={"chat": {"enabled": True}},
        )

        assert config.enabled is True
        assert len(config.rules) == 1
        assert config.rules[0]["type"] == "deadline"
        assert config.channels == {"chat": {"enabled": True}}


class TestLoadReminderConfig:
    """Tests for load_reminder_config function."""

    def test_load_missing_file_returns_defaults(self):
        """Test that loading a missing file returns default config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.yaml"
            config = load_reminder_config(config_path)

            assert config.enabled is False
            assert config.rules == []
            assert config.channels == {}

    def test_load_valid_file(self):
        """Test loading a valid config file."""
        yaml_content = """
reminders:
  enabled: true
  rules:
    - type: deadline
      days: 1
      channels:
        - chat
    - type: recurring
      interval: daily
  channels:
    chat:
      enabled: true
    webhook:
      url: https://example.com/webhook
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(yaml_content)

            config = load_reminder_config(config_path)

            assert config.enabled is True
            assert len(config.rules) == 2
            assert config.rules[0]["type"] == "deadline"
            assert config.rules[1]["type"] == "recurring"
            assert "chat" in config.channels
            assert "webhook" in config.channels

    def test_load_empty_file_returns_defaults(self):
        """Test that loading an empty file returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "empty.yaml"
            config_path.write_text("")

            config = load_reminder_config(config_path)

            assert config.enabled is False
            assert config.rules == []
            assert config.channels == {}

    def test_load_file_without_reminders_key_returns_defaults(self):
        """Test that loading a file without 'reminders' key returns defaults."""
        yaml_content = """
other_section:
  enabled: true
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(yaml_content)

            config = load_reminder_config(config_path)

            assert config.enabled is False
            assert config.rules == []
            assert config.channels == {}

    def test_load_partial_config(self):
        """Test loading a file with partial reminder config."""
        yaml_content = """
reminders:
  enabled: true
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(yaml_content)

            config = load_reminder_config(config_path)

            assert config.enabled is True
            assert config.rules == []
            assert config.channels == {}

    def test_load_with_string_path(self):
        """Test loading config with string path instead of Path object."""
        yaml_content = """
reminders:
  enabled: true
  rules:
    - type: test
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(yaml_content)

            # Pass as string, not Path
            config = load_reminder_config(str(config_path))

            assert config.enabled is True
            assert len(config.rules) == 1

    def test_load_complex_rules(self):
        """Test loading config with complex rule parameters."""
        yaml_content = """
reminders:
  enabled: true
  rules:
    - type: deadline
      days: [1, 3, 7]
      level: urgent
      channels:
        - chat
        - webhook
      filters:
        priority: high
    - type: start_date
      days_before: 2
      level: info
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(yaml_content)

            config = load_reminder_config(config_path)

            assert config.enabled is True
            assert len(config.rules) == 2
            # Check first rule has complex structure
            assert config.rules[0]["days"] == [1, 3, 7]
            assert config.rules[0]["level"] == "urgent"
            assert "filters" in config.rules[0]
            # Check second rule
            assert config.rules[1]["type"] == "start_date"
            assert config.rules[1]["days_before"] == 2
