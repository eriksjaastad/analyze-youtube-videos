---
tags:
  - p/analyze-youtube-videos
  - type/agent
  - domain/content-analysis
  - tech/python
status: #status/active
created: 2026-01-07
---

# Code Review Checklist - Analyze YouTube Videos

Date: 2026-01-07  
Reviewer: GPT-5.1-codex-max  
Pre-Review Scan: ❌ Not run (manual inspection only; no code executed)

---

## TIER 1: PROPAGATION SOURCES (Must Check First)

- Templates: N/A (project has no template dir; risk not applicable)
- Root configs: README present but generators do not enforce required frontmatter (`domain/content-analysis`, `tech/python`), so outputs diverge → ❌
- Data files: Generated markdown lacks schema validation; destination safety not enforced → ❌

**Tier 1 Grade:** ❌ FAIL

---

## TIER 2: EXECUTION CRITICAL

- Scripts: No timeouts/retries around `yt-dlp`/Ollama; failure paths are print-and-return; no typed interfaces → ❌
- Modules: `run_ollama_command` strips `<think>` but lacks size guard or streaming; environment gate hard-fails when Ollama is down → ❌
- Governance: Tests are unit-only; dependencies unpinned/incomplete (`requirements.txt`) → ❌

**Tier 2 Grade:** ❌ FAIL

---

## TIER 3: DOCUMENTATION

- README high-level and lags current flows (`bridge`, `librarian`, `synthesize`) → ❌
- Standards enforcement: Missing; generated files violate frontmatter expectations → ❌
- Links/examples: TODO and queue docs omit current scripted paths → ⚠️

**Tier 3 Grade:** ❌ FAIL

---

## Findings (severity-ordered)

1) **Hard-to-recover data clobber risk (`scripts/bridge.py`)**  
   - Writes directly into `GLOBAL_LIBRARY_PATH` without validating target; no dry-run path once decision parsed. Mis-set env or cwd will spray “production” files into arbitrary locations. No checksum/size sanity check on model output before write.

2) **Unbounded, no-timeout subprocess calls (`scripts/librarian.py`)**  
   - `yt-dlp` calls lack `check=True` and timeouts; hangs block pipeline. Cleanup still runs and may delete partially written artifacts, silently losing state.

3) **Frontmatter/contract drift & bloat (`librarian.py`, `synthesize.py`)**  
   - Generated markdown omits required tags/status taxonomy; dumps full transcripts verbatim. Quotes/`---` in transcripts can break YAML. No size limits or chunking → repo bloat risk.

4) **Brittle index/queue mutation (`update_index`, `update_queue`)**  
   - In-place string splits, no locking/backups. Concurrent runs or crash mid-write can corrupt `library/00_Index_Library.md` or `VIDEOS_QUEUE.md`. Category heuristic (“strategy” → business) misclassifies entries.

5) **Dependency/runtime fragility (repo-wide)**  
   - `requirements.txt` unpinned and incomplete (no timeout/backoff libs, no ollama bindings). `check_environment()` requires running Ollama even when not needed, blocking CI/offline.

6) **Safety gaps in model I/O (`bridge.py`, `synthesize.py`)**  
   - No size guard, content filtering, or structured errors. Malformed/oversized model output either gets written or aborts with generic prints; no retries/backoff; diagnostics not persisted.

7) **Testing scope is narrow**  
   - Helpers only; no integration coverage for ingest → analysis → library → index/queue, and no negative-path tests (bad URL, missing subs, model failure).

---

## Inverse Test Analysis

- `tests/test_librarian.py`: Helper-focused; no real yt-dlp/timeout/queue/index coverage; markdown integrity untested.  
- `tests/test_synthesize.py`: Mocks model; doesn’t validate frontmatter or large input handling.  
- `tests/test_bridge.py`: Regex parsing only; no end-to-end promotion or malformed JSON paths.  
- `tests/test_config.py`: Key presence only; environment gating and subprocess failures untested.

**Gap:** No integration tests; no negative-path cases → high risk of silent regressions.

---

## Meta-Review

- No enforcement of frontmatter/standards on generated artifacts.  
- Dependency safety unverified; no retry/backoff strategy.  
- Exception handling is print-and-continue; no structured errors.  
- Environment assumptions (Ollama + yt-dlp running) make CI brittle.

---

## Final Grade & Blockers

**Overall Grade:** C (Needs major hardening)  
**Ready to Propagate:** ❌ NO  
**Confidence:** Medium (static/manual only; no commands run)

**Ship Blockers (must fix):**
1. Add strict path validation + dry-run to `bridge.py` before writing to `GLOBAL_LIBRARY_PATH`; refuse if target not validated.  
2. Add timeouts/retries and `check=True` for all `subprocess.run` calls; fail fast and preserve partials.  
3. Enforce required frontmatter schema and size limits when writing library/synthesis markdown; escape/truncate transcripts to avoid YAML breakage and bloat.  
4. Make index/queue updates atomic (temp file + rename) with locking and structured parsing.

**Recommended (next):**
1. Pin/complete `requirements.txt`; document setup/run.  
2. Add integration tests for ingest → analysis → library → index/queue (including negative cases).  
3. Decouple environment gating so CI can stub Ollama/yt-dlp.  
4. Add content-length guards and streaming for model interactions.  
5. Harden category detection/tagging to align with project taxonomy.


## Related Documentation

- [[CODE_REVIEW_ANTI_PATTERNS]] - code review
- [[LOCAL_MODEL_LEARNINGS]] - local AI

