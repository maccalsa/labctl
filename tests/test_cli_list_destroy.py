"""CLI list / destroy command tests — mocked machine layer."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from labctl.cli import app
from labctl.errors import MachineNotFoundError
from labctl.machine import MachineInfo

runner = CliRunner()


class TestListCommand:
    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.list_machines")
    def test_list_shows_machines(self, mock_list, mock_runtime):
        mock_list.return_value = [
            MachineInfo(
                name="foo",
                container_id="aaa",
                template="blank",
                status="running",
                image="labctl-tpl-blank:latest",
                ports={},
            ),
            MachineInfo(
                name="bar",
                container_id="bbb",
                template="node",
                status="exited",
                image="labctl-tpl-node:latest",
                ports={"3000/tcp": [{"HostPort": "32768"}]},
            ),
        ]

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "foo" in result.output
        assert "bar" in result.output
        assert "blank" in result.output
        assert "node" in result.output

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.list_machines")
    def test_list_empty_shows_message(self, mock_list, mock_runtime):
        mock_list.return_value = []

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "no machines" in result.output.lower()

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.list_machines")
    def test_list_shows_running_status(self, mock_list, mock_runtime):
        mock_list.return_value = [
            MachineInfo(
                name="api",
                container_id="ccc",
                template="node",
                status="running",
                image="labctl-tpl-node:latest",
                ports={},
            ),
        ]

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "running" in result.output


class TestDestroyCommand:
    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.destroy_machine")
    def test_destroy_success(self, mock_destroy, mock_runtime):
        mock_destroy.return_value = []

        result = runner.invoke(app, ["destroy", "foo"])

        assert result.exit_code == 0
        assert "foo" in result.output
        assert "destroyed" in result.output.lower()

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.destroy_machine")
    def test_destroy_warns_about_volumes(self, mock_destroy, mock_runtime):
        mock_destroy.return_value = ["labctl-foo-data"]

        result = runner.invoke(app, ["destroy", "foo"])

        assert result.exit_code == 0
        assert "labctl-foo-data" in result.output
        assert "--volumes" in result.output

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.destroy_machine")
    def test_destroy_with_volumes_no_warning(self, mock_destroy, mock_runtime):
        mock_destroy.return_value = ["labctl-foo-data"]

        result = runner.invoke(app, ["destroy", "foo", "--volumes"])

        assert result.exit_code == 0
        assert "destroyed" in result.output.lower()
        mock_destroy.assert_called_once_with(
            "foo", mock_runtime(), remove_volumes=True, force=True,
        )

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.destroy_machine")
    def test_destroy_nonexistent_shows_error(self, mock_destroy, mock_runtime):
        mock_destroy.side_effect = MachineNotFoundError("nope")

        result = runner.invoke(app, ["destroy", "nope"])

        assert result.exit_code == 1
        assert "not found" in result.output
