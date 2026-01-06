# Tool Installation Guide

## YouTube Data Collection Tool

### yt-dlp (Python command-line tool)

**What it does:**
- Downloads YouTube video metadata (not videos!)
- Downloads subtitles/transcripts
- Extracts chapter information
- Gets view counts, durations, etc.

**Installation:**

```bash
# Option 1: pip (recommended)
pip install yt-dlp

# Option 2: With uv (if using Python virtual environment)
uv pip install yt-dlp

# Option 3: Homebrew (Mac)
brew install yt-dlp

# Verify installation
yt-dlp --version
```

**NOT an npm package** - This is a Python tool, not JavaScript.

---

## Basic Usage

### Download channel metadata and subtitles (NOT videos):

```bash
# Create data directory
mkdir -p data

# Download metadata + subtitles for entire channel
yt-dlp \
  --skip-download \
  --write-auto-sub \
  --write-info-json \
  --sub-format vtt \
  --output "data/%(uploader)s/%(title)s.%(ext)s" \
  [CHANNEL_URL]
```

**Key flags:**
- `--skip-download` - Don't download videos (just metadata)
- `--write-auto-sub` - Download auto-generated subtitles
- `--write-info-json` - Save video metadata as JSON
- `--sub-format vtt` - Get subtitles in VTT format
- `--output` - Where to save files

**Example:**
```bash
yt-dlp \
  --skip-download \
  --write-auto-sub \
  --write-info-json \
  --sub-format vtt \
  --output "data/%(uploader)s/%(title)s.%(ext)s" \
  "https://www.youtube.com/@nicksaraev/videos"
```

This downloads ALL metadata and subtitles from Nick Saraev's channel.

---

## What You'll Get

For each video:
- `video_title.info.json` - Metadata (views, date, description, etc.)
- `video_title.en.vtt` - English subtitles/transcript

**File structure:**
```
data/
└── Nick Saraev/
    ├── Video 1 Title.info.json
    ├── Video 1 Title.en.vtt
    ├── Video 2 Title.info.json
    ├── Video 2 Title.en.vtt
    └── ...
```

---

## Quick Start

**Step 1: Install yt-dlp**
```bash
pip install yt-dlp
```

**Step 2: Download channel data**
```bash
yt-dlp \
  --skip-download \
  --write-auto-sub \
  --write-info-json \
  --sub-format vtt \
  --output "data/%(uploader)s/%(title)s.%(ext)s" \
  [YOUR_CHANNEL_URL]
```

**Step 3: Tell AI to parse into SQLite**
"Parse the downloaded JSON files into a SQLite database using the schema from the playbook"

---

## Documentation

- **GitHub:** https://github.com/yt-dlp/yt-dlp
- **Full options:** `yt-dlp --help`

---

*Part of analyze-youtube-videos workflow - see .cursorrules for full process*

