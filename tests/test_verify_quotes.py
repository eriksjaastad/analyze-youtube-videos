import http.server
import threading

import pytest
from citecheck import Fetcher

from scripts import verify_quotes as vq

PAGES = {
    "/doc": (200, b"<p>Employees: Approx. 450 people work here. Growth was 40% last year.</p>"),
    "/x": (200, b"<p>Something else entirely.</p>"),
    "/paywall": (403, b"no"),
    "/gone": (404, b""),
    "/blank": (200, b"<html><script>render()</script></html>"),
}


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        code, body = PAGES.get(self.path, (404, b""))
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
    return Fetcher("test-agent/1.0", min_interval=0)


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


def test_whole_word_matching_rejects_a_digit_prefix(base):
    report = ("| # | Claim | Source |\n|---|---|---|\n"
              f'| 1 | x | [s]({base}/doc) "Growth was 4% last year" |\n')
    assert vq.check(vq.extract_rows(report), _fetcher())[0]["status"] == "not_found"


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
