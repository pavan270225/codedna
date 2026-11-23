"""CLI entry point for CodeDNA."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .models import AttributionLabel, ProvenanceHeader, ProvenanceRegion
from .store import Store
from .classifier import Classifier, ClassifierConfig, EditEvent
from .header import HeaderWriter, HeaderParser, round_trip_test


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """CodeDNA - Local AI-code attribution with in-source provenance."""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "summary"]), default="table")
def scan(path: Path, fmt: str) -> None:
    """Scan a file or directory and show attribution report."""
    store = Store()

    if path.is_file():
        files = [path]
    else:
        files = list(path.rglob("*.py")) + list(path.rglob("*.ts")) + list(path.rglob("*.js"))

    all_attrs = []
    for f in files:
        attrs = store.get_for_file(f)
        all_attrs.extend(attrs)

    if fmt == "json":
        console.print(json.dumps([a.to_dict() for a in all_attrs], indent=2))
        return

    if fmt == "summary":
        human, ai = store.get_ratio()
        total = human + ai
        pct = (human / total * 100) if total > 0 else 0
        console.print(f"[green]Human:[/green] {human} lines  [blue]AI:[/blue] {ai} lines  [bold]{pct:.1f}% human[/bold]")
        return

    # Table format
    table = Table(title="CodeDNA Attribution Report")
    table.add_column("File", style="cyan")
    table.add_column("Lines", justify="right")
    table.add_column("Label", justify="center")
    table.add_column("Confidence", justify="right")

    for attr in all_attrs:
        color = attr.label.color
        table.add_row(
            str(attr.file),
            str(len(attr)),
            f"[{color}]{attr.label.value}[/{color}]",
            f"{attr.confidence:.0%}",
        )

    console.print(table)

    human, ai = store.get_ratio()
    total = human + ai
    pct = (human / total * 100) if total > 0 else 0
    console.print(f"\n[bold]Total:[/bold] Human={human}, AI={ai} ({pct:.1f}% human)")


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def ratio(file: Path) -> None:
    """Show H/AI ratio for a single file."""
    store = Store()
    human, ai = store.get_ratio(file)
    total = human + ai
    pct = (human / total * 100) if total > 0 else 0

    console.print(Panel.fit(
        f"[green]Human:[/green] {human} lines\n[blue]AI:[/blue] {ai} lines\n[bold]{pct:.1f}% human[/bold]",
        title=f"Ratio for {file}",
        border_style="cyan",
    ))


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--on/--off", default=True, help="Enable or disable headers")
def headers(file: Path, on: bool) -> None:
    """Toggle in-source provenance headers for a file."""
    writer = HeaderWriter(enabled=on)

    if on:
        # Generate a sample header from store
        store = Store()
        attrs = store.get_for_file(file)
        if not attrs:
            console.print("[yellow]No attribution data found. Run classification first.[/yellow]")
            return

        classifier = Classifier()
        regions = classifier.to_provenance_regions(attrs)
        header = ProvenanceHeader(regions=regions)

        if writer.write_header(file, header):
            console.print(f"[green]✓[/green] Provenance header written to {file}")
        else:
            console.print("[yellow]Header already up to date[/yellow]")
    else:
        if writer.remove_header(file):
            console.print(f"[green]✓[/green] Provenance header removed from {file}")
        else:
            console.print("[yellow]No header found[/yellow]")


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def verify(file: Path) -> None:
    """Verify round-trip integrity of provenance header."""
    # Create a test header
    header = ProvenanceHeader(
        regions=[
            ProvenanceRegion(1, 10, AttributionLabel.HUMAN, 0.9, "human", ["type-hints"]),
            ProvenanceRegion(11, 20, AttributionLabel.AI_GENERATED, 0.85, "copilot", []),
        ],
        used_by=["codedna-cli"],
        rules=["no-secrets", "type-hints"],
    )

    if round_trip_test(file, header):
        console.print(f"[green]✓[/green] Round-trip test passed for {file}")
    else:
        console.print(f"[red]✗[/red] Round-trip test failed for {file}")


@main.command()
def server() -> None:
    """Run stdio IPC server for VS Code extension."""
    import asyncio
    from .ipc import IPCServer

    server = IPCServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
