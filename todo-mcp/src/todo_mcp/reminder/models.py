"""Data models for the reminder system."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NotificationLevel(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"


@dataclass
class Notification:
    """Represents a notification to be sent."""
    title: str
    level: NotificationLevel
    content: str
    actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReminderRule:
    """Configuration for a reminder rule."""
    type: str
    enabled: bool = True
    channels: list[str] = field(default_factory=lambda: ["chat"])
    params: dict[str, Any] = field(default_factory=dict)
