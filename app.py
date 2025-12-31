"""
Agent Autopsy GUI - Streamlit Application

A user-friendly interface for analyzing agent execution traces.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

# Import core Autopsy modules
from src.ingestion import parse_trace_file, TraceNormalizer
from src.preanalysis import RootCauseBuilder
from src.analysis import run_analysis
from src.analysis.agent import run_analysis_without_llm
from src.output import ReportGenerator, ArtifactGenerator
from src.utils.config import get_config, Config


# Page configuration
st.set_page_config(
    page_title="Agent Autopsy",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "trace": None,
        "preanalysis": None,
        "analysis_result": None,
        "report_markdown": None,
        "report_json": None,
        "current_page": "Home",
        "recent_reports": [],
        "batch_results": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_severity_color(severity: str) -> str:
    """Get color for severity level."""
    return {
        "critical": "red",
        "high": "orange",
        "medium": "blue",
        "low": "gray",
    }.get(severity.lower(), "gray")


def get_severity_icon(severity: str) -> str:
    """Get icon for severity level."""
    return {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🔵",
        "low": "⚪",
    }.get(severity.lower(), "⚪")


def get_event_display_name(event) -> str:
    """Get a meaningful display name for an event."""
    name = event.name
    if name and name != "unknown":
        return name

    # Try to extract context from metadata
    if event.metadata:
        node = event.metadata.get("langgraph_node", "")
        if node:
            return f"({node})"
        run_id = event.metadata.get("run_id", "")
        if run_id:
            return f"(run:{run_id[:8]})"

    # Try to extract context from output structure
    if event.output and isinstance(event.output, dict):
        if "analysis_complete" in event.output:
            return "(analysis_result)"
        if "messages" in event.output:
            return "(chain_result)"
        if "trace_summary" in event.output:
            return "(trace_result)"

    return "unnamed"


def load_reports_index() -> list[dict]:
    """Load recent reports from index file."""
    index_path = Path("reports/index.json")
    if index_path.exists():
        try:
            with open(index_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_to_reports_index(report_info: dict):
    """Save report info to index."""
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    index_path = reports_dir / "index.json"

    reports = load_reports_index()
    reports.insert(0, report_info)
    reports = reports[:50]  # Keep last 50

    with open(index_path, "w") as f:
        json.dump(reports, f, indent=2, default=str)


def render_sidebar():
    """Render the sidebar navigation and settings."""
    with st.sidebar:
        st.title("🔍 Agent Autopsy")
        st.markdown("---")

        # Navigation
        pages = ["Home", "Analyze Trace", "Trace Viewer", "Batch Analysis", "Reports", "Settings"]
        selected = st.radio("Navigation", pages, index=pages.index(st.session_state.current_page))
        st.session_state.current_page = selected

        st.markdown("---")

        # API Key Status
        config = get_config()
        if config.openrouter_api_key:
            st.success("API Key: Configured")
        else:
            st.warning("API Key: Not set")
            st.caption("Set OPENROUTER_API_KEY in .env")

        st.markdown("---")

        # Quick stats if trace is loaded
        if st.session_state.trace:
            st.subheader("Loaded Trace")
            trace = st.session_state.trace
            st.text(f"Run ID: {trace.run_id[:20]}...")
            st.text(f"Events: {len(trace.events)}")
            st.text(f"Status: {trace.status.value}")

            if st.button("Clear Trace", width='stretch'):
                st.session_state.trace = None
                st.session_state.preanalysis = None
                st.session_state.analysis_result = None
                st.session_state.report_markdown = None
                st.session_state.report_json = None
                st.rerun()


def render_home_page():
    """Render the home/dashboard page."""
    st.header("Welcome to Agent Autopsy")
    st.markdown("""
    Agent Autopsy helps you debug and analyze agent execution traces.
    Identify root causes, detect patterns, and get actionable recommendations.
    """)

    st.markdown("---")

    # Quick actions
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📊 Analyze Trace")
        st.markdown("Upload and analyze a single trace file.")
        if st.button("Go to Analyze", key="home_analyze", width='stretch'):
            st.session_state.current_page = "Analyze Trace"
            st.rerun()

    with col2:
        st.subheader("📁 Batch Analysis")
        st.markdown("Analyze all traces in a directory.")
        if st.button("Go to Batch", key="home_batch", width='stretch'):
            st.session_state.current_page = "Batch Analysis"
            st.rerun()

    with col3:
        st.subheader("📝 View Reports")
        st.markdown("Browse previously generated reports.")
        if st.button("Go to Reports", key="home_reports", width='stretch'):
            st.session_state.current_page = "Reports"
            st.rerun()

    st.markdown("---")

    # Recent traces
    st.subheader("Recent Traces")
    traces_dir = Path("traces")
    if traces_dir.exists():
        trace_files = sorted(traces_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        if trace_files:
            for idx, trace_file in enumerate(trace_files):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.text(trace_file.name)
                with col2:
                    if st.button("Analyze", key=f"quick_{idx}_{trace_file.name}"):
                        try:
                            trace = parse_trace_file(trace_file)
                            trace = TraceNormalizer.normalize(trace)
                            st.session_state.trace = trace
                            st.session_state.current_page = "Analyze Trace"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error loading trace: {e}")
        else:
            st.info("No trace files found in ./traces/")
    else:
        st.info("Traces directory not found. Create ./traces/ to store trace files.")

    st.markdown("---")

    # Recent reports
    st.subheader("Recent Reports")
    reports = load_reports_index()[:5]
    if reports:
        for idx, report in enumerate(reports):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(f"{report.get('run_id', 'Unknown')[:30]} - {report.get('generated_at', 'Unknown')[:10]}")
            with col2:
                # Use index and run_id to ensure unique key
                run_id = report.get('run_id', f'unknown_{idx}')
                if st.button("View", key=f"view_report_{idx}_{run_id}"):
                    st.session_state.current_page = "Reports"
                    st.rerun()
    else:
        st.info("No reports generated yet.")


def render_analyze_page():
    """Render the analyze trace page."""
    st.header("Analyze Trace")

    # File upload or selection
    upload_tab, select_tab = st.tabs(["Upload File", "Select from Directory"])

    with upload_tab:
        uploaded_file = st.file_uploader("Upload trace JSON file", type=["json"])
        if uploaded_file:
            try:
                content = json.load(uploaded_file)
                # Save temporarily
                temp_path = Path(f"/tmp/autopsy_upload_{uploaded_file.name}")
                with open(temp_path, "w") as f:
                    json.dump(content, f)
                trace = parse_trace_file(temp_path)
                trace = TraceNormalizer.normalize(trace)
                st.session_state.trace = trace
                st.success("Trace loaded successfully!")
            except Exception as e:
                st.error(f"Error parsing trace: {e}")

    with select_tab:
        traces_dir = Path("traces")
        if traces_dir.exists():
            trace_files = list(traces_dir.glob("*.json"))
            if trace_files:
                selected_file = st.selectbox(
                    "Select trace file",
                    options=trace_files,
                    format_func=lambda x: x.name,
                )
                if st.button("Load Trace"):
                    try:
                        trace = parse_trace_file(selected_file)
                        trace = TraceNormalizer.normalize(trace)
                        st.session_state.trace = trace
                        st.success("Trace loaded successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error parsing trace: {e}")
            else:
                st.info("No trace files found in ./traces/")
        else:
            st.info("Traces directory not found.")

    st.markdown("---")

    # Analysis options
    if st.session_state.trace:
        trace = st.session_state.trace

        st.subheader("Analysis Options")
        col1, col2, col3 = st.columns(3)

        with col1:
            no_llm = st.checkbox("Deterministic Only (no LLM)", value=False)

        with col2:
            config = get_config()
            model_override = st.text_input("Model Override", value="", placeholder=config.default_model)

        with col3:
            output_format = st.selectbox("Output Format", ["markdown", "json"])

        # Run analysis button
        if st.button("Run Analysis", type="primary", width='stretch'):
            with st.spinner("Running analysis..."):
                try:
                    # Pre-analysis
                    preanalysis = RootCauseBuilder(trace).build()
                    st.session_state.preanalysis = preanalysis

                    # Full analysis
                    if no_llm or not config.openrouter_api_key:
                        result = run_analysis_without_llm(trace)
                    else:
                        try:
                            model = model_override if model_override else None
                            result = run_analysis(trace, model=model)
                        except Exception as e:
                            st.warning(f"LLM analysis failed: {e}. Falling back to deterministic.")
                            result = run_analysis_without_llm(trace)

                    st.session_state.analysis_result = result

                    # Generate report
                    report_gen = ReportGenerator(trace, result)
                    st.session_state.report_markdown = report_gen.to_markdown()
                    st.session_state.report_json = report_gen.to_json()

                    # Save to reports index
                    report_info = {
                        "run_id": trace.run_id,
                        "status": trace.status.value,
                        "generated_at": datetime.now().isoformat(),
                        "signals": len(preanalysis.signals),
                        "hypotheses": len(preanalysis.hypotheses),
                    }
                    save_to_reports_index(report_info)

                    st.success("Analysis complete!")

                except Exception as e:
                    st.error(f"Analysis failed: {e}")

        st.markdown("---")

        # Display results in tabs
        if st.session_state.trace:
            tabs = st.tabs(["Summary", "Signals", "Hypotheses", "Timeline", "Report"])

            with tabs[0]:
                render_summary_tab(trace)

            with tabs[1]:
                render_signals_tab()

            with tabs[2]:
                render_hypotheses_tab()

            with tabs[3]:
                render_timeline_tab(trace)

            with tabs[4]:
                render_report_tab()


def render_summary_tab(trace):
    """Render trace summary tab."""
    st.subheader("Trace Summary")

    summary = TraceNormalizer.get_summary(trace)

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Status", summary.get("status", "N/A"))
    with col2:
        st.metric("Total Events", summary.get("total_events", 0))
    with col3:
        st.metric("Errors", summary.get("errors", 0))
    with col4:
        duration = summary.get("duration_ms")
        st.metric("Duration", f"{duration}ms" if duration else "N/A")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("LLM Calls", summary.get("llm_calls", 0))
    with col2:
        st.metric("Tool Calls", summary.get("tool_calls", 0))
    with col3:
        tokens = summary.get("total_tokens")
        st.metric("Total Tokens", tokens if tokens else "N/A")
    with col4:
        st.metric("Framework", summary.get("framework", "N/A"))

    st.markdown("---")

    # Details
    with st.expander("Full Details"):
        st.json(summary)


def render_signals_tab():
    """Render signals tab."""
    st.subheader("Detected Signals")

    if not st.session_state.preanalysis:
        st.info("Run analysis to see detected signals.")
        return

    signals = st.session_state.preanalysis.signals

    if not signals:
        st.success("No significant issues detected!")
        return

    for signal in signals:
        icon = get_severity_icon(signal.severity)
        with st.expander(f"{icon} {signal.type} - {signal.severity.upper()}", expanded=signal.severity in ["critical", "high"]):
            st.markdown(f"**Evidence:** {signal.evidence}")
            st.markdown(f"**Events:** {signal.event_ids}")
            if signal.metadata:
                st.json(signal.metadata)


def render_hypotheses_tab():
    """Render hypotheses tab."""
    st.subheader("Root Cause Hypotheses")

    if not st.session_state.preanalysis:
        st.info("Run analysis to see hypotheses.")
        return

    hypotheses = st.session_state.preanalysis.hypotheses

    if not hypotheses:
        st.info("No hypotheses generated.")
        return

    for i, hyp in enumerate(hypotheses, 1):
        confidence_pct = int(hyp.confidence * 100)
        with st.expander(f"#{i}: {hyp.description} ({confidence_pct}% confidence)", expanded=i <= 2):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Category:** {hyp.category}")
                st.progress(hyp.confidence)
            with col2:
                st.markdown(f"**Supporting Events:** {hyp.supporting_events}")

            if hyp.suggested_fixes:
                st.markdown("**Suggested Fixes:**")
                for fix in hyp.suggested_fixes:
                    st.markdown(f"- {fix}")


def render_timeline_tab(trace):
    """Render timeline tab."""
    st.subheader("Event Timeline")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        event_types = ["All"] + list(set(e.type.value for e in trace.events))
        selected_type = st.selectbox("Event Type", event_types)
    with col2:
        show_errors_only = st.checkbox("Errors Only")
    with col3:
        search_term = st.text_input("Search", placeholder="Filter by name or content")

    # Filter events
    events = trace.events
    if selected_type != "All":
        events = [e for e in events if e.type.value == selected_type]
    if show_errors_only:
        events = [e for e in events if e.is_error()]
    if search_term:
        events = [e for e in events if search_term.lower() in str(e.name or "").lower()
                  or search_term.lower() in str(e.input or "").lower()
                  or search_term.lower() in str(e.output or "").lower()]

    st.markdown(f"Showing {len(events)} of {len(trace.events)} events")

    # Display events
    for event in events[:100]:  # Limit to 100 for performance
        error_marker = "❌ " if event.is_error() else ""
        display_name = get_event_display_name(event)
        with st.expander(f"{error_marker}Event {event.event_id}: {event.type.value} - {display_name}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Type:** {event.type.value}")
                st.markdown(f"**Name:** {event.name or 'N/A'}")
                if event.latency_ms:
                    st.markdown(f"**Latency:** {event.latency_ms}ms")
                if event.token_count:
                    st.markdown(f"**Tokens:** {event.token_count}")
            with col2:
                if event.error:
                    st.error(f"**Error:** {event.error.message}")

            if event.input:
                st.markdown("**Input:**")
                if isinstance(event.input, (dict, list)):
                    st.json(event.input)
                elif isinstance(event.input, str):
                    if len(event.input) > 1000:
                        st.code(event.input[:1000] + "...")
                    else:
                        st.code(event.input)
                else:
                    st.code(str(event.input)[:1000])

            if event.output:
                st.markdown("**Output:**")
                if isinstance(event.output, (dict, list)):
                    st.json(event.output)
                elif isinstance(event.output, str):
                    if len(event.output) > 1000:
                        st.code(event.output[:1000] + "...")
                    else:
                        st.code(event.output)
                else:
                    st.code(str(event.output)[:1000])

    if len(events) > 100:
        st.info(f"Showing first 100 events. {len(events) - 100} more events not shown.")


def render_report_tab():
    """Render report tab."""
    st.subheader("Generated Report")

    if not st.session_state.report_markdown:
        st.info("Run analysis to generate a report.")
        return

    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download Markdown",
            st.session_state.report_markdown,
            file_name=f"autopsy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            width='stretch',
        )
    with col2:
        st.download_button(
            "Download JSON",
            json.dumps(st.session_state.report_json, indent=2, default=str),
            file_name=f"autopsy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            width='stretch',
        )

    st.markdown("---")

    # Report preview
    st.markdown(st.session_state.report_markdown)


def render_trace_viewer_page():
    """Render the trace viewer page."""
    st.header("Trace Viewer")

    if not st.session_state.trace:
        st.info("Load a trace from the Analyze page first, or select one below.")

        traces_dir = Path("traces")
        if traces_dir.exists():
            trace_files = list(traces_dir.glob("*.json"))
            if trace_files:
                selected_file = st.selectbox(
                    "Select trace file",
                    options=trace_files,
                    format_func=lambda x: x.name,
                )
                if st.button("Load Trace"):
                    try:
                        trace = parse_trace_file(selected_file)
                        trace = TraceNormalizer.normalize(trace)
                        st.session_state.trace = trace
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error parsing trace: {e}")
        return

    trace = st.session_state.trace

    # Two-column layout
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Events")

        # Filters
        event_types = ["All"] + list(set(e.type.value for e in trace.events))
        selected_type = st.selectbox("Filter by type", event_types, key="viewer_type")
        show_errors = st.checkbox("Show errors only", key="viewer_errors")

        # Event list
        events = trace.events
        if selected_type != "All":
            events = [e for e in events if e.type.value == selected_type]
        if show_errors:
            events = [e for e in events if e.is_error()]

        selected_event = None
        for event in events[:50]:
            error_marker = "❌ " if event.is_error() else ""
            display_name = get_event_display_name(event)
            label = f"{error_marker}{event.event_id}: {event.type.value[:10]}"
            if display_name != "unnamed":
                label += f" - {display_name[:15]}"
            if st.button(label, key=f"ev_{event.event_id}", width='stretch'):
                selected_event = event

    with col2:
        st.subheader("Event Details")

        if selected_event:
            event = selected_event

            st.markdown(f"### Event {event.event_id}: {event.type.value}")

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Name:** {event.name or 'N/A'}")
                st.markdown(f"**Role:** {event.role.value if event.role else 'N/A'}")
            with col_b:
                st.markdown(f"**Latency:** {event.latency_ms}ms" if event.latency_ms else "**Latency:** N/A")
                st.markdown(f"**Tokens:** {event.token_count}" if event.token_count else "**Tokens:** N/A")

            if event.error:
                error_msg = event.error.message
                if event.error.category:
                    error_msg = f"{event.error.category}: {error_msg}"
                st.error(f"**Error:** {error_msg}")
                if event.error.stack:
                    with st.expander("Stack Trace"):
                        st.code(event.error.stack)

            st.markdown("---")

            st.markdown("**Input:**")
            if event.input:
                if isinstance(event.input, (dict, list)):
                    st.json(event.input)
                elif isinstance(event.input, str):
                    st.code(event.input)
                else:
                    st.code(str(event.input))
            else:
                st.text("No input")

            st.markdown("**Output:**")
            if event.output:
                if isinstance(event.output, (dict, list)):
                    st.json(event.output)
                elif isinstance(event.output, str):
                    st.code(event.output)
                else:
                    st.code(str(event.output))
            else:
                st.text("No output")
        else:
            st.info("Select an event from the list to view details.")


def render_batch_analysis_page():
    """Render the batch analysis page."""
    st.header("Batch Analysis")

    st.markdown("Analyze all trace files in a directory at once.")

    # Directory selection
    default_traces_dir = "./traces"
    traces_dir = st.text_input("Traces Directory", value=default_traces_dir)

    # Options
    col1, col2 = st.columns(2)
    with col1:
        no_llm = st.checkbox("Deterministic Only (faster)", value=True, key="batch_no_llm")
    with col2:
        save_reports = st.checkbox("Save Individual Reports", value=True)

    traces_path = Path(traces_dir)
    if traces_path.exists():
        trace_files = list(traces_path.glob("*.json"))
        st.info(f"Found {len(trace_files)} trace files")
    else:
        trace_files = []
        st.warning("Directory not found")

    # Run batch analysis
    if st.button("Run Batch Analysis", type="primary", disabled=len(trace_files) == 0):
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, trace_file in enumerate(trace_files):
            status_text.text(f"Analyzing {trace_file.name}...")

            try:
                trace = parse_trace_file(trace_file)
                trace = TraceNormalizer.normalize(trace)

                preanalysis = RootCauseBuilder(trace).build()

                if no_llm:
                    result = run_analysis_without_llm(trace)
                else:
                    try:
                        result = run_analysis(trace)
                    except:
                        result = run_analysis_without_llm(trace)

                # Save report if requested
                report_path = None
                if save_reports:
                    reports_dir = Path("reports")
                    reports_dir.mkdir(exist_ok=True)
                    report_gen = ReportGenerator(trace, result)
                    report_path = report_gen.save(reports_dir / f"{trace_file.stem}.md")

                results.append({
                    "file": trace_file.name,
                    "run_id": trace.run_id,
                    "status": trace.status.value,
                    "events": len(trace.events),
                    "errors": trace.stats.num_errors,
                    "signals": len(preanalysis.signals),
                    "hypotheses": len(preanalysis.hypotheses),
                    "success": True,
                    "report_path": str(report_path) if report_path else None,
                })

            except Exception as e:
                results.append({
                    "file": trace_file.name,
                    "status": "ERROR",
                    "error": str(e),
                    "success": False,
                })

            progress_bar.progress((i + 1) / len(trace_files))

        status_text.text("Batch analysis complete!")
        st.session_state.batch_results = results

    # Display results
    if st.session_state.batch_results:
        st.markdown("---")
        st.subheader("Results")

        results = st.session_state.batch_results

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Traces", len(results))
        with col2:
            successful = sum(1 for r in results if r.get("success"))
            st.metric("Successful", successful)
        with col3:
            total_signals = sum(r.get("signals", 0) for r in results)
            st.metric("Total Signals", total_signals)
        with col4:
            total_errors = sum(r.get("errors", 0) for r in results)
            st.metric("Total Errors", total_errors)

        # Results table
        st.dataframe(
            results,
            width='stretch',
            column_config={
                "file": "File",
                "run_id": "Run ID",
                "status": "Status",
                "events": "Events",
                "errors": "Errors",
                "signals": "Signals",
                "hypotheses": "Hypotheses",
                "success": "Success",
            },
        )


def render_reports_page():
    """Render the reports page."""
    st.header("Reports")

    reports_dir = Path("reports")

    if not reports_dir.exists():
        st.info("No reports directory found. Run an analysis to generate reports.")
        return

    # List report files
    report_files = list(reports_dir.glob("*.md")) + list(reports_dir.glob("*.json"))
    report_files = sorted(report_files, key=lambda x: x.stat().st_mtime, reverse=True)

    if not report_files:
        st.info("No reports found. Run an analysis to generate reports.")
        return

    # Report list
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Available Reports")
        selected_report = None
        for idx, report_file in enumerate(report_files[:20]):
            mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
            label = f"{report_file.name}\n{mtime.strftime('%Y-%m-%d %H:%M')}"
            if st.button(report_file.name, key=f"rep_{idx}_{report_file.name}", width='stretch'):
                selected_report = report_file

    with col2:
        st.subheader("Report Content")

        if selected_report:
            content = selected_report.read_text()

            # Download button
            st.download_button(
                "Download Report",
                content,
                file_name=selected_report.name,
                mime="text/markdown" if selected_report.suffix == ".md" else "application/json",
            )

            st.markdown("---")

            if selected_report.suffix == ".json":
                try:
                    st.json(json.loads(content))
                except:
                    st.code(content)
            else:
                st.markdown(content)
        else:
            st.info("Select a report from the list to view.")


def render_settings_page():
    """Render the settings page."""
    st.header("Settings")

    config = get_config()

    st.subheader("API Configuration")

    # API Key status
    if config.openrouter_api_key:
        st.success("OpenRouter API Key is configured")
        if st.checkbox("Show API Key"):
            st.code(config.openrouter_api_key[:10] + "..." + config.openrouter_api_key[-4:])
    else:
        st.warning("OpenRouter API Key is not set")
        st.markdown("""
        To enable LLM analysis, set `OPENROUTER_API_KEY` in your `.env` file:
        ```
        OPENROUTER_API_KEY=your_key_here
        ```
        """)

    st.markdown("---")

    st.subheader("Model Settings")
    st.text(f"Default Model: {config.default_model}")
    st.text(f"Fallback Model: {config.fallback_model}")

    st.markdown("---")

    st.subheader("Detection Thresholds")
    col1, col2 = st.columns(2)
    with col1:
        st.text(f"Loop Threshold: {config.loop_threshold}")
        st.text(f"Context Overflow: {config.context_overflow_threshold} tokens")
    with col2:
        st.text(f"Retry Window: {config.retry_window_seconds}s")
        st.text(f"Max Retries: {config.max_retries}")

    st.markdown("---")

    st.subheader("Paths")
    st.text(f"Output Directory: {config.output_dir}")
    st.text(f"Trace Directory: {config.trace_dir}")

    st.markdown("---")

    st.subheader("Current Configuration")
    with st.expander("View Full Config"):
        st.json(config.to_dict())


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()

    # Route to appropriate page
    page = st.session_state.current_page

    if page == "Home":
        render_home_page()
    elif page == "Analyze Trace":
        render_analyze_page()
    elif page == "Trace Viewer":
        render_trace_viewer_page()
    elif page == "Batch Analysis":
        render_batch_analysis_page()
    elif page == "Reports":
        render_reports_page()
    elif page == "Settings":
        render_settings_page()


if __name__ == "__main__":
    main()
