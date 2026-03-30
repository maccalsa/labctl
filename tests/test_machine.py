"""Unit tests for machine orchestration — mocked runtime."""

from __future__ import annotations

from pathlib import Path

from labctl.machine import (
    CONTAINER_PREFIX,
    LABEL_MACHINE,
    LABEL_MANAGED,
    LABEL_NETWORK,
    LABEL_TEMPLATE,
    _container_name,
    _make_labels,
    _make_ports,
    _make_volumes,
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
