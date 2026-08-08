#!/usr/bin/env bash
#
# Agent Autopsy — one-command, fully offline product demo.
#
# Run this from a fresh shell:
#     bash scripts/demo.sh          (auto-bootstraps the venv if needed)
# or (recommended after first run):
#     source .venv/bin/activate && bash scripts/demo.sh
#
# It requires no API keys, does no network calls, and walks through the
# whole deterministic pipeline: analyze a real failing trace, show the
# findings, generate a fix, then diff the failing vs. fixed run.
#
# NOTE: `autopsy analyze` intentionally exits 1 when it detects failure
# patterns — a CI gate you can key off. The demo uses that as a feature.
#
set -euo pipefail

# Keep the offline demo offline even when optional embedding dependencies are
# installed and no model cache is present. Callers may still override these.
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"

# --- resolve paths -------------------------------------------------------
SCRIPT_SRC="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SRC")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$ROOT/.venv"
AUTOPSY="$VENV/bin/autopsy"
PYBIN="$VENV/bin/python"

TRACES="$ROOT/examples/traces"
FAILING_TRACE="$TRACES/loop_failure.json"
FIXED_TRACE="$TRACES/loop_fixed.json"

# --- colors (safe on any terminal; harmless when piped) ------------------
C_RESET=$'\033[0m'
C_BOLD=$'\033[1m'
C_DIM=$'\033[2m'
C_GREEN=$'\033[32m'
C_YELLOW=$'\033[33m'
C_BLUE=$'\033[34m'
C_MAGENTA=$'\033[35m'
C_CYAN=$'\033[36m'

banner() { printf '%s%s%s\n' "$C_BOLD$C_CYAN" "──────────────────────────────────────────────────────────────" "$C_RESET"; }
info()   { printf '%s▸ %s%s\n' "$C_BOLD$C_BLUE" "$*" "$C_RESET"; }
ok()     { printf '%s✓ %s%s\n' "$C_GREEN" "$*" "$C_RESET"; }
label()  { printf '%s%s%s\n' "$C_BOLD$C_MAGENTA" "$*" "$C_RESET"; }
dim()    { printf '%s%s%s\n' "$C_DIM" "$*" "$C_RESET"; }
code()   { printf '%s$ %s%s\n' "$C_BOLD$C_YELLOW" "$*" "$C_RESET"; }

# Run an autopsy command, keep the demo alive if the CLI signals findings.
# Analyze returns 1 on purpose when failure patterns are detected.
run() {
  local rc=0
  "$@" || rc=$?
  if [ "$rc" -eq 1 ]; then
    printf '%s  (exit 1 = failure patterns detected — a CI gate signal)%s\n' "$C_DIM" "$C_RESET"
  elif [ "$rc" -ne 0 ]; then
    printf '%s  (exit %s)%s\n' "$C_DIM" "$rc" "$C_RESET"
  fi
}

pause() {
  if [ -t 0 ] && [ -z "${AUTOPSY_DEMO_FAST:-}" ]; then
    printf '%s(press ENTER to continue)%s' "$C_DIM" "$C_RESET"
    read -r _ || true
  else
    sleep "${AUTOPSY_DEMO_GAP:-0.6}"
  fi
}

# --- stage 0: make sure the CLI exists -----------------------------------
if [ ! -x "$AUTOPSY" ]; then
  info "Bootstrapping a fresh Python venv (first run only)"
  PY="$(command -v python3.12 || command -v python3.11 || command -v python3.10 || echo python3)"
  "$PY" -m venv "$VENV"
  "$PYBIN" -m pip install --quiet --upgrade pip
  "$PYBIN" -m pip install --quiet -e "$ROOT"
fi

# --- stage 1: hero banner ------------------------------------------------
banner
label "A G E N T   A U T O P S Y"
label "local-first debugging for AI agent traces"
banner
dim "Fully OFFLINE · no API keys · no network · deterministic engine only"
echo
code "autopsy analyze examples/traces/loop_failure.json --no-llm --no-embeddings"
echo
ok "autopsy CLI: v$("$PYBIN" -c 'import importlib.metadata as m; print(m.version("agent-autopsy"))' 2>/dev/null || echo '?')"
ok "failure trace: $(basename "$FAILING_TRACE")    fixed trace: $(basename "$FIXED_TRACE")"
pause

# --- stage 2: the failing trace ------------------------------------------
banner
info "Part 1 — a run that is stuck: the infinite retry loop"
banner
dim "An agent must 'find the weather in New York & convert to Fahrenheit'."
dim "Its web_search tool times out... so it retries. And retries. Seven times,"
dim "all identical, all failing — then the run dies with 'Maximum retries exceeded'."
echo
info "Quick read on what happened:"
code "autopsy summary examples/traces/loop_failure.json"
echo
run "$AUTOPSY" summary "$FAILING_TRACE"
pause

# --- stage 3: deterministic root-cause analysis (the WOW) ----------------
banner
info "Part 2 — the deterministic failure-pattern pipeline"
banner
dim "No LLM. No embeddings. Pure signal detection over the event stream:"
dim "loops, retry storms, hallucinated tools, error cascades, timeouts, ..."
echo
code "autopsy analyze examples/traces/loop_failure.json --no-llm --no-embeddings"
echo
run "$AUTOPSY" analyze "$FAILING_TRACE" --no-llm --no-embeddings
echo
ok "Deterministic engine pins the failure to a single loop."
ok "Note the exit code: findings detected ⇒ CLI exits 1 (CI can gate on this)."
pause

# --- stage 4: generate a fix ---------------------------------------------
banner
info "Part 3 — generate a fix"
banner
dim "Autopsy turns findings into concrete, ready-to-apply code: a LoopGuard"
dim "that caps identical tool calls, and an error boundary for the cascade."
echo
code "autopsy fixes examples/traces/loop_failure.json"
echo
run "$AUTOPSY" fixes "$FAILING_TRACE"
echo
FIX_DIR="$(mktemp -d "$ROOT/.demo-fixes.XXXXXX")"
trap 'rm -rf "$FIX_DIR"' EXIT
dim "The same analysis can emit full patch artifacts:"
code "autopsy analyze examples/traces/loop_failure.json --no-llm --no-embeddings --artifacts <dir>"
run "$AUTOPSY" analyze "$FAILING_TRACE" --no-llm --no-embeddings --artifacts "$FIX_DIR" >/dev/null
printf '%s✓ artifacts written to %s: %s%s\n' "$C_GREEN" "$FIX_DIR" "$(ls -1 "$FIX_DIR" | tr '\n' ' ')" "$C_RESET"
echo
label "It is real code — the generated LoopGuard:"
echo
if [ -f "$FIX_DIR/loop_guard.py" ]; then
  sed -n '1,22p' "$FIX_DIR/loop_guard.py"
else
  dim "No loop_guard.py artifact was generated for this trace."
fi
echo
pause

# --- stage 5: diff failing vs fixed --------------------------------------
banner
info "Part 4 — diff the failing run against the fixed run"
banner
dim "Same goal. Before: the looping run. After: the same agent once the"
dim "LoopGuard + timeout fix are in place. One command shows the delta."
echo
code "autopsy diff examples/traces/loop_failure.json examples/traces/loop_fixed.json"
echo
run "$AUTOPSY" diff "$FAILING_TRACE" "$FIXED_TRACE"
echo
ok "Every failure pattern is present ONLY in the failing run."
ok "The fixed run is clean: no loop, no cascades, no timeouts."
pause

# --- stage 6: the fixed run ----------------------------------------------
banner
info "Part 5 — the healthy run, post-fix"
banner
code "autopsy analyze examples/traces/loop_fixed.json --no-llm --no-embeddings"
echo
run "$AUTOPSY" analyze "$FIXED_TRACE" --no-llm --no-embeddings
echo
ok "Health score flips 23/100 → 100/100."
ok "CLI exit code flips 1 → 0: the same gate your CI can enforce."
pause

# --- stage 7: closing ----------------------------------------------------
banner
info "Now point it at your own traces"
echo
code "autopsy analyze ./traces/my_run.json --no-llm --no-embeddings"
code "autopsy diff ./run_before.json ./run_after.json"
code "autopsy replay ./trace.json --step"
code "autopsy benchmark --traces-dir ./traces"
banner
label "✓ demo complete · Agent Autopsy ran fully offline"
