---
tags:
  - map/project
  - p/analyze-youtube-videos
  - type/agent
  - domain/content-analysis
  - tech/python
scaffolding_version: 1.0.0
status: #status/complete
created: 2026-01-02
---

# [[analyze-youtube-videos]]

Autonomous agent system for analyzing YouTube content and extracting strategic insights. This system utilizes a three-tier agent architecture (Librarian, Strategist, Bridge) to ingest video transcripts, synthesize topic-level strategies, and promote high-value patterns to a global skills library. It follows the eriksjaastad industrial hardening standards with atomic writes, path traversal guards, and safety-first file operations.

## Key Components

### Core Agents (scripts/)
- `librarian.py` - Knowledge Extraction & Organization. Downloads transcripts, cleans data, and manages the library index.
- `synthesize.py` - Strategic Synthesis. Aggregates library reports into Master Strategy documents with context budget management.
- `bridge.py` - Skill Promotion. Evaluates and promotes discovered patterns to the global `agent-skills-library`.

### Ecosystem Hardening
- `warden_audit.py` - Security and standards enforcement (Robotic Scan).
- `validate_project.py` - Structural compliance and DNA integrity verification.
- `pre_review_scan.sh` - Automated Gate 0 script for CI/CD readiness.
- `config.py` - Centralized configuration and health checks for local Ollama/DeepSeek models.

### Knowledge Library (library/)
- 10+ Deep-dive video analyses on AI architecture, coding workflows, and creator strategy.
- `00_Index_Library.md` - Rendered map of all analyzed content grouped by category.
- `index.yaml` - Machine-readable Source of Truth for the knowledge library.

### Strategic Synthesis (synthesis/)
- Master strategy reports consolidating cross-video insights.
- Context-aware summaries for scaling beyond LLM context limits.

## Status

**Tags:** #map/project #p/analyze-youtube-videos  
**Status:** #status/complete  
**Last Major Update:** January 2026 (Gold Standard Certification)  
**Purpose:** Insight extraction and creator methodology research
**Index:** [[00_Index_analyze-youtube-videos]]

## Recent Activity

- **2026-01-12**: **Gold Standard Certification Achieved**. All P0/P1 issues remediated.
- **2026-01-12**: Implemented industrial hardening (atomic writes, path traversal guards, subprocess timeouts).
- **2026-01-12**: Applied project-scaffolding v1.0.0 and established standalone portability.
- **2026-01-12**: Implemented the "Librarian" context-budget strategy with summarization fallbacks.
- **2026-01-10**: Initial Skill Library integration and "Bridge" agent implementation.
