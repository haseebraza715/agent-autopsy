# Contributing to Agent Autopsy

Thanks for your interest in contributing.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional modern workflow:

```bash
pip install -e ".[dev]"
```

## Local Checks

Run tests before opening a PR:

```bash
.venv/bin/pytest -q
```

Smoke-check core entrypoints:

```bash
.venv/bin/python -m src.cli --help
.venv/bin/python -m src.mcp --help
```

## Branching and Commits

- Work on focused, logical changes.
- Prefer multiple small commits over one large commit.
- Use conventional commit prefixes:
  - `feat:`
  - `fix:`
  - `docs:`
  - `chore:`
  - `refactor:`
  - `test:`
- Keep commit messages single-line and high-signal.

## Pull Requests

Before opening a PR, ensure:

- Tests pass locally.
- Docs are updated for behavior changes.
- New public behavior includes at least one test.

In PR description, include:

- Problem statement
- What changed
- Validation steps and outputs
- Risk/rollback notes

## Adding New Parsers/Detectors

- Parser changes: update `src/ingestion` and add ingestion tests.
- Detector changes: update `src/preanalysis/patterns.py` and add preanalysis tests.
- If output changes, update report tests and docs.

See:

- `docs/ingestion.md`
- `docs/patterns.md`
- `docs/extensions.md`

## Code of Conduct

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
