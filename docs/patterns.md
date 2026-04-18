# Deterministic pattern detectors

All detectors live in `src/preanalysis/patterns.py` (`PatternDetector.detect_all`) and run before any LLM step.

| Pattern type | Enum value | Summary |
|--------------|------------|---------|
| Infinite loop | `infinite_loop` | Same tool+input signature repeated consecutively |
| Retry storm | `retry_storm` | Same tool many times inside a short window |
| Redundant tool call | `redundant_tool_call` | Duplicate tool calls with similar inputs |
| Empty response | `empty_response` | Blank or useless LLM/tool outputs |
| Error cascade | `error_cascade` | Chained failures across events |
| Hallucinated tool | `hallucinated_tool` | Calls to tools not in the allowed set |
| Auth / permission | `auth_permission_failure` | Auth-related error text or 401/403 signals |
| Timeout pattern | `timeout_pattern` | Timeout-related errors or very slow calls |
| Goal drift | `goal_drift` | Similarity to the task goal drops over the run (embeddings or lexical fallback) |
| Stale context | `stale_context` | Old context reused while the task moved on |
| Token waste | `token_waste` | High token use with little progress |
| Inter-agent failure | `inter_agent_failure` | Handoff / multi-agent issues |
| Context overflow | `context_overflow` | Token totals vs model or trace limits |
| Tool contract mismatch | `tool_contract_mismatch` | Outputs that violate declared contracts |

Plugin detectors registered on the plugin manager are invoked after the built-in list; failures are logged and skipped.
