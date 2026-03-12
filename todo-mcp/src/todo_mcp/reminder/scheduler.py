"""Scheduler for reminder system."""

import asyncio
from datetime import datetime, time
from typing import Any, Callable
from .engine import ReminderEngine
from .models import ReminderRule


class ReminderScheduler:
    """Schedules and runs reminder checks."""

    def __init__(
        self,
        engine: ReminderEngine,
        monitor_interval: int = 300,  # 5 minutes default
        get_tasks_callback: Callable[[], list[dict[str, Any]]] | None = None,
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

        # Wait for tasks to complete (they run indefinitely until stopped)
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        for task in self._tasks:
            try:
                task.cancel()
            except asyncio.CancelledError:
                pass

        # Wait for tasks to finish
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run_monitor(self) -> None:
        """Run continuous monitoring for condition-based rules."""
        while self._running:
            try:
                await self._check_monitor_rules()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue running
                print(f"Reminder monitor error: {e}")
            finally:
                await asyncio.sleep(self.monitor_interval)

    async def _run_scheduled(self) -> None:
        """Run scheduled tasks (daily_brief, weekly_review)."""
        while self._running:
            try:
                await self._check_scheduled_rules()
                # Check every minute for scheduled tasks
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue running
                print(f"Reminder scheduler error: {e}")
                await asyncio.sleep(60)

    async def _check_monitor_rules(self) -> None:
        """Check condition-based rules (due_soon, overdue, overload, stale)."""
        tasks = await self._get_tasks()
        if not tasks:
            return

        # Only check condition-based rules
        rule_types = ["due_soon", "overdue", "overload", "stale"]
        await self.engine.check_and_notify(tasks, rule_types=rule_types)

    async def _check_scheduled_rules(self) -> None:
        """Check scheduled rules (daily_brief, weekly_review)."""
        now = datetime.now()
        rules = self.engine.rule_manager.get_active_rules()

        scheduled_rules = [
            r for r in rules
            if r.type in ("daily_brief", "weekly_review")
        ]

        if not scheduled_rules:
            return

        for rule in scheduled_rules:
            if rule.type == "daily_brief":
                time_str = rule.params.get("time", "09:00")
                if self._should_run_daily(now, time_str):
                    tasks = await self._get_tasks()
                    if tasks:
                        await self.engine.check_and_notify(
                            tasks, rule_types=["daily_brief"]
                        )
            elif rule.type == "weekly_review":
                day = rule.params.get("day", "monday")
                time_str = rule.params.get("time", "10:00")
                if self._should_run_weekly(now, day, time_str):
                    tasks = await self._get_tasks()
                    if tasks:
                        await self.engine.check_and_notify(
                            tasks, rule_types=["weekly_review"]
                        )

    def _should_run_daily(self, now: datetime, time_str: str) -> bool:
        """Check if daily task should run at current time."""
        target_time = self._parse_time(time_str)
        if not target_time:
            return False

        # Check if current time matches target time (within 1 minute)
        current_time = now.time()
        return (
            current_time.hour == target_time.hour and
            current_time.minute == target_time.minute
        )

    def _should_run_weekly(self, now: datetime, day: str, time_str: str) -> bool:
        """Check if weekly task should run on current day and time."""
        # Map day names to weekday numbers (Monday=0, Sunday=6)
        day_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }

        target_weekday = day_map.get(day.lower())
        if target_weekday is None:
            return False

        # Check if today is the target day
        if now.weekday() != target_weekday:
            return False

        # Check if current time matches
        return self._should_run_daily(now, time_str)

    def _parse_time(self, time_str: str) -> time | None:
        """Parse time string in HH:MM format."""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return None

            hour = int(parts[0])
            minute = int(parts[1])

            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return None

            return time(hour, minute)
        except (ValueError, AttributeError):
            return None

    async def _get_tasks(self) -> list[dict[str, Any]]:
        """Get tasks using callback or return empty list."""
        if self.get_tasks:
            try:
                tasks = self.get_tasks()
                # Handle both sync and async callbacks
                if asyncio.iscoroutine(tasks):
                    return await tasks
                return tasks
            except Exception as e:
                print(f"Error getting tasks: {e}")
                return []
        return []
