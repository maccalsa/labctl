"""Machine lifecycle — the orchestration layer between CLI and runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from labctl.errors import MachineNotFoundError
from labctl.runtime.docker import LABCTL_NETWORK, DockerRuntime
from labctl.template import Template, VolumeSpec, build_image, load_template

LABEL_MANAGED = "labctl.managed"
LABEL_MACHINE = "labctl.machine"
LABEL_TEMPLATE = "labctl.template"
LABEL_NETWORK = "labctl.network"

CONTAINER_PREFIX = "labctl-"
VOLUME_PREFIX = "labctl-"


def _container_name(machine_name: str) -> str:
    return f"{CONTAINER_PREFIX}{machine_name}"


@dataclass(frozen=True)
class MachineInfo:
    name: str
    container_id: str
    template: str
    status: str
    image: str
    ports: dict[str, Any]
    created: str = ""
    volumes: list[str] = field(default_factory=list)


def _make_labels(machine_name: str, template_name: str) -> dict[str, str]:
    return {
        LABEL_MANAGED: "true",
        LABEL_MACHINE: machine_name,
        LABEL_TEMPLATE: template_name,
        LABEL_NETWORK: LABCTL_NETWORK,
    }


def _make_ports(template: Template) -> dict[str, int | None] | None:
    if not template.ports:
        return None
    return {str(p): None for p in template.ports}


def _make_volumes(
    machine_name: str, volume_specs: list[VolumeSpec]
) -> dict[str, dict[str, str]] | None:
    if not volume_specs:
        return None
    volumes: dict[str, dict[str, str]] = {}
    for spec in volume_specs:
        vol_name = f"labctl-{machine_name}-{spec.suffix}"
        volumes[vol_name] = {"bind": spec.container_path, "mode": "rw"}
    return volumes


def create_machine(
    name: str,
    template_name: str,
    runtime: DockerRuntime,
) -> MachineInfo:
    """Create, start, and return info about a new machine."""
    tpl = load_template(template_name)

    runtime.ensure_network()

    image_tag = build_image(tpl, runtime._client)

    container_name = _container_name(name)
    labels = _make_labels(name, template_name)
    ports = _make_ports(tpl)
    volumes = _make_volumes(name, tpl.volumes)

    cid = runtime.create_container(
        container_name,
        image_tag,
        labels=labels,
        ports=ports,
        volumes=volumes,
    )

    runtime.connect_network(
        cid, LABCTL_NETWORK, aliases=[name]
    )
    runtime.start(cid)

    info = runtime.inspect(cid)
    return MachineInfo(
        name=name,
        container_id=cid,
        template=template_name,
        status="running",
        image=image_tag,
        ports=info.get("NetworkSettings", {}).get("Ports", {}),
    )


def _format_port_mappings(ports: dict[str, Any]) -> str:
    """Turn Docker port dict into a human-readable string like '3000→32768'."""
    if not ports:
        return ""
    parts: list[str] = []
    for container_port, bindings in sorted(ports.items()):
        port_num = container_port.split("/")[0]
        if bindings:
            for b in bindings:
                parts.append(f"{port_num}→{b['HostPort']}")
        else:
            parts.append(port_num)
    return ", ".join(parts)


def _extract_volume_names(container_info: dict[str, Any]) -> list[str]:
    """Return labctl-managed volume names from a container's inspect data."""
    mounts = container_info.get("Mounts", [])
    return [
        m["Name"]
        for m in mounts
        if m.get("Type") == "volume" and m.get("Name", "").startswith(VOLUME_PREFIX)
    ]


def _parse_created(raw: str) -> str:
    """Parse Docker's ISO timestamp into a short human-readable form."""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return raw[:16] if raw else ""


def _container_to_machine_info(container: dict[str, Any]) -> MachineInfo:
    """Convert a runtime container dict into a MachineInfo."""
    labels = container.get("labels", {})
    return MachineInfo(
        name=labels.get(
            LABEL_MACHINE,
            container["name"].removeprefix(CONTAINER_PREFIX),
        ),
        container_id=container["id"],
        template=labels.get(LABEL_TEMPLATE, "unknown"),
        status=container.get("status", "unknown"),
        image=container.get("image", ""),
        ports=container.get("ports", {}),
    )


def list_machines(runtime: DockerRuntime) -> list[MachineInfo]:
    """Return all labctl-managed machines."""
    containers = runtime.list_containers(
        labels={LABEL_MANAGED: "true"}, all_=True
    )
    return [_container_to_machine_info(c) for c in containers]


def _find_machine(name: str, runtime: DockerRuntime) -> dict[str, Any]:
    """Find a managed container by machine name. Raises MachineNotFoundError."""
    container_name = _container_name(name)
    containers = runtime.list_containers(
        labels={LABEL_MANAGED: "true", LABEL_MACHINE: name}, all_=True
    )
    for c in containers:
        if c["name"] == container_name:
            return c
    raise MachineNotFoundError(name)


def destroy_machine(
    name: str,
    runtime: DockerRuntime,
    *,
    remove_volumes: bool = False,
    force: bool = False,
) -> list[str]:
    """Destroy a machine. Returns list of associated volume names.

    If *remove_volumes* is True the named volumes are also deleted.
    Raises MachineNotFoundError when the machine doesn't exist.
    """
    container = _find_machine(name, runtime)
    cid = container["id"]

    raw = runtime.inspect(cid)
    volume_names = _extract_volume_names(raw)

    runtime.remove(cid, force=force)

    if remove_volumes and volume_names:
        runtime.remove_volumes(volume_names)

    return volume_names
