import os
import json
import subprocess
from pathlib import Path

# --- Configuration Centralization ---
OLLAMA_MODEL = "deepseek-r1:14b"
OLLAMA_URL = "http://localhost:11434/api/generate"  # Reference URL
LIBRARY_DIR = Path("library")
SYNTHESIS_DIR = Path("synthesis")
TEMP_DIR = Path("scripts/temp")
GLOBAL_LIBRARY_PATH = Path("/Users/eriksjaastad/projects/agent-skills-library")

def run_ollama_command(prompt: str, system_prompt: str = None, timeout: int = 300) -> str:
    """
    Standardized Ollama CLI wrapper.
    Standardizes all LLM calls to use the local Ollama CLI.
    """
    cmd = ["ollama", "run", OLLAMA_MODEL, prompt]
    
    # Note: Ollama CLI 'run' command doesn't have a direct --system-prompt flag like the API.
    # We prepending the system prompt to the main prompt for CLI compatibility.
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
    
    cmd = ["ollama", "run", OLLAMA_MODEL, full_prompt]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        # DeepSeek-R1 often includes <think> blocks; stripping them for standard output
        import re
        response = result.stdout.strip()
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
        return response
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Critical: Ollama CLI request timed out after {timeout}s")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Critical: Ollama CLI failed with error: {e.stderr}")
    except Exception as e:
        raise RuntimeError(f"Critical: Ollama CLI not responsive. {str(e)}")

import hashlib

def create_temp_dir_name(url: str) -> str:
    """Generate a unique temporary directory name based on YouTube URL."""
    hash_object = hashlib.sha256(url.encode())
    return hash_object.hexdigest()

def select_subtitle(filenames: list, base_name: str) -> str:
    """Select subtitle file from list of filenames, prioritizing manual over auto."""
    manual_subtitle = f"{base_name}.en.srt"
    auto_subtitle = f"{base_name}.en.auto-subs.srt"
    
    if manual_subtitle in filenames:
        return manual_subtitle
    elif auto_subtitle in filenames:
        return auto_subtitle
    return None

def validate_json_data(data: dict) -> tuple:
    """Validate JSON data contains required keys for the global library."""
    required_keys = {"SKILL_MD", "RULE_MD", "README_MD"}
    missing_keys = required_keys - data.keys()
    
    if missing_keys:
        return False, f"Validation Failed: Missing required keys: {missing_keys}"
    return True, None

def check_environment():
    """
    Proactive health check for critical dependencies.
    """
    import shutil
    
    # Check yt-dlp
    if not shutil.which("yt-dlp"):
        print("[!] Critical: yt-dlp not found in PATH. Install via 'brew install yt-dlp'.")
        return False
        
    # Check Ollama CLI
    if not shutil.which("ollama"):
        print("[!] Critical: Ollama CLI not found in PATH. Install from https://ollama.com.")
        return False
        
    # Check Ollama Service responsiveness
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True, timeout=10)
    except Exception:
        print("[!] Critical: Ollama CLI not responsive. Is the service running?")
        return False
        
    return True

# Initialize directories
for d in [LIBRARY_DIR, SYNTHESIS_DIR, TEMP_DIR]:
    os.makedirs(d, exist_ok=True)

