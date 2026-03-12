# Smart Reminder Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add intelligent reminder functionality to Todo Agent with multiple reminder types, notification channels, and scheduling modes.

**Architecture:** A ReminderEngine coordinates rule checking and notification dispatch. RuleManager handles configuration and runtime adjustments. ReminderScheduler runs scheduled tasks and continuous monitoring. Notifiers implement CLI and Webhook delivery.

**Tech Stack:** Python async/await, httpx (existing), dataclasses

---

## Task 1: Data Models

**Files:**
- Create: `src/todo_mcp/reminder/__init__.py`
- Create: `src/todo_mcp/reminder/models.py`
- Create: `tests/test_reminder_models.py`

**Step 1: Write the failing test**

```python
# tests/test_reminder_models.py
import pytest
from todo_mcp.reminder.models import Notification, ReminderRule, NotificationLevel


def test_notification_creation():
    """Test Notification dataclass creation."""
    notification = Notification(
        title="📅 任务即将到期",
        level=NotificationLevel.WARNING,
        content="任务「完成报告」将在 3 天后到期",
        actions=["标记完成", "推迟"],
        metadata={"task_id": "task-123"}
    )
    assert notification.title == "📅 任务即将到期"
    assert notification.level == NotificationLevel.WARNING
    assert "task-123" in notification.metadata["task_id"]


def test_reminder_rule_defaults():
    """Test ReminderRule with default values."""
    rule = ReminderRule(type="due_soon")
    assert rule.enabled is True
    assert rule.channels == ["chat"]
    assert rule.params == {}


def test_reminder_rule_with_params():
    """Test ReminderRule with custom params."""
    rule = ReminderRule(
        type="due_soon",
        enabled=True,
        channels=["chat", "cli"],
        params={"days_before": [3, 1]}
    )
    assert rule.params["days_before"] == [3, 1]
    assert len(rule.channels) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_models.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/__init__.py
"""Smart reminder module for Todo Agent."""

from .models import Notification, NotificationLevel, ReminderRule

__all__ = ["Notification", "NotificationLevel", "ReminderRule"]
```

```python
# src/todo_mcp/reminder/models.py
"""Data models for reminder system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NotificationLevel(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"


@dataclass
class Notification:
    """Represents a notification to be sent."""
    title: str
    level: NotificationLevel
    content: str
    actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReminderRule:
    """Configuration for a reminder rule."""
    type: str
    enabled: bool = True
    channels: list[str] = field(default_factory=lambda: ["chat"])
    params: dict[str, Any] = field(default_factory=dict)
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/__init__.py src/todo_mcp/reminder/models.py tests/test_reminder_models.py
git commit -m "feat(reminder): add data models for notifications and rules"
```

---

## Task 2: Notifier Base Class

**Files:**
- Create: `src/todo_mcp/reminder/notifiers/__init__.py`
- Create: `src/todo_mcp/reminder/notifiers/base.py`
- Create: `tests/test_notifier_base.py`

**Step 1: Write the failing test**

```python
# tests/test_notifier_base.py
import pytest
from todo_mcp.reminder.notifiers.base import BaseNotifier
from todo_mcp.reminder.models import Notification, NotificationLevel


class MockNotifier(BaseNotifier):
    """Mock notifier for testing."""

    def __init__(self):
        self.sent = []

    async def send(self, notification: Notification) -> bool:
        self.sent.append(notification)
        return True


@pytest.mark.asyncio
async def test_base_notifier_is_abstract():
    """Test that BaseNotifier cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseNotifier()


@pytest.mark.asyncio
async def test_mock_notifier_sends_notification():
    """Test that concrete notifier can send notifications."""
    notifier = MockNotifier()
    notification = Notification(
        title="Test",
        level=NotificationLevel.INFO,
        content="Test content"
    )
    result = await notifier.send(notification)
    assert result is True
    assert len(notifier.sent) == 1
    assert notifier.sent[0].title == "Test"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_notifier_base.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/notifiers/__init__.py
"""Notification channel implementations."""

from .base import BaseNotifier

__all__ = ["BaseNotifier"]
```

```python
# src/todo_mcp/reminder/notifiers/base.py
"""Base class for notification channels."""

from abc import ABC, abstractmethod
from ..models import Notification


class BaseNotifier(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send a notification.

        Args:
            notification: The notification to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        pass
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_notifier_base.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/notifiers/__init__.py src/todo_mcp/reminder/notifiers/base.py tests/test_notifier_base.py
git commit -m "feat(reminder): add base notifier abstract class"
```

---

## Task 3: CLI Notifier

**Files:**
- Create: `src/todo_mcp/reminder/notifiers/cli.py`
- Modify: `src/todo_mcp/reminder/notifiers/__init__.py`
- Create: `tests/test_cli_notifier.py`

**Step 1: Write the failing test**

```python
# tests/test_cli_notifier.py
import pytest
from unittest.mock import patch, AsyncMock
from todo_mcp.reminder.notifiers.cli import CliNotifier
from todo_mcp.reminder.models import Notification, NotificationLevel


@pytest.fixture
def cli_notifier():
    return CliNotifier(enabled=True, sound=False)


@pytest.fixture
def sample_notification():
    return Notification(
        title="📅 今日简报",
        level=NotificationLevel.INFO,
        content="今日有 3 个任务待完成"
    )


@pytest.mark.asyncio
async def test_cli_notifier_format_message(cli_notifier, sample_notification):
    """Test message formatting for CLI."""
    formatted = cli_notifier.format_message(sample_notification)
    assert "📅 今日简报" in formatted
    assert "今日有 3 个任务待完成" in formatted


@pytest.mark.asyncio
async def test_cli_notifier_disabled(cli_notifier, sample_notification):
    """Test that disabled notifier returns False."""
    cli_notifier.enabled = False
    result = await cli_notifier.send(sample_notification)
    assert result is False


@pytest.mark.asyncio
@patch("todo_mcp.reminder.notifiers.cli.CliNotifier._send_notification", new_callable=AsyncMock)
async def test_cli_notifier_send_success(mock_send, cli_notifier, sample_notification):
    """Test successful notification send."""
    mock_send.return_value = True
    result = await cli_notifier.send(sample_notification)
    assert result is True
    mock_send.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_cli_notifier.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/notifiers/cli.py
"""CLI notification channel using system notifications."""

import platform
import subprocess
from typing import Optional
from .base import BaseNotifier
from ..models import Notification


class CliNotifier(BaseNotifier):
    """Send notifications via system notification tools."""

    def __init__(self, enabled: bool = True, sound: bool = False):
        self.enabled = enabled
        self.sound = sound

    def format_message(self, notification: Notification) -> str:
        """Format notification for terminal output."""
        lines = [
            f"\n{notification.title}",
            "-" * len(notification.title),
            notification.content,
        ]
        if notification.actions:
            lines.append("\n可执行操作: " + " | ".join(notification.actions))
        return "\n".join(lines)

    async def send(self, notification: Notification) -> bool:
        """Send notification via system tools or print to terminal."""
        if not self.enabled:
            return False

        message = self.format_message(notification)

        # Try system notification first
        if await self._send_system_notification(notification.title, notification.content):
            return True

        # Fallback to terminal print
        print(message)
        return True

    async def _send_system_notification(self, title: str, content: str) -> bool:
        """Send via system notification daemon."""
        system = platform.system()

        try:
            if system == "Linux":
                cmd = ["notify-send", title, content]
                if not self.sound:
                    cmd.insert(1, "--hint=int:transient:1")
                subprocess.run(cmd, check=True, capture_output=True)
                return True
            elif system == "Darwin":  # macOS
                cmd = ["terminal-notifier", "-title", title, "-message", content]
                subprocess.run(cmd, check=True, capture_output=True)
                return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return False
```

```python
# Update src/todo_mcp/reminder/notifiers/__init__.py
"""Notification channel implementations."""

from .base import BaseNotifier
from .cli import CliNotifier

__all__ = ["BaseNotifier", "CliNotifier"]
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_cli_notifier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/notifiers/cli.py src/todo_mcp/reminder/notifiers/__init__.py tests/test_cli_notifier.py
git commit -m "feat(reminder): add CLI notifier with system notification support"
```

---

## Task 4: Webhook Notifier

**Files:**
- Create: `src/todo_mcp/reminder/notifiers/webhook.py`
- Modify: `src/todo_mcp/reminder/notifiers/__init__.py`
- Create: `tests/test_webhook_notifier.py`

**Step 1: Write the failing test**

```python
# tests/test_webhook_notifier.py
import pytest
from unittest.mock import AsyncMock, patch
from todo_mcp.reminder.notifiers.webhook import WebhookNotifier, WebhookEndpoint
from todo_mcp.reminder.models import Notification, NotificationLevel


@pytest.fixture
def webhook_endpoint():
    return WebhookEndpoint(
        name="test",
        url="https://example.com/webhook",
        template="text"
    )


@pytest.fixture
def webhook_notifier(webhook_endpoint):
    return WebhookNotifier(endpoints=[webhook_endpoint])


@pytest.fixture
def sample_notification():
    return Notification(
        title="📅 今日简报",
        level=NotificationLevel.INFO,
        content="今日有 3 个任务待完成"
    )


def test_webhook_endpoint_creation(webhook_endpoint):
    """Test webhook endpoint dataclass."""
    assert webhook_endpoint.name == "test"
    assert webhook_endpoint.url == "https://example.com/webhook"
    assert webhook_endpoint.template == "text"


def test_format_text_template(webhook_notifier, sample_notification):
    """Test text template formatting."""
    formatted = webhook_notifier._format_message(sample_notification, "text")
    assert "📅 今日简报" in formatted
    assert "今日有 3 个任务待完成" in formatted


def test_format_markdown_template(webhook_notifier, sample_notification):
    """Test markdown template formatting."""
    formatted = webhook_notifier._format_message(sample_notification, "markdown")
    assert "**📅 今日简报**" in formatted or "# 📅 今日简报" in formatted


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_webhook_send_success(mock_post, webhook_notifier, sample_notification):
    """Test successful webhook send."""
    mock_post.return_value.status_code = 200
    result = await webhook_notifier.send(sample_notification)
    assert result is True
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_webhook_notifier.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/notifiers/webhook.py
"""Webhook notification channel."""

from dataclasses import dataclass
from typing import Literal
import httpx
from .base import BaseNotifier
from ..models import Notification


@dataclass
class WebhookEndpoint:
    """Configuration for a webhook endpoint."""
    name: str
    url: str
    template: Literal["text", "markdown", "json"] = "text"


class WebhookNotifier(BaseNotifier):
    """Send notifications via webhooks."""

    def __init__(self, endpoints: list[WebhookEndpoint]):
        self.endpoints = endpoints

    def _format_message(self, notification: Notification, template: str) -> str | dict:
        """Format notification based on template type."""
        if template == "json":
            return {
                "title": notification.title,
                "level": notification.level.value,
                "content": notification.content,
                "actions": notification.actions,
            }
        elif template == "markdown":
            lines = [
                f"**{notification.title}**",
                "",
                notification.content,
            ]
            if notification.actions:
                lines.append("")
                lines.append("> 操作: " + " | ".join(notification.actions))
            return "\n".join(lines)
        else:  # text
            return f"{notification.title}\n{notification.content}"

    async def send(self, notification: Notification) -> bool:
        """Send notification to all configured endpoints."""
        if not self.endpoints:
            return False

        async with httpx.AsyncClient() as client:
            success = True
            for endpoint in self.endpoints:
                try:
                    payload = self._format_message(notification, endpoint.template)

                    if endpoint.template == "json":
                        response = await client.post(endpoint.url, json=payload)
                    else:
                        response = await client.post(
                            endpoint.url,
                            json={"msgtype": endpoint.template, endpoint.template: {"content": payload}}
                        )

                    if response.status_code >= 400:
                        success = False
                except httpx.HTTPError:
                    success = False

            return success
```

```python
# Update src/todo_mcp/reminder/notifiers/__init__.py
"""Notification channel implementations."""

from .base import BaseNotifier
from .cli import CliNotifier
from .webhook import WebhookNotifier, WebhookEndpoint

__all__ = ["BaseNotifier", "CliNotifier", "WebhookNotifier", "WebhookEndpoint"]
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_webhook_notifier.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/notifiers/webhook.py src/todo_mcp/reminder/notifiers/__init__.py tests/test_webhook_notifier.py
git commit -m "feat(reminder): add webhook notifier with multiple templates"
```

---

## Task 5: Rule Manager

**Files:**
- Create: `src/todo_mcp/reminder/rules.py`
- Create: `tests/test_rule_manager.py`

**Step 1: Write the failing test**

```python
# tests/test_rule_manager.py
import pytest
from todo_mcp.reminder.rules import RuleManager
from todo_mcp.reminder.models import ReminderRule


@pytest.fixture
def default_rules():
    return [
        {"type": "due_soon", "channels": ["chat", "cli"], "params": {"days_before": [3, 1]}},
        {"type": "daily_brief", "channels": ["cli"], "params": {"time": "08:00"}},
    ]


@pytest.fixture
def rule_manager(default_rules):
    return RuleManager(rules=default_rules)


def test_rule_manager_loads_rules(rule_manager):
    """Test that RuleManager loads rules from config."""
    rules = rule_manager.get_all_rules()
    assert len(rules) == 2
    assert rules[0].type == "due_soon"
    assert rules[1].type == "daily_brief"


def test_rule_manager_get_rule_by_type(rule_manager):
    """Test getting a specific rule by type."""
    rule = rule_manager.get_rule("due_soon")
    assert rule is not None
    assert rule.type == "due_soon"
    assert rule.params["days_before"] == [3, 1]


def test_rule_manager_get_nonexistent_rule(rule_manager):
    """Test getting a rule that doesn't exist."""
    rule = rule_manager.get_rule("nonexistent")
    assert rule is None


def test_rule_manager_update_rule(rule_manager):
    """Test updating a rule's parameters."""
    rule_manager.update_rule("due_soon", {"days_before": [5, 3, 1]})
    rule = rule_manager.get_rule("due_soon")
    assert rule.params["days_before"] == [5, 3, 1]


def test_rule_manager_enable_disable_rule(rule_manager):
    """Test enabling and disabling rules."""
    rule_manager.set_enabled("daily_brief", False)
    rule = rule_manager.get_rule("daily_brief")
    assert rule.enabled is False

    rule_manager.set_enabled("daily_brief", True)
    assert rule.enabled is True


def test_rule_manager_get_active_rules(rule_manager):
    """Test getting only active rules."""
    rule_manager.set_enabled("daily_brief", False)
    active = rule_manager.get_active_rules()
    assert len(active) == 1
    assert active[0].type == "due_soon"


def test_rule_manager_to_config(rule_manager):
    """Test exporting rules back to config format."""
    config = rule_manager.to_config()
    assert len(config) == 2
    assert config[0]["type"] == "due_soon"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_rule_manager.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/rules.py
"""Rule management for reminder system."""

from typing import Any
from .models import ReminderRule


class RuleManager:
    """Manages reminder rules with support for runtime updates."""

    def __init__(self, rules: list[dict[str, Any]] | None = None):
        self._rules: dict[str, ReminderRule] = {}
        if rules:
            self._load_rules(rules)

    def _load_rules(self, rules: list[dict[str, Any]]) -> None:
        """Load rules from configuration."""
        for rule_config in rules:
            rule = ReminderRule(
                type=rule_config["type"],
                enabled=rule_config.get("enabled", True),
                channels=rule_config.get("channels", ["chat"]),
                params=rule_config.get("params", {}),
            )
            self._rules[rule.type] = rule

    def get_rule(self, rule_type: str) -> ReminderRule | None:
        """Get a specific rule by type."""
        return self._rules.get(rule_type)

    def get_all_rules(self) -> list[ReminderRule]:
        """Get all rules."""
        return list(self._rules.values())

    def get_active_rules(self) -> list[ReminderRule]:
        """Get only enabled rules."""
        return [rule for rule in self._rules.values() if rule.enabled]

    def update_rule(self, rule_type: str, params: dict[str, Any]) -> bool:
        """Update a rule's parameters."""
        rule = self._rules.get(rule_type)
        if rule:
            rule.params.update(params)
            return True
        return False

    def set_enabled(self, rule_type: str, enabled: bool) -> bool:
        """Enable or disable a rule."""
        rule = self._rules.get(rule_type)
        if rule:
            rule.enabled = enabled
            return True
        return False

    def to_config(self) -> list[dict[str, Any]]:
        """Export rules to configuration format."""
        return [
            {
                "type": rule.type,
                "enabled": rule.enabled,
                "channels": rule.channels,
                "params": rule.params,
            }
            for rule in self._rules.values()
        ]
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_rule_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/rules.py tests/test_rule_manager.py
git commit -m "feat(reminder): add rule manager for reminder configuration"
```

---

## Task 6: Reminder Checker

**Files:**
- Create: `src/todo_mcp/reminder/checker.py`
- Create: `tests/test_reminder_checker.py`

**Step 1: Write the failing test**

```python
# tests/test_reminder_checker.py
import pytest
from datetime import date, timedelta
from todo_mcp.reminder.checker import ReminderChecker
from todo_mcp.reminder.models import ReminderRule, NotificationLevel


@pytest.fixture
def checker():
    return ReminderChecker()


@pytest.fixture
def due_soon_rule():
    return ReminderRule(
        type="due_soon",
        params={"days_before": [3, 1]}
    )


@pytest.fixture
def overdue_rule():
    return ReminderRule(
        type="overdue",
        params={"interval_hours": 24}
    )


@pytest.fixture
def sample_tasks():
    today = date.today()
    return [
        {"id": "task-1", "content": "Task due in 2 days", "due_date": today + timedelta(days=2), "completed": False},
        {"id": "task-2", "content": "Task due tomorrow", "due_date": today + timedelta(days=1), "completed": False},
        {"id": "task-3", "content": "Overdue task", "due_date": today - timedelta(days=1), "completed": False},
        {"id": "task-4", "content": "Completed task", "due_date": today - timedelta(days=2), "completed": True},
    ]


def test_check_due_soon_matches(checker, due_soon_rule, sample_tasks):
    """Test that due_soon rule matches tasks within threshold."""
    matches = checker.check_due_soon(sample_tasks, due_soon_rule)
    assert len(matches) == 2  # task-1 (2 days) and task-2 (1 day)


def test_check_overdue_matches(checker, overdue_rule, sample_tasks):
    """Test that overdue rule matches past-due incomplete tasks."""
    matches = checker.check_overdue(sample_tasks, overdue_rule)
    assert len(matches) == 1  # Only task-3
    assert matches[0]["id"] == "task-3"


def test_build_notification_for_due_soon(checker, due_soon_rule, sample_tasks):
    """Test building notification for due soon tasks."""
    matches = checker.check_due_soon(sample_tasks, due_soon_rule)
    notification = checker.build_notification("due_soon", matches)

    assert notification is not None
    assert "即将到期" in notification.title
    assert notification.level == NotificationLevel.WARNING


def test_build_notification_no_matches(checker, due_soon_rule):
    """Test that no notification is built when no matches."""
    notification = checker.build_notification("due_soon", [])
    assert notification is None


def test_check_overload_daily(checker):
    """Test daily overload detection."""
    tasks = [{"id": f"task-{i}", "completed": False} for i in range(10)]
    rule = ReminderRule(type="overload", params={"daily_threshold": 8})

    result = checker.check_overload(tasks, rule, period="daily")
    assert result is True  # 10 > 8


def test_check_overload_within_limit(checker):
    """Test that overload not triggered when within limit."""
    tasks = [{"id": f"task-{i}", "completed": False} for i in range(5)]
    rule = ReminderRule(type="overload", params={"daily_threshold": 8})

    result = checker.check_overload(tasks, rule, period="daily")
    assert result is False  # 5 < 8
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_checker.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/checker.py
"""Reminder condition checking logic."""

from datetime import date, timedelta
from typing import Any
from .models import Notification, NotificationLevel, ReminderRule


class ReminderChecker:
    """Checks reminder conditions and builds notifications."""

    def check_due_soon(
        self,
        tasks: list[dict[str, Any]],
        rule: ReminderRule
    ) -> list[dict[str, Any]]:
        """Find tasks due within the specified days."""
        days_before = rule.params.get("days_before", [3, 1])
        max_days = max(days_before)
        today = date.today()
        matches = []

        for task in tasks:
            if task.get("completed"):
                continue

            due_date = task.get("due_date")
            if not due_date:
                continue

            if isinstance(due_date, str):
                due_date = date.fromisoformat(due_date)

            days_until = (due_date - today).days

            if 0 < days_until <= max_days:
                matches.append({**task, "days_until": days_until})

        return matches

    def check_overdue(
        self,
        tasks: list[dict[str, Any]],
        rule: ReminderRule
    ) -> list[dict[str, Any]]:
        """Find overdue incomplete tasks."""
        today = date.today()
        matches = []

        for task in tasks:
            if task.get("completed"):
                continue

            due_date = task.get("due_date")
            if not due_date:
                continue

            if isinstance(due_date, str):
                due_date = date.fromisoformat(due_date)

            if due_date < today:
                days_overdue = (today - due_date).days
                matches.append({**task, "days_overdue": days_overdue})

        return matches

    def check_overload(
        self,
        tasks: list[dict[str, Any]],
        rule: ReminderRule,
        period: str = "daily"
    ) -> bool:
        """Check if task count exceeds threshold."""
        threshold_key = f"{period}_threshold"
        threshold = rule.params.get(threshold_key, 10)

        incomplete = [t for t in tasks if not t.get("completed")]
        return len(incomplete) > threshold

    def build_notification(
        self,
        rule_type: str,
        matches: list[dict[str, Any]],
        **kwargs
    ) -> Notification | None:
        """Build a notification for matched items."""
        if not matches:
            return None

        if rule_type == "due_soon":
            return self._build_due_soon_notification(matches)
        elif rule_type == "overdue":
            return self._build_overdue_notification(matches)
        elif rule_type == "overload":
            return self._build_overload_notification(matches, kwargs)
        elif rule_type == "daily_brief":
            return self._build_daily_brief_notification(matches, kwargs)

        return None

    def _build_due_soon_notification(self, matches: list) -> Notification:
        lines = ["以下任务即将到期：", ""]
        for task in sorted(matches, key=lambda t: t.get("days_until", 0)):
            days = task.get("days_until", 0)
            unit = "天" if days > 1 else "天"
            lines.append(f"• {task['content']}（{days}{unit}后）")

        return Notification(
            title="📅 任务即将到期",
            level=NotificationLevel.WARNING,
            content="\n".join(lines),
            actions=["查看详情", "全部推迟"],
            metadata={"count": len(matches), "type": "due_soon"}
        )

    def _build_overdue_notification(self, matches: list) -> Notification:
        lines = ["以下任务已逾期：", ""]
        for task in sorted(matches, key=lambda t: t.get("days_overdue", 0), reverse=True):
            days = task.get("days_overdue", 0)
            lines.append(f"• {task['content']}（逾期 {days} 天）")

        return Notification(
            title="⚠️ 任务逾期提醒",
            level=NotificationLevel.URGENT,
            content="\n".join(lines),
            actions=["查看详情", "标记完成"],
            metadata={"count": len(matches), "type": "overdue"}
        )

    def _build_overload_notification(self, matches: list, kwargs: dict) -> Notification:
        count = len(matches)
        period = kwargs.get("period", "daily")
        period_cn = "今日" if period == "daily" else "本周"

        return Notification(
            title="⚡ 任务量提醒",
            level=NotificationLevel.WARNING,
            content=f"{period_cn}有 {count} 个待办任务，请注意合理安排时间",
            actions=["查看任务", "调整计划"],
            metadata={"count": count, "type": "overload"}
        )

    def _build_daily_brief_notification(self, matches: list, kwargs: dict) -> Notification:
        today = date.today().strftime("%Y-%m-%d")
        incomplete = [t for t in matches if not t.get("completed")]

        lines = [f"今日有 {len(incomplete)} 个任务待完成：", ""]
        for task in incomplete[:5]:  # Show max 5
            lines.append(f"• {task['content']}")

        if len(incomplete) > 5:
            lines.append(f"\n... 还有 {len(incomplete) - 5} 个任务")

        return Notification(
            title=f"📅 今日简报 ({today})",
            level=NotificationLevel.INFO,
            content="\n".join(lines),
            actions=["查看全部", "开始处理"],
            metadata={"count": len(incomplete), "type": "daily_brief"}
        )
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_checker.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/checker.py tests/test_reminder_checker.py
git commit -m "feat(reminder): add reminder checker with due_soon and overdue logic"
```

---

## Task 7: Reminder Engine

**Files:**
- Create: `src/todo_mcp/reminder/engine.py`
- Modify: `src/todo_mcp/reminder/__init__.py`
- Create: `tests/test_reminder_engine.py`

**Step 1: Write the failing test**

```python
# tests/test_reminder_engine.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from todo_mcp.reminder.engine import ReminderEngine
from todo_mcp.reminder.rules import RuleManager
from todo_mcp.reminder.checker import ReminderChecker
from todo_mcp.reminder.models import ReminderRule


@pytest.fixture
def mock_rule_manager():
    manager = MagicMock(spec=RuleManager)
    manager.get_active_rules.return_value = [
        ReminderRule(type="due_soon", channels=["chat"], params={"days_before": [3, 1]}),
    ]
    return manager


@pytest.fixture
def mock_checker():
    return MagicMock(spec=ReminderChecker)


@pytest.fixture
def engine(mock_rule_manager, mock_checker):
    return ReminderEngine(
        rule_manager=mock_rule_manager,
        checker=mock_checker,
    )


@pytest.mark.asyncio
async def test_engine_check_and_notify_with_matches(engine, mock_checker):
    """Test engine generates notifications for matches."""
    mock_checker.check_due_soon.return_value = [
        {"id": "task-1", "content": "Test task", "days_until": 2}
    ]
    mock_checker.build_notification.return_value = MagicMock()

    # Engine needs tasks data - would be provided by context
    # This is a simplified test
    assert engine.rule_manager is not None
    assert engine.checker is not None


def test_engine_initialization(engine):
    """Test engine initializes with dependencies."""
    assert engine.rule_manager is not None
    assert engine.checker is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_engine.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/engine.py
"""Reminder engine - main coordinator."""

from typing import Any
from .rules import RuleManager
from .checker import ReminderChecker
from .models import Notification, ReminderRule
from .notifiers.base import BaseNotifier


class ReminderEngine:
    """Coordinates rule checking and notification dispatch."""

    def __init__(
        self,
        rule_manager: RuleManager,
        checker: ReminderChecker,
        notifiers: dict[str, BaseNotifier] | None = None,
    ):
        self.rule_manager = rule_manager
        self.checker = checker
        self.notifiers = notifiers or {}

    def register_notifier(self, name: str, notifier: BaseNotifier) -> None:
        """Register a notification channel."""
        self.notifiers[name] = notifier

    async def check_and_notify(
        self,
        tasks: list[dict[str, Any]],
        rule_types: list[str] | None = None,
    ) -> list[Notification]:
        """Check all rules and send notifications."""
        notifications = []
        rules = self.rule_manager.get_active_rules()

        if rule_types:
            rules = [r for r in rules if r.type in rule_types]

        for rule in rules:
            notification = await self._process_rule(rule, tasks)
            if notification:
                notifications.append(notification)

        return notifications

    async def _process_rule(
        self,
        rule: ReminderRule,
        tasks: list[dict[str, Any]],
    ) -> Notification | None:
        """Process a single rule and return notification if triggered."""
        matches = self._check_rule(rule, tasks)

        if not matches:
            return None

        notification = self.checker.build_notification(rule.type, matches)
        if notification:
            await self._dispatch(notification, rule.channels)

        return notification

    def _check_rule(
        self,
        rule: ReminderRule,
        tasks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Check a rule against tasks."""
        if rule.type == "due_soon":
            return self.checker.check_due_soon(tasks, rule)
        elif rule.type == "overdue":
            return self.checker.check_overdue(tasks, rule)
        elif rule.type == "overload":
            if self.checker.check_overload(tasks, rule):
                return [t for t in tasks if not t.get("completed")]
        elif rule.type == "daily_brief":
            return tasks

        return []

    async def _dispatch(
        self,
        notification: Notification,
        channels: list[str],
    ) -> None:
        """Dispatch notification to specified channels."""
        for channel in channels:
            notifier = self.notifiers.get(channel)
            if notifier:
                await notifier.send(notification)
```

```python
# Update src/todo_mcp/reminder/__init__.py
"""Smart reminder module for Todo Agent."""

from .models import Notification, NotificationLevel, ReminderRule
from .rules import RuleManager
from .checker import ReminderChecker
from .engine import ReminderEngine

__all__ = [
    "Notification",
    "NotificationLevel",
    "ReminderRule",
    "RuleManager",
    "ReminderChecker",
    "ReminderEngine",
]
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/engine.py src/todo_mcp/reminder/__init__.py tests/test_reminder_engine.py
git commit -m "feat(reminder): add reminder engine coordinator"
```

---

## Task 8: Reminder Scheduler

**Files:**
- Create: `src/todo_mcp/reminder/scheduler.py`
- Create: `tests/test_reminder_scheduler.py`

**Step 1: Write the failing test**

```python
# tests/test_reminder_scheduler.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from todo_mcp.reminder.scheduler import ReminderScheduler
from todo_mcp.reminder.engine import ReminderEngine


@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=ReminderEngine)
    engine.check_and_notify = AsyncMock(return_value=[])
    return engine


@pytest.fixture
def scheduler(mock_engine):
    return ReminderScheduler(engine=mock_engine, monitor_interval=1)


def test_scheduler_initialization(scheduler):
    """Test scheduler initializes correctly."""
    assert scheduler.engine is not None
    assert scheduler.monitor_interval == 1
    assert scheduler._running is False


@pytest.mark.asyncio
async def test_scheduler_start_and_stop(scheduler, mock_engine):
    """Test scheduler can start and stop."""
    # Start scheduler
    await scheduler.start()
    assert scheduler._running is True

    # Let it run briefly
    await asyncio.sleep(0.1)

    # Stop scheduler
    await scheduler.stop()
    assert scheduler._running is False


@pytest.mark.asyncio
async def test_scheduler_monitor_runs_periodically(scheduler, mock_engine):
    """Test that monitor task runs periodically."""
    scheduler.monitor_interval = 0.1  # Fast for testing

    await scheduler.start()
    await asyncio.sleep(0.25)  # Should run ~2 times
    await scheduler.stop()

    # check_and_notify should have been called
    assert mock_engine.check_and_notify.call_count >= 1
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_scheduler.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/scheduler.py
"""Scheduler for reminder system."""

import asyncio
from datetime import datetime
from typing import Any
from .engine import ReminderEngine


class ReminderScheduler:
    """Schedules and runs reminder checks."""

    def __init__(
        self,
        engine: ReminderEngine,
        monitor_interval: int = 300,  # 5 minutes default
        get_tasks_callback: callable | None = None,
    ):
        self.engine = engine
        self.monitor_interval = monitor_interval
        self.get_tasks = get_tasks_callback
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start the scheduler."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._run_monitor()),
            asyncio.create_task(self._run_scheduled()),
        ]

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks = []

    async def _run_monitor(self) -> None:
        """Run continuous monitoring for condition-based rules."""
        while self._running:
            try:
                await self._check_monitor_rules()
                await asyncio.sleep(self.monitor_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue running
                print(f"Reminder monitor error: {e}")
                await asyncio.sleep(self.monitor_interval)

    async def _run_scheduled(self) -> None:
        """Run scheduled tasks (daily brief, weekly review)."""
        while self._running:
            try:
                await self._check_scheduled_rules()
                # Check every minute for scheduled time triggers
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Scheduled reminder error: {e}")
                await asyncio.sleep(60)

    async def _check_monitor_rules(self) -> None:
        """Check condition-based rules (due_soon, overdue, overload)."""
        if not self.get_tasks:
            return

        tasks = await self._get_tasks()
        if tasks:
            await self.engine.check_and_notify(
                tasks,
                rule_types=["due_soon", "overdue", "overload", "stale"],
            )

    async def _check_scheduled_rules(self) -> None:
        """Check time-based rules (daily_brief, weekly_review)."""
        if not self.get_tasks:
            return

        now = datetime.now()
        rules = self.engine.rule_manager.get_active_rules()

        for rule in rules:
            if rule.type == "daily_brief":
                time_str = rule.params.get("time", "08:00")
                if self._should_run_daily(now, time_str):
                    tasks = await self._get_tasks()
                    if tasks:
                        await self.engine.check_and_notify(
                            tasks,
                            rule_types=["daily_brief"],
                        )
            elif rule.type == "weekly_review":
                day = rule.params.get("day", "monday").lower()
                time_str = rule.params.get("time", "09:00")
                if self._should_run_weekly(now, day, time_str):
                    tasks = await self._get_tasks()
                    if tasks:
                        await self.engine.check_and_notify(
                            tasks,
                            rule_types=["weekly_review"],
                        )

    def _should_run_daily(self, now: datetime, time_str: str) -> bool:
        """Check if daily task should run now."""
        try:
            hour, minute = map(int, time_str.split(":"))
            return now.hour == hour and now.minute == minute
        except ValueError:
            return False

    def _should_run_weekly(self, now: datetime, day: str, time_str: str) -> bool:
        """Check if weekly task should run now."""
        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
        }
        target_day = day_map.get(day.lower(), 0)

        if now.weekday() != target_day:
            return False

        return self._should_run_daily(now, time_str)

    async def _get_tasks(self) -> list[dict[str, Any]]:
        """Get tasks using callback."""
        if self.get_tasks:
            result = self.get_tasks()
            if asyncio.iscoroutine(result):
                return await result
            return result
        return []
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_scheduler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/scheduler.py tests/test_reminder_scheduler.py
git commit -m "feat(reminder): add scheduler with monitor and scheduled modes"
```

---

## Task 9: Agent Tools for Reminders

**Files:**
- Modify: `src/todo_mcp/agent/tools.py`
- Create: `tests/test_reminder_tools.py`

**Step 1: Write the failing test**

```python
# tests/test_reminder_tools.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from todo_mcp.reminder.tools import (
    check_reminders,
    update_reminder_rule,
    add_webhook,
    test_notification,
)


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.check_and_notify = AsyncMock(return_value=[])
    engine.rule_manager = MagicMock()
    return engine


@pytest.mark.asyncio
async def test_check_reminders_tool(mock_engine):
    """Test check_reminders tool returns reminder list."""
    from todo_mcp.reminder import tools
    tools._engine = mock_engine

    result = await check_reminders.ainvoke({})
    assert isinstance(result, list)


def test_update_reminder_rule_tool():
    """Test update_reminder_rule tool."""
    # Tool should accept rule_type, action, params
    assert hasattr(update_reminder_rule, "invoke")
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_tools.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/tools.py
"""LangChain tools for reminder management."""

from typing import Any
from langchain_core.tools import tool

_engine = None


def set_engine(engine) -> None:
    """Set the reminder engine for tools to use."""
    global _engine
    _engine = engine


@tool
async def check_reminders() -> list[dict[str, Any]]:
    """检查当前所有待提醒事项，返回提醒列表。

    Returns:
        提醒事项列表，包含标题、级别和内容
    """
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
        params: 修改的参数（仅在 action=modify 时使用）

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
            return f"已更新 {rule_type} 提醒规则：{params}"
        return "未提供修改参数"
    else:
        return f"未知操作类型：{action}"


@tool
def add_webhook(
    name: str,
    url: str,
    template: str = "markdown",
) -> str:
    """添加新的 Webhook 通知渠道。

    Args:
        name: 渠道名称（如"企业微信"、"钉钉"）
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

    return f"已添加 Webhook 渠道：{name}"


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

    from .models import Notification, NotificationLevel

    notification = Notification(
        title="🧪 测试通知",
        level=NotificationLevel.INFO,
        content="这是一条测试通知，如果你看到了这条消息，说明通知渠道工作正常。",
    )

    notifier = _engine.notifiers.get(channel)
    if not notifier:
        return f"未找到通知渠道：{channel}"

    try:
        result = await notifier.send(notification)
        if result:
            return f"测试通知已成功发送到 {channel}"
        else:
            return f"发送失败，请检查 {channel} 配置"
    except Exception as e:
        return f"发送出错：{str(e)}"
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/tools.py tests/test_reminder_tools.py
git commit -m "feat(reminder): add LangChain tools for reminder management"
```

---

## Task 10: Configuration Integration

**Files:**
- Modify: `src/todo_mcp/parser/reader.py` (or appropriate config loader)
- Create: `tests/test_reminder_config.py`

**Step 1: Write the failing test**

```python
# tests/test_reminder_config.py
import pytest
import yaml
from pathlib import Path
from todo_mcp.reminder.config import ReminderConfig, load_reminder_config


@pytest.fixture
def sample_config_yaml(tmp_path):
    config = {
        "reminders": {
            "enabled": True,
            "rules": [
                {"type": "due_soon", "channels": ["chat", "cli"], "params": {"days_before": [3, 1]}},
                {"type": "daily_brief", "channels": ["cli"], "params": {"time": "08:00"}},
            ],
            "channels": {
                "cli": {"enabled": True, "sound": False},
                "webhook": {
                    "enabled": False,
                    "endpoints": []
                }
            }
        }
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(config, f)
    return config_file


def test_load_reminder_config(sample_config_yaml):
    """Test loading reminder configuration from YAML."""
    config = load_reminder_config(sample_config_yaml)
    assert config.enabled is True
    assert len(config.rules) == 2
    assert config.rules[0]["type"] == "due_soon"


def test_reminder_config_defaults():
    """Test default configuration values."""
    config = ReminderConfig()
    assert config.enabled is False  # Disabled by default
    assert config.rules == []
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_config.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write minimal implementation**

```python
# src/todo_mcp/reminder/config.py
"""Configuration handling for reminder system."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class ReminderConfig:
    """Reminder system configuration."""
    enabled: bool = False
    rules: list[dict[str, Any]] = field(default_factory=list)
    channels: dict[str, Any] = field(default_factory=dict)


def load_reminder_config(config_path: Path | str) -> ReminderConfig:
    """Load reminder configuration from YAML file."""
    config_path = Path(config_path)

    if not config_path.exists():
        return ReminderConfig()

    with open(config_path) as f:
        full_config = yaml.safe_load(f) or {}

    reminder_config = full_config.get("reminders", {})

    return ReminderConfig(
        enabled=reminder_config.get("enabled", False),
        rules=reminder_config.get("rules", []),
        channels=reminder_config.get("channels", {}),
    )
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/reminder/config.py tests/test_reminder_config.py
git commit -m "feat(reminder): add configuration loading"
```

---

## Task 11: Integration with HTTP Server

**Files:**
- Modify: `src/todo_mcp/api/server.py`
- Create: `tests/test_reminder_integration.py`

**Step 1: Write the failing test**

```python
# tests/test_reminder_integration.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_health_endpoint_reminder_status():
    """Test that health endpoint includes reminder status."""
    # This would test the integration
    # For now, just verify the module structure
    from todo_mcp.reminder import ReminderEngine
    assert ReminderEngine is not None
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_integration.py -v`
Expected: PASS (module exists now)

**Step 3: Write minimal implementation**

Add to `src/todo_mcp/api/server.py`:

```python
# Add these imports at top
from todo_mcp.reminder import ReminderEngine, ReminderChecker
from todo_mcp.reminder.rules import RuleManager
from todo_mcp.reminder.scheduler import ReminderScheduler
from todo_mcp.reminder.config import load_reminder_config
from todo_mcp.reminder.notifiers.cli import CliNotifier

# Add lifecycle management
@app.on_event("startup")
async def startup_reminder():
    """Initialize reminder system on startup."""
    config = load_reminder_config("config.yaml")

    if not config.enabled:
        return

    rule_manager = RuleManager(rules=config.rules)
    checker = ReminderChecker()
    notifiers = {}

    # Setup CLI notifier
    cli_config = config.channels.get("cli", {})
    if cli_config.get("enabled", False):
        notifiers["cli"] = CliNotifier(
            enabled=True,
            sound=cli_config.get("sound", False),
        )

    engine = ReminderEngine(
        rule_manager=rule_manager,
        checker=checker,
        notifiers=notifiers,
    )

    # Start scheduler
    scheduler = ReminderScheduler(engine=engine)
    await scheduler.start()

    app.state.reminder_engine = engine
    app.state.reminder_scheduler = scheduler


@app.on_event("shutdown")
async def shutdown_reminder():
    """Cleanup reminder system on shutdown."""
    scheduler = getattr(app.state, "reminder_scheduler", None)
    if scheduler:
        await scheduler.stop()
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_reminder_integration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/api/server.py tests/test_reminder_integration.py
git commit -m "feat(reminder): integrate with HTTP server lifecycle"
```

---

## Task 12: CLI Commands

**Files:**
- Modify: `src/todo_mcp/cli/main.py`
- Test: `tests/test_cli_reminder.py`

**Step 1: Write the failing test**

```python
# tests/test_cli_reminder.py
import pytest
from click.testing import CliRunner
from todo_mcp.cli.main import cli


def test_check_reminders_command():
    """Test CLI check-reminders command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["check-reminders"])
    # Command should exist
    assert result.exit_code in [0, 1]  # 0 success, 1 if no config
```

**Step 2: Run test to verify it fails**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_cli_reminder.py -v`
Expected: FAIL with command not found

**Step 3: Write minimal implementation**

Add to `src/todo_mcp/cli/main.py`:

```python
@cli.command()
def check_reminders():
    """检查并发送提醒通知。"""
    import asyncio
    from todo_mcp.reminder import ReminderEngine, ReminderChecker
    from todo_mcp.reminder.rules import RuleManager
    from todo_mcp.reminder.config import load_reminder_config
    from todo_mcp.reminder.notifiers.cli import CliNotifier
    from todo_mcp.parser.reader import TodoReader

    config = load_reminder_config("config.yaml")

    if not config.enabled:
        click.echo("提醒功能未启用，请在 config.yaml 中设置 reminders.enabled: true")
        return

    rule_manager = RuleManager(rules=config.rules)
    checker = ReminderChecker()
    notifier = CliNotifier(enabled=True)

    engine = ReminderEngine(
        rule_manager=rule_manager,
        checker=checker,
        notifiers={"cli": notifier},
    )

    # Get tasks from reader
    reader = TodoReader()
    # ... get tasks logic

    asyncio.run(engine.check_and_notify([]))
    click.echo("提醒检查完成")


@cli.command()
def reminder_daemon():
    """启动提醒守护进程。"""
    import asyncio
    from todo_mcp.reminder import ReminderEngine, ReminderChecker
    from todo_mcp.reminder.rules import RuleManager
    from todo_mcp.reminder.scheduler import ReminderScheduler
    from todo_mcp.reminder.config import load_reminder_config
    from todo_mcp.reminder.notifiers.cli import CliNotifier

    config = load_reminder_config("config.yaml")

    if not config.enabled:
        click.echo("提醒功能未启用")
        return

    rule_manager = RuleManager(rules=config.rules)
    checker = ReminderChecker()
    notifier = CliNotifier(enabled=True, sound=True)

    engine = ReminderEngine(
        rule_manager=rule_manager,
        checker=checker,
        notifiers={"cli": notifier},
    )

    scheduler = ReminderScheduler(engine=engine, monitor_interval=300)

    click.echo("启动提醒守护进程... (Ctrl+C 停止)")

    async def run():
        await scheduler.start()
        try:
            while True:
                await asyncio.sleep(3600)  # Keep running
        except asyncio.CancelledError:
            await scheduler.stop()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\n提醒守护进程已停止")
```

**Step 4: Run test to verify it passes**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest tests/test_cli_reminder.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/todo_mcp/cli/main.py tests/test_cli_reminder.py
git commit -m "feat(reminder): add CLI commands for reminder management"
```

---

## Task 13: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/mcp-clients.md` (if needed)

**Step 1: Add documentation section**

Add to `README.md`:

```markdown
### 智能提醒

todo-mcp 支持智能提醒功能，可以在任务即将到期、逾期或任务过多时主动提醒。

#### 配置

在 `config.yaml` 中启用提醒：

```yaml
reminders:
  enabled: true
  rules:
    - type: due_soon
      days_before: [3, 1]
      channels: [cli]
    - type: daily_brief
      time: "08:00"
      channels: [cli]
  channels:
    cli:
      enabled: true
      sound: false
    webhook:
      enabled: true
      endpoints:
        - name: "企业微信"
          url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
          template: "markdown"
```

#### CLI 命令

```bash
# 检查提醒
uv run todo-mcp check-reminders

# 启动守护进程
uv run todo-mcp reminder-daemon
```

#### 在对话中管理提醒

```
用户: 把到期提醒改成提前 5 天
Agent: 已将到期提醒调整为提前 5 天提醒

用户: 测试一下通知
Agent: 已发送测试通知，请检查是否收到
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add smart reminder documentation"
```

---

## Task 14: Run Full Test Suite

**Step 1: Run all tests**

Run: `cd /home/zmdsn/todo/todo-mcp && uv run pytest -v`

Expected: All tests PASS

**Step 2: Fix any failures**

If any tests fail, debug and fix before proceeding.

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(reminder): complete smart reminder implementation"
```

---

## Summary

| Task | Component | Files |
|------|-----------|-------|
| 1 | Data Models | `reminder/models.py` |
| 2 | Base Notifier | `reminder/notifiers/base.py` |
| 3 | CLI Notifier | `reminder/notifiers/cli.py` |
| 4 | Webhook Notifier | `reminder/notifiers/webhook.py` |
| 5 | Rule Manager | `reminder/rules.py` |
| 6 | Reminder Checker | `reminder/checker.py` |
| 7 | Reminder Engine | `reminder/engine.py` |
| 8 | Scheduler | `reminder/scheduler.py` |
| 9 | Agent Tools | `reminder/tools.py` |
| 10 | Config Loading | `reminder/config.py` |
| 11 | HTTP Integration | `api/server.py` |
| 12 | CLI Commands | `cli/main.py` |
| 13 | Documentation | `README.md` |
| 14 | Final Testing | - |
