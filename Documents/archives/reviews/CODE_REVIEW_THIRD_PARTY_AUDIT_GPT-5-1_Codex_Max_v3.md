---
tags:
  - p/analyze-youtube-videos
  - type/agent
  - domain/content-analysis
  - tech/python
  - type/review
status: #status/active
created: 2026-01-07
---

# Code Review Checklist - Third-Party Audit

**Date:** 2026-01-07  
**Reviewer:** GPT-5.1-Codex-Max  
**Pre-Review Scan:** ❌ NOT RUN (manual review only)

---

## TIER 1: PROPAGATION SOURCES (Must Check First)

### Templates / Root Configs
- [ ] `.cursorrules` - Contains absolute-style references to `/agent-skills-library/` that will break on non-rooted checkouts and conflicts with the repo’s own “DNA repair” TODO.
- [ ] Repository-wide markdown standard adherence - Library entries violate required tag set (`domain/content-analysis`, `tech/python` missing).

### Data Files (Used by Scripts)
- [ ] `VIDEOS_QUEUE.md` - Queue relies on in-file mutation; no schema or validation guards.
- [ ] Library markdowns - Include full transcripts without size gating; downstream tools ingest them wholesale.

**Tier 1 Grade:** ❌ FAIL

---

## TIER 2: EXECUTION CRITICAL

### Scripts (scripts/)
- [ ] `scripts/librarian.py` - Ingests entire transcript into stored markdown and later synthesis without truncation or chunking → easy to exceed model context and memory when aggregating.
- [ ] `scripts/synthesize.py` - Aggregates every library file naively; no token budgeting, no streaming, no dedupe, no filtering of “Full Transcript” sections.
- [ ] `scripts/bridge.py` - Writes directly into `GLOBAL_LIBRARY_PATH` with skill-name-derived slugs that are not sanitized for path separators or shell metacharacters; no rollback if any write fails.
- [ ] `scripts/config.py` - `run_ollama_command` has no retry/backoff and blocks the process on any transient CLI failure.

### Governance / Dependencies
- [ ] `requirements.txt` - Completely unpinned; no hashes or upper/lower bounds, no runtime deps for sqlite/report generation captured.
- [ ] Tests - Purely unit-level mocks; no end-to-end path covering yt-dlp/Ollama presence, file writes, or synthesis outputs.

**Tier 2 Grade:** ❌ FAIL

---

## TIER 3: DOCUMENTATION

### Core Docs
- [ ] `README.md` - Still describes “planning phase” and old directory layout; diverges from actual structure (e.g., `Documents/`, `library/`, `synthesis/` exist, no `agent-config.yaml`, `workflows/`).
- [ ] Library entries - Missing mandated tags and omit `domain/content-analysis` / `tech/python` required by `.cursorrules`.

### Consistency
- [ ] Reports/synthesis files embed entire transcripts; contradicts “context window management” rule to avoid bloat.
- [ ] No linkage from scripts to skill adapters defined in `.cursorrules` (no integration docs or runbook).

**Tier 3 Grade:** ❌ FAIL

---

## INVERSE TEST ANALYSIS

**Test:** `tests/test_librarian.py`  
- **Checks:** `clean_srt`, mocked yt-dlp happy/fail paths.  
- **Doesn't Check:** Real yt-dlp invocation, subtitle selection behavior across locales, transcript size constraints, or downstream file writes.  
- **Action Taken:** Manual review only; consider integration test that runs against a tiny fixture video.

**Test:** `tests/test_synthesize.py`  
- **Checks:** Aggregation skips index files; basic mock synthesis output parsing.  
- **Doesn't Check:** Token budgeting, large-library behavior, file write success, or topic/category filtering accuracy.  
- **Action Taken:** Manual review; needs load-aware tests and failure-path coverage.

---

## META-REVIEW

- [ ] Checked ALL files in library/ for frontmatter compliance (spot checks revealed missing required tags).
- [ ] Verified test scope vs. claims (unit-only; no E2E).
- [ ] Scanned for deprecated/brittle API usage (yt-dlp/Ollama CLIs assumed available; no fallbacks).
- [ ] Verified dependency safety (unpinned; no supply-chain controls).
- [ ] Checked exception handling (no retries/backoff on model calls; file writes lack rollback).
- [ ] No assumptions without verification (manual evidence cited below).

---

## EVIDENCE (Key Findings)

**Frontmatter rule violated by library entries** (missing `domain/content-analysis`, `tech/python`; tag shape diverges from `.cursorrules`):

```1:14:library/2026-01-06_Aniket_Panjwani_The-Creator-of-Claude-Code-Shares-His-Exact-Setup.md
---
tags:
  - p/analyze-youtube-videos
  - type/knowledge-extraction
status: #status/active
created: 2026-01-06
...
```

**Full transcripts persisted and later re-ingested by synthesis (prompt bloat risk):**

```169:190:scripts/librarian.py
    content = f"""---
...
## Full Transcript
{data['transcript']}
"""
```

**Synthesis aggregates every markdown wholesale; no chunking or token guard:**

```8:43:scripts/synthesize.py
def aggregate_library(category=None):
    """
    Reads all markdown files in the library and aggregates their content.
    If category is provided, only files in that category are included.
    """
...
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
...
            aggregated_text += f"\n\n--- DOCUMENT: {filename} ---\n\n"
            aggregated_text += content
```

**Bridge writes to global skill library using unsanitized skill name slugs; no rollback on partial failure:**

```197:213:scripts/bridge.py
    slug = args.skill.lower().replace(" ", "-")
    skill_dir = GLOBAL_LIBRARY_PATH / "claude-skills" / slug
...
    with open(skill_dir / "SKILL.md", "w") as f:
        f.write(templates["SKILL_MD"])
```

**Dependencies unpinned; zero integrity controls:**

```1:4:requirements.txt
requests
yt-dlp
pytest
pytest-mock
```

**Documentation vs reality mismatch (promised structure no longer matches repo):**

```106:121:README.md
## Directory Structure (Planned)
...
├── agent-config.yaml            ← Agent configuration
├── workflows/
...
└── outputs/                     ← Generated reports
```

---

## FINAL GRADE & BLOCKERS

**Overall Grade:** C (high fragility in data handling, documentation drift, and dependency hygiene)  

**Ship Blockers (Must Fix):**
1. Enforce frontmatter/tag standards across `library/`, `synthesis/`, and `Documents/`; current files violate `.cursorrules`, breaking downstream tools that rely on taxonomy.
2. Add token/size budgeting and chunking before aggregation in `scripts/synthesize.py`; avoid loading entire transcripts into a single prompt.
3. Harden `scripts/bridge.py` path handling (sanitize slugs, fail atomically, add rollback) before writing to global skill library.
4. Pin runtime dependencies with versions/hashes in `requirements.txt`; add minimum supported versions for yt-dlp/Ollama.

**Recommended Fixes (Nice to Have):**
1. Update `README.md` to actual structure and current phase; add runbook tying scripts to referenced skill adapters.
2. Add integration tests that run yt-dlp/Ollama behind fakes or fixtures to validate end-to-end flows and file outputs.
3. Introduce retries/backoff for `run_ollama_command` and long-running CLI calls; surface errors with structured logs instead of prints.
4. Add size thresholds when writing library entries (truncate or store transcript separately) to keep library files usable by synthesis.
5. Provide schema/validation for `VIDEOS_QUEUE.md` to avoid malformed moves and ensure deterministic updates.

**Confidence Level:** Medium (core scripts reviewed; no dynamic execution performed; risk of hidden data-dependent failures remains).  
**Ready to Propagate:** ❌ NO

---

*This review follows the v1.1 Ecosystem Governance & Review Protocol.*

