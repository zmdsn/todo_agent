"""Configuration handling for reminder system."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ReminderConfig:
    """Reminder system configuration."""
    enabled: bool = False
    rules: list[dict[str, Any]] = field(default_factory=list)
    channels: dict[str, Any] = field(default_factory=dict)


def load_reminder_config(config_path: Path | str) -> ReminderConfig:
    """Load reminder configuration from YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        ReminderConfig with loaded values or defaults if file doesn't exist.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        return ReminderConfig()

    with open(config_path) as f:
        full_config = yaml.safe_load(f) or {}

    reminder_config = full_config.get("reminders", {})

    return ReminderConfig(
        enabled=reminder_config.get("enabled", False),
        rules=reminder_config.get("rules", []),
        channels=reminder_config.get("channels", {}),
    )
