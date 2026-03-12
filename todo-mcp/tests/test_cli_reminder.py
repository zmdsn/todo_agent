"""Tests for CLI reminder commands."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import yaml
from click.testing import CliRunner

from todo_mcp.cli.main import main


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config():
    """Create a temporary config file with reminders enabled."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config = {
            "reminders": {
                "enabled": True,
                "rules": [
                    {
                        "type": "due_soon",
                        "enabled": True,
                        "channels": ["cli"],
                        "params": {"days_before": [3, 1]},
                    },
                    {
                        "type": "overdue",
                        "enabled": True,
                        "channels": ["cli"],
                        "params": {},
                    },
                ],
            }
        }
        yaml.dump(config, f)
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def disabled_config():
    """Create a temporary config file with reminders disabled."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        config = {
            "reminders": {
                "enabled": False,
                "rules": [],
            }
        }
        yaml.dump(config, f)
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def temp_todo_dir():
    """Create a temporary todo directory with sample tasks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        todo_root = Path(tmpdir)

        # Create directory structure
        q1_dir = todo_root / "2026" / "Q1"
        q1_dir.mkdir(parents=True)

        # Create a sample markdown file
        md_file = q1_dir / "03-March.md"
        md_content = """# March Monthly Plan

## March 12

- [ ] Task 1 - pending task
- [x] Task 2 - completed task

## March 15

- [ ] Task 3 with due date
"""
        md_file.write_text(md_content, encoding="utf-8")

        yield todo_root


class TestCheckRemindersCommand:
    """Tests for check-reminders CLI command."""

    def test_command_exists(self, runner):
        """Test that check-reminders command exists."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "check-reminders" in result.output

    def test_check_reminders_disabled(self, runner, disabled_config):
        """Test check-reminders when reminders are disabled."""
        result = runner.invoke(
            main,
            ["check-reminders", "-c", str(disabled_config)]
        )
        assert result.exit_code == 0
        assert "未启用" in result.output

    @patch("todo_mcp.cli.main._collect_tasks")
    @patch("todo_mcp.reminder.engine.ReminderEngine")
    def test_check_reminders_no_tasks(
        self,
        mock_engine_class,
        mock_collect_tasks,
        runner,
        temp_config,
    ):
        """Test check-reminders with no tasks."""
        mock_collect_tasks.return_value = []

        result = runner.invoke(
            main,
            ["check-reminders", "-c", str(temp_config)]
        )
        assert result.exit_code == 0
        assert "未找到任何任务" in result.output

    @patch("todo_mcp.cli.main._collect_tasks")
    @patch("todo_mcp.reminder.engine.ReminderEngine")
    def test_check_reminders_with_tasks(
        self,
        mock_engine_class,
        mock_collect_tasks,
        runner,
        temp_config,
    ):
        """Test check-reminders with tasks."""
        mock_collect_tasks.return_value = [
            {"id": "1", "content": "Task 1", "completed": False},
            {"id": "2", "content": "Task 2", "completed": False},
        ]

        # Mock the engine
        mock_engine = MagicMock()
        mock_engine.check_and_notify = AsyncMock(return_value=[])
        mock_engine_class.return_value = mock_engine

        result = runner.invoke(
            main,
            ["check-reminders", "-c", str(temp_config)]
        )
        assert result.exit_code == 0
        assert "检查 2 个任务" in result.output

    @patch("todo_mcp.cli.main._collect_tasks")
    @patch("todo_mcp.reminder.engine.ReminderEngine")
    def test_check_reminders_with_notifications(
        self,
        mock_engine_class,
        mock_collect_tasks,
        runner,
        temp_config,
    ):
        """Test check-reminders with notifications sent."""
        mock_collect_tasks.return_value = [
            {"id": "1", "content": "Task 1", "completed": False},
        ]

        # Mock the engine with a notification
        from todo_mcp.reminder.models import Notification, NotificationLevel
        mock_notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Test content",
        )

        mock_engine = MagicMock()
        mock_engine.check_and_notify = AsyncMock(return_value=[mock_notification])
        mock_engine_class.return_value = mock_engine

        result = runner.invoke(
            main,
            ["check-reminders", "-c", str(temp_config)]
        )
        assert result.exit_code == 0
        assert "已发送 1 个提醒通知" in result.output


class TestReminderDaemonCommand:
    """Tests for reminder-daemon CLI command."""

    def test_command_exists(self, runner):
        """Test that reminder-daemon command exists."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "reminder-daemon" in result.output

    def test_daemon_disabled(self, runner, disabled_config):
        """Test reminder-daemon when reminders are disabled."""
        result = runner.invoke(
            main,
            ["reminder-daemon", "-c", str(disabled_config)]
        )
        assert result.exit_code == 0
        assert "未启用" in result.output

    @patch("todo_mcp.reminder.scheduler.ReminderScheduler")
    @patch("todo_mcp.cli.main._collect_tasks")
    def test_daemon_starts(
        self,
        mock_collect_tasks,
        mock_scheduler_class,
        runner,
        temp_config,
    ):
        """Test that daemon starts correctly."""
        mock_collect_tasks.return_value = []

        # Mock scheduler to raise CancelledError immediately
        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock(side_effect=asyncio.CancelledError)
        mock_scheduler.stop = AsyncMock()
        mock_scheduler_class.return_value = mock_scheduler

        result = runner.invoke(
            main,
            ["reminder-daemon", "-c", str(temp_config), "-i", "60"]
        )
        # The daemon was invoked
        assert "启动提醒守护进程" in result.output


class TestCollectTasks:
    """Tests for _collect_tasks helper function."""

    def test_collect_from_empty_directory(self):
        """Test collecting tasks from empty directory."""
        from todo_mcp.cli.main import _collect_tasks

        with tempfile.TemporaryDirectory() as tmpdir:
            tasks = _collect_tasks(Path(tmpdir))
            assert tasks == []

    def test_collect_from_nonexistent_directory(self):
        """Test collecting tasks from nonexistent directory."""
        from todo_mcp.cli.main import _collect_tasks

        tasks = _collect_tasks(Path("/nonexistent/path"))
        assert tasks == []

    def test_collect_tasks(self, temp_todo_dir):
        """Test collecting tasks from todo directory."""
        from todo_mcp.cli.main import _collect_tasks

        tasks = _collect_tasks(temp_todo_dir)

        # Should find 3 tasks (2 pending + 1 completed)
        assert len(tasks) == 3

        # Check task structure
        pending_tasks = [t for t in tasks if not t["completed"]]
        completed_tasks = [t for t in tasks if t["completed"]]

        assert len(pending_tasks) == 2
        assert len(completed_tasks) == 1

        # Check task fields
        for task in tasks:
            assert "id" in task
            assert "content" in task
            assert "completed" in task
            assert "location" in task
