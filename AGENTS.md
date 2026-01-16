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



<!-- project-scaffolding template appended -->

# AGENTS.md - Source of Truth for AI Agents

## 🎯 Project Overview
{project_description}

## 🛠 Tech Stack
- Language: {language}
- Frameworks: {frameworks}
- AI Strategy: {ai_strategy}

## 📋 Definition of Done (DoD)
- [ ] Code is documented with type hints.
- [ ] Technical changes are logged to `project-tracker/data/WARDEN_LOG.yaml`.
- [ ] `00_Index_*.md` is updated with recent activity.
- [ ] Code validated (no hardcoded paths, no secrets exposed).
- [ ] Code review completed (if significant architectural changes).
- [ ] [Project-specific DoD item]

## 🚀 Execution Commands
- Environment: `{venv_activation}`
- Run: `{run_command}`
- Test: `{test_command}`

## ⚠️ Critical Constraints
- NEVER hard-code API keys, secrets, or credentials in script files. Use `.env` and `os.getenv()`.
- NEVER use absolute paths (e.g., machine-specific paths). ALWAYS use relative paths or `PROJECT_ROOT` env var.
- ALWAYS run validation before considering work complete: `python "./scripts/validate_project.py" [project-name]`
- {constraint_1}
- {constraint_2}

**Code Review Standards:** See `./REVIEWS_AND_GOVERNANCE_PROTOCOL.md` for full review process.

## 📖 Reference Links
- [[00_Index_{project_name}]]
- [[Project Philosophy]]


<!-- project-scaffolding template appended -->

## Related Documentation

- [[CODE_REVIEW_ANTI_PATTERNS]] - code review
- [[DOPPLER_SECRETS_MANAGEMENT]] - secrets management
- [[PROJECT_STRUCTURE_STANDARDS]] - project structure
- [[ai_model_comparison]] - AI models
- [[research_methodology]] - research
- [[video_analysis_tools]] - video analysis
- [[agent-skills-library/README]] - Agent Skills
- [[analyze-youtube-videos/README]] - YouTube Analyzer
- [[project-scaffolding/README]] - Project Scaffolding
