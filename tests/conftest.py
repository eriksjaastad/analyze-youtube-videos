import json
import subprocess
from pathlib import Path

import pytest

from scripts import librarian


@pytest.fixture(autouse=True)
def _isolate_scratch_dirs(tmp_path, monkeypatch):
    """Fetch mode writes data/fetch_cache and yt-dlp scratch files; keep every test out of the real ones."""
    monkeypatch.setattr(librarian, "FETCH_CACHE_DIR", tmp_path / "fetch_cache")
    monkeypatch.setattr(librarian, "TEMP_DIR", tmp_path)


@pytest.fixture
def fake_ytdlp(monkeypatch):
    """Stand in for the yt-dlp binary; no test touches the network.

    Call it with the metadata --dump-json prints, the caption text per
    language a subtitle call writes, and optionally {flag: stderr} to make
    the call carrying that flag exit 1. Returns the list of commands run.
    """
    def install(metadata, tracks=None, fail=None):
        calls = []

        def run(cmd, **kwargs):
            calls.append(cmd)
            for flag, stderr in (fail or {}).items():
                if flag in cmd:
                    return subprocess.CompletedProcess(cmd, 1, "", stderr)
            if "--dump-json" in cmd:
                return subprocess.CompletedProcess(cmd, 0, json.dumps(metadata), "")
            if "--sub-lang" in cmd:
                lang = cmd[cmd.index("--sub-lang") + 1]
                if lang in (tracks or {}):
                    base = cmd[cmd.index("--output") + 1]
                    Path(f"{base}.{lang}.srt").write_text(
                        f"1\n00:00:01,000 --> 00:00:02,000\n{tracks[lang]}\n", encoding="utf-8"
                    )
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(subprocess, "run", run)
        return calls
    return install
