# Autopsy Agent Scripts

Modular scripts for trace generation, analysis, and verification.

## Structure

```
scripts/
├── modules/                    # Reusable modules
│   ├── trace_generator.py      # Generate traces
│   ├── trace_analyzer.py       # Analyze traces
│   ├── trace_verifier.py       # Verify traces
│   └── report_generator.py     # Generate summary reports
├── eval_detectors.py           # Corpus precision/recall (CI)
├── benchmark_no_llm.py         # Cold-path timing (no LLM)
├── record_demo.sh              # Instructions for asciinema README GIF
├── render_demo_gif.py          # HD README GIF: deterministic CLI + LLM (live or sample)
├── demo_gif_llm_sample.txt     # Representative LLM excerpt when API unavailable
├── generate_traces.py          # Main script for trace generation
├── analyze_traces.py           # Main script for trace analysis
└── verify_traces.py            # Main script for trace verification
```

### Detector eval & benchmarks

```bash
python scripts/eval_detectors.py
python scripts/benchmark_no_llm.py examples/traces/loop_failure.json --repeat 5
./scripts/record_demo.sh
python scripts/render_demo_gif.py              # live LLM if OPENROUTER_API_KEY set
python scripts/render_demo_gif.py --force-sample-llm   # CI / no key
```

## Usage

### Generate Traces

```bash
# Generate at least 20 traces (default)
python scripts/generate_traces.py

# Generate 50 traces
python scripts/generate_traces.py --min-runs 50

# Stop after finding a failure
python scripts/generate_traces.py --stop-on-failure

# Custom traces directory
python scripts/generate_traces.py --traces-dir ./my_traces
```

### Verify Traces

```bash
# Verify all traces
python scripts/verify_traces.py

# Custom traces directory
python scripts/verify_traces.py --traces-dir ./my_traces
```

### Analyze Traces

```bash
# Analyze all traces and generate reports
python scripts/analyze_traces.py

# Custom directories
python scripts/analyze_traces.py --traces-dir ./traces --reports-dir ./reports
```

## Workflow

1. **Generate traces**: Run the analysis agent multiple times to capture execution traces
2. **Verify traces**: Check which traces contain failures
3. **Analyze traces**: Run full autopsy analysis and generate comprehensive reports

This workflow is useful for:
- Testing the analysis agent itself
- Generating test data for development
- Batch analysis of multiple traces
- Pattern detection across multiple runs

## Modules

### TraceGenerator

Generates traces by running the analysis agent on sample traces.

```python
from scripts.modules.trace_generator import TraceGenerator

generator = TraceGenerator()
result = generator.generate_traces(
    sample_traces=["tests/sample_traces/successful_run.json"],
    min_runs=20,
    stop_on_failure=True
)
```

### TraceAnalyzer

Analyzes traces and generates individual reports.

```python
from scripts.modules.trace_analyzer import TraceAnalyzer

analyzer = TraceAnalyzer()
results = analyzer.analyze_all_traces(traces_dir=Path("./traces"))
```

### TraceVerifier

Verifies traces and checks for failures.

```python
from scripts.modules.trace_verifier import TraceVerifier

verifier = TraceVerifier()
result = verifier.verify_all()
```

### SummaryReportGenerator

Generates comprehensive summary reports.

```python
from scripts.modules.report_generator import SummaryReportGenerator

generator = SummaryReportGenerator()
summary = generator.generate_summary(all_results)
```

