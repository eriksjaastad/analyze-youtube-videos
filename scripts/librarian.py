import os
import os
import sys
import argparse
import tempfile
import json
import subprocess
import re
import yaml
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from scripts.config import LIBRARY_DIR, TEMP_DIR, run_ollama_command, check_environment, select_subtitle, initialize_directories, safe_slug, logger, polish_with_cloud, apply_replacements

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

def get_video_data(url: str) -> Optional[Dict[str, Any]]:
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
            result = subprocess.run(cmd_info, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Error fetching metadata: {result.stderr}")
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
            sub_result = subprocess.run(cmd_subs, capture_output=True, text=True, timeout=120)
            if sub_result.returncode != 0:
                logger.warning(f"Subtitle fetch command failed for {url}.")
                logger.debug(f"Stderr: {sub_result.stderr}")
            
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
                "duration_string": metadata.get("duration_string") or "0:00"
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
    
    args = parser.parse_args()
    url = args.url

    # URL Guard: Regex check for valid YouTube URL
    youtube_regex = re.compile(
        r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    )
    if not youtube_regex.match(url):
        logger.error(f"Error: \"{url}\" is not a valid YouTube URL.")
        sys.exit(1)

    data = get_video_data(url)
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
