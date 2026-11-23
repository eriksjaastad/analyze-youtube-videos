from scripts import verify_quotes as vq

REPORT = """\
| # | Claim | Grade | Source | Note |
|---|---|---|---|---|
| 1 | "Nvidia sells 4nm chips" here | ✅ | [Fact sheet](https://a.example/doc) "Employees: Approx. 450 people" | ok |
| 2 | Second claim | ❌ | [Page](https://b.example/x) "this sentence is not there" | x |
| 3 | Third claim | ⚠️ | [Dead](https://dead.example/) "a quote from a dead page" | x |
| 4 | Fourth claim | ✅ | [Page](https://a.example/doc) | He said "a speaker quote in the notes" |
| 5 | Fifth claim | ⚪ | | "no source to check here" |

```
| # | Claim | Source |
|---|---|---|
| 9 | fenced example | [x](https://never.example/) |
```
"""

PAGES = {
    "https://a.example/doc": "Employees: Approx. 450 people work here.",
    "https://b.example/x": "Something else entirely.",
    "https://dead.example/": None,
}


def _run(report=REPORT):
    fetched = []

    def fetch(url):
        fetched.append(url)
        return PAGES.get(url)

    return {r["row"]: r["status"] for r in vq.check(vq.extract_rows(report), fetch, 0)}, fetched


def test_four_outcomes():
    statuses, _ = _run()
    assert statuses == {"1": "supported", "2": "not_found", "3": "unreachable", "4": "no_quote"}


def test_unsourced_and_fenced_rows_are_skipped_and_urls_fetched_once():
    statuses, fetched = _run()
    assert "5" not in statuses and "9" not in statuses
    assert sorted(fetched) == sorted(set(fetched))
    assert "https://never.example/" not in fetched


def test_only_source_cell_quotes_are_evidence():
    rows = vq.extract_rows(REPORT)
    assert rows[0]["quotes"] == ["Employees: Approx. 450 people"]
    assert rows[3]["quotes"] == []


def test_ellipsis_fragments_must_each_appear():
    page = vq.normalize("The first long fragment is here. Then much later, the second long fragment.")
    assert vq.quote_in("first long fragment … the second long fragment", page)
    assert not vq.quote_in("first long fragment … a missing long fragment", page)


def test_main_exit_code(tmp_path, monkeypatch):
    path = tmp_path / "r.md"
    path.write_text(REPORT)
    monkeypatch.setattr(vq, "fetch_text", lambda u: PAGES.get(u))
    monkeypatch.setattr(vq, "PAUSE_S", 0)
    assert vq.main([str(path)]) == 1
    path.write_text(REPORT.split("\n| 2 |")[0] + "\n")
    assert vq.main([str(path)]) == 0


def test_html_to_text_drops_scripts_and_decodes_entities():
    text = vq.html_to_text("<html><script>var x = 'Approx';</script><p>Employees:&nbsp;Approx.&nbsp;450</p>")
    assert vq.quote_in("Employees: Approx. 450 people"[:22], vq.normalize(text))
    assert "var x" not in text


def test_stray_quote_marks_do_not_pair_across_prose():
    report = ('| # | Claim | Source |\n|---|---|---|\n'
              '| 1 | x | [s](https://a.example/doc) said "handed over" is fair, engineers: "hundreds" back |\n'
              '| 2 | y | [s](https://a.example/doc) 6" wafers and 8" wafers differ a lot here |\n')
    rows = vq.extract_rows(report)
    assert rows[0]["quotes"] == [] and rows[1]["quotes"] == []


def test_fetch_errors_are_reported_with_the_row():
    def fetch(url):
        raise vq.FetchError("HTTPError: 403 Forbidden")
    rows = vq.extract_rows(REPORT)[:1]
    result = vq.check(rows, fetch, 0)[0]
    assert result["status"] == "unreachable"
    assert result["errors"] == ["https://a.example/doc: HTTPError: 403 Forbidden"]


def test_non_latin_quotes_are_compared_not_erased():
    quote = "Это предложение на русском языке"
    assert not vq.quote_in(quote, vq.normalize("Totally unrelated english page text here."))
    assert vq.quote_in(quote, vq.normalize("Вот: «Это предложение на русском языке», да."))
    assert vq.normalize("日本の人口は減少している") != ""
    assert not vq.quote_in("!!! ... ???", vq.normalize("any page at all"))


def test_urls_with_parentheses_are_kept_whole():
    report = ('| # | Claim | Source |\n|---|---|---|\n'
              '| 1 | x | [Wiki](https://en.wikipedia.org/wiki/Mercury_(planet)) "the smallest planet" |\n')
    assert vq.extract_rows(report)[0]["urls"] == ["https://en.wikipedia.org/wiki/Mercury_(planet)"]


def test_page_with_no_text_says_so():
    result = vq.check(vq.extract_rows(REPORT)[:1], lambda u: "   ", 0)[0]
    assert result["status"] == "unreachable"
    assert "no text extracted" in result["errors"][0]
