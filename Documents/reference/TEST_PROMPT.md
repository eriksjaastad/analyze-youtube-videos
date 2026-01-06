# Test Prompt: YouTube Channel Analysis Skill

> **Use this prompt to test the agent-skills-library integration**  
> **Model:** Claude Sonnet 4.5 (or current Cursor model)  
> **Project:** analyze-youtube-videos

---

## The Test Prompt

Copy/paste this into a fresh Cursor chat in the `analyze-youtube-videos` directory:

```
I want to test the YouTube Channel Analysis skill from our agent-skills-library.

Target channel: Ali Abdaal (https://www.youtube.com/@aliabdaal)
(Pick any YouTuber you're interested in analyzing)

My Context:
- My channel: Starting fresh, no existing channel yet
- My niche: Productivity and personal development
- My expertise: I have experience with AI tools and automation
- My goals: Build audience first, then monetization through consulting/community
- Data status: I haven't downloaded the channel data yet

Task:
1. Review the .cursorrules file - you should see this project references the agent-skills-library
2. Follow the YouTube Channel Analysis skill located at:
   /agent-skills-library/cursor-rules/youtube-channel-analysis/RULE.md
3. Help me set up yt-dlp and download the channel data
4. Create the SQLite database from the downloaded data
5. Run the 4-stage analysis pipeline
6. Generate personalized video ideas for my niche

Please start by creating an analysis plan (as the skill instructs), then we'll proceed phase by phase.

I want to see if the skills library integration works smoothly.
```

---

## What You're Testing

### ✅ Success Indicators

1. **AI recognizes the skill exists**
   - References the agent-skills-library
   - Reads the Cursor adapter RULE.md
   - Follows the playbook structure

2. **AI creates a plan first**
   - Shows 4-stage pipeline
   - Asks for your approval
   - Doesn't jump straight to execution

3. **AI helps with yt-dlp setup**
   - Provides installation command
   - Shows correct flags (--skip-download, etc.)
   - Creates data directory

4. **AI parses data into SQLite**
   - Creates proper schema
   - Loads metadata and subtitles
   - Verifies data quality

5. **AI runs analysis incrementally**
   - Phase 1: Descriptive analytics report
   - Phase 2: Pattern recognition report
   - Phase 3: Strategic synthesis report
   - Phase 4: Personalized recommendations
   - Saves each report to files

6. **Recommendations are personalized**
   - References YOUR niche (productivity)
   - References YOUR goals (audience building)
   - Not generic advice

### ❌ Red Flags

1. **AI doesn't mention skills library**
   - Means .cursorrules reference isn't working
   - AI isn't finding the skill files

2. **AI skips planning step**
   - Jumps straight to queries
   - Doesn't follow playbook structure

3. **AI downloads full videos**
   - Wastes bandwidth
   - Ignores --skip-download instruction

4. **Generic recommendations**
   - "Make productivity videos"
   - Doesn't reference your specific context

5. **All-in-one dump**
   - Generates all reports at once
   - Doesn't work incrementally
   - No chance to review/adjust

---

## Alternative Shorter Test

If you want a quicker test (30 minutes instead of 2-3 hours):

```
I want to do a quick test of the YouTube Channel Analysis skill.

I already have some YouTube data in the Nick Saraev directory.

Task: Just create a plan showing me how you would analyze this channel using the skills library.

Don't execute yet - I just want to verify you're:
1. Finding the skills library
2. Following the playbook structure
3. Understanding the 4-stage pipeline

Show me the plan, and explain which files from agent-skills-library you're referencing.
```

This tests the **integration** without doing a full **analysis**.

---

## Model Recommendation

**Start with:** Sonnet 4.5 (Tier 2 task - structured implementation)

**Upgrade to Opus if:**
- Strategic synthesis feels shallow
- Recommendations are too generic
- "Why" explanations lack depth

**Cost estimate:**
- Sonnet 4.5: $3-5 for full analysis
- Opus 4: $15-20 for full analysis

---

## What to Document

After the test, note:

### What Worked Well
- [ ] Integration smooth?
- [ ] Instructions clear?
- [ ] Reports useful?
- [ ] Recommendations personalized?

### What Needs Improvement
- [ ] Confusing instructions?
- [ ] Missing information?
- [ ] Tool-specific issues?
- [ ] Unclear workflow?

### Changes Needed
- [ ] Playbook updates?
- [ ] Adapter updates?
- [ ] .cursorrules improvements?
- [ ] Integration guide additions?

---

## After Testing

Update these files based on learnings:
1. `/agent-skills-library/playbooks/youtube-channel-analysis/README.md` (if instructions unclear)
2. `/agent-skills-library/cursor-rules/youtube-channel-analysis/RULE.md` (if Cursor workflow needs tweaks)
3. `/agent-skills-library/INTEGRATION_GUIDE.md` (if integration issues found)
4. `/analyze-youtube-videos/.cursorrules` (if project setup needs improvement)

Then bump skill to **v1.1.0** with improvements!

---

*Save your test notes - this validates the entire skills library approach*

