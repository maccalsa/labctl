"""Unit tests for DockerRuntime — mocked docker.DockerClient."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from docker.errors import DockerException, NotFound

from labctl.errors import (
    DockerUnavailableError,
    MachineExistsError,
    MachineNotFoundError,
)
from labctl.runtime.docker import DockerRuntime


@pytest.fixture()
def mock_client():
    client = MagicMock()
    client.ping.return_value = True
    return client


@pytest.fixture()
def runtime(mock_client):
    return DockerRuntime(client=mock_client)


class TestHealthCheck:
    def test_raises_when_docker_unavailable(self):
        client = MagicMock()
        client.ping.side_effect = DockerException("connection refused")

        with pytest.raises(DockerUnavailableError, match="Cannot connect"):
            DockerRuntime(client=client)

    def test_succeeds_when_docker_is_running(self, mock_client):
        rt = DockerRuntime(client=mock_client)
        assert rt is not None


class TestNetwork:
    def test_create_network_new(self, runtime, mock_client):
        mock_client.networks.get.side_effect = NotFound("nope")
        mock_net = MagicMock()
        mock_net.id = "net-123"
        mock_client.networks.create.return_value = mock_net

        result = runtime.create_network("labctl-net")

        assert result == "net-123"
        mock_client.networks.create.assert_called_once_with(
            "labctl-net", driver="bridge"
        )

    def test_create_network_idempotent(self, runtime, mock_client):
        existing = MagicMock()
        existing.id = "net-existing"
        mock_client.networks.get.return_value = existing

        result = runtime.create_network("labctl-net")

        assert result == "net-existing"
        mock_client.networks.create.assert_not_called()

    def test_network_exists_true(self, runtime, mock_client):
        mock_client.networks.get.return_value = MagicMock()
        assert runtime.network_exists("labctl-net") is True

    def test_network_exists_false(self, runtime, mock_client):
        mock_client.networks.get.side_effect = NotFound("nope")
        assert runtime.network_exists("labctl-net") is False


class TestCreateContainer:
    def test_creates_with_labels_and_network(self, runtime, mock_client):
        mock_client.containers.get.side_effect = NotFound("nope")
        mock_client.images.get.return_value = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_client.containers.create.return_value = mock_container

        labels = {"labctl.managed": "true", "labctl.machine": "foo"}
        cid = runtime.create_container(
            "foo",
            "ubuntu:24.04",
            labels=labels,
            network="labctl-net",
        )

        assert cid == "abc123"
        call_kwargs = mock_client.containers.create.call_args
        assert call_kwargs.kwargs["labels"] == labels
        assert call_kwargs.kwargs["network"] == "labctl-net"
        assert call_kwargs.kwargs["hostname"] == "foo"

    def test_rejects_duplicate_name(self, runtime, mock_client):
        mock_client.containers.get.return_value = MagicMock()

        with pytest.raises(MachineExistsError, match="already exists"):
            runtime.create_container("foo", "ubuntu:24.04")

    def test_pulls_image_if_missing(self, runtime, mock_client):
        mock_client.containers.get.side_effect = NotFound("nope")
        mock_client.images.get.side_effect = (
            __import__("docker").errors.ImageNotFound("nope")
        )
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_client.containers.create.return_value = mock_container

        runtime.create_container("foo", "ubuntu:24.04")

        mock_client.images.pull.assert_called_once_with("ubuntu:24.04")

    def test_formats_ports(self, runtime, mock_client):
        mock_client.containers.get.side_effect = NotFound("nope")
        mock_client.images.get.return_value = MagicMock()
        mock_container = MagicMock()
        mock_container.id = "abc123"
        mock_client.containers.create.return_value = mock_container

        runtime.create_container(
            "foo", "ubuntu:24.04", ports={"8000": None, "443/tcp": 8443}
        )

        call_kwargs = mock_client.containers.create.call_args
        assert call_kwargs.kwargs["ports"] == {
            "8000/tcp": None,
            "443/tcp": 8443,
        }


class TestContainerOps:
    def test_start(self, runtime, mock_client):
        container = MagicMock()
        mock_client.containers.get.return_value = container

        runtime.start("abc123")

        container.start.assert_called_once()

    def test_stop(self, runtime, mock_client):
        container = MagicMock()
        mock_client.containers.get.return_value = container

        runtime.stop("abc123")

        container.stop.assert_called_once()

    def test_remove(self, runtime, mock_client):
        container = MagicMock()
        mock_client.containers.get.return_value = container

        runtime.remove("abc123", force=True)

        container.remove.assert_called_once_with(force=True)

    def test_get_nonexistent_raises(self, runtime, mock_client):
        mock_client.containers.get.side_effect = NotFound("nope")

        with pytest.raises(MachineNotFoundError, match="not found"):
            runtime.start("ghost")


class TestListContainers:
    def test_list_with_label_filter(self, runtime, mock_client):
        container = MagicMock()
        container.id = "abc123"
        container.name = "foo"
        container.status = "running"
        container.labels = {"labctl.managed": "true"}
        container.ports = {}
        img = MagicMock()
        img.tags = ["ubuntu:24.04"]
        container.image = img
        mock_client.containers.list.return_value = [container]

        result = runtime.list_containers(
            labels={"labctl.managed": "true"}, all_=True
        )

        assert len(result) == 1
        assert result[0]["name"] == "foo"
        assert result[0]["status"] == "running"
        mock_client.containers.list.assert_called_once_with(
            all=True,
            filters={"label": ["labctl.managed=true"]},
        )

    def test_list_empty(self, runtime, mock_client):
        mock_client.containers.list.return_value = []
        result = runtime.list_containers()
        assert result == []


class TestLogs:
    def test_logs_returns_string(self, runtime, mock_client):
        container = MagicMock()
        container.logs.return_value = b"hello world\n"
        mock_client.containers.get.return_value = container

        result = runtime.logs("abc123", tail=50)

        assert result == "hello world\n"
        container.logs.assert_called_once_with(follow=False, tail=50)


class TestInspect:
    def test_inspect_returns_attrs(self, runtime, mock_client):
        container = MagicMock()
        container.attrs = {"Id": "abc123", "State": {"Running": True}}
        mock_client.containers.get.return_value = container

        result = runtime.inspect("abc123")

        assert result["Id"] == "abc123"


class TestEnsureNetwork:
    def test_ensure_creates_default_network(self, runtime, mock_client):
        mock_client.networks.get.side_effect = NotFound("nope")
        mock_net = MagicMock()
        mock_net.id = "net-default"
        mock_client.networks.create.return_value = mock_net

        net_id = runtime.ensure_network()

        assert net_id == "net-default"
        mock_client.networks.create.assert_called_once_with(
            "labctl-net", driver="bridge"
        )
