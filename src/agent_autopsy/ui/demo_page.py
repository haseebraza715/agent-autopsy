"""Minimal demo experience backed by the real deterministic analysis pipeline."""

from __future__ import annotations

import html
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st

from agent_autopsy import api
from agent_autopsy.errors import ParseError, PluginError, SchemaValidationError
from agent_autopsy.preanalysis import PreAnalysisBundle
from agent_autopsy.schema import EventType, Trace, TraceEvent

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DIR = REPO_ROOT / "tests" / "fixtures" / "real_traces"

SAMPLES: dict[str, tuple[str, str]] = {
    "fail_retrystorm_b8f735cd.json": (
        "Retry Storm During Tool Execution",
        "Payment health check · 10 events",
    ),
    "fail_auth_1f666704.json": (
        "Authentication Failure",
        "Expired credentials block a tool call",
    ),
    "fail_timeout_12c9776c.json": (
        "Tool Timeout",
        "External dependency exceeds its deadline",
    ),
    "test_hallucination_6b5f8c42.json": (
        "Hallucinated Tool Call",
        "Agent calls a tool that does not exist",
    ),
    "fail_validation_b88e8b98.json": (
        "Invalid Tool Arguments",
        "Tool input fails contract validation",
    ),
}

DEFAULT_SAMPLE = "fail_retrystorm_b8f735cd.json"


@dataclass(frozen=True)
class DemoDiagnosis:
    """Presentation model distilled from deterministic pipeline output."""

    category: str
    severity: str
    headline: str
    detail: str
    cause: str
    fixes: tuple[str, ...]
    first_failure_id: int
    causal_event_ids: tuple[int, ...]
    terminal_event_id: int


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _error_message(event: TraceEvent) -> str:
    if event.error:
        return event.error.message
    return ""


def _first_failure_id(trace: Trace) -> int:
    for event in trace.events:
        if event.is_error():
            return event.event_id
    return trace.events[-1].event_id if trace.events else 0


def _primary_signal(preanalysis: PreAnalysisBundle):
    rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    specificity = {
        "auth_permission_failure": 8,
        "timeout_pattern": 8,
        "hallucinated_tool": 8,
        "tool_contract_mismatch": 8,
        "contract_unknown_tool": 7,
        "infinite_loop": 6,
        "retry_storm": 6,
        "error_cascade": 2,
        "empty_response": 1,
    }
    if not preanalysis.signals:
        return None
    return max(
        preanalysis.signals,
        key=lambda signal: (rank.get(signal.severity, 0), specificity.get(signal.type, 5)),
    )


def build_demo_diagnosis(trace: Trace, preanalysis: PreAnalysisBundle) -> DemoDiagnosis:
    """Turn real findings into concise, deterministic demo copy."""
    primary = _primary_signal(preanalysis)
    first_failure = _first_failure_id(trace)
    terminal = trace.events[-1].event_id if trace.events else first_failure
    repeated_calls: list[TraceEvent] = []

    tool_calls = trace.get_tool_calls()
    if tool_calls:
        signature_counts: dict[str, list[TraceEvent]] = {}
        for event in tool_calls:
            signature = event.get_tool_signature() or f"{event.name}:{event.input}"
            signature_counts.setdefault(signature, []).append(event)
        repeated_calls = max(signature_counts.values(), key=len)

    repeated_failures = [event for event in repeated_calls if event.is_error()]
    retry_like = len(repeated_failures) >= 3

    if retry_like:
        tool_name = repeated_failures[0].name or "tool"
        count = len(repeated_failures)
        causal_ids = tuple(event.event_id for event in repeated_failures)
        category = "Retry Storm"
        severity = primary.severity if primary else "high"
        headline = "Repeated tool call with unchanged arguments"
        detail = (
            f"The agent called {tool_name} {count} times with the same input. "
            "Every attempt returned the same error, but the recovery strategy never changed."
        )
        cause = (
            "The first tool failure was treated as retryable without checking whether the error "
            "or arguments had changed. With no effective retry ceiling or alternate path, the run "
            "repeated the same failed action until termination."
        )
        fixes = (
            "Limit identical retries to 2 attempts",
            "Stop when the error and arguments are unchanged",
            "Route persistent failures to a fallback or human approval",
        )
    else:
        signal_type = primary.type if primary else "execution_failure"
        category = signal_type.replace("_", " ").title()
        severity = primary.severity if primary else "high"
        headline = primary.evidence if primary else (trace.error_summary or "The run did not complete")
        detail = preanalysis.summary or "The deterministic analyzer found the first failing event."
        top_hypothesis = preanalysis.hypotheses[0] if preanalysis.hypotheses else None
        cause = (
            top_hypothesis.description
            if top_hypothesis
            else "The run reached an unrecoverable failure state at the cited event."
        )
        suggested = top_hypothesis.suggested_fixes if top_hypothesis else []
        fixes = tuple(suggested[:3]) or (
            "Validate the failing step before execution",
            "Add a bounded recovery path",
            "Escalate when the same failure repeats",
        )
        causal_ids = tuple(primary.event_ids) if primary and primary.event_ids else (first_failure,)

    return DemoDiagnosis(
        category=category,
        severity=severity,
        headline=headline,
        detail=detail,
        cause=cause,
        fixes=fixes,
        first_failure_id=first_failure,
        causal_event_ids=causal_ids,
        terminal_event_id=terminal,
    )


def _event_title(event: TraceEvent) -> str:
    if event.type == EventType.LLM_CALL:
        return "Agent planning"
    if event.type == EventType.TOOL_CALL:
        attempt = event.metadata.get("retry_attempt")
        if attempt:
            return f"Tool attempt {attempt}"
        return "Tool call"
    if event.type == EventType.ERROR:
        return "Run terminated"
    if event.type == EventType.DECISION:
        return "Agent decision"
    return "Message"


def _event_description(event: TraceEvent) -> str:
    error = _error_message(event)
    if error:
        return error
    if event.type == EventType.LLM_CALL:
        output = str(event.output or "Agent evaluated the next action.")
        return output[:120]
    if event.type == EventType.TOOL_CALL:
        return f"Called {event.name or 'tool'}"
    if event.output:
        return str(event.output)[:120]
    if event.input:
        return str(event.input)[:120]
    return event.name or event.type.value.replace("_", " ").title()


def _duration(event: TraceEvent) -> str:
    if event.latency_ms is None:
        return ""
    if event.latency_ms >= 1000:
        return f"{event.latency_ms / 1000:.1f}s"
    return f"{event.latency_ms}ms"


def _render_timeline(trace: Trace, diagnosis: DemoDiagnosis) -> None:
    rows: list[str] = []
    causal_ids = set(diagnosis.causal_event_ids)
    for index, event in enumerate(trace.events, start=1):
        is_first = event.event_id == diagnosis.first_failure_id
        is_causal = event.event_id in causal_ids
        is_terminal = event.event_id == diagnosis.terminal_event_id and event.is_error()
        state = "failure" if is_first or is_terminal else "loop" if is_causal else "normal"
        status = "First failure" if is_first else "Terminated" if is_terminal else "Retry loop" if is_causal else "Completed"
        latency = _duration(event)
        latency_html = f'<span class="timeline-duration">{_escape(latency)}</span>' if latency else ""
        # Keep every row flush-left. Markdown treats four-space-indented HTML
        # after the first row as a code block instead of rendering the timeline.
        rows.append(
            f"""<div class="timeline-row {state}">
<div class="timeline-rail"><span class="timeline-dot"></span></div>
<div class="timeline-step">{index:02d}</div>
<div class="timeline-copy">
<div class="timeline-title">{_escape(_event_title(event))}</div>
<div class="timeline-description">{_escape(_event_description(event))}</div>
</div>
<div class="timeline-meta">{latency_html}<span class="timeline-status">{status}</span></div>
</div>"""
        )

    st.markdown(
        f"""
        <section class="panel timeline-panel">
          <div class="section-kicker">Execution timeline</div>
          <div class="section-heading-row">
            <h2>What happened</h2>
            <span class="loop-key"><i></i> repeated sequence</span>
          </div>
          <div class="timeline">{''.join(rows)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_summary(trace: Trace, diagnosis: DemoDiagnosis) -> None:
    failed_step = diagnosis.first_failure_id + 1
    total = len(trace.events)
    severity = diagnosis.severity.upper()
    st.markdown(
        f"""
        <section class="failure-card">
          <div class="failure-topline">
            <span class="failure-flag"><span></span>Failure detected</span>
            <span class="severity-pill">{_escape(severity)} SEVERITY</span>
          </div>
          <div class="failure-content">
            <div>
              <div class="failure-category">{_escape(diagnosis.category)}</div>
              <h1>{_escape(diagnosis.headline)}</h1>
              <p>{_escape(diagnosis.detail)}</p>
            </div>
            <div class="failure-index">
              <span>Failed at</span>
              <strong>{failed_step}<small> / {total}</small></strong>
              <em>events</em>
            </div>
          </div>
          <div class="metric-row">
            <div><span>Category</span><strong>{_escape(diagnosis.category)}</strong></div>
            <div><span>Failed step</span><strong>Event {failed_step}</strong></div>
            <div><span>Events</span><strong>{total}</strong></div>
            <div><span>Run status</span><strong class="failed-status">{_escape(trace.status.value)}</strong></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_diagnosis_cards(trace: Trace, diagnosis: DemoDiagnosis) -> None:
    fix_items = "".join(
        f'<li><span class="check-icon">✓</span><span>{_escape(fix)}</span></li>'
        for fix in diagnosis.fixes
    )
    st.markdown(
        f"""
        <section class="panel diagnosis-panel">
          <div class="section-kicker">Root cause</div>
          <h2>Why it failed</h2>
          <p>{_escape(diagnosis.cause)}</p>
          <div class="causal-chain">
            <span>Tool unavailable</span><b>→</b><span>Identical retry</span><b>→</b><span>Run aborted</span>
          </div>
        </section>
        <section class="panel fix-panel">
          <div class="section-kicker">Prevention</div>
          <h2>Recommended fix</h2>
          <ul>{fix_items}</ul>
        </section>
        """,
        unsafe_allow_html=True,
    )

    first_step = diagnosis.first_failure_id + 1
    st.markdown(
        f"""
        <div class="final-insight"><span class="insight-mark">✦</span> Agent Autopsy reconstructed
        <strong>{len(trace.events)} events</strong> and identified the first causal failure at
        <strong>event {first_step}</strong>.</div>
        """,
        unsafe_allow_html=True,
    )


def _render_raw_event_inspector(trace: Trace) -> None:
    with st.expander("Inspect raw event data"):
        selected = st.selectbox(
            "Event",
            options=range(len(trace.events)),
            format_func=lambda index: f"Event {index + 1} · {_event_title(trace.events[index])}",
            key="demo_raw_event",
        )
        st.json(trace.events[selected].model_dump(mode="json"), expanded=False)


def _run_analysis(trace: Trace) -> tuple[PreAnalysisBundle, Any, DemoDiagnosis]:
    """Run the same deterministic analysis used by the CLI and advanced UI."""
    api.apply_embedding_defaults_for_trace(trace)
    preanalysis = api.run_preanalysis(trace)
    analysis = api.run_deterministic_analysis(trace)
    diagnosis = build_demo_diagnosis(trace, preanalysis)
    return preanalysis, analysis, diagnosis


def _analysis_animation() -> None:
    placeholder = st.empty()
    stages = (
        ("Reconstructing execution", "Normalizing events and ordering the run"),
        ("Inspecting tool calls", "Comparing arguments, errors, and retry behavior"),
        ("Detecting failure pattern", "Locating the first causal failure"),
    )
    for index, (title, detail) in enumerate(stages):
        stage_rows = []
        for stage_index, (stage_title, _) in enumerate(stages):
            state = "done" if stage_index < index else "active" if stage_index == index else "pending"
            marker = "✓" if state == "done" else str(stage_index + 1)
            stage_rows.append(
                f'<div class="analysis-stage {state}"><i>{marker}</i><span>{_escape(stage_title)}</span></div>'
            )
        placeholder.markdown(
            f"""
            <div class="analysis-progress">
              <div class="analysis-scan"></div>
              <div class="analysis-progress-label"><span>Analyzing trace</span><em>{index + 1} / {len(stages)}</em></div>
              <div class="analysis-stages">{''.join(stage_rows)}</div>
              <p>{_escape(detail)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(0.45)
    time.sleep(0.15)
    placeholder.empty()


def _load_sample(filename: str) -> Trace:
    return api.load_trace(SAMPLE_DIR / filename)


def _reset_demo_result() -> None:
    st.session_state.demo_result = None
    st.session_state.demo_error = None


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --aa-bg: #090b0d;
          --aa-panel: #101316;
          --aa-panel-2: #13171a;
          --aa-border: #262b30;
          --aa-border-soft: #1d2226;
          --aa-text: #f2f0e9;
          --aa-muted: #9299a1;
          --aa-dim: #636a72;
          --aa-amber: #e6aa4a;
          --aa-amber-soft: rgba(230, 170, 74, .11);
          --aa-red: #ef6666;
          --aa-red-soft: rgba(239, 102, 102, .09);
        }
        html, body, [data-testid="stAppViewContainer"], .stApp { background: var(--aa-bg); }
        [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"],
        [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
        [data-testid="stAppViewContainer"] > .main { margin-left: 0 !important; }
        .block-container {
          max-width: 1180px !important;
          padding: 2.1rem 2rem 4rem !important;
        }
        .stApp, button, input, textarea, select { font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        .demo-header { display:flex; align-items:center; justify-content:space-between; margin-bottom: 2.55rem; }
        .brand { display:flex; align-items:center; gap:.75rem; }
        .brand-mark { width:29px; height:29px; display:grid; place-items:center; border:1px solid #5c492b; background:#17130d; color:var(--aa-amber); font:600 14px ui-monospace, monospace; }
        .brand-name { color:var(--aa-text); font-size:15px; font-weight:650; letter-spacing:-.01em; }
        .brand-subtitle { color:var(--aa-muted); font-size:13px; margin-left:.65rem; padding-left:.8rem; border-left:1px solid var(--aa-border); }
        .trace-status { display:flex; align-items:center; gap:.48rem; color:var(--aa-muted); font:500 11px ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing:.04em; text-transform:uppercase; }
        .trace-status i { width:6px; height:6px; border-radius:50%; background:#67bd91; box-shadow:0 0 0 4px rgba(103,189,145,.08); }
        .intro { margin-bottom:1.45rem; }
        .intro .eyebrow, .section-kicker { color:var(--aa-amber); font:600 10px ui-monospace, SFMono-Regular, Consolas, monospace; letter-spacing:.13em; text-transform:uppercase; }
        .intro h1 { color:var(--aa-text); font-size:31px; line-height:1.15; font-weight:610; letter-spacing:-.035em; margin:.55rem 0 .45rem; }
        .intro p { color:var(--aa-muted); font-size:14px; margin:0; }
        .st-key-trace_selector { border:1px solid var(--aa-border) !important; background:var(--aa-panel); border-radius:8px; padding:1.05rem 1.1rem .75rem; margin-bottom:1.1rem; }
        .trace-shell-label { color:#c8c5bd; font-size:11px; font-weight:600; margin-bottom:.5rem; }
        [data-testid="stSelectbox"] label, [data-testid="stFileUploader"] label { display:none; }
        [data-testid="stSelectbox"] > div > div { background:#0c0f11; border-color:#30363c; border-radius:5px; min-height:42px; }
        [data-testid="stSelectbox"] p { color:#dedbd3; font-size:13px; }
        [data-testid="stFileUploader"] { border:0; padding:0; }
        [data-testid="stFileUploaderDropzone"] { min-height:42px; padding:.25rem .55rem; border:1px solid #30363c; border-radius:5px; background:#0c0f11; }
        [data-testid="stFileUploaderDropzone"] > div:first-child, [data-testid="stFileUploaderDropzoneInstructions"] > div:first-child { display:none; }
        [data-testid="stFileUploaderDropzoneInstructions"] span { font-size:0; }
        [data-testid="stFileUploaderDropzoneInstructions"] span:after { content:"Upload JSON"; font-size:12px; color:#b4b0a8; }
        [data-testid="stFileUploaderDropzone"] button { color:#c9c5bb; background:transparent; border:0; font-size:12px; }
        .stButton > button { min-height:42px; border-radius:5px; font-weight:650; letter-spacing:-.01em; }
        .stButton > button[kind="primary"] { background:var(--aa-amber); color:#17120a; border:1px solid var(--aa-amber); }
        .stButton > button[kind="primary"]:hover { background:#f0b65b; border-color:#f0b65b; color:#17120a; }
        .trace-file-meta { color:var(--aa-dim); font:500 10px ui-monospace, SFMono-Regular, Consolas, monospace; margin-top:-.35rem; }
        .failure-card { position:relative; overflow:hidden; border:1px solid #493031; background:linear-gradient(110deg, var(--aa-red-soft), rgba(16,19,22,.95) 45%); border-radius:8px; margin:1.5rem 0 1rem; }
        .failure-card:before { content:""; position:absolute; left:0; top:0; bottom:0; width:2px; background:var(--aa-red); }
        .failure-topline { display:flex; justify-content:space-between; align-items:center; padding:1rem 1.25rem 0; }
        .failure-flag { color:#f28a8a; font:600 10px ui-monospace, monospace; letter-spacing:.12em; text-transform:uppercase; display:flex; align-items:center; gap:.5rem; }
        .failure-flag span { width:6px; height:6px; background:var(--aa-red); border-radius:50%; box-shadow:0 0 0 4px rgba(239,102,102,.09); }
        .severity-pill { color:#bd8585; border:1px solid #543536; background:#1c1214; border-radius:999px; padding:.25rem .48rem; font:600 9px ui-monospace, monospace; letter-spacing:.06em; }
        .failure-content { display:grid; grid-template-columns:1fr 130px; gap:2rem; padding:1.55rem 1.5rem 1.45rem; }
        .failure-category { color:var(--aa-text); font:650 13px ui-monospace, monospace; margin-bottom:.45rem; }
        .failure-content h1 { color:var(--aa-text); font-size:24px; font-weight:610; letter-spacing:-.025em; margin:0 0 .6rem; }
        .failure-content p { color:#a6abb0; font-size:13px; line-height:1.65; margin:0; max-width:700px; }
        .failure-index { border-left:1px solid #38292b; display:flex; flex-direction:column; justify-content:center; padding-left:1.5rem; }
        .failure-index span, .failure-index em { color:#797f85; font:500 9px ui-monospace, monospace; letter-spacing:.1em; text-transform:uppercase; font-style:normal; }
        .failure-index strong { color:var(--aa-text); font:500 34px/1.1 ui-monospace, monospace; margin:.2rem 0; }
        .failure-index small { color:#777d83; font-size:15px; }
        .metric-row { border-top:1px solid #2d2426; display:grid; grid-template-columns:1.25fr 1fr .75fr .75fr; background:rgba(4,6,7,.23); }
        .metric-row > div { padding:.8rem 1.25rem; border-right:1px solid #2d2426; }
        .metric-row > div:last-child { border-right:0; }
        .metric-row span { display:block; color:#686f76; font:500 9px ui-monospace, monospace; text-transform:uppercase; letter-spacing:.08em; margin-bottom:.28rem; }
        .metric-row strong { display:block; color:#c9c7c0; font-size:12px; font-weight:550; }
        .metric-row .failed-status { color:#ed7b7b; text-transform:capitalize; }
        .panel { border:1px solid var(--aa-border); background:var(--aa-panel); border-radius:8px; padding:1.3rem; }
        .panel h2 { color:var(--aa-text); font-size:17px; font-weight:600; letter-spacing:-.02em; margin:.42rem 0 1rem; }
        .section-heading-row { display:flex; justify-content:space-between; align-items:center; }
        .loop-key { color:#747b82; font:500 9px ui-monospace, monospace; text-transform:uppercase; display:flex; align-items:center; gap:.4rem; }
        .loop-key i { width:13px; height:2px; background:var(--aa-amber); opacity:.7; }
        .timeline { margin-top:.25rem; }
        .timeline-row { display:grid; grid-template-columns:20px 36px 1fr auto; min-height:55px; position:relative; align-items:start; }
        .timeline-rail { position:relative; height:100%; }
        .timeline-rail:after { content:""; position:absolute; top:14px; bottom:-14px; left:6px; width:1px; background:#2a2f34; }
        .timeline-row:last-child .timeline-rail:after { display:none; }
        .timeline-dot { position:absolute; top:7px; left:3px; width:7px; height:7px; border-radius:50%; background:#5a6168; border:2px solid var(--aa-panel); z-index:1; }
        .timeline-step { color:#60676e; font:500 10px/21px ui-monospace, monospace; }
        .timeline-copy { padding-right:1rem; }
        .timeline-title { color:#c8c6bf; font-size:12px; font-weight:570; line-height:1.45; }
        .timeline-description { color:#737a81; font-size:11px; line-height:1.45; max-width:570px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .timeline-meta { display:flex; gap:.55rem; align-items:center; padding-top:.12rem; }
        .timeline-duration { color:#636a71; font:500 9px ui-monospace, monospace; }
        .timeline-status { min-width:65px; text-align:right; color:#60676d; font:500 9px ui-monospace, monospace; text-transform:uppercase; }
        .timeline-row.loop .timeline-rail:after { background:rgba(230,170,74,.5); }
        .timeline-row.loop .timeline-dot { background:var(--aa-amber); }
        .timeline-row.loop .timeline-status { color:#9d7b45; }
        .timeline-row.failure .timeline-dot { background:var(--aa-red); box-shadow:0 0 0 4px rgba(239,102,102,.09); }
        .timeline-row.failure .timeline-title { color:#f1d4d4; }
        .timeline-row.failure .timeline-description, .timeline-row.failure .timeline-status { color:#c56d6d; }
        .diagnosis-panel p { color:#9da3aa; font-size:12px; line-height:1.7; margin:0; }
        .causal-chain { display:flex; align-items:center; gap:.55rem; flex-wrap:wrap; border-top:1px solid var(--aa-border-soft); margin-top:1.1rem; padding-top:1rem; }
        .causal-chain span { color:#aaa69d; background:#0b0e10; border:1px solid #282d31; border-radius:4px; padding:.38rem .48rem; font:500 9px ui-monospace, monospace; }
        .causal-chain b { color:#5f656b; font-weight:400; }
        .fix-panel { margin-top:1rem; }
        .fix-panel ul { padding:0; margin:.25rem 0 0; list-style:none; }
        .fix-panel li { display:flex; gap:.7rem; align-items:flex-start; border-top:1px solid var(--aa-border-soft); padding:.75rem 0; color:#b8b5ae; font-size:12px; line-height:1.45; }
        .fix-panel li:first-child { border-top:0; padding-top:.2rem; }
        .check-icon { color:var(--aa-amber); font:600 11px ui-monospace, monospace; }
        .final-insight { color:#787f86; font:500 10px ui-monospace, monospace; text-align:center; border-top:1px solid #171b1e; margin:1.4rem 0 .6rem; padding-top:1.2rem; }
        .final-insight strong { color:#aaa79f; font-weight:600; }
        .insight-mark { color:var(--aa-amber); margin-right:.4rem; }
        [data-testid="stExpander"] { border:1px solid var(--aa-border) !important; border-radius:6px !important; background:#0d1012; margin-top:.9rem; }
        [data-testid="stExpander"] summary { color:#898f95; font-size:11px; }
        .analysis-progress { position:relative; overflow:hidden; border:1px solid #3b3223; background:#10110f; border-radius:8px; padding:1.2rem 1.35rem; margin:1.5rem 0; }
        .analysis-scan { position:absolute; inset:0; background:linear-gradient(90deg, transparent, rgba(230,170,74,.04), transparent); transform:translateX(-100%); animation:scan 1.2s infinite; }
        @keyframes scan { to { transform:translateX(100%); } }
        .analysis-progress-label { position:relative; display:flex; justify-content:space-between; color:#d7d3ca; font-size:12px; font-weight:600; margin-bottom:1rem; }
        .analysis-progress-label em { color:#7e725e; font:500 10px ui-monospace, monospace; font-style:normal; }
        .analysis-stages { position:relative; display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; }
        .analysis-stage { display:flex; gap:.5rem; align-items:center; color:#5f666c; font:500 10px ui-monospace, monospace; }
        .analysis-stage i { width:18px; height:18px; display:grid; place-items:center; border:1px solid #343a3f; border-radius:50%; font-style:normal; font-size:9px; }
        .analysis-stage.active { color:#d3ae70; }
        .analysis-stage.active i { border-color:var(--aa-amber); color:var(--aa-amber); box-shadow:0 0 0 4px var(--aa-amber-soft); }
        .analysis-stage.done { color:#7e858b; }
        .analysis-stage.done i { border-color:#58715e; color:#70b485; }
        .analysis-progress p { position:relative; color:#686f75; font-size:10px; margin:1rem 0 0; }
        [data-testid="stAlert"] { background:#171112; border-color:#4a2b2d; color:#e7aaaa; }
        @media (max-width: 800px) {
          .block-container { padding:1.25rem 1rem 3rem !important; }
          .brand-subtitle { display:none; }
          .failure-content { grid-template-columns:1fr; }
          .failure-index { border-left:0; border-top:1px solid #38292b; padding:1rem 0 0; }
          .metric-row { grid-template-columns:1fr 1fr; }
          .timeline-row { grid-template-columns:20px 30px 1fr; }
          .timeline-meta { grid-column:3; margin-top:.25rem; }
          .analysis-stages { grid-template-columns:1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_demo_page() -> None:
    """Render the focused demo at ``/demo``."""
    st.set_page_config(
        page_title="Analyze a failed run — Agent Autopsy",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_styles()

    if "demo_result" not in st.session_state:
        st.session_state.demo_result = None
    if "demo_error" not in st.session_state:
        st.session_state.demo_error = None

    active_trace = st.session_state.demo_result[0] if st.session_state.demo_result else None
    status_text = f"Trace loaded · {len(active_trace.events)} events" if active_trace else "Ready to analyze"
    st.markdown(
        f"""
        <header class="demo-header">
          <div class="brand"><span class="brand-mark">AA</span><span class="brand-name">Agent Autopsy</span>
          <span class="brand-subtitle">Find where an AI agent failed — and why.</span></div>
          <div class="trace-status"><i></i>{_escape(status_text)}</div>
        </header>
        <section class="intro"><div class="eyebrow">Run diagnosis</div><h1>Find the failure. Fix the agent.</h1>
        <p>Load a failed execution trace and reconstruct the exact point where the run went wrong.</p></section>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True, key="trace_selector"):
        st.markdown('<div class="trace-shell-label">Agent run</div>', unsafe_allow_html=True)
        selection_col, upload_col, action_col = st.columns([2.55, 1.05, 1.05], gap="small")
        with selection_col:
            selected_filename = st.selectbox(
                "Agent run",
                options=list(SAMPLES),
                index=list(SAMPLES).index(DEFAULT_SAMPLE),
                format_func=lambda filename: SAMPLES[filename][0],
                key="demo_sample",
                on_change=_reset_demo_result,
            )
            st.markdown(
                f'<div class="trace-file-meta">{_escape(selected_filename)} · {_escape(SAMPLES[selected_filename][1])}</div>',
                unsafe_allow_html=True,
            )
        with upload_col:
            uploaded = st.file_uploader(
                "Upload trace",
                type=["json"],
                key="demo_upload",
                on_change=_reset_demo_result,
            )
        with action_col:
            analyze_clicked = st.button("Analyze Run", type="primary", use_container_width=True)

    if analyze_clicked:
        try:
            if uploaded is not None:
                data = json.load(uploaded)
                trace = api.load_trace_from_dict(data)
            else:
                trace = _load_sample(selected_filename)
            _analysis_animation()
            preanalysis, analysis, diagnosis = _run_analysis(trace)
            st.session_state.demo_result = (trace, preanalysis, analysis, diagnosis)
            st.session_state.demo_error = None
            st.rerun()
        except (json.JSONDecodeError, ParseError, SchemaValidationError, PluginError, ValueError) as exc:
            st.session_state.demo_error = str(exc)
            st.session_state.demo_result = None

    if st.session_state.demo_error:
        st.error(f"This trace could not be analyzed: {st.session_state.demo_error}")

    if st.session_state.demo_result:
        trace, preanalysis, analysis, diagnosis = st.session_state.demo_result
        _render_summary(trace, diagnosis)
        timeline_col, diagnosis_col = st.columns([1.55, 1], gap="medium")
        with timeline_col:
            _render_timeline(trace, diagnosis)
        with diagnosis_col:
            _render_diagnosis_cards(trace, diagnosis)
        _render_raw_event_inspector(trace)
