"""Tests for CLI notifier."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import subprocess

from todo_mcp.reminder.models import Notification, NotificationLevel
from todo_mcp.reminder.notifiers.cli import CliNotifier


class TestCliNotifier:
    """Tests for CliNotifier class."""

    @pytest.fixture
    def notification(self):
        """Create a test notification."""
        return Notification(
            title="Test Notification",
            level=NotificationLevel.INFO,
            content="This is a test message",
            actions=["Mark Done", "Snooze"],
        )

    @pytest.fixture
    def simple_notification(self):
        """Create a simple notification without actions."""
        return Notification(
            title="Simple",
            level=NotificationLevel.INFO,
            content="Just a message",
        )

    def test_format_message_with_actions(self, notification):
        """Test message formatting with actions."""
        notifier = CliNotifier()
        result = notifier.format_message(notification)

        assert "Test Notification" in result
        assert "This is a test message" in result
        assert "可执行操作: Mark Done | Snooze" in result
        assert "-" * len("Test Notification") in result

    def test_format_message_without_actions(self, simple_notification):
        """Test message formatting without actions."""
        notifier = CliNotifier()
        result = notifier.format_message(simple_notification)

        assert "Simple" in result
        assert "Just a message" in result
        assert "可执行操作" not in result

    @pytest.mark.asyncio
    async def test_disabled_notifier_returns_false(self, notification):
        """Test that disabled notifier returns False."""
        notifier = CliNotifier(enabled=False)
        result = await notifier.send(notification)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_falls_back_to_print(self, simple_notification, capsys):
        """Test that send prints to terminal when system notification fails."""
        notifier = CliNotifier()

        with patch.object(notifier, '_send_system_notification', return_value=False):
            result = await notifier.send(simple_notification)

        assert result is True
        captured = capsys.readouterr()
        assert "Simple" in captured.out
        assert "Just a message" in captured.out

    @pytest.mark.asyncio
    async def test_send_uses_system_notification(self, notification):
        """Test that send tries system notification first."""
        notifier = CliNotifier()

        with patch.object(notifier, '_send_system_notification', new_callable=AsyncMock) as mock_sys:
            mock_sys.return_value = True
            result = await notifier.send(notification)

        assert result is True
        mock_sys.assert_called_once_with(notification.title, notification.content)

    @pytest.mark.asyncio
    async def test_system_notification_linux_success(self):
        """Test Linux system notification with notify-send."""
        notifier = CliNotifier()

        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = await notifier._send_system_notification("Title", "Message")

        assert result is True
        mock_run.assert_called_once()
        # Check that notify-send was used
        call_args = mock_run.call_args[0][0]
        assert "notify-send" in call_args

    @pytest.mark.asyncio
    async def test_system_notification_linux_no_sound(self):
        """Test Linux notification with sound disabled."""
        notifier = CliNotifier(sound=False)

        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = await notifier._send_system_notification("Title", "Message")

        assert result is True
        # Check that transient hint was added
        call_args = mock_run.call_args[0][0]
        assert "--hint=int:transient:1" in call_args

    @pytest.mark.asyncio
    async def test_system_notification_macos(self):
        """Test macOS system notification with terminal-notifier."""
        notifier = CliNotifier()

        with patch('platform.system', return_value='Darwin'):
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = await notifier._send_system_notification("Title", "Message")

        assert result is True
        call_args = mock_run.call_args[0][0]
        assert "terminal-notifier" in call_args

    @pytest.mark.asyncio
    async def test_system_notification_missing_tool(self):
        """Test graceful handling when system tool is missing."""
        notifier = CliNotifier()

        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.run', side_effect=FileNotFoundError):
                result = await notifier._send_system_notification("Title", "Message")

        assert result is False

    @pytest.mark.asyncio
    async def test_system_notification_failure(self):
        """Test graceful handling when system notification fails."""
        notifier = CliNotifier()

        with patch('platform.system', return_value='Linux'):
            with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cmd')):
                result = await notifier._send_system_notification("Title", "Message")

        assert result is False

    @pytest.mark.asyncio
    async def test_unsupported_platform(self):
        """Test handling of unsupported platforms."""
        notifier = CliNotifier()

        with patch('platform.system', return_value='Windows'):
            result = await notifier._send_system_notification("Title", "Message")

        assert result is False
