import os
import sys
import json
import subprocess
import re
import requests
from datetime import datetime

# --- Configuration ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "deepseek-r1:14b" # User can update this to a long-context model or use Cursor
LIBRARY_DIR = "library"
TEMP_DIR = "scripts/temp"

def clean_srt(srt_content):
    """
    Cleans SRT file content by removing indices, timestamps, and deduplicating lines.
    Optimized for Gemini 3 Flash long-context processing.
    """
    # Remove timestamps and indices
    # SRT format:
    # 1
    # 00:00:00,000 --> 00:00:01,000
    # Text
    
    lines = srt_content.splitlines()
    cleaned_lines = []
    
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}')
    index_pattern = re.compile(r'^\d+$')
    
    last_line = ""
    for line in lines:
        line = line.strip()
        # Skip empty lines, indices, and timestamps
        if not line or index_pattern.match(line) or timestamp_pattern.match(line):
            continue
        
        # Remove HTML-like tags
        line = re.sub(r'<[^>]+>', '', line)
        
        # Simple deduplication
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
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        
    print(f"[*] Fetching metadata for: {url}")
    
    # 1. Get robust metadata
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
    
    # 2. Get transcript (Prioritize manual SRT)
    print("[*] Fetching manual and auto-subtitles...")
    sub_path_base = os.path.join(TEMP_DIR, "transcript")
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
    
    # Check for manual sub first, then auto
    manual_sub = f"{sub_path_base}.en.srt"
    auto_sub = f"{sub_path_base}.en.auto-subs.srt" # yt-dlp often uses this naming for auto-subs
    
    # Sometimes it might just be .en.srt regardless of manual/auto depending on yt-dlp version
    # We check all .srt files in the temp dir
    srt_files = [f for f in os.listdir(TEMP_DIR) if f.endswith('.srt')]
    
    transcript = ""
    target_file = None
    
    # Prioritize manual if identified, otherwise take whatever is there
    if os.path.exists(manual_sub):
        target_file = manual_sub
    elif srt_files:
        target_file = os.path.join(TEMP_DIR, srt_files[0])
        
    if target_file and os.path.exists(target_file):
        with open(target_file, 'r', encoding='utf-8') as f:
            srt_content = f.read()
            transcript = clean_srt(srt_content)
        # Clean up ALL srt files in temp
        for f in srt_files:
            try: os.remove(os.path.join(TEMP_DIR, f))
            except: pass
    else:
        print("[!] No SRT transcript found.")
        
    return {
        "title": metadata.get("title"),
        "channel": metadata.get("uploader"),
        "date": metadata.get("upload_date"),
        "url": url,
        "description": metadata.get("description"),
        "transcript": transcript,
        "tags": metadata.get("tags", []),
        "view_count": metadata.get("view_count"),
        "like_count": metadata.get("like_count"),
        "duration_string": metadata.get("duration_string")
    }

def analyze_with_ollama(data):
    """
    Calls local Ollama (or other router) to analyze the transcript.
    Optimized for Gemini 3 Flash's 1M context window.
    """
    print(f"[*] Analyzing with {MODEL} (Full Context Enabled)...")
    
    prompt = f"""
You are "The Librarian," a senior AI automation engineer. Your goal is to analyze the following YouTube video transcript and extract high-density, architecturally-focused insights.

### Methodology Reference: Strategic Synthesis
We want to combine insights into actionable patterns. Focus on WHY things work and how they can be applied to build robust AI systems.

### Analysis Goals:
- **Architectural Patterns**: Identify the high-level system designs mentioned.
- **Deterministic Tooling**: Detail any specific code, APIs, or deterministic processes that reduce reliance on "fuzzy" prompts.
- **Skill Modularity**: Explain how the concepts can be broken down into reusable skills for an agentic library.

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
Generate a structured report in Markdown format with the following sections:

1. **Executive Summary**: A high-level overview of the video's core message.
2. **Architectural Patterns**: Deep dive into the system designs and orchestration logic.
3. **Deterministic Tooling & Code**: Specific mentions of code-based solutions, TypeScript/Python logic, or APIs.
4. **Knowledge Nuggets**: Bullet points of the most valuable insights (strategic and technical).
5. **Actionable Skills/Prompts**: Specific prompt strategies or workflow steps found in the video.
6. **Potential Skill Library Additions**: Identify specific techniques from this video that should be added to our global "agent-skills-library".

Return ONLY the Markdown content for these sections.
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"[!] Ollama error: {e}")
        return "Error during analysis. Check if Ollama is running."

def save_to_library(data, analysis):
    """
    Saves the final report to the library/ directory.
    """
    if not os.path.exists(LIBRARY_DIR):
        os.makedirs(LIBRARY_DIR)
        
    date_str = data['date']
    if len(date_str) == 8:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        formatted_date = datetime.now().strftime("%Y-%m-%d")
        
    clean_title = re.sub(r'[^\w\s-]', '', data['title']).strip()
    clean_title = re.sub(r'[-\s]+', '-', clean_title)
    
    filename = f"{formatted_date}_{data['channel'].replace(' ', '_')}_{clean_title[:50]}.md"
    filepath = os.path.join(LIBRARY_DIR, filename)
    
    tags = ["p/analyze-youtube-videos", "type/knowledge-extraction"]
    if data['tags']:
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
    in_analyzed = False
    
    # Identify sections
    priority_marker = "### Priority Queue"
    analyzed_marker = "## Videos Analyzed"

    # Normalize URL for matching
    clean_url = url.split('?si=')[0].split('&si=')[0]

    for line in lines:
        if priority_marker in line:
            in_priority = True
            new_lines.append(line)
            continue
        if analyzed_marker in line:
            in_priority = False
            in_analyzed = True
            new_lines.append(line)
            # Add the new entry right after the marker
            if found:
                entry = f"- [x] **\"{title}\"** by {channel}\n"
                entry += f"  - **Date analyzed:** {datetime.now().strftime('%Y-%m-%d')}\n"
                entry += f"  - **URL:** {url}\n"
                entry += f"  - **Location:** `{filepath}`\n\n"
                new_lines.append(entry)
            continue
        
        # Check for URL in priority section
        if in_priority and clean_url in line:
            found = True
            continue # Skip adding it to priority
            
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

    # Determine category based on tags or simple heuristic
    # For now, we'll try to find the right section
    category = "## 🤖 AI & Automation" # Default
    if "diet" in title.lower() or "fat" in title.lower() or "health" in title.lower():
        category = "## 🥗 Health & Diet"
    elif "business" in title.lower() or "strategy" in title.lower():
        category = "## 💡 Content Strategy & Business"

    # Create the link entry
    entry = f"- [[{title}]] ({channel}) - *Analyzed {date}*\n"
    
    # Check if entry already exists
    if f"[[{title}]]" in content:
        return

    # Insert after category marker
    if category in content:
        parts = content.split(category)
        new_content = parts[0] + category + "\n" + entry + parts[1]
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[*] Updated {index_file}: Added to {category}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/librarian.py [YouTube URL]")
        sys.exit(1)
        
    url = sys.argv[1]
    
    data = get_video_data(url)
    if not data:
        print("[!] Failed to get video data.")
        sys.exit(1)
        
    analysis = analyze_with_ollama(data)
    filepath = save_to_library(data, analysis)
    
    # Format date for index
    date_str = data['date']
    if len(date_str) == 8:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        formatted_date = datetime.now().strftime("%Y-%m-%d")
        
    update_queue(url, data['title'], data['channel'], filepath)
    update_index(data['title'], data['channel'], formatted_date, filepath)

if __name__ == "__main__":
    main()

