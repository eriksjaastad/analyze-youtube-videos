import os
import json
import subprocess
import hashlib
import requests
import re
import shutil
from pathlib import Path

# --- Configuration Centralization ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
LIBRARY_DIR = Path(os.getenv("LIBRARY_DIR", "library"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "scripts/temp"))
GLOBAL_LIBRARY_PATH = Path(os.getenv("SKILLS_LIBRARY_PATH", "./agent-skills-library"))
SYNTHESIS_DIR = Path(os.getenv("SYNTHESIS_DIR", "synthesis"))

def check_ollama_health():
    """Health check for Ollama CLI responsiveness."""
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False

def run_ollama_command(prompt: str, system_prompt: str = None, timeout: int = 300) -> str:
    """
    Standardized Ollama CLI wrapper.
    Standardizes all LLM calls to use the local Ollama CLI.
    """
    if not check_ollama_health():
        raise RuntimeError(f"Critical: Ollama is not running at {OLLAMA_URL}. Start it with: ollama serve")

    # Construct the full prompt for the CLI
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
    
    cmd = ["ollama", "run", OLLAMA_MODEL, full_prompt]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Ollama command timed out after {timeout} seconds.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ollama command failed with exit code {e.returncode}: {e.stderr}")

def validate_json_data(data: dict) -> tuple:
    """Validate JSON data contains required keys for the global library."""
    required_keys = {"SKILL_MD", "RULE_MD", "README_MD"}
    if not isinstance(data, dict):
        return False, "Validation Failed: Input is not a dictionary."
    
    if not required_keys.issubset(data.keys()):
        missing = required_keys - set(data.keys())
        return False, f"Validation Failed: Missing required keys: {missing}"
    return True, None

def create_temp_dir_name(url: str) -> str:
    """Generate a unique temporary directory name based on YouTube URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"transcript_{url_hash}"

def select_subtitle(filenames: list, base_name: str) -> str:
    """
    Select subtitle file from list of filenames, prioritizing manual over auto.
    Locale-agnostic regex to catch variants like .en-US.srt and .en-GB.srt.
    """
    # Pattern: base_name.LOCALE.srt or base_name.LOCALE.auto.srt
    # Group 1: Locale (e.g., en, en-US), Group 2: .auto/ .auto-subs (optional)
    pattern = re.compile(rf"^{re.escape(base_name)}\.([a-zA-Z0-9-]+)(\.auto(?:-subs)?)?\.srt$", re.IGNORECASE)
    
    manual_matches = []
    auto_matches = []
    
    for f in filenames:
        match = pattern.match(f)
        if match:
            is_auto = match.group(2) is not None
            if is_auto:
                auto_matches.append(f)
            else:
                manual_matches.append(f)
    
    # Priority 1: Manual Subtitles (often higher quality)
    if manual_matches:
        # Sort to ensure deterministic behavior (e.g., en before en-US if both exist)
        manual_matches.sort()
        return manual_matches[0]
    
    # Priority 2: Auto-generated Subtitles
    if auto_matches:
        auto_matches.sort()
        return auto_matches[0]
        
    return None

def check_environment():
    """
    Proactive health check for critical dependencies.
    """
    # Check yt-dlp
    if not shutil.which("yt-dlp"):
        print("[!] Critical: yt-dlp not found in PATH. Install via 'brew install yt-dlp'.")
        return False
        
    # Check Ollama CLI
    if not shutil.which("ollama"):
        print("[!] Critical: Ollama CLI not found in PATH. Install from https://ollama.com.")
        return False
        
    # Check Ollama Service responsiveness
    if not check_ollama_health():
        print(f"[!] Critical: Ollama is not running. Start it with: ollama serve")
        return False
        
    return True

def initialize_directories():
    """
    Ensures all necessary directories exist.
    """
    for d in [LIBRARY_DIR, SYNTHESIS_DIR, TEMP_DIR]:
        d.mkdir(parents=True, exist_ok=True)
