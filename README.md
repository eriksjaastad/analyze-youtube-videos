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

## 🤖 Agents

This project utilizes several specialized roles implemented as **autonomous scripts** (Workers), orchestrated to analyze and synthesize YouTube content.

> **Note on Indexing**: The *Worker Agents* manage internal data indices (like `library/index.yaml`). The *Floor Manager* (Claude/Cursor) is responsible for maintaining the high-level **Project Index** (`00_Index_*.md`) per `CLAUDE.md` standards.

### 1. The Librarian (scripts/librarian.py)
**Role**: Knowledge Extraction & Organization
**Function**: 
- Downloads YouTube transcripts using `yt-dlp`.
- Cleans and formats transcripts for LLM processing.
- Performs deep-dive analysis of individual videos.
- Manages the `library/index.yaml` source of truth and renders the library index.

### 2. The Strategist (scripts/synthesize.py)
**Role**: Strategic Synthesis
**Function**: 
- Aggregates multiple reports from the library.
- Synthesizes findings into a "Master Strategy" document.
- Identifies patterns, contradictions, and "Common Truths".
- Manages context limits via document summarization.

### 3. The Bridge (scripts/bridge.py)
**Role**: Skill Promotion
**Function**: 
- Evaluates potential skills for promotion to the global `agent-skills-library`.
- Generates Claude Adapters, Cursor Rules, and Playbooks for new skills.

---

## 📂 Project Structure

```bash
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
doppler run -- python3 scripts/librarian.py "https://www.youtube.com/watch?v=..."
```
The Librarian downloads the transcript, cleans it, and uses local AI (DeepSeek-R1 via Ollama) to generate a deep-dive report in `library/`.

### Step 2: Synthesize Strategy
```bash
doppler run -- python3 scripts/synthesize.py --topic "AI Orchestration"
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

- **Ecosystem Standards**: `.agent/rules/governance.md`
- **Methodology**: `.agent/rules/YouTube_Analysis_Methodology.md`
- **Skills Library**: Configured via `SKILLS_LIBRARY_PATH` env var.

---
*Last Updated: January 2026*  
*Part of the eriksjaastad ecosystem.*

---

## Status

**Tags:** #map/project #p/analyze-youtube-videos  
**Status:** #status/complete  
**Last Major Update:** January 2026 (Gold Standard Certification)  
**Purpose:** Insight extraction and creator methodology research

## Recent Activity

- **2026-01-12**: **Gold Standard Certification Achieved**. All P0/P1 issues remediated.
- **2026-01-12**: Implemented industrial hardening (atomic writes, path traversal guards, subprocess timeouts).
- **2026-01-12**: Applied project-scaffolding v1.0.0 and established standalone portability.
- **2026-01-12**: Implemented the "Librarian" context-budget strategy with summarization fallbacks.
- **2026-01-10**: Initial Skill Library integration and "Bridge" agent implementation.

## Ecosystem Hardening
- `warden_audit.py` - Security and standards enforcement (Robotic Scan).
- `validate_project.py` - Structural compliance and DNA integrity verification.
- `pre_review_scan.sh` - Automated Gate 0 script for CI/CD readiness.
- `config.py` - Centralized configuration and health checks for local Ollama/DeepSeek models.

---

## Related Documentation

- [Doppler Secrets Management](../.agent/rules/DOPPLER_SECRETS_MANAGEMENT.md) - secrets management
- [Local Model Learnings](.agent/rules/local-model-learnings.md) - local AI
- [Agent Skills Library](../agent-skills-library/README.md) - Agent Skills
- [README](README) - YouTube Analyzer
- [Project Scaffolding](../project-scaffolding/README.md) - Project Scaffolding
- [Code Review Anti-Patterns](../.agent/rules/CODE_REVIEW_ANTI_PATTERNS.md) - code review
- [AI Model Cost Comparison](../.agent/rules/MODEL_COST_COMPARISON.md) - AI models
- [Cost Management](../.agent/rules/MODEL_COST_COMPARISON.md) - cost management
- [Safety Systems](patterns/safety-systems.md) - security
## CI / Automated Code Review

Pull requests are automatically reviewed by Claude Sonnet via a [centralized reusable workflow](https://github.com/eriksjaastad/tools/blob/main/.github/workflows/claude-review-reusable.yml) hosted in the `tools` repo.

**On every PR:**
- Tests run (if any exist)
- AI reviews the diff against project standards and governance protocol
- Posts a sticky review comment and a `claude-review` commit status
- Auto-merges on APPROVE, blocks on REQUEST_CHANGES

See [tools repo](https://github.com/eriksjaastad/tools) for configuration details.
