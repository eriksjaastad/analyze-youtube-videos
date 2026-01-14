# 📚 YouTube Analysis Agent

> **Status: Production Ready (Gold Standard Certified)**  
> **Scaffolding Version: 1.0.0**

Autonomous agent system for analyzing YouTube content and extracting strategic insights. This system follows the eriksjaastad industrial hardening standards and utilizes a tiered agent architecture to ingest, analyze, and synthesize video data.

---

## 🏗️ Architecture

This agent uses a specialized three-tier architecture:

1. **The Librarian (`scripts/librarian.py`)**: Responsible for data ingestion. It downloads transcripts, cleans data, and maintains the `library/` index.
2. **The Strategist (`scripts/synthesize.py`)**: Responsible for synthesis. It aggregates multiple library entries into a "Master Strategy" in the `synthesis/` directory.
3. **The Bridge (`scripts/bridge.py`)**: Responsible for skill promotion. It identifies high-value patterns and promotes them to the global `agent-skills-library`.

---

## 🛡️ Industrial Hardening

This project is certified under the **Gold Standard** governance protocol:
- **Atomic Writes**: All file modifications use temp-file-and-rename for crash safety.
- **Path Safety**: Strict traversal guards and `safe_slug` sanitization on all user-provided strings.
- **Subprocess Integrity**: All external calls (yt-dlp, ollama) have mandatory timeouts and non-zero exit code checks.
- **Safety-First Operations**: Uses `tempfile.TemporaryDirectory` for safe cleanup of temporary assets.

---

## 📂 Project Structure

```
analyze-youtube-videos/
├── scripts/                   ← Tier 1 Core Agents
│   ├── librarian.py           ← Data ingestion & cleaning
│   ├── synthesize.py          ← Strategy aggregation
│   └── bridge.py              ← Skill promotion
│   └── config.py              ← Centralized config & health checks
├── library/                   ← Knowledge Library
│   ├── 00_Index_Library.md    ← Knowledge Map
│   └── index.yaml             ← Source of Truth (YAML)
├── synthesis/                 ← Master Strategy Reports
├── tests/                     ← Unit tests & cleanup verification
├── requirements.txt           ← Pinned production dependencies
└── 00_Index_analyze-youtube-videos.md ← Project Index
```

---

## 🚀 Workflow

### Step 1: Ingest & Analyze
```bash
python3 scripts/librarian.py "https://www.youtube.com/watch?v=..."
```
The Librarian downloads the transcript, cleans it, and uses local AI (DeepSeek-R1 via Ollama) to generate a deep-dive report in `library/`.

### Step 2: Synthesize Strategy
```bash
python3 scripts/synthesize.py --topic "AI Orchestration"
```
The Strategist aggregates all relevant reports in the library into a cohesive "Master Strategy" document.

### Step 3: Promote Skills
```bash
python3 scripts/bridge.py --source synthesis/2026-01-12_ai-orchestration.md --skill "Pattern Detection"
```
The Bridge evaluates patterns and promotes them to the global skills library.

---

## 🧪 Testing

Run the full test suite to verify system integrity:
```bash
pytest tests/
```

Before committing or pushing, run the pre-review scan:
```bash
bash scripts/pre_review_scan.sh
```

---

## 📝 Related Documentation

- **Ecosystem Standards**: `Documents/REVIEWS_AND_GOVERNANCE_PROTOCOL.md`
- **Methodology**: `Documents/core/YouTube_Analysis_Methodology.md`
- **Skills Library**: Configured via `SKILLS_LIBRARY_PATH` env var.

---
*Last Updated: January 2026*  
*Part of the eriksjaastad ecosystem.*
