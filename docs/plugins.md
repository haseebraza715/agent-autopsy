# Plugin System

Agent Autopsy supports extension plugins for advanced customization without modifying core code.

## Plugin Types

- `ParserPlugin`: add support for custom trace formats
- `PatternDetectorPlugin`: add custom deterministic detectors
- `ReportTemplatePlugin`: add custom report output formats
- `FixGeneratorPlugin`: add framework-specific fix suggestion generation
- `VisualizationPlugin`: add custom visualization payloads

Interfaces are defined in [`src/plugins/base.py`](../src/plugins/base.py).

## Registration Options

### 1) Local plugin directory (quickest)

Set an environment variable pointing to a directory of `.py` files:

```bash
export AGENT_AUTOPSY_PLUGINS_DIR=/absolute/path/to/plugins
```

Each plugin module must expose:

```python
def register(plugin_manager):
    ...
```

### 2) Python entry points

Use entry point groups:

- `agent_autopsy.parsers`
- `agent_autopsy.pattern_detectors`
- `agent_autopsy.report_templates`
- `agent_autopsy.fix_generators`
- `agent_autopsy.visualizations`

## Minimal Parser Plugin Example

```python
from datetime import datetime
from agent_autopsy.plugins import ParserPlugin
from agent_autopsy.schema import Trace, TraceStatus, EnvironmentInfo

class MyParser(ParserPlugin):
    name = "my_format"

    def can_parse(self, data):
        return data.get("format") == "my_format"

    def parse(self, data):
        return Trace(
            run_id=data.get("run_id", "my-run"),
            timestamp_start=datetime(2026, 1, 1, 0, 0, 0),
            status=TraceStatus.SUCCESS,
            env=EnvironmentInfo(agent_framework="custom"),
            events=[],
        )


def register(plugin_manager):
    plugin_manager.register_parser(MyParser())
```

## Introspection

- MCP resource: `agent-autopsy://plugins/active`
- Service helper: [`src/mcp/service.py`](../src/mcp/service.py) (`plugin_resource()`)

Both expose loaded plugin names and plugin-load errors.
