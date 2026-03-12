"""Tests for rule manager functionality."""

import pytest
from todo_mcp.reminder.rules import RuleManager
from todo_mcp.reminder.models import ReminderRule


class TestRuleManager:
    """Test cases for RuleManager."""

    def test_load_rules_from_config(self):
        """RuleManager should load rules from configuration."""
        config = [
            {
                "type": "deadline",
                "enabled": True,
                "channels": ["chat", "email"],
                "params": {"hours_before": 24},
            },
            {
                "type": "daily_summary",
                "enabled": False,
                "channels": ["chat"],
                "params": {"time": "09:00"},
            },
        ]

        manager = RuleManager(rules=config)

        assert len(manager.get_all_rules()) == 2

        deadline_rule = manager.get_rule("deadline")
        assert deadline_rule is not None
        assert deadline_rule.type == "deadline"
        assert deadline_rule.enabled is True
        assert deadline_rule.channels == ["chat", "email"]
        assert deadline_rule.params == {"hours_before": 24}

        summary_rule = manager.get_rule("daily_summary")
        assert summary_rule is not None
        assert summary_rule.type == "daily_summary"
        assert summary_rule.enabled is False

    def test_get_rule_returns_correct_rule(self):
        """get_rule should return the correct rule by type."""
        config = [
            {"type": "deadline", "enabled": True, "channels": ["chat"], "params": {}},
            {"type": "recurring", "enabled": True, "channels": ["email"], "params": {}},
        ]

        manager = RuleManager(rules=config)

        rule = manager.get_rule("deadline")
        assert rule is not None
        assert rule.type == "deadline"

        rule = manager.get_rule("recurring")
        assert rule is not None
        assert rule.type == "recurring"

    def test_get_rule_returns_none_for_nonexistent(self):
        """get_rule should return None for nonexistent rule type."""
        manager = RuleManager(rules=[])

        rule = manager.get_rule("nonexistent")
        assert rule is None

    def test_update_rule_modifies_params(self):
        """update_rule should modify rule parameters."""
        config = [
            {
                "type": "deadline",
                "enabled": True,
                "channels": ["chat"],
                "params": {"hours_before": 24},
            }
        ]

        manager = RuleManager(rules=config)

        # Update params
        result = manager.update_rule("deadline", {"hours_before": 48, "repeat": True})
        assert result is True

        rule = manager.get_rule("deadline")
        assert rule is not None
        assert rule.params == {"hours_before": 48, "repeat": True}

    def test_update_rule_returns_false_for_nonexistent(self):
        """update_rule should return False for nonexistent rule."""
        manager = RuleManager(rules=[])

        result = manager.update_rule("nonexistent", {"some": "param"})
        assert result is False

    def test_set_enabled_toggles_rule_state(self):
        """set_enabled should enable or disable a rule."""
        config = [
            {"type": "deadline", "enabled": True, "channels": ["chat"], "params": {}}
        ]

        manager = RuleManager(rules=config)

        # Disable the rule
        result = manager.set_enabled("deadline", False)
        assert result is True

        rule = manager.get_rule("deadline")
        assert rule is not None
        assert rule.enabled is False

        # Re-enable the rule
        result = manager.set_enabled("deadline", True)
        assert result is True

        rule = manager.get_rule("deadline")
        assert rule is not None
        assert rule.enabled is True

    def test_set_enabled_returns_false_for_nonexistent(self):
        """set_enabled should return False for nonexistent rule."""
        manager = RuleManager(rules=[])

        result = manager.set_enabled("nonexistent", True)
        assert result is False

    def test_get_active_rules_only_returns_enabled(self):
        """get_active_rules should only return enabled rules."""
        config = [
            {"type": "deadline", "enabled": True, "channels": ["chat"], "params": {}},
            {"type": "recurring", "enabled": False, "channels": ["chat"], "params": {}},
            {"type": "summary", "enabled": True, "channels": ["email"], "params": {}},
        ]

        manager = RuleManager(rules=config)

        active_rules = manager.get_active_rules()
        assert len(active_rules) == 2

        active_types = {rule.type for rule in active_rules}
        assert active_types == {"deadline", "summary"}

    def test_get_all_rules(self):
        """get_all_rules should return all rules regardless of enabled state."""
        config = [
            {"type": "deadline", "enabled": True, "channels": ["chat"], "params": {}},
            {"type": "recurring", "enabled": False, "channels": ["chat"], "params": {}},
        ]

        manager = RuleManager(rules=config)

        all_rules = manager.get_all_rules()
        assert len(all_rules) == 2

    def test_to_config_exports_to_dict_format(self):
        """to_config should export rules to configuration format."""
        config = [
            {
                "type": "deadline",
                "enabled": True,
                "channels": ["chat", "email"],
                "params": {"hours_before": 24},
            },
            {
                "type": "daily_summary",
                "enabled": False,
                "channels": ["chat"],
                "params": {"time": "09:00"},
            },
        ]

        manager = RuleManager(rules=config)

        exported = manager.to_config()

        assert len(exported) == 2

        # Find the deadline config
        deadline_config = next(
            (c for c in exported if c["type"] == "deadline"), None
        )
        assert deadline_config is not None
        assert deadline_config["enabled"] is True
        assert deadline_config["channels"] == ["chat", "email"]
        assert deadline_config["params"] == {"hours_before": 24}

    def test_empty_rules_initialization(self):
        """RuleManager should work with no initial rules."""
        manager = RuleManager(rules=None)

        assert len(manager.get_all_rules()) == 0
        assert len(manager.get_active_rules()) == 0
        assert manager.get_rule("any") is None

    def test_default_values_for_rules(self):
        """Rules should use default values when not specified in config."""
        config = [{"type": "minimal"}]

        manager = RuleManager(rules=config)

        rule = manager.get_rule("minimal")
        assert rule is not None
        assert rule.enabled is True  # default
        assert rule.channels == ["chat"]  # default
        assert rule.params == {}  # default

    def test_update_rule_preserves_existing_params(self):
        """update_rule should preserve existing params when adding new ones."""
        config = [
            {
                "type": "deadline",
                "enabled": True,
                "channels": ["chat"],
                "params": {"hours_before": 24, "notify_owner": True},
            }
        ]

        manager = RuleManager(rules=config)

        # Update only one param
        manager.update_rule("deadline", {"hours_before": 48})

        rule = manager.get_rule("deadline")
        assert rule is not None
        assert rule.params == {"hours_before": 48, "notify_owner": True}
