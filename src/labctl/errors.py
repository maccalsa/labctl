"""labctl exceptions."""


class LabctlError(Exception):
    """Base exception for all labctl errors."""


class DockerUnavailableError(LabctlError):
    """Raised when the Docker daemon is unreachable."""

    def __init__(self, reason: str = "") -> None:
        detail = f": {reason}" if reason else ""
        super().__init__(
            f"Cannot connect to Docker{detail}. "
            "Is Docker running? Check `docker info`."
        )


class MachineNotFoundError(LabctlError):
    """Raised when a machine name doesn't match any managed container."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Machine '{name}' not found.")
        self.name = name


class MachineExistsError(LabctlError):
    """Raised when creating a machine with a name that's already taken."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Machine '{name}' already exists.")
        self.name = name


class MachineNotRunningError(LabctlError):
    """Raised when an operation requires a running machine."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Machine '{name}' is not running. "
            f"Start it with: labctl start {name}"
        )
        self.name = name
