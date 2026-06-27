import pytest
import subprocess
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from scripts.librarian import clean_srt, get_video_data, check_flagged_channel
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
    assert check_flagged_channel(data) is not None


def test_flagged_channel_matches_by_name_case_insensitive(flag_config):
    data = {"channel": "the diary of a ceo", "channel_id": "", "uploader_id": ""}
    assert check_flagged_channel(data) is not None


def test_unflagged_channel_returns_none(flag_config):
    data = {"channel": "Your AI Guy", "channel_id": "UCsomethingelse", "uploader_id": "@YourAIGuy"}
    assert check_flagged_channel(data) is None


def test_missing_config_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(librarian, "FLAGGED_CHANNELS_PATH", tmp_path / "nope.yaml")
    assert check_flagged_channel({"channel": "Anything", "channel_id": "UCx", "uploader_id": "@x"}) is None

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
