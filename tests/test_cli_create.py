"""CLI create command tests — mocked machine layer."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from labctl.cli import app
from labctl.errors import MachineExistsError
from labctl.machine import MachineInfo
from labctl.template import TemplateNotFoundError

runner = CliRunner()


class TestCreateCommand:
    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.create_machine")
    def test_create_success(self, mock_create, mock_runtime):
        mock_create.return_value = MachineInfo(
            name="foo",
            container_id="abc123",
            template="blank",
            status="running",
            image="labctl-tpl-blank:latest",
            ports={},
        )

        result = runner.invoke(app, ["create", "foo"])

        assert result.exit_code == 0
        assert "foo" in result.output
        assert "running" in result.output.lower() or "✓" in result.output

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.create_machine")
    def test_create_with_template(self, mock_create, mock_runtime):
        mock_create.return_value = MachineInfo(
            name="api",
            container_id="abc123",
            template="node",
            status="running",
            image="labctl-tpl-node:latest",
            ports={},
        )

        runner.invoke(app, ["create", "api", "-t", "node"])

        mock_create.assert_called_once_with("api", "node", mock_runtime())

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.create_machine")
    def test_create_duplicate_shows_error(self, mock_create, mock_runtime):
        mock_create.side_effect = MachineExistsError("labctl-foo")

        result = runner.invoke(app, ["create", "foo"])

        assert result.exit_code == 1
        assert "already exists" in result.output

    @patch("labctl.cli._get_runtime")
    @patch("labctl.machine.create_machine")
    def test_create_bad_template_shows_error(self, mock_create, mock_runtime):
        mock_create.side_effect = TemplateNotFoundError("nope", ["blank"])

        result = runner.invoke(app, ["create", "foo", "-t", "nope"])

        assert result.exit_code == 1
        assert "not found" in result.output
