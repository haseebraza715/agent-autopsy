<h1 align="center">
  <pre>
    ╔═══════════════════════════════════╗
    ║                                   ║
    ║      🔍 AGENT AUTOPSY            ║
    ║                                   ║
    ║   Trace Analysis Engine           ║
    ║                                   ║
    ╚═══════════════════════════════════╝
  </pre>
</h1>

<p align="center">
  <a href="https://github.com/haseebraza715/agent-autopsy/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" />
  </a>
  <a href="https://github.com/haseebraza715/agent-autopsy">
    <img src="https://img.shields.io/github/stars/haseebraza715/agent-autopsy?style=social" alt="GitHub stars" />
  </a>
</p>

<p align="center">
  <b>Intelligent trace analysis for AI agents</b></br>
  <sub>Automatically detect failures, loops, and issues in your agent execution traces</sub><br>
</p>

<br />

- **Multi-Format Support**: Parse traces from LangGraph, LangChain, OpenTelemetry, and generic JSON formats
- **Pattern Detection**: Automatically detect loops, error cascades, hallucinated tools, and more
- **Contract Validation**: Validate tool usage against defined schemas
- **LLM Analysis**: AI-powered root cause analysis with event citations
- **Report Generation**: Structured markdown reports with actionable fix recommendations
- **Artifact Generation**: Generate code patches for retry policies, loop guards, and more
- **Light-weight**: Minimal dependencies, fast analysis
- **Highly Customizable**: Powerful API for custom analysis workflows
- **TypeScript Ready**: Full type support for trace schemas
- **MIT Licensed**: Free for personal and commercial use

<br />

## Documentation

For detailed documentation and guides, visit the [docs](docs/) folder:

- [Architecture](docs/architecture.md) — System overview and components
- [Quick Start](docs/quickstart.md) — Installation and basic usage
- [Ingestion](docs/ingestion.md) — Trace format support and parsing
- [Analysis](docs/analysis.md) — Pattern detection and LLM analysis
- [Patterns](docs/patterns.md) — Detected failure patterns
- [Output](docs/output.md) — Report and artifact generation

<br />

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

# Analyze a trace
python -m src.cli analyze trace.json
```

<br />

## So, yet another trace analyzer?

**No**, it's more than a trace analyzer. **Analysis is just one of the many use-cases**. Agent Autopsy can be used wherever you need to understand agent behavior; some common usecases could be: debugging failed agent runs, identifying infinite loops and retry storms, validating tool contracts, generating fix recommendations, creating code patches for common issues, analyzing agent performance, and of-course comprehensive failure analysis etc.

Agent Autopsy is written in Python, has minimal dependencies and is highly customizable. It has several options allowing you to change how it analyzes traces and also **provides you the hooks** to customize the analysis pipeline, pattern detection, and report generation.

> Also, comparing the capabilities of Agent Autopsy with other tools, it's the most comprehensive, providing **both deterministic pattern detection and LLM-powered root cause analysis** while others focus on just one approach.

<br>

## Detected Patterns

| Pattern | Severity | Description |
|---------|----------|-------------|
| Infinite Loop | **Critical** | Same tool+input repeated 3+ times |
| Retry Storm | **High** | Same tool called repeatedly with varying inputs |
| Context Overflow | **Critical** | Token count exceeding model limit |
| Hallucinated Tool | **High** | Tool called not in available tools list |
| Empty Response | **Medium** | LLM or tool returning empty output |
| Error Cascade | **High** | Sequential errors propagating through events |

<br />

## CLI Commands

### `analyze`
Full analysis with pattern detection and LLM reasoning.

```bash
python -m src.cli analyze trace.json [OPTIONS]

Options:
  -o, --output PATH      Output file for report
  --artifacts PATH       Output directory for patches
  --model TEXT          Model override
  -v, --verbose         Show detailed output
  --no-llm              Skip LLM analysis
  -f, --format TEXT     Output format: markdown or json
```

### Other Commands

- `summary` — Quick trace summary without full analysis
- `validate` — Validate trace file format
- `config` — Show current configuration

<br />

## Configuration

Environment variables (`.env`):

```env
OPENROUTER_API_KEY=your_key_here
DEFAULT_MODEL=meta-llama/llama-3.1-8b-instruct
FALLBACK_MODEL=meta-llama/llama-3.1-8b-instruct:free
LOG_LEVEL=INFO
```

<br />

## Architecture

![Architecture](diagrams/architecture.png)

<br />

## Contributions

Feel free to submit pull requests, create issues or spread the word.

<br />

## License

MIT &copy; [Haseeb Raza](https://github.com/haseebraza715)
