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

## 🔄 Ongoing / Maintenance
- [ ] **YouTube-to-Skill Pipeline:** Integrate with the `agent-skills-library`. Build an automated workflow where extracted "Actionable Skills" from transcripts are formatted into standard `.md` skill templates and proposed for the library.
- [ ] Ingest new URLs as they appear in the queue
- [ ] Monitor model performance on long transcripts (M4 Pro memory check)
