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

# analyze-youtube-videos

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
- **Anti-Gravity & Agentic Workflows**: specialized section for Vibe Coding and DOE framework research.
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
**Index:** 00_Index_analyze-youtube-videos

## Recent Activity

- **2026-01-20**: Analyzed **"The Claude Code Feature Senior Engineers KEEP MISSING"** by IndyDevDan. Extracted insights on self-validating agents via hooks.
- **2026-01-19**: Analyzed **"Use Local LLMs Already!"** by The Art of the Terminal. Extracted insights on private AI infrastructure.
- **2026-01-19**: Analyzed **"Making $$$ with AI SaaS"** by David Ondrej. Linked insights to the **Prospector** project.
- **2026-01-17**: **Anti-Gravity Deep-Dive Initiated**. Analyzed 3 new advanced tutorials and workflow guides (Mikey Itua, George Alonge, Nate B. Jones).
- **2026-01-17**: Established new **Anti-Gravity & Agentic Workflows** category in the knowledge library.
- **2026-01-16**: Analyzed **"Don't build AI Automations... Build Agentic Workflows"** by Duncan Rogoff (AI Automation).
- **2026-01-12**: **Gold Standard Certification Achieved**. All P0/P1 issues remediated.
- **2026-01-12**: Implemented industrial hardening (atomic writes, path traversal guards, subprocess timeouts).
- **2026-01-12**: Applied project-scaffolding v1.0.0 and established standalone portability.
- **2026-01-12**: Implemented the "Librarian" context-budget strategy with summarization fallbacks.
- **2026-01-10**: Initial Skill Library integration and "Bridge" agent implementation.

## Related Documentation

- [[LOCAL_MODEL_LEARNINGS]] - local AI
- [[PROJECT_STRUCTURE_STANDARDS]] - project structure
- [[architecture_patterns]] - architecture
- [[cost_management]] - cost management
- [[adult_business_compliance]] - adult industry
- [[research_methodology]] - research
- [[security_patterns]] - security
- [[video_analysis_tools]] - video analysis
- [[agent-skills-library/README]] - Agent Skills
- [[analyze-youtube-videos/README]] - YouTube Analyzer
- [[project-scaffolding/README]] - Project Scaffolding

<!-- LIBRARIAN-INDEX-START -->

### File Index

| File | Description |
| :--- | :--- |
| [[AGENTS.md]] | This project utilizes several specialized roles implemented as **autonomous scripts** (Workers), orc... |
| [[CLAUDE.md]] | Project Context |
| [[CODE_REVIEW_CLAUDE_OPUS_v3.md]] | CODE REVIEW: analyze-youtube-videos (v3 - Gold Standard Certification) |
| [[Documents/REVIEWS_AND_GOVERNANCE_PROTOCOL.md]] | 🛡️ Ecosystem Governance & Review Protocol (v1.2) |
| [[Documents/core/YouTube_Analysis_Methodology.md]] | Reverse Engineering YouTube Channels with Claude Code |
| [[Documents/patterns/code-review-standard.md]] | Code Review Standardization |
| [[Documents/patterns/learning-loop-pattern.md]] | Learning Loop Pattern |
| [[Documents/reference/LOCAL_MODEL_LEARNINGS.md]] | Local Model Learnings |
| [[Documents/reference/TEST_PROMPT.md]] | Test Prompt: YouTube Channel Analysis Skill |
| [[Documents/reference/TOOLS.md]] | Tool Installation Guide |
| [[README.md]] | 📚 YouTube Analysis Agent |
| [[TODO.md]] | This document outlines the remaining tasks and future development roadmap for the YouTube Channel An... |
| [[VIDEOS_QUEUE.md]] | Videos Queue |
| [[config/categories.yaml]] | No description available. |
| [[library/2025-10-21_Zen_van_Riel_The-Ultimate-Local-AI-Coding-Guide-For-2026.md]] | The Ultimate Local AI Coding Guide For 2026 |
| [[library/2025-12-02_george-alonge_antigraviy-rules-and-workflows_7tzgitax.md]] | [[Antigraviy Rules and Workflows]] |
| [[library/2025-12-03_AWS_Events_AWS-reInvent-2025-Building-Scalable-Self-Orchestra.md]] | AWS re:Invent 2025 - Building Scalable, Self-Orchestrating AI Workflows with A2A and MCP (DEV415) |
| [[library/2025-12-11_chromatic_agentic-design-systems-in-2026-with-brad_vg78k3t9.md]] | Agentic Design Systems in 2026 with Brad Frost |
| [[library/2025-12-16_Unsupervised_Learning_A-Deepdive-on-my-Personal-AI-Infrastructure-PAI-v2.md]] | A Deepdive on my Personal AI Infrastructure (PAI v2.0, December 2025) |
| [[library/2025-12-31_Renaissance_Periodization_I-Lost-Over-Half-My-Body-Fat-DOING-THIS.md]] | I Lost Over Half My Body Fat DOING THIS! |
| [[library/2026-01-03_Parker_Prompts_Give-me-9-Min-Become-Dangerously-Good-at-Gemini-30.md]] | Give me 9 Min, Become Dangerously Good at Gemini 3.0 Pro |
| [[library/2026-01-05_AI_Engineer_Claude-Agent-SDK-Full-Workshop-Thariq-Sh_TqC1qOfi.md]] | Claude Agent SDK [Full Workshop] — Thariq Shihipar, Anthropic |
| [[library/2026-01-05_Aniket_Panjwani_Claude-Code-Skills-vs-MCPs-Complete-Beginners-Guid.md]] | Claude Code Skills vs MCPs: Complete Beginner's Guide 2026 |
| [[library/2026-01-05_duncan-rogoff-ai-automation_dont-build-ai-automations-build-agentic-_7u6pkex9.md]] | [[DON'T build AI automations, build agentic workflows! (Google Antigravity)]] |
| [[library/2026-01-06_Aniket_Panjwani_The-Creator-of-Claude-Code-Shares-His-Exact-Setup.md]] | The Creator of Claude Code Shares His Exact Setup |
| [[library/2026-01-07_Aniket_Panjwani_The-Only-Claude-Code-Skill-You-Need_MMpaPV3K.md]] | The Only Claude Code Skill You Need |
| [[library/2026-01-08_the-art-of-the-terminal_use-local-llms-already_pfxglx-m.md]] | [[Use Local LLMs Already!]] |
| [[library/2026-01-09_ai-labs_claude-codes-creator-does-this-before-ev_b-uxpnek.md]] | Claude Code's Creator Does This Before Every Single Project |
| [[library/2026-01-14_mikey-itua_antigravity-advanced-tutorial-easy-tutor_-x0wvsud.md]] | [[Antigravity Advanced Tutorial Easy Tutorial]] |
| [[library/2026-01-16_ai-news-strategy-daily-nate-b-jones_stop-competing-with-400-applicants-build_0tezqotp.md]] | [[Stop Competing With 400 Applicants. Build This in One Weekend (Yes, there's a  no code option too!... |
| [[library/2026-01-17_david-ondrej_making-with-ai-saas-i-might-delete-this_ns62guax.md]] | [[Making $$$ with AI SaaS (I might delete this)]] |
| [[library/2026-01-19_indydevdan_the-claude-code-feature-senior-engineers_u5gkg71p.md]] | [[The Claude Code Feature Senior Engineers KEEP MISSING]] |
| [[library/index.yaml]] | No description available. |
| [[requirements.txt]] | No description available. |
| [[scripts/bridge.py]] | No description available. |
| [[scripts/config.py]] | No description available. |
| [[scripts/librarian.py]] | No description available. |
| [[scripts/pre_review_scan.sh]] | pre_review_scan.sh - Run before code reviews or commits |
| [[scripts/synthesize.py]] | No description available. |
| [[scripts/validate_project.py]] | No description available. |
| [[scripts/warden_audit.py]] | No description available. |
| [[synthesis/2026-01-06_AI_Orchestration_Patterns.md]] | Master Strategy: AI Orchestration Patterns |
| [[tests/test_bridge.py]] | No description available. |
| [[tests/test_config.py]] | No description available. |
| [[tests/test_librarian.py]] | No description available. |
| [[tests/test_synthesize.py]] | No description available. |

<!-- LIBRARIAN-INDEX-END -->