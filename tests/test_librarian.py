import pytest
import yaml
import subprocess
import os
import shutil
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
# get_category() does SUBSTRING matching over (title + tags) and returns on the FIRST
# matching category in config order. That makes short keywords dangerous: a keyword that
# happens to appear inside an unrelated phrase silently steals every video containing it.
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


@pytest.mark.parametrize(
    "unsafe",
    ["war", "nato", "china", "world order", "cult", "ai"],
)
def test_geopolitics_avoids_known_colliding_keywords(unsafe):
    """These substrings appear inside unrelated words or other genres' stock phrases.

    "war" is in software/warrior/warehouse, "nato" is in seNATOr, "china" and "ai" belong
    to AI-industry videos, "world order" to conspiracy content, "cult" to difficult/culture.
    """
    cfg = yaml.safe_load(Path("config/categories.yaml").read_text(encoding="utf-8"))
    geo = next(c for c in cfg["categories"] if c["id"] == "geopolitics")
    assert unsafe not in geo["keywords"]


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
    monkeypatch.chdir(tmp_path)
    with caplog.at_level("WARNING"):
        librarian.emit_fact_check_protocol_reminder()
    assert "NOT FOUND" in caplog.text


def test_protocol_file_exists_at_repo_root():
    """The reminder points at this path; a rename must break a test, not just the docs."""
    assert Path("FACT_CHECK_PROTOCOL.md").is_file()
