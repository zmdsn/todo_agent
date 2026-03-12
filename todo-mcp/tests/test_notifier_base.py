"""Tests for the BaseNotifier abstract class."""
import pytest

from todo_mcp.reminder.models import Notification, NotificationLevel
from todo_mcp.reminder.notifiers import BaseNotifier


class TestBaseNotifier:
    """Tests for BaseNotifier abstract class."""

    def test_cannot_instantiate_directly(self):
        """BaseNotifier should not be instantiable directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseNotifier()

    @pytest.mark.asyncio
    async def test_concrete_implementation_can_send(self):
        """A concrete implementation should be able to send notifications."""
        class MockNotifier(BaseNotifier):
            def __init__(self):
                self.sent = []

            async def send(self, notification: Notification) -> bool:
                self.sent.append(notification)
                return True

        notifier = MockNotifier()
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Test content"
        )

        result = await notifier.send(notification)

        assert result is True
        assert len(notifier.sent) == 1
        assert notifier.sent[0] == notification

    @pytest.mark.asyncio
    async def test_send_method_is_async(self):
        """The send method should be async (awaitable)."""
        class MockNotifier(BaseNotifier):
            async def send(self, notification: Notification) -> bool:
                return True

        notifier = MockNotifier()
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Test content"
        )

        # Verify that send returns a coroutine
        import asyncio
        result = notifier.send(notification)
        assert asyncio.iscoroutine(result)
        # Await it to clean up
        await result
