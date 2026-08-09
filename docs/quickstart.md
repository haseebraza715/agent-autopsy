# Quick Start Guide

Get started with TraceAutopsy in minutes.

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install (pick extras you need; full includes CLI+GUI+LLM+MCP+tests+embeddings)
pip install -e ".[full]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys and PROVIDER
```

## Basic Usage

The basic workflow involves analyzing a trace file to identify failures and issues.

```bash
# Analyze a trace file
python -m agent_autopsy.cli analyze trace.json

# Save report to file
python -m agent_autopsy.cli analyze trace.json -o report.md
```

## Commands

### Analysis Commands

```bash
# Full analysis with LLM
python -m agent_autopsy.cli analyze trace.json -o report.md

# Generate code patches
python -m agent_autopsy.cli analyze trace.json --artifacts ./patches/

# Deterministic analysis only (no LLM)
python -m agent_autopsy.cli analyze trace.json --no-llm

# Quick summary without full analysis
python -m agent_autopsy.cli summary trace.json

# Validate trace format
python -m agent_autopsy.cli validate trace.json

# Analyze captured trace (TraceSaver format)
python -m agent_autopsy.cli autopsy-run traces/trace.json
```

### Trace Generation & Batch Analysis

```bash
# Generate traces by running analysis agent
python scripts/generate_traces.py --min-runs 20

# Verify all traces for failures
python scripts/verify_traces.py

# Analyze all traces and generate summary report
python scripts/analyze_traces.py --traces-dir ./traces --reports-dir ./reports
```

### Example Traces

Example files:
- [`examples/traces/successful_run.json`](../examples/traces/successful_run.json)
- [`examples/traces/loop_failure.json`](../examples/traces/loop_failure.json)

```bash
python -m agent_autopsy.cli summary examples/traces/successful_run.json
python -m agent_autopsy.cli analyze examples/traces/loop_failure.json --no-llm -o /tmp/loop_report.md
```

### MCP Server

```bash
# Run MCP server over stdio (for local MCP clients)
python -m agent_autopsy.mcp --transport stdio

# Run MCP server over streamable HTTP
python -m agent_autopsy.mcp --transport streamable-http --mount-path /mcp
```

## Example Workflows

### Single Trace Analysis

1. **Collect trace**: Export trace from your agent framework
2. **Analyze**: Run `analyze` command on trace file
3. **Review report**: Check root cause analysis and recommendations
4. **Apply fixes**: Use generated artifacts to fix issues

### Batch Trace Analysis

1. **Generate traces**: Run [`scripts/generate_traces.py`](../scripts/generate_traces.py) to create test traces
2. **Verify traces**: Run [`scripts/verify_traces.py`](../scripts/verify_traces.py) to check for failures
3. **Analyze all**: Run [`scripts/analyze_traces.py`](../scripts/analyze_traces.py) to generate comprehensive reports
4. **Review summary**: Check `reports/analysis_summary.md` for patterns across all traces

## Next Steps

- Read [Architecture](architecture.md) for system overview
- See [Patterns](patterns.md) for detected failure types
- Check [Analysis](analysis.md) for analysis pipeline details
- See [MCP Server](mcp.md) for MCP tools/resources/prompts
- See [Extension Guide](extensions.md) for extending parsers/detectors/reports
- See [Examples](../examples/README.md) for curated walkthrough traces
- Review [Scripts](../scripts/README.md) for trace generation tools
