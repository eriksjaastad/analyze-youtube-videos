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

- **Ecosystem Standards**: `Documents/REVIEWS_AND_GOVERNANCE_PROTOCOL.md`
- **Methodology**: `Documents/core/YouTube_Analysis_Methodology.md`
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

- [[DOPPLER_SECRETS_MANAGEMENT]] - secrets management
- [[LOCAL_MODEL_LEARNINGS]] - local AI
- [[PROJECT_STRUCTURE_STANDARDS]] - project structure
- [[architecture_patterns]] - architecture
- [[queue_processing_guide]] - queue/workflow
- [[testing_strategy]] - testing/QA
- [[video_analysis_tools]] - video analysis
- [[agent-skills-library/README]] - Agent Skills
- [[analyze-youtube-videos/README]] - YouTube Analyzer
- [[project-scaffolding/README]] - Project Scaffolding
- [[CODE_REVIEW_ANTI_PATTERNS]] - code review
- [[ai_model_comparison]] - AI models
- [[research_methodology]] - research
- [[cost_management]] - cost management
- [[adult_business_compliance]] - adult industry
- [[security_patterns]] - security

<!-- project-scaffolding template appended -->

# [PROJECT_NAME]

[Brief 2-3 sentence description of the project.]

## Quick Start

### Installation
```bash
# [Add installation steps here]
```

### Usage
```bash
# [Add usage steps here]
```

## Documentation
See the `Documents/` directory for detailed documentation:
- [Architecture Overview](Documents/ARCHITECTURE_OVERVIEW.md)
- [Operations Guide](Documents/OPERATIONS_GUIDE.md)

## Development Resources
- [[analyze-youtube-videos/tests/__init__.py|__init__.py]]
- [[analyze-youtube-videos/scripts/warden_audit.py|warden_audit.py]]

## Status
- **Current Phase:** [Phase Name]
- **Status:** #status/active
