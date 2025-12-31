"""
CLI interface for Agent Autopsy.

Provides commands for analyzing traces and generating reports.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.ingestion import parse_trace_file, TraceNormalizer
from src.preanalysis import RootCauseBuilder
from src.analysis import run_analysis
from src.analysis.agent import run_analysis_without_llm
from src.output import ReportGenerator, ArtifactGenerator
from src.utils.config import get_config

app = typer.Typer(
    name="autopsy",
    help="Agent Autopsy - Debug and analyze agent execution traces",
    add_completion=False,
)
console = Console()


@app.command()
def analyze(
    trace_file: Path = typer.Argument(
        ...,
        help="Path to the trace JSON file",
        exists=True,
        readable=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "-o", "--output",
        help="Output file path for the report",
    ),
    artifacts: Optional[Path] = typer.Option(
        None,
        "--artifacts",
        help="Output directory for patch artifacts",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Model to use for analysis (overrides default)",
    ),
    verbose: bool = typer.Option(
        False,
        "-v", "--verbose",
        help="Show detailed output including tool traces",
    ),
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Run only deterministic analysis without LLM",
    ),
    format: str = typer.Option(
        "markdown",
        "-f", "--format",
        help="Output format: markdown or json",
    ),
):
    """
    Analyze an agent execution trace and generate an autopsy report.

    Example:
        autopsy analyze ./traces/run_001.json
        autopsy analyze ./traces/run_001.json -o report.md --artifacts ./patches/
    """
    config = get_config()

    console.print(Panel.fit(
        "[bold blue]Agent Autopsy[/bold blue]\n"
        "Analyzing agent execution trace...",
        border_style="blue",
    ))

    # Step 1: Parse trace
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing trace file...", total=None)

        try:
            trace = parse_trace_file(trace_file)
            trace = TraceNormalizer.normalize(trace)
        except Exception as e:
            console.print(f"[red]Error parsing trace:[/red] {e}")
            raise typer.Exit(1)

        progress.update(task, description="Trace parsed successfully")

    # Show trace summary
    summary = TraceNormalizer.get_summary(trace)
    _print_trace_summary(summary)

    # Step 2: Run pre-analysis
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running pre-analysis...", total=None)

        preanalysis = RootCauseBuilder(trace).build()
        progress.update(task, description="Pre-analysis complete")

    # Show pre-analysis results
    if verbose:
        _print_preanalysis(preanalysis)

    # Step 3: Run analysis
    if no_llm or not config.openrouter_api_key:
        if not no_llm:
            console.print("[yellow]Warning:[/yellow] No API key configured. Running without LLM.")

        result = run_analysis_without_llm(trace)
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Running LLM analysis with {model or config.default_model}...", total=None)

            try:
                result = run_analysis(trace, model=model, verbose=verbose)
            except Exception as e:
                console.print(f"[yellow]LLM analysis failed:[/yellow] {e}")
                console.print("Falling back to deterministic analysis...")
                result = run_analysis_without_llm(trace)

            progress.update(task, description="Analysis complete")

    # Step 4: Generate report
    report_generator = ReportGenerator(trace, result)

    if output:
        saved_path = report_generator.save(output, format=format)
        console.print(f"\n[green]Report saved to:[/green] {saved_path}")
    else:
        # Print to console
        console.print("\n")
        if format == "json":
            import json
            console.print_json(json.dumps(report_generator.to_json(), default=str))
        else:
            console.print(report_generator.to_markdown())

    # Step 5: Generate artifacts if requested
    if artifacts:
        artifact_generator = ArtifactGenerator(trace, preanalysis)
        saved_artifacts = artifact_generator.save_all(artifacts)

        console.print(f"\n[green]Artifacts saved to:[/green] {artifacts}")
        for path in saved_artifacts:
            console.print(f"  - {path.name}")

    # Print summary
    console.print("\n")
    _print_result_summary(result, preanalysis)


@app.command()
def summary(
    trace_file: Path = typer.Argument(
        ...,
        help="Path to the trace JSON file",
        exists=True,
        readable=True,
    ),
):
    """
    Show a quick summary of a trace without full analysis.

    Example:
        autopsy summary ./traces/run_001.json
    """
    try:
        trace = parse_trace_file(trace_file)
        trace = TraceNormalizer.normalize(trace)
    except Exception as e:
        console.print(f"[red]Error parsing trace:[/red] {e}")
        raise typer.Exit(1)

    summary = TraceNormalizer.get_summary(trace)
    _print_trace_summary(summary)

    # Quick pre-analysis
    preanalysis = RootCauseBuilder(trace).build()
    _print_preanalysis(preanalysis)


@app.command()
def validate(
    trace_file: Path = typer.Argument(
        ...,
        help="Path to the trace JSON file",
        exists=True,
        readable=True,
    ),
):
    """
    Validate a trace file format without running analysis.

    Example:
        autopsy validate ./traces/run_001.json
    """
    try:
        trace = parse_trace_file(trace_file)
        issues = TraceNormalizer.validate(trace)

        if issues:
            console.print("[yellow]Validation issues found:[/yellow]")
            for issue in issues:
                console.print(f"  - {issue}")
        else:
            console.print("[green]Trace is valid![/green]")

        # Print basic info
        console.print(f"\nRun ID: {trace.run_id}")
        console.print(f"Events: {len(trace.events)}")
        console.print(f"Status: {trace.status.value}")

    except Exception as e:
        console.print(f"[red]Invalid trace file:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def config():
    """
    Show current configuration.
    """
    cfg = get_config()

    table = Table(title="Agent Autopsy Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    for key, value in cfg.to_dict().items():
        table.add_row(key, str(value))

    console.print(table)


def _print_trace_summary(summary: dict):
    """Print trace summary table."""
    table = Table(title="Trace Summary", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Run ID", summary.get("run_id", "N/A"))
    table.add_row("Status", summary.get("status", "N/A"))
    table.add_row("Framework", summary.get("framework", "N/A"))
    table.add_row("Model", summary.get("model", "N/A"))
    table.add_row("Total Events", str(summary.get("total_events", 0)))
    table.add_row("LLM Calls", str(summary.get("llm_calls", 0)))
    table.add_row("Tool Calls", str(summary.get("tool_calls", 0)))
    table.add_row("Errors", str(summary.get("errors", 0)))
    table.add_row("Total Tokens", str(summary.get("total_tokens", "N/A")))
    table.add_row("Duration (ms)", str(summary.get("duration_ms", "N/A")))

    console.print(table)


def _print_preanalysis(preanalysis):
    """Print pre-analysis results."""
    console.print("\n[bold]Pre-Analysis Results[/bold]")
    console.print(f"Summary: {preanalysis.summary}")

    if preanalysis.signals:
        console.print("\n[bold]Signals Detected:[/bold]")
        for signal in preanalysis.signals:
            severity_color = {
                "critical": "red",
                "high": "yellow",
                "medium": "blue",
                "low": "white",
            }.get(signal.severity, "white")

            console.print(
                f"  [{severity_color}]{signal.severity.upper()}[/{severity_color}] "
                f"{signal.type}: {signal.evidence}"
            )
            console.print(f"    Events: {signal.event_ids}")

    if preanalysis.hypotheses:
        console.print("\n[bold]Top Hypotheses:[/bold]")
        for i, hyp in enumerate(preanalysis.hypotheses[:3], 1):
            console.print(f"  {i}. {hyp.description}")
            console.print(f"     Confidence: {hyp.confidence:.0%} | Category: {hyp.category}")


def _print_result_summary(result, preanalysis):
    """Print analysis result summary."""
    status = "[green]SUCCESS[/green]" if result.success else "[red]FAILED[/red]"
    console.print(Panel.fit(
        f"Analysis Status: {status}\n"
        f"Signals Found: {len(preanalysis.signals)}\n"
        f"Hypotheses Generated: {len(preanalysis.hypotheses)}",
        title="Analysis Complete",
        border_style="green" if result.success else "red",
    ))


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
