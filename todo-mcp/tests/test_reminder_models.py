"""Tests for reminder data models."""
from todo_mcp.reminder import Notification, NotificationLevel, ReminderRule


def test_notification_creation():
    """Test Notification creation with all fields."""
    notification = Notification(
        title="Task Due Soon",
        level=NotificationLevel.WARNING,
        content="Task 'Complete report' is due in 2 days",
        actions=["snooze", "dismiss"],
        metadata={"task_id": "2026-Q1-03-12-1"}
    )

    assert notification.title == "Task Due Soon"
    assert notification.level == NotificationLevel.WARNING
    assert notification.content == "Task 'Complete report' is due in 2 days"
    assert notification.actions == ["snooze", "dismiss"]
    assert notification.metadata == {"task_id": "2026-Q1-03-12-1"}


def test_notification_defaults():
    """Test Notification with default values."""
    notification = Notification(
        title="Test",
        level=NotificationLevel.INFO,
        content="Test content"
    )

    assert notification.actions == []
    assert notification.metadata == {}


def test_reminder_rule_defaults():
    """Test ReminderRule with default values."""
    rule = ReminderRule(type="due_soon")

    assert rule.type == "due_soon"
    assert rule.enabled is True
    assert rule.channels == ["chat"]
    assert rule.params == {}


def test_reminder_rule_custom_params():
    """Test ReminderRule with custom params."""
    rule = ReminderRule(
        type="overdue",
        enabled=False,
        channels=["chat", "email"],
        params={"days_before": 3, "repeat": True}
    )

    assert rule.type == "overdue"
    assert rule.enabled is False
    assert rule.channels == ["chat", "email"]
    assert rule.params == {"days_before": 3, "repeat": True}


def test_notification_level_enum():
    """Test NotificationLevel enum values."""
    assert NotificationLevel.INFO == "info"
    assert NotificationLevel.WARNING == "warning"
    assert NotificationLevel.URGENT == "urgent"
