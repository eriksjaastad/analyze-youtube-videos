"""Quote gate: does each cited source load, and does it contain the quoted passage?

FACT_CHECK_PROTOCOL.md F1 (graded from a snippet) and F3 (graded from memory) leave the
same trace: a claim row cites a URL, but the words the grade rests on are not in it.
This script reads the claim tables of a report and hands every source URL and evidence
quote to citecheck, which fetches the page and does the matching. The evidence quote
sits in the Source cell beside its link, "..." or “...”, 12+ characters:
[PFN factsheet](url) "Employees: Approx. 450".

Per row with a source link:
  supported   a quoted passage was found in a fetched source
  not_found   a source was read whole, and no quoted passage is in any source
  blocked     the sources refused us (401, 402, 403, 429, 451): paywall or bot wall
  unreachable no source was read (dead link, timeout, script-built page, image PDF)
  no_quote    the Source cell quotes nothing, so there is nothing to check

Matching is citecheck's: whole words, with signs, decimals and percent kept, so "4%"
is not in "40%". Exits 1 when any row is not_found, blocked or unreachable. Fix the
source or the quote, or set the grade to Unchecked, before filing. A miss is a prompt
to look, not proof the grade is wrong.

    uv run scripts/verify_quotes.py library/<report>.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from citecheck import Citation, EmptySourceError, Fetcher, FetchError, Status, check_quote
from pypdf.errors import PyPdfError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.librarian import _CLAIM_HEADER, _FENCE_RE, _TABLE_SEP_RE, _split_row  # noqa: E402

USER_AGENT = "research-reader/1.0"
MIN_QUOTE = 12

# A quote opens after a space, bracket or cell start and closes before a space,
# punctuation or cell end, and its text neither starts nor ends with a space. That stops a
# stray quote mark from pairing with the next one and "quoting" the prose between them.
_QUOTE_RE = re.compile(
    r'(?:^|(?<=[\s(\[:*]))(?:"(\S[^"\n]{%d,398}\S)"|“(\S[^”\n]{%d,398}\S)”)(?=$|[\s.,;:)\]!?*])'
    % (MIN_QUOTE - 2, MIN_QUOTE - 2))
# One level of balanced parentheses, so Wikipedia-style URLs aren't cut at the first ')'.
_LINK_HREF_RE = re.compile(r'\]\((https?://(?:[^()\s]|\([^()\s]*\))+)\)')
_BARE_URL_RE = re.compile(r'(?<!\()https?://[^\s)\]|>]+')


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


class OnceFetcher(Fetcher):
    """A citecheck Fetcher that downloads each URL once per run.

    citecheck fetches per citation. A report quotes the same source in many rows, and a
    site that rate-limits the second request would turn a supported row into blocked.
    """

    def __init__(self, user_agent: str, **kwargs: Any) -> None:
        super().__init__(user_agent, **kwargs)
        self._seen: Dict[tuple, Any] = {}
        self.requests = 0

    def _get(self, url: str, *, read_body: bool = True):
        key = (url, read_body)
        if key not in self._seen:
            self.requests += 1
            try:
                self._seen[key] = super()._get(url, read_body=read_body)
            except FetchError as exc:
                self._seen[key] = exc
        hit = self._seen[key]
        if isinstance(hit, FetchError):
            raise hit
        return hit


def _one(url: str, quote: str, fetcher: Fetcher) -> tuple[str, str]:
    """citecheck's verdict on one quote in one source, as (status, reason)."""
    try:
        result = check_quote(Citation(source=url, quote=quote), network=True, fetcher=fetcher)
    except EmptySourceError:
        return "unreachable", "loaded, but no text extracted (script-built page or image PDF?)"
    except ValueError as exc:  # undecodable page, bad URL
        return "unreachable", str(exc)
    except PyPdfError as exc:  # damaged or password-protected PDF
        return "unreachable", f"PDF unreadable: {type(exc).__name__}: {exc}"
    status = {Status.SUPPORTED: "supported", Status.NOT_FOUND: "not_found",
              Status.BLOCKED: "blocked"}.get(result.status, "unreachable")
    return status, result.reason


# When a row's sources disagree, the best outcome wins: one supporting source is enough,
# and a source read whole without the quote outranks one we could not read.
_RANK = ("supported", "not_found", "blocked", "unreachable")


def check(rows: List[Dict[str, Any]], fetcher: Fetcher) -> List[Dict[str, Any]]:
    """Attach a status to every row that cites a source."""
    results = []
    for row in rows:
        urls, quotes = row["urls"], row["quotes"]
        if not urls:
            continue
        if not quotes:
            results.append({**row, "status": "no_quote", "errors": []})
            continue
        best, errors = "unreachable", []
        for url in urls:
            for quote in quotes:
                status, reason = _one(url, quote, fetcher)
                if status in ("blocked", "unreachable"):
                    errors.append(f"{url}: {reason}")
                if _RANK.index(status) < _RANK.index(best):
                    best = status
                if best == "supported":
                    break
            if best == "supported":
                break
        results.append({**row, "status": best,
                        "errors": list(dict.fromkeys(errors)) if best != "supported" else []})
    return results


def main(argv: Optional[List[str]] = None, fetcher: Optional[Fetcher] = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    rows = extract_rows(args.report.read_text(encoding="utf-8"))
    results = check(rows, fetcher or OnceFetcher(USER_AGENT))
    counts: Dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        if r["status"] in ("not_found", "blocked", "unreachable"):
            print(f"{r['status']:11} line {r['line']} row {r['row']}: {str(r['claim'])[:80]}")
            for err in r["errors"]:
                print(f"            {err}")
    print("summary: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
          if counts else "summary: no claim rows with sources")
    return 1 if any(counts.get(k) for k in ("not_found", "blocked", "unreachable")) else 0


if __name__ == "__main__":
    sys.exit(main())
