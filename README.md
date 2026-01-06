# YouTube Analysis Agent

> **Agent + Skill Combination**

This directory contains an autonomous agent that analyzes YouTube videos and channels, using skills from the agent-skills-library.

---

## Architecture

This agent is composed of:

1. **Agent-Specific Rules** (this directory)
   - Agent configuration
   - YouTube-specific workflows
   - Data processing logic
   - Output formatting

2. **Reusable Skills** (references agent-skills-library)
   - Content analysis skill → `agent-skills-library/playbooks/content-analysis/`
   - Pattern detection skill → `agent-skills-library/playbooks/pattern-detection/`
   - Report generation skill → `agent-skills-library/playbooks/report-generation/`

---

## Pattern: Agent vs. Skill

**Agent (this directory):**
- Has a specific job: "Analyze YouTube content"
- Combines multiple skills
- Has specific inputs/outputs
- May have state/memory
- Lives in its own directory

**Skill (in agent-skills-library):**
- Reusable capability: "Analyze patterns in content"
- Tool-agnostic instructions
- Can be used by many agents
- Lives in skills library

**Analogy:** 
- **Agent** = Employee with a specific job
- **Skills** = Capabilities that employee uses

---

## Current Status

### Existing Content:
- `Nick Saraev/transcript.en.vtt` - Example transcript
- `Nick Saraev/YouTube_Analysis_Methodology.md` - Analysis approach

### To Be Developed:

**Phase 1: Extract Skills**
- [ ] Identify reusable analysis patterns
- [ ] Create playbooks in agent-skills-library:
  - [ ] `playbooks/video-content-analysis/`
  - [ ] `playbooks/engagement-pattern-detection/`
  - [ ] `playbooks/content-idea-generation/`

**Phase 2: Build Agent**
- [ ] Agent configuration (YAML/JSON)
- [ ] YouTube-specific workflows
- [ ] Reference skills from library
- [ ] Input/output handling

**Phase 3: Test & Iterate**
- [ ] Test with multiple channels
- [ ] Refine skills based on results
- [ ] Version skills properly

---

## When to Use This Agent

**Use this agent when:**
- Analyzing YouTube channels for content patterns
- Generating video ideas based on successful content
- Understanding engagement patterns
- Competitive content analysis

**Don't use this agent for:**
- General content analysis (use the skills directly)
- Non-YouTube content (adapt or create different agent)

---

## Example Workflow

```
User Request:
"Analyze Nick Saraev's channel for content patterns"

Agent Flow:
1. Load transcript/metadata
2. Apply content-analysis skill (from library)
3. Apply pattern-detection skill (from library)
4. Use YouTube-specific context
5. Apply report-generation skill (from library)
6. Output formatted analysis
```

---

## Directory Structure (Planned)

```
analyze-youtube-videos/
├── README.md                    ← You are here
├── agent-config.yaml            ← Agent configuration
├── workflows/
│   ├── channel-analysis.md
│   └── video-comparison.md
├── data/                        ← Input data
│   └── Nick Saraev/
│       ├── transcript.en.vtt
│       └── YouTube_Analysis_Methodology.md
└── outputs/                     ← Generated reports
    └── [analysis results]
```

---

## Related

- **Skills Library:** `/agent-skills-library/` - Reusable analysis skills
- **AI Training Lab:** `/AI agent training lab/` - Agent orchestration testing

---

*Created: December 29, 2024*  
*Status: Planning phase - skills need to be extracted to library first*

