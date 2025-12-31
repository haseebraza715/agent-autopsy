# 🔍 Agent Autopsy

> **Intelligent trace analysis for AI agents** — Automatically detect failures, loops, and issues in your agent execution traces.

![Architecture](diagrams/architecture.png)

---

## ✨ Features

- 🔄 **Multi-Format Support** — Parse traces from LangGraph, LangChain, OpenTelemetry, and generic JSON
- 🎯 **Pattern Detection** — Automatically detect loops, error cascades, hallucinated tools, and more
- ✅ **Contract Validation** — Validate tool usage against defined schemas
- 🤖 **LLM Analysis** — AI-powered root cause analysis with event citations
- 📊 **Report Generation** — Structured markdown reports with actionable recommendations
- 🛠️ **Artifact Generation** — Code patches for retry policies, loop guards, and fixes

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

# Analyze a trace
python -m src.cli analyze trace.json
```

---

## 📚 Documentation

- **[Architecture](docs/architecture.md)** — System overview and components
- **[Quick Start](docs/quickstart.md)** — Installation and basic usage
- **[Ingestion](docs/ingestion.md)** — Trace format support and parsing
- **[Analysis](docs/analysis.md)** — Pattern detection and LLM analysis
- **[Patterns](docs/patterns.md)** — Detected failure patterns
- **[Output](docs/output.md)** — Report and artifact generation

---

## 💻 CLI Commands

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

---

## 🎯 Detected Patterns

| Pattern | Severity | Description |
|---------|----------|-------------|
| 🔁 Infinite Loop | **Critical** | Same tool+input repeated 3+ times |
| ⚡ Retry Storm | **High** | Same tool called repeatedly with varying inputs |
| 📊 Context Overflow | **Critical** | Token count exceeding model limit |
| 🎭 Hallucinated Tool | **High** | Tool called not in available tools list |
| ⚠️ Empty Response | **Medium** | LLM or tool returning empty output |
| 🔗 Error Cascade | **High** | Sequential errors propagating through events |

---

## 📁 Project Structure

```
agent-autopsy/
├── src/
│   ├── main.py              # Entry point
│   ├── cli.py               # CLI interface
│   ├── ingestion/          # Trace parsing
│   ├── schema/              # Pydantic models
│   ├── preanalysis/         # Pattern detection
│   ├── analysis/            # LLM analysis
│   └── output/              # Report generation
├── docs/                     # Documentation
├── diagrams/                 # Architecture diagrams
├── tests/                    # Test files
└── requirements.txt
```

---

## ⚙️ Configuration

Environment variables (`.env`):

```env
OPENROUTER_API_KEY=your_key_here
DEFAULT_MODEL=meta-llama/llama-3.1-8b-instruct
FALLBACK_MODEL=meta-llama/llama-3.1-8b-instruct:free
LOG_LEVEL=INFO
```

---

## 🧪 Development

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

---

## 📄 License

MIT
