---
tags:
  - p/analyze-youtube-videos
  - type/agent
  - domain/content-analysis
  - tech/python
status: #status/active
created: 2026-01-07
---

# Code Review Checklist - Project Scaffolding

**Date:** 2026-01-07  
**Reviewer:** GPT-5.1 Codex MAX  
**Pre-Review Scan:** ❌ Not run (AI-only review, no automated scan executed)

---

## TIER 1: PROPAGATION SOURCES (Must Check First)

### Templates (Highest Blast Radius)
- [ ] `templates/.cursorrules.template` - N/A (not present in repo)
- [ ] `templates/CLAUDE.md.template` - N/A
- [ ] `templates/AGENTS.md.template` - N/A
- [ ] `templates/TODO.md.template` - N/A
- [ ] `templates/*.template` - N/A

### Root Configs (Referenced by Projects)
- [ ] `AGENTS.md` - N/A in this repo
- [ ] `.cursorrules` - ❌ Hardcoded absolute-style paths to skills library; portability risk when cloned elsewhere.

```
69:80:.cursorrules
- **Playbook:** `/agent-skills-library/playbooks/youtube-channel-analysis/README.md`
- **Cursor adapter:** `/agent-skills-library/cursor-rules/youtube-channel-analysis/RULE.md`
...
Follow the adapter instructions in `/agent-skills-library/cursor-rules/youtube-channel-analysis/RULE.md`
```

- [ ] `.cursorignore` - Not reviewed (not requested/visible)

### Data Files (Used by Scripts)
- [ ] `EXTERNAL_RESOURCES.yaml` - N/A in this repo
- [ ] Schema validation script works - N/A
- [ ] Data structure is sound - N/A

**Tier 1 Grade:** ❌ FAIL (root rules reference absolute paths)

---

## TIER 2: EXECUTION CRITICAL

### Scripts (scripts/)
- [ ] All functions have type hints – ❌ None of the major entrypoints are typed.
- [ ] No `except: pass` or silent failures – ✅ No bare excepts found.
- [ ] Error handling returns status codes – ⚠️ Partial; many flows only print and return `None`.
- [ ] No hardcoded paths (verified by scan) – ⚠️ Uses relative defaults to implicit working directory; slug handling unsafe.
- [ ] No hardcoded secrets – ✅ None found.

Key issues:
1) Unbounded yt-dlp calls without timeouts can hang the pipeline indefinitely.

```
43:74:scripts/librarian.py
cmd_info = ["yt-dlp", "--skip-download", "--print-json", url]
result = subprocess.run(cmd_info, capture_output=True, text=True)
...
cmd_subs = ["yt-dlp", "--skip-download", "--write-subs", ... , url]
sub_result = subprocess.run(cmd_subs, capture_output=True, text=True)
```

2) Generated library entries violate required frontmatter tags (missing `type/agent`, `domain/content-analysis`, `tech/python`).

```
165:186:scripts/librarian.py
tags = ["p/analyze-youtube-videos", "type/knowledge-extraction"]
...
---
tags:
  - p/analyze-youtube-videos
  - type/knowledge-extraction
status: #status/active
created: ...
```

3) Skill promotion path construction is unsanitized; malicious/odd skill names can traverse directories or clobber files.

```
196:213:scripts/bridge.py
slug = args.skill.lower().replace(" ", "-")
skill_dir = GLOBAL_LIBRARY_PATH / "claude-skills" / slug
rule_dir = GLOBAL_LIBRARY_PATH / "cursor-rules" / slug
playbook_dir = GLOBAL_LIBRARY_PATH / "playbooks" / slug
```

4) Index update is brittle; if a category header is missing, the function silently drops the write, leaving new entries unindexed.

```
244:272:scripts/librarian.py
if category in content:
    parts = content.split(category, 1)
    new_content = parts[0] + category + "\n" + entry + parts[1]
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
```

5) Synthesis aggregator loads the entire library into memory with no size guard, retry, or streaming; easy to OOM or exceed model limits as the library grows.

```
8:43:scripts/synthesize.py
aggregated_text = ""
...
aggregated_text += content
```

### Modules (scaffold/)
- [ ] Same standards as scripts – N/A (no scaffold/ here)
- [ ] Async error handling correct – N/A
- [ ] Retry logic present for external calls – ❌ None for yt-dlp/Ollama interactions.

### Governance
- [ ] `.git/hooks/pre-commit` is executable – Not checked
- [ ] Test suite covers expected scope – ❌ Tests mock narrow slices; no integration coverage for queue/index writes or bridge happy-path.
- [ ] Tests actually pass (not just claimed) – Not executed.

**Tier 2 Grade:** ❌ FAIL

---

## TIER 3: DOCUMENTATION

### Core Docs
- [ ] README.md is accurate – ❌ Outdated “Planned” structure diverges from actual (scripts/, library/, synthesis/, tests/ present; workflows/ absent).

```
106:121:README.md
## Directory Structure (Planned)
├── agent-config.yaml
├── workflows/
...
└── outputs/
```

### Consistency
- [ ] Docs don't contradict code – ⚠️ Frontmatter standard in `.cursorrules` conflicts with generated outputs.
- [ ] Examples are runnable – Not verified.
- [ ] Links aren't broken – Not verified.

**Tier 3 Grade:** ❌ FAIL

---

## INVERSE TEST ANALYSIS

**Test:** `tests/test_librarian.py`  
- **Checks:** `clean_srt`, `get_video_data` error paths, limited `run_ollama_command` behavior.  
- **Doesn't Check:** Success path for saving to library, queue/index mutation, frontmatter compliance, network timeouts.  
- **Action Taken:** Flagged as coverage gap.

**Test:** `tests/test_bridge.py`  
- **Checks:** `parse_decision`, `extract_skill_data`, `evaluate_utility` stub.  
- **Doesn't Check:** Main flow, file writes, slug/path safety, JSON validation failure paths.  
- **Action Taken:** Flagged as coverage gap.

**Test:** `tests/test_synthesize.py`  
- **Checks:** Aggregation skip logic, basic synthesis parsing.  
- **Doesn't Check:** Large-library performance, output frontmatter correctness, retry/backoff on LLM failures.  
- **Action Taken:** Flagged as coverage gap.

---

## META-REVIEW

- [x] Checked ALL files in scripts/ and tests/ relevant to execution  
- [ ] Verified test scope matches claims – Gaps noted above  
- [ ] Scanned for deprecated APIs – Not done  
- [ ] Verified dependency safety – Requirements unpinned; yt-dlp/requests versions unspecified  
- [ ] Checked exception handling – Partial; prints without retries/timeouts remain  
- [ ] No assumptions without verification – Outstanding items noted as not checked

---

## FINAL GRADE & BLOCKERS

**Overall Grade:** C (significant execution and governance risks)

**Ship Blockers (Must Fix):**
1. `.cursorrules` references absolute-style paths to the skills library; violates portability and the project’s own TODO to remove hardcoded paths.  
2. `scripts/librarian.py` generates frontmatter missing required tags, guaranteeing non-compliant docs and downstream index/report drift.  
3. `scripts/bridge.py` slug/path construction lacks sanitization and validation; a crafted skill name can traverse or clobber arbitrary directories under `GLOBAL_LIBRARY_PATH`.  
4. `scripts/librarian.py` invokes `yt-dlp` twice with no timeout/retry; a stalled network call hangs the run and blocks cleanup.  
5. `scripts/synthesize.py` aggregates all library content into memory and sends it to the model without chunking/guardrails; high risk of OOM or model rejection as the library grows.

**Recommended Fixes (Nice to Have):**
1. Add type hints across scripts and enforce via CI; align with Tier 2 standard.  
2. Harden `update_index` to handle missing categories and preserve file integrity (use structured parsing rather than naive split).  
3. Add end-to-end tests covering library save → queue/index updates and bridge promotion happy-path with temporary directories.  
4. Pin dependencies (yt-dlp/requests/pytest) and document exact Ollama model versions.  
5. Update README to reflect the actual repository layout (scripts/, library/, synthesis/, tests/) and current workflows.

**Confidence Level:** Medium (manual static review only; no execution or automated scan)

**Ready to Propagate:** ❌ NO

---

