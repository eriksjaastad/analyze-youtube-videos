# Videos Queue

**Purpose:** Track YouTube videos to analyze - add URLs here and we'll download metadata + transcripts

**Last Updated:** January 5, 2026

---

## How to Use This File

1. **Add video URL** to "To Analyze" section below
2. **Run the download command** (provided below)
3. **AI will parse** metadata and transcript
4. **Video moves** to "Analyzed" section with date

---

## Quick Download Command

```bash
# Download single video metadata + transcript
yt-dlp \
  --skip-download \
  --write-auto-sub \
  --write-info-json \
  --sub-format vtt \
  --output "data/%(uploader)s/%(title)s.%(ext)s" \
  [VIDEO_URL]
```

Or just paste the URL and ask AI: "Download and analyze this video"

---

## Videos To Analyze

### Priority Queue

<!-- Add new video URLs here -->


### Backlog

<!-- Videos to analyze eventually -->



---

## Videos Analyzed
- [x] **"The Only Claude Code Skill You Need"** by Aniket Panjwani
  - **Date analyzed:** 2026-01-07
  - **URL:** https://youtu.be/MMpaPV3KMFI?si=WTIxum75wOdEyJHk
  - **Location:** `library/2026-01-07_Aniket_Panjwani_The-Only-Claude-Code-Skill-You-Need_MMpaPV3K.md`

- [x] **"Claude Agent SDK [Full Workshop] — Thariq Shihipar, Anthropic"** by AI Engineer
  - **Date analyzed:** 2026-01-07
  - **URL:** https://youtu.be/TqC1qOfiVcQ?si=T_qkyvwFjuSOUN5z
  - **Location:** `library/2026-01-05_AI_Engineer_Claude-Agent-SDK-Full-Workshop-Thariq-Sh_TqC1qOfi.md`

- [x] **"Claude Code Skills vs MCPs: Complete Beginner's Guide 2026"** by Aniket Panjwani
  - **Date analyzed:** 2026-01-06
  - **URL:** https://youtu.be/42nz2FfKA9A?si=v5Cn0w_p4mm0HY0-
  - **Location:** `library/2026-01-05_Aniket_Panjwani_Claude-Code-Skills-vs-MCPs-Complete-Beginners-Guid.md`

- [x] **"Give me 9 Min, Become Dangerously Good at Gemini 3.0 Pro"** by Parker Prompts
  - **Date analyzed:** 2026-01-06
  - **URL:** https://youtu.be/tTplmSnPIHQ?si=wigSqJWTVHOd3skL
  - **Location:** `library/2026-01-03_Parker_Prompts_Give-me-9-Min-Become-Dangerously-Good-at-Gemini-30.md`

- [x] **"AWS re:Invent 2025 - Building Scalable, Self-Orchestrating AI Workflows with A2A and MCP (DEV415)"** by AWS Events
  - **Date analyzed:** 2026-01-06
  - **URL:** https://youtu.be/9O9zZ1lQWiI?si=lpZqKLK2591dFkDy
  - **Location:** `library/2025-12-03_AWS_Events_AWS-reInvent-2025-Building-Scalable-Self-Orchestra.md`

- [x] **"The Creator of Claude Code Shares His Exact Setup"** by Aniket Panjwani
  - **Date analyzed:** 2026-01-06
  - **URL:** https://youtu.be/eSB79p_CPQQ?si=DohxHGfg8qcGfHeR
  - **Location:** `library/2026-01-06_Aniket_Panjwani_The-Creator-of-Claude-Code-Shares-His-Exact-Setup.md`

- [x] **"A Deepdive on my Personal AI Infrastructure (PAI v2.0, December 2025)"** by Unsupervised Learning
  - **Date analyzed:** 2026-01-06
  - **URL:** https://youtu.be/Le0DLrn7ta0?si=vVgYHhFkMzQQn7de
  - **Location:** `library/2025-12-16_Unsupervised_Learning_A-Deepdive-on-my-Personal-AI-Infrastructure-PAI-v2.md`


### Aniket Panjwani
- [x] **"Claude Code Skills vs MCPs: Complete Beginner's Guide"**
  - **Date analyzed:** January 5, 2026
  - **URL:** https://youtu.be/42nz2FfKA9A
  - **Location:** `library/2026-01-05_Aniket_Panjwani_Claude-Code-Skills-vs-MCPs-Complete-Beginners-Guid.md`

### Renaissance Periodization
- [x] **"I Lost Over Half My Body Fat DOING THIS"**
  - **Date analyzed:** January 5, 2026
  - **URL:** https://youtu.be/S8UfefiAwD8
  - **Location:** `library/2025-12-31_Renaissance_Periodization_I-Lost-Over-Half-My-Body-Fat-DOING-THIS.md`

### Testing "The Librarian"
- [x] **"The Ultimate Local AI Coding Guide For 2026"** by Zen van Riel
  - **Date analyzed:** January 5, 2026
  - **URL:** https://youtu.be/rp5EwOogWEw
  - **Location:** `library/2025-10-21_Zen_van_Riel_The-Ultimate-Local-AI-Coding-Guide-For-2026.md`

### Nick Saraev
- [x] **"I Reverse Engineered Nick Saraev's YouTube Channel With Claude Code"** by Aniket Panjwani
  - **Date analyzed:** December 29, 2025
  - **URL:** *(need to add)*
  - **Location:** `Documents/archives/sessions/transcript.en.vtt`
  - **Methodology:** `Documents/core/YouTube_Analysis_Methodology.md`
  - **Notes:** Source methodology for YouTube analysis skill, 252 videos referenced

---

## Analysis Status by Creator

| Creator | Videos Analyzed | Last Analysis | Notes |
|---------|----------------|---------------|-------|
| Nick Saraev (via Aniket) | 1 | Dec 29, 2025 | Methodology video |

---

## Notes

### What Gets Downloaded
For each video:
- `video_title.info.json` - Metadata (title, date, views, description, duration, etc.)
- `video_title.en.vtt` - English transcript/subtitles

### Where Files Go
```
data/
└── [Creator Name]/
    ├── Video_Title.info.json
    ├── Video_Title.en.vtt
    └── [more videos...]
```

### Analysis Options
1. **Single video analysis** - Quick insights from one video
2. **Channel analysis** - Download entire channel, run 4-stage pipeline
3. **Comparison analysis** - Compare multiple creators' approaches

### Related Files
- **Download instructions:** `Documents/reference/TOOLS.md`
- **Analysis methodology:** `Documents/core/YouTube_Analysis_Methodology.md`
- **Test prompts:** `Documents/reference/TEST_PROMPT.md`
- **Project status:** `TODO.md`

---

## Video Ideas to Explore

<!-- Keep a running list of interesting videos/channels to potentially analyze -->

### AI & Automation
- 

### Content Strategy
- 

### Other
- 

---

*Just paste a YouTube URL and say "add this to the queue" or "analyze this video"*

