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
        notifiers: dict[str, BaseNotifier] | None,
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
                await self._dispatch(notification, rule.channels)
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

        return self.checker.build_notification(rule.type, matches)

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
        elif rule.type == "weekly_review":
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
