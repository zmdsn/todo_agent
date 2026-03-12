"""Tests for reminder LangChain tools."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from todo_mcp.reminder.models import Notification, NotificationLevel


@pytest.fixture
def mock_engine():
    """Create a mock reminder engine."""
    engine = Mock()
    engine.rule_manager = Mock()
    engine.notifiers = {}
    engine.check_and_notify = AsyncMock()
    return engine


class TestCheckReminders:
    """Tests for check_reminders tool."""

    @pytest.mark.asyncio
    async def test_returns_list_when_engine_initialized(self, mock_engine):
        """测试引擎初始化时返回列表。"""
        from todo_mcp.reminder.tools import check_reminders, set_engine

        # Setup
        notifications = [
            Notification(
                title="Test 1",
                level=NotificationLevel.WARNING,
                content="Content 1"
            ),
            Notification(
                title="Test 2",
                level=NotificationLevel.INFO,
                content="Content 2"
            ),
        ]
        mock_engine.check_and_notify.return_value = notifications
        set_engine(mock_engine)

        # Execute
        result = await check_reminders.ainvoke({})

        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["title"] == "Test 1"
        assert result[0]["level"] == "warning"
        assert result[1]["title"] == "Test 2"

    @pytest.mark.asyncio
    async def test_returns_error_when_engine_not_initialized(self):
        """测试引擎未初始化时返回错误。"""
        from todo_mcp.reminder.tools import check_reminders, set_engine

        # Reset engine
        set_engine(None)

        # Execute
        result = await check_reminders.ainvoke({})

        # Verify
        assert isinstance(result, list)
        assert len(result) == 1
        assert "error" in result[0]
        assert "未初始化" in result[0]["error"]


class TestUpdateReminderRule:
    """Tests for update_reminder_rule tool."""

    def test_enable_rule(self, mock_engine):
        """测试启用规则。"""
        from todo_mcp.reminder.tools import update_reminder_rule, set_engine

        # Setup
        set_engine(mock_engine)
        mock_engine.rule_manager.set_enabled.return_value = True

        # Execute
        result = update_reminder_rule.invoke({
            "rule_type": "due_soon",
            "action": "enable"
        })

        # Verify
        mock_engine.rule_manager.set_enabled.assert_called_once_with("due_soon", True)
        assert "已启用" in result
        assert "due_soon" in result

    def test_disable_rule(self, mock_engine):
        """测试禁用规则。"""
        from todo_mcp.reminder.tools import update_reminder_rule, set_engine

        # Setup
        set_engine(mock_engine)
        mock_engine.rule_manager.set_enabled.return_value = True

        # Execute
        result = update_reminder_rule.invoke({
            "rule_type": "overdue",
            "action": "disable"
        })

        # Verify
        mock_engine.rule_manager.set_enabled.assert_called_once_with("overdue", False)
        assert "已禁用" in result
        assert "overdue" in result

    def test_modify_rule_with_params(self, mock_engine):
        """测试修改规则参数。"""
        from todo_mcp.reminder.tools import update_reminder_rule, set_engine

        # Setup
        set_engine(mock_engine)
        mock_engine.rule_manager.update_rule.return_value = True

        # Execute
        result = update_reminder_rule.invoke({
            "rule_type": "daily_brief",
            "action": "modify",
            "params": {"time": "09:00"}
        })

        # Verify
        mock_engine.rule_manager.update_rule.assert_called_once_with(
            "daily_brief", {"time": "09:00"}
        )
        assert "已更新" in result
        assert "daily_brief" in result

    def test_modify_rule_without_params(self, mock_engine):
        """测试修改规则但未提供参数。"""
        from todo_mcp.reminder.tools import update_reminder_rule, set_engine

        # Setup
        set_engine(mock_engine)

        # Execute
        result = update_reminder_rule.invoke({
            "rule_type": "daily_brief",
            "action": "modify",
            "params": None
        })

        # Verify
        mock_engine.rule_manager.update_rule.assert_not_called()
        assert "未提供修改参数" in result

    def test_unknown_action(self, mock_engine):
        """测试未知操作类型。"""
        from todo_mcp.reminder.tools import update_reminder_rule, set_engine

        # Setup
        set_engine(mock_engine)

        # Execute
        result = update_reminder_rule.invoke({
            "rule_type": "due_soon",
            "action": "unknown"
        })

        # Verify
        assert "未知操作类型" in result

    def test_engine_not_initialized(self):
        """测试引擎未初始化。"""
        from todo_mcp.reminder.tools import update_reminder_rule, set_engine

        # Reset engine
        set_engine(None)

        # Execute
        result = update_reminder_rule.invoke({
            "rule_type": "due_soon",
            "action": "enable"
        })

        # Verify
        assert "未初始化" in result


class TestAddWebhook:
    """Tests for add_webhook tool."""

    def test_add_webhook_creates_notifier(self, mock_engine):
        """测试添加webhook创建新的通知器。"""
        from todo_mcp.reminder.tools import add_webhook, set_engine

        # Setup
        set_engine(mock_engine)
        mock_engine.notifiers = {}

        # Execute
        result = add_webhook.invoke({
            "name": "企业微信",
            "url": "https://example.com/webhook",
            "template": "markdown"
        })

        # Verify
        assert "webhook" in mock_engine.notifiers
        assert "已添加" in result
        assert "企业微信" in result

    def test_add_webhook_appends_endpoint(self, mock_engine):
        """测试添加webhook追加到现有通知器。"""
        from todo_mcp.reminder.tools import add_webhook, set_engine
        from todo_mcp.reminder.notifiers.webhook import WebhookNotifier, WebhookEndpoint

        # Setup
        set_engine(mock_engine)
        existing_notifier = WebhookNotifier(endpoints=[
            WebhookEndpoint(name="钉钉", url="https://old.example.com")
        ])
        mock_engine.notifiers = {"webhook": existing_notifier}

        # Execute
        result = add_webhook.invoke({
            "name": "企业微信",
            "url": "https://example.com/webhook",
            "template": "markdown"
        })

        # Verify
        assert len(existing_notifier.endpoints) == 2
        assert existing_notifier.endpoints[1].name == "企业微信"
        assert "已添加" in result

    def test_add_webhook_engine_not_initialized(self):
        """测试引擎未初始化。"""
        from todo_mcp.reminder.tools import add_webhook, set_engine

        # Reset engine
        set_engine(None)

        # Execute
        result = add_webhook.invoke({
            "name": "企业微信",
            "url": "https://example.com/webhook"
        })

        # Verify
        assert "未初始化" in result


class TestTestNotification:
    """Tests for test_notification tool."""

    @pytest.mark.asyncio
    async def test_test_notification_success(self, mock_engine):
        """测试通知发送成功。"""
        from todo_mcp.reminder.tools import test_notification, set_engine

        # Setup
        set_engine(mock_engine)
        mock_notifier = AsyncMock()
        mock_notifier.send.return_value = True
        mock_engine.notifiers = {"cli": mock_notifier}

        # Execute
        result = await test_notification.ainvoke({"channel": "cli"})

        # Verify
        mock_notifier.send.assert_called_once()
        assert "成功发送" in result
        assert "cli" in result

    @pytest.mark.asyncio
    async def test_test_notification_channel_not_found(self, mock_engine):
        """测试通知渠道不存在。"""
        from todo_mcp.reminder.tools import test_notification, set_engine

        # Setup
        set_engine(mock_engine)
        mock_engine.notifiers = {}

        # Execute
        result = await test_notification.ainvoke({"channel": "webhook"})

        # Verify
        assert "未找到" in result
        assert "webhook" in result

    @pytest.mark.asyncio
    async def test_test_notification_send_failed(self, mock_engine):
        """测试通知发送失败。"""
        from todo_mcp.reminder.tools import test_notification, set_engine

        # Setup
        set_engine(mock_engine)
        mock_notifier = AsyncMock()
        mock_notifier.send.return_value = False
        mock_engine.notifiers = {"cli": mock_notifier}

        # Execute
        result = await test_notification.ainvoke({"channel": "cli"})

        # Verify
        assert "发送失败" in result

    @pytest.mark.asyncio
    async def test_test_notification_send_error(self, mock_engine):
        """测试通知发送异常。"""
        from todo_mcp.reminder.tools import test_notification, set_engine

        # Setup
        set_engine(mock_engine)
        mock_notifier = AsyncMock()
        mock_notifier.send.side_effect = Exception("Network error")
        mock_engine.notifiers = {"cli": mock_notifier}

        # Execute
        result = await test_notification.ainvoke({"channel": "cli"})

        # Verify
        assert "发送出错" in result
        assert "Network error" in result

    @pytest.mark.asyncio
    async def test_test_notification_engine_not_initialized(self):
        """测试引擎未初始化。"""
        from todo_mcp.reminder.tools import test_notification, set_engine

        # Reset engine
        set_engine(None)

        # Execute
        result = await test_notification.ainvoke({"channel": "cli"})

        # Verify
        assert "未初始化" in result


class TestToolDecorators:
    """Test that tools are properly decorated."""

    def test_check_reminders_has_tool_decorator(self):
        """测试check_reminders有tool装饰器。"""
        from todo_mcp.reminder.tools import check_reminders
        assert hasattr(check_reminders, 'name')
        assert check_reminders.name == "check_reminders"

    def test_update_reminder_rule_has_tool_decorator(self):
        """测试update_reminder_rule有tool装饰器。"""
        from todo_mcp.reminder.tools import update_reminder_rule
        assert hasattr(update_reminder_rule, 'name')
        assert update_reminder_rule.name == "update_reminder_rule"

    def test_add_webhook_has_tool_decorator(self):
        """测试add_webhook有tool装饰器。"""
        from todo_mcp.reminder.tools import add_webhook
        assert hasattr(add_webhook, 'name')
        assert add_webhook.name == "add_webhook"

    def test_test_notification_has_tool_decorator(self):
        """测试test_notification有tool装饰器。"""
        from todo_mcp.reminder.tools import test_notification
        assert hasattr(test_notification, 'name')
        assert test_notification.name == "test_notification"
