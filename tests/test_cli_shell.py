"""CLI shell command tests — mocked machine layer."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from labctl.cli import app
from labctl.errors import MachineNotFoundError, MachineNotRunningError

runner = CliRunner()


class TestShellCommand:
    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.shell_machine")
    def test_shell_exits_with_command_exit_code(
        self, mock_shell, mock_runtime
    ):
        mock_shell.return_value = 0

        result = runner.invoke(app, ["shell", "foo"])

        assert result.exit_code == 0
        mock_shell.assert_called_once_with("foo", mock_runtime())

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.shell_machine")
    def test_shell_nonexistent_shows_error(
        self, mock_shell, mock_runtime
    ):
        mock_shell.side_effect = MachineNotFoundError("nope")

        result = runner.invoke(app, ["shell", "nope"])

        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.shell_machine")
    def test_shell_stopped_shows_start_hint(
        self, mock_shell, mock_runtime
    ):
        mock_shell.side_effect = MachineNotRunningError("foo")

        result = runner.invoke(app, ["shell", "foo"])

        assert result.exit_code == 1
        assert "not running" in result.output
        assert "labctl start foo" in result.output

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.shell_machine")
    def test_shell_propagates_nonzero_exit(
        self, mock_shell, mock_runtime
    ):
        mock_shell.return_value = 127

        result = runner.invoke(app, ["shell", "foo"])

        assert result.exit_code == 127
