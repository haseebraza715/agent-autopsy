# Analysis Pipeline

Agent Autopsy uses deterministic pattern detection combined with LLM reasoning.

## Analysis Flow

The analysis pipeline processes traces through multiple stages. See [System Flow Diagram](../diagrams/system_flow.mmd) for complete flow.

### Stage 1: Pre-Analysis

**Pattern Detection**
- Detects infinite loops, retry storms, error cascades
- Identifies hallucinated tools and empty responses
- Checks for context overflow

**Contract Validation**
- Validates tool schemas and input/output types
- Checks for contract violations

**Root Cause Builder**
- Generates hypotheses based on detected patterns
- Assigns confidence scores to hypotheses
- Links hypotheses to supporting events

### Stage 2: Analysis Mode Decision

The system chooses between two analysis modes:

**Deterministic Analysis** (--no-llm flag or no API key)
- Uses only pattern detection results
- Generates basic report from pre-analysis
- Fast, no external API calls

**LLM Analysis** (default with API key)
- Uses LangGraph ReAct agent
- Queries trace data using analysis tools
- Performs deep root cause analysis
- Generates detailed reports with event citations

### Stage 3: LLM Analysis (if enabled)

**Analysis Tools**
- `get_event`: Retrieve specific event by ID
- `find_errors`: Find all error events
- `get_trace_summary`: Get high-level trace summary
- `get_preanalysis_bundle`: Get pre-analysis results

**ReAct Pattern**
- Agent reasons about trace events
- Uses tools to gather evidence
- Builds root cause chain step-by-step
- Cites specific events in analysis

**OpenRouter Integration**
- Sends prompts to OpenRouter API
- Receives LLM responses
- Handles API errors gracefully

### Stage 4: Report Generation

**Report Components**
- Summary with status and confidence
- Timeline of key events
- Root cause chain with event citations
- Fix recommendations categorized by type
- Evidence with cited events

**Artifact Generation**
- Code patches for retry policies
- Loop guard implementations
- Error handling improvements
- Configuration updates

## Pattern Detection Details

See [Patterns](patterns.md) for detailed information on detected patterns.

## LLM Analysis Details

The LLM analysis uses a ReAct (Reasoning + Acting) agent pattern:

1. **Initial Prompt**: Provides trace summary and pre-analysis results
2. **Tool Usage**: Agent queries trace data using analysis tools
3. **Reasoning**: Agent analyzes evidence and builds causal chain
4. **Report Generation**: Agent generates structured report with citations
5. **Validation**: System validates report completeness

**Key Features**:
- Event citations for all claims
- Step-by-step root cause analysis
- Categorized fix recommendations
- Confidence scoring
