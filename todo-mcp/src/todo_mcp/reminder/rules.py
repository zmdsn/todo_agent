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
