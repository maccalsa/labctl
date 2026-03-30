"""Integration test — full labctl create flow against real Docker."""

from __future__ import annotations

import contextlib

import docker
import pytest

from labctl.machine import (
    CONTAINER_PREFIX,
    LABEL_MACHINE,
    LABEL_MANAGED,
    LABEL_NETWORK,
    LABEL_TEMPLATE,
    create_machine,
)
from labctl.runtime.docker import LABCTL_NETWORK, DockerRuntime


def _docker_available() -> bool:
    try:
        docker.from_env().ping()
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _docker_available(), reason="Docker daemon not available"
)

TEST_MACHINE = "integ-create-test"
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
        for img in client.images.list(name="labctl-tpl-blank"):
            client.images.remove(img.id, force=True)


class TestCreateMachineIntegration:
    def test_create_returns_running_machine(self, runtime):
        info = create_machine(TEST_MACHINE, "blank", runtime)

        assert info.name == TEST_MACHINE
        assert info.template == "blank"
        assert info.status == "running"
        assert info.container_id

    def test_container_has_correct_labels(self, runtime):
        info = create_machine(TEST_MACHINE, "blank", runtime)

        raw = runtime.inspect(info.container_id)
        labels = raw["Config"]["Labels"]
        assert labels[LABEL_MANAGED] == "true"
        assert labels[LABEL_MACHINE] == TEST_MACHINE
        assert labels[LABEL_TEMPLATE] == "blank"
        assert labels[LABEL_NETWORK] == LABCTL_NETWORK

    def test_container_on_labctl_network(self, runtime):
        info = create_machine(TEST_MACHINE, "blank", runtime)

        raw = runtime.inspect(info.container_id)
        networks = raw["NetworkSettings"]["Networks"]
        assert LABCTL_NETWORK in networks

    def test_machine_name_is_dns_alias(self, runtime):
        info = create_machine(TEST_MACHINE, "blank", runtime)

        raw = runtime.inspect(info.container_id)
        networks = raw["NetworkSettings"]["Networks"]
        aliases = networks[LABCTL_NETWORK].get("Aliases", [])
        assert TEST_MACHINE in aliases
