"""CLI boundary coverage: invalid URLs must never reach extraction or writes."""

from unittest.mock import MagicMock

import pytest

from scripts import librarian


@pytest.fixture
def cli(tmp_path, monkeypatch):
    process = MagicMock(return_value=True)
    monkeypatch.setattr(librarian, "LIBRARY_DIR", tmp_path / "library")
    monkeypatch.setattr(librarian, "process_single_video", process)

    def run(*args):
        monkeypatch.setattr("sys.argv", ["librarian.py", *args])
        librarian.main()

    return run, process


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
def test_cli_rejects_invalid_urls_before_any_work(cli, url):
    run, process = cli
    with pytest.raises(SystemExit) as error:
        run(url)
    assert error.value.code == 2
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
    run, process = cli
    run(url)
    assert process.call_count == 1
    assert process.call_args.args[0] == url

