import os
import subprocess
import hashlib
import re
import shutil
import logging
import unicodedata
from pathlib import Path
from typing import Optional, Tuple, List

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("warden")

# --- Configuration Centralization ---
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
LIBRARY_DIR = Path(os.getenv("LIBRARY_DIR", "library"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "scripts/temp"))
GLOBAL_LIBRARY_PATH = Path(os.getenv("SKILLS_LIBRARY_PATH", "./agent-skills-library"))
SYNTHESIS_DIR = Path(os.getenv("SYNTHESIS_DIR", "synthesis"))

# Health check cache to minimize CLI latency
_OLLAMA_HEALTH_VERIFIED = False

def safe_slug(text: str) -> str:
    """
    Sanitizes text for use in file names and paths.
    Uses unicodedata and re for robust cleaning.
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    # Replace non-word characters with hyphens and lowercase
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '-', text)

def check_ollama_health() -> bool:
    """Health check for Ollama CLI responsiveness."""
    try:
        subprocess.run(["ollama", "list"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False

def run_ollama_command(prompt: str, system_prompt: Optional[str] = None, timeout: int = 300) -> str:
    """
    Standardized Ollama CLI wrapper.
    Standardizes all LLM calls to use the local Ollama CLI.
    """
    global _OLLAMA_HEALTH_VERIFIED
    
    if not _OLLAMA_HEALTH_VERIFIED:
        if not check_ollama_health():
            raise RuntimeError("Critical: Ollama is not running. Start it with: ollama serve")
        _OLLAMA_HEALTH_VERIFIED = True

    # Construct the full prompt for the CLI
    full_prompt = prompt
    if system_prompt:
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
    
    cmd = ["ollama", "run", OLLAMA_MODEL, full_prompt]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=timeout)
        response = result.stdout.strip()
        
        # Strip DeepSeek-R1 internal monologue
        return re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Ollama command timed out after {timeout} seconds.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ollama command failed with exit code {e.returncode}: {e.stderr}")

def validate_json_data(data: Optional[dict]) -> Tuple[bool, Optional[str]]:
    """Validate JSON data contains required keys for the global library."""
    required_keys = {"SKILL_MD", "RULE_MD", "README_MD"}
    if data is None or not isinstance(data, dict):
        return False, "Validation Failed: Input is not a dictionary."
    
    if not required_keys.issubset(data.keys()):
        missing = required_keys - set(data.keys())
        return False, f"Validation Failed: Missing required keys: {missing}"
    return True, None

def create_temp_dir_name(url: str) -> str:
    """Generate a unique temporary directory name based on YouTube URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"transcript_{url_hash}"

def select_subtitle(filenames: List[str], base_name: str) -> Optional[str]:
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

def check_environment() -> bool:
    """
    Proactive health check for critical dependencies and paths.
    Refuses to start if misconfigured.
    """
    global _OLLAMA_HEALTH_VERIFIED
    
    # Check yt-dlp
    if not shutil.which("yt-dlp"):
        logger.error("Critical: yt-dlp not found in PATH. Install via 'brew install yt-dlp'.")
        return False
        
    # Check Ollama CLI
    if not shutil.which("ollama"):
        logger.error("Critical: Ollama CLI not found in PATH. Install from https://ollama.com.")
        return False
        
    # Check Ollama Service responsiveness
    if not check_ollama_health():
        logger.error("Critical: Ollama is not running. Start it with: ollama serve")
        return False
    
    # Check critical paths and writability
    critical_paths = [LIBRARY_DIR, SYNTHESIS_DIR, TEMP_DIR]
    for path in critical_paths:
        try:
            path.mkdir(parents=True, exist_ok=True)
            # Test writability
            test_file = path / ".warden_test"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            logger.error(f"Critical: Path {path} is not writable or cannot be created: {e}")
            return False

    _OLLAMA_HEALTH_VERIFIED = True
    logger.info("Environment check passed.")
    return True

def initialize_directories() -> None:
    """
    Ensures all necessary directories exist.
    """
    for d in [LIBRARY_DIR, SYNTHESIS_DIR, TEMP_DIR]:
        d.mkdir(parents=True, exist_ok=True)
