# CODE REVIEW: YouTube-to-Skill Pipeline

**Review Date:** 2026-01-06 20:51 UTC
**Reviewer:** Senior Principal Engineer (Systems Architecture)
**Commit Reviewed:** acc9651

---

## 1. The Engineering Verdict

### **[Dangerous Wrapper]**

This pipeline is a toy dressed up as infrastructure. It creates the *illusion* of automation while harboring silent data corruption vectors, hardcoded paths that guarantee failure on any machine but yours, and an LLM-powered "Healer" that will eventually destroy your source code when it hallucinates a "fix." The cross-project coupling to `/Users/eriksjaastad/projects/agent-skills-library/` is not configuration—it's a time bomb. The moment you onboard a collaborator, containerize this, or simply move your home directory, every script in `bridge.py` will fail silently or write files into the void. The "utility evaluation" in bridge.py burns tokens on an LLM call that provides zero gating—you parse the decision string with `if "[REJECT]" in evaluation`, which is prompt-injection territory. This is not production code. This is a weekend hack with aspirations.

---

## 2. The "Toy" Test & Utility Reality Check

### False Confidence (The "Lies" in the Code)

| # | File | Code | Problem | Impact |
|---|------|------|---------|--------|
| 1 | `scripts/bridge.py:12` | `GLOBAL_LIBRARY_PATH = Path("/Users/eriksjaastad/projects/agent-skills-library")` | **Hardcoded absolute path to a user's home directory.** No environment variable, no config file, no CLI argument. | Script fails on any other machine. Docker? CI/CD? Collaboration? Dead on arrival. |
| 2 | `scripts/librarian.py:104-105` | `elif srt_files: target_file = os.path.join(TEMP_DIR, srt_files[0])` | **Non-deterministic file selection.** `os.listdir()` returns in arbitrary filesystem order. If multiple SRT variants exist, you pick whichever the inode gods favor. | You might analyze auto-subs one run, manual subs the next. Results are non-reproducible. |
| 3 | `scripts/librarian.py:113-114` | `try: os.remove(...) except: pass` | **Bare except that swallows all errors.** Permission denied? Disk full? File locked? You'll never know. | Silent failures corrupt your assumptions about system state. Debugging becomes impossible. |
| 4 | `scripts/healer.py:98-99` | `with open(args.skill, 'w', ...): f.write(healed_code)` | **LLM output written directly to source file with ZERO validation.** No syntax check, no AST parse, no test run, no diff review. | One hallucinated fix corrupts your codebase. The "backup" doesn't help if you don't notice until 10 commits later. |
| 5 | `scripts/bridge.py:162` | `if "[REJECT]" in evaluation and not args.dry_run:` | **String-matching on unstructured LLM output for control flow.** If the model says "This is NOT a [REJECT]ion," your conditional fails. | Prompt injection or model drift bypasses your "gatekeeper." This is security theater. |
| 6 | `scripts/bridge.py:189-194` | `f.write(templates["SKILL_MD"])` | **No validation that `templates` dict contains expected keys.** `generate_templates()` can return malformed JSON. | `KeyError` crash, or worse—partial writes to the skills library. |
| 7 | `scripts/librarian.py:77-88` | Writes to `scripts/temp/transcript` without locking | **Race condition.** Two concurrent librarian runs write to the same temp file. | Data corruption. You analyze a transcript from the wrong video. |
| 8 | `scripts/synthesize.py:29` | `for filename in sorted(os.listdir(LIBRARY_DIR)):` | **Sorts by filename, not by creation date or semantic relevance.** | Synthesis order is arbitrary. If file naming conventions drift, so does your aggregation logic. |
| 9 | Configuration sprawl | `OLLAMA_URL` defined in `librarian.py:10`, `healer.py:8`, `synthesize.py:9` | **DRY violation.** Three places to change if you switch Ollama port. | Configuration drift. One script points to localhost:11434, another to a Docker container. Silent mismatch. |
| 10 | `scripts/bridge.py:20-24` | `subprocess.run(["ollama", "run", OLLAMA_MODEL, prompt], ...)` | **Different Ollama invocation than other scripts** (CLI vs HTTP API). No timeout. | Inconsistent behavior. If Ollama CLI changes, this breaks while others keep working. |

---

### The Bus Factor

**Undocumented Order Dependencies:**

1. **Librarian → Library directory** must exist or `save_to_library()` creates it, but `update_index()` expects `library/00_Index_Library.md` to already exist (line 300-301). If you run Librarian before manually creating the index, it prints a warning and silently skips indexing.

2. **Synthesize → Library** assumes `library/` contains `.md` files. If Librarian hasn't run, Synthesize exits with "No documents found." No programmatic way to verify the pipeline state.

3. **Bridge → Synthesize output** expects a source file from synthesis, but there's no contract. You pass `--source` manually. Nothing validates the file is a synthesis output vs. raw library entry.

4. **Healer → Any Python file**. No scope restriction. You could point it at `bridge.py` itself and let the LLM rewrite your promotion logic.

5. **GLOBAL_LIBRARY_PATH** in bridge.py is assumed to exist with specific subdirectories (`claude-skills/`, `cursor-rules/`, `playbooks/`). No validation. `mkdir -p` on line 185 will create them, but if the base path is wrong, you're writing to `/Users/eriksjaastad/projects/agent-skills-library/claude-skills/some-skill/SKILL.md` on a Linux server where that path doesn't exist.

---

### 10 Failure Modes

1. **Ollama Not Running:** Every script prints an error and returns `None` or a useless string. No retry. No health check. User sees partial output with no clear indication of what failed.

2. **Ollama Timeout:** `synthesize.py` sets 300s timeout (line 88). If your M4 Pro takes 301 seconds on a 64k context synthesis, you get a `requests.exceptions.ReadTimeout` and lose all progress.

3. **Disk Full During Write:** `save_to_library()` opens file, writes partial content, crashes. File exists but is corrupt. Index update runs anyway if the exception wasn't raised.

4. **yt-dlp Rate Limited:** YouTube returns 429. `subprocess.run()` captures stderr but doesn't parse it. Script continues with empty transcript. LLM analyzes nothing.

5. **Multiple Concurrent Runs:** Two terminals running `librarian.py` on different URLs. Both write to `scripts/temp/transcript.en.srt`. One overwrites the other mid-read. Corrupt analysis.

6. **LLM Returns Non-JSON (Bridge):** DeepSeek-R1 wraps response in markdown despite prompt. `json.loads()` fails. `generate_templates()` returns `None`. User told "Failed to generate templates" with no context.

7. **LLM Hallucinates Python Syntax (Healer):** Model returns `def foo(: pass`. You write this to your source file. Now your codebase won't even parse. Backup exists but you don't notice until CI fails.

8. **VIDEOS_QUEUE.md Format Drift:** `update_queue()` parses markdown with hardcoded section markers (lines 259-260). Someone adds a typo: `### Priorty Queue`. The URL is never removed. User re-analyzes the same video.

9. **Non-English Subtitles:** Video has Spanish subs only. `--sub-lang en` finds nothing. Auto-subs disabled on video. `transcript` is empty string. LLM "analyzes" an empty transcript and produces hallucinated summary.

10. **agent-skills-library Directory Missing:** Bridge tries to write to `/Users/eriksjaastad/projects/agent-skills-library/claude-skills/`. Path doesn't exist (wrong machine, renamed folder). `mkdir -p` creates nested dirs under non-existent root → `FileNotFoundError` or worse, creates orphan directories in `/Users/` on a shared server.

---

## 3. Deep Technical Teardown

### Architectural Anti-Patterns

**1. Global Constant Redefinition**

```
librarian.py:10   OLLAMA_URL = "http://localhost:11434/api/generate"
librarian.py:11   MODEL = "deepseek-r1:14b"

healer.py:8       OLLAMA_URL = "http://localhost:11434/api/generate"
healer.py:9       MODEL = "deepseek-r1:14b"

synthesize.py:9   OLLAMA_URL = "http://localhost:11434/api/generate"
synthesize.py:10  MODEL = "deepseek-r1:14b"

bridge.py:13      OLLAMA_MODEL = "deepseek-r1:14b"  # Different variable name
bridge.py:15-31   Uses subprocess CLI instead of HTTP API
```

This is configuration by copy-paste. Change the model in one file, forget the others. Now Librarian uses R1:14b, Healer uses R1:8b, and your pipeline produces inconsistent outputs.

**2. Mixed Ollama Invocation**

- `librarian.py`, `healer.py`, `synthesize.py`: HTTP POST to `/api/generate`
- `bridge.py`: `subprocess.run(["ollama", "run", ...])`

The CLI invocation doesn't support the same options (no `num_ctx`, no `temperature` passthrough). Your "evaluation" runs with default parameters while everything else uses tuned settings.

**3. Temp Directory as Global Mutable State**

`TEMP_DIR = "scripts/temp"` is a shared dumping ground. No namespacing per video ID. No atomic file operations. No cleanup on failure. This is a classic "works on my machine" pattern that breaks under any concurrent or interrupted execution.

---

### State & Data Integrity

**Skill Promotion Has No Verification**

`bridge.py` "promotes" a skill by:
1. Calling LLM to evaluate (lines 56-80)
2. Calling LLM to generate templates (lines 82-139)
3. Writing three files directly (lines 189-194)

**Missing:**
- No verification that generated SKILL.md contains valid markdown
- No verification that the playbook structure matches expectations
- No test that the skill is parseable by the consuming tools
- No idempotency check—run twice, overwrite without warning
- No rollback if one of three writes fails

**Library Index Integrity**

`librarian.py:295-328` (`update_index()`) manipulates markdown by splitting strings at section headers. If the index file structure changes—a refactor, a new category—the split logic silently fails. The entry either duplicates or vanishes.

---

### Silent Killers

**1. No Service Health Checks**

None of the scripts verify Ollama is running before making requests. A simple `GET /api/tags` health check would save 10 minutes of debugging "why is my analysis empty?"

**2. No Telemetry**

- No timing data (how long did analysis take?)
- No token counts (how much context did we actually use?)
- No success/failure metrics
- No cost tracking if you switch to paid API

**3. Happy Path Assumes External State**

- `yt-dlp` is installed (no check)
- `ollama` CLI is in PATH (bridge.py assumes it)
- `VIDEOS_QUEUE.md` exists and is well-formed
- `library/00_Index_Library.md` exists
- Network is available
- YouTube isn't blocking your IP

Every external dependency is assumed present. Every failure mode is a surprise.

---

### Complexity Tax

**1. The "Utility Evaluation" is Redundant**

`bridge.py` calls the LLM twice:
1. `evaluate_utility()` — asks "should we promote this?"
2. `generate_templates()` — asks "generate the files"

The evaluation output is passed to generation, but the generation prompt doesn't meaningfully use it beyond stuffing it in context. You're burning ~2000 tokens on a decision that could be:
- A deterministic rule (if source contains specific markers)
- A single combined prompt
- A human decision (it's a CLI tool, ask the user)

**2. Regex Gymnastics for JSON Extraction**

```python
# bridge.py:126-136
start_idx = response.find('{')
end_idx = response.rfind('}')
if start_idx != -1 and end_idx != -1:
    json_str = response[start_idx:end_idx+1]
```

This "find first `{` and last `}`" approach fails if:
- The model outputs explanation before JSON
- The JSON contains nested objects (finds wrong braces)
- The model outputs multiple JSON blocks

Use a proper JSON extraction pattern or constrain the model output with system prompts.

---

## 4. Evidence-Based Critique

| Issue | File:Line | Code Evidence | Impact |
|-------|-----------|---------------|--------|
| Hardcoded user path | `bridge.py:12` | `Path("/Users/eriksjaastad/projects/agent-skills-library")` | Zero portability |
| Bare except | `librarian.py:114` | `except: pass` | Silent failures |
| Non-deterministic selection | `librarian.py:105` | `srt_files[0]` | Non-reproducible results |
| Unvalidated LLM write | `healer.py:98-99` | `f.write(healed_code)` | Source corruption |
| String-match control flow | `bridge.py:162` | `if "[REJECT]" in evaluation` | Bypassable gating |
| No key validation | `bridge.py:189` | `templates["SKILL_MD"]` | KeyError crash |
| Mixed API patterns | `bridge.py:20` vs `librarian.py:182` | CLI vs HTTP | Inconsistent behavior |
| Race condition | `librarian.py:77` | Shared temp path | Data corruption |
| No timeout handling | `bridge.py:20-24` | `subprocess.run()` no timeout | Infinite hang |
| Missing deps check | All files | No `shutil.which()` calls | Cryptic failures |

---

## 5. Minimum Viable Power (MVP)

### The "Signal": Worth Saving

1. **`clean_srt()` in librarian.py (lines 15-49)**: Solid, deterministic text processing. The regex patterns are correct. This is the kind of code that belongs in a utility module.

2. **Prompt structure in `analyze_with_ollama()` (lines 138-173)**: The "Librarian" persona prompt is well-structured with clear sections. Good example of prompt engineering.

3. **Frontmatter generation in `save_to_library()` (lines 212-234)**: The YAML frontmatter pattern with tags is a reasonable knowledge management approach.

4. **`aggregate_library()` in synthesize.py (lines 14-49)**: Clean file iteration with index filtering. Does one thing correctly.

### The "Noise": Delete Immediately

1. **`healer.py` (entire file)**: This is not "self-healing." This is automated code corruption. Delete it before someone uses it in anger. If you want LLM-assisted fixing, use a proper code review workflow where a human approves changes.

2. **`evaluate_utility()` in bridge.py (lines 56-80)**: Remove this function. It provides no value. Either make promotion deterministic based on source file markers, or trust the human who ran the command.

3. **The existing REVIEW.md content**: It was a friendly chat log, not a code review. (Now replaced.)

4. **Inline Ollama option variations**: The scattered `num_ctx`, `temperature`, `num_predict` settings across files. Centralize or delete.

---

## 6. Remediation Task Breakdown (Atomic Tasks)

### Task 1: Create Central Configuration
**File:** `scripts/config.py` (new file)
**Location:** New file
**Code:**
```python
import os
from pathlib import Path

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
LIBRARY_DIR = Path(os.getenv("LIBRARY_DIR", "library"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "scripts/temp"))
SKILLS_LIBRARY_PATH = Path(os.getenv("SKILLS_LIBRARY_PATH", "./agent-skills-library"))
```
**Done when:** `python -c "from scripts.config import OLLAMA_URL; print(OLLAMA_URL)"` prints the URL.

---

### Task 2: Fix Bare Except in Librarian
**File:** `scripts/librarian.py`
**Location:** Line 113-114
**Current:**
```python
try: os.remove(os.path.join(TEMP_DIR, f))
except: pass
```
**Replace with:**
```python
try:
    os.remove(os.path.join(TEMP_DIR, f))
except OSError as e:
    print(f"[!] Failed to remove temp file {f}: {e}")
```
**Done when:** Running with a locked temp file produces a visible error message.

---

### Task 3: Fix Non-Deterministic SRT Selection
**File:** `scripts/librarian.py`
**Location:** Lines 96-105
**Current:**
```python
srt_files = [f for f in os.listdir(TEMP_DIR) if f.endswith('.srt')]
# ...
elif srt_files:
    target_file = os.path.join(TEMP_DIR, srt_files[0])
```
**Replace with:**
```python
srt_files = sorted([f for f in os.listdir(TEMP_DIR) if f.endswith('.srt')])
# Prefer non-auto subs
manual_srt = [f for f in srt_files if '.auto' not in f.lower()]
target_file = os.path.join(TEMP_DIR, manual_srt[0] if manual_srt else srt_files[0]) if srt_files else None
```
**Done when:** Running twice on same video produces identical transcript selection.

---

### Task 4: Add Ollama Health Check
**File:** `scripts/librarian.py`
**Location:** Before line 182 (in `analyze_with_ollama`)
**Add:**
```python
def check_ollama_health():
    try:
        resp = requests.get(OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=5)
        return resp.status_code == 200
    except:
        return False

# In analyze_with_ollama, before the request:
if not check_ollama_health():
    print("[!] Ollama is not running. Start it with: ollama serve")
    return None
```
**Done when:** Running with Ollama stopped produces clear error message instead of connection refused.

---

### Task 5: Remove Hardcoded Path in Bridge
**File:** `scripts/bridge.py`
**Location:** Line 12
**Current:**
```python
GLOBAL_LIBRARY_PATH = Path("/Users/eriksjaastad/projects/agent-skills-library")
```
**Replace with:**
```python
GLOBAL_LIBRARY_PATH = Path(os.getenv("SKILLS_LIBRARY_PATH", "./agent-skills-library"))
```
**Done when:** `SKILLS_LIBRARY_PATH=/tmp/test python scripts/bridge.py --help` doesn't crash.

---

### Task 6: Add JSON Schema Validation to Bridge
**File:** `scripts/bridge.py`
**Location:** After line 132
**Add:**
```python
required_keys = {"SKILL_MD", "RULE_MD", "README_MD"}
if not required_keys.issubset(templates.keys()):
    missing = required_keys - set(templates.keys())
    print(f"❌ Generated templates missing keys: {missing}")
    return None
```
**Done when:** Malformed LLM output produces "missing keys" error instead of KeyError crash.

---

### Task 7: Delete healer.py
**File:** `scripts/healer.py`
**Location:** Entire file
**Action:** `rm scripts/healer.py`
**Done when:** `ls scripts/healer.py` returns "No such file or directory".

---

### Task 8: Add Temp Directory Namespacing
**File:** `scripts/librarian.py`
**Location:** Line 77
**Current:**
```python
sub_path_base = os.path.join(TEMP_DIR, "transcript")
```
**Replace with:**
```python
import hashlib
url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
sub_path_base = os.path.join(TEMP_DIR, f"transcript_{url_hash}")
```
**Done when:** Two concurrent runs on different URLs produce different temp files.

---

### Task 9: Add yt-dlp Dependency Check
**File:** `scripts/librarian.py`
**Location:** Top of `main()` function, line 331
**Add:**
```python
import shutil
if not shutil.which("yt-dlp"):
    print("[!] yt-dlp not found. Install with: pip install yt-dlp")
    sys.exit(1)
```
**Done when:** Running without yt-dlp installed produces clear install instruction.

---

### Task 10: Add Timeout to Bridge Subprocess
**File:** `scripts/bridge.py`
**Location:** Line 20-25
**Current:**
```python
result = subprocess.run(
    ["ollama", "run", OLLAMA_MODEL, prompt],
    capture_output=True,
    text=True,
    check=True
)
```
**Replace with:**
```python
result = subprocess.run(
    ["ollama", "run", OLLAMA_MODEL, prompt],
    capture_output=True,
    text=True,
    check=True,
    timeout=300
)
```
**Done when:** Hanging Ollama process is killed after 5 minutes instead of running forever.

---

## 7. Task Dependency Graph & Execution Order

### Phase 1: Parallel (No Dependencies)
These can be done simultaneously:

```
┌─────────────────────────────────────────────────────────────┐
│  Task 2: Fix bare except                                    │
│  Task 7: Delete healer.py                                   │
│  Task 9: Add yt-dlp check                                   │
│  Task 10: Add subprocess timeout                            │
└─────────────────────────────────────────────────────────────┘
```

### Phase 2: Sequential (Depends on Phase 1)
Must be done in order:

```
Task 1: Create config.py
    │
    ▼
Task 5: Use config in bridge.py (requires config.py to exist)
    │
    ▼
Task 4: Add Ollama health check (should use config.py's OLLAMA_URL)
```

### Phase 3: Parallel (Depends on Phase 2)
Can be done simultaneously after config exists:

```
┌─────────────────────────────────────────────────────────────┐
│  Task 3: Fix SRT selection                                  │
│  Task 6: Add JSON validation                                │
│  Task 8: Namespace temp directory                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Final Note

The fundamental problem isn't the bugs—those are fixable. The problem is **design philosophy**. This codebase treats LLM output as trustworthy, external services as always-available, and configuration as something to hardcode. Until that philosophy changes, every fix is a patch on a sinking ship.

The Healer must die. The Bridge needs a complete rewrite with proper JSON mode and schema validation. The Librarian is salvageable but needs its global state eliminated.

You have the architecture of a distributed system (multiple scripts, external services, cross-project dependencies) with the error handling of a Jupyter notebook. Pick one.

---

*Review complete. No encouragement given. Ship it or delete it.*
