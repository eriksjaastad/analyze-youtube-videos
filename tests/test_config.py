import pytest
import hashlib
from scripts.config import validate_json_data, create_temp_dir_name, select_subtitle

def test_validate_json_data():
    # Valid dict
    data = {"SKILL_MD": "content", "RULE_MD": "content", "README_MD": "content"}
    is_valid, error = validate_json_data(data)
    assert is_valid is True
    assert error is None

    # Missing keys
    data = {"SKILL_MD": "content"}
    is_valid, error = validate_json_data(data)
    assert is_valid is False
    assert "Missing required keys" in error

    # None input
    is_valid, error = validate_json_data(None)
    assert is_valid is False
    assert "not a dictionary" in error

    # Non-dict input
    is_valid, error = validate_json_data("not a dict")
    assert is_valid is False
    assert "not a dictionary" in error

def test_create_temp_dir_name():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    dir_name = create_temp_dir_name(url)
    assert dir_name.startswith("transcript_")
    assert len(dir_name) == len("transcript_") + 8
    
    # Consistency
    assert create_temp_dir_name(url) == dir_name
    
    # Uniqueness
    assert create_temp_dir_name("https://youtube.com/other") != dir_name

def test_create_temp_dir_name_variations():
    urls = [
        "https://youtube.com/watch?v=123",
        "https://youtu.be/123",
        "https://www.youtube.com/watch?v=123&t=10s",
        "youtube.com/watch?v=123"
    ]
    # Each unique string should have unique hash
    hashes = [create_temp_dir_name(u) for u in urls]
    assert len(set(hashes)) == len(urls)

def test_select_subtitle_priority():
    base = "transcript"
    # Alphabetical order: transcript.en-US.srt comes BEFORE transcript.en.srt
    # Because '-' (45) < '.' (46)
    assert select_subtitle(["transcript.en-US.srt", "transcript.en.srt"], base) == "transcript.en-US.srt"
    
    # Auto en-US vs Auto en
    assert select_subtitle(["transcript.en-US.auto.srt", "transcript.en.auto.srt"], base) == "transcript.en-US.auto.srt"
    
    # Manual any vs Auto any
    assert select_subtitle(["transcript.fr.srt", "transcript.en.auto.srt"], base) == "transcript.fr.srt"

@pytest.mark.parametrize("url,expected", [
    ("https://youtube.com/1", "transcript_3c52936a"),
    ("https://youtube.com/2", "transcript_9aa625c6"),
])
def test_create_temp_dir_name_parameterized(url, expected):
    assert create_temp_dir_name(url) == expected

def test_validate_json_data_types():
    # Test with unexpected types
    assert validate_json_data(123)[0] is False
    assert validate_json_data([])[0] is False

