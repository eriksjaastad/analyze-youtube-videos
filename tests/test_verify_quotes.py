import http.server
import io
import threading
from collections import Counter

import pytest
from pypdf import PdfWriter

from scripts import verify_quotes as vq


def _locked_pdf():
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    writer.encrypt("secret")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


PAGES = {
    "/doc": (200, b"<p>Employees: Approx. 450 people work here. Growth was 40% last year.</p>"),
    "/x": (200, b"<p>Something else entirely.</p>"),
    "/paywall": (403, b"no"),
    "/gone": (404, b""),
    "/blank": (200, b"<html><script>render()</script></html>"),
    "/legal": (200, b"<p>Police found illegal activity. The index moved -5.5% in May.</p>"),
    "/refs": (200, b'<p>The treatment reduced mortality<sup><a href="#ref1" role="doc-noteref">1</a>'
                  b'</sup> in adults.</p>'),
    "/broken.pdf": (200, b"%PDF-1.4 this is not really a pdf"),
    "/locked.pdf": (200, _locked_pdf()),
}
HITS = Counter()


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        HITS[self.path] += 1
        code, body = PAGES.get(self.path, (404, b""))
        if self.path == "/once" and HITS[self.path] > 1:  # rate-limits the second request
            code, body = 429, b""
        elif self.path == "/once":
            code, body = 200, b"<p>Employees: Approx. 450 people work here.</p>"
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def base():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _fetcher():
    return vq.OnceFetcher("test-agent/1.0", min_interval=0)


def _report(base):
    return f"""\
| # | Claim | Grade | Source | Note |
|---|---|---|---|---|
| 1 | "Nvidia sells 4nm chips" here | ✅ | [Fact sheet]({base}/doc) "Employees: Approx. 450 people" | ok |
| 2 | Second claim | ❌ | [Page]({base}/x) "this sentence is not there" | x |
| 3 | Third claim | ⚠️ | [Dead]({base}/gone) "a quote from a dead page" | x |
| 4 | Fourth claim | ✅ | [Page]({base}/doc) | He said "a speaker quote in the notes" |
| 5 | Fifth claim | ⚪ | | "no source to check here" |
| 6 | Sixth claim | ✅ | [Paywall]({base}/paywall) "words behind the wall" | x |
| 7 | Seventh claim | ✅ | [Blank]({base}/blank) "words never rendered" | x |
| 8 | Eighth claim | ✅ | [Dead]({base}/gone) [Fact sheet]({base}/doc) "Approx. 450 people work" | x |

```
| # | Claim | Source |
|---|---|---|
| 9 | fenced example | [x](https://never.example/) |
```
"""


def test_each_outcome(base):
    results = vq.check(vq.extract_rows(_report(base)), _fetcher())
    assert {r["row"]: r["status"] for r in results} == {
        "1": "supported", "2": "not_found", "3": "unreachable", "4": "no_quote",
        "6": "blocked", "7": "unreachable", "8": "supported"}


def test_failures_say_why(base):
    results = {r["row"]: r for r in vq.check(vq.extract_rows(_report(base)), _fetcher())}
    assert "HTTP 403" in results["6"]["errors"][0]
    assert "no text extracted" in results["7"]["errors"][0]
    assert results["8"]["errors"] == []


def _statuses(base, *cells):
    report = "| # | Claim | Source |\n|---|---|---|\n" + "".join(
        f"| {n} | x | {cell.format(base=base)} |\n" for n, cell in enumerate(cells, 1))
    return [r["status"] for r in vq.check(vq.extract_rows(report), _fetcher())]


def test_matching_keeps_whole_words_and_signs(base):
    # The old matcher passed both misses: it found "legal" inside "illegal" and dropped signs.
    assert _statuses(base,
                     '[s]({base}/legal) "legal activity"',
                     '[s]({base}/legal) "index moved 5.5% in May"',
                     '[s]({base}/legal) "found illegal activity"',
                     '[s]({base}/legal) "index moved -5.5% in May"',
                     ) == ["not_found", "not_found", "supported", "supported"]


def test_bad_pdfs_are_unreachable_and_the_run_goes_on(base):
    assert _statuses(base,
                     '[s]({base}/broken.pdf) [t]({base}/doc) "Approx. 450 people work"',
                     '[s]({base}/locked.pdf) "words inside a locked file"',
                     '[s]({base}/doc) "Employees: Approx. 450 people"',
                     ) == ["supported", "unreachable", "supported"]


def test_each_source_is_fetched_once_per_run(base):
    HITS.clear()
    assert _statuses(base,
                     '[s]({base}/once) "Employees: Approx. 450"',
                     '[s]({base}/once) "this sentence is not there" "Approx. 450 people work"',
                     '[s]({base}/once) "Approx. 450 people"',
                     ) == ["supported", "supported", "supported"]
    assert HITS["/once"] == 1


def test_only_source_cell_quotes_are_evidence(base):
    rows = vq.extract_rows(_report(base))
    assert rows[0]["quotes"] == ["Employees: Approx. 450 people"]
    assert rows[3]["quotes"] == []


def test_stray_quote_marks_do_not_pair_across_prose():
    report = ('| # | Claim | Source |\n|---|---|---|\n'
              '| 1 | x | [s](https://a.example/doc) said "handed over" is fair, engineers: "hundreds" back |\n'
              '| 2 | y | [s](https://a.example/doc) 6" wafers and 8" wafers differ a lot here |\n')
    rows = vq.extract_rows(report)
    assert rows[0]["quotes"] == [] and rows[1]["quotes"] == []


def test_urls_with_parentheses_are_kept_whole():
    report = ('| # | Claim | Source |\n|---|---|---|\n'
              '| 1 | x | [Wiki](https://en.wikipedia.org/wiki/Mercury_(planet)) "the smallest planet" |\n')
    assert vq.extract_rows(report)[0]["urls"] == ["https://en.wikipedia.org/wiki/Mercury_(planet)"]


def test_main_exit_code(base, tmp_path):
    path = tmp_path / "r.md"
    path.write_text(_report(base))
    assert vq.main([str(path)], _fetcher()) == 1
    path.write_text(_report(base).split("\n| 2 |")[0] + "\n")
    assert vq.main([str(path)], _fetcher()) == 0


@pytest.mark.parametrize("cell, code", [
    ('[s]({base}/x) "this sentence is not there"', 1),       # not_found
    ('[s]({base}/paywall) "words behind the wall"', 1),       # blocked
    ('[s]({base}/gone) "a quote from a dead page"', 1),       # unreachable
    ('[s]({base}/doc) "Employees: Approx. 450 people"', 0),   # supported
    ('[s]({base}/doc)', 0),                                    # no_quote
])
def test_each_failing_outcome_alone_fails_the_gate(base, tmp_path, cell, code):
    path = tmp_path / "r.md"
    path.write_text(f"| # | Claim | Source |\n|---|---|---|\n| 1 | x | {cell.format(base=base)} |\n")
    assert vq.main([str(path)], _fetcher()) == code


def test_footnote_markers_do_not_glue_to_words(base):
    assert _statuses(base, '[s]({base}/refs) "The treatment reduced mortality in adults"') == ["supported"]
