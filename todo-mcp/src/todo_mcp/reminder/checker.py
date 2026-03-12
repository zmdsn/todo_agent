"""Reminder condition checking logic."""

from datetime import date
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
