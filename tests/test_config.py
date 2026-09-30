import pytest
from scripts.config import select_subtitle, has_manual_english_subs

def test_select_subtitle_priority():
    base = "transcript"
    # Alphabetical order: transcript.en-US.srt comes BEFORE transcript.en.srt
    # Because '-' (45) < '.' (46)
    assert select_subtitle(["transcript.en-US.srt", "transcript.en.srt"], base) == "transcript.en-US.srt"
    
    # Auto en-US vs Auto en
    assert select_subtitle(["transcript.en-US.auto.srt", "transcript.en.auto.srt"], base) == "transcript.en-US.auto.srt"
    
    # Manual any vs Auto any
    assert select_subtitle(["transcript.fr.srt", "transcript.en.auto.srt"], base) == "transcript.fr.srt"

def test_select_subtitle_tiktok_vtt():
    """Verify TikTok VTT files with eng-US locale are found and prioritized."""
    base = "transcript"
    # TikTok VTT file
    assert select_subtitle(["transcript.eng-US.vtt"], base) == "transcript.eng-US.vtt"
    # Manual VTT preferred over auto SRT
    assert select_subtitle(["transcript.eng-US.vtt", "transcript.en.auto.srt"], base) == "transcript.eng-US.vtt"
    # VTT and SRT manual — alphabetical tiebreak
    assert select_subtitle(["transcript.en.srt", "transcript.eng-US.vtt"], base) == "transcript.en.srt"


def test_select_subtitle_prefer_original_picks_en_orig():
    files = ["transcript.en.srt", "transcript.en-orig.srt", "transcript.en-US.srt"]
    assert select_subtitle(files, "transcript", prefer_original=True) == "transcript.en-orig.srt"


def test_select_subtitle_prefer_original_falls_back_without_en_orig():
    files = ["transcript.en.srt", "transcript.fr-FR-orig.srt"]
    assert select_subtitle(files, "transcript", prefer_original=True) == "transcript.en.srt"


@pytest.mark.parametrize("subtitles,expected", [
    ({}, False),
    (None, False),
    ({"live_chat": []}, False),
    ({"fr": []}, False),
    ({"en": []}, True),
    ({"en-US": []}, True),
    ({"eng-US": []}, True),
])
def test_has_manual_english_subs(subtitles, expected):
    assert has_manual_english_subs({"subtitles": subtitles}) is expected
