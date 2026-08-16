import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch
from scripts.librarian import clean_srt, get_video_data, check_flagged_channel, extract_research_targets
import scripts.librarian as librarian


FLAG_YAML = """
channels:
  - name: "The Diary Of A CEO"
    channel_id: "UCGq-a57w-aPwyi3pW7XLiHw"
    handle: "@TheDiaryOfACEO"
    severity: high
    reason: Test reason.
"""


@pytest.fixture
def flag_config(tmp_path, monkeypatch):
    """Point the flagged-channel check at an isolated config file."""
    cfg = tmp_path / "flagged_channels.yaml"
    cfg.write_text(FLAG_YAML)
    monkeypatch.setattr(librarian, "FLAGGED_CHANNELS_PATH", cfg)
    return cfg


def test_flagged_channel_matches_by_id(flag_config):
    # channel_id is the stable key; display name differs but ID matches.
    data = {"channel": "Some Renamed Channel", "channel_id": "UCGq-a57w-aPwyi3pW7XLiHw", "uploader_id": ""}
    entry = check_flagged_channel(data)
    assert entry is not None and entry["severity"] == "high"


def test_flagged_channel_matches_by_handle(flag_config):
    data = {"channel": "x", "channel_id": "", "uploader_id": "@TheDiaryOfACEO"}
    entry = check_flagged_channel(data)
    assert entry is not None and entry["channel_id"] == "UCGq-a57w-aPwyi3pW7XLiHw"


def test_flagged_channel_handle_match_ignores_at_prefix(flag_config):
    # TikTok-style uploader_id arrives without the '@' the config stores.
    data = {"channel": "x", "channel_id": "", "uploader_id": "thediaryofaceo"}
    entry = check_flagged_channel(data)
    assert entry is not None and entry["channel_id"] == "UCGq-a57w-aPwyi3pW7XLiHw"


def test_flagged_channel_matches_by_name_case_insensitive(flag_config):
    data = {"channel": "the diary of a ceo", "channel_id": "", "uploader_id": ""}
    entry = check_flagged_channel(data)
    assert entry is not None and entry["severity"] == "high"


def test_unflagged_channel_returns_none(flag_config):
    data = {"channel": "Your AI Guy", "channel_id": "UCsomethingelse", "uploader_id": "@YourAIGuy"}
    assert check_flagged_channel(data) is None


def test_missing_config_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(librarian, "FLAGGED_CHANNELS_PATH", tmp_path / "nope.yaml")
    assert check_flagged_channel({"channel": "Anything", "channel_id": "UCx", "uploader_id": "@x"}) is None


def test_malformed_config_returns_none(tmp_path, monkeypatch):
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("channels: [unclosed\n  - oops:")
    monkeypatch.setattr(librarian, "FLAGGED_CHANNELS_PATH", cfg)
    assert check_flagged_channel({"channel": "x", "channel_id": "UCGq-a57w-aPwyi3pW7XLiHw", "uploader_id": ""}) is None

def test_clean_srt():
    srt_content = """1
00:00:01,000 --> 00:00:02,000
Hello <b>World</b>

2
00:00:03,000 --> 00:00:04,000
This is a test.

This is a test.
"""
    cleaned = clean_srt(srt_content)
    # Check timestamp removal
    assert "00:00" not in cleaned
    assert "-->" not in cleaned
    # Check index removal
    assert "1" not in cleaned.split()
    # Check HTML stripping
    assert "<b>" not in cleaned
    assert "World" in cleaned
    # Check deduplication
    assert cleaned.count("This is a test.") == 1
    # Check extra whitespace
    assert "  " not in cleaned

def test_clean_srt_complex():
    srt = """1
00:00:01,000 --> 00:00:02,000
Line 1
Line 1

2
00:00:02,000 --> 00:00:03,000
Line 2
<font color="red">Line 3</font>

3
00:00:03,000 --> 00:00:04,000
Line 2
"""
    cleaned = clean_srt(srt)
    # Deduplication across blocks
    assert "Line 1 Line 2 Line 3 Line 2" in cleaned

@pytest.mark.parametrize("srt,expected", [
    ("1\n00:00:01,000 --> 00:00:02,000\nHello", "Hello"),
    ("1\n00:00:01,000 --> 00:00:02,000\n<b>Hi</b>", "Hi"),
    ("1\n00:00:01,000 --> 00:00:02,000\nA\n1\n00:00:02,000 --> 00:00:03,000\nA", "A"),
])
def test_clean_srt_parameterized(srt, expected):
    assert clean_srt(srt) == expected

def test_clean_srt_vtt_format():
    """Verify that VTT content (WEBVTT headers, dot timestamps) is properly cleaned."""
    vtt_content = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:02.000
Hello World

00:00:03.000 --> 00:00:04.000
This is TikTok.
"""
    cleaned = clean_srt(vtt_content)
    assert "WEBVTT" not in cleaned
    assert "Kind:" not in cleaned
    assert "Language:" not in cleaned
    assert "00:00" not in cleaned
    assert cleaned == "Hello World This is TikTok."


@patch("subprocess.run")
@patch("tempfile.TemporaryDirectory")
@patch("pathlib.Path.exists")
@patch("pathlib.Path.mkdir")
def test_get_video_data_failure_cleanup(mock_mkdir, mock_exists, mock_tempdir, mock_run):
    """Verify that cleanup (tempfile.TemporaryDirectory) is used even if subprocess.run fails."""
    mock_exists.return_value = True
    mock_run.return_value = MagicMock(returncode=1, stderr="metadata error")
    
    # Mock context manager behavior
    mock_temp_path = MagicMock()
    mock_tempdir.return_value.__enter__.return_value = str(mock_temp_path)
    
    data = get_video_data("https://youtube.com/watch?v=fail")
    
    assert data is None
    # Verify the context manager was entered
    assert mock_tempdir.called

@patch("subprocess.run")
@patch("os.listdir")
@patch("builtins.open", new_callable=MagicMock)
@patch("pathlib.Path.exists")
@patch("pathlib.Path.mkdir")
@patch("tempfile.TemporaryDirectory")
def test_get_video_data_success(mock_tempdir, mock_mkdir, mock_exists, mock_open, mock_listdir, mock_run):
    mock_exists.return_value = True
    mock_run.side_effect = [
        # First call: metadata
        MagicMock(returncode=0, stdout='{"title": "Test Title", "uploader": "Test Channel", "id": "123"}'),
        # Second call: subtitles
        MagicMock(returncode=0, stdout="", stderr="")
    ]
    
    # Mock context manager behavior
    mock_temp_path = "/tmp/fake_temp"
    mock_tempdir.return_value.__enter__.return_value = mock_temp_path
    
    mock_listdir.return_value = ["transcript.en.srt"]
    mock_open.return_value.__enter__.return_value.read.return_value = "1\n00:00:01,000 --> 00:00:02,000\nHello"
    
    data = get_video_data("https://youtube.com/watch?v=123")
    
    assert data["title"] == "Test Title"
    assert data["channel"] == "Test Channel"
    assert data["video_id"] == "123"
    assert "Hello" in data["transcript"]
    
    # Verify context manager was used
    assert mock_tempdir.called

    # Inverse Test Analysis:
    # 1. We don't test the actual library file content generated (only its presence and metadata).
    # 2. We don't test the --dry-run flag behavior in these unit tests.
    # 3. We don't test the actual yt-dlp binary output (only mocked responses).

@patch("subprocess.run")
@patch("tempfile.TemporaryDirectory")
@patch("pathlib.Path.mkdir")
def test_get_video_data_metadata_failure_simple(mock_mkdir, mock_tempdir, mock_run):
    mock_run.return_value = MagicMock(returncode=1, stderr="metadata error")
    
    # Mock context manager behavior
    mock_temp_path = "/tmp/fake_temp"
    mock_tempdir.return_value.__enter__.return_value = mock_temp_path
    
    data = get_video_data("https://youtube.com/watch?v=fail")
    assert data is None


# --- extract_research_targets -------------------------------------------------

def test_extract_research_targets_links_dedup_and_strip():
    data = {
        "description": "Watch https://youtube.com/watch?v=abc and https://hostinger.com/x.\n"
                       "Repeat https://youtube.com/watch?v=abc again. Trailing https://example.com/page,",
    }
    out = extract_research_targets(data)
    # Deduped, order preserved, trailing comma stripped.
    assert out["links"] == [
        "https://youtube.com/watch?v=abc",
        "https://hostinger.com/x",
        "https://example.com/page",
    ]


def test_extract_research_targets_hashtags_merge_description_and_tags():
    data = {"description": "Cool stuff #AI #OpenAI", "tags": ["LLM", "ai"]}
    out = extract_research_targets(data)
    # Lowercased, deduped across description hashtags and tags.
    assert out["hashtags"] == ["ai", "openai", "llm"]


def test_extract_research_targets_mentions_excludes_emails():
    # Both word-preceded (wesroth@...) and space-preceded (@smoothmedia.co) email
    # domains must be filtered; only the real social handle survives.
    data = {"description": "Reach me @WesRoth not at wesroth@smoothmedia.co or @smoothmedia.co"}
    out = extract_research_targets(data)
    assert out["mentions"] == ["WesRoth"]


def test_extract_research_targets_mentions_preserves_dotted_handles():
    # The domain filter is TLD-restricted: dotted handles whose suffix is not a
    # known TLD (Mr.Beast, john.doe) must survive; real domains (brand.io) drop.
    data = {"description": "Shoutout @Mr.Beast and @john.doe, not @brand.io"}
    out = extract_research_targets(data)
    assert out["mentions"] == ["Mr.Beast", "john.doe"]


def test_extract_research_targets_chapters_from_metadata():
    data = {"chapters": [{"timestamp": "00:00", "title": "Intro"}, {"timestamp": "02:40", "title": ""}]}
    out = extract_research_targets(data)
    assert out["chapters"] == ["Intro"]


def test_extract_research_targets_chapters_tolerates_null_entries():
    # Real yt-dlp metadata can include null/non-dict chapter entries; must not crash.
    data = {"chapters": [None, {"title": "Real"}, "bogus", {"no_title": 1}]}
    out = extract_research_targets(data)
    assert out["chapters"] == ["Real"]


def test_extract_research_targets_empty_metadata():
    out = extract_research_targets({})
    assert out == {"links": [], "hashtags": [], "mentions": [], "chapters": []}


# --- save_to_library subdir (topic collections) ---

@pytest.fixture
def library_root(tmp_path, monkeypatch):
    """Point save_to_library at a throwaway library dir."""
    root = tmp_path / "library"
    root.mkdir()
    monkeypatch.setattr(librarian, "LIBRARY_DIR", root)
    return root


VIDEO_STUB = {
    "title": "Test Video",
    "channel": "Test Channel",
    "date": "20260623",
    "url": "https://youtu.be/abc123",
    "video_id": "abc123",
    "view_count": 1,
    "like_count": 1,
    "duration_string": "1:00",
}


def test_save_to_library_without_subdir_stays_flat(library_root):
    path = librarian.save_to_library(dict(VIDEO_STUB), "body")
    assert path.parent == library_root
    assert path.exists()


def test_save_to_library_with_subdir_nests(library_root):
    path = librarian.save_to_library(dict(VIDEO_STUB), "body", subdir="agentic-work")
    assert path.parent == library_root / "agentic-work"
    assert path.exists()
    assert "body" in path.read_text()


def test_save_to_library_creates_missing_subdir(library_root):
    assert not (library_root / "brand-new").exists()
    librarian.save_to_library(dict(VIDEO_STUB), "body", subdir="brand-new")
    assert (library_root / "brand-new").is_dir()


@pytest.mark.parametrize("hostile", ["../../etc", "..", "/", "../sibling", "a/../../b"])
def test_save_to_library_subdir_cannot_escape_library(library_root, hostile):
    path = librarian.save_to_library(dict(VIDEO_STUB), "body", subdir=hostile)
    assert path.resolve().is_relative_to(library_root.resolve())
    assert ".." not in path.parts


def test_save_to_library_degenerate_subdir_falls_back_to_root(library_root):
    # "..." sanitizes to empty — must land in the root, not create a weird dir.
    path = librarian.save_to_library(dict(VIDEO_STUB), "body", subdir="...")
    assert path.parent == library_root
    assert sorted(p.name for p in library_root.iterdir()) == [path.name]


# --- get_category() keyword routing -------------------------------------------------
# get_category() uses word-boundary matching over (title + tags) and returns on the FIRST
# matching category in config order. Category order therefore remains part of the routing
# contract while short keywords no longer match inside unrelated words.
# These tests pin the collisions we have already been bitten by.

@pytest.mark.parametrize(
    "title,tags,expected",
    [
        # The case that motivated the geopolitics category: geopolitics videos tag
        # "AI drone warfare", and ai_automation's bare "ai" keyword was swallowing them.
        ("Four Ex-Stratfor Analysts Reunite to Predict How the World Ends",
         ["geopolitics", "AI drone warfare", "deglobalization"], "geopolitics"),
        # "New World Order" is stock cults/politics_power phrasing. geopolitics is ordered
        # ahead of politics_power, so a "world order" keyword there would hijack it.
        ("Christian Dominionism and the New World Order",
         ["dominionism", "religion"], "politics_power"),
        # Chinese-model AI videos must not be captured by a geopolitics "china" keyword.
        ("China's Free AI Just Embarrassed Claude", ["ai", "llm"], "ai_automation"),
        # self_improvement stays ahead of ai_automation (the Seth Godin regression).
        ("The Quitting Expert: Quit Now Before AI Makes The Choice For You",
         ["self-help", "quitting"], "self_improvement"),
        ("Claude Code Task System: ANTI-HYPE Agentic Coding", ["agentic", "ai"],
         "agentic_workflows"),
        ("Day Trading Taxes Step By Step Guide", ["taxes"], "miscellaneous"),
    ],
)
def test_get_category_routes_expected(title, tags, expected):
    assert librarian.get_category(title, tags)["id"] == expected


@pytest.mark.parametrize("title", ["What does this script do?", "What doesn't this script do?"])
def test_get_category_doe_does_not_match_inside_words(title):
    assert librarian.get_category(title, [])["id"] == "miscellaneous"


def test_get_category_matches_standalone_doe_keyword():
    assert librarian.get_category("DOE", [])["id"] == "agentic_workflows"


@pytest.mark.parametrize(
    "unsafe",
    ["war", "nato", "china", "world order", "cult", "ai"],
)
def test_geopolitics_avoids_known_colliding_keywords(unsafe):
    """These broad keywords collide with unrelated words or other genres' stock phrases.

    "war" is in software/warrior/warehouse, "nato" is in seNATOr, "china" and "ai" belong
    to AI-industry videos, "world order" to conspiracy content, "cult" to difficult/culture.
    """
    cfg = yaml.safe_load(Path("config/categories.yaml").read_text(encoding="utf-8"))
    geo = next(c for c in cfg["categories"] if c["id"] == "geopolitics")
    assert unsafe not in geo["keywords"]


def test_update_index_falls_back_for_unknown_category(tmp_path, monkeypatch, caplog):
    """Unknown legacy IDs stay in YAML/Markdown under the configured default."""
    library_root = tmp_path / "library"
    library_root.mkdir()
    config_root = tmp_path / "config"
    config_root.mkdir()
    (config_root / "categories.yaml").write_text(
        "categories:\n"
        "  - id: supported\n"
        "    name: 'Supported'\n"
        "default_category:\n"
        "  id: fallback\n"
        "  name: 'Fallback'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(librarian, "LIBRARY_DIR", library_root)
    monkeypatch.chdir(tmp_path)

    index = {
        "entries": [
            {"title": "Legacy entry", "channel": "Old", "date": "2026-01-01",
             "url": "https://example.test/legacy", "category_id": "retired"},
            {"title": "Supported entry", "channel": "New", "date": "2026-01-02",
             "url": "https://example.test/supported", "category_id": "supported"},
        ]
    }
    (library_root / "index.yaml").write_text(yaml.safe_dump(index), encoding="utf-8")

    with caplog.at_level("WARNING"):
        librarian.update_index({
            "title": "New entry",
            "channel": "New",
            "date": "2026-01-03",
            "url": "https://example.test/new",
            "category_id": "new-retired",
            "filepath": "library/new.md",
        })

    rendered_index = yaml.safe_load((library_root / "index.yaml").read_text(encoding="utf-8"))
    entries = rendered_index["entries"]
    assert len(entries) == 3
    assert {entry["title"] for entry in entries} == {"Legacy entry", "Supported entry", "New entry"}
    assert next(entry for entry in entries if entry["title"] == "Legacy entry")["category_id"] == "fallback"
    assert next(entry for entry in entries if entry["title"] == "New entry")["category_id"] == "fallback"
    markdown = (library_root / "00_Index_Library.md").read_text(encoding="utf-8")
    assert "Legacy entry" in markdown
    assert "Supported entry" in markdown
    assert "New entry" in markdown
    assert "unknown category_id 'retired'" in caplog.text
    backup = yaml.safe_load((library_root / "index.yaml.bak").read_text(encoding="utf-8"))
    assert backup["entries"][0]["category_id"] == "retired"


def test_update_index_leaves_index_unchanged_when_categories_config_is_missing(
    tmp_path, monkeypatch, caplog
):
    library_root = tmp_path / "library"
    library_root.mkdir()
    monkeypatch.setattr(librarian, "LIBRARY_DIR", library_root)
    monkeypatch.chdir(tmp_path)

    index_path = library_root / "index.yaml"
    original = {
        "entries": [
            {
                "title": "Existing entry",
                "url": "https://example.test/existing",
                "category_id": "supported",
            }
        ]
    }
    original_yaml = yaml.safe_dump(original)
    index_path.write_text(original_yaml, encoding="utf-8")

    with caplog.at_level("ERROR"):
        assert librarian.update_index(
            {
                "title": "New entry",
                "url": "https://example.test/new",
                "category_id": "retired",
            }
        ) is False

    assert index_path.read_text(encoding="utf-8") == original_yaml
    assert not (library_root / "00_Index_Library.md").exists()
    assert "category configuration" in caplog.text


@patch("scripts.librarian.get_video_data")
@patch("scripts.librarian.save_to_library")
def test_process_single_video_fails_before_writes_when_categories_config_is_missing(
    mock_save, mock_get, tmp_path, monkeypatch, caplog
):
    monkeypatch.chdir(tmp_path)
    analysis_path = tmp_path / "analysis.md"
    analysis_path.write_text("analysis", encoding="utf-8")
    mock_get.return_value = dict(VIDEO_STUB)
    mock_save.return_value = tmp_path / "report.md"
    args = MagicMock(
        analysis_file=str(analysis_path), no_whisper=True, subdir=None, dry_run=False
    )

    with caplog.at_level("ERROR"):
        assert librarian.process_single_video("https://youtu.be/abc", args) is False

    mock_save.assert_not_called()
    assert "category configuration" in caplog.text


def test_batch_mode_exits_nonzero_when_a_video_fails(tmp_path, monkeypatch):
    library_root = tmp_path / "library"
    library_root.mkdir()
    monkeypatch.setattr(librarian, "LIBRARY_DIR", library_root)
    monkeypatch.setattr(librarian, "initialize_directories", lambda: None)
    monkeypatch.setattr(librarian, "get_profile_video_urls", lambda *_args, **_kwargs: ["url"])
    monkeypatch.setattr(librarian, "process_single_video", lambda *_args: False)
    monkeypatch.setattr(librarian.time, "sleep", lambda *_args: None)
    monkeypatch.setattr("sys.argv", ["librarian.py", "--batch-profile", "profile", "--delay", "0"])

    with pytest.raises(SystemExit) as exc_info:
        librarian.main()

    assert exc_info.value.code == 1


# --- fact-check protocol reminder ---------------------------------------------------
# Reports land in library/, which is gitignored, so no PR or CI check ever sees them.
# This warning is the pipeline's only enforcement point — hence tests that it actually fires.

def test_fact_check_reminder_emits_core_rules(caplog):
    with caplog.at_level("WARNING"):
        librarian.emit_fact_check_protocol_reminder()
    out = caplog.text
    assert "FACT_CHECK_PROTOCOL.md" in out
    # The three rules that caused real overturns must be in the reminder itself, not
    # only in the file — an agent that never opens the file still has to see them.
    assert "No grade from memory" in out
    assert "primary source" in out
    assert "speaker's framing" in out


def test_fact_check_reminder_flags_missing_protocol_file(caplog, tmp_path, monkeypatch):
    """If the protocol file goes missing, say so loudly rather than pointing at nothing."""
    monkeypatch.setattr(librarian, "FACT_CHECK_PROTOCOL_PATH", tmp_path / "gone.md")
    with caplog.at_level("WARNING"):
        librarian.emit_fact_check_protocol_reminder()
    assert "NOT FOUND" in caplog.text


def test_fact_check_reminder_path_is_cwd_independent(caplog, tmp_path, monkeypatch):
    """A gate that cries NOT FOUND when run from another directory is worse than no gate.

    FACT_CHECK_PROTOCOL_PATH is anchored to __file__, so changing CWD must not affect it.
    """
    monkeypatch.chdir(tmp_path)
    with caplog.at_level("WARNING"):
        librarian.emit_fact_check_protocol_reminder()
    assert "NOT FOUND" not in caplog.text


def test_protocol_file_exists_at_repo_root():
    """The reminder points at this path; a rename must break a test, not just the docs."""
    assert librarian.FACT_CHECK_PROTOCOL_PATH.is_file()


@patch("scripts.librarian.extract_research_targets", return_value={})
@patch("scripts.librarian.check_flagged_channel", return_value=None)
@patch("scripts.librarian.get_video_data")
@patch("scripts.librarian.emit_fact_check_protocol_reminder")
def test_reminder_is_wired_into_fetch_path(mock_reminder, mock_get, _flag, _targets, capsys):
    """Covers the WIRING, not just the function.

    The isolated tests above would still pass if a refactor dropped the call from
    process_single_video() — this asserts it actually fires on the fetch that precedes
    grading, and before the JSON the analyst reads.
    """
    mock_get.return_value = dict(VIDEO_STUB)
    args = MagicMock(analysis_file=None, no_whisper=True, subdir=None, dry_run=False)
    librarian.process_single_video("https://youtu.be/abc", args)
    assert mock_reminder.called, "fact-check reminder is no longer called on the fetch path"


# --- Rule 0: sources bound per claim row --------------------------------------------
# The 2026-08-14 report had 40+ source links in a bulk list and 0 of 49 claim rows bound
# to any of them. An unsourced grade and a sourced grade look identical without this.

SOURCED_TABLE = """## Claim table

| # | Claim | Grade | Source | Note |
|---|---|---|---|---|
| 1 | 80% of energy imported | Wrong | [SASAC](http://en.sasac.gov.cn/x) | Actually ~15% |
| 2 | Gulf share is 80% | Wrong | [CGEP](https://energypolicy.columbia.edu/y) | ~42% |
"""

UNSOURCED_TABLE = """## Claim table

| # | Claim | Grade | Note |
|---|---|---|---|
| 1 | 80% of energy imported | Wrong | Actually ~15% |
| 2 | Gulf share is 80% | Wrong | ~42% |
| 3 | Japan aging claim | Wrong | No |

## Sources
- [SASAC](http://en.sasac.gov.cn/x)
- [CGEP](https://energypolicy.columbia.edu/y)
"""


def test_audit_returns_none_when_there_is_no_claim_table():
    """Tutorial extractions have no claims to source — they must never be nagged."""
    assert librarian.audit_claim_sources("# Workflow\n\n1. Open the app\n2. Click render") is None


def test_audit_counts_fully_sourced_table():
    stats = librarian.audit_claim_sources(SOURCED_TABLE)
    assert stats == {"total": 2, "unsourced": 0, "documented": 0, "ratio": 0.0}


def test_bulk_source_list_does_not_satisfy_rule_zero():
    """The exact 2026-08-14 failure: links present in the report, none bound to a claim."""
    stats = librarian.audit_claim_sources(UNSOURCED_TABLE)
    assert stats["total"] == 3
    assert stats["unsourced"] == 3, "a bottom-of-report Sources list must not count as binding"
    assert stats["ratio"] > librarian.UNSOURCED_CLAIM_CEILING


# Every claim-bearing table header found in the 128-report library on 2026-08-14.
# library/ is gitignored, so a real full-corpus dry run can never be a committed test —
# this catalog is the durable stand-in. Two detector versions shipped and were sent back
# because they were validated by spot check against a subset of these shapes.
# Regenerate with: grep table headers containing "claim" across library/**/*.md
REAL_CLAIM_HEADERS = [
    "# | Claim | Grade | Note",
    "Claim | Grade | Detail",
    "# | Claim | Verdict",
    "Claim in video | Verified? | Detail from sources",
    "Claim | Reality",
    "Claim | Researchers | Verdict | What the critic / split caught",
    "Claim | Researchers | Verdict | vs. Pass 1 | Why",
    "# | Claim | Where",
    "# | Claim | Verdict | Evidence",
    "Claim | Grade | Source",
    "# | Claim | Grade | Source / Note",
    "# | Beat | Claim",
    "# | Claim | Verdict | Detail",
    "Group | Hassan's claim | Holds up?",
    "Claim | Grade",
    "# | Who | Claim | Grade | Note",
]


@pytest.mark.parametrize("header", REAL_CLAIM_HEADERS)
def test_every_real_library_header_shape_is_detected(header):
    """An allowlist of verdict words missed 'Verified?' and 'Holds up?' in production.

    Detection matches on 'claim' alone precisely so this parametrize can't rot.
    """
    ncols = len(header.split("|"))
    table = (f"| {header} |\n|" + "---|" * ncols + "\n"
             + "| " + " | ".join(["x"] * ncols) + " |\n")
    stats = librarian.audit_claim_sources(table)
    assert stats is not None, f"claim table not detected: {header}"
    assert stats["total"] == 1


def test_unverified_row_with_search_trail_is_not_counted_unsourced():
    """The protocol REQUIRES an Unverified row to record what was searched, with no link.

    Counting that as unsourced would penalise a report for complying, and a warning that
    fires on compliant work is a warning people learn to ignore.
    """
    table = ("| # | Claim | Grade | Source |\n|---|---|---|---|\n"
             "| 1 | x | Unverified | searched EIA, IEA, SEC filings; nothing primary |\n")
    stats = librarian.audit_claim_sources(table)
    assert stats["unsourced"] == 0, "a documented search trail is Unverified, not Unchecked"
    assert stats["documented"] == 1
    assert stats["ratio"] == 0.0


@pytest.mark.parametrize("grade,waived", [
    ("Unverified", True),
    ("❓ Unverified", True),
    ("**🟡 Unverified**", True),
    # Composite grades assert something about the claim, so they still need a link.
    ("Confirmed, timing unverified", False),
    ("🟡 Number confirmed, timing unverified", False),
    ("Wrong; the rest is unverified", False),
    ("Confirmed", False),
    ("Unverified specifics", True),
    # Beat the old allowlist: "misleading" was never in it, so this used to be waived.
    ("Misleading, unverified", False),
    ("Debunked, timing unverified", False),
])
def test_only_a_pure_unverified_grade_waives_the_link(grade, waived):
    """Substring-matching the grade cell waived composite grades — real content in
    library/lance-breitstein/ row 12 hit exactly this."""
    table = ("| # | Claim | Grade | Source |\n|---|---|---|---|\n"
             f"| 1 | x | {grade} | searched A, B; nothing primary |\n")
    stats = librarian.audit_claim_sources(table)
    assert stats["documented"] == (1 if waived else 0)
    assert stats["unsourced"] == (0 if waived else 1)


def test_unverified_grade_with_empty_source_is_still_unchecked():
    """Unverified earns a waiver for the LINK, never for the cell being empty."""
    table = ("| # | Claim | Grade | Source |\n|---|---|---|---|\n"
             "| 1 | x | Unverified | |\n")
    assert librarian.audit_claim_sources(table)["unsourced"] == 1


def test_unverified_in_claim_text_does_not_waive_the_link():
    """The word must be in the grade cell, not anywhere in the row."""
    table = ("| # | Claim | Grade | Source |\n|---|---|---|---|\n"
             "| 1 | he called it unverified | Wrong | some prose |\n")
    assert librarian.audit_claim_sources(table)["unsourced"] == 1


def test_prose_note_column_does_not_launder_an_uncited_table():
    """The narrow half of the rule above.

    Only an Unverified grade earns a link-free Source cell. Accepting any prose would let
    a Detail/Note column absolve a wholly uncited table — the 2026-08-14 pattern exactly.
    """
    table = ("| Claim in video | Verified? | Detail from sources |\n|---|---|---|\n"
             "| China's AI is free | Yes | It is open-weight and widely mirrored |\n"
             "| It beats Claude | No | Benchmarks are cherry-picked |\n")
    stats = librarian.audit_claim_sources(table)
    assert stats["unsourced"] == 2, "prose in a source-ish column must not count as a citation"
    assert stats["documented"] == 0


def test_unclosed_fence_does_not_disable_auditing_for_the_rest_of_the_document():
    """An unbalanced fence must not silently switch Rule 0 off.

    Latching the skip flag on would return None — indistinguishable from 'no claims here',
    which is the exact silent-miss class this whole feature exists to remove.
    """
    text = ("```\nthis fence is never closed\n\n"
            "| # | Claim | Grade | Source |\n|---|---|---|---|\n"
            "| 1 | a real claim | Wrong | |\n")
    stats = librarian.audit_claim_sources(text)
    assert stats is not None, "unclosed fence silently disabled the audit"
    assert stats["unsourced"] == 1


def test_null_byte_in_source_text_is_not_rewritten():
    """An earlier version swapped \\x00 as an escaping placeholder and corrupted real ones."""
    cells = librarian._split_row("| a\x00b | c |")
    assert cells[0] == "a\x00b"


def test_claim_table_inside_code_fence_is_ignored():
    """FACT_CHECK_PROTOCOL.md shows an example table; docs must not be audited as reports."""
    text = ("Example of the required shape:\n\n```markdown\n"
            "| # | Claim | Grade | Source |\n|---|---|---|---|\n"
            "| 1 | example | Wrong | |\n```\n")
    assert librarian.audit_claim_sources(text) is None


def test_escaped_pipe_does_not_shift_the_source_column():
    """A \\| inside claim text must not misalign columns and fake an unsourced row."""
    table = ("| # | Claim | Grade | Source |\n|---|---|---|---|\n"
             "| 1 | he said a \\| b | Wrong | [src](http://a.example) |\n")
    assert librarian.audit_claim_sources(table)["unsourced"] == 0


def test_ragged_row_shorter_than_header_counts_as_unsourced():
    """A row missing its Source cell is unsourced, not silently skipped."""
    table = ("| # | Claim | Grade | Source |\n|---|---|---|---|\n| 1 | x | Wrong |\n")
    assert librarian.audit_claim_sources(table)["unsourced"] == 1


def test_audit_detects_claim_table_without_numeric_id_column():
    """The regression that FAILed review: 3 real reports number differently, 2 of them
    100% unsourced. Keying off a leading digit skipped exactly the worst cases."""
    table = ("| Claim | Reality |\n|---|---|\n"
             "| China makes unlimited fuel | No such thing |\n"
             "| It runs on seawater | Also no |\n")
    stats = librarian.audit_claim_sources(table)
    assert stats is not None, "a claim table without an ID column must still be detected"
    assert stats == {"total": 2, "unsourced": 2, "documented": 0, "ratio": 1.0}


def test_audit_accepts_bare_url_as_a_source():
    """A bare URL in the Source cell is a citation; dropping this branch must fail a test."""
    table = ("| # | Claim | Grade | Source |\n|---|---|---|---|\n"
             "| 1 | x | Wrong | https://eia.gov/report |\n")
    assert librarian.audit_claim_sources(table)["unsourced"] == 0


def test_url_in_claim_text_does_not_launder_an_uncited_row():
    """Only the Source cell counts — a URL quoted in the claim can't stand in for a citation."""
    table = ("| # | Claim | Grade | Source |\n|---|---|---|---|\n"
             "| 1 | He cited https://example.com/paper | Wrong | |\n")
    assert librarian.audit_claim_sources(table)["unsourced"] == 1


def test_non_claim_tables_are_ignored():
    """Forecast scoreboards and chapter tables must not be audited as claims."""
    text = ("| # | Who | Prediction | Due | Status |\n|---|---|---|---|---|\n"
            "| F1 | Zeihan | oil hits minimums | 2026 | Open |\n\n"
            "| Timestamp | Section |\n|---|---|\n| 00:00 | Intro |\n")
    assert librarian.audit_claim_sources(text) is None


def test_ceiling_matches_protocol_doc():
    """The comment claims doc and code can't drift; this is what actually prevents it."""
    doc = Path("FACT_CHECK_PROTOCOL.md").read_text(encoding="utf-8")
    pct = f"{librarian.UNSOURCED_CLAIM_CEILING:.0%}"
    assert pct in doc, f"protocol doc does not mention the {pct} ceiling defined in code"


def test_audit_counts_suffixed_claim_ids():
    """Rows numbered 25a/25b are real — the Stratfor report used them."""
    table = ("| # | Claim | Grade | Source |\n|---|---|---|---|\n"
             "| 25a | x | Wrong | [s](http://a.example) |\n"
             "| 25b | y | Wrong | |\n")
    stats = librarian.audit_claim_sources(table)
    assert stats["total"] == 2 and stats["unsourced"] == 1


def test_audit_ignores_urls_in_surrounding_prose():
    """A link in prose around the table must not launder an unsourced row."""
    text = ("See https://example.com for background.\n\n"
            "| # | Claim | Grade | Source |\n|---|---|---|---|\n"
            "| 1 | claim | Wrong | |\n\n"
            "More context at https://example.org/other\n")
    stats = librarian.audit_claim_sources(text)
    assert stats == {"total": 1, "unsourced": 1, "documented": 0, "ratio": 1.0}


def test_source_audit_warns_and_flags_ceiling(caplog):
    with caplog.at_level("WARNING"):
        librarian.emit_claim_source_audit({"total": 3, "unsourced": 3, "ratio": 1.0})
    assert "NOT publishable as a fact-check" in caplog.text
    assert "Rule 0" in caplog.text


def test_source_audit_stays_quiet_when_fully_sourced(caplog):
    with caplog.at_level("WARNING"):
        librarian.emit_claim_source_audit({"total": 4, "unsourced": 0, "ratio": 0.0})
    assert caplog.text == ""


def test_source_audit_below_ceiling_warns_without_publishability_verdict(caplog):
    """One unsourced row out of twenty is worth flagging, not worth condemning."""
    with caplog.at_level("WARNING"):
        librarian.emit_claim_source_audit({"total": 20, "unsourced": 1, "ratio": 0.05})
    assert "1 of 20" in caplog.text
    assert "NOT publishable" not in caplog.text
