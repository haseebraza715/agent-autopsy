"""
CLI interface for Agent Autopsy.

Provides commands for analyzing traces and generating reports.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src import api
from src.advanced import benchmark_trace_directory, compare_traces_advanced, LiveTraceMonitor
from src.errors import ParseError, PluginError, SchemaValidationError
from src.ingestion import TraceNormalizer
from src.output import ArtifactGenerator, FixSuggestionGenerator, ReportGenerator
from src.utils.config import get_config

logger = logging.getLogger(__name__)

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
    no_embeddings: bool = typer.Option(
        False,
        "--no-embeddings",
        help="Do not load sentence-transformers for semantic drift (saves memory)",
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
    prev_skip = config.skip_embeddings
    if no_embeddings:
        config.skip_embeddings = True

    try:
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
                trace = api.load_trace(trace_file)
                api.apply_embedding_defaults_for_trace(trace)
            except (ParseError, SchemaValidationError, PluginError) as e:
                console.print(f"[red]Error parsing trace:[/red] {e}")
                raise typer.Exit(1)
            except Exception:
                logger.exception("Unexpected error while parsing trace file")
                console.print("[red]Error parsing trace (see logs for details).[/red]")
                raise typer.Exit(1)

            progress.update(task, description="Trace parsed successfully")

        # Show trace summary
        summary = api.trace_summary(trace)
        _print_trace_summary(summary)

        # Step 2: Run pre-analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running pre-analysis...", total=None)

            preanalysis = api.run_preanalysis(trace)
            progress.update(task, description="Pre-analysis complete")

        # Show pre-analysis results
        if verbose:
            _print_preanalysis(preanalysis)

        # Step 3: Run analysis
        if no_llm or not api.llm_credentials_configured(config):
            if not no_llm:
                console.print("[yellow]Warning:[/yellow] No API key configured for the selected LLM provider. Running without LLM.")

            result = api.run_deterministic_analysis(trace)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Running LLM analysis with {model or config.default_model}...", total=None)

                try:
                    result = api.run_llm_analysis(trace, model=model, verbose=verbose)
                except Exception as e:
                    logger.exception("LLM analysis failed")
                    console.print(f"[yellow]LLM analysis failed:[/yellow] {e}")
                    console.print("Falling back to deterministic analysis...")
                    result = api.run_deterministic_analysis(trace)

                progress.update(task, description="Analysis complete")

        # Step 4: Generate report
        report_generator = api.generate_report(trace, result)

        if output:
            saved_path = report_generator.save(output, format=format)
            console.print(f"\n[green]Report saved to:[/green] {saved_path}")
        else:
            # Print to console
            console.print("\n")
            if format == "json":
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
    finally:
        config.skip_embeddings = prev_skip


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
        trace = api.load_trace(trace_file)
    except (ParseError, SchemaValidationError, PluginError) as e:
        console.print(f"[red]Error parsing trace:[/red] {e}")
        raise typer.Exit(1)
    except Exception:
        logger.exception("Unexpected error parsing trace")
        console.print("[red]Error parsing trace (see logs for details).[/red]")
        raise typer.Exit(1)

    summary = api.trace_summary(trace)
    _print_trace_summary(summary)

    # Quick pre-analysis
    preanalysis = api.run_preanalysis(trace)
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
        trace = api.load_trace(trace_file)
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

    except (ParseError, SchemaValidationError, PluginError) as e:
        console.print(f"[red]Invalid trace file:[/red] {e}")
        raise typer.Exit(1)
    except Exception:
        logger.exception("Unexpected error validating trace")
        console.print("[red]Invalid trace file (see logs for details).[/red]")
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


@app.command()
def compare(
    trace_a: Path = typer.Argument(..., exists=True, readable=True, help="First trace file"),
    trace_b: Path = typer.Argument(..., exists=True, readable=True, help="Second trace file"),
):
    """Compare two traces and highlight regressions/improvements."""
    try:
        a = api.load_trace(trace_a)
        b = api.load_trace(trace_b)
    except (ParseError, SchemaValidationError, PluginError) as e:
        console.print(f"[red]Error parsing traces:[/red] {e}")
        raise typer.Exit(1)
    except Exception:
        logger.exception("Unexpected error parsing traces for compare")
        console.print("[red]Error parsing traces (see logs for details).[/red]")
        raise typer.Exit(1)

    result = compare_traces_advanced(a, b)
    table = Table(title="Trace Comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Trace A", a.run_id)
    table.add_row("Trace B", b.run_id)
    table.add_row("New Tool Signatures", str(len(result.new_tool_signatures)))
    table.add_row("Removed Tool Signatures", str(len(result.removed_tool_signatures)))
    table.add_row("Changed LLM Outputs", str(len(result.changed_llm_outputs)))
    table.add_row("Regressions", ", ".join(result.regressions) if result.regressions else "None")
    table.add_row("Improvements", ", ".join(result.improvements) if result.improvements else "None")
    console.print(table)


@app.command()
def benchmark(
    traces_dir: Path = typer.Option(
        Path("./traces"),
        "--traces-dir",
        help="Directory containing trace JSON files",
    ),
    limit: int = typer.Option(100, "--limit", help="Maximum number of traces to include"),
):
    """Run benchmark/evaluation metrics across traces."""
    result = benchmark_trace_directory(traces_dir, limit=limit).to_dict()
    table = Table(title="Benchmark Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Total Runs", str(result["total_runs"]))
    table.add_row("Success Rate", f"{result['success_rate']:.0%}")
    table.add_row("Average Tokens", str(result["average_tokens"]))
    table.add_row("Average Latency (ms)", str(result["average_latency_ms"]))
    table.add_row("Average Errors", str(result["average_errors"]))
    table.add_row(
        "Top Patterns",
        ", ".join(f"{p['pattern']}({p['count']})" for p in result["top_failure_patterns"]) or "None",
    )
    table.add_row(
        "Degradation Alerts",
        "; ".join(result["degradation_alerts"]) if result["degradation_alerts"] else "None",
    )
    console.print(table)


@app.command()
def monitor(
    traces_dir: Path = typer.Option(Path("./traces"), "--traces-dir", help="Trace directory to monitor"),
    duration: float = typer.Option(10.0, "--duration", help="Monitor duration in seconds"),
    poll_interval: float = typer.Option(1.0, "--poll-interval", help="Polling interval in seconds"),
    max_alerts: int = typer.Option(50, "--max-alerts", help="Maximum alerts to print"),
):
    """Monitor traces in near real-time and print pattern alerts."""
    mon = LiveTraceMonitor(traces_dir, poll_interval_seconds=poll_interval)
    alert_count = 0
    for alert in mon.stream(duration_seconds=duration):
        console.print(
            f"[yellow]alert[/yellow] {alert.severity.upper()} "
            f"{alert.pattern_type} run={alert.run_id} events={alert.event_ids} "
            f"file={alert.trace_file}"
        )
        alert_count += 1
        if alert_count >= max_alerts:
            break
    console.print(f"Monitoring complete. Alerts emitted: {alert_count}")


@app.command()
def fixes(
    trace_file: Path = typer.Argument(..., exists=True, readable=True, help="Trace file path"),
):
    """Generate advanced fix suggestions for a trace."""
    try:
        trace = api.load_trace(trace_file)
    except (ParseError, SchemaValidationError, PluginError) as e:
        console.print(f"[red]Error parsing trace:[/red] {e}")
        raise typer.Exit(1)
    except Exception:
        logger.exception("Unexpected error parsing trace for fixes")
        console.print("[red]Error parsing trace (see logs for details).[/red]")
        raise typer.Exit(1)

    preanalysis = api.run_preanalysis(trace)
    suggestions = FixSuggestionGenerator(trace, preanalysis).to_dict()
    if not suggestions:
        console.print("No advanced fix suggestions generated.")
        return

    for idx, suggestion in enumerate(suggestions, 1):
        console.print(Panel.fit(
            f"[bold]{suggestion['title']}[/bold]\n"
            f"Category: {suggestion['category']}\n"
            f"Events: {suggestion['event_ids']}\n\n"
            f"Rationale: {suggestion['rationale']}\n\n"
            f"Patch snippet:\n{suggestion['patch_snippet']}",
            title=f"Fix Suggestion {idx}",
            border_style="blue",
        ))


@app.command("agent-flow")
def agent_flow(
    trace_file: Path = typer.Argument(..., exists=True, readable=True, help="Trace file path"),
):
    """Show inter-agent communication and handoff flow."""
    try:
        trace = api.load_trace(trace_file)
    except (ParseError, SchemaValidationError, PluginError) as e:
        console.print(f"[red]Error parsing trace:[/red] {e}")
        raise typer.Exit(1)
    except Exception:
        logger.exception("Unexpected error parsing trace for agent-flow")
        console.print("[red]Error parsing trace (see logs for details).[/red]")
        raise typer.Exit(1)

    agent_ids = trace.get_agent_ids()
    handoffs = trace.get_agent_handoffs()
    table = Table(title="Agent Flow")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Agents", ", ".join(agent_ids) if agent_ids else "None")
    table.add_row("Handoffs", str(len(handoffs)))
    console.print(table)

    if handoffs:
        detail = Table(title="Handoff Details")
        detail.add_column("Event ID", style="cyan")
        detail.add_column("From", style="white")
        detail.add_column("To", style="white")
        for event_id, src, dst in handoffs:
            detail.add_row(str(event_id), src, dst)
        console.print(detail)


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
    table.add_row("Agent Count", str(summary.get("agent_count", 0)))

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


def _print_preanalysis_summary(preanalysis):
    """Backward-compatible alias for concise pre-analysis output."""
    _print_preanalysis(preanalysis)


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
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Run only deterministic analysis without LLM",
    ),
    no_embeddings: bool = typer.Option(
        False,
        "--no-embeddings",
        help="Do not load sentence-transformers for semantic drift (saves memory)",
    ),
    verbose: bool = typer.Option(
        False,
        "-v", "--verbose",
        help="Show detailed output",
    ),
):
    """
    Run full autopsy analysis on a captured trace file.

    This command loads a trace JSON file (captured by TraceSaver),
    runs the complete analysis pipeline (parsing, normalization,
    pattern detection, and LLM analysis), and generates a report.

    Example:
        python -m src.cli autopsy-run traces/20241231_123456_abc123.json
        python -m src.cli autopsy-run traces/my_trace.json -o report.md --no-llm
    """
    config = get_config()
    prev_skip = config.skip_embeddings
    if no_embeddings:
        config.skip_embeddings = True

    try:
        console.print(Panel.fit(
            "[bold blue]Agent Autopsy[/bold blue]\n"
            "Running full analysis pipeline...",
            border_style="blue",
        ))

        # Step 1: Parse and normalize trace
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Parsing trace file...", total=None)

            try:
                trace = api.load_trace(trace_file)
                api.apply_embedding_defaults_for_trace(trace)
            except (ParseError, SchemaValidationError, PluginError) as e:
                console.print(f"[red]Error parsing trace:[/red] {e}")
                raise typer.Exit(1)
            except Exception:
                logger.exception("Unexpected error parsing trace for autopsy-run")
                console.print("[red]Error parsing trace (see logs for details).[/red]")
                raise typer.Exit(1)

            progress.update(task, description="Trace parsed successfully")

        # Print trace summary
        table = Table(title="Trace Summary", show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Trace File", str(trace_file))
        table.add_row("Run ID", trace.run_id)
        table.add_row("Status", trace.status.value)
        table.add_row("Total Events", str(len(trace.events)))
        table.add_row("LLM Calls", str(trace.stats.num_llm_calls))
        table.add_row("Tool Calls", str(trace.stats.num_tool_calls))
        table.add_row("Errors", f"[red]{trace.stats.num_errors}[/red]" if trace.stats.num_errors else "0")

        console.print(table)

        # Step 2: Run pre-analysis
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running pre-analysis...", total=None)

            preanalysis = api.run_preanalysis(trace)

            progress.update(
                task,
                description=f"Pre-analysis complete: {len(preanalysis.signals)} signals, {len(preanalysis.hypotheses)} hypotheses",
            )

        if verbose:
            _print_preanalysis_summary(preanalysis)

        # Step 3: Run analysis (LLM or deterministic)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            if no_llm or not api.llm_credentials_configured(config):
                task = progress.add_task("Running deterministic analysis...", total=None)
                result = api.run_deterministic_analysis(trace)
            else:
                task = progress.add_task("Running LLM analysis...", total=None)
                try:
                    result = api.run_llm_analysis(trace, verbose=verbose)
                except Exception as e:
                    logger.exception("LLM analysis failed in autopsy-run")
                    console.print(f"[yellow]LLM analysis failed, falling back to deterministic:[/yellow] {e}")
                    result = api.run_deterministic_analysis(trace)

            progress.update(task, description="Analysis complete")

        # Step 4: Generate report
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating report...", total=None)

            # Determine output path
            if output is None:
                reports_dir = Path("./reports")
                reports_dir.mkdir(parents=True, exist_ok=True)
                output = reports_dir / f"{trace_file.stem}.md"

            # Generate and save the report
            report_gen = api.generate_report(trace, result)
            output_format = "json" if output.suffix.lower() == ".json" else "markdown"
            output = report_gen.save(output, format=output_format)

            progress.update(task, description="Report generated")

        console.print(f"\n[green]Report saved to:[/green] {output}")

        # Print result summary
        _print_result_summary(result, preanalysis)

        # Return status based on findings
        if trace.stats.num_errors > 0 or len(preanalysis.signals) > 0:
            console.print("\n[yellow]Issues detected in trace - review report for details[/yellow]")
        else:
            console.print("\n[green]No issues detected in trace[/green]")
    finally:
        config.skip_embeddings = prev_skip


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
