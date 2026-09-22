"""CLI boundary coverage: invalid URLs must never reach extraction or writes."""

from unittest.mock import MagicMock

import pytest

from scripts import librarian


@pytest.fixture
def cli(tmp_path, monkeypatch):
    initialize = MagicMock()
    profile = MagicMock(return_value=["https://youtu.be/abc"])
    process = MagicMock(return_value=True)
    monkeypatch.setattr(librarian, "LIBRARY_DIR", tmp_path / "library")
    monkeypatch.setattr(librarian, "initialize_directories", initialize)
    monkeypatch.setattr(librarian, "get_profile_video_urls", profile)
    monkeypatch.setattr(librarian, "process_single_video", process)
    monkeypatch.setattr(librarian.time, "sleep", MagicMock())

    def run(*args):
        monkeypatch.setattr("sys.argv", ["librarian.py", *args])
        librarian.main()

    return run, initialize, profile, process


@pytest.mark.parametrize("batch", [False, True])
@pytest.mark.parametrize("url", [
    "https://example.test/channel",
    "https://youtube.com.evil.test/@creator",
    "https://notinstagram.com/reel/abc",
    "https://instagram.com@evil.test/reel/abc",
    "https://evil.test@youtube.com/@creator",
    "https://tiktok.com:8443/@creator",
    "file:///tmp/videos",
    "ftp://youtube.com/@creator",
    "https://[broken/channel",
    "https://youtube.com/",
    "https://youtube.com/?next=/@creator",
    "https://youtube.com/@creator\n",
    "https://youtube.com/\t@creator",
    "https://youtube.com/@creator\x00",
    "https://youtube/@creator",
])
def test_cli_rejects_invalid_urls_before_any_work(cli, url, batch):
    run, initialize, profile, process = cli
    with pytest.raises(SystemExit) as error:
        run(*(["--batch-profile", url] if batch else [url]))
    assert error.value.code == 2
    initialize.assert_not_called()
    profile.assert_not_called()
    process.assert_not_called()


@pytest.mark.parametrize("url", [
    "https://youtube.com/watch?v=abc",
    "https://youtu.be/abc?si=sharing",
    "youtube.com/watch?v=abc",
    "youtube.com/watch?v=abc&next=https://example.test",
    "youtu.be/abc#https://example.test",
    "instagram.com/reel/abc/?next=https://example.test",
    "http://www.youtube.com/shorts/abc",
    "https://www.tiktok.com/@creator/video/123",
    "https://www.instagram.com/reel/abc/",
    "https://instagram.com/p/abc/?igsh=sharing",
    "https://instagram.com/creator/reel/abc/",
])
def test_single_cli_keeps_supported_video_urls(cli, url):
    run, initialize, profile, process = cli
    run(url)
    initialize.assert_called_once_with()
    profile.assert_not_called()
    assert process.call_count == 1
    assert process.call_args.args[0] == url


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/@creator/videos",
    "youtube.com/channel/UC123",
    "youtube.com/@creator?next=https://example.test",
    "tiktok.com/@creator#https://example.test",
    "https://www.tiktok.com/@creator",
])
def test_batch_cli_keeps_supported_profiles(cli, url):
    run, initialize, profile, process = cli
    run("--batch-profile", url, "--limit", "1", "--delay", "0")
    initialize.assert_called_once_with()
    profile.assert_called_once_with(url, limit=1)
    assert process.call_count == 1
    assert process.call_args.args[0] == "https://youtu.be/abc"


def test_instagram_batches_fail_with_actionable_message(cli, capsys):
    run, initialize, profile, process = cli
    with pytest.raises(SystemExit) as error:
        run("--batch-profile", "https://instagram.com/creator/")
    assert error.value.code == 2
    assert "use an individual post or reel URL" in capsys.readouterr().err
    initialize.assert_not_called()
    profile.assert_not_called()
    process.assert_not_called()


def test_batch_validates_extracted_urls_and_reports_partial_failure(cli, caplog):
    run, _, profile, process = cli
    profile.return_value = ["https://evil.test/video", "https://youtu.be/abc"]
    with pytest.raises(SystemExit) as error:
        run("--batch-profile", "https://youtube.com/@creator", "--delay", "0")
    assert error.value.code == 1
    assert process.call_count == 1
    assert process.call_args.args[0] == "https://youtu.be/abc"
    assert "Unsupported video URL returned by profile" in caplog.text
