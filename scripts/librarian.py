import os
import sys
import json
import subprocess
import re
from datetime import datetime
from scripts.config import LIBRARY_DIR, TEMP_DIR, run_ollama_command, check_environment, create_temp_dir_name, select_subtitle, initialize_directories

def clean_srt(srt_content):
    """
    Cleans SRT file content by removing indices, timestamps, and deduplicating lines.
    Optimized for Gemini 3 Flash long-context processing.
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

def get_video_data(url):
    """
    Uses yt-dlp to fetch video metadata and SRT transcript.
    Prioritizes manual subtitles over auto-generated ones.
    """
    unique_temp = os.path.join(TEMP_DIR, create_temp_dir_name(url))
    if not os.path.exists(unique_temp):
        os.makedirs(unique_temp)
        
    print(f"[*] Fetching metadata for: {url}")
    
    cmd_info = [
        "yt-dlp",
        "--skip-download",
        "--print-json",
        url
    ]
    result = subprocess.run(cmd_info, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Error fetching metadata: {result.stderr}")
        return None
    
    metadata = json.loads(result.stdout)
    
    print("[*] Fetching manual and auto-subtitles...")
    sub_path_base = os.path.join(unique_temp, "transcript")
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
    subprocess.run(cmd_subs, capture_output=True, text=True)
    
    srt_files = [f for f in os.listdir(unique_temp) if f.endswith('.srt')]
    transcript = ""
    target_file = select_subtitle(srt_files, "transcript")
        
    if target_file:
        target_path = os.path.join(unique_temp, target_file)
        with open(target_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
            transcript = clean_srt(srt_content)
        for f in os.listdir(unique_temp):
            try:
                os.remove(os.path.join(unique_temp, f))
            except OSError as e:
                print(f"[!] Failed to remove temp file {f}: {e}")
        try:
            os.rmdir(unique_temp)
        except OSError:
            pass
    else:
        print("[!] No SRT transcript found.")
        
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

def analyze_with_ollama(data):
    """
    Calls local Ollama to analyze the transcript.
    Returns None on failure to prevent data corruption.
    """
    print(f"[*] Analyzing with Ollama CLI (Full Context Enabled)...")
    
    prompt = f"""
You are "The Librarian," a senior AI automation engineer. Your goal is to analyze the following YouTube video transcript and extract high-density, architecturally-focused insights.

### Video Metadata
Title: {data['title']}
Channel: {data['channel']}
URL: {data['url']}
Views: {data['view_count']}
Likes: {data['like_count']}
Duration: {data['duration_string']}

### Full Transcript
{data['transcript']}

---

### Instructions
Generate a structured report in Markdown format. Return ONLY the Markdown content.
"""

    try:
        return run_ollama_command(prompt)
    except Exception as e:
        print(f"[!] Analysis failed: {e}")
        return None

def save_to_library(data, analysis):
    """
    Saves the final report to the library/ directory.
    Uses video_id to prevent filename collisions.
    """
    date_str = data.get('date')
    if date_str and len(date_str) == 8:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        formatted_date = datetime.now().strftime("%Y-%m-%d")
        
    clean_title = re.sub(r'[^\w\s-]', '', data['title']).strip()
    clean_title = re.sub(r'[-\s]+', '-', clean_title)
    
    vid_id = data.get('video_id', 'unknown')[:8]
    filename = f"{formatted_date}_{data['channel'].replace(' ', '_')}_{clean_title[:40]}_{vid_id}.md"
    filepath = os.path.join(LIBRARY_DIR, filename)
    
    tags = ["p/analyze-youtube-videos", "type/knowledge-extraction"]
    if data.get('tags'):
        tags.extend([f"topic/{t.lower().replace(' ', '-')}" for t in data['tags'][:5]])
        
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

# [[{data['title']}]]

{analysis}

---

## Full Transcript
{data['transcript']}
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"[+] Saved to: {filepath}")
    return filepath

def update_queue(url, title, channel, filepath):
    """
    Moves a URL from the Priority Queue to the Analyzed section in VIDEOS_QUEUE.md.
    """
    queue_file = "VIDEOS_QUEUE.md"
    if not os.path.exists(queue_file):
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
        with open(queue_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"[*] Updated {queue_file}: Moved to Analyzed.")

def update_index(title, channel, date, filepath):
    """
    Updates the library/00_Index_Library.md file with the new entry.
    """
    index_file = "library/00_Index_Library.md"
    if not os.path.exists(index_file):
        print(f"[!] Index file not found: {index_file}")
        return

    with open(index_file, 'r', encoding='utf-8') as f:
        content = f.read()

    category = "## 🤖 AI & Automation"
    if "diet" in title.lower() or "fat" in title.lower() or "health" in title.lower():
        category = "## 🥗 Health & Diet"
    elif "business" in title.lower() or "strategy" in title.lower():
        category = "## 💡 Content Strategy & Business"

    entry = f"- [[{title}]] ({channel}) - *Analyzed {date}*\n"
    if f"[[{title}]]" in content:
        return

    if category in content:
        parts = content.split(category)
        new_content = parts[0] + category + "\n" + entry + parts[1]
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[*] Updated {index_file}: Added to {category}")

def main():
    # Proactive Health Check
    if not check_environment():
        sys.exit(1)

    # Initialize Directories
    initialize_directories()

    if len(sys.argv) < 2:
        print("Usage: python scripts/librarian.py [YouTube URL]")
        sys.exit(1)
        
    url = sys.argv[1]
    data = get_video_data(url)
    if not data:
        print("[!] Failed to get video data.")
        sys.exit(1)
        
    analysis = analyze_with_ollama(data)
    if analysis is None:
        print("[!] CRITICAL ERROR: Analysis failed. Aborting to prevent library corruption.")
        sys.exit(1)
        
    date_str = data.get('date')
    if date_str and len(date_str) == 8:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        formatted_date = datetime.now().strftime("%Y-%m-%d")
        
    filepath = save_to_library(data, analysis)
    update_queue(url, data['title'], data['channel'], filepath)
    update_index(data['title'], data['channel'], formatted_date, filepath)

if __name__ == "__main__":
    main()
