# TODO: YouTube Channel Analysis Agent

## ✅ Phase 1: The Librarian (Knowledge Extraction)
- [x] Build `scripts/librarian.py` (Refactored for High-Detail & SRT)
- [x] Implement SRT cleaning & metadata extraction (view_count, duration, etc.)
- [x] Integrate local Ollama (DeepSeek-R1) and long-context optimization
- [x] Establish `library/` directory with standardized Markdown templates

## ✅ Phase 2: Knowledge Accumulation (Operational)
- [x] Process initial `VIDEOS_QUEUE.md` priority items (Queue Cleared)
- [x] Automate "Skill Library Additions" section in every ingestion
- [x] Refine extraction prompts for high "Architectural Pattern" density
- [x] Automated indexing system (`library/00_Index_Library.md`)

## ✅ Phase 3: Advanced Orchestration & Experiments

### 1. "Skill Healer" Automation (`scripts/healer.py`)
- [x] Build initial prototype of `scripts/healer.py`

### 2. Multi-Channel Strategy Synthesis (`scripts/synthesize.py`)
- [x] Build synthesis engine to "distill the distillations"

### 3. Establish Research-to-Production "Bridge" (`scripts/bridge.py`)
- [x] Build `scripts/bridge.py` prototype with utility evaluation (DeepSeek-R1)
- [x] Implement logic to promote skills to global `/agent-skills-library/`

### 4. Production Integration: The "Top 5" Build-Out

#### 1. **Spec-Driven Developer** (PROMOTED ✅)
- **Objective:** Force agents to generate Specs and Tests before Code.
- **Implementation:** Integrated into `/agent-skills-library/`.

#### 2. **Technical Diagrammer**
- **Objective:** Auto-generate architectural and workflow diagrams from research reports.
- **Done Definition:** A skill that parses a "Master Strategy" document and outputs a valid Mermaid.js or D3 diagram representing the architecture.
- **Implementation:** `bridge.py --skill "Technical Diagrammer"`. Uses DeepSeek-R1 to map textual relationships to Mermaid syntax.

#### 3. **First-Principles Red Teamer**
- **Objective:** Challenge and refine strategy by identifying hidden assumptions and failure modes.
- **Done Definition:** A reasoning framework that generates a "Critical Analysis" section in every Synthesis report, stress-testing the "Common Truths."
- **Implementation:** A specialized `synthesis` prompt variant that plays "Devil's Advocate" against the extracted patterns.

#### 4. **CLI Wrapper Generator**
- **Objective:** Convert manual analysis scripts into structured CLI tools for the agent to use deterministically.
- **Done Definition:** A script that reads a prototype script (e.g., a one-off parser) and wraps it in `argparse` with standardized JSON output.
- **Implementation:** A "Meta-Script" that uses AST parsing to wrap logic in a CLI interface.

#### 5. **Contextual Historian**
- **Objective:** Maintain a persistent, searchable log of project-specific "lessons learned" to prevent repeating errors.
- **Done Definition:** A system that automatically appends a "Pattern Learned" entry to a local history file after every successful Bridge promotion.
- **Implementation:** A hook in `bridge.py` that writes to `library/00_HISTORY.md`.

## 🛡️ Phase 4: Industrial-Grade Hardening (Post-Review)

- [ ] **Flat Root Transition:** Move contents of `Documents/core/` to `Documents/` root and delete the core directory.
- [ ] **[CRITICAL] DNA Repair:** Replace absolute paths in `.cursorrules` with relative or parameterized references.
- [ ] **[SECURITY] Dependency Pinning:** Update `requirements.txt` with specific versions.
- [ ] **[STABILITY] Robust Indexing:** Refactor `scripts/librarian.py` to use structured data for index updates instead of string splits.
- [ ] **[SCALE] Synthesis Map-Reduce:** Implement a tiered aggregation strategy in `scripts/synthesize.py` for large libraries.
- [ ] **[QUALITY] Type Hardening:** Add complete type hints to `scripts/bridge.py` and `scripts/librarian.py`.


<!-- project-scaffolding template appended -->

# {{PROJECT_NAME}} - TODO

**Last Updated:** {{DATE}}  
**Project Status:** {{STATUS}} (In Progress/Active/Development/Paused/Stalled/Complete)  
**Current Phase:** {{PHASE}} (Foundation/MVP/Production/etc.)

---

## 📍 Current State

### What's Working ✅
<!-- List what's operational and tested -->
- **Feature 1:** Brief description of what works
- **Feature 2:** Another working component
- **Automation:** Any scheduled jobs or automated processes

### What's Missing ❌
<!-- Honest assessment of gaps -->
- **Feature X:** Not implemented yet
- **Integration Y:** Needs setup
- **Documentation Z:** Incomplete

### Blockers & Dependencies
<!-- What's stopping progress? -->
- ⛔ **Blocker:** Clear description of what blocks progress
- 🔗 **Dependency:** External service, API key, or approval needed
- ⏳ **Waiting:** What you're waiting for

---

## ✅ Completed Tasks

### Phase {{PHASE_NUMBER}}: {{PHASE_NAME}} ({{DATE_RANGE}})
- [x] Task description with clear outcome
- [x] Another completed task
- [x] Task that was finished

### Phase {{PREVIOUS_PHASE}}: {{PHASE_NAME}} ({{DATE_RANGE}})
- [x] Historical completed task
- [x] Another past milestone

---

## 📋 Pending Tasks

### Phase 0: Industrial Hardening (Gate 0)
- [ ] **Dependency Pinning:** Replace `>=` with `~=` or `==` in `requirements.txt`.
- [ ] **DNA Check:** Verify zero machine-specific absolute paths remain in codebase.
- [ ] **Error Audit:** Replace `except: pass` with explicit logging.
- [ ] **Subprocess Audit:** Ensure all CLI calls have `check=True` and `timeout`.

### 🔴 CRITICAL - Must Do First
<!-- High-priority, blocking other work -->

#### Task Group 1: {{TASK_GROUP_NAME}}
- [ ] Specific actionable task
- [ ] Another task with clear success criteria
- [ ] Task that depends on previous tasks

#### Task Group 2: {{TASK_GROUP_NAME}}
- [ ] Task description
  - [ ] Sub-task (if needed)
  - [ ] Another sub-task

---

### 🟡 HIGH PRIORITY - Important
<!-- Important but not blocking -->

#### Task Group 3: {{TASK_GROUP_NAME}}
- [ ] High-value task
- [ ] Another important task

---

### 🔵 MEDIUM PRIORITY - Nice to Have
<!-- Useful but can wait -->

#### Task Group 4: {{TASK_GROUP_NAME}}
- [ ] Enhancement or improvement
- [ ] Optional feature

---

### 🟢 LOW PRIORITY - Future
<!-- Backlog items, not urgent -->

#### Task Group 5: {{TASK_GROUP_NAME}}
- [ ] Long-term idea
- [ ] Nice-to-have feature

---

## 🎯 Success Criteria

### {{PHASE}} Complete When:
- [ ] Clear, measurable criterion
- [ ] Another specific goal
- [ ] Outcome that defines "done"

### Project Complete When:
- [ ] Final outcome achieved
- [ ] All core features working
- [ ] Documentation complete

---

## 📊 Notes

### AI Agents in Use
<!-- Which AI is helping with what? NEW SECTION -->
- **{{AI_NAME}} ({{MODEL}}):** Role description (e.g., "Implementation", "Code Review", "Architecture")
- **{{AI_NAME}}:** Another AI agent and its role

### Cron Jobs / Automation
<!-- Scheduled tasks for this project -->
- **Schedule:** `{{CRON_EXPRESSION}}` (e.g., "0 14 * * *" = daily 2 PM)
- **Command:** `{{COMMAND}}`
- **Purpose:** What it does
- **Status:** Active/Inactive

### External Services Used
<!-- From project-scaffolding/EXTERNAL_RESOURCES.md -->
- **{{SERVICE_NAME}}:** Purpose, cost
- **{{SERVICE_NAME}}:** Another service

### Cost Estimates
<!-- If applicable -->
- **Development:** Estimated time or cost
- **Monthly:** Recurring costs (API, hosting, etc.)
- **One-time:** Setup or infrastructure costs

### Time Estimates
<!-- Rough guidance -->
- **{{PHASE}}:** X-Y hours
- **Total project:** X-Y hours/weeks
- **Next milestone:** X hours

### Related Projects & Documentation
<!-- Links to other relevant projects or docs -->
- **{{PROJECT_NAME}}:** How it relates
- **{{DOC_PATH}}:** Important reference document

### Technical Stack
<!-- Key technologies -->
- **Language:** Python 3.11+ / JavaScript / etc.
- **Framework:** FastAPI / React / etc.
- **Database:** SQLite / PostgreSQL / etc.
- **Deployment:** Railway / Local / etc.

### Key Decisions Made
<!-- Important choices for future reference -->
1. **Decision:** Rationale and date
2. **Decision:** Another key choice

### Open Questions
<!-- Unresolved items needing discussion -->
- ❓ Question that needs answering
- ❓ Choice that needs to be made

---

## 🔄 Change Log (Optional)

### {{DATE}} - {{PHASE_NAME}}
- Major milestone or significant change
- Another important update

### {{PREVIOUS_DATE}} - {{PREVIOUS_PHASE}}
- Historical change
- Past update

---

<!-- 
=============================================================================
GUIDANCE FOR AI SESSIONS:
=============================================================================

This TODO is designed to be both HUMAN and AI readable.

When updating this file:
1. Always update "Last Updated" date at the top
2. Move completed tasks from Pending → Completed (keep the checkbox [x])
3. Add dates to completed phases
4. Update "Current State" section as project evolves
5. Keep Blockers section honest and current
6. Mark tasks as [x] when done, don't delete them (shows progress)
7. Update Success Criteria as understanding improves
8. Keep Notes section current (costs, time, related projects)

When reading this file at session start:
1. Read "Current State" first (understand where things are)
2. Check "Blockers & Dependencies" (know what's stopping progress)
3. Review "Pending Tasks" (understand what's next)
4. Check "Success Criteria" (know what "done" looks like)
5. Scan "Notes" for context (costs, related projects, decisions)

Priority Emojis:
- 🔴 CRITICAL: Must do first, blocking other work
- 🟡 HIGH: Important but not blocking
- 🔵 MEDIUM: Nice to have, can wait
- 🟢 LOW: Backlog, future consideration

Task Status:
- [ ] Not started
- [x] Completed (never delete, shows progress!)

Formatting:
- Use clear hierarchy (Phase → Task Group → Task → Sub-task)
- Keep task descriptions actionable ("Create X", not "X needs creating")
- Include enough context for a new AI session to understand

Meta-Philosophy:
- This is a living document
- Honest assessment > optimistic projection
- Show progress (keep completed tasks)
- Context for future you/AI (notes, decisions, questions)

=============================================================================
-->

---

*Template Version: 1.0*  
*Last Modified: December 30, 2025*  
*Source: ./templates/TODO.md.template*


<!-- project-scaffolding template appended -->

## Related Documentation

- [[CODE_REVIEW_ANTI_PATTERNS]] - code review
- [[DOPPLER_SECRETS_MANAGEMENT]] - secrets management
- [[LOCAL_MODEL_LEARNINGS]] - local AI
- [[PROJECT_STRUCTURE_STANDARDS]] - project structure
- [[architecture_patterns]] - architecture
- [[automation_patterns]] - automation
- [[cost_management]] - cost management
- [[dashboard_architecture]] - dashboard/UI
- [[database_setup]] - database
- [[error_handling_patterns]] - error handling
- [[prompt_engineering_guide]] - prompt engineering
- [[queue_processing_guide]] - queue/workflow
- [[deployment_patterns]] - deployment
- [[performance_optimization]] - performance
- [[project_planning]] - planning/roadmap
- [[research_methodology]] - research
- [[security_patterns]] - security
- [[testing_strategy]] - testing/QA
- [[video_analysis_tools]] - video analysis
- [[agent-skills-library/README]] - Agent Skills
- [[analyze-youtube-videos/README]] - YouTube Analyzer
- [[project-scaffolding/README]] - Project Scaffolding
