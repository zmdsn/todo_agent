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
