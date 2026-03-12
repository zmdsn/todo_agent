"""CLI notification channel using system notifications."""

import platform
import subprocess
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
