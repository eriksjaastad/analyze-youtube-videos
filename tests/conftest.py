import pytest

from scripts import librarian


@pytest.fixture(autouse=True)
def _isolate_fetch_cache(tmp_path, monkeypatch):
    """Fetch mode writes data/fetch_cache; keep every test out of the real one."""
    monkeypatch.setattr(librarian, "FETCH_CACHE_DIR", tmp_path / "fetch_cache")
