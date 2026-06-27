# YouTube Analysis Agent

Video analysis pipeline for extracting insights from YouTube and TikTok content. Erik hands URLs directly to Claude, who fetches transcripts, analyzes the content, and saves structured reports to the library.

---

## How It Works

1. **Erik provides a URL** in conversation with Claude
2. **Claude fetches the data** — runs `librarian.py` to download metadata + transcript via `yt-dlp`
3. **Claude (or a Haiku sub-agent) analyzes** the transcript and writes the report
4. **Claude saves to library** — runs `librarian.py --analysis-file` to save, index, and catalog

That's it. No external LLMs, no API keys, no extra steps.

### Quick Reference

```bash
# Fetch transcript data (returns JSON)
uv run scripts/librarian.py "https://youtube.com/watch?v=..."

# Save a pre-written analysis to the library
uv run scripts/librarian.py "https://youtube.com/watch?v=..." --analysis-file /tmp/analysis.md

# Batch fetch from a profile (TikTok or YouTube)
uv run scripts/librarian.py --batch-profile "https://tiktok.com/@creator" --limit 10
```

### Supported Platforms
- YouTube (youtube.com, youtu.be)
- TikTok (tiktok.com)

### Analysis Modes
- **Standard analysis** — video overview, key concepts, actionable takeaways, critical assessment
- **Tutorial extraction** — step-by-step reproducible workflow from how-to videos

---

## Project Structure

```
analyze-youtube-videos/
├── scripts/
│   ├── librarian.py       ← Transcript fetching, cleaning, library management
│   ├── synthesize.py      ← Multi-document aggregation
│   ├── bridge.py          ← Skill promotion to global library
│   └── config.py          ← Shared config, env, utilities
├── library/               ← Individual video reports
│   ├── index.yaml         ← Source of truth
│   └── 00_Index_Library.md
├── synthesis/             ← Cross-video strategy documents
├── config/
│   ├── replacements.yaml      ← Find-replace rules for analysis cleanup
│   └── flagged_channels.yaml  ← Watchlist of low-trust sources (see below)
└── tests/
```

---

## Flagged Channels (Misinformation Watchlist)

Some channels warrant heightened fact-checking scrutiny. `config/flagged_channels.yaml`
holds a watchlist; on every fetch, the librarian checks the video's channel against it.

- **Matching** is by stable `channel_id` first (immutable across renames), then `@handle`,
  then a case-insensitive display-name fallback.
- **On a match**, the librarian prints a prominent `[!!] FLAGGED CHANNEL` warning and adds
  a `flag` object to the fetch-only JSON output. That `flag` is the signal to **verify every
  factual claim against primary sources** before writing analysis — do not take the video at
  face value.

Add a channel by appending an entry (find its IDs with the `yt-dlp --print` snippet in the
file's header comment). The watchlist is advisory; it never blocks processing.

---

## Supporting Scripts

| Script | Purpose |
|--------|---------|
| `librarian.py` | Fetch transcripts, clean subtitles, save reports, manage library index |
| `synthesize.py` | Aggregate library entries for cross-video synthesis (run through Claude) |
| `bridge.py` | Evaluate and promote skills to global library (run through Claude) |
| `config.py` | Shared config: paths, env loading, subtitle selection, replacements |

---

## Testing

```bash
uv run pytest tests/ -v
```

---

## CI / Automated Code Review

PRs are reviewed by Claude Sonnet via a [reusable workflow](https://github.com/eriksjaastad/tools/blob/main/.github/workflows/claude-review-reusable.yml) in the `tools` repo. Auto-merges on APPROVE, blocks on REQUEST_CHANGES.
