# Good first issues (seed list)

Copy any block into a new GitHub issue. Maintainers may edit titles/labels.

---

### 1. Add `--json` shorthand for `analyze -f json`

**Problem:** Muscle memory from other CLIs expects `--json`.  
**Scope:** Typer option on `analyze` only; wire to existing format flag.  
**Tests:** Extend CLI subprocess test if present, or add one.

---

### 2. Colorize `replay` output by event type

**Problem:** `replay` is plain text; tool vs LLM vs error could use Rich styles.  
**Scope:** `src/cli.py` `replay_trace` loop only.  
**Tests:** Optional snapshot or smoke that command exits 0.

---

### 3. Document OpenTelemetry ingestion edge case

**Problem:** Users hit traces that parse but normalize oddly.  
**Scope:** Add a subsection to `docs/ingestion.md` with one fixture path and expected behavior.  
**Tests:** None required if docs-only.

---

### 4. Detector: “silent tool” (tool returns `{}` every time)

**Problem:** Some agents spam empty dicts without marking errors.  
**Scope:** New `PatternType` + detector in `patterns.py`, one fixture + manifest line, `test_preanalysis` assertion.  
**Tests:** Required.

---

### 5. `watch`: optional `--recursive` flag

**Problem:** Some projects nest traces in subfolders.  
**Scope:** Watchdog `recursive=True` when flag set; default stays `False`.  
**Tests:** Unit test with temporary nested dir (short timeout).

---

### 6. PyPI README badges after first release

**Problem:** Badges in README need real PyPI version links.  
**Scope:** README only, post-publish.  
**Tests:** N/A
