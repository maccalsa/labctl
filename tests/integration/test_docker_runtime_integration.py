"""Integration tests — DockerRuntime against a real Docker daemon.

Requires Docker to be running. Skipped automatically if not.
"""

from __future__ import annotations

import contextlib

import docker
import pytest

from labctl.errors import MachineExistsError, MachineNotFoundError
from labctl.runtime.docker import DockerRuntime

INTEGRATION_NET = "labctl-test-net"
INTEGRATION_PREFIX = "labctl-test-"


def _docker_available() -> bool:
    try:
        docker.from_env().ping()
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _docker_available(), reason="Docker daemon not available"
)


@pytest.fixture()
def runtime():
    return DockerRuntime()


@pytest.fixture(autouse=True)
def _cleanup(runtime):
    """Remove all test containers and networks after each test."""
    yield
    containers = runtime.list_containers(
        labels={"labctl.test": "true"}, all_=True
    )
    for c in containers:
        with contextlib.suppress(Exception):
            runtime.remove(c["id"], force=True)
    with contextlib.suppress(Exception):
        client = docker.from_env()
        net = client.networks.get(INTEGRATION_NET)
        net.remove()


def _test_labels(name: str) -> dict[str, str]:
    return {
        "labctl.managed": "true",
        "labctl.test": "true",
        "labctl.machine": name,
    }


class TestNetworkIntegration:
    def test_create_network_and_verify(self, runtime):
        net_id = runtime.create_network(INTEGRATION_NET)
        assert net_id
        assert runtime.network_exists(INTEGRATION_NET)

    def test_create_network_idempotent(self, runtime):
        id1 = runtime.create_network(INTEGRATION_NET)
        id2 = runtime.create_network(INTEGRATION_NET)
        assert id1 == id2

    def test_network_exists_false_for_unknown(self, runtime):
        assert runtime.network_exists("labctl-nonexistent-net-xyz") is False


class TestContainerLifecycle:
    def test_create_start_stop_remove(self, runtime):
        name = f"{INTEGRATION_PREFIX}lifecycle"
        runtime.create_network(INTEGRATION_NET)
        cid = runtime.create_container(
            name,
            "alpine:latest",
            labels=_test_labels("lifecycle"),
            network=INTEGRATION_NET,
        )
        assert cid

        runtime.start(cid)
        info = runtime.inspect(cid)
        assert info["State"]["Running"] is True

        runtime.stop(cid)
        info = runtime.inspect(cid)
        assert info["State"]["Running"] is False

        runtime.remove(cid)
        with pytest.raises(MachineNotFoundError):
            runtime.inspect(cid)

    def test_duplicate_name_rejected(self, runtime):
        name = f"{INTEGRATION_PREFIX}duplicate"
        runtime.create_container(
            name,
            "alpine:latest",
            labels=_test_labels("duplicate"),
        )

        with pytest.raises(MachineExistsError, match="already exists"):
            runtime.create_container(
                name,
                "alpine:latest",
                labels=_test_labels("duplicate"),
            )


class TestListContainers:
    def test_list_filters_by_label(self, runtime):
        name = f"{INTEGRATION_PREFIX}listed"
        cid = runtime.create_container(
            name,
            "alpine:latest",
            labels=_test_labels("listed"),
        )
        runtime.start(cid)

        machines = runtime.list_containers(
            labels={"labctl.test": "true"}
        )
        names = [m["name"] for m in machines]
        assert name in names

    def test_list_empty_when_no_match(self, runtime):
        machines = runtime.list_containers(
            labels={"labctl.nonexistent": "true"}
        )
        assert machines == []


class TestContainerHostname:
    def test_container_gets_hostname(self, runtime):
        name = f"{INTEGRATION_PREFIX}hostname"
        runtime.create_network(INTEGRATION_NET)
        cid = runtime.create_container(
            name,
            "alpine:latest",
            labels=_test_labels("hostname"),
            network=INTEGRATION_NET,
        )
        runtime.start(cid)

        info = runtime.inspect(cid)
        assert info["Config"]["Hostname"] == name
