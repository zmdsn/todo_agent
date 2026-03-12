"""Tests for webhook notification channel."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from todo_mcp.reminder.notifiers.webhook import WebhookNotifier, WebhookEndpoint
from todo_mcp.reminder.models import Notification, NotificationLevel


class TestWebhookEndpoint:
    """Tests for WebhookEndpoint dataclass."""

    def test_webhook_endpoint_creation(self):
        """Test creating a webhook endpoint."""
        endpoint = WebhookEndpoint(
            name="test",
            url="https://example.com/webhook"
        )
        assert endpoint.name == "test"
        assert endpoint.url == "https://example.com/webhook"
        assert endpoint.template == "text"  # default

    def test_webhook_endpoint_with_markdown_template(self):
        """Test creating endpoint with markdown template."""
        endpoint = WebhookEndpoint(
            name="markdown",
            url="https://example.com/webhook",
            template="markdown"
        )
        assert endpoint.template == "markdown"

    def test_webhook_endpoint_with_json_template(self):
        """Test creating endpoint with json template."""
        endpoint = WebhookEndpoint(
            name="json",
            url="https://example.com/webhook",
            template="json"
        )
        assert endpoint.template == "json"


class TestWebhookNotifierFormatting:
    """Tests for message formatting."""

    def test_format_text_template(self):
        """Test formatting notification as plain text."""
        notifier = WebhookNotifier([])
        notification = Notification(
            title="Test Title",
            level=NotificationLevel.INFO,
            content="Test content"
        )
        result = notifier._format_message(notification, "text")
        assert result == "Test Title\nTest content"

    def test_format_markdown_template(self):
        """Test formatting notification as markdown."""
        notifier = WebhookNotifier([])
        notification = Notification(
            title="Test Title",
            level=NotificationLevel.WARNING,
            content="Test content",
            actions=["Action 1", "Action 2"]
        )
        result = notifier._format_message(notification, "markdown")
        expected = "**Test Title**\n\nTest content\n\n> 操作: Action 1 | Action 2"
        assert result == expected

    def test_format_markdown_template_without_actions(self):
        """Test formatting notification as markdown without actions."""
        notifier = WebhookNotifier([])
        notification = Notification(
            title="Test Title",
            level=NotificationLevel.INFO,
            content="Test content"
        )
        result = notifier._format_message(notification, "markdown")
        expected = "**Test Title**\n\nTest content"
        assert result == expected

    def test_format_json_template(self):
        """Test formatting notification as JSON."""
        notifier = WebhookNotifier([])
        notification = Notification(
            title="Test Title",
            level=NotificationLevel.URGENT,
            content="Test content",
            actions=["Action 1"]
        )
        result = notifier._format_message(notification, "json")
        assert result == {
            "title": "Test Title",
            "level": "urgent",
            "content": "Test content",
            "actions": ["Action 1"]
        }


class TestWebhookNotifierSend:
    """Tests for sending notifications."""

    @pytest.mark.asyncio
    async def test_send_success_text_template(self):
        """Test successful send with text template."""
        endpoint = WebhookEndpoint(
            name="test",
            url="https://example.com/webhook",
            template="text"
        )
        notifier = WebhookNotifier([endpoint])
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Content"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_context = AsyncMock()
            mock_context.post = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_client.return_value = mock_context

            result = await notifier.send(notification)
            assert result is True

            mock_context.post.assert_called_once()
            call_args = mock_context.post.call_args
            assert call_args[0][0] == "https://example.com/webhook"
            assert call_args[1]["json"]["msgtype"] == "text"
            assert "Test" in call_args[1]["json"]["text"]["content"]

    @pytest.mark.asyncio
    async def test_send_success_markdown_template(self):
        """Test successful send with markdown template."""
        endpoint = WebhookEndpoint(
            name="test",
            url="https://example.com/webhook",
            template="markdown"
        )
        notifier = WebhookNotifier([endpoint])
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Content"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_context = AsyncMock()
            mock_context.post = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_client.return_value = mock_context

            result = await notifier.send(notification)
            assert result is True

            mock_context.post.assert_called_once()
            call_args = mock_context.post.call_args
            assert call_args[1]["json"]["msgtype"] == "markdown"
            assert "**Test**" in call_args[1]["json"]["markdown"]["content"]

    @pytest.mark.asyncio
    async def test_send_success_json_template(self):
        """Test successful send with json template."""
        endpoint = WebhookEndpoint(
            name="test",
            url="https://example.com/webhook",
            template="json"
        )
        notifier = WebhookNotifier([endpoint])
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Content"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_context = AsyncMock()
            mock_context.post = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_client.return_value = mock_context

            result = await notifier.send(notification)
            assert result is True

            mock_context.post.assert_called_once()
            call_args = mock_context.post.call_args
            assert call_args[0][0] == "https://example.com/webhook"
            # json template sends the payload directly as json, not wrapped
            assert call_args[1]["json"]["title"] == "Test"

    @pytest.mark.asyncio
    async def test_send_failure_handling(self):
        """Test handling of send failures."""
        endpoint = WebhookEndpoint(
            name="test",
            url="https://example.com/webhook"
        )
        notifier = WebhookNotifier([endpoint])
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Content"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500

            mock_context = AsyncMock()
            mock_context.post = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_client.return_value = mock_context

            result = await notifier.send(notification)
            assert result is False

    @pytest.mark.asyncio
    async def test_send_http_error_handling(self):
        """Test handling of HTTP errors."""
        endpoint = WebhookEndpoint(
            name="test",
            url="https://example.com/webhook"
        )
        notifier = WebhookNotifier([endpoint])
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Content"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_context = AsyncMock()
            mock_context.post = AsyncMock(side_effect=httpx.HTTPError("Connection error"))
            mock_context.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_client.return_value = mock_context

            result = await notifier.send(notification)
            assert result is False

    @pytest.mark.asyncio
    async def test_empty_endpoints_returns_false(self):
        """Test that empty endpoints returns False."""
        notifier = WebhookNotifier([])
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Content"
        )

        result = await notifier.send(notification)
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_endpoints_partial_failure(self):
        """Test with multiple endpoints where one fails."""
        endpoints = [
            WebhookEndpoint(name="success", url="https://example.com/ok"),
            WebhookEndpoint(name="fail", url="https://example.com/fail")
        ]
        notifier = WebhookNotifier(endpoints)
        notification = Notification(
            title="Test",
            level=NotificationLevel.INFO,
            content="Content"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_ok = MagicMock()
            mock_response_ok.status_code = 200

            mock_response_fail = MagicMock()
            mock_response_fail.status_code = 500

            mock_context = AsyncMock()
            mock_context.post = AsyncMock(side_effect=[mock_response_ok, mock_response_fail])
            mock_context.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context.__aexit__ = AsyncMock(return_value=None)

            mock_client.return_value = mock_context

            result = await notifier.send(notification)
            # Should return False if any endpoint fails
            assert result is False
            assert mock_context.post.call_count == 2
