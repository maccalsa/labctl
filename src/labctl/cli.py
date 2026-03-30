"""labctl CLI — Typer application and top-level commands."""

from __future__ import annotations

import typer

from labctl import __version__

app = typer.Typer(
    name="labctl",
    help="Local dev labs without the nonsense.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


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
    typer.echo(f"Creating machine '{name}' from template '{template}'...")
    raise typer.Exit(code=1)  # stub — not implemented


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
