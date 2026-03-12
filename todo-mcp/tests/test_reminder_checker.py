"""Tests for reminder checker."""

from datetime import date, timedelta

import pytest

from todo_mcp.reminder.checker import ReminderChecker
from todo_mcp.reminder.models import NotificationLevel, ReminderRule


class TestCheckDueSoon:
    """Tests for check_due_soon method."""

    def test_matches_tasks_within_threshold(self):
        """Should find tasks due within the specified days."""
        checker = ReminderChecker()
        today = date.today()

        tasks = [
            {
                "content": "Task due in 1 day",
                "due_date": today + timedelta(days=1),
                "completed": False,
            },
            {
                "content": "Task due in 3 days",
                "due_date": today + timedelta(days=3),
                "completed": False,
            },
            {
                "content": "Task due in 10 days",
                "due_date": today + timedelta(days=10),
                "completed": False,
            },
        ]

        rule = ReminderRule(type="due_soon", params={"days_before": [3, 1]})
        matches = checker.check_due_soon(tasks, rule)

        assert len(matches) == 2
        assert matches[0]["content"] == "Task due in 1 day"
        assert matches[0]["days_until"] == 1
        assert matches[1]["content"] == "Task due in 3 days"
        assert matches[1]["days_until"] == 3

    def test_excludes_completed_tasks(self):
        """Should exclude completed tasks."""
        checker = ReminderChecker()
        today = date.today()

        tasks = [
            {
                "content": "Completed task",
                "due_date": today + timedelta(days=1),
                "completed": True,
            },
            {
                "content": "Incomplete task",
                "due_date": today + timedelta(days=1),
                "completed": False,
            },
        ]

        rule = ReminderRule(type="due_soon", params={"days_before": [3, 1]})
        matches = checker.check_due_soon(tasks, rule)

        assert len(matches) == 1
        assert matches[0]["content"] == "Incomplete task"

    def test_handles_string_due_dates(self):
        """Should handle ISO format string dates."""
        checker = ReminderChecker()
        today = date.today()
        due_date = today + timedelta(days=2)

        tasks = [
            {
                "content": "Task with string date",
                "due_date": due_date.isoformat(),
                "completed": False,
            },
        ]

        rule = ReminderRule(type="due_soon", params={"days_before": [3, 1]})
        matches = checker.check_due_soon(tasks, rule)

        assert len(matches) == 1
        assert matches[0]["days_until"] == 2

    def test_excludes_tasks_due_today_or_past(self):
        """Should only include future tasks."""
        checker = ReminderChecker()
        today = date.today()

        tasks = [
            {
                "content": "Task due today",
                "due_date": today,
                "completed": False,
            },
            {
                "content": "Task due yesterday",
                "due_date": today - timedelta(days=1),
                "completed": False,
            },
            {
                "content": "Task due tomorrow",
                "due_date": today + timedelta(days=1),
                "completed": False,
            },
        ]

        rule = ReminderRule(type="due_soon", params={"days_before": [3, 1]})
        matches = checker.check_due_soon(tasks, rule)

        assert len(matches) == 1
        assert matches[0]["content"] == "Task due tomorrow"


class TestCheckOverdue:
    """Tests for check_overdue method."""

    def test_matches_overdue_incomplete_tasks(self):
        """Should find overdue incomplete tasks."""
        checker = ReminderChecker()
        today = date.today()

        tasks = [
            {
                "content": "Task overdue by 1 day",
                "due_date": today - timedelta(days=1),
                "completed": False,
            },
            {
                "content": "Task overdue by 5 days",
                "due_date": today - timedelta(days=5),
                "completed": False,
            },
            {
                "content": "Task due tomorrow",
                "due_date": today + timedelta(days=1),
                "completed": False,
            },
        ]

        rule = ReminderRule(type="overdue")
        matches = checker.check_overdue(tasks, rule)

        assert len(matches) == 2
        assert matches[0]["days_overdue"] == 1
        assert matches[1]["days_overdue"] == 5

    def test_excludes_completed_overdue_tasks(self):
        """Should exclude completed tasks even if overdue."""
        checker = ReminderChecker()
        today = date.today()

        tasks = [
            {
                "content": "Completed overdue task",
                "due_date": today - timedelta(days=3),
                "completed": True,
            },
            {
                "content": "Incomplete overdue task",
                "due_date": today - timedelta(days=2),
                "completed": False,
            },
        ]

        rule = ReminderRule(type="overdue")
        matches = checker.check_overdue(tasks, rule)

        assert len(matches) == 1
        assert matches[0]["content"] == "Incomplete overdue task"

    def test_handles_string_dates(self):
        """Should handle ISO format string dates."""
        checker = ReminderChecker()
        today = date.today()
        overdue_date = today - timedelta(days=2)

        tasks = [
            {
                "content": "Overdue task",
                "due_date": overdue_date.isoformat(),
                "completed": False,
            },
        ]

        rule = ReminderRule(type="overdue")
        matches = checker.check_overdue(tasks, rule)

        assert len(matches) == 1
        assert matches[0]["days_overdue"] == 2


class TestCheckOverload:
    """Tests for check_overload method."""

    def test_returns_true_when_over_threshold(self):
        """Should return True when task count exceeds threshold."""
        checker = ReminderChecker()

        tasks = [
            {"content": f"Task {i}", "completed": False} for i in range(15)
        ]

        rule = ReminderRule(type="overload", params={"daily_threshold": 10})
        result = checker.check_overload(tasks, rule, period="daily")

        assert result is True

    def test_returns_false_when_under_threshold(self):
        """Should return False when task count is under threshold."""
        checker = ReminderChecker()

        tasks = [
            {"content": f"Task {i}", "completed": False} for i in range(5)
        ]

        rule = ReminderRule(type="overload", params={"daily_threshold": 10})
        result = checker.check_overload(tasks, rule, period="daily")

        assert result is False

    def test_excludes_completed_tasks(self):
        """Should only count incomplete tasks."""
        checker = ReminderChecker()

        tasks = [
            {"content": f"Incomplete {i}", "completed": False} for i in range(6)
        ] + [
            {"content": f"Completed {i}", "completed": True} for i in range(10)
        ]

        rule = ReminderRule(type="overload", params={"daily_threshold": 5})
        result = checker.check_overload(tasks, rule, period="daily")

        assert result is True  # Only 6 incomplete, over threshold of 5

    def test_supports_weekly_threshold(self):
        """Should support weekly threshold."""
        checker = ReminderChecker()

        tasks = [
            {"content": f"Task {i}", "completed": False} for i in range(25)
        ]

        rule = ReminderRule(type="overload", params={"weekly_threshold": 20})
        result = checker.check_overload(tasks, rule, period="weekly")

        assert result is True


class TestBuildNotification:
    """Tests for build_notification method."""

    def test_returns_none_when_no_matches(self):
        """Should return None when matches list is empty."""
        checker = ReminderChecker()

        result = checker.build_notification("due_soon", [])
        assert result is None

    def test_builds_due_soon_notification(self):
        """Should build notification for due_soon rule."""
        checker = ReminderChecker()

        matches = [
            {"content": "Task 1", "days_until": 1},
            {"content": "Task 2", "days_until": 3},
        ]

        notification = checker.build_notification("due_soon", matches)

        assert notification is not None
        assert notification.title == "📅 任务即将到期"
        assert notification.level == NotificationLevel.WARNING
        assert "Task 1" in notification.content
        assert "Task 2" in notification.content
        assert notification.metadata["count"] == 2
        assert notification.metadata["type"] == "due_soon"

    def test_builds_overdue_notification(self):
        """Should build notification for overdue rule."""
        checker = ReminderChecker()

        matches = [
            {"content": "Overdue Task 1", "days_overdue": 2},
            {"content": "Overdue Task 2", "days_overdue": 5},
        ]

        notification = checker.build_notification("overdue", matches)

        assert notification is not None
        assert notification.title == "⚠️ 任务逾期提醒"
        assert notification.level == NotificationLevel.URGENT
        assert "Overdue Task 1" in notification.content
        assert "Overdue Task 2" in notification.content
        assert notification.metadata["count"] == 2
        assert notification.metadata["type"] == "overdue"

    def test_builds_overload_notification(self):
        """Should build notification for overload rule."""
        checker = ReminderChecker()

        matches = [{"content": f"Task {i}"} for i in range(15)]

        notification = checker.build_notification(
            "overload", matches, period="daily"
        )

        assert notification is not None
        assert notification.title == "⚡ 任务量提醒"
        assert notification.level == NotificationLevel.WARNING
        assert "15" in notification.content
        assert notification.metadata["count"] == 15
        assert notification.metadata["type"] == "overload"

    def test_builds_daily_brief_notification(self):
        """Should build notification for daily_brief rule."""
        checker = ReminderChecker()

        matches = [
            {"content": "Task 1", "completed": False},
            {"content": "Task 2", "completed": False},
            {"content": "Task 3", "completed": True},
        ]

        notification = checker.build_notification("daily_brief", matches)

        assert notification is not None
        assert "今日简报" in notification.title
        assert notification.level == NotificationLevel.INFO
        assert "2" in notification.content  # 2 incomplete tasks
        assert notification.metadata["count"] == 2
        assert notification.metadata["type"] == "daily_brief"

    def test_returns_none_for_unknown_rule_type(self):
        """Should return None for unknown rule types."""
        checker = ReminderChecker()

        matches = [{"content": "Task 1"}]
        result = checker.build_notification("unknown_type", matches)

        assert result is None


class TestDailyBriefFormatting:
    """Tests for daily brief notification formatting."""

    def test_shows_max_five_tasks(self):
        """Should show at most 5 tasks in brief."""
        checker = ReminderChecker()

        matches = [
            {"content": f"Task {i}", "completed": False} for i in range(10)
        ]

        notification = checker.build_notification("daily_brief", matches)

        assert notification is not None
        # Should show first 5 tasks
        assert "Task 0" in notification.content
        assert "Task 4" in notification.content
        # Should mention remaining tasks
        assert "5" in notification.content  # "还有 5 个任务"

    def test_excludes_completed_tasks_from_count(self):
        """Should only count incomplete tasks."""
        checker = ReminderChecker()

        matches = [
            {"content": "Incomplete 1", "completed": False},
            {"content": "Incomplete 2", "completed": False},
            {"content": "Completed", "completed": True},
        ]

        notification = checker.build_notification("daily_brief", matches)

        assert notification is not None
        assert notification.metadata["count"] == 2
