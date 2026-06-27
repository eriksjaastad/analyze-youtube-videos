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

Both modes carry a **Research Addendum** (see below) whenever the video makes
external factual claims.

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

## Research Layer

Videos name-drop products, companies, benchmarks, and claims that are worth verifying and
documenting rather than repeating at face value. The research layer splits this into a
**deterministic seed** (code) and a **semantic pass** (agent):

1. **Seed — `extract_research_targets()`.** On every fetch, the librarian adds a
   `research_targets` block to the JSON output, harvesting the high-signal, deterministic
   things worth researching:
   - `links` — every URL in the description (deduped, order-preserved)
   - `hashtags` — from description + tags
   - `mentions` — `@handles` from the description (emails excluded)
   - `chapters` — author-curated chapter titles (topic markers)

   This is a checklist, **not** the research. It never calls the web.

2. **Pass — the research agent.** During analysis, a research sub-agent (or Claude directly)
   takes the transcript plus `research_targets`, extracts the **named entities and
   factual/numeric claims** (the model does this far better than a regex), verifies each
   against primary sources via web search, and writes them up.

3. **Output — the Research Addendum.** Findings land in a `## Research Addendum` section of
   the saved report: a claim-by-claim verification table (✅/❌ + detail), a "things the
   video soft-pedals" list, and a `Sources consulted` line with links. See any recent
   roundup/tutorial entry in `library/` for the format.

**Flagged channels (see above) get a mandatory deep pass** — every factual/medical claim is
treated as unverified until a primary source confirms it.

### Deep Research Mode (multi-model verification)

Research is **opt-in** — by default Erik just wants the video analyzed. When he asks (e.g.
"also research this", "deep-research this one"), there are two tiers:

- **Single-threaded** (default when asked): Claude gathers web evidence and writes the Research
  Addendum directly. Fast, no extra cost.
- **Deep multi-model**: claims are verified by a panel of independent models plus an adversarial
  critic — for AI-setup or high-stakes claims where one model's blind spots aren't enough.

The deep tier uses the **claim verification panel** that lives in the `auxesis-research-labs`
project (`src/auxesis_research_labs/panel/claim_panel.py`), where the model keys and dispatch
harness already are. This keeps *this* project's "no external LLMs in the librarian" rule intact —
the librarian still only fetches; the panel is a separate, opt-in component.

**Flow:**
1. Claude extracts the claims from the transcript and gathers web evidence per claim
   (`WebSearch` / Firecrawl).
2. Claude writes a `claims.json` (`[{"id", "text", "evidence": [{"source", "snippet"}]}]`).
3. Run the panel under the auxesis Doppler config:
   ```bash
   doppler run -p auxesis-research-labs -c dev -- \
     uv run scripts/run_claim_panel.py --claims-file claims.json --budget-usd 0.50
   ```
   Researcher models (Grok / Gemini / GPT) judge each claim against the shared evidence
   independently → deterministic vote tally → a different-family critic (Claude) tries to
   **falsify** the majority (downgrade to `DISPUTED`). Output is per-claim verdicts
   (`SUPPORTED` / `REFUTED` / `UNVERIFIED` / `DISPUTED`) with reasoning and cost.
4. Claude folds the verdicts into the report's `## Research Addendum`.

Cost-capped by both a budget cap and a per-run call cap (default 40 calls ≈ 10 claims). "Independence
+ criticism beats consensus": the critic routinely catches over-confident agreement built on weak
evidence. See `auxesis-research-labs/src/auxesis_research_labs/panel/README.md` for full options.

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
