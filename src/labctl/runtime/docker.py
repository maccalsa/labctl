"""DockerRuntime — ContainerRuntime implementation backed by docker-py."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

import docker
from docker.errors import DockerException, NotFound

from labctl.errors import (
    DockerUnavailableError,
    MachineExistsError,
    MachineNotFoundError,
)

LABCTL_NETWORK = "labctl-net"


class DockerRuntime:
    """Container runtime backed by the local Docker daemon."""

    def __init__(self, client: docker.DockerClient | None = None) -> None:
        try:
            self._client = client or docker.from_env()
            self._client.ping()
        except DockerException as exc:
            raise DockerUnavailableError(str(exc)) from exc

    # -- network -----------------------------------------------------------

    def create_network(self, name: str) -> str:
        """Create a bridge network. Returns its ID. Idempotent."""
        if self.network_exists(name):
            return self._client.networks.get(name).id
        net = self._client.networks.create(name, driver="bridge")
        return net.id

    def network_exists(self, name: str) -> bool:
        try:
            self._client.networks.get(name)
        except NotFound:
            return False
        return True

    # -- containers --------------------------------------------------------

    def create_container(
        self,
        name: str,
        image: str,
        *,
        labels: dict[str, str] | None = None,
        ports: dict[str, int | None] | None = None,
        volumes: dict[str, dict[str, str]] | None = None,
        network: str | None = None,
    ) -> str:
        """Create a container and return its ID."""
        self._assert_name_available(name)
        self._ensure_image(image)

        container = self._client.containers.create(
            image=image,
            name=name,
            hostname=name,
            labels=labels or {},
            ports=self._format_ports(ports),
            volumes=volumes or {},
            network=network,
            stdin_open=True,
            tty=True,
            detach=True,
        )
        return container.id

    def start(self, container_id: str) -> None:
        container = self._get_container(container_id)
        container.start()

    def stop(self, container_id: str) -> None:
        container = self._get_container(container_id)
        container.stop()

    def remove(self, container_id: str, *, force: bool = False) -> None:
        container = self._get_container(container_id)
        container.remove(force=force)

    def list_containers(
        self,
        *,
        labels: dict[str, str] | None = None,
        all_: bool = False,
    ) -> list[dict[str, Any]]:
        filters: dict[str, Any] = {}
        if labels:
            filters["label"] = [f"{k}={v}" for k, v in labels.items()]

        containers = self._client.containers.list(all=all_, filters=filters)
        return [self._container_to_dict(c) for c in containers]

    def exec_interactive(
        self, container_id: str, command: str = "/bin/bash"
    ) -> int:
        """Attach an interactive exec via subprocess (needs a real TTY)."""
        return subprocess.call(
            ["docker", "exec", "-it", container_id, command],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    def inspect(self, container_id: str) -> dict[str, Any]:
        container = self._get_container(container_id)
        return container.attrs  # type: ignore[return-value]

    def logs(
        self, container_id: str, *, follow: bool = False, tail: int = 100
    ) -> str:
        container = self._get_container(container_id)
        output = container.logs(follow=follow, tail=tail)
        if isinstance(output, bytes):
            return output.decode("utf-8", errors="replace")
        return "".join(
            chunk.decode("utf-8", errors="replace") for chunk in output
        )

    # -- helpers -----------------------------------------------------------

    def ensure_network(self) -> str:
        """Ensure the default labctl network exists. Returns its ID."""
        return self.create_network(LABCTL_NETWORK)

    def _get_container(self, container_id: str) -> Any:
        try:
            return self._client.containers.get(container_id)
        except NotFound as exc:
            raise MachineNotFoundError(container_id) from exc

    def _assert_name_available(self, name: str) -> None:
        try:
            self._client.containers.get(name)
        except NotFound:
            return
        raise MachineExistsError(name)

    def _ensure_image(self, image: str) -> None:
        """Pull the image if it's not available locally."""
        try:
            self._client.images.get(image)
        except docker.errors.ImageNotFound:
            self._client.images.pull(image)

    @staticmethod
    def _format_ports(
        ports: dict[str, int | None] | None,
    ) -> dict[str, int | None] | None:
        """Normalise port spec for docker-py.

        docker-py expects ``{"8000/tcp": None}`` to publish to a random
        host port, or ``{"8000/tcp": 8000}`` for a fixed mapping.
        """
        if not ports:
            return None
        formatted: dict[str, int | None] = {}
        for container_port, host_port in ports.items():
            key = (
                container_port
                if "/" in container_port
                else f"{container_port}/tcp"
            )
            formatted[key] = host_port
        return formatted

    @staticmethod
    def _container_to_dict(container: Any) -> dict[str, Any]:
        return {
            "id": container.id,
            "name": container.name,
            "status": container.status,
            "labels": container.labels,
            "image": str(container.image.tags[0])
            if container.image.tags
            else str(container.image.id[:12]),
            "ports": container.ports,
        }
