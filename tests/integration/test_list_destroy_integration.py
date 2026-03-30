"""Integration test — labctl list + destroy against real Docker."""

from __future__ import annotations

import contextlib

import docker
import pytest

from labctl.errors import MachineNotFoundError
from labctl.machine import (
    CONTAINER_PREFIX,
    create_machine,
    destroy_machine,
    list_machines,
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

TEST_MACHINE = "integ-listdestroy"
TEST_CONTAINER = f"{CONTAINER_PREFIX}{TEST_MACHINE}"


@pytest.fixture()
def runtime():
    return DockerRuntime()


@pytest.fixture(autouse=True)
def _cleanup(runtime):
    yield
    with contextlib.suppress(Exception):
        runtime.remove(TEST_CONTAINER, force=True)
    with contextlib.suppress(Exception):
        client = docker.from_env()
        for vol in client.volumes.list():
            if vol.name.startswith(f"labctl-{TEST_MACHINE}"):
                vol.remove(force=True)


class TestListDestroyIntegration:
    def test_list_shows_created_machine(self, runtime):
        create_machine(TEST_MACHINE, "blank", runtime)

        machines = list_machines(runtime)
        names = [m.name for m in machines]

        assert TEST_MACHINE in names

    def test_list_shows_correct_template(self, runtime):
        create_machine(TEST_MACHINE, "blank", runtime)

        machines = list_machines(runtime)
        match = [m for m in machines if m.name == TEST_MACHINE]

        assert len(match) == 1
        assert match[0].template == "blank"
        assert match[0].status == "running"

    def test_destroy_removes_machine(self, runtime):
        create_machine(TEST_MACHINE, "blank", runtime)

        destroy_machine(TEST_MACHINE, runtime, force=True)

        machines = list_machines(runtime)
        names = [m.name for m in machines]
        assert TEST_MACHINE not in names

    def test_destroy_nonexistent_raises(self, runtime):
        with pytest.raises(MachineNotFoundError):
            destroy_machine("no-such-machine-xyz", runtime)

    def test_full_lifecycle_create_list_destroy_list(self, runtime):
        """The key AC: create → list (appears) → destroy → list (gone)."""
        create_machine(TEST_MACHINE, "blank", runtime)

        machines_before = list_machines(runtime)
        assert any(m.name == TEST_MACHINE for m in machines_before)

        destroy_machine(TEST_MACHINE, runtime, force=True)

        machines_after = list_machines(runtime)
        assert not any(m.name == TEST_MACHINE for m in machines_after)

    def test_list_empty_returns_empty(self, runtime):
        machines = [
            m for m in list_machines(runtime) if m.name == TEST_MACHINE
        ]
        assert machines == []
