"""Tests for the reminder scheduler."""

import asyncio
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todo_mcp.reminder.models import Notification, NotificationLevel, ReminderRule
from todo_mcp.reminder.engine import ReminderEngine
from todo_mcp.reminder.rules import RuleManager
from todo_mcp.reminder.checker import ReminderChecker
from todo_mcp.reminder.scheduler import ReminderScheduler
from todo_mcp.reminder.notifiers.base import BaseNotifier


class MockNotifier(BaseNotifier):
    """Mock notifier for testing."""

    def __init__(self):
        self.sent = []

    async def send(self, notification: Notification) -> bool:
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
            "channels": ["chat"],
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
            "enabled": True,
            "channels": ["chat"],
            "params": {"time": "09:00"},
        },
        {
            "type": "weekly_review",
            "enabled": True,
            "channels": ["chat"],
            "params": {"day": "monday", "time": "10:00"},
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


@pytest.fixture
def mock_tasks():
    """Create mock tasks for testing."""
    from datetime import date, timedelta

    today = date.today()
    return [
        {"content": "Task due soon", "due_date": today + timedelta(days=1), "completed": False},
        {"content": "Overdue task", "due_date": today - timedelta(days=1), "completed": False},
        {"content": "Task 1", "due_date": today, "completed": False},
        {"content": "Task 2", "due_date": today, "completed": False},
    ]


class TestReminderSchedulerInit:
    """Test scheduler initialization."""

    def test_init_with_engine(self, engine):
        """Scheduler initializes with engine."""
        scheduler = ReminderScheduler(engine=engine)

        assert scheduler.engine is engine
        assert scheduler.monitor_interval == 300
        assert scheduler.get_tasks is None
        assert scheduler._running is False

    def test_init_with_custom_interval(self, engine):
        """Scheduler accepts custom monitor interval."""
        scheduler = ReminderScheduler(engine=engine, monitor_interval=600)

        assert scheduler.monitor_interval == 600

    def test_init_with_callback(self, engine):
        """Scheduler accepts get_tasks callback."""
        async def get_tasks():
            return []

        scheduler = ReminderScheduler(engine=engine, get_tasks_callback=get_tasks)

        assert scheduler.get_tasks is get_tasks


class TestSchedulerLifecycle:
    """Test scheduler start and stop."""

    @pytest.mark.asyncio
    async def test_start_sets_running_flag(self, engine):
        """Start sets _running flag to True."""
        scheduler = ReminderScheduler(engine=engine)

        # Start should set running but we need to stop it quickly
        task = asyncio.create_task(scheduler.start())

        # Give it a moment to start
        await asyncio.sleep(0.1)

        # The scheduler should have started
        assert scheduler._running or task.done()

        # Stop the scheduler
        await scheduler.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self, engine):
        """Stop cancels all running tasks."""
        scheduler = ReminderScheduler(engine=engine)

        task = asyncio.create_task(scheduler.start())
        await asyncio.sleep(0.1)

        await scheduler.stop()

        # Tasks should be cancelled
        assert all(t.cancelled() or t.done() for t in scheduler._tasks)

        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_stop_handles_already_stopped(self, engine):
        """Stop handles already stopped scheduler."""
        scheduler = ReminderScheduler(engine=engine)

        # Should not raise error
        await scheduler.stop()


class TestMonitorMode:
    """Test continuous monitoring for condition-based rules."""

    @pytest.mark.asyncio
    async def test_monitor_checks_rules_periodically(self, engine, mock_tasks):
        """Monitor checks rules at specified interval."""
        call_count = 0

        async def get_tasks():
            nonlocal call_count
            call_count += 1
            return mock_tasks

        scheduler = ReminderScheduler(
            engine=engine,
            monitor_interval=0.1,  # Fast interval for testing
            get_tasks_callback=get_tasks,
        )

        scheduler._running = True  # Set running flag before starting
        task = asyncio.create_task(scheduler._run_monitor())

        # Wait for multiple check cycles
        await asyncio.sleep(0.35)

        scheduler._running = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have checked at least 2 times
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_monitor_handles_errors(self, engine, mock_tasks):
        """Monitor continues running after errors."""
        call_count = 0

        async def get_tasks():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            return mock_tasks

        scheduler = ReminderScheduler(
            engine=engine,
            monitor_interval=0.1,
            get_tasks_callback=get_tasks,
        )

        scheduler._running = True  # Set running flag before starting
        task = asyncio.create_task(scheduler._run_monitor())

        # Wait for error recovery
        await asyncio.sleep(0.35)

        scheduler._running = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have continued after error
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_monitor_checks_condition_rules(self, engine, mock_tasks, notifier):
        """Monitor checks due_soon, overdue, overload rules."""
        scheduler = ReminderScheduler(
            engine=engine,
            monitor_interval=0.1,
            get_tasks_callback=lambda: mock_tasks,
        )

        scheduler._running = True  # Set running flag before starting
        task = asyncio.create_task(scheduler._run_monitor())

        # Wait for at least one check
        await asyncio.sleep(0.15)

        scheduler._running = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have sent notifications for condition rules
        assert len(notifier.sent) >= 1


class TestScheduledMode:
    """Test scheduled tasks (daily_brief, weekly_review)."""

    @pytest.mark.asyncio
    async def test_should_run_daily_at_correct_time(self, engine):
        """_should_run_daily returns True at scheduled time."""
        scheduler = ReminderScheduler(engine=engine)

        # Mock current time to be 09:00
        now = datetime(2024, 3, 15, 9, 0)

        result = scheduler._should_run_daily(now, "09:00")
        assert result is True

    @pytest.mark.asyncio
    async def test_should_run_daily_wrong_time(self, engine):
        """_should_run_daily returns False at wrong time."""
        scheduler = ReminderScheduler(engine=engine)

        # Mock current time to be 10:00
        now = datetime(2024, 3, 15, 10, 0)

        result = scheduler._should_run_daily(now, "09:00")
        assert result is False

    @pytest.mark.asyncio
    async def test_should_run_weekly_correct_day(self, engine):
        """_should_run_weekly returns True on correct day."""
        scheduler = ReminderScheduler(engine=engine)

        # March 15, 2024 is a Friday
        now = datetime(2024, 3, 15, 10, 0)

        # Friday
        result = scheduler._should_run_weekly(now, "friday", "10:00")
        assert result is True

    @pytest.mark.asyncio
    async def test_should_run_weekly_wrong_day(self, engine):
        """_should_run_weekly returns False on wrong day."""
        scheduler = ReminderScheduler(engine=engine)

        # March 15, 2024 is a Friday
        now = datetime(2024, 3, 15, 10, 0)

        # Monday
        result = scheduler._should_run_weekly(now, "monday", "10:00")
        assert result is False

    @pytest.mark.asyncio
    async def test_scheduled_runs_daily_brief(self, engine, mock_tasks, notifier):
        """Scheduled mode runs daily brief at scheduled time."""
        scheduler = ReminderScheduler(
            engine=engine,
            monitor_interval=0.1,
            get_tasks_callback=lambda: mock_tasks,
        )

        # Mock time to be 09:00
        with patch('todo_mcp.reminder.scheduler.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 3, 15, 9, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            scheduler._running = True  # Set running flag before starting
            task = asyncio.create_task(scheduler._run_scheduled())

            # Wait for check
            await asyncio.sleep(0.15)

            scheduler._running = False
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            # Should have sent daily brief notification
            assert len(notifier.sent) >= 1
            assert any("简报" in n.title for n in notifier.sent)

    @pytest.mark.asyncio
    async def test_scheduled_runs_weekly_review(self, engine, mock_tasks, notifier):
        """Scheduled mode runs weekly review on correct day and time."""
        scheduler = ReminderScheduler(
            engine=engine,
            monitor_interval=0.1,
            get_tasks_callback=lambda: mock_tasks,
        )

        # Mock time to be Monday 10:00 (matches rule_manager fixture)
        with patch('todo_mcp.reminder.scheduler.datetime') as mock_datetime:
            # Monday, March 11, 2024, 10:00
            mock_datetime.now.return_value = datetime(2024, 3, 11, 10, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            scheduler._running = True  # Set running flag before starting
            task = asyncio.create_task(scheduler._run_scheduled())

            # Wait for check
            await asyncio.sleep(0.15)

            scheduler._running = False
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            # Should have sent weekly review notification
            assert len(notifier.sent) >= 1


class TestHelperMethods:
    """Test helper methods."""

    def test_parse_time_string(self, engine):
        """_parse_time correctly parses time string."""
        scheduler = ReminderScheduler(engine=engine)

        result = scheduler._parse_time("09:30")

        assert result == time(9, 30)

    def test_parse_time_invalid(self, engine):
        """_parse_time handles invalid time string."""
        scheduler = ReminderScheduler(engine=engine)

        result = scheduler._parse_time("invalid")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_tasks_with_callback(self, engine, mock_tasks):
        """_get_tasks uses callback when available."""
        scheduler = ReminderScheduler(
            engine=engine,
            get_tasks_callback=lambda: mock_tasks,
        )

        result = await scheduler._get_tasks()

        assert result == mock_tasks

    @pytest.mark.asyncio
    async def test_get_tasks_without_callback(self, engine):
        """_get_tasks returns empty list when no callback."""
        scheduler = ReminderScheduler(engine=engine)

        result = await scheduler._get_tasks()

        assert result == []


class TestIntegration:
    """Integration tests for scheduler."""

    @pytest.mark.asyncio
    async def test_full_scheduler_lifecycle(self, engine, mock_tasks, notifier):
        """Test complete scheduler lifecycle."""
        scheduler = ReminderScheduler(
            engine=engine,
            monitor_interval=0.1,
            get_tasks_callback=lambda: mock_tasks,
        )

        # Start scheduler
        task = asyncio.create_task(scheduler.start())

        # Let it run for a bit
        await asyncio.sleep(0.3)

        # Stop scheduler
        await scheduler.stop()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have processed some rules
        assert len(notifier.sent) >= 1

    @pytest.mark.asyncio
    async def test_scheduler_handles_no_rules(self, checker, notifier):
        """Scheduler handles when no rules are configured."""
        rule_manager = RuleManager([])  # Empty rules
        engine = ReminderEngine(
            rule_manager=rule_manager,
            checker=checker,
            notifiers={"chat": notifier},
        )

        scheduler = ReminderScheduler(
            engine=engine,
            monitor_interval=0.1,
            get_tasks_callback=lambda: [],
        )

        task = asyncio.create_task(scheduler._run_monitor())

        # Let it run
        await asyncio.sleep(0.15)

        scheduler._running = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should not crash
        assert True

    @pytest.mark.asyncio
    async def test_scheduler_handles_no_tasks(self, engine, notifier):
        """Scheduler handles when no tasks are available."""
        scheduler = ReminderScheduler(
            engine=engine,
            monitor_interval=0.1,
            get_tasks_callback=lambda: [],
        )

        task = asyncio.create_task(scheduler._run_monitor())

        # Let it run
        await asyncio.sleep(0.15)

        scheduler._running = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should not crash and not send notifications
        assert len(notifier.sent) == 0
