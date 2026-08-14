import os
import tempfile

import pytest
from click.testing import CliRunner

from eventhubs.cli import cli
from eventhubs.config import load_config, save_config


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    """Point config to a temp directory so tests don't touch real config."""
    config_path = str(tmp_path / "config.yaml")
    monkeypatch.setenv("EVENTHUB_CONFIG", config_path)
    return config_path


@pytest.fixture
def runner():
    return CliRunner()


class TestConfigSetContext:
    def test_create_context_with_credential(self, runner):
        result = runner.invoke(cli, [
            "config", "set-context", "dev",
            "--fully-qualified-namespace", "dev.servicebus.windows.net",
            "--eventhub-name", "events",
            "--credential", "default",
        ])
        assert result.exit_code == 0
        assert "Context 'dev' updated." in result.output

        cfg = load_config()
        ctx = cfg["contexts"]["dev"]
        assert ctx["fully-qualified-namespace"] == "dev.servicebus.windows.net"
        assert ctx["eventhub-name"] == "events"
        assert ctx["credential"] == "default"

    def test_create_context_with_connection_string(self, runner):
        result = runner.invoke(cli, [
            "config", "set-context", "prod",
            "--connection-string", "Endpoint=sb://prod.servicebus.windows.net/;SharedAccessKeyName=key;SharedAccessKey=val",
            "--eventhub-name", "telemetry",
        ])
        assert result.exit_code == 0

        cfg = load_config()
        ctx = cfg["contexts"]["prod"]
        assert ctx["connection-string"].startswith("Endpoint=")
        assert ctx["eventhub-name"] == "telemetry"

    def test_update_existing_context_merges(self, runner):
        runner.invoke(cli, [
            "config", "set-context", "dev",
            "--fully-qualified-namespace", "dev.servicebus.windows.net",
            "--credential", "default",
            "--eventhub-name", "events",
        ])
        runner.invoke(cli, [
            "config", "set-context", "dev",
            "--consumer-group", "processors",
        ])

        cfg = load_config()
        ctx = cfg["contexts"]["dev"]
        assert ctx["fully-qualified-namespace"] == "dev.servicebus.windows.net"
        assert ctx["consumer-group"] == "processors"


class TestConfigGetContexts:
    def test_empty(self, runner):
        result = runner.invoke(cli, ["config", "get-contexts"])
        assert result.exit_code == 0
        assert "No contexts configured." in result.output

    def test_lists_contexts(self, runner):
        runner.invoke(cli, [
            "config", "set-context", "a",
            "--fully-qualified-namespace", "a.servicebus.windows.net",
            "--credential", "azurecli",
            "--eventhub-name", "hub-a",
        ])
        runner.invoke(cli, [
            "config", "set-context", "b",
            "--connection-string", "Endpoint=sb://b/",
            "--eventhub-name", "hub-b",
        ])

        result = runner.invoke(cli, ["config", "get-contexts"])
        assert result.exit_code == 0
        assert "a" in result.output
        assert "b" in result.output
        assert "azurecli@a.servicebus.windows.net" in result.output
        assert "connection-string" in result.output


class TestConfigUseContext:
    def test_switch_context(self, runner):
        runner.invoke(cli, [
            "config", "set-context", "dev",
            "--fully-qualified-namespace", "dev.servicebus.windows.net",
            "--credential", "default",
            "--eventhub-name", "events",
        ])

        result = runner.invoke(cli, ["config", "use-context", "dev"])
        assert result.exit_code == 0
        assert "Switched to context 'dev'" in result.output

        result = runner.invoke(cli, ["config", "current-context"])
        assert result.exit_code == 0
        assert result.output.strip() == "dev"

    def test_use_nonexistent_context_fails(self, runner):
        result = runner.invoke(cli, ["config", "use-context", "nope"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestConfigDeleteContext:
    def test_delete_existing(self, runner):
        runner.invoke(cli, [
            "config", "set-context", "temp",
            "--connection-string", "Endpoint=sb://temp/",
            "--eventhub-name", "hub",
        ])
        result = runner.invoke(cli, ["config", "delete-context", "temp"])
        assert result.exit_code == 0
        assert "deleted" in result.output

        cfg = load_config()
        assert "temp" not in cfg["contexts"]

    def test_delete_current_clears_current(self, runner):
        runner.invoke(cli, [
            "config", "set-context", "temp",
            "--connection-string", "Endpoint=sb://temp/",
            "--eventhub-name", "hub",
        ])
        runner.invoke(cli, ["config", "use-context", "temp"])
        runner.invoke(cli, ["config", "delete-context", "temp"])

        cfg = load_config()
        assert cfg["current-context"] == ""

    def test_delete_nonexistent_fails(self, runner):
        result = runner.invoke(cli, ["config", "delete-context", "nope"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestConfigCurrentContext:
    def test_no_current(self, runner):
        result = runner.invoke(cli, ["config", "current-context"])
        assert result.exit_code == 0
        assert "No current context is set." in result.output


class TestSettingsResolution:
    def test_connection_string_flag_still_works(self, runner):
        """Backward compat: --connection-string + --name works without config."""
        result = runner.invoke(cli, [
            "--connection-string", "Endpoint=sb://test.servicebus.windows.net/;SharedAccessKeyName=k;SharedAccessKey=v",
            "--name", "hub",
            "events", "--help",
        ])
        assert result.exit_code == 0

    def test_requires_some_auth(self, runner):
        result = runner.invoke(cli, [
            "--name", "hub",
            "events", "--help",
        ])
        assert result.exit_code != 0
        assert "either --connection-string or --fully-qualified-namespace" in result.output

    def test_mutual_exclusion(self, runner):
        result = runner.invoke(cli, [
            "--connection-string", "Endpoint=sb://test/;SharedAccessKeyName=k;SharedAccessKey=v",
            "--fully-qualified-namespace", "test.servicebus.windows.net",
            "--credential", "default",
            "--name", "hub",
            "events", "--help",
        ])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_credential_required_with_fqns(self, runner):
        result = runner.invoke(cli, [
            "--fully-qualified-namespace", "test.servicebus.windows.net",
            "--name", "hub",
            "events", "--help",
        ])
        assert result.exit_code != 0
        assert "--credential is required" in result.output
