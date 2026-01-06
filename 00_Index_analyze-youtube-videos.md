---
tags:
  - map/project
  - p/analyze-youtube-videos
  - type/research
  - domain/data-analysis
  - status/active
created: 2026-01-02
---

# analyze-youtube-videos

Research and data analysis project focused on extracting insights from YouTube content. This project uses transcripts and AI-powered analysis to understand creator methodologies, content trends, and information architecture. It includes established methodologies for channel deep-dives and tools for processing video metadata and transcripts.

## Key Components

### Analysis Core
- `Documents/core/YouTube_Analysis_Methodology.md` - Canonical methodology for video and channel analysis.
- `Documents/reference/TOOLS.md` - Recommended tools for transcript extraction and data collection.

### Automation & Tools
- `tools/` - Python scripts for automated data extraction and database ingestion.
  - `pull_youtube_data.py` - Script to download metadata/transcripts from URLs (Planned).
  - `parse_to_sqlite.py` - Script to parse raw data into SQLite (Planned).

### Data & Transcripts
- `data/` - Raw metadata and transcript files organized by uploader.
- `Documents/archives/sessions/` - Historical transcripts and session-specific data (e.g., VTT files).
- `Documents/reference/TEST_PROMPT.md` - Standardized prompts for AI analysis consistency.
- `youtube_data.db` - SQLite database containing processed analysis data.

## Status

**Tags:** #map/project #p/analyze-youtube-videos  
**Status:** #status/active  
**Type:** #type/research
**Last Major Update:** January 2026 (Scaffolded for Project Tracker)  
**Purpose:** Insight extraction and creator methodology research

