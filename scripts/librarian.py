import os
import sys
import argparse
import tempfile
import json
import subprocess
import re
import yaml
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from scripts.config import LIBRARY_DIR, TEMP_DIR, select_subtitle, initialize_directories, safe_slug, logger, apply_replacements

def run_with_retry(cmd: List[str], timeout: int, max_retries: int = 3, base_delay: float = 2.0) -> Optional[subprocess.CompletedProcess]:
    """
    Runs a subprocess command with exponential backoff retry logic.

    Args:
        cmd: Command to run as list of strings
        timeout: Timeout in seconds for each attempt
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 2.0)

    Returns:
        subprocess.CompletedProcess on success, None on exhaustion
    """
    for attempt in range(max_retries):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

            # Success - return immediately
            if result.returncode == 0:
                return result

            # Non-zero return code - retry with backoff
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning(f"Command failed (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                logger.error(f"Command failed after {max_retries} attempts")
                return result  # Return the failed result for error handling

        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning(f"Command timed out (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                logger.error(f"Command timed out after {max_retries} attempts")
                return None

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            raise

        except FileNotFoundError:
            logger.error(f"Command not found: {cmd[0]}")
            return None

    return None

def atomic_write(path: Path, content: str) -> None:
    """Atomic write using a temp file and rename pattern."""
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    temp_path.rename(path)

def clean_srt(srt_content: str) -> str:
    """
    Cleans SRT/VTT file content by removing indices, timestamps, and deduplicating lines.
    Handles both SRT (commas in timestamps) and VTT (dots in timestamps) formats.
    Optimized for long-context processing.
    """
    lines = srt_content.splitlines()
    cleaned_lines = []

    # Match both SRT (00:00:00,000) and VTT (00:00:00.000) timestamp formats
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}[,.]\d{3} --> \d{2}:\d{2}:\d{2}[,.]\d{3}')
    index_pattern = re.compile(r'^\d+$')
    # Skip VTT headers and metadata
    vtt_header_pattern = re.compile(r'^(WEBVTT|Kind:|Language:)', re.IGNORECASE)
    
    last_line = ""
    for line in lines:
        line = line.strip()
        if not line or index_pattern.match(line) or timestamp_pattern.match(line) or vtt_header_pattern.match(line):
            continue
        line = re.sub(r'<[^>]+>', '', line)
        if line != last_line:
            cleaned_lines.append(line)
            last_line = line
            
    text = " ".join(cleaned_lines)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def download_audio(url: str, temp_dir: Path) -> Optional[Path]:
    """
    Downloads audio from a YouTube video using yt-dlp.
    Returns path to the downloaded MP3 file, or None on failure.
    """
    try:
        audio_path = temp_dir / "audio.mp3"
        logger.info(f"[*] Downloading audio for Whisper transcription...")

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--output", str(audio_path.with_suffix('')),  # yt-dlp adds .mp3
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"Audio download failed: {result.stderr}")
            return None

        if audio_path.exists():
            return audio_path
        else:
            logger.error(f"Audio file not found at {audio_path}")
            return None

    except subprocess.TimeoutExpired:
        logger.error("Audio download timed out after 300 seconds")
        return None
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")
        return None

def extract_chapters(metadata: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extracts and formats chapter information from YouTube metadata.

    Args:
        metadata: Video metadata dict from yt-dlp

    Returns:
        List of dicts with 'timestamp' and 'title' keys, or empty list if no chapters
    """
    chapters = metadata.get("chapters", [])
    if not chapters:
        return []

    formatted_chapters = []
    for chapter in chapters:
        start_time = chapter.get("start_time", 0)
        title = chapter.get("title", "Untitled")

        # Format timestamp as HH:MM:SS or MM:SS
        hours = int(start_time // 3600)
        minutes = int((start_time % 3600) // 60)
        seconds = int(start_time % 60)

        if hours > 0:
            timestamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            timestamp = f"{minutes:02d}:{seconds:02d}"

        formatted_chapters.append({
            "timestamp": timestamp,
            "title": title
        })

    return formatted_chapters

def transcribe_with_whisper(audio_path: Path) -> Optional[str]:
    """
    Transcribes audio file using faster-whisper.
    Returns transcript text, or None on failure.
    """
    try:
        # Lazy import so faster-whisper is optional
        from faster_whisper import WhisperModel

        logger.info(f"[*] Transcribing with Whisper (this may take a few minutes)...")

        # Use base model with CPU and int8 for reasonable speed/quality tradeoff
        model = WhisperModel("base", device="cpu", compute_type="int8")

        # Transcribe with VAD filter to improve accuracy
        segments, info = model.transcribe(
            str(audio_path),
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        # Combine all segments into single transcript
        transcript_parts = []
        for segment in segments:
            transcript_parts.append(segment.text.strip())

        transcript = " ".join(transcript_parts)
        logger.info(f"[+] Whisper transcription complete ({len(transcript)} characters)")

        return transcript

    except ImportError:
        logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
        return None
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return None

def get_video_data(url: str, use_whisper_fallback: bool = True) -> Optional[Dict[str, Any]]:
    """
    Uses yt-dlp to fetch video metadata and SRT transcript.
    Prioritizes manual subtitles over auto-generated ones.
    Uses tempfile.TemporaryDirectory for safe, automatic cleanup.
    """
    with tempfile.TemporaryDirectory(dir=TEMP_DIR, prefix="transcript_") as temp_dir:
        unique_temp = Path(temp_dir)
        
        try:
            logger.info(f"[*] Fetching metadata for: {url}")

            cmd_info = [
                "yt-dlp",
                "--skip-download",
                "--print-json",
                url
            ]
            result = run_with_retry(cmd_info, timeout=60)
            if result is None or result.returncode != 0:
                error_msg = result.stderr if result else "Command failed after retries"
                logger.error(f"Error fetching metadata: {error_msg}")
                return None

            metadata = json.loads(result.stdout)
            
            logger.info("[*] Fetching manual and auto-subtitles...")
            sub_path_base = str(unique_temp / "transcript")
            cmd_subs = [
                "yt-dlp",
                "--skip-download",
                "--write-subs",
                "--write-auto-subs",
                "--sub-lang", "en,en-US,en-GB,eng,eng-US,eng-GB",
                "--sub-format", "srt/vtt/best",
                "--output", sub_path_base,
                url
            ]
            sub_result = run_with_retry(cmd_subs, timeout=120)
            if sub_result is None or sub_result.returncode != 0:
                error_msg = sub_result.stderr if sub_result else "Command failed after retries"
                logger.warning(f"Subtitle fetch command failed for {url}.")
                logger.debug(f"Stderr: {error_msg}")
            
            srt_files = [f for f in os.listdir(unique_temp) if f.endswith(('.srt', '.vtt'))]
            transcript = ""
            target_file = select_subtitle(srt_files, "transcript")

            if target_file:
                target_path = unique_temp / target_file
                with open(target_path, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                    transcript = clean_srt(srt_content)
            else:
                logger.warning("No SRT transcript found.")

                # Try Whisper fallback if enabled
                if use_whisper_fallback:
                    logger.info("[*] Attempting Whisper fallback...")
                    audio_path = download_audio(url, unique_temp)
                    if audio_path:
                        whisper_transcript = transcribe_with_whisper(audio_path)
                        if whisper_transcript:
                            transcript = whisper_transcript
                            logger.info("[+] Using Whisper-generated transcript")
                        else:
                            logger.error("Whisper transcription failed")
                    else:
                        logger.error("Audio download failed")

                # If both SRT and Whisper failed, return None
                if not transcript:
                    logger.error("No transcript available (SRT and Whisper both failed)")
                    return None
                
            # Extract chapters if available
            chapters = extract_chapters(metadata)

            # Detect platform from URL or extractor
            extractor = metadata.get("extractor_key", "").lower()
            if "tiktok" in extractor or "tiktok.com" in url:
                platform = "tiktok"
                # TikTok: 'channel' is display name, 'uploader' is handle
                channel = metadata.get("channel") or metadata.get("uploader") or "Unknown_Channel"
            else:
                platform = "youtube"
                channel = metadata.get("uploader") or "Unknown_Channel"

            return {
                "title": metadata.get("title") or "Untitled",
                "channel": channel,
                "channel_id": metadata.get("channel_id") or "",
                "uploader_id": metadata.get("uploader_id") or "",
                "date": metadata.get("upload_date"),
                "url": url,
                "video_id": metadata.get("id") or "unknown",
                "description": metadata.get("description") or "",
                "transcript": transcript,
                "tags": metadata.get("tags", []) or [],
                "view_count": metadata.get("view_count") or 0,
                "like_count": metadata.get("like_count") or 0,
                "duration_string": metadata.get("duration_string") or "0:00",
                "chapters": chapters,
                "platform": platform
            }
        except subprocess.TimeoutExpired as e:
            logger.error(f"Subprocess timed out: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_video_data: {e}")
            return None

def build_tutorial_prompt(data: Dict[str, Any]) -> str:
    """Build a tutorial-extraction prompt for short-form or long-form video content."""
    return f"""You are a senior technical writer creating a step-by-step tutorial from a video transcript. Your task is to extract the creator's exact workflow and turn it into reproducible documentation that someone could follow without watching the video.

**VIDEO METADATA**
- Title: {data['title']}
- Channel: {data['channel']}
- Duration: {data['duration_string']}
- Platform: {data.get('platform', 'unknown')}

**TRANSCRIPT TO ANALYZE**
{data['transcript']}

---

**YOUR OUTPUT MUST FOLLOW THIS EXACT STRUCTURE:**

## Tutorial: [Descriptive title of what you'll learn]

**Source:** "{data['title']}" by {data['channel']}
**Duration:** {data['duration_string']}
**Difficulty:** [Beginner / Intermediate / Advanced]

---

## What You'll Build / Achieve

[1-2 sentences: What is the end result of following this tutorial?]

---

## Tools & Resources Required

[Bulleted list of every tool, platform, model, or resource mentioned. For each:
- **Name** — what it is, whether it's free/paid, and its URL if mentioned
- Mark which are essential vs. optional]

---

## Step-by-Step Workflow

[This is the core of the tutorial. Break the video into numbered steps. For each step:
1. **Step title** — what you're doing
   - Detailed instructions on HOW to do it
   - Include specific settings, prompts, parameters, or configurations mentioned
   - Note any tips or warnings the creator gives
   - If the creator shows a specific prompt or text, quote it exactly]

---

## Pro Tips & Tricks

[Bulleted list of non-obvious techniques, shortcuts, or lessons the creator shares. These are the "insider knowledge" bits that make the tutorial valuable beyond basic steps.]

---

## Common Mistakes to Avoid

[If the creator mentions pitfalls, failures, or things that don't work — list them here. If not mentioned, omit this section entirely.]

---

## Related Workflows

[Brief list of related techniques or next steps the creator mentions or that would logically follow.]

---

**IMPORTANT RULES:**
1. Extract SPECIFIC details — exact tool names, model names, prompt text, settings values
2. The goal is REPRODUCIBILITY — someone should be able to follow this without watching the video
3. If the creator uses a specific prompt, quote it verbatim in a code block
4. Do NOT include meta-commentary about your process
5. Do NOT pad with generic advice — only include what the creator actually said or showed
6. IGNORE sponsor segments, like/subscribe requests, and promotional content
7. Focus on the WORKFLOW — the sequence of actions, not opinions
8. Output ONLY the markdown content — no preamble or explanation

BEGIN YOUR TUTORIAL EXTRACTION:"""


# A claim-table row starts with "| <digits>" — the numbering convention every collection
# README specifies. Suffixed ids like "25a" are counted too.
_CLAIM_ROW_RE = re.compile(r'^\|\s*\d+[a-z]?\s*\|')
_MD_LINK_RE = re.compile(r'\[[^\]]+\]\([^)]+\)|https?://')
# Threshold from FACT_CHECK_PROTOCOL.md: above this, the report is not publishable as a
# fact-check. Kept here as the single numeric definition so doc and code can't drift.
UNSOURCED_CLAIM_CEILING = 0.20


def audit_claim_sources(analysis: str) -> Optional[Dict[str, Any]]:
    """Count claim-table rows that carry no source link.

    Rule 0 of FACT_CHECK_PROTOCOL.md: the source goes in the row, because an unsourced
    grade and a sourced grade are visually identical without it — which is how two of the
    2026-08-14 overturns survived review. A bulk '## Sources' list proves nothing about
    any individual grade, so it deliberately does not count here.

    Returns None when the report has no claim table (tutorial extractions, workflow
    write-ups), so those are never nagged. Detection is intentionally naive: it reports,
    it never blocks, and a false positive costs one ignored warning.
    """
    rows = [ln for ln in analysis.splitlines() if _CLAIM_ROW_RE.match(ln.strip())]
    if not rows:
        return None
    unsourced = [r for r in rows if not _MD_LINK_RE.search(r)]
    return {
        "total": len(rows),
        "unsourced": len(unsourced),
        "ratio": len(unsourced) / len(rows),
    }


def emit_claim_source_audit(stats: Dict[str, Any]) -> None:
    """Warn when claim rows lack bound sources. Reports, never blocks."""
    total, unsourced, ratio = stats["total"], stats["unsourced"], stats["ratio"]
    if not unsourced:
        logger.info(f"[fact-check] {total}/{total} claim rows carry a source link.")
        return
    over = ratio > UNSOURCED_CLAIM_CEILING
    logger.warning("=" * 70)
    logger.warning(f"[fact-check] {unsourced} of {total} claim rows have NO source link "
                   f"({ratio:.0%}).")
    logger.warning("[fact-check] Rule 0: the source goes IN the row. A bulk '## Sources'")
    logger.warning("[fact-check] list at the bottom does not satisfy this.")
    if over:
        logger.warning(f"[fact-check] !! Above the {UNSOURCED_CLAIM_CEILING:.0%} ceiling — this "
                       "is NOT publishable as a fact-check.")
        logger.warning("[fact-check] !! Either bind the sources or grade those rows Unchecked.")
    logger.warning("=" * 70)


def save_to_library(data: Dict[str, Any], analysis: str, subdir: Optional[str] = None) -> Path:
    """
    Saves the final report to the library/ directory.
    Uses video_id and safe_slug to prevent filename collisions and ensure safety.

    `subdir` files the report under library/<subdir>/ instead of the flat root, for
    topic collections that accumulate over time (see library/*/README.md).
    """
    date_str = data.get('date')
    if date_str and len(date_str) == 8:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        formatted_date = datetime.now().strftime("%Y-%m-%d")

    clean_title = safe_slug(data['title'])
    clean_channel = safe_slug(data['channel'])

    vid_id = safe_slug(data.get('video_id', 'unknown'))[:8]
    filename = f"{formatted_date}_{clean_channel}_{clean_title[:40]}_{vid_id}.md"

    target_dir = LIBRARY_DIR
    if subdir:
        # Slug the subdir so it can never introduce separators or traversal segments.
        # safe_slug strips '.' and '/', so a hostile value can't survive as a path part.
        slugged = safe_slug(subdir)
        if not slugged:
            logger.warning(f"[!] Subdir {subdir!r} sanitized to empty; saving to library root instead.")
        else:
            target_dir = LIBRARY_DIR / slugged
            target_dir.mkdir(parents=True, exist_ok=True)
    filepath = target_dir / filename

    # Traversal Guard
    if not filepath.resolve().is_relative_to(LIBRARY_DIR.resolve()):
        raise RuntimeError(f"Potential Path Traversal detected: {filepath}")

    tags = ["p/analyze-youtube-videos", "type/knowledge-extraction"]
    if data.get('tags'):
        tags.extend([f"topic/{safe_slug(t)}" for t in data['tags'][:5]])
        
    # Build chapter timeline section if chapters exist
    chapter_section = ""
    if data.get('chapters'):
        chapter_lines = [f"- [{ch['timestamp']}] {ch['title']}" for ch in data['chapters']]
        chapter_section = f"\n## Chapter Timeline\n\n" + "\n".join(chapter_lines) + "\n"

    content = f"""---
tags:
{chr(10).join([f"  - {t}" for t in tags])}
status: #status/active
created: {datetime.now().strftime("%Y-%m-%d")}
url: "{data['url']}"
title: "{data['title']}"
channel: "{data['channel']}"
upload_date: {formatted_date}
views: {data['view_count']}
likes: {data['like_count']}
duration: "{data['duration_string']}"
---

# {data['title']}

> **Channel:** [{data['channel']}]({data['url']}) | **Duration:** {data['duration_string']} | **Views:** {data['view_count']:,}
{chapter_section}
{analysis}
"""
    
    atomic_write(filepath, content)
    logger.info(f"[+] Saved to: {filepath}")
    return filepath

def get_category(title: str, tags: List[str]) -> Dict[str, str]:
    """Determine category from title and tags using config/categories.yaml."""
    categories_path = Path("config/categories.yaml")
    if not categories_path.exists():
        return {"id": "miscellaneous", "name": "📦 Miscellaneous"}
    
    with open(categories_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    text_to_check = (title + " " + " ".join(tags)).lower()
    for cat in config.get("categories", []):
        for keyword in cat.get("keywords", []):
            if keyword.lower() in text_to_check:
                return {"id": cat["id"], "name": cat["name"]}
                
    return config.get("default_category", {"id": "miscellaneous", "name": "📦 Miscellaneous"})

def update_index(entry_data: Dict[str, Any]) -> None:
    """
    Updates library/index.yaml as Source of Truth, then renders 00_Index_Library.md.
    """
    index_yaml_path = LIBRARY_DIR / "index.yaml"
    index_md_path = LIBRARY_DIR / "00_Index_Library.md"
    
    index_data = {"entries": []}
    if index_yaml_path.exists():
        with open(index_yaml_path, "r", encoding="utf-8") as f:
            try:
                index_data = yaml.safe_load(f) or {"entries": []}
            except yaml.YAMLError as e:
                logger.error(f"Error reading index.yaml: {e}")
                index_data = {"entries": []}
            
    # Check for duplicates
    for entry in index_data["entries"]:
        if entry.get("url") == entry_data["url"]:
            logger.info(f"Entry for {entry_data['title']} already exists in index. Skipping.")
            return

    index_data["entries"].append(entry_data)
    
    # Sort entries by date descending
    index_data["entries"].sort(key=lambda x: x.get("date", ""), reverse=True)
    
    # Atomic write YAML
    temp_yaml = index_yaml_path.with_suffix(".yaml.tmp")
    with open(temp_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(index_data, f, allow_unicode=True, sort_keys=False)
    temp_yaml.rename(index_yaml_path)
    
    # Render Markdown
    md_content = "# 📚 YouTube Knowledge Library\n\n"
    
    # Group by category
    categories_path = Path("config/categories.yaml")
    categories_config = []
    if categories_path.exists():
        with open(categories_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            categories_config = config.get("categories", [])
            default_cat = config.get("default_category", {"id": "miscellaneous", "name": "📦 Miscellaneous"})
            categories_config.append(default_cat)
            
    for cat in categories_config:
        cat_entries = [e for e in index_data["entries"] if e.get("category_id") == cat["id"]]
        if cat_entries:
            md_content += f"## {cat['name']}\n"
            for e in cat_entries:
                md_content += f"- [[{e['title']}]] ({e['channel']}) - *Analyzed {e['date']}*\n"
            md_content += "\n"
            
    atomic_write(index_md_path, md_content)
    logger.info(f"Updated index YAML and rendered Markdown at {index_md_path}")

def update_queue(url: str, title: str, channel: str, filepath: Path) -> None:
    """
    Moves a URL from the Priority Queue to the Analyzed section in VIDEOS_QUEUE.md.
    """
    queue_file = Path("VIDEOS_QUEUE.md")
    if not queue_file.exists():
        logger.info(f"No queue file found at {queue_file}. Skipping queue update.")
        return

    with open(queue_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    found = False
    in_priority = False
    
    priority_marker = "### Priority Queue"
    analyzed_marker = "## Videos Analyzed"
    clean_url = url.split('?si=')[0].split('&si=')[0]

    for line in lines:
        if priority_marker in line:
            in_priority = True
            new_lines.append(line)
            continue
        if analyzed_marker in line:
            in_priority = False
            new_lines.append(line)
            if found:
                entry = f"- [x] **\"{title}\"** by {channel}\n"
                entry += f"  - **Date analyzed:** {datetime.now().strftime('%Y-%m-%d')}\n"
                entry += f"  - **URL:** {url}\n"
                entry += f"  - **Location:** `{filepath}`\n\n"
                new_lines.append(entry)
            continue
        if in_priority and clean_url in line:
            found = True
            continue
        new_lines.append(line)

    if found:
        atomic_write(queue_file, "".join(new_lines))
        logger.info(f"Updated {queue_file}: Moved to Analyzed.")

def get_profile_video_urls(profile_url: str, limit: Optional[int] = None) -> List[str]:
    """
    Fetches all video URLs from a TikTok or YouTube profile/channel.
    Returns list of video URLs, optionally limited.
    """
    logger.info(f"[*] Fetching video list from profile: {profile_url}")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(webpage_url)s",
        profile_url
    ]
    result = run_with_retry(cmd, timeout=60)
    if result is None or result.returncode != 0:
        logger.error("Failed to fetch profile video list.")
        return []

    urls = [u.strip() for u in result.stdout.strip().splitlines() if u.strip()]
    logger.info(f"[+] Found {len(urls)} videos on profile")

    if limit:
        urls = urls[:limit]
        logger.info(f"[*] Limited to first {limit} videos")

    return urls


# Anchor to the script's own location so the check works regardless of CWD
# (the librarian may be invoked from a wrapper, cron job, or test runner).
FLAGGED_CHANNELS_PATH = Path(__file__).resolve().parent.parent / "config" / "flagged_channels.yaml"


def _norm_handle(value: Optional[str]) -> str:
    """Normalize a channel handle for comparison: lowercase, no leading '@'.

    YouTube's uploader_id arrives with the '@' prefix; TikTok's does not. The
    watchlist stores handles with '@' for readability, so strip it on both sides.
    """
    return (value or "").strip().lstrip("@").lower()


def check_flagged_channel(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Checks the video's channel against config/flagged_channels.yaml.

    Matches by channel_id (stable across renames), then @handle, then a
    case-insensitive display-name fallback. Returns the matching flag entry
    (dict) or None. A missing/unreadable config is treated as "no flags".
    """
    try:
        if not FLAGGED_CHANNELS_PATH.exists():
            return None
        with open(FLAGGED_CHANNELS_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        logger.warning(f"Could not read {FLAGGED_CHANNELS_PATH}: {e}")
        return None

    cid = (data.get("channel_id") or "").strip()
    handle = _norm_handle(data.get("uploader_id"))
    name = (data.get("channel") or "").strip().lower()

    for entry in config.get("channels", []) or []:
        e_cid = (entry.get("channel_id") or "").strip()
        e_handle = _norm_handle(entry.get("handle"))
        e_name = (entry.get("name") or "").strip().lower()
        if (e_cid and cid and e_cid == cid) \
                or (e_handle and handle and e_handle == handle) \
                or (e_name and name and e_name == name):
            return entry
    return None


def emit_flag_warning(entry: Dict[str, Any], data: Dict[str, Any]) -> None:
    """Print a prominent multi-line warning when a flagged channel is detected."""
    severity = (entry.get("severity") or "watch").upper()
    reason = " ".join((entry.get("reason") or "").split())
    logger.warning("=" * 70)
    logger.warning(f"[!!] FLAGGED CHANNEL [{severity}]: {data.get('channel')}")
    logger.warning(f"[!!] {reason}")
    logger.warning("[!!] FACT-CHECK every factual claim against primary sources before saving.")
    logger.warning("=" * 70)


# Anchored to the script's own location, not CWD — same reason as FLAGGED_CHANNELS_PATH above.
# A CWD-relative lookup here would report the protocol "NOT FOUND" whenever the librarian is
# invoked from anywhere but the repo root, which is the exact opposite of a reliability gate.
FACT_CHECK_PROTOCOL_PATH = Path(__file__).resolve().parent.parent / "FACT_CHECK_PROTOCOL.md"


# Reports land in library/, which is gitignored — no PR, hook, or CI check ever sees them.
# This warning is the only enforcement point the pipeline has, so it fires on every fetch.
def emit_fact_check_protocol_reminder() -> None:
    """Surface the fact-check protocol at fetch time, before any grading happens.

    Origin: 2026-08-14, an ~11% materially-wrong first-pass grade rate. The three rules
    below are the ones that caused overturns; the file has the other four and the reasoning.
    """
    logger.warning("-" * 70)
    logger.warning("[fact-check] Before grading any claim, read FACT_CHECK_PROTOCOL.md")
    if not FACT_CHECK_PROTOCOL_PATH.exists():
        logger.warning("[fact-check] !! FACT_CHECK_PROTOCOL.md NOT FOUND at repo root !!")
    logger.warning("[fact-check]  0. SOURCE LINK GOES IN THE CLAIM ROW. A bulk source list at")
    logger.warning("[fact-check]     the bottom does NOT count. Empty source cell == Unchecked.")
    logger.warning("[fact-check]  1. No grade from memory. Unsearched == Unchecked.")
    logger.warning("[fact-check]  2. Fetch the primary source. A search snippet is not evidence.")
    logger.warning("[fact-check]  3. Search the speaker's framing and units FIRST, not yours.")
    logger.warning("[fact-check] Re-check every 'Wrong' grade in the speaker's favour before "
                   "publishing.")
    logger.warning("-" * 70)


# High-signal patterns for harvesting deterministic research targets.
_URL_RE = re.compile(r'https?://[^\s<>"\')]+')
_HASHTAG_RE = re.compile(r'(?<!\w)#(\w+)')
_MENTION_RE = re.compile(r'(?<!\w)@([A-Za-z0-9_.]+)')
# A mention candidate shaped like "name.tld" where tld is a common TLD (e.g.
# "smoothmedia.co" from an email address) is a domain, not a social handle.
# Restricting to known TLDs preserves legitimate dotted handles like "Mr.Beast".
_DOMAIN_LIKE_RE = re.compile(r'^[A-Za-z0-9_-]+\.([A-Za-z]{2,})$')
_COMMON_TLDS = frozenset({
    "com", "co", "io", "net", "org", "me", "ai", "dev", "app", "tv",
    "gg", "xyz", "info", "biz", "edu", "gov", "us", "uk", "ca",
})


def _looks_like_domain(handle: str) -> bool:
    """True if a mention candidate is really a domain/email tail, not a handle."""
    m = _DOMAIN_LIKE_RE.match(handle)
    return bool(m) and m.group(1).lower() in _COMMON_TLDS


def extract_research_targets(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Harvest high-signal, deterministic research targets from video metadata to
    seed the research pass. This does NOT do the research — it produces a
    checklist for a research agent to verify and document.

    Semantic targets (named products, companies, factual/numeric claims) are
    intentionally left to the research agent, which extracts them from the
    transcript far more reliably than a regex could.

    Returns a dict with:
      - links:    unique URLs from the description, order-preserved
      - hashtags: unique hashtags from description + tags (without '#')
      - mentions: unique @handles from the description (without '@'); candidates
                  shaped like a domain with a common TLD (e.g. "smoothmedia.co"
                  from an email) are filtered, but dotted handles like "Mr.Beast"
                  are preserved
      - chapters: author-curated chapter titles (topic markers worth researching)
    """
    description = data.get("description") or ""

    links: List[str] = []
    for u in _URL_RE.findall(description):
        u = u.rstrip('.,;')
        if u and u not in links:
            links.append(u)

    hashtags = list(dict.fromkeys(
        [h.lower() for h in _HASHTAG_RE.findall(description)]
        + [str(t).lower() for t in (data.get("tags") or [])]
    ))

    mentions = list(dict.fromkeys(
        m for m in _MENTION_RE.findall(description) if not _looks_like_domain(m)
    ))

    chapters = [
        ch["title"] for ch in (data.get("chapters") or [])
        if isinstance(ch, dict) and ch.get("title")
    ]

    return {
        "links": links,
        "hashtags": hashtags,
        "mentions": mentions,
        "chapters": chapters,
    }


def process_single_video(url: str, args) -> bool:
    """
    Processes a single video URL through the full pipeline.
    In fetch-only mode, outputs JSON metadata + transcript for external analysis.
    In save mode (--analysis-file), saves a pre-generated analysis to the library.
    Returns True on success, False on failure.
    """
    data = get_video_data(url, use_whisper_fallback=not args.no_whisper)
    if not data:
        logger.error(f"Failed to get video data for: {url}")
        return False

    # Flag known-problematic sources so claims get extra fact-checking scrutiny.
    flag = check_flagged_channel(data)
    if flag:
        emit_flag_warning(flag, data)
        data["flag"] = {
            "flagged": True,
            "severity": flag.get("severity"),
            "reason": " ".join((flag.get("reason") or "").split()),
            "name": flag.get("name"),
        }

    # If no analysis file provided, output data as JSON for external analysis (Claude)
    if not args.analysis_file:
        # Seed the research pass with a deterministic checklist of what to verify.
        data["research_targets"] = extract_research_targets(data)
        # Fires here, on the fetch that precedes grading — not on the save, which is too late.
        emit_fact_check_protocol_reminder()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return True

    # Load pre-generated analysis from file
    analysis_path = Path(args.analysis_file)
    if not analysis_path.exists():
        logger.error(f"Analysis file not found: {args.analysis_file}")
        return False

    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = f.read()

    # Apply find-replace rules from config/replacements.yaml
    analysis = apply_replacements(analysis)

    if args.dry_run:
        logger.info(f"--- DRY RUN: {data['title']} ---")
        logger.info(analysis)
        logger.info("--------------------------------")
        return True

    date_str = data.get('date')
    if date_str and len(date_str) == 8:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        formatted_date = datetime.now().strftime("%Y-%m-%d")

    # Rule 0 audit runs on the way in, so an unsourced claim table is caught at the moment
    # it lands rather than on a re-read months later. Reports, never blocks — a false
    # positive costs one ignored warning, a missed one costs an unsourced grade in the library.
    source_stats = audit_claim_sources(analysis)
    if source_stats:
        emit_claim_source_audit(source_stats)

    filepath = save_to_library(data, analysis, subdir=getattr(args, "subdir", None))

    # Determine category
    category_info = get_category(data['title'], data.get('tags', []))

    # Prepare index entry data
    entry_data = {
        "title": data['title'],
        "channel": data['channel'],
        "date": formatted_date,
        "url": url,
        "category_id": category_info["id"],
        "filepath": str(filepath)
    }
    # Derive the collection from where the file actually landed, not from the raw flag —
    # a subdir that sanitizes to empty falls back to the root and gets no collection tag.
    if filepath.parent != LIBRARY_DIR:
        entry_data["collection"] = filepath.parent.name

    update_queue(url, data['title'], data['channel'], filepath)
    update_index(entry_data)
    return True


def main() -> None:
    # Initialize Directories
    initialize_directories()

    parser = argparse.ArgumentParser(description="The Librarian: Extract video transcripts from YouTube and TikTok.")
    parser.add_argument("url", nargs="?", help="YouTube or TikTok URL to process")
    parser.add_argument("--batch-profile", help="Process all videos from a TikTok/YouTube profile URL")
    parser.add_argument("--limit", type=int, help="Limit number of videos to process in batch mode")
    parser.add_argument("--delay", type=int, default=45, help="Delay in seconds between videos in batch mode (default: 45)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just show output")
    parser.add_argument("--analysis-file", help="Path to a markdown file containing pre-generated analysis to save")
    parser.add_argument("--no-whisper", action="store_true", help="Disable Whisper fallback for videos without transcripts")
    parser.add_argument("--subdir", help="File the report under library/<subdir>/ instead of the library root (topic collection)")

    args = parser.parse_args()

    # Batch profile mode
    if args.batch_profile:
        urls = get_profile_video_urls(args.batch_profile, limit=args.limit)
        if not urls:
            logger.error("No videos found on profile.")
            sys.exit(1)

        # Check which URLs are already in the index to skip duplicates
        index_yaml_path = LIBRARY_DIR / "index.yaml"
        existing_urls = set()
        if index_yaml_path.exists():
            import yaml
            with open(index_yaml_path, "r", encoding="utf-8") as f:
                index_data = yaml.safe_load(f) or {"entries": []}
            existing_urls = {e.get("url") for e in index_data.get("entries", [])}

        succeeded = 0
        failed = 0
        skipped = 0
        total = len(urls)

        for i, url in enumerate(urls):
            if url in existing_urls:
                logger.info(f"[{i+1}/{total}] SKIP (already in library): {url}")
                skipped += 1
                continue

            logger.info(f"\n{'='*60}")
            logger.info(f"[{i+1}/{total}] Processing: {url}")
            logger.info(f"{'='*60}")

            if process_single_video(url, args):
                succeeded += 1
            else:
                failed += 1

            # Delay between videos (skip delay after last video)
            if i < total - 1 and args.delay > 0:
                logger.info(f"[*] Waiting {args.delay}s before next video...")
                time.sleep(args.delay)

        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH COMPLETE: {succeeded} succeeded, {failed} failed, {skipped} skipped (already in library)")
        logger.info(f"{'='*60}")
        return

    # Single URL mode
    if not args.url:
        parser.error("Either url or --batch-profile is required")

    url = args.url

    # URL Guard: Regex check for valid YouTube or TikTok URL
    supported_url_regex = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be|tiktok\.com)/.+$'
    )
    if not supported_url_regex.match(url):
        logger.error(f"Error: \"{url}\" is not a valid YouTube or TikTok URL.")
        sys.exit(1)

    if not process_single_video(url, args):
        logger.error("CRITICAL ERROR: Processing failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
