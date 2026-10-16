"""429 fail-fast and save-without-network coverage for the librarian.

Every test mocks subprocess.run; none of them touch the network or invoke a
real yt-dlp binary.
"""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scripts import librarian


def _completed(returncode, stdout="", stderr=""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


# --- is_rate_limited ---------------------------------------------------------

@pytest.mark.parametrize("stderr", [
    "ERROR: HTTP Error 429: Too Many Requests",
    "http error 429",
    "Too Many Requests",
    "too many requests",
])
def test_is_rate_limited_detects_429_phrases(stderr):
    assert librarian.is_rate_limited(stderr) is True


@pytest.mark.parametrize("stderr", ["", "some other failure", "HTTP Error 500"])
def test_is_rate_limited_rejects_other_stderr(stderr):
    assert librarian.is_rate_limited(stderr) is False


# --- _yt_dlp ------------------------------------------------------------------

@patch("subprocess.run")
def test_yt_dlp_fails_fast_on_429(mock_run):
    mock_run.return_value = _completed(1, stderr="ERROR: HTTP Error 429: Too Many Requests")

    with pytest.raises(librarian.RateLimitedError):
        librarian._yt_dlp(["--dump-json", "u"], timeout=60)

    assert mock_run.call_count == 1


@patch("subprocess.run")
def test_yt_dlp_runs_a_failed_call_once(mock_run):
    mock_run.return_value = _completed(1, stderr="generic failure")

    with pytest.raises(librarian.YtDlpError, match="generic failure"):
        librarian._yt_dlp(["--dump-json", "u"], timeout=60)

    assert mock_run.call_count == 1


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("yt-dlp", 60), FileNotFoundError("yt-dlp")])
def test_yt_dlp_that_cannot_complete_is_a_yt_dlp_error(error):
    with patch("subprocess.run", side_effect=error), pytest.raises(librarian.YtDlpError):
        librarian._yt_dlp(["--dump-json", "u"], timeout=60)


# --- download_audio rate limiting ---------------------------------------------

@patch("subprocess.run")
def test_download_audio_raises_rate_limited_error_on_429_stderr(mock_run):
    mock_run.return_value = _completed(1, stderr="ERROR: HTTP Error 429: Too Many Requests")

    with pytest.raises(librarian.RateLimitedError):
        librarian.download_audio("https://youtu.be/v", Path("/tmp/fake"))


# --- get_video_data rate limiting --------------------------------------------

AUTO_ONLY = {"title": "T", "uploader": "C", "id": "v", "automatic_captions": {"en-orig": []}}
RATE_LIMITED = "ERROR: HTTP Error 429: Too Many Requests"


def test_get_video_data_raises_on_metadata_429(fake_ytdlp):
    fake_ytdlp(AUTO_ONLY, fail={"--dump-json": RATE_LIMITED})

    with pytest.raises(librarian.RateLimitedError):
        librarian.get_video_data("https://youtube.com/watch?v=fail")


def test_get_video_data_raises_on_subtitle_429_and_never_downloads_audio(fake_ytdlp):
    calls = fake_ytdlp(AUTO_ONLY, fail={"--sub-lang": RATE_LIMITED})

    with pytest.raises(librarian.RateLimitedError):
        librarian.get_video_data("https://youtube.com/watch?v=v")

    assert not any("--extract-audio" in cmd for cmd in calls)


@patch("scripts.librarian.transcribe_with_whisper")
def test_get_video_data_whisper_fallback_audio_429_propagates(mock_transcribe, fake_ytdlp):
    # The subtitle call succeeds but writes no file, so the fetch falls back to audio.
    calls = fake_ytdlp(AUTO_ONLY, tracks={}, fail={"--extract-audio": RATE_LIMITED})

    with pytest.raises(librarian.RateLimitedError):
        librarian.get_video_data("https://youtube.com/watch?v=v")

    assert "--extract-audio" in calls[-1]
    mock_transcribe.assert_not_called()


def test_metadata_only_makes_one_call_and_returns_empty_transcript(fake_ytdlp):
    calls = fake_ytdlp({"title": "T", "uploader": "C", "id": "v", "view_count": 5})

    data = librarian.get_video_data("https://youtube.com/watch?v=v", metadata_only=True)

    assert len(calls) == 1
    assert data["transcript"] == ""
    assert data["title"] == "T"
    assert data["video_id"] == "v"


# --- save mode without network -----------------------------------------------

SAVE_DATA = {
    "title": "Test Video",
    "channel": "Test Channel",
    "url": "https://youtu.be/abc123",
    "video_id": "abc123",
}


@pytest.fixture
def save_env(tmp_path, monkeypatch):
    """Isolated library + config, CWD moved so save_to_library/add_to_index work."""
    library_root = tmp_path / "library"
    library_root.mkdir()
    monkeypatch.setattr(librarian, "LIBRARY_DIR", library_root)

    config_root = tmp_path / "config"
    config_root.mkdir()
    (config_root / "replacements.yaml").write_text("replacements: []\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    analysis = tmp_path / "analysis.md"
    analysis.write_text("# Analysis\n\nbody\n", encoding="utf-8")

    return SimpleNamespace(library_root=library_root, analysis=analysis, tmp_path=tmp_path)


def _save_args(analysis, data_file=None):
    return MagicMock(
        analysis_file=str(analysis),
        data_file=data_file,
        no_whisper=True,
        subdir=None,
        dry_run=False,
    )


@patch("scripts.librarian.check_flagged_channel", return_value=None)
@patch("scripts.librarian.get_video_data")
def test_save_with_data_file_makes_zero_get_video_data_calls_and_writes_report(
    mock_get, mock_flag, save_env
):
    data_path = save_env.tmp_path / "fetch.json"
    data_path.write_text(json.dumps(SAVE_DATA), encoding="utf-8")

    assert librarian.process_single_video(SAVE_DATA["url"], _save_args(save_env.analysis, data_file=str(data_path))) is True

    mock_get.assert_not_called()
    mock_flag.assert_called_once()
    reports = list(save_env.library_root.glob("*.md"))
    assert len(reports) == 1
    assert "body" in reports[0].read_text(encoding="utf-8")


@patch("scripts.librarian.get_video_data")
def test_save_with_data_file_url_mismatch_returns_false_and_writes_nothing(mock_get, save_env):
    data_path = save_env.tmp_path / "fetch.json"
    data_path.write_text(json.dumps({**SAVE_DATA, "url": "https://youtu.be/other"}), encoding="utf-8")

    assert librarian.process_single_video(SAVE_DATA["url"], _save_args(save_env.analysis, data_file=str(data_path))) is False

    mock_get.assert_not_called()
    assert not list(save_env.library_root.glob("*.md"))
    assert not (save_env.library_root / "index.yaml").exists()


@patch("scripts.librarian.get_video_data")
def test_save_with_data_file_missing_required_key_returns_false(mock_get, save_env):
    data_path = save_env.tmp_path / "fetch.json"
    data_path.write_text(json.dumps({k: v for k, v in SAVE_DATA.items() if k != "video_id"}), encoding="utf-8")

    assert librarian.process_single_video(SAVE_DATA["url"], _save_args(save_env.analysis, data_file=str(data_path))) is False

    mock_get.assert_not_called()
    assert not (save_env.library_root / "index.yaml").exists()


@patch("scripts.librarian.check_flagged_channel", return_value=None)
@patch("scripts.librarian.get_video_data")
def test_save_with_matching_cache_file_makes_zero_get_video_data_calls(
    mock_get, mock_flag, save_env, monkeypatch
):
    cache_dir = save_env.tmp_path / "fetch_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(librarian, "FETCH_CACHE_DIR", cache_dir)
    (cache_dir / "youtube-abc123.json").write_text(json.dumps(SAVE_DATA), encoding="utf-8")

    assert librarian.process_single_video(SAVE_DATA["url"], _save_args(save_env.analysis)) is True

    mock_get.assert_not_called()
    mock_flag.assert_called_once()
    assert list(save_env.library_root.glob("*.md"))


@patch("scripts.librarian.check_flagged_channel", return_value=None)
@patch("scripts.librarian.get_video_data")
def test_save_without_cache_falls_back_to_metadata_only_get_video_data(
    mock_get, mock_flag, save_env, monkeypatch
):
    monkeypatch.setattr(librarian, "FETCH_CACHE_DIR", save_env.tmp_path / "empty_cache")
    mock_get.return_value = dict(SAVE_DATA)

    assert librarian.process_single_video(SAVE_DATA["url"], _save_args(save_env.analysis)) is True

    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs.get("metadata_only") is True
    mock_flag.assert_called_once()


@pytest.mark.parametrize("broken", ["entries: [unclosed\n", "", "null\n", "[]\n", "entries: oops\n", "entries:\n- 5\n"])
@patch("scripts.librarian.check_flagged_channel", return_value=None)
def test_broken_index_fails_the_save_before_any_report_is_written(mock_flag, broken, save_env):
    index = save_env.library_root / "index.yaml"
    index.write_text(broken, encoding="utf-8")
    data_path = save_env.tmp_path / "fetch.json"
    data_path.write_text(json.dumps(SAVE_DATA), encoding="utf-8")

    with pytest.raises((librarian.yaml.YAMLError, ValueError)):
        librarian.process_single_video(SAVE_DATA["url"], _save_args(save_env.analysis, data_file=str(data_path)))

    assert index.read_text(encoding="utf-8") == broken
    assert not list(save_env.library_root.glob("*.md"))


# --- fetch cache write -------------------------------------------------------

@patch("scripts.librarian.check_flagged_channel", return_value=None)
@patch("scripts.librarian.extract_research_targets", return_value={})
@patch("scripts.librarian.emit_fact_check_protocol_reminder")
@patch("scripts.librarian.get_video_data")
def test_fetch_mode_writes_printed_json_to_cache(
    mock_get, mock_reminder, mock_targets, mock_flag, tmp_path, monkeypatch, capsys
):
    cache_dir = tmp_path / "fetch_cache"
    monkeypatch.setattr(librarian, "FETCH_CACHE_DIR", cache_dir)
    data = {
        **SAVE_DATA,
        "platform": "youtube",
        "video_id": "abc123",
        "date": "20260926",
        "description": "",
        "transcript": "hello",
        "tags": [],
        "view_count": 10,
        "like_count": 2,
        "duration_string": "1:23",
        "chapters": [],
        "channel_id": "",
        "uploader_id": "",
    }
    mock_get.return_value = dict(data)
    args = MagicMock(analysis_file=None, data_file=None, no_whisper=True, subdir=None, dry_run=False)

    assert librarian.process_single_video("https://youtu.be/abc123", args) is True

    printed = capsys.readouterr().out
    cache_path = cache_dir / "youtube-abc123.json"
    assert cache_path.exists()
    assert json.loads(cache_path.read_text(encoding="utf-8")) == json.loads(printed)
    assert json.loads(printed)["url"] == "https://youtu.be/abc123"


# --- CLI -------------------------------------------------------------

def test_main_single_video_rate_limited_exits_1(monkeypatch):
    monkeypatch.setattr(librarian, "initialize_directories", lambda: None)
    process = MagicMock(side_effect=librarian.RateLimitedError("HTTP Error 429"))
    monkeypatch.setattr(librarian, "process_single_video", process)
    monkeypatch.setattr("sys.argv", ["librarian.py", "https://youtu.be/abc"])

    with pytest.raises(SystemExit) as exc_info:
        librarian.main()

    assert exc_info.value.code == 1
    assert process.call_count == 1


# --- broken flagged-channel watchlist ----------------------------------------

def _broken_watchlist(tmp_path, monkeypatch):
    cfg = tmp_path / "flagged_channels.yaml"
    cfg.write_text("channels: [unclosed\n  - oops:", encoding="utf-8")
    monkeypatch.setattr(librarian, "FLAGGED_CHANNELS_PATH", cfg)


@patch("scripts.librarian.get_video_data")
def test_save_with_broken_watchlist_raises_before_writing_anything(
    mock_get, save_env, monkeypatch
):
    _broken_watchlist(save_env.tmp_path, monkeypatch)
    data_path = save_env.tmp_path / "fetch.json"
    data_path.write_text(json.dumps(SAVE_DATA), encoding="utf-8")

    with pytest.raises(librarian.FlaggedChannelsConfigError):
        librarian.process_single_video(
            SAVE_DATA["url"], _save_args(save_env.analysis, data_file=str(data_path))
        )

    assert not list(save_env.library_root.glob("*.md"))
    assert not (save_env.library_root / "index.yaml").exists()


def test_main_single_video_broken_watchlist_exits_1(monkeypatch, caplog):
    monkeypatch.setattr(librarian, "initialize_directories", lambda: None)
    process = MagicMock(side_effect=librarian.FlaggedChannelsConfigError("watchlist broken"))
    monkeypatch.setattr(librarian, "process_single_video", process)
    monkeypatch.setattr("sys.argv", ["librarian.py", "https://youtu.be/abc"])

    with pytest.raises(SystemExit) as exc_info:
        librarian.main()

    assert exc_info.value.code == 1
    assert "watchlist broken" in caplog.text


def test_data_file_requires_analysis_file(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["librarian.py", "https://youtu.be/abc", "--data-file", "fetch.json"],
    )

    with pytest.raises(SystemExit) as exc_info:
        librarian.main()

    assert exc_info.value.code == 2
