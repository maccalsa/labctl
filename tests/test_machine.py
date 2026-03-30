"""Unit tests for machine orchestration — mocked runtime."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from labctl.errors import MachineNotFoundError, MachineNotRunningError
from labctl.machine import (
    CONTAINER_PREFIX,
    LABEL_MACHINE,
    LABEL_MANAGED,
    LABEL_NETWORK,
    LABEL_TEMPLATE,
    _container_name,
    _container_to_machine_info,
    _detect_shell,
    _extract_volume_names,
    _format_port_mappings,
    _make_labels,
    _make_ports,
    _make_volumes,
    destroy_machine,
    list_machines,
    shell_machine,
)
from labctl.template import VolumeSpec


class TestContainerName:
    def test_prefixes_name(self):
        assert _container_name("foo") == "labctl-foo"

    def test_prefix_constant(self):
        assert CONTAINER_PREFIX == "labctl-"


class TestMakeLabels:
    def test_all_labels_present(self):
        labels = _make_labels("api-dev", "node")
        assert labels[LABEL_MANAGED] == "true"
        assert labels[LABEL_MACHINE] == "api-dev"
        assert labels[LABEL_TEMPLATE] == "node"
        assert labels[LABEL_NETWORK] == "labctl-net"


class TestMakePorts:
    def test_empty_ports(self):
        from labctl.template import Template

        tpl = Template(name="blank", description="", path=Path("."), ports=[])
        assert _make_ports(tpl) is None

    def test_ports_mapped_to_dynamic(self):
        from labctl.template import Template

        tpl = Template(
            name="node", description="", path=Path("."), ports=[3000, 8080]
        )
        result = _make_ports(tpl)
        assert result == {"3000": None, "8080": None}


class TestMakeVolumes:
    def test_empty_volumes(self):
        assert _make_volumes("foo", []) is None

    def test_named_volumes(self):
        specs = [VolumeSpec(container_path="/var/lib/pg", suffix="data")]
        result = _make_volumes("db-dev", specs)
        assert result == {
            "labctl-db-dev-data": {"bind": "/var/lib/pg", "mode": "rw"}
        }

    def test_multiple_volumes(self):
        specs = [
            VolumeSpec(container_path="/data", suffix="data"),
            VolumeSpec(container_path="/logs", suffix="logs"),
        ]
        result = _make_volumes("svc", specs)
        assert "labctl-svc-data" in result
        assert "labctl-svc-logs" in result


# -- Phase 3: list / destroy helpers and orchestration --------------------


class TestFormatPortMappings:
    def test_empty_ports(self):
        assert _format_port_mappings({}) == ""

    def test_single_port_with_binding(self):
        ports = {"3000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "32768"}]}
        assert _format_port_mappings(ports) == "3000→32768"

    def test_multiple_ports(self):
        ports = {
            "3000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "32768"}],
            "8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "32769"}],
        }
        result = _format_port_mappings(ports)
        assert "3000→32768" in result
        assert "8080→32769" in result

    def test_port_with_no_binding(self):
        ports = {"5432/tcp": None}
        assert _format_port_mappings(ports) == "5432"


class TestExtractVolumeNames:
    def test_no_mounts(self):
        assert _extract_volume_names({}) == []

    def test_labctl_volumes_extracted(self):
        info = {
            "Mounts": [
                {"Type": "volume", "Name": "labctl-db-data"},
                {"Type": "bind", "Name": "/host/path"},
                {"Type": "volume", "Name": "other-vol"},
            ]
        }
        result = _extract_volume_names(info)
        assert result == ["labctl-db-data"]

    def test_multiple_labctl_volumes(self):
        info = {
            "Mounts": [
                {"Type": "volume", "Name": "labctl-db-data"},
                {"Type": "volume", "Name": "labctl-db-logs"},
            ]
        }
        assert len(_extract_volume_names(info)) == 2


class TestContainerToMachineInfo:
    def test_converts_container_dict(self):
        container = {
            "id": "abc123",
            "name": "labctl-api",
            "status": "running",
            "image": "labctl-tpl-node:latest",
            "labels": {
                LABEL_MANAGED: "true",
                LABEL_MACHINE: "api",
                LABEL_TEMPLATE: "node",
                LABEL_NETWORK: "labctl-net",
            },
            "ports": {"3000/tcp": [{"HostPort": "32768"}]},
        }
        info = _container_to_machine_info(container)
        assert info.name == "api"
        assert info.template == "node"
        assert info.status == "running"


class TestListMachines:
    def test_returns_machine_infos(self):
        runtime = MagicMock()
        runtime.list_containers.return_value = [
            {
                "id": "aaa",
                "name": "labctl-foo",
                "status": "running",
                "image": "labctl-tpl-blank:latest",
                "labels": {
                    LABEL_MANAGED: "true",
                    LABEL_MACHINE: "foo",
                    LABEL_TEMPLATE: "blank",
                    LABEL_NETWORK: "labctl-net",
                },
                "ports": {},
            },
            {
                "id": "bbb",
                "name": "labctl-bar",
                "status": "exited",
                "image": "labctl-tpl-node:latest",
                "labels": {
                    LABEL_MANAGED: "true",
                    LABEL_MACHINE: "bar",
                    LABEL_TEMPLATE: "node",
                    LABEL_NETWORK: "labctl-net",
                },
                "ports": {},
            },
        ]
        result = list_machines(runtime)
        assert len(result) == 2
        assert result[0].name == "foo"
        assert result[1].name == "bar"
        runtime.list_containers.assert_called_once_with(
            labels={LABEL_MANAGED: "true"}, all_=True
        )

    def test_empty_list(self):
        runtime = MagicMock()
        runtime.list_containers.return_value = []
        assert list_machines(runtime) == []


class TestDestroyMachine:
    def _make_runtime(self, containers, inspect_data=None):
        runtime = MagicMock()
        runtime.list_containers.return_value = containers
        runtime.inspect.return_value = inspect_data or {"Mounts": []}
        return runtime

    def test_destroys_container(self):
        containers = [
            {
                "id": "abc123",
                "name": "labctl-foo",
                "status": "running",
                "labels": {LABEL_MANAGED: "true", LABEL_MACHINE: "foo"},
                "ports": {},
            }
        ]
        runtime = self._make_runtime(containers)

        destroy_machine("foo", runtime)

        runtime.remove.assert_called_once_with("abc123", force=False)

    def test_destroys_with_force(self):
        containers = [
            {
                "id": "abc123",
                "name": "labctl-foo",
                "status": "running",
                "labels": {LABEL_MANAGED: "true", LABEL_MACHINE: "foo"},
                "ports": {},
            }
        ]
        runtime = self._make_runtime(containers)

        destroy_machine("foo", runtime, force=True)

        runtime.remove.assert_called_once_with("abc123", force=True)

    def test_returns_volume_names(self):
        containers = [
            {
                "id": "abc123",
                "name": "labctl-db",
                "status": "running",
                "labels": {LABEL_MANAGED: "true", LABEL_MACHINE: "db"},
                "ports": {},
            }
        ]
        inspect_data = {
            "Mounts": [
                {"Type": "volume", "Name": "labctl-db-data"},
            ]
        }
        runtime = self._make_runtime(containers, inspect_data)

        vol_names = destroy_machine("db", runtime)

        assert vol_names == ["labctl-db-data"]
        runtime.remove_volumes.assert_not_called()

    def test_removes_volumes_when_requested(self):
        containers = [
            {
                "id": "abc123",
                "name": "labctl-db",
                "status": "running",
                "labels": {LABEL_MANAGED: "true", LABEL_MACHINE: "db"},
                "ports": {},
            }
        ]
        inspect_data = {
            "Mounts": [
                {"Type": "volume", "Name": "labctl-db-data"},
            ]
        }
        runtime = self._make_runtime(containers, inspect_data)

        destroy_machine("db", runtime, remove_volumes=True)

        runtime.remove_volumes.assert_called_once_with(["labctl-db-data"])

    def test_nonexistent_machine_raises(self):
        runtime = self._make_runtime([])

        with pytest.raises(MachineNotFoundError):
            destroy_machine("nope", runtime)


# -- Phase 4: shell -------------------------------------------------------

def _running_container(name="foo"):
    return {
        "id": "abc123",
        "name": f"labctl-{name}",
        "status": "running",
        "labels": {LABEL_MANAGED: "true", LABEL_MACHINE: name},
        "ports": {},
    }


def _stopped_container(name="foo"):
    return {
        "id": "abc123",
        "name": f"labctl-{name}",
        "status": "exited",
        "labels": {LABEL_MANAGED: "true", LABEL_MACHINE: name},
        "ports": {},
    }


class TestDetectShell:
    def test_returns_bash_when_available(self):
        runtime = MagicMock()
        runtime.exec_run.return_value = (0, "")
        assert _detect_shell("abc123", runtime) == "/bin/bash"

    def test_falls_back_to_sh(self):
        runtime = MagicMock()
        runtime.exec_run.return_value = (1, "")
        assert _detect_shell("abc123", runtime) == "/bin/sh"


class TestShellMachine:
    def test_calls_exec_interactive_with_bash(self):
        runtime = MagicMock()
        runtime.list_containers.return_value = [_running_container()]
        runtime.exec_run.return_value = (0, "")
        runtime.exec_interactive.return_value = 0

        exit_code = shell_machine("foo", runtime)

        assert exit_code == 0
        runtime.exec_interactive.assert_called_once_with(
            "abc123", "/bin/bash"
        )

    def test_falls_back_to_sh(self):
        runtime = MagicMock()
        runtime.list_containers.return_value = [_running_container()]
        runtime.exec_run.return_value = (1, "")
        runtime.exec_interactive.return_value = 0

        shell_machine("foo", runtime)

        runtime.exec_interactive.assert_called_once_with(
            "abc123", "/bin/sh"
        )

    def test_raises_on_nonexistent_machine(self):
        runtime = MagicMock()
        runtime.list_containers.return_value = []

        with pytest.raises(MachineNotFoundError):
            shell_machine("nope", runtime)

    def test_raises_on_stopped_machine(self):
        runtime = MagicMock()
        runtime.list_containers.return_value = [_stopped_container()]

        with pytest.raises(MachineNotRunningError) as exc_info:
            shell_machine("foo", runtime)

        assert "labctl start foo" in str(exc_info.value)
