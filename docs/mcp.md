# MCP Server

Agent Autopsy includes an MCP server so MCP-compatible clients can analyze traces directly from chat/IDE workflows.

## Run

Stdio transport (local client integration):

```bash
python -m src.mcp --transport stdio
```

HTTP transport (Streamable HTTP):

```bash
python -m src.mcp --transport streamable-http --mount-path /mcp
```

SSE transport:

```bash
python -m src.mcp --transport sse --mount-path /mcp
```

## Tools

- `analyze_trace`
- `detect_patterns`
- `validate_trace`
- `get_trace_summary`
- `compare_traces`
- `capture_trace`
- `list_traces`
- `get_event_details`
- `suggest_fixes`
- `health_check`

All tools accept trace input as a file path (`trace_file`) or inline JSON (`trace_json`) where relevant.

## Resources

- `agent-autopsy://traces/recent`
- `agent-autopsy://reports/archive`
- `agent-autopsy://patterns/catalog`
- `agent-autopsy://config/current`

## Prompts

- `debug_my_agent`
- `quick_health_check`
- `compare_runs`
- `explain_failure`
