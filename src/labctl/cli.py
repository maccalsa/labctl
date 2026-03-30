"""labctl CLI — Typer application and top-level commands."""

from __future__ import annotations

import typer
from rich.console import Console

from labctl import __version__
from labctl.errors import LabctlError

app = typer.Typer(
    name="labctl",
    help="Local dev labs without the nonsense.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()
err_console = Console(stderr=True)


def _get_runtime():
    """Lazy-import and construct the DockerRuntime."""
    from labctl.runtime.docker import DockerRuntime

    return DockerRuntime()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"labctl {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Local dev labs without the nonsense."""


@app.command()
def create(
    name: str = typer.Argument(help="Name for the new machine."),
    template: str = typer.Option(
        "blank", "--template", "-t", help="Template to use."
    ),
) -> None:
    """Create a new dev machine."""
    from labctl.machine import create_machine

    try:
        runtime = _get_runtime()
        with console.status(
            f"Creating machine [bold]{name}[/bold] "
            f"from template [bold]{template}[/bold]..."
        ):
            info = create_machine(name, template, runtime)
        console.print(
            f"[green]✓[/green] Machine [bold]{info.name}[/bold] is running."
        )
    except LabctlError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=1) from None


@app.command("list")
def list_machines() -> None:
    """List all dev machines."""
    typer.echo("Listing machines...")
    raise typer.Exit(code=1)


@app.command()
def destroy(
    name: str = typer.Argument(help="Machine to destroy."),
) -> None:
    """Destroy a dev machine."""
    typer.echo(f"Destroying machine '{name}'...")
    raise typer.Exit(code=1)


@app.command()
def shell(
    name: str = typer.Argument(help="Machine to open a shell in."),
) -> None:
    """Open an interactive shell in a dev machine."""
    typer.echo(f"Opening shell in '{name}'...")
    raise typer.Exit(code=1)
