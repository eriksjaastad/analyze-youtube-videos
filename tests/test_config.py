import pytest
from scripts.config import choose_subtitle_track


# Manual English and en-orig are covered end to end in test_librarian.py.
@pytest.mark.parametrize("metadata,expected", [
    ({"subtitles": {"eng-US": []}}, ("eng-US", False)),  # TikTok's manual track
    ({"subtitles": {"fr": []}, "automatic_captions": {"fr": [], "en": []}}, ("en", True)),
    ({"subtitles": {"live_chat": []}, "automatic_captions": {"fr-orig": []}}, None),
    ({}, None),
])
def test_choose_subtitle_track(metadata, expected):
    assert choose_subtitle_track(metadata) == expected
