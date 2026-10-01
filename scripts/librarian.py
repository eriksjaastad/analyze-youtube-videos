"""The Librarian: fetch YouTube, TikTok, and Instagram transcripts and file analysis reports.

Modes
-----
fetch-only (default)
    Run with just a url. Fetches metadata + transcript from the platform,
    adds research_targets, prints JSON (transcript, metadata, and
    research_targets) to stdout, and caches that same JSON under
    data/fetch_cache/<platform>-<video_id>.json so a later save can file
    the report without hitting the network again. Nothing is written to
    the library.

save (--analysis-file)
    Loads a pre-written markdown analysis, applies config/replacements.yaml,
    runs the claim-source audit (warns on empty Source cells, never blocks),
    writes the report to library/, updates library/index.yaml, re-renders
    library/00_Index_Library.md. Requires config/categories.yaml. Video data comes from
    --data-file when given, otherwise from a fetch cache file whose url
    matches, otherwise from a metadata-only fetch; save never downloads
    subtitles or audio.

    A channel on config/flagged_channels.yaml emits a warning in both fetch
    and save modes; the "flag" object only appears in the fetch JSON. It
    never blocks.

batch (--batch-profile)
    Processes every video on a YouTube or TikTok profile, skipping URLs
    already in library/index.yaml. Instagram profile batches are rejected.
    --limit caps the number of videos and --delay sets the seconds between
    videos. A YouTube HTTP 429 rate limit stops the batch immediately; any
    batch failure exits 1.

Supported platforms
-------------------
YouTube (youtube.com, youtu.be), TikTok (tiktok.com), and Instagram
(instagram.com) posts/reels.

CLI flags
---------
url
    YouTube, TikTok, or Instagram URL to process.
--batch-profile
    Process all videos from a TikTok/YouTube profile URL.
--limit
    Limit number of videos to process in batch mode.
--delay
    Delay in seconds between videos in batch mode (default: 45).
--dry-run
    Save mode only: show the report without writing anything to library/.
    Fetch mode ignores it and still writes data/fetch_cache, the input a
    later offline save needs.
--analysis-file
    Path to a markdown file containing pre-generated analysis to save.
--data-file
    Path to JSON previously printed by fetch mode to use as video data in
    save mode. Requires --analysis-file.
--no-whisper
    Disable Whisper fallback for videos without transcripts.
--subdir
    File the report under library/<subdir>/ instead of the library root.

Examples
--------
    uv run --with pyyaml scripts/librarian.py "https://www.youtube.com/watch?v=..."
    uv run --with pyyaml scripts/librarian.py "https://www.youtube.com/watch?v=..." --analysis-file /tmp/analysis.md
    uv run --with pyyaml scripts/librarian.py "https://www.youtube.com/watch?v=..." --analysis-file /tmp/analysis.md --subdir agentic-work
    uv run --with pyyaml scripts/librarian.py "https://www.youtube.com/watch?v=..." --analysis-file /tmp/analysis.md --data-file data/fetch_cache/youtube-abc123.json
    uv run --with pyyaml scripts/librarian.py --batch-profile "https://www.tiktok.com/@creator" --limit 10

Dependencies
------------
    The invocation prefix is `uv run --with pyyaml`. The Whisper fallback
    (on by default, and always needed for Instagram, which has no captions)
    also needs `--with faster-whisper==1.2.1`, else pass --no-whisper.
    yt-dlp is invoked as a subprocess from PATH on purpose, not pinned:
    YouTube changes break old yt-dlp releases within weeks, so the runtime
    wants the current Homebrew build (`brew upgrade yt-dlp`). The test
    suite mocks every yt-dlp call and needs no yt-dlp at all.

Exit codes
----------
0  Success (single-video success, or a batch with no failed videos).
1  Failure: single-video processing failed, no videos found on a profile, or
   at least one batch video failed.
2  Argparse usage error: missing url or --batch-profile, unsupported URL/host,
   Instagram profile batch, unknown flag, or invalid flag value.
"""
import os
import sys
import argparse
import tempfile
import json
import subprocess
import re
import shutil
import yaml
import time
import random
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlsplit
from scripts.config import LIBRARY_DIR, TEMP_DIR, ORIGINAL_ENGLISH_SUB_LANG, has_manual_english_subs, select_subtitle, initialize_directories, safe_slug, logger, apply_replacements

# data/ is gitignored; the fetch cache is a local convenience, not library content.
FETCH_CACHE_DIR = Path(os.getenv("FETCH_CACHE_DIR", "data/fetch_cache"))


class RateLimitedError(RuntimeError):
    """YouTube answered HTTP 429; retrying would only make the rate limit worse."""


class FlaggedChannelsConfigError(RuntimeError):
    """config/flagged_channels.yaml exists but cannot be read or parsed.

    Treating a broken watchlist as "no flags" would silently drop the extra
    fact-check scrutiny for every flagged channel, so the run fails instead.
    """


def is_rate_limited(stderr: str) -> bool:
    """True when stderr reports an HTTP 429 rate limit (case-insensitive)."""
    if not stderr:
        return False
    lowered = stderr.lower()
    return "http error 429" in lowered or "too many requests" in lowered


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

            # Non-zero return code - fail fast on rate limits, retry others
            if is_rate_limited(result.stderr or ""):
                logger.error("YouTube rate limit (HTTP 429) — not retrying; wait before fetching again")
                return result

            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning(f"Command failed (attempt {attempt + 1}/{max_retries}), retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                logger.error(f"Command failed after {max_retries} attempts")
                return result  # Return the failed result for error handling

        except subprocess.TimeoutExpired:  # governance: allow-silent SF002: None is run_with_retry's documented exhaustion result; every caller treats None as failure (get_video_data returns None -> process_single_video False -> exit 1; profile fetch -> 'No videos found' exit 1)
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

        except FileNotFoundError:  # governance: allow-silent SF002: yt-dlp missing returns the documented None failure result; every caller treats None as a failed command and the CLI exits 1
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
    Cleans SRT/VTT file content by removing indices, timestamps, and deduplicating lines.
    Handles both SRT (commas in timestamps) and VTT (dots in timestamps) formats.
    Optimized for long-context processing.
    """
    lines = srt_content.splitlines()
    cleaned_lines = []

    # Match both SRT (00:00:00,000) and VTT (00:00:00.000) timestamp formats
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}[,.]\d{3} --> \d{2}:\d{2}:\d{2}[,.]\d{3}')
    index_pattern = re.compile(r'^\d+$')
    # Skip VTT headers and metadata
    vtt_header_pattern = re.compile(r'^(WEBVTT|Kind:|Language:)', re.IGNORECASE)
    
    last_line = ""
    for line in lines:
        line = line.strip()
        if not line or index_pattern.match(line) or timestamp_pattern.match(line) or vtt_header_pattern.match(line):
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
        logger.info("[*] Downloading audio for Whisper transcription...")

        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--output", str(audio_path.with_suffix('')),  # yt-dlp adds .mp3
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            if is_rate_limited(result.stderr or ""):
                raise RateLimitedError(f"YouTube rate-limited the audio download for {url}")
            logger.error(f"Audio download failed: {result.stderr}")
            return None

        if audio_path.exists():
            return audio_path
        else:
            logger.error(f"Audio file not found at {audio_path}")
            return None

    except RateLimitedError:
        raise
    except subprocess.TimeoutExpired:  # governance: allow-silent SF002: None is download_audio's failure result; get_video_data logs 'Audio download failed' and, with no transcript, returns None so the CLI exits 1
        logger.error("Audio download timed out after 300 seconds")
        return None
    except Exception as e:  # governance: allow-silent SF002: None is download_audio's failure result; get_video_data logs 'Audio download failed' and, with no transcript, returns None so the CLI exits 1
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

        logger.info("[*] Transcribing with Whisper (this may take a few minutes)...")

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

    except ImportError:  # governance: allow-silent SF002: faster-whisper is an optional dependency; None is the failure result and get_video_data returns None (CLI exit 1) when no SRT transcript exists
        logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
        return None
    except Exception as e:  # governance: allow-silent SF002: None is transcribe_with_whisper's failure result; get_video_data returns None (CLI exit 1) when no SRT transcript exists
        logger.error(f"Whisper transcription failed: {e}")
        return None

def supported_platform(url: str) -> Optional[str]:
    """Validate a CLI/video URL's scheme and exact host, not its extractor path.

    Bare supported domains remain accepted. Credentials, ports, whitespace,
    lookalike hosts and non-HTTP schemes are outside the librarian's URL contract.
    """
    if not url or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url):
        return None
    try:
        has_scheme = re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", url)
        parsed = urlsplit(url if has_scheme else "https://" + url)
    except ValueError:  # governance: allow-silent SF002: a URL urlsplit cannot parse is outside the supported-URL contract; None makes main() reject it via parser.error
        return None
    hosts = {"youtube.com": "youtube", "youtu.be": "youtube",
             "tiktok.com": "tiktok", "instagram.com": "instagram"}
    host = parsed.netloc.lower().removeprefix("www.")
    if parsed.scheme not in {"http", "https"} or not parsed.path.strip("/"):
        return None
    return hosts.get(host)


def _instagram_handle(metadata: Dict[str, Any]) -> str:
    """Use extracted identity, never infer a handle from a name, numeric ID or URL.

    Instagram post URLs can include an arbitrary username prefix, so even a
    user-qualified URL cannot establish ownership of a post.
    """
    channel = (metadata.get("channel") or "").strip()
    if channel:
        return channel
    # Older extractors sometimes supplied a handle in uploader_id; modern ones
    # supply a numeric owner ID, which must not be used as a handle.
    legacy = str(metadata.get("uploader_id") or "").strip()
    if not legacy.isdecimal() and re.fullmatch(r"@?[A-Za-z0-9_.]{1,30}", legacy):
        return legacy
    logger.warning("Instagram handle unavailable: handle-based watchlist matching is incomplete; "
                   "only available account IDs and display names can be checked.")
    return ""


def get_video_data(url: str, use_whisper_fallback: bool = True, metadata_only: bool = False) -> Optional[Dict[str, Any]]:
    """
    Uses yt-dlp to fetch video metadata and SRT transcript.
    Prioritizes manual subtitles over auto-generated ones.
    Uses tempfile.TemporaryDirectory for safe, automatic cleanup.

    With metadata_only=True, only the --print-json metadata call runs and the
    returned dict carries an empty transcript — no subtitle, audio, or Whisper.
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
                if result is not None and is_rate_limited(result.stderr or ""):
                    raise RateLimitedError(f"YouTube rate-limited the metadata request for {url}")
                error_msg = result.stderr if result else "Command failed after retries"
                logger.error(f"Error fetching metadata: {error_msg}")
                return None

            metadata = json.loads(result.stdout)

            transcript = ""
            if not metadata_only:
                logger.info("[*] Fetching manual and auto-subtitles...")
                sub_path_base = str(unique_temp / "transcript")
                # Without a manual English track, also request en-orig: on auto-dubbed
                # videos the plain "en" auto track can be a machine translation.
                prefer_original = not has_manual_english_subs(metadata)
                sub_langs = "en,en-US,en-GB,eng,eng-US,eng-GB"
                if prefer_original:
                    sub_langs = f"{ORIGINAL_ENGLISH_SUB_LANG},{sub_langs}"
                cmd_subs = [
                    "yt-dlp",
                    "--skip-download",
                    "--write-subs",
                    "--write-auto-subs",
                    "--sub-lang", sub_langs,
                    "--sub-format", "srt/vtt/best",
                    "--output", sub_path_base,
                    url
                ]
                sub_result = run_with_retry(cmd_subs, timeout=120)
                if sub_result is None or sub_result.returncode != 0:
                    if sub_result is not None and is_rate_limited(sub_result.stderr or ""):
                        raise RateLimitedError(f"YouTube rate-limited the subtitle request for {url}")
                    error_msg = sub_result.stderr if sub_result else "Command failed after retries"
                    logger.warning(f"Subtitle fetch command failed for {url}.")
                    logger.debug(f"Stderr: {error_msg}")

                srt_files = [f for f in os.listdir(unique_temp) if f.endswith(('.srt', '.vtt'))]
                target_file = select_subtitle(srt_files, "transcript", prefer_original=prefer_original)

                if target_file:
                    logger.info(f"[*] Using subtitle track {target_file}")
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

            # Detect platform from URL or extractor
            extractor = metadata.get("extractor_key", "").lower()
            channel_id = metadata.get("channel_id") or ""
            if "tiktok" in extractor or "tiktok.com" in url:
                platform = "tiktok"
                # TikTok: 'channel' is display name, 'uploader' is handle
                channel = metadata.get("channel") or metadata.get("uploader") or "Unknown_Channel"
                uploader_id = metadata.get("uploader_id") or ""
            elif "instagram" in extractor or "instagram.com" in url:
                platform = "instagram"
                # Instagram inverts the TikTok convention: 'uploader' is the
                # display name, 'channel' is the @handle, and 'uploader_id' is
                # the numeric owner ID. Keep the handle and stable ID separate
                # for check_flagged_channel().
                channel = metadata.get("uploader") or metadata.get("channel") or "Unknown_Channel"
                uploader_id = _instagram_handle(metadata)
                # Preserve the numeric owner ID separately for stable-ID watchlists.
                owner_id = str(metadata.get("uploader_id") or "")
                if not channel_id and owner_id.isdecimal():
                    channel_id = owner_id
            else:
                platform = "youtube"
                channel = metadata.get("uploader") or "Unknown_Channel"
                uploader_id = metadata.get("uploader_id") or ""

            return {
                "title": metadata.get("title") or "Untitled",
                "channel": channel,
                "channel_id": channel_id,
                "uploader_id": uploader_id,
                "date": metadata.get("upload_date"),
                "url": url,
                "video_id": metadata.get("id") or "unknown",
                "description": metadata.get("description") or "",
                "transcript": transcript,
                "tags": metadata.get("tags", []) or [],
                "view_count": metadata.get("view_count") or 0,
                "like_count": metadata.get("like_count") or 0,
                "duration_string": metadata.get("duration_string") or "0:00",
                "chapters": chapters,
                "platform": platform
            }
        except RateLimitedError:
            raise
        except subprocess.TimeoutExpired as e:  # governance: allow-silent SF002: None is get_video_data's failure result; process_single_video returns False and main() exits 1 or counts the batch item failed
            logger.error(f"Subprocess timed out: {e}")
            return None
        except Exception as e:  # governance: allow-silent SF002: None is get_video_data's failure result; process_single_video returns False and main() exits 1 or counts the batch item failed
            logger.error(f"Unexpected error in get_video_data: {e}")
            return None


def _fill_save_data_defaults(data: Dict[str, Any]) -> None:
    """Fill optional save fields so cached/fetched JSON is always saveable."""
    data.setdefault("view_count", 0)
    data.setdefault("like_count", 0)
    data.setdefault("duration_string", "0:00")
    data.setdefault("tags", [])
    data.setdefault("chapters", [])


def _load_data_file(url: str, data_file: str) -> Optional[Dict[str, Any]]:
    """Load a --data-file JSON object and validate it against the CLI url."""
    path = Path(data_file)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:  # governance: allow-silent SF002: None is the --data-file failure result; process_single_video logs 'Failed to get video data' and main() exits 1
        logger.error(f"Could not read --data-file {data_file}: {e}")
        return None
    if not isinstance(data, dict):
        logger.error(f"--data-file {data_file} must contain a JSON object")
        return None
    missing = [key for key in ("title", "channel", "url", "video_id") if key not in data]
    if missing:
        logger.error(f"--data-file {data_file} is missing required key(s): {', '.join(missing)}")
        return None
    if data["url"] != url:
        logger.error(f"--data-file url {data['url']!r} does not match the CLI url {url!r}")
        return None
    _fill_save_data_defaults(data)
    return data


def _find_cache_for_url(url: str) -> Optional[Dict[str, Any]]:
    """Return cached fetch JSON whose url matches, or None. Unreadable files warn."""
    if not FETCH_CACHE_DIR.is_dir():
        return None
    for cache_path in FETCH_CACHE_DIR.glob("*.json"):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Ignoring unreadable fetch cache file {cache_path}: {e}")
            continue
        if isinstance(data, dict) and data.get("url") == url:
            _fill_save_data_defaults(data)
            logger.info(f"[+] Using fetch cache {cache_path}")
            return data
    return None


def _write_fetch_cache(data: Dict[str, Any], payload: str) -> None:
    """Write the printed fetch JSON to the cache. A failure warns, never fails the fetch."""
    try:
        FETCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        platform = data.get("platform") or "unknown"
        video_id = data.get("video_id") or "unknown"
        cache_path = FETCH_CACHE_DIR / f"{platform}-{safe_slug(video_id)}.json"
        atomic_write(cache_path, payload)
        logger.info(f"[+] Cached fetch JSON at {cache_path}")
    except OSError as e:
        logger.warning(f"Could not write fetch cache: {e}")


def _load_save_data(url: str, args) -> Optional[Dict[str, Any]]:
    """Resolve video data for save mode without subtitles or audio.

    Order: --data-file, then a fetch cache file matching the URL, then a
    metadata-only fetch.
    """
    data_file = getattr(args, "data_file", None)
    if isinstance(data_file, str) and data_file:
        return _load_data_file(url, data_file)
    data = _find_cache_for_url(url)
    if data is None:
        data = get_video_data(url, use_whisper_fallback=False, metadata_only=True)
    if isinstance(data, dict):
        _fill_save_data_defaults(data)
    return data


_MD_LINK_RE = re.compile(r'\[[^\]]+\]\([^)]+\)|https?://')
_TABLE_SEP_RE = re.compile(r'^\|[\s:|-]+\|$')
_FENCE_RE = re.compile(r'^\s*(```|~~~)')
# Threshold from FACT_CHECK_PROTOCOL.md. Both live in one place only because
# test_ceiling_matches_protocol_doc() asserts they agree — comments don't prevent drift.
UNSOURCED_CLAIM_CEILING = 0.20
# A table is a claim table if any header cell contains "claim". Nothing more.
#
# Two earlier versions tried to be cleverer and both failed review for the same reason.
# Keying off a numbered first column missed tables that don't number. Adding an allowlist
# of verdict words (grade/verdict/reality/...) missed "Verified?" and "Holds up?". A survey
# of every claim-bearing table in the library found 16 distinct header shapes and the
# verdict column spelled at least seven ways — an allowlist will always be one spelling
# behind, and each miss is invisible rather than noisy.
#
# So: match the one word that is actually invariant. Two of the 16 shapes are not grading
# tables ("# | beat | claim", "# | claim | where") and will be flagged anyway. That is the
# right trade — this reports and never blocks, so a false positive costs one ignored
# warning while a false negative costs an unsourced grade shipped into the library.
_CLAIM_HEADER = "claim"


_UNESCAPED_PIPE_RE = re.compile(r'(?<!\\)\|')


def _split_row(line: str) -> List[str]:
    """Split a markdown table row into trimmed cells, dropping the outer pipes.

    Splits on unescaped pipes only, so a \\| inside claim text can't shift column
    alignment and mislabel a sourced row as unsourced. Uses a lookbehind rather than a
    placeholder swap — an earlier version substituted \\x00, which corrupted any literal
    NUL byte in the source text.
    """
    cells = _UNESCAPED_PIPE_RE.split(line.strip())
    # The outer pipes produce empty leading/trailing entries; drop only those.
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [c.strip().replace(r'\|', '|') for c in cells]


_WORD_RE = re.compile(r'[a-z]+')


def _is_unverified_grade(cell: str) -> bool:
    """True only when the grade LEADS with Unverified, not merely mentions it.

    Emoji and markdown emphasis are stripped by tokenisation, so "**🟡 Unverified**" and
    "🟡 Unverified specifics" both match, while "Number confirmed, timing unverified"
    does not — its primary grade is Confirmed, which the Grades table says needs a link.

    Deliberately positional rather than an allowlist of assertive grade words. A previous
    version listed confirmed/wrong/imprecise/... and could still be beaten by any spelling
    absent from it ("Misleading, unverified"). Round two of this review failed on exactly
    that shape of mistake at the header level; the fix is to stop enumerating vocabulary
    and key on structure, which cannot fall behind.
    """
    words = _WORD_RE.findall(cell.lower())
    return bool(words) and words[0] == "unverified"


def audit_claim_sources(analysis: str) -> Optional[Dict[str, Any]]:
    """Count claim-table rows whose Source cell is empty.

    Rule 0 of FACT_CHECK_PROTOCOL.md: the source goes in the row, because an unsourced
    grade and a sourced grade are visually identical without it — which is how two of the
    2026-08-14 overturns survived review. A bulk '## Sources' list proves nothing about
    any individual grade, so it deliberately does not count here.

    Detection reads the table HEADER, matching only on the word "claim" — see the note on
    _CLAIM_HEADER for why every cleverer version failed. A table with no Source column at
    all counts every row as unsourced, which is the correct reading of the 2026-08-14
    report. Tables inside fenced code blocks are skipped so documentation examples of the
    format don't get audited as real reports.

    Only the Source cell is inspected, not the whole row, so a URL quoted inside the
    claim text can't launder an uncited grade.

    Returns None when the report contains no claim table (tutorial extractions, workflow
    write-ups), so those are never nagged.
    """
    lines = analysis.splitlines()
    total = unsourced = documented = 0
    found_table = False
    in_fence = False

    # Only honour fences when they are balanced. An unclosed fence would otherwise latch
    # the skip flag on and silently disable auditing for the rest of the document —
    # returning None, indistinguishable from "this report has no claims". Over-auditing a
    # stray fenced block is the safe direction: this warns, it never blocks.
    fences_balanced = sum(1 for ln in lines if _FENCE_RE.match(ln)) % 2 == 0

    i = 0
    while i < len(lines) - 1:
        if fences_balanced and _FENCE_RE.match(lines[i]):
            in_fence = not in_fence
            i += 1
            continue
        if in_fence:
            i += 1
            continue

        line, nxt = lines[i].strip(), lines[i + 1].strip()
        if not (line.startswith('|') and _TABLE_SEP_RE.match(nxt)):
            i += 1
            continue

        header = [h.lower() for h in _split_row(line)]
        if not any(_CLAIM_HEADER in h for h in header):
            i += 1
            continue

        found_table = True
        src_idx = next((n for n, h in enumerate(header) if "source" in h), None)
        grade_idx = next((n for n, h in enumerate(header)
                          if any(v in h for v in ("grade", "verdict", "verified", "reality",
                                                  "holds up", "status", "assessment"))), None)
        i += 2  # skip header and separator
        while i < len(lines) and lines[i].strip().startswith('|'):
            cells = _split_row(lines[i])
            total += 1
            # No Source column means nothing in this table is cited, by definition.
            cell = cells[src_idx] if src_idx is not None and src_idx < len(cells) else ""
            grade = (cells[grade_idx] if grade_idx is not None and grade_idx < len(cells)
                     else "")
            if _MD_LINK_RE.search(cell):
                pass  # cited
            elif cell and _is_unverified_grade(grade):
                # A link-free Source cell is legitimate on exactly one grade: Unverified,
                # where the protocol asks for the search trail instead ("searched X, Y;
                # nothing primary found"). Counting that as unsourced would fire the
                # warning at a report for complying, and a warning that punishes
                # compliance is one people learn to ignore.
                #
                # Narrow on purpose. Accepting *any* prose here would let a "Detail" or
                # "Note" column launder a whole uncited table — which is the 2026-08-14
                # pattern exactly: prose in every row, links only in a list at the bottom.
                documented += 1
            else:
                unsourced += 1
            i += 1

    if not found_table or not total:
        return None
    return {
        "total": total,
        "unsourced": unsourced,
        "documented": documented,
        "ratio": unsourced / total,
    }


def emit_claim_source_audit(stats: Dict[str, Any]) -> None:
    """Warn when claim rows have an empty Source cell. Reports, never blocks."""
    total, unsourced, ratio = stats["total"], stats["unsourced"], stats["ratio"]
    documented = stats.get("documented", 0)
    if not unsourced:
        note = f" ({documented} carry a search trail rather than a link)" if documented else ""
        logger.info(f"[fact-check] {total}/{total} claim rows carry a source{note}.")
        return
    over = ratio > UNSOURCED_CLAIM_CEILING
    logger.warning("=" * 70)
    logger.warning(f"[fact-check] {unsourced} of {total} claim rows have an EMPTY source "
                   f"cell ({ratio:.0%}).")
    logger.warning("[fact-check] Rule 0: the source goes IN the row. A bulk '## Sources'")
    logger.warning("[fact-check] list at the bottom does not satisfy this.")
    if documented:
        logger.warning(f"[fact-check] ({documented} more carry a search trail rather than a "
                       "link — those count as Unverified, not Unchecked.)")
    if over:
        logger.warning(f"[fact-check] !! Above the {UNSOURCED_CLAIM_CEILING:.0%} ceiling — this "
                       "is NOT publishable as a fact-check.")
        logger.warning("[fact-check] !! Either bind the sources or grade those rows Unchecked.")
    logger.warning("=" * 70)


def save_to_library(data: Dict[str, Any], analysis: str, subdir: Optional[str] = None) -> Path:
    """
    Saves the final report to the library/ directory.
    Uses video_id and safe_slug to prevent filename collisions and ensure safety.

    `subdir` files the report under library/<subdir>/ instead of the flat root, for
    topic collections that accumulate over time (see library/*/README.md).
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

    target_dir = LIBRARY_DIR
    if subdir:
        # Slug the subdir so it can never introduce separators or traversal segments.
        # safe_slug strips '.' and '/', so a hostile value can't survive as a path part.
        slugged = safe_slug(subdir)
        if not slugged:
            logger.warning(f"[!] Subdir {subdir!r} sanitized to empty; saving to library root instead.")
        else:
            target_dir = LIBRARY_DIR / slugged
    # Created here, not at startup, so --dry-run leaves library/ untouched.
    target_dir.mkdir(parents=True, exist_ok=True)
    filepath = target_dir / filename

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
        chapter_section = "\n## Chapter Timeline\n\n" + "\n".join(chapter_lines) + "\n"

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

def _category_text(text: str) -> str:
    """Normalize punctuation/spacing while retaining whole Unicode words."""
    return " " + " ".join(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())) + " "


def _category_evidence(fields: List[str], keywords: Dict[str, float]) -> float:
    """Count each signal once; a phrase subsumes its nested keyword matches."""
    matches = {phrase: weight for phrase, weight in keywords.items()
               if any(phrase in field for field in fields)}
    return sum(weight for phrase, weight in matches.items()
               if not any(phrase != other and phrase in other for other in matches))


def get_category(title: str, tags: List[str]) -> Dict[str, str]:
    """Score topic evidence, independent of category order or library contents.

    Titles carry three times the evidence of tags; total tag evidence is capped
    at two so channel-wide/SEO tags cannot overwhelm a clear title topic. Each
    keyword contributes once per source, with nested matches counted only as
    the longer phrase. Configured weights distinguish topic signals from broad
    context such as 'ai'. Equal best scores abstain to the default category.
    Collection labels and historical assignments are never classifier inputs.
    """
    categories_path = Path("config/categories.yaml")
    if not categories_path.exists():
        return {"id": "miscellaneous", "name": "📦 Miscellaneous"}
    
    with open(categories_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    title_fields = [_category_text(title)]
    tag_fields = [_category_text(tag) for tag in tags]
    default = config.get("default_category", {"id": "miscellaneous", "name": "📦 Miscellaneous"})
    best_score = 0.0
    winners = []
    for cat in config.get("categories", []):
        configured = cat.get("keywords", {})
        # Lists remain supported for existing/custom category configurations.
        if isinstance(configured, list):
            configured = dict.fromkeys(configured, 1.0)
        keywords = {_category_text(word): weight for word, weight in configured.items()}
        score = (3 * _category_evidence(title_fields, keywords)
                 + min(2, _category_evidence(tag_fields, keywords)))
        if score > best_score:
            best_score, winners = score, [cat]
        elif score == best_score:
            winners.append(cat)
    if best_score > 0 and len(winners) == 1:
        return {"id": winners[0]["id"], "name": winners[0]["name"]}
    return default

def update_index(entry_data: Dict[str, Any]) -> bool:
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
            
    categories_path = Path("config/categories.yaml")
    if not categories_path.exists():
        logger.error(
            "Cannot update index: category configuration %s is missing; leaving the index unchanged",
            categories_path,
        )
        return False

    with open(categories_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    categories_config = config.get("categories", [])
    default_cat = config.get(
        "default_category", {"id": "miscellaneous", "name": "📦 Miscellaneous"}
    )

    supported_category_ids = {cat.get("id") for cat in categories_config}
    supported_category_ids.add(default_cat["id"])

    # Check for duplicates, but still write/render the repaired index below.
    if any(entry.get("url") == entry_data["url"] for entry in index_data["entries"]):
        logger.info(f"Entry for {entry_data['title']} already exists in index. Skipping.")
    else:
        index_data["entries"].append(entry_data)

    # Repair retired/unknown category IDs before rendering. Keeping the entry in
    # the source-of-truth YAML and placing it in the configured default bucket is
    # safer than silently losing it from the Markdown index. This covers both
    # legacy entries already in the index and a newly supplied entry.
    unknown_entries = [
        entry
        for entry in index_data.get("entries", [])
        if entry.get("category_id") not in supported_category_ids
    ]
    # This is a stateful catalog repair: preserve the pre-repair source of truth
    # so an incorrect category configuration can be recovered.
    if unknown_entries and index_yaml_path.exists():
        backup_yaml_path = index_yaml_path.with_suffix(".yaml.bak")
        try:
            shutil.copy2(index_yaml_path, backup_yaml_path)
        except OSError as e:  # governance: allow-silent SF002: False is update_index's failure result (index left unrepaired); process_single_video returns it and main() exits 1
            logger.error("Could not back up index before category repair: %s", e)
            return False

    for entry in unknown_entries:
        category_id = entry.get("category_id")
        entry_label = entry.get("title") or entry.get("url") or "<untitled entry>"
        logger.warning(
            "Entry %r has unknown category_id %r; falling back to default category %r",
            entry_label,
            category_id,
            default_cat["id"],
        )
        entry["category_id"] = default_cat["id"]
    
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
    if not any(cat.get("id") == default_cat["id"] for cat in categories_config):
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
    return True

def get_profile_video_urls(profile_url: str, limit: Optional[int] = None) -> List[str]:
    """
    Fetches all video URLs from a TikTok or YouTube profile/channel.
    Returns list of video URLs, optionally limited.
    """
    logger.info(f"[*] Fetching video list from profile: {profile_url}")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(webpage_url)s",
        profile_url
    ]
    result = run_with_retry(cmd, timeout=60)
    if result is None or result.returncode != 0:
        logger.error("Failed to fetch profile video list.")
        return []

    urls = [u.strip() for u in result.stdout.strip().splitlines() if u.strip()]
    logger.info(f"[+] Found {len(urls)} videos on profile")

    if limit:
        urls = urls[:limit]
        logger.info(f"[*] Limited to first {limit} videos")

    return urls


# Anchor to the script's own location so the check works regardless of CWD
# (the librarian may be invoked from a wrapper, cron job, or test runner).
FLAGGED_CHANNELS_PATH = Path(__file__).resolve().parent.parent / "config" / "flagged_channels.yaml"


def _norm_handle(value: Optional[str]) -> str:
    """Normalize a channel handle for comparison: lowercase, no leading '@'.

    YouTube's uploader_id arrives with the '@' prefix; TikTok's does not. The
    watchlist stores handles with '@' for readability, so strip it on both sides.
    """
    return (value or "").strip().lstrip("@").lower()


def check_flagged_channel(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Checks the video's channel against config/flagged_channels.yaml.

    Matches by channel_id (stable across renames), then @handle, then a
    case-insensitive display-name fallback. Returns the matching flag entry
    (dict) or None. A missing config means "no flags". A config that exists
    but is unreadable or malformed raises FlaggedChannelsConfigError: a broken
    watchlist must fail the run, not silently unflag every channel. It is
    called before anything is written for the video, so nothing is left
    half-saved.
    """
    if not FLAGGED_CHANNELS_PATH.exists():
        return None
    try:
        with open(FLAGGED_CHANNELS_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        raise FlaggedChannelsConfigError(
            f"Flagged-channel watchlist {FLAGGED_CHANNELS_PATH} is unreadable or "
            f"malformed; fix it before fetching or saving: {e}"
        ) from e
    if not isinstance(config, dict):
        raise FlaggedChannelsConfigError(
            f"Flagged-channel watchlist {FLAGGED_CHANNELS_PATH} must be a YAML "
            f"mapping with a 'channels' list, got {type(config).__name__}"
        )

    cid = (data.get("channel_id") or "").strip()
    handle = _norm_handle(data.get("uploader_id"))
    name = (data.get("channel") or "").strip().lower()

    for entry in config.get("channels", []) or []:
        e_cid = (entry.get("channel_id") or "").strip()
        e_handle = _norm_handle(entry.get("handle"))
        e_name = (entry.get("name") or "").strip().lower()
        if (e_cid and cid and e_cid == cid) \
                or (e_handle and handle and e_handle == handle) \
                or (e_name and name and e_name == name):
            return entry
    return None


def emit_flag_warning(entry: Dict[str, Any], data: Dict[str, Any]) -> None:
    """Print a prominent multi-line warning when a flagged channel is detected."""
    severity = (entry.get("severity") or "watch").upper()
    reason = " ".join((entry.get("reason") or "").split())
    logger.warning("=" * 70)
    logger.warning(f"[!!] FLAGGED CHANNEL [{severity}]: {data.get('channel')}")
    logger.warning(f"[!!] {reason}")
    logger.warning("[!!] FACT-CHECK every factual claim against primary sources before saving.")
    logger.warning("=" * 70)


# Anchored to the script's own location, not CWD — same reason as FLAGGED_CHANNELS_PATH above.
# A CWD-relative lookup here would report the protocol "NOT FOUND" whenever the librarian is
# invoked from anywhere but the repo root, which is the exact opposite of a reliability gate.
FACT_CHECK_PROTOCOL_PATH = Path(__file__).resolve().parent.parent / "FACT_CHECK_PROTOCOL.md"


# Reports land in library/, which is gitignored — no PR, hook, or CI check ever sees them.
# This warning is the only enforcement point the pipeline has, so it fires on every fetch.
def emit_fact_check_protocol_reminder() -> None:
    """Surface the fact-check protocol at fetch time, before any grading happens.

    Origin: 2026-08-14, an ~11% materially-wrong first-pass grade rate. The three rules
    below are the ones that caused overturns; the file has the other four and the reasoning.
    """
    logger.warning("-" * 70)
    logger.warning("[fact-check] Before grading any claim, read FACT_CHECK_PROTOCOL.md")
    if not FACT_CHECK_PROTOCOL_PATH.exists():
        logger.warning("[fact-check] !! FACT_CHECK_PROTOCOL.md NOT FOUND at repo root !!")
    logger.warning("[fact-check]  0. SOURCE LINK GOES IN THE CLAIM ROW. A bulk source list at")
    logger.warning("[fact-check]     the bottom does NOT count. Empty source cell == Unchecked.")
    logger.warning("[fact-check]  1. No grade from memory. Unsearched == Unchecked.")
    logger.warning("[fact-check]  2. Fetch the primary source. A search snippet is not evidence.")
    logger.warning("[fact-check]  3. Search the speaker's framing and units FIRST, not yours.")
    logger.warning("[fact-check] Re-check every 'Wrong' grade in the speaker's favour before "
                   "publishing.")
    logger.warning("-" * 70)


# High-signal patterns for harvesting deterministic research targets.
_URL_RE = re.compile(r'https?://[^\s<>"\')]+')
_HASHTAG_RE = re.compile(r'(?<!\w)#(\w+)')
_MENTION_RE = re.compile(r'(?<!\w)@([A-Za-z0-9_.]+)')
# A mention candidate shaped like "name.tld" where tld is a common TLD (e.g.
# "smoothmedia.co" from an email address) is a domain, not a social handle.
# Restricting to known TLDs preserves legitimate dotted handles like "Mr.Beast".
_DOMAIN_LIKE_RE = re.compile(r'^[A-Za-z0-9_-]+\.([A-Za-z]{2,})$')
_COMMON_TLDS = frozenset({
    "com", "co", "io", "net", "org", "me", "ai", "dev", "app", "tv",
    "gg", "xyz", "info", "biz", "edu", "gov", "us", "uk", "ca",
})


def _looks_like_domain(handle: str) -> bool:
    """True if a mention candidate is really a domain/email tail, not a handle."""
    m = _DOMAIN_LIKE_RE.match(handle)
    return bool(m) and m.group(1).lower() in _COMMON_TLDS


def extract_research_targets(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Harvest high-signal, deterministic research targets from video metadata to
    seed the research pass. This does NOT do the research — it produces a
    checklist for a research agent to verify and document.

    Semantic targets (named products, companies, factual/numeric claims) are
    intentionally left to the research agent, which extracts them from the
    transcript far more reliably than a regex could.

    Returns a dict with:
      - links:    unique URLs from the description, order-preserved
      - hashtags: unique hashtags from description + tags (without '#')
      - mentions: unique @handles from the description (without '@'); candidates
                  shaped like a domain with a common TLD (e.g. "smoothmedia.co"
                  from an email) are filtered, but dotted handles like "Mr.Beast"
                  are preserved
      - chapters: author-curated chapter titles (topic markers worth researching)
    """
    description = data.get("description") or ""

    links: List[str] = []
    for u in _URL_RE.findall(description):
        u = u.rstrip('.,;')
        if u and u not in links:
            links.append(u)

    hashtags = list(dict.fromkeys(
        [h.lower() for h in _HASHTAG_RE.findall(description)]
        + [str(t).lower() for t in (data.get("tags") or [])]
    ))

    mentions = list(dict.fromkeys(
        m for m in _MENTION_RE.findall(description) if not _looks_like_domain(m)
    ))

    chapters = [
        ch["title"] for ch in (data.get("chapters") or [])
        if isinstance(ch, dict) and ch.get("title")
    ]

    return {
        "links": links,
        "hashtags": hashtags,
        "mentions": mentions,
        "chapters": chapters,
    }


def process_single_video(url: str, args) -> bool:
    """
    Processes a single video URL through the full pipeline.
    In fetch-only mode, outputs JSON metadata + transcript for external analysis.
    In save mode (--analysis-file), saves a pre-generated analysis to the library.
    Returns True on success, False on failure.
    """
    if args.analysis_file:
        data = _load_save_data(url, args)
    else:
        data = get_video_data(url, use_whisper_fallback=not args.no_whisper)
    if not data:
        logger.error(f"Failed to get video data for: {url}")
        return False

    # Flag known-problematic sources so claims get extra fact-checking scrutiny.
    flag = check_flagged_channel(data)
    if flag:
        emit_flag_warning(flag, data)
        data["flag"] = {
            "flagged": True,
            "severity": flag.get("severity"),
            "reason": " ".join((flag.get("reason") or "").split()),
            "name": flag.get("name"),
        }

    # If no analysis file provided, output data as JSON for external analysis (Claude)
    if not args.analysis_file:
        # Seed the research pass with a deterministic checklist of what to verify.
        data["research_targets"] = extract_research_targets(data)
        # Fires here, on the fetch that precedes grading — not on the save, which is too late.
        emit_fact_check_protocol_reminder()
        payload = json.dumps(data, indent=2, ensure_ascii=False)
        print(payload)
        # Cache the exact printed JSON so save mode can file the report offline.
        _write_fetch_cache(data, payload)
        return True

    # Load pre-generated analysis from file
    analysis_path = Path(args.analysis_file)
    if not analysis_path.exists():
        logger.error(f"Analysis file not found: {args.analysis_file}")
        return False

    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis = f.read()

    # Apply find-replace rules from config/replacements.yaml
    analysis = apply_replacements(analysis)

    if args.dry_run:
        logger.info(f"--- DRY RUN: {data['title']} ---")
        logger.info(analysis)
        logger.info("--------------------------------")
        return True

    date_str = data.get('date')
    if date_str and len(date_str) == 8:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    else:
        formatted_date = datetime.now().strftime("%Y-%m-%d")

    # Rule 0 audit runs on the way in, so an unsourced claim table is caught at the moment
    # it lands rather than on a re-read months later. Reports, never blocks — a false
    # positive costs one ignored warning, a missed one costs an unsourced grade in the library.
    source_stats = audit_claim_sources(analysis)
    if source_stats:
        emit_claim_source_audit(source_stats)

    categories_path = Path("config/categories.yaml")
    if not categories_path.exists():
        logger.error(
            "Cannot save video: category configuration %s is missing",
            categories_path,
        )
        return False

    filepath = save_to_library(data, analysis, subdir=getattr(args, "subdir", None))

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
    # Derive the collection from where the file actually landed, not from the raw flag —
    # a subdir that sanitizes to empty falls back to the root and gets no collection tag.
    if filepath.parent != LIBRARY_DIR:
        entry_data["collection"] = filepath.parent.name

    return update_index(entry_data)


def build_parser() -> argparse.ArgumentParser:
    """Build the librarian CLI parser. The module docstring is the description."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", nargs="?", help="YouTube, TikTok, or Instagram URL to process")
    parser.add_argument("--batch-profile", help="Process all videos from a TikTok/YouTube profile URL")
    parser.add_argument("--limit", type=int, help="Limit number of videos to process in batch mode")
    parser.add_argument("--delay", type=int, default=45, help="Delay in seconds between videos in batch mode (default: 45)")
    parser.add_argument("--dry-run", action="store_true", help="Save mode only: show the report without writing to library/")
    parser.add_argument("--analysis-file", help="Path to a markdown file containing pre-generated analysis to save")
    parser.add_argument("--data-file", help="Path to JSON previously printed by fetch mode to use as video data (requires --analysis-file)")
    parser.add_argument("--no-whisper", action="store_true", help="Disable Whisper fallback for videos without transcripts")
    parser.add_argument("--subdir", help="File the report under library/<subdir>/ instead of the library root (topic collection)")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.data_file and not args.analysis_file:
        parser.error("--data-file requires --analysis-file")

    url = args.batch_profile or args.url
    if not url:
        parser.error("Either url or --batch-profile is required")
    platform = supported_platform(url)
    if platform is None:
        parser.error("Expected a YouTube, TikTok, or Instagram HTTP(S) URL on a supported host")
    if args.batch_profile and platform == "instagram":
        parser.error("Instagram profile batches are unsupported; use an individual post or reel URL")

    initialize_directories()

    # Batch profile mode
    if args.batch_profile:
        urls = get_profile_video_urls(args.batch_profile, limit=args.limit)
        if not urls:
            logger.error("No videos found on profile.")
            sys.exit(1)

        # Check which URLs are already in the index to skip duplicates
        index_yaml_path = LIBRARY_DIR / "index.yaml"
        existing_urls = set()
        if index_yaml_path.exists():
            import yaml
            with open(index_yaml_path, "r", encoding="utf-8") as f:
                index_data = yaml.safe_load(f) or {"entries": []}
            existing_urls = {e.get("url") for e in index_data.get("entries", [])}

        succeeded = 0
        failed = 0
        skipped = 0
        total = len(urls)

        for i, url in enumerate(urls):
            if supported_platform(url) is None:
                logger.error("[%s/%s] Unsupported video URL returned by profile: %s", i + 1, total, url)
                failed += 1
                continue
            if url in existing_urls:
                logger.info(f"[{i+1}/{total}] SKIP (already in library): {url}")
                skipped += 1
                continue

            logger.info(f"\n{'='*60}")
            logger.info(f"[{i+1}/{total}] Processing: {url}")
            logger.info(f"{'='*60}")

            try:
                ok = process_single_video(url, args)
            except RateLimitedError as e:
                logger.error(f"Rate limited on {url}: {e}")
                failed += 1
                break
            except FlaggedChannelsConfigError as e:
                # Same watchlist for every remaining video: stop, don't fail each one.
                logger.error(f"Aborting batch at {url}: {e}")
                failed += 1
                break

            if ok:
                succeeded += 1
            else:
                failed += 1

            # Delay between videos (skip delay after last video)
            if i < total - 1 and args.delay > 0:
                logger.info(f"[*] Waiting {args.delay}s before next video...")
                time.sleep(args.delay)

        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH COMPLETE: {succeeded} succeeded, {failed} failed, {skipped} skipped (already in library)")
        logger.info(f"{'='*60}")
        if failed:
            sys.exit(1)
        return

    try:
        ok = process_single_video(url, args)
    except RateLimitedError as e:
        logger.error(f"Rate limited on {url}: {e}")
        sys.exit(1)
    except FlaggedChannelsConfigError as e:
        logger.error(f"CRITICAL ERROR: {e}")
        sys.exit(1)

    if not ok:
        logger.error("CRITICAL ERROR: Processing failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
