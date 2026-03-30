"""Integration test — labctl shell against real Docker."""

from __future__ import annotations

import contextlib

import docker
import pytest

from labctl.errors import MachineNotFoundError, MachineNotRunningError
from labctl.machine import (
    CONTAINER_PREFIX,
    _detect_shell,
    _find_machine,
    create_machine,
    shell_machine,
)
from labctl.runtime.docker import DockerRuntime


def _docker_available() -> bool:
    try:
        docker.from_env().ping()
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _docker_available(), reason="Docker daemon not available"
)

TEST_MACHINE = "integ-shell-test"
TEST_CONTAINER = f"{CONTAINER_PREFIX}{TEST_MACHINE}"


@pytest.fixture()
def runtime():
    return DockerRuntime()


@pytest.fixture(autouse=True)
def _cleanup(runtime):
    yield
    with contextlib.suppress(Exception):
        runtime.remove(TEST_CONTAINER, force=True)


class TestShellIntegration:
    def test_detect_shell_finds_bash(self, runtime):
        """The blank template (ubuntu) has bash."""
        info = create_machine(TEST_MACHINE, "blank", runtime)
        shell = _detect_shell(info.container_id, runtime)
        assert shell == "/bin/bash"

    def test_exec_run_echo(self, runtime):
        """Verify we can run a command inside the container."""
        info = create_machine(TEST_MACHINE, "blank", runtime)
        exit_code, output = runtime.exec_run(
            info.container_id, ["echo", "hello from labctl"]
        )
        assert exit_code == 0
        assert "hello from labctl" in output

    def test_shell_on_nonexistent_raises(self, runtime):
        with pytest.raises(MachineNotFoundError):
            shell_machine("no-such-machine-xyz", runtime)

    def test_shell_on_stopped_raises(self, runtime):
        info = create_machine(TEST_MACHINE, "blank", runtime)
        runtime.stop(info.container_id)

        with pytest.raises(MachineNotRunningError) as exc_info:
            shell_machine(TEST_MACHINE, runtime)

        assert "labctl start" in str(exc_info.value)

    def test_find_machine_returns_running(self, runtime):
        create_machine(TEST_MACHINE, "blank", runtime)
        container = _find_machine(TEST_MACHINE, runtime)
        assert container["status"] == "running"
        assert container["name"] == TEST_CONTAINER
