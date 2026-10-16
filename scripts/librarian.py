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
    writes the report to library/ and adds it to library/index.yaml, the
    record of what has been analyzed. Video data comes from
    --data-file when given, otherwise from a fetch cache file whose url
    matches, otherwise from a metadata-only fetch; save never downloads
    subtitles or audio.

    A channel on config/flagged_channels.yaml emits a warning in both fetch
    and save modes; the "flag" object only appears in the fetch JSON. It
    never blocks.

Supported platforms
-------------------
YouTube (youtube.com, youtu.be), TikTok (tiktok.com), and Instagram
(instagram.com) posts/reels.

CLI flags
---------
url
    YouTube, TikTok, or Instagram URL to process.
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
0  Success.
1  Failure: fetching or saving the video failed.
2  Argparse usage error: missing url, unsupported URL/host, unknown flag, or
   invalid flag value.
"""
import os
import sys
import argparse
import tempfile
import json
import subprocess
import re
import yaml
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlsplit
from scripts.config import LIBRARY_DIR, TEMP_DIR, choose_subtitle_track, initialize_directories, safe_slug, logger, apply_replacements

# data/ is gitignored; the fetch cache is a local convenience, not library content.
FETCH_CACHE_DIR = Path(os.getenv("FETCH_CACHE_DIR", "data/fetch_cache"))


class RateLimitedError(RuntimeError):
    """YouTube answered HTTP 429; retrying would only make the rate limit worse."""


class YtDlpError(RuntimeError):
    """A yt-dlp call failed: non-zero exit, timeout, or yt-dlp missing from PATH."""


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


def _yt_dlp(args: List[str], timeout: int) -> str:
    """Run yt-dlp once with args and return its stdout.

    Raises RateLimitedError on HTTP 429 and YtDlpError on any other failure.
    There is no outer retry: yt-dlp already retries transient network errors
    itself (--retries, --extractor-retries), and re-running a failed call only
    multiplies the YouTube requests that the rate limit counts.
    """
    try:
        result = subprocess.run(["yt-dlp", *args], capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise YtDlpError(f"yt-dlp did not complete: {e}") from e
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        if is_rate_limited(stderr):
            raise RateLimitedError(stderr)
        raise YtDlpError(f"yt-dlp exited {result.returncode}: {stderr}")
    return result.stdout


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
    """Download the video's audio as MP3 into temp_dir for Whisper; None on failure."""
    audio_path = temp_dir / "audio.mp3"
    logger.info("[*] Downloading audio for Whisper transcription...")
    try:
        # yt-dlp adds the .mp3 extension itself.
        _yt_dlp(["--extract-audio", "--audio-format", "mp3",
                 "--output", str(audio_path.with_suffix("")), url], timeout=300)
    except YtDlpError as e:  # governance: allow-silent SF002: None is download_audio's failure result; with no caption track either, _fetch_transcript returns None and the CLI exits 1
        logger.error(f"Audio download failed: {e}")
        return None
    if not audio_path.exists():
        logger.error(f"Audio file not found at {audio_path}")
        return None
    return audio_path

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
    """Fetch one video's metadata and transcript as the librarian's video dict.

    Returns None when the metadata call fails or no transcript source works.
    RateLimitedError propagates so the caller stops instead of fetching more.
    With metadata_only=True only the metadata call runs and the transcript is
    empty: no subtitle, audio, or Whisper.
    """
    logger.info(f"[*] Fetching metadata for: {url}")
    try:
        # --dump-json simulates, so nothing downloads. --write-subs makes the
        # TikTok extractor, which lists captions only on request, include them
        # in the metadata that choose_subtitle_track reads.
        metadata = json.loads(_yt_dlp(["--dump-json", "--write-subs", url], timeout=60))
    except (YtDlpError, json.JSONDecodeError) as e:  # governance: allow-silent SF002: None is get_video_data's failure result; process_single_video returns False and main() exits 1
        logger.error(f"Error fetching metadata: {e}")
        return None
    transcript = "" if metadata_only else _fetch_transcript(url, metadata, use_whisper_fallback)
    if transcript is None:
        return None
    return _video_fields(metadata, url, transcript)


def _fetch_transcript(url: str, metadata: Dict[str, Any], use_whisper_fallback: bool) -> Optional[str]:
    """The cleaned caption track the metadata lists, else a Whisper transcript, else None."""
    with tempfile.TemporaryDirectory(dir=TEMP_DIR, prefix="transcript_") as temp_dir:
        work_dir = Path(temp_dir)
        track = choose_subtitle_track(metadata)
        if track:
            sub_lang, is_auto = track
            logger.info(f"[*] Fetching {'auto' if is_auto else 'manual'} subtitle track {sub_lang}...")
            try:
                _yt_dlp([
                    "--skip-download",
                    "--write-auto-subs" if is_auto else "--write-subs",
                    "--sub-lang", sub_lang,
                    "--sub-format", "srt/vtt/best",
                    "--output", str(work_dir / "transcript"),
                    url,
                ], timeout=120)
            except YtDlpError as e:  # governance: allow-silent SF002: a failed subtitle call falls through to the Whisper fallback; with no transcript at all this returns None and the CLI exits 1
                logger.warning(f"Subtitle fetch failed for {url}: {e}")
            sub_file = next((f for f in sorted(work_dir.iterdir()) if f.suffix in (".srt", ".vtt")), None)
            if sub_file:
                logger.info(f"[*] Using subtitle track {sub_file.name}")
                return clean_srt(sub_file.read_text(encoding="utf-8"))
        else:
            logger.warning("Metadata lists no English subtitle track.")
        logger.warning("No SRT transcript found.")

        transcript = None
        if use_whisper_fallback:
            logger.info("[*] Attempting Whisper fallback...")
            audio_path = download_audio(url, work_dir)
            transcript = transcribe_with_whisper(audio_path) if audio_path else None
        if not transcript:
            logger.error("No transcript available (SRT and Whisper both failed)")
            return None
        logger.info("[+] Using Whisper-generated transcript")
        return transcript


def _video_fields(metadata: Dict[str, Any], url: str, transcript: str) -> Dict[str, Any]:
    """Map yt-dlp metadata to the librarian's video dict, per platform."""
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
        "chapters": extract_chapters(metadata),
        "platform": platform
    }


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
# A table is a claim table if any header cell contains "claim", the one invariant word
# across the library's 16 header shapes. Over-flagging costs an ignored warning; a miss
# costs an unsourced grade. DECISIONS.md has the versions that failed.
_CLAIM_HEADER = "claim"


_UNESCAPED_PIPE_RE = re.compile(r'(?<!\\)\|')


def _split_row(line: str) -> List[str]:
    """Split a markdown table row into trimmed cells, dropping the outer pipes.

    Splits on unescaped pipes only, so a \\| inside claim text can't shift column
    alignment and mislabel a sourced row as unsourced.
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
    Positional on purpose: a vocabulary allowlist is always one spelling behind.
    """
    words = _WORD_RE.findall(cell.lower())
    return bool(words) and words[0] == "unverified"


def audit_claim_sources(analysis: str) -> Optional[Dict[str, Any]]:
    """Count claim-table rows whose Source cell is empty.

    Rule 0 of FACT_CHECK_PROTOCOL.md: the source goes in the row, because an unsourced
    grade and a sourced grade are visually identical without it — which is how two of the
    2026-08-14 overturns survived review. A bulk '## Sources' list proves nothing about
    any individual grade, so it deliberately does not count here.

    Detection reads the table HEADER, matching only on the word "claim" (see
    _CLAIM_HEADER). A table with no Source column at
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
                # Unverified is the one grade where the protocol asks for a search trail
                # instead of a link. Only that grade, so a prose "Note" column can't
                # launder an uncited table (the 2026-08-14 pattern).
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


def report_date(data: Dict[str, Any]) -> date:
    """The upload date from yt-dlp's YYYYMMDD, or today when it is missing or not a real date."""
    raw = data.get("date") or ""
    if len(raw) != 8:
        return date.today()
    try:
        return datetime.strptime(raw, "%Y%m%d").date()
    except ValueError:  # governance: allow-silent SF002: a malformed upload date is logged and the report is filed under today, as for a missing one
        logger.warning(f"Upload date {raw!r} is not a real date; filing under today")
        return date.today()


def save_to_library(data: Dict[str, Any], analysis: str, subdir: Optional[str] = None) -> Path:
    """
    Saves the final report to the library/ directory.
    Uses video_id and safe_slug to prevent filename collisions and ensure safety.

    `subdir` files the report under library/<subdir>/ instead of the flat root, for
    topic collections that accumulate over time (see library/*/README.md).
    """
    upload_date = report_date(data)

    clean_title = safe_slug(data['title'])
    clean_channel = safe_slug(data['channel'])

    vid_id = safe_slug(data.get('video_id', 'unknown'))[:8]
    filename = f"{upload_date.isoformat()}_{clean_channel}_{clean_title[:40]}_{vid_id}.md"

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

    # safe_dump, not an f-string: a title with a quote or a "#" must still be valid YAML.
    frontmatter = yaml.safe_dump({
        "tags": tags,
        "status": "#status/active",
        "created": date.today(),
        "url": data["url"],
        "title": data["title"],
        "channel": data["channel"],
        "upload_date": upload_date,
        "views": data["view_count"],
        "likes": data["like_count"],
        "duration": data["duration_string"],
    }, allow_unicode=True, sort_keys=False, width=float("inf"))
    content = f"""---
{frontmatter}---

# {data['title']}

> **Channel:** [{data['channel']}]({data['url']}) | **Duration:** {data['duration_string']} | **Views:** {data['view_count']:,}
{chapter_section}
{analysis}
"""
    
    atomic_write(filepath, content)
    logger.info(f"[+] Saved to: {filepath}")
    return filepath

def load_index() -> Dict[str, Any]:
    """library/index.yaml, the record of what has been analyzed; empty when none exists yet.

    An index that exists but is not a mapping with an 'entries' list of
    mappings raises ValueError (or yaml.YAMLError) instead of being replaced:
    a replaced index would hold only the next entry.
    """
    index_yaml_path = LIBRARY_DIR / "index.yaml"
    if not index_yaml_path.exists():
        return {"entries": []}
    with open(index_yaml_path, "r", encoding="utf-8") as f:
        index_data = yaml.safe_load(f)
    entries = index_data.get("entries") if isinstance(index_data, dict) else None
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise ValueError(f"{index_yaml_path} must be a mapping with an 'entries' list of mappings; fix it before saving")
    return index_data


def add_to_index(index_data: Dict[str, Any], entry_data: Dict[str, Any]) -> None:
    """Append one report to the loaded index and write it; an already-indexed url is left as it is."""
    if any(entry.get("url") == entry_data["url"] for entry in index_data["entries"]):
        logger.info(f"Entry for {entry_data['title']} already exists in index. Skipping.")
        return
    index_data["entries"].append(entry_data)
    # str(): older entries may hold a YAML date or null, which can't be compared with a string.
    index_data["entries"].sort(key=lambda x: str(x.get("date") or ""), reverse=True)
    index_yaml_path = LIBRARY_DIR / "index.yaml"
    atomic_write(index_yaml_path, yaml.safe_dump(index_data, allow_unicode=True, sort_keys=False))
    logger.info(f"Updated index at {index_yaml_path}")


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

    # Rule 0 audit runs on the way in, so an unsourced claim table is caught at the moment
    # it lands rather than on a re-read months later. Reports, never blocks — a false
    # positive costs one ignored warning, a missed one costs an unsourced grade in the library.
    source_stats = audit_claim_sources(analysis)
    if source_stats:
        emit_claim_source_audit(source_stats)

    # Loaded before the report is written, so a broken index leaves no orphaned report.
    index_data = load_index()
    filepath = save_to_library(data, analysis, subdir=getattr(args, "subdir", None))

    # Prepare index entry data
    entry_data = {
        "title": data['title'],
        "channel": data['channel'],
        "date": report_date(data).isoformat(),
        "url": url,
        "filepath": str(filepath)
    }
    # Derive the collection from where the file actually landed, not from the raw flag —
    # a subdir that sanitizes to empty falls back to the root and gets no collection tag.
    if filepath.parent != LIBRARY_DIR:
        entry_data["collection"] = filepath.parent.name

    add_to_index(index_data, entry_data)
    return True


def build_parser() -> argparse.ArgumentParser:
    """Build the librarian CLI parser. The module docstring is the description."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="YouTube, TikTok, or Instagram URL to process")
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

    url = args.url
    if supported_platform(url) is None:
        parser.error("Expected a YouTube, TikTok, or Instagram HTTP(S) URL on a supported host")

    initialize_directories()

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
