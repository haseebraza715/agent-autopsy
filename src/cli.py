"""
CLI interface for Agent Autopsy.

Provides commands for analyzing traces and generating reports.
"""

import json
from datetime import datetime
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


@app.command("autopsy-run")
def autopsy_run(
    trace_file: Path = typer.Argument(
        ...,
        help="Path to the trace JSON file to analyze",
        exists=True,
        readable=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "-o", "--output",
        help="Output file path for the report (default: ./reports/<trace_name>.md)",
    ),
):
    """
    Run autopsy analysis on a captured trace file.

    This command loads a trace JSON file (captured by TraceSaver),
    analyzes it for patterns and issues, and generates a report.

    Example:
        python -m src.cli autopsy-run traces/20241231_123456_abc123.json
        python -m src.cli autopsy-run traces/my_trace.json -o report.md
    """
    console.print(Panel.fit(
        "[bold blue]Agent Autopsy[/bold blue]\n"
        "Analyzing captured trace...",
        border_style="blue",
    ))

    # Load trace JSON
    try:
        with open(trace_file, "r") as f:
            trace_data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading trace file:[/red] {e}")
        raise typer.Exit(1)

    # Print basic stats
    run_id = trace_data.get("run_id", "unknown")
    total_events = trace_data.get("total_events", len(trace_data.get("events", [])))
    duration_ms = trace_data.get("duration_ms", "N/A")
    start_time = trace_data.get("start_time", "N/A")

    events = trace_data.get("events", [])

    # Count event types
    event_counts = {}
    error_count = 0
    for event in events:
        event_type = event.get("type", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
        if event_type == "error":
            error_count += 1

    # Detect potential loops (same tool+input repeated)
    tool_calls = []
    for event in events:
        if event.get("type") == "tool_start":
            tool_calls.append((event.get("name"), str(event.get("input", ""))[:100]))

    loop_count = 0
    if len(tool_calls) >= 3:
        for i in range(len(tool_calls) - 2):
            if tool_calls[i] == tool_calls[i+1] == tool_calls[i+2]:
                loop_count += 1

    # Print trace summary
    table = Table(title="Trace Summary", show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Trace File", str(trace_file))
    table.add_row("Run ID", run_id)
    table.add_row("Start Time", start_time)
    table.add_row("Duration (ms)", str(duration_ms))
    table.add_row("Total Events", str(total_events))
    table.add_row("Errors", f"[red]{error_count}[/red]" if error_count else "0")
    table.add_row("Potential Loops", f"[yellow]{loop_count}[/yellow]" if loop_count else "0")

    console.print(table)

    # Print event type breakdown
    console.print("\n[bold]Event Type Breakdown:[/bold]")
    for event_type, count in sorted(event_counts.items()):
        console.print(f"  {event_type}: {count}")

    # Print errors if any
    if error_count > 0:
        console.print("\n[bold red]Errors Found:[/bold red]")
        for event in events:
            if event.get("type") == "error":
                console.print(f"  - Event {event.get('event_id')}: {event.get('error', 'Unknown error')}")
                if event.get("name"):
                    console.print(f"    Component: {event.get('name')}")

    # Generate report
    report_lines = [
        f"# Autopsy Report: {run_id}",
        "",
        "## Trace Summary",
        "",
        f"- **Trace File:** `{trace_file}`",
        f"- **Run ID:** {run_id}",
        f"- **Start Time:** {start_time}",
        f"- **Duration:** {duration_ms}ms",
        f"- **Total Events:** {total_events}",
        f"- **Errors:** {error_count}",
        f"- **Potential Loops:** {loop_count}",
        "",
        "## Event Breakdown",
        "",
    ]

    for event_type, count in sorted(event_counts.items()):
        report_lines.append(f"- **{event_type}:** {count}")

    if error_count > 0:
        report_lines.extend([
            "",
            "## Errors",
            "",
        ])
        for event in events:
            if event.get("type") == "error":
                report_lines.append(f"### Error at Event {event.get('event_id')}")
                report_lines.append("")
                report_lines.append(f"- **Component:** {event.get('name', 'Unknown')}")
                report_lines.append(f"- **Error:** {event.get('error', 'Unknown error')}")
                if event.get("metadata"):
                    report_lines.append(f"- **Error Type:** {event['metadata'].get('error_type', 'Unknown')}")
                report_lines.append("")

    if loop_count > 0:
        report_lines.extend([
            "",
            "## Potential Loops Detected",
            "",
            f"Found {loop_count} potential infinite loop(s) where the same tool was called with the same input 3+ times consecutively.",
            "",
        ])

    report_lines.extend([
        "",
        "## Event Timeline",
        "",
        "| Event ID | Type | Name | Latency (ms) |",
        "|----------|------|------|--------------|",
    ])

    for event in events[:50]:  # Limit to first 50 events for readability
        event_id = event.get("event_id", "-")
        event_type = event.get("type", "-")
        name = event.get("name", "-")
        latency = event.get("latency_ms", "-")
        report_lines.append(f"| {event_id} | {event_type} | {name} | {latency} |")

    if len(events) > 50:
        report_lines.append(f"\n*... and {len(events) - 50} more events*")

    report_lines.extend([
        "",
        "---",
        "",
        f"*Report generated by Agent Autopsy at {datetime.utcnow().isoformat()}Z*",
    ])

    report_content = "\n".join(report_lines)

    # Determine output path
    if output is None:
        reports_dir = Path("./reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        output = reports_dir / f"{trace_file.stem}.md"

    # Write report
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        f.write(report_content)

    console.print(f"\n[green]Report saved to:[/green] {output}")

    # Print summary panel
    status_color = "green" if error_count == 0 and loop_count == 0 else "yellow" if error_count == 0 else "red"
    status_text = "HEALTHY" if error_count == 0 and loop_count == 0 else "WARNING" if error_count == 0 else "ISSUES FOUND"

    console.print(Panel.fit(
        f"Status: [{status_color}]{status_text}[/{status_color}]\n"
        f"Events: {total_events}\n"
        f"Errors: {error_count}\n"
        f"Loops: {loop_count}",
        title="Autopsy Complete",
        border_style=status_color,
    ))


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
