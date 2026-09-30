import os
import re
import logging
import unicodedata
from pathlib import Path
from typing import Optional, List

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
LIBRARY_DIR = Path(os.getenv("LIBRARY_DIR", "library"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", "scripts/temp"))

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

ORIGINAL_ENGLISH_SUB_LANG = "en-orig"


def has_manual_english_subs(metadata: dict) -> bool:
    """True if yt-dlp metadata lists a human-made English subtitle track."""
    return any(
        lang.lower().startswith("en")
        for lang in (metadata.get("subtitles") or {})
    )


def select_subtitle(filenames: List[str], base_name: str, prefer_original: bool = False) -> Optional[str]:
    """
    Select subtitle file from list of filenames, prioritizing manual over auto.
    Locale-agnostic regex to catch variants like .en-US.srt, .en-GB.srt, and .vtt files.
    Supports both SRT and VTT formats (TikTok serves VTT).

    With prefer_original=True, an en-orig file wins outright. On auto-dubbed YouTube
    videos the plain "en" auto track can be translated back from a dub; en-orig is
    the speech recognition of the original audio. Pass it only when the video has no
    manual English track, since en-orig is auto-generated too.
    """
    # Pattern: base_name.LOCALE.[auto.]srt or base_name.LOCALE.[auto.]vtt
    # Group 1: Locale (e.g., en, en-US), Group 2: .auto/ .auto-subs (optional)
    pattern = re.compile(rf"^{re.escape(base_name)}\.([a-zA-Z0-9-]+)(\.auto(?:-subs)?)?\.(srt|vtt)$", re.IGNORECASE)
    
    manual_matches = []
    auto_matches = []
    
    for f in filenames:
        match = pattern.match(f)
        if match:
            if prefer_original and match.group(1).lower() == ORIGINAL_ENGLISH_SUB_LANG:
                return f
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

def initialize_directories() -> None:
    """
    Ensures the yt-dlp scratch directory exists. library/ is created by the
    save that writes to it, so --dry-run never creates it.
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def apply_replacements(content: str) -> str:
    """
    Apply find-replace rules from config/replacements.yaml.
    Returns content with all replacements applied.
    """
    import yaml
    
    replacements_path = Path("config/replacements.yaml")
    if not replacements_path.exists():
        return content
    
    try:
        with open(replacements_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        rules = config.get("replacements") or []
        if not rules:
            return content
        
        for rule in rules:
            find_text = rule.get("find", "")
            replace_text = rule.get("replace", "")
            case_sensitive = rule.get("case_sensitive", False)
            
            if not find_text:
                continue
            
            if case_sensitive:
                content = content.replace(find_text, replace_text)
            else:
                # Case-insensitive replacement
                pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                content = pattern.sub(replace_text, content)
        
        return content
        
    except Exception as e:
        logger.warning(f"Failed to apply replacements: {e}")
        return content


