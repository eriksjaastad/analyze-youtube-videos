import os
import re
import logging
import unicodedata
from pathlib import Path
from typing import Optional

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


def _first_english(tracks: Optional[dict]) -> Optional[str]:
    """The alphabetically first English language key (en, en-US, eng-US, ...), or None."""
    english = sorted(lang for lang in (tracks or {}) if lang.lower().startswith("en"))
    return english[0] if english else None


def choose_subtitle_track(metadata: dict) -> Optional[tuple[str, bool]]:
    """
    Pick the one English caption track to download, as (language, is_auto).

    Order: manual English, else en-orig, else any auto English track. None when
    the metadata lists no English track at all.

    One track, not several: yt-dlp makes one request per requested track and
    fails the whole call if any of them is rate-limited. On auto-captioned
    YouTube videos the plain "en" auto track is a machine translation
    (lang=xx&tlang=en; on auto-dubbed videos it comes from a dub), YouTube 429s
    those requests, and the fetch aborted even when en-orig, the recognition of
    the original audio, would have downloaded fine.
    """
    manual = _first_english(metadata.get("subtitles"))
    if manual:
        return manual, False
    auto = metadata.get("automatic_captions") or {}
    if ORIGINAL_ENGLISH_SUB_LANG in auto:
        return ORIGINAL_ENGLISH_SUB_LANG, True
    auto_english = _first_english(auto)
    return (auto_english, True) if auto_english else None

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


