"""Quote gate: does each cited source load, and does it contain the quoted passage?

FACT_CHECK_PROTOCOL.md F1 (graded from a snippet) and F3 (graded from memory) leave the
same trace: a claim row cites a URL, but the words the grade rests on are not in it.
This script fetches every source URL in a report's claim tables and looks for the row's
evidence quote in the page text. The evidence quote sits in the Source cell beside its
link, "..." or “...”, 12+ characters: [PFN factsheet](url) "Employees: Approx. 450".

Per row with a source link:
  supported   a quoted passage was found in a fetched source
  not_found   sources loaded, but none contains any quoted passage
  unreachable no source loaded (dead link, paywall, block, unreadable PDF)
  no_quote    the Source cell quotes nothing, so there is nothing to check

Exits 1 when any row is not_found or unreachable. Fix the source or the quote, or set
the grade to Unchecked, before filing. A miss is a prompt to look, not proof the grade
is wrong: paywalls and script-rendered pages also land here.

    uv run scripts/verify_quotes.py library/<report>.md
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.librarian import _CLAIM_HEADER, _FENCE_RE, _TABLE_SEP_RE, _split_row  # noqa: E402

USER_AGENT = "research-reader/1.0"
MAX_BYTES = 8 * 1024 * 1024
MIN_QUOTE = 12
PAUSE_S = 0.5

# A quote opens after a space, bracket or cell start and closes before a space,
# punctuation or cell end, and its text neither starts nor ends with a space. That stops a
# stray quote mark from pairing with the next one and "quoting" the prose between them.
_QUOTE_RE = re.compile(
    r'(?:^|(?<=[\s(\[:*]))(?:"(\S[^"\n]{%d,398}\S)"|“(\S[^”\n]{%d,398}\S)”)(?=$|[\s.,;:)\]!?*])'
    % (MIN_QUOTE - 2, MIN_QUOTE - 2))
# One level of balanced parentheses, so Wikipedia-style URLs aren't cut at the first ')'.
_LINK_HREF_RE = re.compile(r'\]\((https?://(?:[^()\s]|\([^()\s]*\))+)\)')
_BARE_URL_RE = re.compile(r'(?<!\()https?://[^\s)\]|>]+')
_ELLIPSIS_RE = re.compile(r'\s*(?:…|\.\.\.)\s*')
_TAG_RE = re.compile(r'<[^>]+>')
_DROP_BLOCKS_RE = re.compile(r'<(script|style|noscript)\b.*?</\1>', re.S | re.I)
_NON_WORD_RE = re.compile(r'[\W_]+')


def normalize(text: str) -> str:
    """Casefold, NFKC-fold, and reduce punctuation and spacing to single spaces.

    Letters in any script survive, so a Cyrillic or CJK quote is compared, not erased.
    """
    text = unicodedata.normalize("NFKC", text).casefold()
    return _NON_WORD_RE.sub(" ", text).strip()


def extract_rows(report: str) -> List[Dict[str, Any]]:
    """Claim-table rows with their source URLs and quoted passages.

    Table detection matches the librarian's claim-source audit: a header cell containing
    "claim", tables in balanced fenced blocks skipped. Only quotes in the Source cell are
    evidence. Notes and claim cells quote the speaker, whose words are not expected to
    be on the source page.
    """
    lines = report.splitlines()
    fences_balanced = sum(1 for ln in lines if _FENCE_RE.match(ln)) % 2 == 0
    rows: List[Dict[str, Any]] = []
    in_fence = False
    i = 0
    while i < len(lines) - 1:
        if fences_balanced and _FENCE_RE.match(lines[i]):
            in_fence = not in_fence
            i += 1
            continue
        line, nxt = lines[i].strip(), lines[i + 1].strip()
        if in_fence or not (line.startswith('|') and _TABLE_SEP_RE.match(nxt)):
            i += 1
            continue
        header = [h.lower() for h in _split_row(line)]
        claim_idx = next((n for n, h in enumerate(header) if _CLAIM_HEADER in h), None)
        if claim_idx is None:
            i += 1
            continue
        src_idx = next((n for n, h in enumerate(header) if "source" in h), None)
        i += 2
        while i < len(lines) and lines[i].strip().startswith('|'):
            cells = _split_row(lines[i])
            src = cells[src_idx] if src_idx is not None and src_idx < len(cells) else ""
            urls = list(dict.fromkeys(
                u.rstrip('.,;') for u in _LINK_HREF_RE.findall(src) + _BARE_URL_RE.findall(src)))
            quotes = [a or b for a, b in _QUOTE_RE.findall(src)]
            rows.append({
                "line": i + 1,
                "row": cells[0] if cells else "",
                "claim": cells[claim_idx] if claim_idx < len(cells) else "",
                "urls": urls,
                "quotes": quotes,
            })
            i += 1
    return rows


def quote_in(quote: str, page: str) -> bool:
    """True when every ellipsis-separated fragment of the quote appears in the page.

    Fragments shorter than MIN_QUOTE are ignored; if nothing that long is left, the whole
    quote must appear. A quote that normalizes to nothing never matches: an empty string
    is in every page.
    """
    parts = [normalize(p) for p in _ELLIPSIS_RE.split(quote)]
    parts = [p for p in parts if len(p) >= MIN_QUOTE] or [normalize(quote)]
    return all(parts) and all(p in page for p in parts)


def html_to_text(body: str) -> str:
    """Visible text of an HTML page: scripts and styles dropped, tags removed, entities decoded."""
    return html.unescape(_TAG_RE.sub(" ", _DROP_BLOCKS_RE.sub(" ", body)))


class FetchError(Exception):
    """A source could not be read; the message says why and is printed with the row."""


def _pdf_text(data: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(data)
        f.flush()
        try:
            out = subprocess.run(["pdftotext", "-layout", "-q", f.name, "-"], capture_output=True,
                                 timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise FetchError(f"pdftotext failed: {exc}") from exc
    if out.returncode != 0:
        raise FetchError(f"pdftotext exit {out.returncode}")
    return out.stdout.decode("utf-8", "replace")


def fetch_text(url: str) -> str:
    """Page text for a URL (HTML stripped, PDF extracted). Raises FetchError if unreadable."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read(MAX_BYTES)
            ctype = resp.headers.get("Content-Type", "")
    except Exception as exc:
        raise FetchError(f"{type(exc).__name__}: {exc}") from exc
    if data[:4] == b"%PDF" or "pdf" in ctype:
        return _pdf_text(data)
    return html_to_text(data.decode("utf-8", "replace"))


def check(rows: List[Dict[str, Any]],
          fetch: Callable[[str], Optional[str]] = fetch_text,
          pause: float = PAUSE_S) -> List[Dict[str, Any]]:
    """Attach a status to every row that cites a source. Each URL is fetched once."""
    cache: Dict[str, Optional[str]] = {}
    errors: Dict[str, str] = {}
    results = []
    for row in rows:
        urls, quotes = row["urls"], row["quotes"]
        if not urls:
            continue
        if not quotes:
            results.append({**row, "status": "no_quote"})
            continue
        pages = []
        for url in urls:
            if url not in cache:
                try:
                    text = fetch(url)
                except FetchError as exc:
                    errors[url] = str(exc)
                    text = None
                if text is not None and not normalize(text):
                    errors[url] = "loaded, but no text extracted (script-built page or image PDF?)"
                cache[url] = normalize(text) if text else None
                if pause:
                    time.sleep(pause)
            if cache[url]:
                pages.append(cache[url])
        if not pages:
            status = "unreachable"
        elif any(quote_in(q, p) for q in quotes for p in pages):
            status = "supported"
        else:
            status = "not_found"
        results.append({**row, "status": status,
                        "errors": [f"{u}: {errors[u]}" for u in urls if u in errors]})
    return results


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    results = check(extract_rows(args.report.read_text(encoding="utf-8")), fetch_text, PAUSE_S)
    counts: Dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        if r["status"] in ("not_found", "unreachable"):
            print(f"{r['status']:11} line {r['line']} row {r['row']}: {str(r['claim'])[:80]}")
            for err in r.get("errors", []):
                print(f"            {err}")
    print("summary: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
          if counts else "summary: no claim rows with sources")
    return 1 if counts.get("not_found") or counts.get("unreachable") else 0


if __name__ == "__main__":
    sys.exit(main())
