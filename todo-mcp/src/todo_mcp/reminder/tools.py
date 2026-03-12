"""LangChain tools for reminder management."""

from typing import Any
from langchain_core.tools import tool

from .engine import ReminderEngine
from .models import Notification, NotificationLevel


_engine = None


def set_engine(engine: ReminderEngine) -> None:
    """Set the reminder engine for tools to use."""
    global _engine
    _engine = engine


@tool
async def check_reminders() -> list[dict[str, Any]]:
    """检查当前所有待提醒事项，返回提醒列表。"""
    if not _engine:
        return [{"error": "提醒引擎未初始化"}]

    # Get tasks from the engine's callback
    notifications = await _engine.check_and_notify([])

    return [
        {
            "title": n.title,
            "level": n.level.value,
            "content": n.content,
        }
        for n in notifications
    ]


@tool
def update_reminder_rule(
    rule_type: str,
    action: str,
    params: dict[str, Any] | None = None,
) -> str:
    """更新提醒规则配置。

    Args:
        rule_type: 规则类型 (due_soon, overdue, overload, daily_brief, weekly_review)
        action: 操作类型 (enable, disable, modify)
        params: 修改的参数（仅在 action=modify 时使用)

    Returns:
        操作结果描述
    """
    if not _engine:
        return "提醒引擎未初始化"

    if action == "enable":
        _engine.rule_manager.set_enabled(rule_type, True)
        return f"已启用 {rule_type} 提醒规则"
    elif action == "disable":
        _engine.rule_manager.set_enabled(rule_type, False)
        return f"已禁用 {rule_type} 提醒规则"
    elif action == "modify":
        if params:
            _engine.rule_manager.update_rule(rule_type, params)
            return f"已更新 {rule_type} 提醒规则： {params}"
        return "未提供修改参数"
    else:
        return f"未知操作类型： {action}"


@tool
def add_webhook(
    name: str,
    url: str,
    template: str = "markdown",
) -> str:
    """添加新的 Webhook 通知渠道。

    Args:
        name: 渠道名称（如"企业微信"、"钉钉")
        url: Webhook URL
        template: 消息模板 (text, markdown, json)

    Returns:
        操作结果描述
    """
    if not _engine:
        return "提醒引擎未初始化"

    from .notifiers.webhook import WebhookEndpoint, WebhookNotifier

    endpoint = WebhookEndpoint(name=name, url=url, template=template)

    # Get or create webhook notifier
    if "webhook" not in _engine.notifiers:
        _engine.notifiers["webhook"] = WebhookNotifier(endpoints=[endpoint])
    else:
        _engine.notifiers["webhook"].endpoints.append(endpoint)

    return f"已添加 Webhook 渠道: {name}"


@tool
async def test_notification(channel: str = "cli") -> str:
    """测试通知渠道是否正常工作。

    Args:
        channel: 要测试的渠道 (cli, webhook)

    Returns:
        测试结果描述
    """
    if not _engine:
        return "提醒引擎未初始化"

    notification = Notification(
        title="🧪 测试通知",
        level=NotificationLevel.INFO,
        content="这是一条测试通知，如果你看到了这条消息，说明通知渠道工作正常。",
    )

    notifier = _engine.notifiers.get(channel)
    if not notifier:
        return f"未找到通知渠道: {channel}"

    try:
        result = await notifier.send(notification)
        if result:
            return f"测试通知已成功发送到 {channel}"
        else:
            return f"发送失败,请检查 {channel} 配置"
    except Exception as e:
        return f"发送出错: {str(e)}"
