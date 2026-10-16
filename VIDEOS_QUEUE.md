# Videos Queue

**Purpose:** Track YouTube videos to analyze - add URLs here and we'll download metadata + transcripts

---

## How to Use This File

1. **Add video URL** to "To Analyze" section below
2. **Fetch metadata + transcript:** `uv run scripts/librarian.py [URL]` prints JSON and caches it under `data/fetch_cache/`
3. **Claude writes the analysis** from that JSON (the librarian never analyzes)
4. **Save it:** `uv run scripts/librarian.py [URL] --analysis-file <report.md>` writes the report to `library/` and updates the index
5. **Remove the URL here by hand.** `library/index.yaml` is the record of what has been analyzed

---

## Videos To Analyze

### Priority Queue

<!-- Videos to re-analyze with improved prompt -->
https://youtu.be/7fltOAg8ZGI?si=OyKGoIIixRAf0jZE
https://youtu.be/rPAKq2oQVBs?si=E2sxpRQrOkFOf7HG
https://youtu.be/oW4hgB1vIoY?si=z4WHCsxQFWuqn7aJ - trading - reinforcement learning - be sure to include info about PPO model (Proximal Policy Optimization)
https://youtu.be/1jlKUxqRQAw?si=KqBqj6LBISWJR1Bj claude teams
https://youtu.be/ZcIqiLLT7Fg?si=Rwv5Cl39vUQZFj3E install open clawd
https://youtu.be/2KWhHY0KTMk?si=FiZ1Ymgb7sdT7gtN open claw wit local models
https://youtu.be/f8cfH5XX-XU?si=mO0s_EmZMICU3J_B - New agentic AI open source 
https://youtu.be/KYe2IToDzl4 - **Prof Steve Keen, "You Won't Believe Who's Actually Controlling America"** (2026-08-02, 16 min). Campaign-finance reform proposal: ban private political donations outright, replace with GDP-linked public funding of parties financed by "democracy bonds," enacted via referendum.
    - **ERIK TODO: take screenshots of Keen's on-screen tables** — he wants to build infographics around the campaign-finance data. Transcripts won't capture the tables; they have to be grabbed from the video.
    - Fact-check targets when analyzed: "80% of US politicians funded by pro-Israel lobby groups", "60% of Americans unfavorable toward Israel", UK polling 2:1 claim. Keen is a credible heterodox economist (debt/Minsky) but this is outside his lane. Channel is a Skool funnel ($ course link in description).

### Backlog

<!-- Videos to analyze eventually -->



---

## Notes

### Running the Librarian

```bash
# Fetch metadata + transcript as JSON (also cached under data/fetch_cache/)
uv run scripts/librarian.py https://youtu.be/VIDEO_ID

# Save a report written by Claude
uv run scripts/librarian.py https://youtu.be/VIDEO_ID --analysis-file report.md

# Dry run: preview the save without writing anything to library/
uv run scripts/librarian.py https://youtu.be/VIDEO_ID --analysis-file report.md --dry-run
```

### What Gets Created

- **Fetch** prints metadata + transcript JSON to stdout and caches it under `data/fetch_cache/`
- **Save** writes the report to `library/` and adds it to `library/index.yaml`
- The librarian never analyzes — Claude writes the analysis

### Related Files
- **Librarian script:** `scripts/librarian.py`

---

*Just paste a YouTube URL and say "add this to the queue" or "analyze this video"*
