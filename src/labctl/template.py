"""Template loading and image building."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from labctl.errors import LabctlError

USER_TEMPLATES_DIR = Path.home() / ".labctl" / "templates"
IMAGE_PREFIX = "labctl-tpl-"


@dataclass(frozen=True)
class VolumeSpec:
    container_path: str
    suffix: str


@dataclass(frozen=True)
class Template:
    name: str
    description: str
    path: Path
    ports: list[int] = field(default_factory=list)
    volumes: list[VolumeSpec] = field(default_factory=list)

    @property
    def image_tag(self) -> str:
        return f"{IMAGE_PREFIX}{self.name}:latest"

    @property
    def dockerfile(self) -> Path:
        return self.path / "Dockerfile"


class TemplateNotFoundError(LabctlError):
    def __init__(self, name: str, available: list[str]) -> None:
        avail = ", ".join(sorted(available)) if available else "none"
        super().__init__(
            f"Template '{name}' not found. Available: {avail}"
        )
        self.name = name
        self.available = available


def _builtin_templates_dir() -> Path:
    """Locate the built-in templates shipped with the package."""
    return Path(str(resources.files("labctl") / "templates"))


def _discover_templates() -> dict[str, Path]:
    """Return a map of template name → directory for all known templates."""
    templates: dict[str, Path] = {}

    builtin = _builtin_templates_dir()
    if builtin.is_dir():
        for child in builtin.iterdir():
            if child.is_dir() and (child / "template.toml").exists():
                templates[child.name] = child

    if USER_TEMPLATES_DIR.is_dir():
        for child in USER_TEMPLATES_DIR.iterdir():
            if child.is_dir() and (child / "template.toml").exists():
                templates[child.name] = child

    return templates


def _parse_template(name: str, path: Path) -> Template:
    toml_path = path / "template.toml"
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    tpl = data.get("template", {})
    raw_volumes = tpl.get("volumes", [])
    volumes = [
        VolumeSpec(
            container_path=v["container_path"], suffix=v.get("suffix", "data")
        )
        for v in raw_volumes
    ]
    return Template(
        name=name,
        description=tpl.get("description", ""),
        path=path,
        ports=tpl.get("ports", []),
        volumes=volumes,
    )


def load_template(name: str) -> Template:
    """Load a template by name. Raises TemplateNotFoundError if unknown."""
    available = _discover_templates()
    if name not in available:
        raise TemplateNotFoundError(name, list(available.keys()))
    return _parse_template(name, available[name])


def list_templates() -> list[Template]:
    """Return all available templates."""
    available = _discover_templates()
    return [_parse_template(n, p) for n, p in sorted(available.items())]


def build_image(
    template: Template, docker_client: object
) -> str:
    """Build the template's Docker image. Returns the image tag."""
    client = docker_client  # type: ignore[assignment]
    client.images.build(
        path=str(template.path),
        tag=template.image_tag,
        rm=True,
    )
    return template.image_tag
