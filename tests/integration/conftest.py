"""Shared fixtures for integration tests.

These tests require a running Docker daemon. Skip the entire directory
if Docker is not available.
"""

from __future__ import annotations

import contextlib

import docker
import pytest

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


@pytest.fixture(scope="session")
def docker_runtime():
    return DockerRuntime()


@pytest.fixture()
def cleanup_containers(docker_runtime):
    """Track containers created during a test and remove them after."""
    created: list[str] = []
    yield created
    for cid in created:
        with contextlib.suppress(Exception):
            docker_runtime.remove(cid, force=True)


@pytest.fixture()
def cleanup_networks():
    """Remove test networks after each test."""
    client = docker.from_env()
    created: list[str] = []
    yield created
    for name in created:
        with contextlib.suppress(Exception):
            net = client.networks.get(name)
            net.remove()
