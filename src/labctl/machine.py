"""Machine lifecycle — the orchestration layer between CLI and runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from labctl.runtime.docker import LABCTL_NETWORK, DockerRuntime
from labctl.template import Template, VolumeSpec, build_image, load_template

LABEL_MANAGED = "labctl.managed"
LABEL_MACHINE = "labctl.machine"
LABEL_TEMPLATE = "labctl.template"
LABEL_NETWORK = "labctl.network"

CONTAINER_PREFIX = "labctl-"


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
