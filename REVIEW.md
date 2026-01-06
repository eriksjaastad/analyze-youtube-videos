# CODE REVIEW: YouTube-to-Skill Pipeline (v2)

**Review Date:** 2026-01-06 20:55 UTC
**Reviewer:** Senior Principal Engineer (Systems Architecture)
**Previous Review:** 2026-01-06 20:51 UTC
**Commit Reviewed:** cedb58f

---

## 1. The Engineering Verdict

### **[Needs Major Refactor]** *(Upgraded from "Dangerous Wrapper")*

Credit where due: someone actually read the last review. The Healer is dead. There's a central config. Health checks exist. Temp directories are namespaced. This is no longer a ticking time bomb—it's now merely a minefield with some flags planted.

**But the #1 issue from the last review is still unfixed.** The hardcoded absolute path `/Users/eriksjaastad/projects/agent-skills-library` moved from `bridge.py` to `config.py`, where it's now a *centralized* landmine instead of a *scattered* one. Same explosion radius, different file. The subtitle selection logic will miss any non-standard language codes. And the `[REJECT]` string-matching control flow remains bypassable.

You've gone from "will definitely break" to "will probably break under specific conditions." Progress. Not victory.

---

## 2. What Was Fixed (Acknowledgment)

| Original Issue | Status | Evidence |
|----------------|--------|----------|
| healer.py (code corruption) | ✅ **FIXED** | File deleted |
| Configuration sprawl | ✅ **FIXED** | `scripts/config.py` centralizes constants |
| Bare `except: pass` | ✅ **FIXED** | `librarian.py:101-102` now catches `OSError` with message |
| No health checks | ✅ **FIXED** | `config.py:76-99` checks yt-dlp, ollama CLI, service responsiveness |
| Race condition in temp dir | ✅ **FIXED** | `config.py:51-54` uses SHA256 hash of URL for unique temp dirs |
| No subprocess timeout | ✅ **FIXED** | `config.py:35` adds timeout parameter (default 300s) |
| No JSON validation in bridge | ✅ **FIXED** | `config.py:67-74` validates required keys before write |
| Mixed Ollama invocation | ✅ **FIXED** | All scripts now use `run_ollama_command()` wrapper |

**Net improvement: 8 of 10 critical issues addressed.** That's a solid remediation pass.

---

## 3. What's Still Broken

### Critical: Hardcoded Absolute Path (UNFIXED)

**File:** `scripts/config.py:12`
```python
GLOBAL_LIBRARY_PATH = Path("/Users/eriksjaastad/projects/agent-skills-library")
```

**Problem:** This was Issue #1 in the last review. It's still here. Just moved files.

**Impact:** Bridge.py writes to this path. On any machine where this path doesn't exist:
- Linux server: Creates `/Users/eriksjaastad/projects/...` directory structure (if permissions allow)
- Docker container: Same orphan directory creation
- Collaborator's Mac: Writes to Erik's directory if it exists, fails silently if not

**Required Fix:**
```python
GLOBAL_LIBRARY_PATH = Path(os.getenv("SKILLS_LIBRARY_PATH", "./agent-skills-library"))
```

---

### High: Subtitle Selection Misses Variants

**File:** `scripts/config.py:56-65`
```python
def select_subtitle(filenames: list, base_name: str) -> str:
    manual_subtitle = f"{base_name}.en.srt"
    auto_subtitle = f"{base_name}.en.auto-subs.srt"

    if manual_subtitle in filenames:
        return manual_subtitle
    elif auto_subtitle in filenames:
        return auto_subtitle
    return None
```

**Problem:** yt-dlp generates variant filenames:
- `transcript.en-US.srt`
- `transcript.en-GB.srt`
- `transcript.en.vtt` (wrong format, but could exist)

This function only matches exact strings. If YouTube serves `en-US` subtitles, this returns `None` and the transcript is empty.

**Required Fix:**
```python
def select_subtitle(filenames: list, base_name: str) -> str:
    # Sort for determinism, prefer manual over auto
    srt_files = sorted([f for f in filenames if f.endswith('.srt')])
    manual = [f for f in srt_files if base_name in f and 'auto' not in f.lower()]
    auto = [f for f in srt_files if base_name in f and 'auto' in f.lower()]

    if manual:
        return manual[0]
    elif auto:
        return auto[0]
    elif srt_files:
        return srt_files[0]  # Fallback to any SRT
    return None
```

---

### Medium: String-Match Control Flow Still Bypassable

**File:** `scripts/bridge.py:147`
```python
if "[REJECT]" in evaluation and not args.dry_run:
```

**Problem:** LLM can output "I'm not going to [REJECT] this" and bypass the gate.

**Mitigation (not fix):** This is fundamentally unfixable without structured output. Either:
1. Remove the gate entirely (trust the human who ran the command)
2. Use Ollama's JSON mode with a schema
3. Parse the evaluation with a regex that requires `DECISION: [REJECT]` format

---

### Medium: Side Effects at Import Time

**File:** `scripts/config.py:101-103`
```python
# Initialize directories
for d in [LIBRARY_DIR, SYNTHESIS_DIR, TEMP_DIR]:
    os.makedirs(d, exist_ok=True)
```

**Problem:** This runs when `config.py` is imported, not when scripts execute. If you write a unit test that imports config, you create directories. If you import from a read-only filesystem, you crash.

**Required Fix:** Move to a function called explicitly by each script's `main()`:
```python
def initialize_directories():
    for d in [LIBRARY_DIR, SYNTHESIS_DIR, TEMP_DIR]:
        os.makedirs(d, exist_ok=True)
```

---

### Low: Inconsistent Import Placement

**File:** `scripts/config.py`
```python
# Line 1-4: imports at top
import os
import json
import subprocess
from pathlib import Path

# Line 38: import inside function
import re

# Line 49: import in middle of file (not inside function)
import hashlib

# Line 80: import inside function
import shutil
```

**Problem:** Scattered imports make dependencies unclear. `hashlib` is imported at module level between function definitions. `re` and `shutil` are imported inside functions (acceptable for optional deps, confusing here since they're always used).

**Required Fix:** Move all imports to top of file.

---

### Low: Orphan Directory Cleanup Missing

**File:** `scripts/librarian.py:103-106`
```python
try:
    os.rmdir(unique_temp)
except OSError:
    pass
```

**Problem:** If temp cleanup fails (non-empty dir), the unique temp directory stays forever. No logging.

**Improvement:**
```python
except OSError as e:
    print(f"[!] Could not remove temp directory {unique_temp}: {e}")
```

---

## 4. New Issues Introduced

### Issue: Health Check Catches Too Broadly

**File:** `scripts/config.py:93-97`
```python
try:
    subprocess.run(["ollama", "list"], capture_output=True, check=True, timeout=10)
except Exception:
    print("[!] Critical: Ollama CLI not responsive. Is the service running?")
    return False
```

**Problem:** `except Exception` catches everything including `KeyboardInterrupt`. If user hits Ctrl+C during health check, they get "Ollama CLI not responsive" instead of a clean exit.

**Required Fix:**
```python
except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
    print(f"[!] Critical: Ollama CLI not responsive: {e}")
    return False
```

---

### Issue: Duplicate cmd Assignment

**File:** `scripts/config.py:19-27`
```python
def run_ollama_command(prompt: str, system_prompt: str = None, timeout: int = 300) -> str:
    cmd = ["ollama", "run", OLLAMA_MODEL, prompt]  # Line 19: First assignment

    # ...
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

    cmd = ["ollama", "run", OLLAMA_MODEL, full_prompt]  # Line 27: Overwrites line 19
```

**Problem:** `cmd` is assigned twice. Line 19 is dead code.

**Required Fix:** Remove line 19.

---

## 5. Evidence-Based Critique (Updated)

| Issue | File:Line | Code Evidence | Status |
|-------|-----------|---------------|--------|
| Hardcoded user path | `config.py:12` | `Path("/Users/eriksjaastad/projects/agent-skills-library")` | ❌ UNFIXED |
| Subtitle selection misses variants | `config.py:56-65` | Only matches exact `.en.srt` or `.en.auto-subs.srt` | ❌ UNFIXED |
| String-match control flow | `bridge.py:147` | `if "[REJECT]" in evaluation` | ❌ UNFIXED |
| Side effects at import | `config.py:101-103` | `os.makedirs()` at module level | 🆕 NEW |
| Broad exception catch | `config.py:95` | `except Exception:` | 🆕 NEW |
| Dead code | `config.py:19` | First `cmd =` assignment overwritten | 🆕 NEW |
| Inconsistent imports | `config.py:38,49,80` | `import re/hashlib/shutil` scattered | 🆕 NEW |

---

## 6. Remediation Tasks (Remaining)

### Task 1: Environment Variable for Skills Library Path
**File:** `scripts/config.py`
**Location:** Line 12
**Current:**
```python
GLOBAL_LIBRARY_PATH = Path("/Users/eriksjaastad/projects/agent-skills-library")
```
**Replace with:**
```python
GLOBAL_LIBRARY_PATH = Path(os.getenv("SKILLS_LIBRARY_PATH", "./agent-skills-library"))
```
**Done when:** `SKILLS_LIBRARY_PATH=/tmp/test python -c "from scripts.config import GLOBAL_LIBRARY_PATH; print(GLOBAL_LIBRARY_PATH)"` prints `/tmp/test`

---

### Task 2: Fix Subtitle Selection for Variants
**File:** `scripts/config.py`
**Location:** Lines 56-65
**Replace entire function with:**
```python
def select_subtitle(filenames: list, base_name: str) -> str:
    """Select subtitle file, handling locale variants like en-US, en-GB."""
    srt_files = sorted([f for f in filenames if f.endswith('.srt') and base_name in f])
    manual = [f for f in srt_files if 'auto' not in f.lower()]
    auto = [f for f in srt_files if 'auto' in f.lower()]

    return manual[0] if manual else (auto[0] if auto else None)
```
**Done when:** Function returns correct file for `["transcript.en-US.srt"]` input

---

### Task 3: Remove Dead Code
**File:** `scripts/config.py`
**Location:** Line 19
**Delete:**
```python
cmd = ["ollama", "run", OLLAMA_MODEL, prompt]
```
**Done when:** Only one `cmd =` assignment exists in `run_ollama_command()`

---

### Task 4: Move Directory Init to Function
**File:** `scripts/config.py`
**Location:** Lines 101-103
**Current:**
```python
for d in [LIBRARY_DIR, SYNTHESIS_DIR, TEMP_DIR]:
    os.makedirs(d, exist_ok=True)
```
**Replace with:**
```python
def initialize_directories():
    """Create required directories. Call from main() only."""
    for d in [LIBRARY_DIR, SYNTHESIS_DIR, TEMP_DIR]:
        os.makedirs(d, exist_ok=True)
```
**Then:** Add `initialize_directories()` call to each script's `main()` function
**Done when:** Importing config.py doesn't create directories

---

### Task 5: Consolidate Imports
**File:** `scripts/config.py`
**Location:** Top of file
**Move all imports to top:**
```python
import os
import json
import re
import hashlib
import shutil
import subprocess
from pathlib import Path
```
**Remove:** Lines 38, 49, 80 (inline imports)
**Done when:** No `import` statements appear after line 10

---

### Task 6: Narrow Exception Catch in Health Check
**File:** `scripts/config.py`
**Location:** Lines 93-97
**Current:**
```python
except Exception:
```
**Replace with:**
```python
except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
    print(f"[!] Critical: Ollama CLI check failed: {e}")
    return False
```
**Done when:** Ctrl+C during health check raises KeyboardInterrupt properly

---

## 7. Task Dependency Graph

### Phase 1: Parallel (Independent)
```
┌─────────────────────────────────────────────────────────────┐
│  Task 1: Environment variable for GLOBAL_LIBRARY_PATH       │
│  Task 2: Fix subtitle selection                             │
│  Task 3: Remove dead code                                   │
│  Task 5: Consolidate imports                                │
│  Task 6: Narrow exception catch                             │
└─────────────────────────────────────────────────────────────┘
```

### Phase 2: Sequential (Depends on Phase 1)
```
Task 4: Move directory init to function
    │
    ▼
Update librarian.py, bridge.py, synthesize.py main() to call initialize_directories()
```

---

## 8. Final Assessment

**Progress made:** You fixed 8 of 10 issues from the first review. The codebase moved from "dangerous" to "fragile." That's real progress.

**Remaining risk:** The hardcoded path is still the critical blocker for any use outside your specific machine. Fix that first. Everything else is polish.

**Verdict change:** Upgraded from **[Dangerous Wrapper]** to **[Needs Major Refactor]** because:
1. No more auto-corruption of source code (healer dead)
2. Health checks prevent silent failures
3. Race conditions eliminated
4. Proper error handling in most places

**What blocks [Production Ready]:**
1. Hardcoded absolute path (must use env var)
2. Subtitle selection too strict
3. Import-time side effects

Fix those three and you have something deployable.

---

*Review complete. Progress acknowledged. Finish the job.*
