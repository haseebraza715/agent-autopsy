"""
Core analysis agent using LangGraph with ReAct pattern.

This agent analyzes traces using a combination of:
- Pre-analysis results (deterministic patterns, contracts)
- LLM reasoning with tool calling
- Structured report generation
"""

import json
from typing import Any, Annotated, TypedDict
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from src.schema import Trace
from src.ingestion import TraceNormalizer
from src.preanalysis import RootCauseBuilder
from src.tracing import TraceSaver, start_trace, end_trace, get_trace_config
from .tools import AnalysisToolkit, TOOL_DEFINITIONS
from .prompts import SYSTEM_PROMPT, get_analysis_prompt, get_final_report_prompt
from src.utils.config import get_config


class AgentState(TypedDict):
    """State for the analysis agent."""
    messages: Annotated[list, add_messages]
    trace_summary: dict
    preanalysis: dict
    analysis_complete: bool
    final_report: str


@dataclass
class AnalysisResult:
    """Result of the analysis."""
    report: str
    trace_summary: dict
    preanalysis: dict
    success: bool
    error: str | None = None


class AnalysisAgent:
    """
    LLM-powered agent for trace analysis.

    Uses ReAct pattern with guarded tool calling.
    """

    def __init__(
        self,
        trace: Trace,
        model: str | None = None,
        verbose: bool = False,
    ):
        self.trace = trace
        self.config = get_config()
        self.model_name = model or self.config.default_model
        self.verbose = verbose

        # Initialize toolkit
        self.toolkit = AnalysisToolkit(trace)

        # Initialize LLM
        self.llm = self._create_llm()

        # Build the agent graph
        self.graph = self._build_graph()

    def _create_llm(self) -> ChatOpenAI:
        """Create the LLM client."""
        return ChatOpenAI(
            model=self.model_name,
            openai_api_key=self.config.openrouter_api_key,
            openai_api_base=self.config.openrouter_base_url,
            max_tokens=self.config.max_tokens,
            temperature=0.1,  # Low temperature for analysis
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("analyze", self._analyze_node)
        graph.add_node("execute_tools", self._execute_tools_node)
        graph.add_node("generate_report", self._generate_report_node)

        # Set entry point
        graph.set_entry_point("analyze")

        # Add edges
        graph.add_conditional_edges(
            "analyze",
            self._should_continue,
            {
                "tools": "execute_tools",
                "report": "generate_report",
                "end": END,
            },
        )
        graph.add_edge("execute_tools", "analyze")
        graph.add_edge("generate_report", END)

        return graph.compile()

    def _analyze_node(self, state: AgentState) -> AgentState:
        """Main analysis node - calls LLM to reason about trace."""
        messages = state["messages"]

        # Bind tools to LLM
        llm_with_tools = self.llm.bind_tools(
            TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        try:
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}
        except Exception as e:
            # Handle LLM errors gracefully
            error_msg = f"LLM error: {str(e)}"
            if self.verbose:
                print(f"Warning: {error_msg}")
            return {
                "messages": [AIMessage(content=f"Analysis error: {error_msg}")],
                "analysis_complete": True,
            }

    def _execute_tools_node(self, state: AgentState) -> AgentState:
        """Execute tools requested by the LLM."""
        last_message = state["messages"][-1]

        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return state

        tool_messages = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if self.verbose:
                print(f"Executing tool: {tool_name}({tool_args})")

            # Execute the tool
            result = self._execute_tool(tool_name, tool_args)

            tool_messages.append(
                ToolMessage(
                    content=json.dumps(result, default=str),
                    tool_call_id=tool_call["id"],
                )
            )

        return {"messages": tool_messages}

    def _execute_tool(self, tool_name: str, args: dict) -> Any:
        """Execute a single tool and return the result."""
        tool_map = {
            "get_trace_summary": lambda: self.toolkit.get_trace_summary(),
            "get_event": lambda: self.toolkit.get_event(args.get("event_id", 0)),
            "get_events_range": lambda: self.toolkit.get_events_range(
                args.get("start_id", 0), args.get("end_id", 0)
            ),
            "find_errors": lambda: self.toolkit.find_errors(),
            "find_loops": lambda: self.toolkit.find_loops(),
            "find_tool_calls": lambda: self.toolkit.find_tool_calls(args.get("tool_name")),
            "compare_events": lambda: self.toolkit.compare_events(
                args.get("event_id_1", 0), args.get("event_id_2", 0)
            ),
            "get_context_at_event": lambda: self.toolkit.get_context_at_event(
                args.get("event_id", 0), args.get("window", 3)
            ),
            "get_contract_violations": lambda: self.toolkit.get_contract_violations(),
            "get_preanalysis_bundle": lambda: self.toolkit.get_preanalysis_bundle(),
            "get_all_patterns": lambda: self.toolkit.get_all_patterns(),
        }

        if tool_name not in tool_map:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return tool_map[tool_name]()
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    def _generate_report_node(self, state: AgentState) -> AgentState:
        """Generate the final structured report."""
        messages = state["messages"]

        # Add prompt for final report
        messages.append(HumanMessage(content=get_final_report_prompt()))

        try:
            response = self.llm.invoke(messages)
            return {
                "messages": [response],
                "final_report": response.content,
                "analysis_complete": True,
            }
        except Exception as e:
            return {
                "final_report": f"Report generation failed: {str(e)}",
                "analysis_complete": True,
            }

    def _should_continue(self, state: AgentState) -> str:
        """Determine next step based on state."""
        if state.get("analysis_complete"):
            return "end"

        last_message = state["messages"][-1]

        # Check if LLM wants to use tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        # Check if we have enough analysis to generate report
        # (This is a simplified heuristic - could be more sophisticated)
        message_count = len(state["messages"])
        if message_count > 10:  # After several rounds, generate report
            return "report"

        # Check if the message indicates analysis is complete
        content = last_message.content.lower() if hasattr(last_message, "content") else ""
        if any(phrase in content for phrase in [
            "root cause",
            "recommendation",
            "fix",
            "in conclusion",
            "summary",
        ]):
            return "report"

        return "report"  # Default to generating report

    def run(self, trace_handler: TraceSaver | None = None) -> AnalysisResult:
        """Run the analysis and return results.

        Args:
            trace_handler: Optional TraceSaver callback for capturing execution trace.
        """
        # Prepare initial state
        trace_summary = TraceNormalizer.get_summary(self.trace)
        preanalysis = RootCauseBuilder(self.trace).build()

        initial_prompt = get_analysis_prompt(trace_summary, preanalysis.summary)

        initial_state: AgentState = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=initial_prompt),
            ],
            "trace_summary": trace_summary,
            "preanalysis": preanalysis.to_dict(),
            "analysis_complete": False,
            "final_report": "",
        }

        # Build config with callbacks if trace handler provided
        config = {}
        if trace_handler:
            config["callbacks"] = [trace_handler]
            config["run_name"] = "agent_autopsy_analysis"

        try:
            # Run the graph with optional tracing
            final_state = self.graph.invoke(initial_state, config=config if config else None)

            return AnalysisResult(
                report=final_state.get("final_report", ""),
                trace_summary=trace_summary,
                preanalysis=preanalysis.to_dict(),
                success=True,
            )
        except Exception as e:
            # Record error in trace if handler provided
            if trace_handler:
                trace_handler.add_error_event(e, context="agent_run")
            return AnalysisResult(
                report="",
                trace_summary=trace_summary,
                preanalysis=preanalysis.to_dict(),
                success=False,
                error=str(e),
            )


def run_analysis(
    trace: Trace,
    model: str | None = None,
    verbose: bool = False,
    enable_tracing: bool | None = None,
) -> AnalysisResult:
    """
    Convenience function to run analysis on a trace.

    Args:
        trace: The trace to analyze
        model: Optional model override
        verbose: Whether to print debug output
        enable_tracing: Override for trace capture (None = use env config)

    Returns:
        AnalysisResult with report and metadata
    """
    agent = AnalysisAgent(trace, model=model, verbose=verbose)

    # Determine if tracing should be enabled
    trace_config = get_trace_config()
    should_trace = enable_tracing if enable_tracing is not None else trace_config.enabled

    trace_handler = None
    if should_trace:
        trace_handler, run_id = start_trace()

    try:
        result = agent.run(trace_handler=trace_handler)
        return result
    except Exception as e:
        # Ensure error is captured
        if trace_handler:
            trace_handler.add_error_event(e, context="run_analysis")
        raise
    finally:
        # Always save trace, even on exception
        if trace_handler:
            end_trace(trace_handler)


def run_analysis_without_llm(trace: Trace) -> AnalysisResult:
    """
    Run deterministic analysis without LLM.

    Useful when API key is not available or for quick analysis.
    """
    trace_summary = TraceNormalizer.get_summary(trace)
    preanalysis = RootCauseBuilder(trace).build()

    # Generate a basic report from pre-analysis
    report_lines = [
        f"# Autopsy Report: Run {trace.run_id}",
        "",
        "## Summary",
        f"- Status: {trace.status.value}",
        f"- Total Events: {len(trace.events)}",
        f"- Errors: {trace.stats.num_errors}",
        "",
        "## Pre-Analysis Results",
        "",
        preanalysis.summary,
        "",
        "### Signals Detected",
    ]

    for signal in preanalysis.signals:
        report_lines.append(f"- **{signal.type}** ({signal.severity}): {signal.evidence}")
        report_lines.append(f"  - Events: {signal.event_ids}")

    report_lines.extend([
        "",
        "### Hypotheses",
    ])

    for hyp in preanalysis.hypotheses:
        report_lines.append(f"- **{hyp.description}** (confidence: {hyp.confidence:.0%})")
        report_lines.append(f"  - Category: {hyp.category}")
        report_lines.append(f"  - Supporting events: {hyp.supporting_events}")
        if hyp.suggested_fixes:
            report_lines.append("  - Suggested fixes:")
            for fix in hyp.suggested_fixes:
                report_lines.append(f"    - {fix}")

    report_lines.extend([
        "",
        "---",
        "*Note: This report was generated without LLM analysis (deterministic pre-analysis only).*",
    ])

    return AnalysisResult(
        report="\n".join(report_lines),
        trace_summary=trace_summary,
        preanalysis=preanalysis.to_dict(),
        success=True,
    )
