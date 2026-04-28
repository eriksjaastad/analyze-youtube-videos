---
name: youtube-channel-analysis
description: Systematic analysis of YouTube channels using metadata and transcripts to understand content patterns, strategic positioning, and generate personalized video ideas.
---

# YouTube Channel Analysis

> **Adapter for:** `playbooks/youtube-channel-analysis/`  
> **Version:** 1.0.0  
> **Tool:** Claude (Code and Chat)

---

## Skill Overview

**Name:** YouTube Channel Analysis  
**Type:** Data Analysis + Content Strategy  
**Complexity:** Medium (2-3 hours)

**What this skill does:**  
Systematically analyzes YouTube channels using data (metadata + transcripts) to understand content patterns, strategic positioning, and generate personalized video ideas based on proven patterns.

**Canonical instructions:** `../../playbooks/youtube-channel-analysis/README.md`

---

## When to Activate This Skill

**User signals:**
- "Analyze [YouTube channel]"
- "Help me understand what works for [creator]"
- "Generate video ideas based on [successful channel]"
- "Reverse engineer [YouTuber's] strategy"
- "I want to research my competitors"

**Context requirements:**
- Target channel URL provided
- User's own niche/goals shared (for personalization)
- Optionally: Database path if data already collected

---

## Skill Activation Prompt

When user requests channel analysis, respond with:

```
I'll analyze [CHANNEL] using a systematic 4-stage pipeline:

**Phase 1: Descriptive Analytics** - What IS happening? (channel overview, growth, patterns)
**Phase 2: Pattern Recognition** - What patterns exist? (top performers, content evolution)
**Phase 3: Strategic Synthesis** - WHY does it work? (positioning, principles)
**Phase 4: Personalized Recommendations** - How can YOU apply this? (20+ video ideas)

Before we start, I need some context to personalize the recommendations:

1. **Your channel:** [URL or "starting fresh"]
2. **Your niche:** [What you focus on]
3. **Your expertise:** [Your unique background/angle]
4. **Your goals:** [Audience building / Monetization / Education / etc.]
5. **Data status:** Have you already downloaded the channel data with yt-dlp?

This context ensures I generate recommendations tailored to YOUR situation, not generic advice.
```

---

## Claude-Specific Workflow

### Phase 0: Data Collection (If Needed)

**If user hasn't collected data yet:**

```
To analyze [CHANNEL], we need to download metadata and transcripts (NOT videos).

Here's the setup:

1. **Install yt-dlp:**
   ```bash
   pip install yt-dlp
   ```

2. **Download channel data:**
   ```bash
   yt-dlp \
     --skip-download \
     --write-auto-sub \
     --write-info-json \
     --sub-format vtt \
     --output "data/%(uploader)s/%(title)s.%(ext)s" \
     [CHANNEL_URL]
   ```

3. **Create SQLite database:**
   I'll write a Python script to parse the downloaded metadata and create
   a structured database for analysis.

Would you like me to create the data collection scripts?
Or have you already collected the data?
```

**If user has data:**

```
Great! Please provide the path to your SQLite database.

I'll verify the data structure and start the analysis.
```

### Phase 1: Analysis Planning

**Always create a plan first (for complex tasks):**

```markdown
# Analysis Plan: [CHANNEL]

## Context
- **Target channel:** [URL]
- **Your niche:** [User's niche]
- **Your goals:** [User's goals]
- **Videos to analyze:** [Count, if known]

## 4-Stage Pipeline

### Stage 1: Descriptive Analytics (30 min)
- [ ] Channel overview (total videos, date range, views)
- [ ] Growth trajectory by year/month
- [ ] Upload frequency patterns
- [ ] Output: `reports/01-descriptive-analytics.md`

### Stage 2: Pattern Recognition (45 min)
- [ ] Content evolution timeline
- [ ] Duration vs performance analysis
- [ ] Top 20 performer patterns
- [ ] Bottom 20 performer anti-patterns
- [ ] Content type correlation
- [ ] Output: `reports/02-pattern-recognition.md`

### Stage 3: Strategic Synthesis (30 min)
- [ ] Why patterns work (reasoning)
- [ ] Strategic positioning insights
- [ ] Reusable principles extraction
- [ ] Output: `reports/03-strategic-synthesis.md`

### Stage 4: Personalized Recommendations (45 min)
- [ ] Generate 20+ video ideas (adapted to your niche)
- [ ] Prioritization matrix (effort vs impact)
- [ ] 30/90/180-day content roadmap
- [ ] Output: `reports/04-content-roadmap.md`

### Optional: Deep Dive (30-60 min)
- [ ] Delivery style analysis (openings, teaching, transitions)
- [ ] Course structure patterns (if applicable)
- [ ] Output: `reports/05-delivery-style.md`

**Total estimated time:** 2-3 hours

---

Does this plan look good? Any adjustments before we start?
```

**Wait for user approval before proceeding.**

### Phase 2-5: Execute Analysis

**Follow the canonical playbook for each phase.**

**Key Claude behaviors:**

1. **Show SQL queries before running:**
   ```
   To find top performers, I'll query:
   
   ```sql
   SELECT title, view_count, duration, upload_date
   FROM videos
   ORDER BY view_count DESC
   LIMIT 20;
   ```
   
   This will show us the most successful videos.
   ```

2. **Present findings incrementally:**
   ```
   ✅ **Phase 1 Complete: Descriptive Analytics**
   
   ## Key Findings:
   - 252 videos analyzed
   - Active from 2020-01 to 2025-12
   - Peak period: April 2022 (32 uploads)
   - Growth: 45K views (2020) → 6.8M views (2022)
   
   ## Strategic Observation:
   The 2022 pivot to [Topic Y] coincided with explosive growth.
   
   📄 Full report saved: `reports/01-descriptive-analytics.md`
   
   ---
   
   Ready to proceed to Phase 2 (Pattern Recognition)?
   Or would you like to explore any Phase 1 findings deeper?
   ```

3. **Synthesize insights (not just data dumps):**
   ```
   ## Pattern Found: Long-form Courses Outperform
   
   **Data:**
   - Videos 3+ hours: Avg 250K views
   - Videos <15 min: Avg 35K views
   - Top 5 videos are all 3-6 hour courses
   
   **Why this works:**
   - YouTube algorithm rewards watch time
   - High perceived value ("complete course")
   - Searchable for specific tools
   - Positions creator as authority
   
   **Implication for you:**
   Consider creating [Your Niche] comprehensive course (3-5 hours)
   rather than competing in saturated "quick tips" space.
   ```

4. **Personalize Phase 4 recommendations:**
   ```
   # Video Idea #3: [Tool X] Full Course - Zero to Pro
   
   **Why this will work for YOU:**
   - Applying Nick's "mega course" pattern (3-6 hours = high views)
   - [Tool X] is new, no definitive course exists yet
   - Your [specific expertise] gives unique angle
   
   **Your differentiation:**
   Unlike generic tutorials, you can show [specific application]
   to [your target audience].
   
   **Title suggestion:** "[Tool X] Complete Course - [Transformation] in [Timeframe]"
   **Length:** 4-5 hours
   **Chapters:** 10-12 comprehensive sections
   **Monetization hook:** "[Outcome] without [pain point]"
   
   **Prerequisites to create this:**
   - 20+ hours of examples to record
   - Chapter structure mapped out
   - Test audience for feedback
   
   **Effort:** High | **Impact:** High | **Priority:** Q1 2026
   ```

---

## Output Format for Claude

### Report Structure

Each phase generates a markdown report:

```markdown
# [Phase Name]: [Channel Name]

> **Analysis Date:** December 30, 2025  
> **Analyzed by:** [User] with Claude assistance  
> **Channel:** [URL]  
> **Videos analyzed:** [Count]

---

## Executive Summary

[2-3 sentences: most important findings]

---

## Detailed Analysis

[Phase-specific content with headings, tables, lists]

### Finding 1: [Title]

**Data:** [Numbers, patterns, queries]

**Insight:** [What this means]

**Implication:** [How to use this]

---

### Finding 2: [Title]

...

---

## Key Takeaways

1. [Most important insight]
2. [Second most important insight]
3. [Third most important insight]

---

## Recommendations

[If applicable - especially in Phase 4]

---

## Next Steps

[What to do with this information]

---

*Generated using youtube-channel-analysis skill v1.0.0*  
*Analyzed by Claude Sonnet 4.5*
```

### Markdown Formatting Best Practices

- **Tables for comparisons:**
  ```markdown
  | Year | Videos | Avg Views | Top Topic |
  |------|--------|-----------|-----------|
  | 2021 | 48     | 25K       | Tool X    |
  | 2022 | 96     | 70K       | Tool Y    |
  ```

- **Code blocks for SQL:**
  ```sql
  SELECT title, view_count 
  FROM videos 
  WHERE duration > 10800  -- 3+ hours
  ORDER BY view_count DESC;
  ```

- **Lists for patterns:**
  - Pattern 1: [Description]
  - Pattern 2: [Description]

- **Blockquotes for key insights:**
  > **Key Insight:** The 2022 pivot to Tool Y resulted in 3x growth in average views.

---

## Claude Code-Specific Features

When using **Claude Code** (not just Chat):

1. **Write Python scripts for analysis:**
   ```python
   # analyze_channel.py
   import sqlite3
   import pandas as pd
   
   def analyze_top_performers(db_path):
       conn = sqlite3.connect(db_path)
       query = """
           SELECT title, view_count, duration, upload_date
           FROM videos
           ORDER BY view_count DESC
           LIMIT 20
       """
       df = pd.read_sql_query(query, conn)
       return df
   ```

2. **Create data visualization:**
   ```python
   # Simple text-based chart for terminal
   def print_chart(data, label):
       max_val = max(data.values())
       for key, value in data.items():
           bar = '█' * int((value / max_val) * 50)
           print(f"{key:10} {bar} {value}")
   ```

3. **Automate report generation:**
   ```python
   # generate_report.py
   def generate_markdown_report(findings, output_path):
       with open(output_path, 'w') as f:
           f.write(f"# Analysis Report\n\n")
           for section, content in findings.items():
               f.write(f"## {section}\n\n")
               f.write(f"{content}\n\n")
   ```

4. **Run the full pipeline:**
   Create a script that runs all 4 phases automatically:
   ```python
   # run_full_analysis.py
   from analyze_channel import *
   
   def main(db_path, user_context):
       # Phase 1
       desc_analytics = run_descriptive_analytics(db_path)
       save_report(desc_analytics, 'reports/01-descriptive-analytics.md')
       
       # Phase 2
       patterns = run_pattern_recognition(db_path)
       save_report(patterns, 'reports/02-pattern-recognition.md')
       
       # Phase 3
       synthesis = synthesize_insights(patterns, user_context)
       save_report(synthesis, 'reports/03-strategic-synthesis.md')
       
       # Phase 4
       recommendations = generate_recommendations(synthesis, user_context)
       save_report(recommendations, 'reports/04-content-roadmap.md')
   ```

---

## Constraints and Formatting

### Output Constraints

- ✅ Generate complete, actionable reports
- ✅ Use markdown formatting consistently
- ✅ Include SQL queries in code blocks
- ✅ Provide specific, personalized recommendations
- ✅ Save each phase as separate file

- ❌ Don't just dump data without insights
- ❌ Don't skip the synthesis (WHY things work)
- ❌ Don't give generic advice (personalize to user)
- ❌ Don't analyze more than necessary (focus on actionable)

### Tone and Style

- **Professional but accessible** - Explain technical terms
- **Data-driven** - Back insights with numbers
- **Actionable** - Always include "what to do with this"
- **Personalized** - Reference user's specific context
- **Encouraging** - Frame findings as opportunities

### Example Tone:

Good:
> "Based on the data, long-form courses (3+ hours) average 250K views, while short videos average 35K. For your [niche], this suggests creating comprehensive tutorials could 7x your reach. Your [expertise] makes you uniquely positioned to create '[Topic] Complete Course' - this could be your breakout content."

Bad:
> "Long videos get more views. You should make long videos."

---

## Common User Follow-ups

### "Can we analyze another channel for comparison?"

```
Absolutely! Comparing multiple channels reveals universal patterns vs 
channel-specific quirks.

Who should we analyze next? 
- Another competitor in the same niche?
- A successful creator in an adjacent niche?
- An aspirational channel you want to learn from?

I'll run the same 4-stage analysis and then create a comparative report 
showing common patterns across both channels.
```

### "This is taking too long, can we skip to recommendations?"

```
I understand the time pressure. However, recommendations without analysis 
often miss what makes patterns work in YOUR specific context.

Quick option: I can run a "Fast Track" analysis:
- Skip Phase 1 (descriptive) - you know the channel
- Quick Phase 2 (just top 10 performers)
- Brief Phase 3 (key insights only)
- Full Phase 4 (personalized recommendations)

Estimated time: 45 minutes instead of 2-3 hours.

Would that work better?
```

### "Why do you think [pattern] works?"

```
Great question! Let me break down the reasoning:

[Provide strategic synthesis]

This is exactly what Phase 3 (Strategic Synthesis) digs into.
```

### "How do I actually implement these ideas?"

```
Let's create an action plan for your top 3 ideas:

[For each idea]
## Idea: [Title]

**Next steps:**
1. [Concrete action]
2. [Concrete action]
3. [Concrete action]

**Timeline:** [Realistic estimate]
**Blockers:** [What might slow you down]
**Quick win:** [Simplest version to start]
```

---

## Best Practices for Claude

1. **Always provide context interpretation**
   - Don't just show data
   - Explain what it means
   - Connect to user's goals

2. **Make SQL queries educational**
   - Show the query
   - Explain what it does
   - Present results with insight

3. **Synthesize, don't just describe**
   - "The data shows X" → "The data shows X, which means Y, so you should consider Z"

4. **Personalize Phase 4 aggressively**
   - Every video idea should reference user's unique context
   - Explain WHY this idea fits them specifically

5. **Create actionable next steps**
   - End each report with "What to do with this"
   - Provide concrete actions, not vague suggestions

6. **Save work incrementally**
   - Generate reports after each phase
   - User can reference later
   - Builds a knowledge base

---

## Success Criteria

**This skill is successful when:**

- [ ] User understands what content works for the target channel (not just that it works, but WHY)
- [ ] User has 20+ specific video ideas tailored to their niche
- [ ] User can explain the strategic positioning of the target channel
- [ ] User has a prioritized content roadmap (30/90/180 days)
- [ ] Reports are saved and referenceable
- [ ] User feels confident about their content strategy
- [ ] Analysis took 2-3 hours (not days)

**Red flags (skill not working):**

- Generic recommendations that could apply to anyone
- Data dumps without insight
- No connection to user's specific context
- User still asking "but why does this work?"
- No actionable next steps

---

## Version History

**1.0.0** (December 30, 2025)
- Initial Claude adapter created
- Maps to playbook v1.0.0
- Includes Claude Code-specific Python scripting examples
- Tone and formatting guidelines defined

---

