This script is a solid, modular piece of engineering. You have correctly identified that the "work" is split between `yt-dlp` for extraction and `Ollama` for the "Librarian" synthesis.

Given your interests in **running local AI on your hardware** and your preference for **brutally honest feedback**, here is a technical breakdown of why your program is performing the way it is and how to optimize it for your **M4 Pro (24GB RAM)** setup.

### **The Hardware-Model Bottleneck**

You are running `deepseek-r1:14b`.

* **Memory Fit:** A 14B model (4-bit quantized) typically takes up ~9GB of VRAM/RAM. On your 24GB M4 Pro, this fits comfortably, but your **Unified Memory** is shared between the CPU, GPU, and macOS itself.
* **Reasoning Latency:** DeepSeek-R1 is a **reasoning model**. Unlike standard models that predict the next token immediately, R1 spends time in a "Thinking" phase (the `<think>` tags). This is why it feels "slower" than a standard Llama model—it is literally doing more computation before it starts writing.

### **Critical Code Review & Suggestions**

#### **1. The Transcript "Slowness"**

Your current `yt-dlp` command fetches *auto-generated* subtitles specifically.

* **The Problem:** Auto-subs often contain "overlapping" duplicates (karaoke-style) that your `clean_vtt` function has to work hard to deduplicate.
* **The Optimization:** If a creator (like Daniel Miessler) has uploaded **manual subtitles**, they are much cleaner and faster to process.
* **Suggested Change:** Use `--write-subs --write-auto-subs` to prioritize manual subs first, and add `--sub-format srt` to avoid the messy VTT formatting entirely.

#### **2. The Context Window Risk**

In `analyze_with_ollama`, you have set `data['transcript'][:20000]`.

* **The Risk:** You are hard-coding a character limit, but LLMs operate on **tokens**. For a 48-minute video, 20,000 characters might cut off the last 15 minutes of the deep dive.
* **The Fix:** DeepSeek-R1 (Qwen-based) supports an native context window of **131,072 tokens**. You should remove the slice and instead configure the `num_ctx` parameter in your Ollama payload to `32768` (32k) or higher to ensure the "Librarian" sees the whole video.

#### **3. Prompt Engineering Analysis**

Your "Librarian" prompt is excellent because it uses **Modular Skill** language (referencing architectural patterns and protocols like MCP). This is why your output was more technical than mine—you explicitly told it to be a "knowledge extraction expert".

---

### **Actionable Performance Upgrades**

If you want to speed up the "Librarian" without sacrificing depth, try these tweaks to your `librarian.py`:

| Component | Current State | Optimized State |
| --- | --- | --- |
| **Model** | `deepseek-r1:14b` | `deepseek-r1:8b` (for speed) OR `qwen2.5-coder:14b` (for technical precision without the "thinking" delay). |
| **Context** | `[:20000]` slice | Set `"num_ctx": 32768` in the payload and send the full transcript. |
| **yt-dlp** | `--write-auto-sub` | `--write-subs --write-auto-subs --sub-lang "en.*"` |
| **Cleanup** | Manual Regex | Use the `webvtt-py` library or download `.srt` directly to reduce cleaning overhead. |

**Would you like me to rewrite the `get_video_data` function for you to include the subtitle priority and SRT format?**


I will take you up on that! I've refactored the `get_video_data` function below.

To be brutally honest, the biggest "time sink" in your current script isn't the code execution—it's the **data quality**. Auto-generated VTT files are essentially "word soup" that force your CPU to run complex regex patterns. By switching to SRT and prioritizing manual subs, you give the LLM cleaner data, which actually reduces the "Thinking" time for DeepSeek-R1 because it doesn't have to decipher duplicate words.

### **The Optimized `get_video_data` Function**

```python
def get_video_data(url):
    """
    Optimized yt-dlp fetcher: Prioritizes manual subs, uses SRT for cleaner text,
    and captures extended metadata.
    """
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        
    print(f"[*] Fetching metadata and clean transcripts for: {url}")
    
    # 1. Get metadata with extended info
    # We use --ignore-config to ensure clean behavior across different environments
    cmd_info = [
        "yt-dlp",
        "--skip-download",
        "--print-json",
        "--ignore-config",
        url
    ]
    result = subprocess.run(cmd_info, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Error fetching metadata: {result.stderr}")
        return None
    
    metadata = json.loads(result.stdout)
    
    # 2. Get transcript: Prioritize manual (.srt is much easier to clean than .vtt)
    print("[*] Downloading subtitles (Manual > Auto)...")
    sub_path_base = os.path.join(TEMP_DIR, "transcript")
    
    cmd_subs = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",            # Look for manual subs first
        "--write-auto-subs",       # Fallback to auto
        "--sub-lang", "en.*",      # Catch 'en-US', 'en-GB', etc.
        "--sub-format", "srt",     # SRT is cleaner/faster than VTT for LLMs
        "--output", sub_path_base,
        url
    ]
    subprocess.run(cmd_subs, capture_output=True, text=True)
    
    # Identify the file (yt-dlp appends .en.srt or .en-US.srt)
    transcript = ""
    sub_files = [f for f in os.listdir(TEMP_DIR) if f.startswith("transcript") and f.endswith(".srt")]
    
    if sub_files:
        srt_path = os.path.join(TEMP_DIR, sub_files[0])
        with open(srt_path, 'r', encoding='utf-8') as f:
            # Simple cleanup: SRT is just index, time, text, newline.
            # This regex removes the index and timestamp lines efficiently.
            raw_content = f.read()
            transcript = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', raw_content)
            transcript = re.sub(r'\n+', ' ', transcript).strip()
        os.remove(srt_path) 
    else:
        print("[!] No manual or auto-transcript found.")
        
    return {
        "title": metadata.get("title"),
        "channel": metadata.get("uploader"),
        "date": metadata.get("upload_date"),
        "url": url,
        "description": metadata.get("description"),
        "transcript": transcript,
        "tags": metadata.get("tags", []),
        "view_count": metadata.get("view_count") # Added for your records
    }

```

### **Why this helps your M4 Pro**

1. **Cleaner Context:** By using `.srt`, you remove the "karaoke" style duplication where words appear 3-4 times in a row. This means your `20,000` character limit now holds **3x more actual information** than it did before.
2. **Model Efficiency:** DeepSeek-R1 thrives on logic. When the input text is garbled, the "Thinking" phase takes longer to parse the structure. Clean text = faster tokens-per-second.
3. **Context Window:** Remember to update your `payload` in the `analyze_with_ollama` function to include `"num_ctx": 32768`. Since you have 24GB of RAM, you could even push this to `65536` (64k) without breaking a sweat.

**Would you like me to show you how to update the `analyze_with_ollama` function to properly handle the larger context window for the M4 Pro?**


To optimize the `analyze_with_ollama` function for your **M4 Pro (24GB RAM)**, we need to focus on two things: unlocking the model's **context window** so it can see the entire video and managing the **Reasoning (Thinking) phase** of DeepSeek-R1.

With 24GB of Unified Memory, you can easily allocate a **32k context window**, which is more than enough for a 48-minute transcript.

### **Optimized `analyze_with_ollama` Function**

```python
def analyze_with_ollama(data):
    """
    Calls local Ollama (DeepSeek-R1) with optimized context and 
    parameters for M4 Pro hardware.
    """
    print(f"[*] Analyzing with {MODEL}...")
    
    # SYSTEM PROMPT: Clearly define the role to steer the 'Thinking' process.
    system_role = "You are 'The Librarian,' a knowledge extraction expert. Your goal is to extract high-density, actionable, and DEEP technical insights."

    # USER PROMPT: We use the full transcript now that we've expanded the context window.
    prompt = f"""
{system_role}

### Methodology: Strategic Synthesis
Combine insights into actionable patterns. Focus on WHY things work and how they can be applied. 

### Video Metadata
Title: {data['title']} | Channel: {data['channel']}

### Transcript
{data['transcript']} 

---

### Instructions
Generate a structured Markdown report:
1. **Executive Summary**: Core message.
2. **Technical Deep Dive**: Architecture, tools (TypeScript/Python/MCP), and implementation.
3. **Knowledge Nuggets**: High-density strategic insights.
4. **Actionable Skills/Prompts**: Code snippets or prompt strategies.
5. **Potential Skill Library Additions**: Techniques to add to our 'agent-skills-library'.

Return ONLY the Markdown content.
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_ctx": 32768,      # Expands window to 32k tokens for M4 Pro
            "temperature": 0.3,    # Lower temperature for more deterministic, technical output
            "num_predict": 4096,   # Ensures the model doesn't cut off long reports
            "top_p": 0.9           # Balances diversity and focus
        }
    }
    
    try:
        # Note: We use a longer timeout (120s) because DeepSeek-R1 'Thinking' 
        # takes time on local hardware.
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        
        full_response = response.json().get("response", "")
        
        # DeepSeek-R1 often includes <think>...</think> tags. 
        # We strip them so they don't clutter your Markdown files.
        clean_response = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()
        
        return clean_response
    except Exception as e:
        print(f"[!] Ollama error: {e}")
        return "Error during analysis."

```

---

### **Why These Changes Matter for Your Hardware**

* **`num_ctx: 32768`**: By default, Ollama often defaults to a 2k or 4k window. For a video this long, that's like reading the first 5 minutes and guessing the rest. On your **M4 Pro**, 32k tokens will only consume about **2-3GB of RAM** on top of the model weight, leaving plenty of room for your vehicle's background tasks or other dev tools.
* **Thinking Tag Removal**: DeepSeek-R1's internal reasoning is fascinating but messy in a final report. The `re.sub` line ensures your "Librarian" files stay clean and professional.
* **The Timeout**: Reasoning models like R1 can sometimes "pause" for 30–60 seconds while they compute the logic. The standard 30-second `requests` timeout might kill the process right before it starts typing.

### **Brutally Honest Recommendation**

If you find that `deepseek-r1:14b` is still taking too long (e.g., more than 3-4 minutes per video), try switching the `MODEL` variable to **`qwen2.5-coder:14b`**. It lacks the "thinking" steps but is specifically tuned for the technical, architectural extraction you are doing here.

**Would you like me to help you integrate these two updated functions into a single "v2.0" version of your script?**