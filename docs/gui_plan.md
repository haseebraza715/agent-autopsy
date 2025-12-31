# GUI Plan for Agent Autopsy

This document describes a practical plan to build a GUI for Agent Autopsy without implementing anything yet. It focuses on architecture, workflows, data flow, and milestones so the UI can be built later with minimal surprises.

---

## Goals

- Provide a clear, user-friendly interface for analyzing trace files.
- Support both deterministic and LLM analysis modes.
- Surface pre-analysis signals, hypotheses, and evidence in a navigable way.
- Make batch trace analysis and report browsing easy.
- Keep the GUI aligned with the existing CLI behavior and outputs.

Non-goals:
- Replace the CLI or alter core analysis logic.
- Add new analysis features beyond what already exists.

---

## Target Users

- Engineers debugging agent traces.
- Researchers investigating failure patterns.
- Operators running batch analysis on stored traces.

---

## Core User Flows

1) Single Trace Analysis
   - Upload or select a trace file.
   - Choose analysis mode (LLM vs deterministic).
   - Run analysis and view report.
   - Download report and artifacts.

2) Trace Summary / Quick Inspect
   - Drop a trace file.
   - View summary stats and detected signals.
   - Optionally run full analysis.

3) Batch Analysis
   - Select a traces directory.
   - Run batch analysis.
   - View summary report and per-trace results.

4) Trace Viewer
   - Browse timeline of events.
   - Filter by event type, tool name, errors.
   - Inspect event details and inputs/outputs.

---

## Proposed UI Pages (Streamlit Sections)

1) Home / Dashboard
   - Quick actions: Analyze Trace, Batch Analysis, View Reports.
   - Recent traces and reports.

2) Analyze Trace
   - File picker / drag-and-drop.
   - Options: output format, model override, no-LLM toggle.
   - Run button and progress indicator.
   - Summary panel, signals, hypotheses, report preview.

3) Trace Viewer
   - Timeline list + detail pane.
   - Filters (event type, error-only, tool name).
   - Search by event ID.

4) Batch Analysis
   - Directory picker.
   - Run analysis, progress, and table of results.
   - Link to generated summary report.

5) Reports
   - List of saved reports.
   - Open/download report.
   - Quick metadata (run_id, status, confidence).

6) Settings
   - Model defaults, OpenRouter key status, trace dirs.
   - Toggle tracing (for live capture workflows).

---

## UX Details (Streamlit)

- Provide a single primary action per page (e.g., Analyze, Run Batch).
- Use expanders for verbose sections (signals, evidence, raw report).
- Use tabs for major sections (Summary, Signals, Hypotheses, Timeline, Report).
- Use sidebar for global settings (model, output format, API key status).
- Keep event detail in a right-side column (two-column layout).

## UI Quality Bar

- Use `st.metric` for key stats (errors, duration, total events, confidence).
- Use `st.status` or `st.spinner` for long-running analysis steps.
- Use severity colors and icons for signals (critical/high/medium/low).
- Use `st.dataframe` for event tables with search/filter controls.
- Provide report download buttons for both Markdown and JSON.

---

## Data/Logic Integration

The GUI should call existing Python entry points:

- `src.cli analyze` for single trace analysis.
- `src.cli summary` for quick summary.
- `src.cli validate` for format validation.
- `scripts/analyze_traces.py` for batch analysis (or call its module API).

Prefer a thin API layer to invoke the same functions the CLI uses:
- `parse_trace_file`, `TraceNormalizer`, `RootCauseBuilder`, `run_analysis`,
  `run_analysis_without_llm`, `ReportGenerator`, `ArtifactGenerator`.

---

## Architecture (Streamlit-Only)

Use a single-process Streamlit app that calls the same Python functions as the CLI.

- No separate backend server required.
- Keep all processing local.
- Use Streamlit session state to store results between interactions.

---

## Streamlit App Structure

Single entry file (example: `app.py`):

- Sidebar
  - Navigation: `st.sidebar.radio(["Home", "Analyze", "Trace Viewer", "Batch", "Reports", "Settings"])`
  - File picker (single trace or batch directory).
  - Analysis options: `--no-llm`, model override, output format.
  - Status: API key present or missing.

- Main content (tabs)
  - `Summary`: trace stats, status, duration.
  - `Signals`: detected patterns with severity and evidence.
  - `Hypotheses`: top suspects with confidence.
  - `Timeline`: event list with filters.
  - `Report`: rendered markdown report + download button.

Session state keys:
- `trace`
- `preanalysis`
- `analysis_result`
- `report_markdown`
- `report_json`

---

## File and Artifact Handling

- Store generated reports in `reports/`.
- Store artifacts in user-selected output directory.
- Track recent reports in a lightweight index file (e.g., `reports/index.json`).

---

## Security & Privacy

- Keep all processing local by default.
- Only use network calls when LLM analysis is enabled and API key is set.
- Redact secrets in trace displays (reuse existing redaction logic if needed).

---

## Error Handling & UX States

- Parse errors should surface actionable messages.
- LLM failures should auto-fallback to deterministic analysis (matching CLI).
- Display a clear banner when `OPENROUTER_API_KEY` is missing.

---

## Milestones (Streamlit)

1) MVP
   - Single trace analysis page.
   - Summary + report preview.

2) Trace Viewer
   - Timeline + event details with filtering.

3) Batch Analysis
   - Directory run + summary table.

4) Reports & History
   - Report list + download.

5) Settings & UX polish
   - Model overrides, output format, preferences.

---

## Technical Dependencies (Streamlit)

- `streamlit`
- Existing project dependencies

---

## Open Questions

- Should the GUI support live trace capture or only static files?
- Where should configuration settings live (env file vs UI settings)?
- Do we want user authentication, or keep it local-only?

---

## Success Criteria

- Analyze a trace end-to-end without using the CLI.
- View signals, hypotheses, and evidence clearly.
- Run batch analysis and access the summary report.
- Match CLI outputs and behavior for consistency.
