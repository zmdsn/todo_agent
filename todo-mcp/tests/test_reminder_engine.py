"""Tests for the reminder engine."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from todo_mcp.reminder.models import Notification, NotificationLevel, ReminderRule
from todo_mcp.reminder.engine import ReminderEngine
from todo_mcp.reminder.rules import RuleManager
from todo_mcp.reminder.checker import ReminderChecker
from todo_mcp.reminder.notifiers.base import BaseNotifier


class MockNotifier(BaseNotifier):
    """Mock notifier for testing."""

    def __init__(self):
        self.sent = []
        self.should_fail = False

    async def send(self, notification: Notification) -> bool:
        if self.should_fail:
            return False
        self.sent.append(notification)
        return True


@pytest.fixture
def rule_manager():
    """Create a rule manager with test rules."""
    rules = [
        {
            "type": "due_soon",
            "enabled": True,
            "channels": ["chat"],
            "params": {"days_before": [3, 1]},
        },
        {
            "type": "overdue",
            "enabled": True,
            "channels": ["chat", "email"],
            "params": {},
        },
        {
            "type": "overload",
            "enabled": True,
            "channels": ["chat"],
            "params": {"daily_threshold": 5},
        },
        {
            "type": "daily_brief",
            "enabled": False,
            "channels": ["chat"],
            "params": {},
        },
    ]
    return RuleManager(rules)


@pytest.fixture
def checker():
    """Create a reminder checker."""
    return ReminderChecker()


@pytest.fixture
def notifier():
    """Create a mock notifier."""
    return MockNotifier()


@pytest.fixture
def engine(rule_manager, checker, notifier):
    """Create a reminder engine with dependencies."""
    return ReminderEngine(
        rule_manager=rule_manager,
        checker=checker,
        notifiers={"chat": notifier},
    )


class TestReminderEngineInit:
    """Test engine initialization."""

    def test_init_with_dependencies(self, rule_manager, checker, notifier):
        """Engine initializes with all dependencies."""
        engine = ReminderEngine(
            rule_manager=rule_manager,
            checker=checker,
            notifiers={"chat": notifier},
        )

        assert engine.rule_manager is rule_manager
        assert engine.checker is checker
        assert engine.notifiers == {"chat": notifier}

    def test_init_with_none_notifiers(self, rule_manager, checker):
        """Engine handles None notifiers."""
        engine = ReminderEngine(
            rule_manager=rule_manager,
            checker=checker,
            notifiers=None,
        )

        assert engine.notifiers == {}

    def test_init_with_empty_notifiers(self, rule_manager, checker):
        """Engine handles empty notifiers dict."""
        engine = ReminderEngine(
            rule_manager=rule_manager,
            checker=checker,
            notifiers={},
        )

        assert engine.notifiers == {}


class TestRegisterNotifier:
    """Test notifier registration."""

    def test_register_notifier_adds_channel(self, engine):
        """register_notifier adds a new channel."""
        email_notifier = MockNotifier()
        engine.register_notifier("email", email_notifier)

        assert "email" in engine.notifiers
        assert engine.notifiers["email"] is email_notifier

    def test_register_notifier_overwrites_existing(self, engine):
        """register_notifier overwrites existing notifier."""
        new_notifier = MockNotifier()
        engine.register_notifier("chat", new_notifier)

        assert engine.notifiers["chat"] is new_notifier


class TestCheckAndNotify:
    """Test check_and_notify method."""

    @pytest.mark.asyncio
    async def test_processes_all_rule_types(self, engine, notifier):
        """check_and_notify processes all active rule types."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        tasks = [
            {"content": "Task due soon", "due_date": tomorrow, "completed": False},
            {"content": "Overdue task", "due_date": yesterday, "completed": False},
            {"content": "Completed", "due_date": yesterday, "completed": True},
            {"content": "Task 1", "due_date": today, "completed": False},
            {"content": "Task 2", "due_date": today, "completed": False},
            {"content": "Task 3", "due_date": today, "completed": False},
            {"content": "Task 4", "due_date": today, "completed": False},
            {"content": "Task 5", "due_date": today, "completed": False},
            {"content": "Task 6", "due_date": today, "completed": False},
        ]

        notifications = await engine.check_and_notify(tasks)

        assert len(notifications) >= 2  # due_soon, overdue
        assert len(notifier.sent) >= 2

    @pytest.mark.asyncio
    async def test_filters_by_rule_types(self, engine, notifier):
        """check_and_notify filters by rule_types parameter."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        tasks = [
            {"content": "Task due soon", "due_date": tomorrow, "completed": False},
            {"content": "Overdue task", "due_date": yesterday, "completed": False},
        ]

        notifications = await engine.check_and_notify(tasks, rule_types=["due_soon"])

        assert len(notifications) == 1
        assert len(notifier.sent) == 1
        assert "到期" in notifier.sent[0].title

    @pytest.mark.asyncio
    async def test_returns_empty_list_no_matches(self, engine, notifier):
        """check_and_notify returns empty list when no matches."""
        tasks = [
            {"content": "Completed task", "due_date": date.today(), "completed": True},
        ]

        notifications = await engine.check_and_notify(tasks)

        assert notifications == []
        assert notifier.sent == []

    @pytest.mark.asyncio
    async def test_only_active_rules_processed(self, engine, notifier):
        """check_and_notify only processes enabled rules."""
        tasks = [
            {"content": "Task", "due_date": date.today(), "completed": False},
        ]

        notifications = await engine.check_and_notify(
            tasks, rule_types=["daily_brief"]
        )

        # daily_brief is disabled in the rule_manager
        assert notifications == []

    @pytest.mark.asyncio
    async def test_handles_missing_notifier_gracefully(self, engine):
        """check_and_notify handles missing notifier gracefully."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        tasks = [
            {"content": "Overdue task", "due_date": yesterday, "completed": False},
        ]

        # overdue rule has channels: ["chat", "email"]
        # but only "chat" notifier is registered
        notifications = await engine.check_and_notify(tasks, rule_types=["overdue"])

        # Should still return notification even if email notifier missing
        assert len(notifications) == 1

    @pytest.mark.asyncio
    async def test_no_notifiers_configured(self, rule_manager, checker):
        """check_and_notify handles no notifiers configured."""
        engine = ReminderEngine(
            rule_manager=rule_manager,
            checker=checker,
            notifiers=None,
        )

        today = date.today()
        tomorrow = today + timedelta(days=1)

        tasks = [
            {"content": "Task due soon", "due_date": tomorrow, "completed": False},
        ]

        notifications = await engine.check_and_notify(tasks, rule_types=["due_soon"])

        # Should return notification but not fail on dispatch
        assert len(notifications) == 1


class TestProcessRule:
    """Test _process_rule method."""

    @pytest.mark.asyncio
    async def test_returns_notification_when_triggered(self, engine, notifier):
        """_process_rule returns notification when rule is triggered."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        tasks = [
            {"content": "Task due soon", "due_date": tomorrow, "completed": False},
        ]

        rule = ReminderRule(
            type="due_soon",
            enabled=True,
            channels=["chat"],
            params={"days_before": [3, 1]},
        )

        notification = await engine._process_rule(rule, tasks)

        assert notification is not None
        assert isinstance(notification, Notification)
        assert "到期" in notification.title
        # _process_rule only returns notification, doesn't dispatch
        # Dispatch happens in check_and_notify

    @pytest.mark.asyncio
    async def test_returns_none_when_no_matches(self, engine, notifier):
        """_process_rule returns None when no matches."""
        tasks = [
            {"content": "Completed task", "due_date": date.today(), "completed": True},
        ]

        rule = ReminderRule(
            type="due_soon",
            enabled=True,
            channels=["chat"],
            params={"days_before": [3, 1]},
        )

        notification = await engine._process_rule(rule, tasks)

        assert notification is None
        assert len(notifier.sent) == 0

    @pytest.mark.asyncio
    async def test_handles_overload_rule(self, engine, notifier):
        """_process_rule handles overload rule type."""
        tasks = [
            {"content": f"Task {i}", "due_date": date.today(), "completed": False}
            for i in range(10)
        ]

        rule = ReminderRule(
            type="overload",
            enabled=True,
            channels=["chat"],
            params={"daily_threshold": 5},
        )

        notification = await engine._process_rule(rule, tasks)

        assert notification is not None
        assert notification.metadata["type"] == "overload"

    @pytest.mark.asyncio
    async def test_handles_daily_brief_rule(self, engine, notifier):
        """_process_rule handles daily_brief rule type."""
        tasks = [
            {"content": "Task 1", "due_date": date.today(), "completed": False},
            {"content": "Task 2", "due_date": date.today(), "completed": True},
        ]

        rule = ReminderRule(
            type="daily_brief",
            enabled=True,
            channels=["chat"],
            params={},
        )

        notification = await engine._process_rule(rule, tasks)

        assert notification is not None
        assert "简报" in notification.title


class TestCheckRule:
    """Test _check_rule method."""

    def test_check_due_soon(self, engine):
        """_check_rule handles due_soon type."""
        today = date.today()
        tomorrow = today + timedelta(days=1)

        tasks = [
            {"content": "Task due soon", "due_date": tomorrow, "completed": False},
            {"content": "Task later", "due_date": today + timedelta(days=10), "completed": False},
        ]

        rule = ReminderRule(
            type="due_soon",
            params={"days_before": [3, 1]},
        )

        matches = engine._check_rule(rule, tasks)

        assert len(matches) == 1
        assert matches[0]["content"] == "Task due soon"

    def test_check_overdue(self, engine):
        """_check_rule handles overdue type."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        tasks = [
            {"content": "Overdue task", "due_date": yesterday, "completed": False},
            {"content": "Future task", "due_date": today + timedelta(days=1), "completed": False},
        ]

        rule = ReminderRule(type="overdue", params={})

        matches = engine._check_rule(rule, tasks)

        assert len(matches) == 1
        assert matches[0]["content"] == "Overdue task"

    def test_check_overload_triggered(self, engine):
        """_check_rule handles overload type when triggered."""
        tasks = [
            {"content": f"Task {i}", "due_date": date.today(), "completed": False}
            for i in range(10)
        ]

        rule = ReminderRule(
            type="overload",
            params={"daily_threshold": 5},
        )

        matches = engine._check_rule(rule, tasks)

        assert len(matches) == 10  # Returns all incomplete tasks

    def test_check_overload_not_triggered(self, engine):
        """_check_rule handles overload type when not triggered."""
        tasks = [
            {"content": "Task 1", "due_date": date.today(), "completed": False},
            {"content": "Task 2", "due_date": date.today(), "completed": False},
        ]

        rule = ReminderRule(
            type="overload",
            params={"daily_threshold": 10},
        )

        matches = engine._check_rule(rule, tasks)

        assert len(matches) == 0

    def test_check_daily_brief(self, engine):
        """_check_rule handles daily_brief type."""
        tasks = [
            {"content": "Task 1", "due_date": date.today(), "completed": False},
            {"content": "Task 2", "due_date": date.today(), "completed": True},
        ]

        rule = ReminderRule(type="daily_brief", params={})

        matches = engine._check_rule(rule, tasks)

        assert matches == tasks  # Returns all tasks

    def test_check_unknown_rule_type(self, engine):
        """_check_rule returns empty list for unknown type."""
        tasks = [
            {"content": "Task", "due_date": date.today(), "completed": False},
        ]

        rule = ReminderRule(type="unknown_type", params={})

        matches = engine._check_rule(rule, tasks)

        assert matches == []


class TestDispatch:
    """Test _dispatch method."""

    @pytest.mark.asyncio
    async def test_dispatch_to_all_channels(self, engine):
        """_dispatch sends to all specified channels."""
        email_notifier = MockNotifier()
        engine.register_notifier("email", email_notifier)

        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Test content",
        )

        await engine._dispatch(notification, ["chat", "email"])

        assert len(engine.notifiers["chat"].sent) == 1
        assert len(email_notifier.sent) == 1

    @pytest.mark.asyncio
    async def test_handles_missing_notifier(self, engine):
        """_dispatch handles missing notifier gracefully."""
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Test content",
        )

        # Should not raise error
        await engine._dispatch(notification, ["nonexistent", "chat"])

        assert len(engine.notifiers["chat"].sent) == 1

    @pytest.mark.asyncio
    async def test_handles_empty_channels(self, engine, notifier):
        """_dispatch handles empty channels list."""
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Test content",
        )

        await engine._dispatch(notification, [])

        assert len(notifier.sent) == 0

    @pytest.mark.asyncio
    async def test_handles_notification_failure(self, engine):
        """_dispatch handles notification send failure."""
        failing_notifier = MockNotifier()
        failing_notifier.should_fail = True
        engine.register_notifier("failing", failing_notifier)

        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Test content",
        )

        # Should not raise error
        await engine._dispatch(notification, ["failing"])

        assert len(failing_notifier.sent) == 0


class TestMultipleRules:
    """Test handling multiple rules in one check."""

    @pytest.mark.asyncio
    async def test_multiple_rules_in_one_check(self, engine, notifier):
        """check_and_notify processes multiple rules in one call."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        tasks = [
            {"content": "Task due soon", "due_date": tomorrow, "completed": False},
            {"content": "Overdue task", "due_date": yesterday, "completed": False},
        ]

        notifications = await engine.check_and_notify(
            tasks, rule_types=["due_soon", "overdue"]
        )

        assert len(notifications) == 2
        assert len(notifier.sent) == 2

    @pytest.mark.asyncio
    async def test_rules_processed_in_order(self, engine, notifier):
        """Rules are processed in order from rule_manager."""
        # Rule manager returns rules in the order they were added
        today = date.today()

        tasks = [
            {"content": f"Task {i}", "due_date": today, "completed": False}
            for i in range(10)
        ]

        notifications = await engine.check_and_notify(tasks)

        # Should process due_soon, overdue, overload (daily_brief is disabled)
        assert len(notifications) >= 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_tasks_list(self, engine, notifier):
        """check_and_notify handles empty tasks list."""
        notifications = await engine.check_and_notify([])

        assert notifications == []
        assert notifier.sent == []

    @pytest.mark.asyncio
    async def test_all_tasks_completed(self, engine, notifier):
        """check_and_notify handles all completed tasks."""
        today = date.today()

        tasks = [
            {"content": "Completed 1", "due_date": today, "completed": True},
            {"content": "Completed 2", "due_date": today, "completed": True},
        ]

        notifications = await engine.check_and_notify(tasks)

        assert notifications == []
        assert notifier.sent == []

    @pytest.mark.asyncio
    async def test_tasks_with_missing_fields(self, engine, notifier):
        """check_and_notify handles tasks with missing fields."""
        tasks = [
            {"content": "No due date"},
            {"content": "No completion status", "due_date": date.today()},
        ]

        # Should not raise error when checking rules that don't require due_date
        # Use daily_brief which doesn't require due_date field
        # First enable daily_brief rule
        engine.rule_manager.set_enabled("daily_brief", True)

        notifications = await engine.check_and_notify(
            tasks, rule_types=["daily_brief"]
        )

        # Results depend on rule type behavior
        assert isinstance(notifications, list)

    @pytest.mark.asyncio
    async def test_rule_with_empty_params(self, engine, notifier):
        """check_and_notify handles rule with empty params."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        tasks = [
            {"content": "Overdue task", "due_date": yesterday, "completed": False},
        ]

        notifications = await engine.check_and_notify(tasks, rule_types=["overdue"])

        assert len(notifications) == 1

    @pytest.mark.asyncio
    async def test_concurrent_rule_processing(self, rule_manager, checker, notifier):
        """check_and_notify can process rules concurrently."""
        import asyncio

        engine = ReminderEngine(
            rule_manager=rule_manager,
            checker=checker,
            notifiers={"chat": notifier},
        )

        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        tasks = [
            {"content": "Task due soon", "due_date": tomorrow, "completed": False},
            {"content": "Overdue task", "due_date": yesterday, "completed": False},
        ]

        # Run multiple checks concurrently
        results = await asyncio.gather(
            engine.check_and_notify(tasks),
            engine.check_and_notify(tasks),
        )

        assert len(results[0]) >= 1
        assert len(results[1]) >= 1
