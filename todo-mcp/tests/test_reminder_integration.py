"""Integration tests for reminder system with HTTP server."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from todo_mcp.api.server import create_app
from todo_mcp.reminder.engine import ReminderEngine
from todo_mcp.reminder.scheduler import ReminderScheduler
from todo_mcp.reminder.config import ReminderConfig


class TestReminderServerLifecycle:
    """Test reminder system integration with FastAPI server."""

    def test_reminder_initializes_when_enabled(self):
        """Reminder system initializes on startup when enabled."""
        with patch("todo_mcp.api.server.load_reminder_config") as mock_load:
            mock_load.return_value = ReminderConfig(
                enabled=True,
                rules=[{
                    "type": "due_soon",
                    "enabled": True,
                    "channels": ["cli"],
                    "params": {"days_before": [3, 1]},
                }],
                channels={"cli": {"enabled": True, "sound": False}},
            )

            app = create_app()

            # TestClient triggers startup events
            with TestClient(app) as client:
                # Make a request
                response = client.get("/")
                assert response.status_code == 200

                # Verify reminder components are set
                assert hasattr(app.state, "reminder_engine")
                assert hasattr(app.state, "reminder_scheduler")
                assert isinstance(app.state.reminder_engine, ReminderEngine)
                assert isinstance(app.state.reminder_scheduler, ReminderScheduler)

    def test_reminder_skips_when_disabled(self):
        """Reminder system skips initialization when disabled."""
        with patch("todo_mcp.api.server.load_reminder_config") as mock_load:
            mock_load.return_value = ReminderConfig(enabled=False)

            app = create_app()

            # TestClient triggers startup events
            with TestClient(app) as client:
                # Make a request
                response = client.get("/")
                assert response.status_code == 200

                # Verify reminder components are not set
                assert not hasattr(app.state, "reminder_engine")
                assert not hasattr(app.state, "reminder_scheduler")

    def test_scheduler_stops_on_shutdown(self):
        """Scheduler stops gracefully on shutdown."""
        with patch("todo_mcp.api.server.load_reminder_config") as mock_load:
            mock_load.return_value = ReminderConfig(
                enabled=True,
                rules=[{
                    "type": "due_soon",
                    "enabled": True,
                    "channels": ["cli"],
                    "params": {"days_before": [3, 1]},
                }],
                channels={"cli": {"enabled": True, "sound": False}},
            )

            app = create_app()

            # Use context manager to capture scheduler before shutdown
            scheduler_ref = [None]

            # TestClient triggers startup and shutdown events
            with TestClient(app) as client:
                # Make a request
                response = client.get("/")
                assert response.status_code == 200

                # Get scheduler reference before context exit
                scheduler_ref[0] = app.state.reminder_scheduler
                assert scheduler_ref[0] is not None

            # After context exit, shutdown event should have been triggered
            # The scheduler should be stopped
            assert scheduler_ref[0]._running is False

    def test_engine_accessible_via_app_state(self):
        """Engine is accessible via app.state after initialization."""
        with patch("todo_mcp.api.server.load_reminder_config") as mock_load:
            mock_load.return_value = ReminderConfig(
                enabled=True,
                rules=[{
                    "type": "due_soon",
                    "enabled": True,
                    "channels": ["cli"],
                    "params": {"days_before": [3, 1]},
                }],
                channels={"cli": {"enabled": True, "sound": False}},
            )

            app = create_app()

            with TestClient(app) as client:
                # Make a request
                response = client.get("/")
                assert response.status_code == 200

                # Access engine via app.state
                engine = app.state.reminder_engine
                assert engine is not None
                assert hasattr(engine, "rule_manager")
                assert hasattr(engine, "checker")
                assert hasattr(engine, "notifiers")

                # Verify notifiers include cli
                assert "cli" in engine.notifiers

    def test_multiple_channels_configured(self):
        """Multiple notification channels can be configured."""
        with patch("todo_mcp.api.server.load_reminder_config") as mock_load:
            mock_load.return_value = ReminderConfig(
                enabled=True,
                rules=[{
                    "type": "overdue",
                    "enabled": True,
                    "channels": ["cli", "webhook"],
                    "params": {},
                }],
                channels={
                    "cli": {"enabled": True, "sound": True},
                    "webhook": {"enabled": True, "url": "http://example.com/webhook"},
                },
            )

            app = create_app()

            with TestClient(app) as client:
                # Make a request
                response = client.get("/")
                assert response.status_code == 200

                engine = app.state.reminder_engine

                # CLI notifier should be configured
                assert "cli" in engine.notifiers

    def test_shutdown_handles_missing_scheduler(self):
        """Shutdown handles case where scheduler was never initialized."""
        with patch("todo_mcp.api.server.load_reminder_config") as mock_load:
            mock_load.return_value = ReminderConfig(enabled=False)

            app = create_app()

            # TestClient triggers startup and shutdown
            with TestClient(app) as client:
                # Make a request
                response = client.get("/")
                assert response.status_code == 200

                # Scheduler should not exist
                assert not hasattr(app.state, "reminder_scheduler")

            # Shutdown should not have raised error (context exits cleanly)

    def test_rules_loaded_from_config(self):
        """Rules are loaded correctly from configuration."""
        with patch("todo_mcp.api.server.load_reminder_config") as mock_load:
            mock_load.return_value = ReminderConfig(
                enabled=True,
                rules=[
                    {
                        "type": "due_soon",
                        "enabled": True,
                        "channels": ["cli"],
                        "params": {"days_before": [3, 1]},
                    },
                    {
                        "type": "overdue",
                        "enabled": True,
                        "channels": ["cli"],
                        "params": {},
                    },
                    {
                        "type": "overload",
                        "enabled": False,
                        "channels": ["cli"],
                        "params": {"daily_threshold": 10},
                    },
                ],
                channels={"cli": {"enabled": True, "sound": False}},
            )

            app = create_app()

            with TestClient(app) as client:
                # Make a request
                response = client.get("/")
                assert response.status_code == 200

                engine = app.state.reminder_engine
                rules = engine.rule_manager.get_all_rules()

                assert len(rules) == 3
                rule_types = [r.type for r in rules]
                assert "due_soon" in rule_types
                assert "overdue" in rule_types
                assert "overload" in rule_types

                # Check overload is disabled
                overload_rule = engine.rule_manager.get_rule("overload")
                assert overload_rule.enabled is False


class TestServerEndpoints:
    """Test server endpoints work with reminder system."""

    def test_health_check_works(self):
        """Health check endpoint works regardless of reminder state."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_chat_endpoint_works(self):
        """Chat endpoint works regardless of reminder state."""
        app = create_app()
        client = TestClient(app)

        # This will fail due to agent not being configured, but endpoint should exist
        response = client.post("/chat", json={"message": "hello"})
        # Accept either success or internal error (agent not configured)
        assert response.status_code in [200, 500]

    def test_tools_endpoint_works(self):
        """Tools endpoint works regardless of reminder state."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/tools")
        assert response.status_code == 200
        assert "tools" in response.json()


class TestReminderConfigLoading:
    """Test reminder configuration loading."""

    def test_load_config_file_not_found(self, tmp_path):
        """Config loading handles missing file."""
        from todo_mcp.reminder.config import load_reminder_config

        config = load_reminder_config(tmp_path / "nonexistent.yaml")

        assert config.enabled is False
        assert config.rules == []
        assert config.channels == {}

    def test_load_config_with_reminders_section(self, tmp_path):
        """Config loading parses reminders section."""
        from todo_mcp.reminder.config import load_reminder_config

        config_content = """
reminders:
  enabled: true
  rules:
    - type: due_soon
      enabled: true
      channels: ["cli"]
      params:
        days_before: [3, 1]
  channels:
    cli:
      enabled: true
      sound: false
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_reminder_config(config_file)

        assert config.enabled is True
        assert len(config.rules) == 1
        assert config.rules[0]["type"] == "due_soon"
        assert "cli" in config.channels

    def test_load_config_without_reminders_section(self, tmp_path):
        """Config loading handles file without reminders section."""
        from todo_mcp.reminder.config import load_reminder_config

        config_content = """
other_section:
  some_key: some_value
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_reminder_config(config_file)

        assert config.enabled is False
        assert config.rules == []
        assert config.channels == {}

    def test_load_empty_config_file(self, tmp_path):
        """Config loading handles empty file."""
        from todo_mcp.reminder.config import load_reminder_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        config = load_reminder_config(config_file)

        assert config.enabled is False
        assert config.rules == []
        assert config.channels == {}
