"""ContainerRuntime protocol — the seam for backend abstraction.

MVP implements DockerRuntime only. Podman/nerdctl can be added later
behind this same interface.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ContainerRuntime(Protocol):
    """Minimal contract every container backend must satisfy."""

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
        """Create and return the container ID."""
        ...

    def start(self, container_id: str) -> None: ...

    def stop(self, container_id: str) -> None: ...

    def remove(self, container_id: str, *, force: bool = False) -> None: ...

    def list_containers(
        self,
        *,
        labels: dict[str, str] | None = None,
        all_: bool = False,
    ) -> list[dict[str, Any]]: ...

    def exec_interactive(self, container_id: str, command: str = "/bin/bash") -> int:
        """Attach an interactive exec session. Returns exit code."""
        ...

    def inspect(self, container_id: str) -> dict[str, Any]: ...

    def logs(
        self, container_id: str, *, follow: bool = False, tail: int = 100
    ) -> str: ...

    def connect_network(
        self,
        container_id: str,
        network: str,
        *,
        aliases: list[str] | None = None,
    ) -> None:
        """Connect a container to a network with optional DNS aliases."""
        ...

    def create_network(self, name: str) -> str:
        """Create a network and return its ID. No-op if it already exists."""
        ...

    def network_exists(self, name: str) -> bool: ...

    def remove_volumes(self, names: list[str]) -> None:
        """Remove named volumes."""
        ...
