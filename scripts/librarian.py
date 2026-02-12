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
from scripts.config import LIBRARY_DIR, TEMP_DIR, run_ollama_command, check_environment, select_subtitle, initialize_directories, safe_slug, logger, polish_with_cloud, apply_replacements

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
    Cleans SRT file content by removing indices, timestamps, and deduplicating lines.
    Optimized for long-context processing.
    """
    lines = srt_content.splitlines()
    cleaned_lines = []
    
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}')
    index_pattern = re.compile(r'^\d+$')
    
    last_line = ""
    for line in lines:
        line = line.strip()
        if not line or index_pattern.match(line) or timestamp_pattern.match(line):
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
                "--sub-lang", "en",
                "--sub-format", "srt",
                "--output", sub_path_base,
                url
            ]
            sub_result = run_with_retry(cmd_subs, timeout=120)
            if sub_result is None or sub_result.returncode != 0:
                error_msg = sub_result.stderr if sub_result else "Command failed after retries"
                logger.warning(f"Subtitle fetch command failed for {url}.")
                logger.debug(f"Stderr: {error_msg}")
            
            srt_files = [f for f in os.listdir(unique_temp) if f.endswith('.srt')]
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

            return {
                "title": metadata.get("title") or "Untitled",
                "channel": metadata.get("uploader") or "Unknown_Channel",
                "date": metadata.get("upload_date"),
                "url": url,
                "video_id": metadata.get("id") or "unknown",
                "description": metadata.get("description") or "",
                "transcript": transcript,
                "tags": metadata.get("tags", []) or [],
                "view_count": metadata.get("view_count") or 0,
                "like_count": metadata.get("like_count") or 0,
                "duration_string": metadata.get("duration_string") or "0:00",
                "chapters": chapters
            }
        except subprocess.TimeoutExpired as e:
            logger.error(f"Subprocess timed out: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_video_data: {e}")
            return None

def analyze_with_ollama(data: Dict[str, Any], timeout: int = 600) -> Optional[str]:
    """
    Calls local Ollama to analyze the transcript.
    Returns None on failure to prevent data corruption.
    """
    logger.info(f"[*] Analyzing with Ollama CLI (Full Context Enabled)...")
    
    prompt = f"""You are a senior technical writer creating a professional analysis document. Your task is to transform a YouTube video transcript into a structured, actionable report.

**VIDEO METADATA**
- Title: {data['title']}
- Channel: {data['channel']}
- Duration: {data['duration_string']}
- Views: {data['view_count']:,} | Likes: {data['like_count']:,}

**TRANSCRIPT TO ANALYZE**
{data['transcript']}

---

**YOUR OUTPUT MUST FOLLOW THIS EXACT STRUCTURE:**

## Video Overview

**Source:** "{data['title']}" by {data['channel']}
**Duration:** {data['duration_string']}

**Core Premise:** [1-2 sentences: What is the main argument or purpose of this video?]

---

## Key Concepts & Methodology

[Break down the video into its major sections/concepts. For each:
- Give it a descriptive heading
- Explain what was covered in 2-4 bullet points
- Include any specific tools, techniques, or frameworks mentioned]

---

## Actionable Takeaways

[List 5-10 specific, concrete actions a viewer could take. These should be practical and implementable, not vague advice. Format as a numbered list.]

---

## Notable Quotes & Insights

[Extract 3-5 of the most valuable quotes or insights from the video. Include context for why each matters.]

---

## Critical Assessment

**Strengths:** [What did this video do well?]

**Limitations:** [What was missing, unclear, or could be improved?]

**Best For:** [Who would benefit most from this video?]

---

## Related Concepts

[List related topics, tools, or frameworks mentioned that warrant further exploration. Use bullet points with brief descriptions.]

---

**IMPORTANT RULES:**
1. Write in clear, professional prose - no filler phrases like "In this video, we will..."
2. Extract SPECIFIC details (names, tools, numbers, techniques) - not vague summaries
3. Focus on WHAT the viewer can DO with this information
4. Do NOT include meta-commentary about your analysis process
5. Do NOT repeat the transcript - synthesize and distill it
6. Output ONLY the markdown content - no preamble or explanation
7. IGNORE sponsor segments and promotional content entirely
8. SKIP like and subscribe requests and channel/social media plugs
9. OMIT intro/outro fluff (Hey everyone welcome back, Before we get started)
10. FOCUS ONLY on substantive educational or informational content

BEGIN YOUR ANALYSIS:"""

    try:
        return run_ollama_command(prompt)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return None

def save_to_library(data: Dict[str, Any], analysis: str) -> Path:
    """
    Saves the final report to the library/ directory.
    Uses video_id and safe_slug to prevent filename collisions and ensure safety.
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
    filepath = LIBRARY_DIR / filename
    
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

def main() -> None:
    # Proactive Health Check
    if not check_environment():
        sys.exit(1)

    # Initialize Directories
    initialize_directories()

    parser = argparse.ArgumentParser(description="The Librarian: Extract and analyze YouTube transcripts.")
    parser.add_argument("url", help="YouTube URL to analyze")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files, just show analysis")
    parser.add_argument("--polish", action="store_true", help="Use cloud model (Gemini) to polish the analysis")
    parser.add_argument("--no-whisper", action="store_true", help="Disable Whisper fallback for videos without transcripts")

    args = parser.parse_args()
    url = args.url

    # URL Guard: Regex check for valid YouTube URL
    youtube_regex = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    )
    if not youtube_regex.match(url):
        logger.error(f"Error: \"{url}\" is not a valid YouTube URL.")
        sys.exit(1)

    data = get_video_data(url, use_whisper_fallback=not args.no_whisper)
    if not data:
        logger.error("Failed to get video data.")
        sys.exit(1)
        
    # Increased timeout for long transcripts
    analysis = analyze_with_ollama(data, timeout=900)
    if analysis is None:
        logger.error("CRITICAL ERROR: Analysis failed. Aborting to prevent library corruption.")
        sys.exit(1)
    
    # Optional polish step with cloud model
    if args.polish:
        logger.info("[*] Running polish step with Gemini...")
        polished = polish_with_cloud(analysis)
        if polished:
            analysis = polished
    
    # Apply find-replace rules from config/replacements.yaml
    analysis = apply_replacements(analysis)
        
    if args.dry_run:
        logger.info("--- DRY RUN: Analysis Report ---")
        logger.info(analysis)
        logger.info("--------------------------------")
        logger.info("✨ Dry run complete. No files written.")
        return

    date_str = data.get('date')
    if date_str and len(date_str) == 8:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        formatted_date = datetime.now().strftime("%Y-%m-%d")
        
    filepath = save_to_library(data, analysis)
    
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
    
    update_queue(url, data['title'], data['channel'], filepath)
    update_index(entry_data)

if __name__ == "__main__":
    main()
