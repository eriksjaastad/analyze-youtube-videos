# Antigravity Rules for analyze-youtube-videos

<!-- AUTO-GENERATED from .agentsync/rules/ - Do not edit directly -->
<!-- Run: uv run $TOOLS_ROOT/agentsync/sync_rules.py analyze-youtube-videos -->

# Agents in analyze-youtube-videos

This project utilizes several specialized roles implemented as **autonomous scripts** (Workers), orchestrated to analyze and synthesize YouTube content.

> **Note on Indexing**: The *Worker Agents* manage internal data indices (like `library/index.yaml`). The *Floor Manager* (Claude/Cursor) is responsible for maintaining the high-level **Project Index** (`00_Index_*.md`) per `CLAUDE.md` standards.

## 1. The Librarian (scripts/librarian.py)
**Role**: Knowledge Extraction & Organization
**Function**: 
- Downloads YouTube transcripts using `yt-dlp`.
- Cleans and formats transcripts for LLM processing.
- Performs deep-dive analysis of individual videos.
- Manages the `library/index.yaml` source of truth and renders the library index.

## 2. The Strategist (scripts/synthesize.py)
**Role**: Strategic Synthesis
**Function**: 
- Aggregates multiple reports from the library.
- Synthesizes findings into a "Master Strategy" document.
- Identifies patterns, contradictions, and "Common Truths".
- Manages context limits via document summarization.

## 3. The Bridge (scripts/bridge.py)
**Role**: Skill Promotion
**Function**: 
- Evaluates potential skills for promotion to the global `agent-skills-library`.
- Generates Claude Adapters, Cursor Rules, and Playbooks for new skills.
