"""Data models for the reminder system."""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NotificationLevel(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"


class Notification(BaseModel):
    """Represents a notification to be sent."""
    title: str
    level: NotificationLevel
    content: str
    actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReminderRule(BaseModel):
    """Configuration for a reminder rule."""
    type: str
    enabled: bool = True
    channels: list[str] = Field(default_factory=lambda: ["chat"])
    params: dict[str, Any] = Field(default_factory=dict)
