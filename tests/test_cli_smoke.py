"""Smoke tests — CLI entry point loads and --help exits 0."""

from typer.testing import CliRunner

from labctl.cli import app

runner = CliRunner()


def test_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "labctl" in result.output.lower()


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_create_help():
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "template" in result.output.lower()


def test_list_help():
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0


def test_destroy_help():
    result = runner.invoke(app, ["destroy", "--help"])
    assert result.exit_code == 0


def test_shell_help():
    result = runner.invoke(app, ["shell", "--help"])
    assert result.exit_code == 0
